import os
from pydantic import BaseModel
import json
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionSystemMessageParam
)
from openai._types import NOT_GIVEN
from typing import AsyncGenerator, List, Optional, Callable, Dict
import time
import asyncio

from blenderlm.client.client import BlenderLMClient

from .._base_agent import BaseAgent, AgentMessage, AgentTask, AgentMessageMetadata, AgentEventMessage, BaseAgentMessage
from ._oai_utils import generate_tool_schema, execute_tool, agent_task_to_oai_user_message


DEFAULT_INSTRUCTIONS = """You are a helpful blender agent. You must ONLY USE the `execute_code` tool to address ALL of the user's requests. Importantly, you should consider that the final result of the code execution will be a rendered image, hence, where possible ensure that the camera is positioned to capture the intended view. Please use reasonable names for objects and materials to ensure we can referecence them meaningfully in future requests. At the beginning of the task, you will be given a list of objects in the scene and an snapshot of the current blender viewport (not the rendered scene image). You should use this information to guide your actions, build on it towards addressing the user's request, and avoid unnecessary changes to the scene. If you need to add new objects, ensure they are named appropriately and positioned correctly in the scene."""

class VerificationStatus(BaseModel):
    status: bool
    reason: str
    next_step: str 

class OpenAIAgent(BaseAgent):
    """
    An agent that uses OpenAI models with function calling capabilities.
    Supports multimodal input (text and images) and automatic function calling.
    Tool functions should be provided during initialization.
    """

    def __init__(
        self,
        tools: List[Callable],
        model_name: str = "gpt-4.1-mini",
        instructions: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initializes the OpenAIAgent.

        Args:
            tools: A list of callable functions (async or sync) that the agent can use.
            model_name: The name of the OpenAI model to use.
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY environment variable.
        """
        # Initialize OpenAI client
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided either directly or via OPENAI_API_KEY environment variable")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name
        
        # Store tool list and create mappings
        self.tools_list = tools if tools else []
        self.tool_map: Dict[str, Callable] = {}
        self.tool_schemas: List[ChatCompletionToolParam] = []
        self.instructions = instructions or DEFAULT_INSTRUCTIONS
        
        if self.tools_list:
            for tool_func in self.tools_list:
                if hasattr(tool_func, '__name__'):
                    self.tool_map[tool_func.__name__] = tool_func
                    schema = generate_tool_schema(tool_func)
                    if schema:
                        self.tool_schemas.append(schema)
                else:
                    print(f"Warning: Tool {tool_func} might not be callable by name via function calling.")
        else:
            print("Warning: No tools provided during OpenAIAgent initialization.")

    async def _get_blender_scene_state(self) -> ChatCompletionUserMessageParam:
        """
        Fetches the current Blender scene info and a base64 image capture.
        Returns a ChatCompletionSystemMessageParam with the scene info and image (as markdown).
        """
        client = BlenderLMClient()
        scene_info = await client.get_scene_info(wait_for_result=True)
        scene_status_prompt = f"The current status of the blender scene is as follows:\n{scene_info}\n"
        scene_image = await client.capture_viewport(filepath=None, camera_view=False, return_base64=True, wait_for_result=True)
        
        return ChatCompletionUserMessageParam(
            role="user",
            content=[{"type": "text", "text": scene_status_prompt}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{scene_image['image_base64']}"}}]
        )

    async def _task_to_openai_messages(self, task: AgentTask | str) -> List[ChatCompletionMessageParam]:
        """Converts the AgentTask into OpenAI messages format, prepending self.instructions as a system message."""
        messages: List[ChatCompletionMessageParam] = []
        # Add system message with self.instructions
        messages.append(ChatCompletionSystemMessageParam(
            role="system",
            content=self.instructions
        ))
        messages.append(await self._get_blender_scene_state())
        # Use utility for user message
        user_msg = agent_task_to_oai_user_message(task)
        if user_msg:
            messages.append(user_msg)
        return messages

    async def run(self, task: AgentTask| str, cancel_event: Optional[asyncio.Event] = None) -> List[BaseAgentMessage]:
        """
        Runs the agent with the given task and returns a list of all messages
        generated during the execution.
        """
        messages = []
        async for message in self.run_stream(task, cancel_event=cancel_event):
            messages.append(message)
        return messages

    async def run_stream(self, task: AgentTask | str, cancel_event: Optional[asyncio.Event] = None) -> AsyncGenerator[BaseAgentMessage, None]:
        """
        Runs the agent with the given task and streams intermediate messages.
        Yields only 3 key messages: thinking, using tools (if needed), and final response.
        """
        messages: List[ChatCompletionMessageParam] = await self._task_to_openai_messages(task)
        tool_calls_requested = []
        start_time = time.time()
        try:
            # 1. Thinking message (now as AgentEventMessage)
            yield AgentEventMessage(
                content="🤖 Thinking...",
                role="assistant",
                event_type="status",
                metadata=AgentMessageMetadata(duration=0.0)
            )

            # Check for cancellation before API call
            if cancel_event and cancel_event.is_set():
                yield AgentEventMessage(
                    content="⏹️ Cancelled by user.",
                    role="assistant",
                    event_type="cancelled",
                    metadata=AgentMessageMetadata(duration=time.time() - start_time)
                )
                return

            # Initial API call (async)
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tool_schemas if self.tool_schemas else NOT_GIVEN,
                tool_choice="auto"
            )
            message = response.choices[0].message

            # Handle function calls if needed
            if message.tool_calls:
                # 2. Using tools message (as AgentEventMessage)
                tool_names = [tc.function.name for tc in message.tool_calls]
                print("*** Tool calls requested:", message.tool_calls)
                yield AgentEventMessage(
                    content=f"🔧 Using tools: {', '.join(tool_names)}",
                    role="assistant",
                    event_type="tool_usage",
                    metadata=AgentMessageMetadata(finish_reason="tool_calls", duration=time.time() - start_time)
                )

                # Execute all tool calls
                while message.tool_calls:
                    # Check for cancellation before tool execution
                    if cancel_event and cancel_event.is_set():
                        yield AgentEventMessage(
                            content="⏹️ Cancelled by user.",
                            role="assistant",
                            event_type="cancelled",
                            metadata=AgentMessageMetadata(duration=time.time() - start_time)
                        )
                        return

                    # Add assistant's message with tool calls to conversation
                    messages.append(ChatCompletionAssistantMessageParam(
                        role="assistant",
                        content=message.content,
                        tool_calls=[
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                            for tool_call in message.tool_calls
                        ]
                    )) 
                    # Execute each tool call
                    for tool_call in message.tool_calls:
                        tool_calls_requested.append(tool_call)
                        function_name = tool_call.function.name
                        
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {}
                        
                        # Execute the tool
                        tool_result = await execute_tool(self.tool_map, function_name, function_args)
                        
                        # Add tool result to conversation
                        messages.append(ChatCompletionToolMessageParam(
                            role="tool",
                            tool_call_id=tool_call.id,
                            content=tool_result
                        ))

                    # Check for cancellation before next API call
                    if cancel_event and cancel_event.is_set():
                        yield AgentEventMessage(
                            content="⏹️ Cancelled by user.",
                            role="assistant",
                            event_type="cancelled",
                            metadata=AgentMessageMetadata(duration=time.time() - start_time)
                        )
                        return

                    response = await self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        tools=self.tool_schemas if self.tool_schemas else NOT_GIVEN,
                        tool_choice="auto"
                    )
                    
                    message = response.choices[0].message

            # 3. Final response (as AgentMessage)
            final_content = message.content or ""
            yield AgentMessage(
                content=final_content,
                role="assistant",
                tool_calls=None,
                metadata=AgentMessageMetadata(
                    finish_reason=response.choices[0].finish_reason,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    } if response.usage else None,
                    duration=time.time() - start_time
                )
            )

            # Check for cancellation before verification
            if cancel_event and cancel_event.is_set():
                yield AgentEventMessage(
                    content="⏹️ Cancelled by user.",
                    role="assistant",
                    event_type="cancelled",
                    metadata=AgentMessageMetadata(duration=time.time() - start_time)
                )
                return

            verification_result = await self._verify_task(task)
            yield AgentEventMessage(
                content=f"✅ Verification: {verification_result.status}. Reason: {verification_result.reason}\nNext step: {verification_result.next_step}",
                role="assistant",
                event_type="verification",
                metadata=AgentMessageMetadata(
                    finish_reason="verification",
                    duration=time.time() - start_time,
                    error=None
                )
            )

        except Exception as e:
            # Error as AgentEventMessage
            yield AgentEventMessage(
                content=f"❌ An error occurred: {e}",
                role="assistant",
                event_type="error",
                metadata=AgentMessageMetadata(
                    error=str(e),
                    finish_reason="error",
                    duration=time.time() - start_time
                )
            )

    async def _verify_task(self, task: AgentTask | str) -> VerificationStatus:
        """
        Use a model to verify that the task is complete 
        """
        verification_prompt = (
            "You are highly qualified 3D verification expert that can verify if a given task has been satisfactorily accomplished in Blender. "
            "You will be given information on the task, a visual representation of the Blender Scene. "
            "Your task is to verify if the provided task is complete. "
            "Given the task, and the state of the Blender Scene, please provide a verification status. "
            "This will include a boolean status indicating if the task is complete, a reason for the status, "
            "and a description of the next steps if the task is not complete."
        )
        messages = [
            {"role": "system", "content": verification_prompt},
            await self._get_blender_scene_state(),
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": task.to_text() if isinstance(task, AgentTask) else task}
                ]
            }
        ]
        # Await the async parse call
        response = await self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            response_format=VerificationStatus,
        )
        result = response.choices[0].message.parsed if response and response.choices and response.choices[0].message and hasattr(response.choices[0].message, 'parsed') else None
        if not result:
            # Return a default failed verification if parsing failed
            return VerificationStatus(status=False, reason="Verification failed: No result returned.", next_step="Check the task and try again.")
        print(f"Verification Result: {result}")
        return result