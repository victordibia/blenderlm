import os
from pydantic import BaseModel
import json
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionSystemMessageParam
)
from openai.types.responses import EasyInputMessageParam, EasyInputMessage
from openai._types import NOT_GIVEN
from typing import AsyncGenerator, List, Optional, Callable, Dict, Any
from PIL import Image
import inspect
import asyncio

from blenderlm.client.client import BlenderLMClient
from blenderlm.client.tools import capture_viewport, get_blender_scene_info

from ._base_agent import BaseAgent, AgentMessage, AgentTask, AgentMessageMetadata, AgentEventMessage, BaseAgentMessage

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
        model_name: str = "gpt-4-turbo",
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
        
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        
        # Store tool list and create mappings
        self.tools_list = tools if tools else []
        self.tool_map: Dict[str, Callable] = {}
        self.tool_schemas: List[ChatCompletionToolParam] = []
        self.instructions = instructions or "You are a helpful assistant. Use the tools provided to complete tasks."
        self.blender_client = BlenderLMClient()
        
        if self.tools_list:
            for tool_func in self.tools_list:
                if hasattr(tool_func, '__name__'):
                    self.tool_map[tool_func.__name__] = tool_func
                    # Generate tool schema from function
                    schema = self._generate_tool_schema(tool_func)
                    if schema:
                        self.tool_schemas.append(schema)
                else:
                    print(f"Warning: Tool {tool_func} might not be callable by name via function calling.")
        else:
            print("Warning: No tools provided during OpenAIAgent initialization.")

    async def _verify_task(self, task: AgentTask | str) -> None:
        """
        Use a model to verify that the task is complete 
        """

        scene_info = await get_blender_scene_info(session_id="")

        verification_prompt = f"""
        You are highly qualified 3D verification expert that can verify if a given task has been satisfactorily accomplished in Blender. You will be given information on the task, a visual representation of the Blender Scene. Your task is to verify if the provided task is complete. Given the task, and the state of the Blender Scene, please provide a verification status. This will include a boolean status indicating if the task is complete, a reason for the status, and a description of the next steps if the task is not complete. 
        The followig materials are currently in the scene: {scene_info}
        """

        # blender_image = self.blender_client.()
        scene_capture = await capture_viewport(filepath=None, camera_view=False, return_base64=True, session_id="")

        
        

        response = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": verification_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": task.to_text() if isinstance(task, AgentTask) else task},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{scene_capture.image_base64}"}
                        }
                    ]
                }
            ],
            response_format=VerificationStatus,
        )

        result = response.choices[0].message.parsed 

        print(f"Verification Result: {result}") 

    def _generate_tool_schema(self, func: Callable) -> Optional[ChatCompletionToolParam]:
        """
        Generate OpenAI function schema from a Python function.
        This is a basic implementation - you may want to enhance it with more sophisticated
        type inference or use a library like pydantic for better schema generation.
        """
        try:
            sig = inspect.signature(func)
            parameters = {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
            
            for param_name, param in sig.parameters.items():
                param_info = {"type": "string", "description": f"Parameter {param_name}"}
                
                # Basic type inference
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_info["type"] = "integer"
                    elif param.annotation == float:
                        param_info["type"] = "number"
                    elif param.annotation == bool:
                        param_info["type"] = "boolean"
                    elif param.annotation == list:
                        param_info["type"] = "array"
                    elif param.annotation == dict:
                        param_info["type"] = "object"
                
                parameters["properties"][param_name] = param_info
                
                # Mark as required if no default value
                if param.default == inspect.Parameter.empty:
                    parameters["required"].append(param_name)
            
            return ChatCompletionToolParam(
                type="function",
                function={
                    "name": func.__name__,
                    "description": func.__doc__ or f"Function {func.__name__}",
                    "parameters": parameters,
                    "strict": True
                }
            )
        except Exception as e:
            print(f"Warning: Could not generate schema for function {func.__name__}: {e}")
            return None

    async def _task_to_openai_messages(self, task: AgentTask | str) -> List[ChatCompletionMessageParam]:
        """Converts the AgentTask into OpenAI messages format, prepending self.instructions as a system message."""
        messages: List[ChatCompletionMessageParam] = []
        # Add system message with self.instructions
        messages.append(ChatCompletionSystemMessageParam(
            role="system",
            content=self.instructions
        ))
        scene_info = get_blender_scene_info(session_id="")
        scene_status_prompt = f""" The current status of the blender scene is as follows: 
        {scene_info}
        """
        scene_image = await capture_viewport(filepath=None, camera_view=False, return_base64=True, session_id="")

        messages.append(ChatCompletionSystemMessageParam(
            role="system",
            content=scene_status_prompt
        ))
        if scene_image:
            messages.append(ChatCompletionUserMessageParam(
                role="user",
                content=[
                    {"type": "text", "text": "Here is the current Blender scene image:"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{scene_image.image_base64}"}
                    }
                ]
            ))

        if isinstance(task, str):
            messages.append(ChatCompletionUserMessageParam(
                role="user", 
                content=task
            ))
        elif isinstance(task, list):
            content = []
            for item in task:
                if isinstance(item, str):
                    content.append({"type": "text", "text": item})
                elif isinstance(item, Image.Image):
                    # Convert PIL Image to base64 for OpenAI
                    import io
                    import base64
                    buffer = io.BytesIO()
                    item.save(buffer, format='PNG')
                    img_str = base64.b64encode(buffer.getvalue()).decode()
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_str}"}
                    })
                else:
                    print(f"Warning: Unsupported type in task list: {type(item)}. Skipping.")
            
            if content:
                messages.append(ChatCompletionUserMessageParam(
                    role="user", 
                    content=content
                ))
        else:
            raise TypeError(f"Unsupported task type: {type(task)}")
        
        return messages

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool function and return the result as a string."""
        if tool_name not in self.tool_map:
            return f"Error: Tool '{tool_name}' not found"
        
        tool_func = self.tool_map[tool_name]
        
        try:
            print(f"Executing tool: {tool_name} with args: {tool_args}")
            
            # Check if function is async
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**tool_args)
            else:
                result = tool_func(**tool_args)
            
            # Convert result to string
            if isinstance(result, str):
                return result
            elif isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            else:
                return str(result)
                
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            print(error_msg)
            return error_msg

    async def run(self, task: AgentTask| str) -> List[BaseAgentMessage]:
        """
        Runs the agent with the given task and returns a list of all messages
        generated during the execution.
        """
        messages = []
        async for message in self.run_stream(task):
            messages.append(message)
        return messages

    async def run_stream(self, task: AgentTask | str) -> AsyncGenerator[BaseAgentMessage, None]:
        """
        Runs the agent with the given task and streams intermediate messages.
        Yields only 3 key messages: thinking, using tools (if needed), and final response.
        """
        scene_status_prompt = """
        
        """
        messages: List[ChatCompletionMessageParam] = await self._task_to_openai_messages(task)
        tool_calls_requested = []
        
        try:
            # 1. Thinking message (now as AgentEventMessage)
            yield AgentEventMessage(
                content="🤖 Thinking...",
                role="assistant",
                event_type="status",
            )
            
            # Initial API call
            response = self.client.chat.completions.create(
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
                yield AgentEventMessage(
                    content=f"🔧 Using tools: {', '.join(tool_names)}",
                    role="assistant",
                    event_type="tool_usage",
                    metadata=AgentMessageMetadata(finish_reason="tool_calls")
                )
                
                # Execute all tool calls
                while message.tool_calls:
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
                        tool_result = await self._execute_tool(function_name, function_args)
                        
                        # Add tool result to conversation
                        messages.append(ChatCompletionToolMessageParam(
                            role="tool",
                            tool_call_id=tool_call.id,
                            content=tool_result
                        ))
                    
                    # Make another API call with the updated conversation
                    response = self.client.chat.completions.create(
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
                    } if response.usage else None
                )
            )
            await self._verify_task(task)
            
        except Exception as e:
            # Error as AgentEventMessage
            yield AgentEventMessage(
                content=f"❌ An error occurred: {e}",
                role="assistant",
                event_type="error",
                metadata=AgentMessageMetadata(
                    error=str(e),
                    finish_reason="error"
                )
            )