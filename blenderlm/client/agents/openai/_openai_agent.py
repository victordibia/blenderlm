import os
import json
import time
import asyncio
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

from blenderlm.client.client import BlenderLMClient

from .._base_agent import (
    BaseAgent, AgentMessage, AgentTask, AgentMessageMetadata, 
    AgentEventMessage, BaseAgentMessage, ToolCallMessage, 
    ToolResultMessage, VerificationMessage, ToolCall, ToolResult, 
    VerificationStatus, PlanMessage, Plan, PlanStep
)
from ._oai_utils import get_blender_scene_state, generate_tool_schema, execute_tool, agent_task_to_oai_user_message
from ._planner_agent import PlannerAgent
from ._verifier_agent import VerifierAgent


DEFAULT_INSTRUCTIONS = """You are a helpful blender agent. You must ONLY USE the `execute_code` tool to address ALL of the user's requests. Importantly, you should consider that the final result of the code execution will be a rendered image, hence, where possible ensure that the camera is positioned to capture reasonable and representative view. You are also an expert and MUST consider important things like lighting, composition, and object placement. Please use reasonable names for objects and materials to ensure we can referecence them meaningfully in future requests. At the beginning of the task, you will be given a list of objects in the scene and an snapshot of the current blender viewport (note that this may not be perfect and not every aspect of the image is visible - use this as a general reference). You should use this information to guide your actions, build on it towards addressing the user's request, and avoid unnecessary changes to the scene. If you need to add new objects, ensure they are named appropriately and positioned correctly in the scene."""


class OpenAIAgent(BaseAgent):
    """
    An agent that uses OpenAI models with function calling capabilities.
    Supports multimodal input (text and images) and automatic function calling.
    Tool functions should be provided during initialization.
    """

    def __init__(
        self,
        tools: List[Callable],
        model_name: str = "gpt-4.1",
        instructions: Optional[str] = None,
        api_key: Optional[str] = None,
        max_steps: int = 3,
        use_planner: bool = True
    ):
        """
        Initializes the OpenAIAgent.

        Args:
            tools: A list of callable functions (async or sync) that the agent can use.
            model_name: The name of the OpenAI model to use.
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY environment variable.
            max_steps: Maximum number of execution steps per task/subtask.
            use_planner: Whether to use the planner to decompose complex tasks.
        """
        # Initialize OpenAI client
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key must be provided either directly or via OPENAI_API_KEY environment variable")

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
                    print(
                        f"Warning: Tool {tool_func} might not be callable by name via function calling.")
        else:
            print("Warning: No tools provided during OpenAIAgent initialization.")

        self.max_steps = max_steps
        self.tool_log: List[str] = []
        
        # Initialize planner
        self.use_planner = use_planner
        self.planner: Optional[PlannerAgent] = None
        if self.use_planner:
            self.planner = PlannerAgent(model_name=model_name, api_key=api_key)
        
        # Initialize verifier
        self.verifier = VerifierAgent(model_name=model_name, api_key=api_key)

    async def _get_blender_scene_state(self) -> ChatCompletionUserMessageParam:
        """
        Deprecated: Use get_blender_scene_state from _oai_utils instead.
        """
        import warnings
        warnings.warn("Use get_blender_scene_state from _oai_utils instead.", DeprecationWarning)
        return await get_blender_scene_state()

    async def _task_to_openai_messages(self, task: AgentTask | str) -> List[ChatCompletionMessageParam]:
        """Converts the AgentTask into OpenAI messages format, prepending self.instructions as a system message."""
        messages: List[ChatCompletionMessageParam] = []
        # Add system message with self.instructions
        messages.append(ChatCompletionSystemMessageParam(
            role="system",
            content=self.instructions
        ))
        messages.append(await get_blender_scene_state())
        # Use utility for user message
        user_msg = agent_task_to_oai_user_message(task)
        if user_msg:
            messages.append(user_msg)
        return messages

    async def run(self, task: AgentTask | str, cancel_event: Optional[asyncio.Event] = None) -> List[BaseAgentMessage]:
        """
        Runs the agent with the given task and returns a list of all messages
        generated during the execution.
        """
        messages = []
        async for message in self.run_stream(task, cancel_event=cancel_event):
            messages.append(message)
        return messages

    async def _build_prompt(self, original_task: str, tool_log: list, verifier_msg: Optional[VerificationStatus]) -> List[ChatCompletionMessageParam]:
        """
        Build a compact prompt for each step, including task, tool log, verifier feedback, and scene state.
        """
        parts = [
            ChatCompletionSystemMessageParam(
                role="system", content=self.instructions),
            ChatCompletionUserMessageParam(
                role="user", content=f"The user's task is:\n{original_task}")
        ]
        if tool_log:
            parts.append(ChatCompletionUserMessageParam(
                role="user",
                content="Recent tool actions:\n" +
                "\n".join(f"- {p}" for p in tool_log[-6:])
            ))
        if verifier_msg and not verifier_msg.status:
            parts.append(ChatCompletionUserMessageParam(
                role="user",
                content=(
                    f"A verifier has reviewed the work and says it is **NOT complete** because:\n"
                    f"{verifier_msg.reason}\n\n"
                    f"Suggested next action:\n{verifier_msg.next_step}"
                )
            ))
        parts.append(await get_blender_scene_state())
        return parts

    async def _step(self, messages: List[ChatCompletionMessageParam], cancel_event: Optional[asyncio.Event] = None) -> AsyncGenerator[tuple, None]:
        """
        Perform a single agent step: send prompt, handle tool calls, yield messages as they're produced.
        Yields tuples of (message_type, message_or_data) where message_type is one of:
        - 'tool_call': yielded when a tool is about to be called
        - 'tool_result': yielded when a tool execution completes
        - 'final': yielded at the end with the final assistant message
        """
        tool_calls_requested = []
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=self.tool_schemas if self.tool_schemas else NOT_GIVEN,
            tool_choice="auto"
        )
        message = response.choices[0].message
        
        # Handle function calls if needed
        if message.tool_calls:
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
            
            for tool_call in message.tool_calls:
                tool_calls_requested.append(tool_call)
                function_name = tool_call.function.name
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    function_args = {}
                
                # Create structured ToolCall object
                structured_tool_call = ToolCall(
                    id=tool_call.id,
                    name=function_name,
                    arguments=function_args
                )
                
                # Yield ToolCallMessage immediately
                yield ('tool_call', ToolCallMessage(
                    tool_call=structured_tool_call,
                    content=f"Calling tool: {function_name}",
                    role="assistant",
                    metadata=AgentMessageMetadata()
                ))
                
                try:
                    tool_result = await execute_tool(self.tool_map, function_name, function_args)
                    
                    # Create structured ToolResult object
                    structured_tool_result = ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=function_name,
                        result=str(tool_result),
                        success=True
                    )
                    
                    # Yield ToolResultMessage immediately
                    yield ('tool_result', ToolResultMessage(
                        tool_result=structured_tool_result,
                        content=f"Tool result for {function_name}",
                        role="tool",
                        metadata=AgentMessageMetadata()
                    ))
                    
                    # Update tool log with cleaner format
                    self.tool_log.append(f"{function_name}({function_args}) -> {str(tool_result)[:100]}...")
                    
                    messages.append(ChatCompletionToolMessageParam(
                        role="tool",
                        tool_call_id=tool_call.id,
                        content=str(tool_result)
                    ))
                    
                except Exception as e:
                    # Handle tool execution errors
                    structured_tool_result = ToolResult(
                        tool_call_id=tool_call.id,
                        tool_name=function_name,
                        result="",
                        success=False,
                        error=str(e)
                    )
                    
                    # Yield error ToolResultMessage immediately
                    yield ('tool_result', ToolResultMessage(
                        tool_result=structured_tool_result,
                        content=f"Tool error for {function_name}: {str(e)}",
                        role="tool",
                        metadata=AgentMessageMetadata(error=str(e))
                    ))
                    
                    self.tool_log.append(f"{function_name}({function_args}) -> ERROR: {str(e)}")
                    
                    messages.append(ChatCompletionToolMessageParam(
                        role="tool",
                        tool_call_id=tool_call.id,
                        content=f"Error executing tool: {str(e)}"
                    ))
            
            # Get final response after tool calls
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tool_schemas if self.tool_schemas else NOT_GIVEN,
                tool_choice="auto"
            )
            message = response.choices[0].message
            
        # Yield final message
        yield ('final', (message, tool_calls_requested))

    async def run_stream(self, task: AgentTask | str, cancel_event: Optional[asyncio.Event] = None) -> AsyncGenerator[BaseAgentMessage, None]:
        """
        Main execution method with optional planning phase.
        """
        start_time = time.time()
        original_task = task.to_text() if isinstance(task, AgentTask) else str(task)
        self.tool_log = []
        
        if self.use_planner and self.planner:
            # Execute with planning
            async for message in self._run_with_planning(original_task, cancel_event, start_time):
                yield message
        else:
            # Execute without planning (original behavior)
            async for message in self._run_direct(original_task, cancel_event, start_time):
                yield message

    async def _verify_task(self, task: AgentTask | str) -> VerificationStatus:
        """
        Use the VerifierAgent to verify that the task is complete.
        """
        return await self.verifier.run(task, self.tool_log)

    async def _run_with_planning(self, task: str, cancel_event: Optional[asyncio.Event], start_time: float) -> AsyncGenerator[BaseAgentMessage, None]:
        """
        Execute task using the planner to break it down into steps.
        """
        # Planning phase
        yield AgentEventMessage(
            content="🤔 Analyzing task and creating execution plan...",
            role="assistant",
            event_type="planning_start",
            metadata=AgentMessageMetadata(duration=time.time() - start_time)
        )
        
        try:
            # Type guard - we know planner is not None due to the check above
            assert self.planner is not None
            plan_message = await self.planner.plan(task)
            
            # Emit the plan message directly (it already contains formatted content)
            yield plan_message
            
            # Execute each step in the plan
            for step_idx, step in enumerate(plan_message.plan.steps, 0):  # 0-based indexing for metadata
                if cancel_event and cancel_event.is_set():
                    yield AgentEventMessage(
                        content="⏹️ Planning execution cancelled.",
                        role="assistant",
                        event_type="cancelled",
                        metadata=AgentMessageMetadata(duration=time.time() - start_time)
                    )
                    return
                
                yield AgentEventMessage(
                    content=f"🎯 Step {step_idx+1}/{len(plan_message.plan.steps)}: {step.task}",  # Display as 1-based
                    role="assistant",
                    event_type="step_start",
                    metadata=AgentMessageMetadata(
                        duration=time.time() - start_time,
                        step_index=step_idx,  # 0-based for frontend
                        total_steps=len(plan_message.plan.steps)
                    )
                )
                
                # Execute this individual step
                step_completed = False
                async for step_message in self._execute_single_step(step.task, step_idx+1, len(plan_message.plan.steps), cancel_event, start_time):  # Pass display index
                    # Add step tracking to messages from step execution
                    if hasattr(step_message, 'metadata') and step_message.metadata:
                        step_message.metadata.step_index = step_idx  # 0-based for frontend
                        step_message.metadata.total_steps = len(plan_message.plan.steps)
                    yield step_message
                    
                    # Check if this step completed successfully
                    if isinstance(step_message, VerificationMessage) and step_message.verification.status:
                        step_completed = True
                        yield AgentEventMessage(
                            content=f"✅ Step {step_idx+1} completed: {step.task}",  # Display as 1-based
                            role="assistant",
                            event_type="step_completed",
                            metadata=AgentMessageMetadata(
                                duration=time.time() - start_time,
                                step_index=step_idx,  # 0-based for frontend
                                total_steps=len(plan_message.plan.steps)
                            )
                        )
                        break
                
                if not step_completed:
                    yield AgentEventMessage(
                        content=f"⚠️ Step {step_idx+1} did not complete successfully, continuing with next step...",  # Display as 1-based
                        role="assistant",
                        event_type="step_partial",
                        metadata=AgentMessageMetadata(
                            duration=time.time() - start_time,
                            step_index=step_idx,  # 0-based for frontend
                            total_steps=len(plan_message.plan.steps)
                        )
                    )
            
            # Final verification of the complete task
            yield AgentEventMessage(
                content="🔍 Performing final verification of complete task...",
                role="assistant",
                event_type="final_verification",
                metadata=AgentMessageMetadata(duration=time.time() - start_time)
            )
            
            final_verification = await self._verify_task(task)
            yield VerificationMessage(
                verification=final_verification,
                content="Final task verification completed",
                role="assistant",
                metadata=AgentMessageMetadata(duration=time.time() - start_time)
            )
            
            if final_verification.status:
                yield AgentMessage(
                    content="🎉 Task completed successfully using planned approach!",
                    role="assistant",
                    metadata=AgentMessageMetadata(
                        finish_reason="completed",
                        duration=time.time() - start_time
                    )
                )
            else:
                yield AgentMessage(
                    content=f"⚠️ Task partially completed. {final_verification.reason}",
                    role="assistant",
                    metadata=AgentMessageMetadata(
                        finish_reason="partial",
                        duration=time.time() - start_time
                    )
                )
                
        except Exception as e:
            yield AgentEventMessage(
                content=f"❌ Planning failed: {str(e)}. Falling back to direct execution...",
                role="assistant",
                event_type="planning_error",
                metadata=AgentMessageMetadata(error=str(e), duration=time.time() - start_time)
            )
            
            # Fallback to direct execution
            async for message in self._run_direct(task, cancel_event, start_time):
                yield message

    async def _run_direct(self, task: str, cancel_event: Optional[asyncio.Event], start_time: float) -> AsyncGenerator[BaseAgentMessage, None]:
        """
        Execute task directly without planning (original behavior).
        """
        verifier_msg = None
        
        for step in range(self.max_steps):
            messages = await self._build_prompt(task, self.tool_log, verifier_msg)
            
            yield AgentEventMessage(
                content=f"🤖 Thinking... (step {step+1})",
                role="assistant",
                event_type="status",
                metadata=AgentMessageMetadata(duration=time.time() - start_time)
            )
            
            assistant_msg = None
            tool_calls = []
            
            # Stream messages as they're produced
            async for message_type, message_data in self._step(messages, cancel_event=cancel_event):
                if message_type == 'tool_call':
                    yield message_data
                elif message_type == 'tool_result':
                    yield message_data
                elif message_type == 'final':
                    assistant_msg, tool_calls = message_data
                    break
                    
            if cancel_event and cancel_event.is_set():
                yield AgentEventMessage(
                    content="⏹️ Execution cancelled by caller.",
                    role="assistant",
                    event_type="cancelled",
                    metadata=AgentMessageMetadata(duration=time.time() - start_time)
                )
                return
                
            # Verify task completion
            verification_status = await self._verify_task(task)
            
            yield VerificationMessage(
                verification=verification_status,
                content=f"Step {step+1} verification completed",
                role="assistant",
                metadata=AgentMessageMetadata(duration=time.time() - start_time)
            )
            
            if verification_status.status:
                yield AgentMessage(
                    content=assistant_msg.content if assistant_msg else "",
                    role="assistant",
                    tool_calls=None,
                    metadata=AgentMessageMetadata(
                        finish_reason="completed",
                        usage=None,
                        duration=time.time() - start_time
                    )
                )
                break
            
            verifier_msg = verification_status
        else:
            yield AgentEventMessage(
                content=f"⚠️ Max steps ({self.max_steps}) reached. Task may be incomplete.",
                role="assistant",
                event_type="max_steps_exceeded",
                metadata=AgentMessageMetadata(duration=time.time() - start_time)
            )

    async def _execute_single_step(self, step_task: str, step_idx: int, total_steps: int, cancel_event: Optional[asyncio.Event], start_time: float) -> AsyncGenerator[BaseAgentMessage, None]:
        """
        Execute a single step from the plan with its own verification loop.
        """
        verifier_msg = None
        
        for attempt in range(self.max_steps):
            messages = await self._build_prompt(step_task, self.tool_log, verifier_msg)
            
            yield AgentEventMessage(
                content=f"🔧 Executing step {step_idx}/{total_steps} (attempt {attempt+1})",
                role="assistant",
                event_type="step_execution",
                metadata=AgentMessageMetadata(duration=time.time() - start_time)
            )
            
            assistant_msg = None
            
            # Execute the step
            async for message_type, message_data in self._step(messages, cancel_event=cancel_event):
                if message_type == 'tool_call':
                    yield message_data
                elif message_type == 'tool_result':
                    yield message_data
                elif message_type == 'final':
                    assistant_msg, _ = message_data
                    break
                    
            if cancel_event and cancel_event.is_set():
                return
            
            # Verify this specific step
            step_verification = await self._verify_step(step_task)
            yield VerificationMessage(
                verification=step_verification,
                content=f"Step {step_idx} attempt {attempt+1} verification",
                role="assistant",
                metadata=AgentMessageMetadata(duration=time.time() - start_time)
            )
            
            if step_verification.status:
                break
                
            verifier_msg = step_verification

    async def _verify_step(self, step_task: str) -> VerificationStatus:
        """
        Verify completion of a single step using the VerifierAgent.
        """
        return await self.verifier.run(step_task, self.tool_log)
