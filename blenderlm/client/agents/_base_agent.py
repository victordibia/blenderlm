from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Literal, Optional, Union, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from PIL import Image

# Define the type for the task input, allowing string or list containing text and PIL Images
class AgentTask(BaseModel):
    """
    Represents a task input for an agent, allowing a string or a list of strings and PIL Images.
    The content field holds the input data.
    """
    content: Union[str, List[Union[str, Image.Image]]]
    
    model_config = ConfigDict(arbitrary_types_allowed=True) 
    
    def to_text(self) -> str:
        """
        Returns a human-readable string representation of the content,
        using <Image> for image objects.
        """
        if isinstance(self.content, str):
            return self.content
        else:
            return " ".join([item if isinstance(item, str) else "<Image>" for item in self.content])


# Define a model for structured metadata
class AgentMessageMetadata(BaseModel):
    """Structured metadata for an agent message."""
    usage: Optional[Dict[str, int]] = None # e.g., {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    finish_reason: Optional[str] = None # e.g., "stop", "length", "tool_calls", "error"
    error: Optional[str] = None # Details of an error if one occurred
    duration: Optional[float] = None # Duration of the agent run in seconds
    
    # Step tracking fields for planned execution
    step_index: Optional[int] = None # Current step index (0-based) in planned execution
    total_steps: Optional[int] = None # Total number of steps in the plan

    class Config:
        extra = "allow" # Allow other arbitrary fields

# Tool-related models
class ToolCall(BaseModel):
    """Represents a tool/function call."""
    id: str
    name: str
    arguments: Dict[str, Any]

class ToolResult(BaseModel):
    """Represents the result of a tool execution."""
    tool_call_id: str
    tool_name: str
    result: str
    success: bool
    error: Optional[str] = None

class VerificationStatus(BaseModel):
    """Represents the status of task verification."""
    status: bool
    reason: str
    next_step: Optional[str] = None
    confidence: Optional[float] = None

# Planning-related models
class PlanStep(BaseModel):
    """A single step in a task plan."""
    task: str = Field(description="Clear, actionable description of what to accomplish in this step")
    reasoning: str = Field(description="Justification for why this step is necessary and how it contributes to the overall goal")

class Plan(BaseModel):
    """A complete plan for accomplishing a task."""
    steps: List[PlanStep] = Field(description="Ordered list of steps to complete the task")

# Base message for all agent messages
class BaseAgentMessage(BaseModel):
    """Base message object for agent communication."""
    content: Optional[str] = None
    role: Literal["user", "assistant", "tool", "event"] = "assistant"
    metadata: Optional[AgentMessageMetadata] = Field(default_factory=AgentMessageMetadata)
    type: Optional[str] = None  # e.g., "llm", "event", etc.

    def to_text(self) -> str:
        parts = [f"Role: {self.role}"]
        if self.content:
            parts.append(f"Content: {self.content}")
        if self.metadata:
            parts.append(f"Metadata: {self.metadata.model_dump()}")
        if self.type:
            parts.append(f"Type: {self.type}")
        return "\n".join(parts)

# Message for LLM/agent responses
class AgentMessage(BaseAgentMessage):
    """Standardized message object returned by agent runs (LLM/agent responses)."""
    tool_calls: Optional[List[Dict[str, Any]]] = None # For potential tool/function calling
    type: Optional[str] = "llm"

    def to_text(self) -> str:
        parts = [f"Role: {self.role}"]
        if self.content:
            parts.append(f"Content: {self.content}")
        if self.tool_calls:
            parts.append(f"Tool Calls: {self.tool_calls}")
        if self.metadata:
            parts.append(f"Metadata: {self.metadata.model_dump()}")
        parts.append(f"Type: {self.type}")
        return "\n".join(parts)

# Message for event-driven or system messages
class AgentEventMessage(BaseAgentMessage):
    """Message object for random events or system notifications."""
    event_type: Optional[str] = None  # e.g., "system", "notification", etc.
    type: Optional[str] = "event"

    def to_text(self) -> str:
        parts = [f"Role: {self.role}"]
        if self.content:
            parts.append(f"Content: {self.content}")
        if self.event_type:
            parts.append(f"Event Type: {self.event_type}")
        if self.metadata:
            parts.append(f"Metadata: {self.metadata.model_dump()}")
        parts.append(f"Type: {self.type}")
        return "\n".join(parts)

# Specialized message types for tools and verification
class ToolCallMessage(BaseAgentMessage):
    """Message representing a tool/function call."""
    tool_call: ToolCall
    type: Optional[str] = "tool_call"
    role: Literal["user", "assistant", "tool", "event"] = "assistant"

    def to_text(self) -> str:
        parts = [f"Role: {self.role}"]
        parts.append(f"Tool Call: {self.tool_call.name}({self.tool_call.arguments})")
        if self.content:
            parts.append(f"Content: {self.content}")
        if self.metadata:
            parts.append(f"Metadata: {self.metadata.model_dump()}")
        parts.append(f"Type: {self.type}")
        return "\n".join(parts)

class ToolResultMessage(BaseAgentMessage):
    """Message representing the result of a tool execution."""
    tool_result: ToolResult
    type: Optional[str] = "tool_result"
    role: Literal["user", "assistant", "tool", "event"] = "tool"

    def to_text(self) -> str:
        parts = [f"Role: {self.role}"]
        parts.append(f"Tool Result: {self.tool_result.tool_name} -> {self.tool_result.result[:100]}...")
        if not self.tool_result.success and self.tool_result.error:
            parts.append(f"Error: {self.tool_result.error}")
        if self.content:
            parts.append(f"Content: {self.content}")
        if self.metadata:
            parts.append(f"Metadata: {self.metadata.model_dump()}")
        parts.append(f"Type: {self.type}")
        return "\n".join(parts)

class VerificationMessage(BaseAgentMessage):
    """Message representing task verification status."""
    verification: VerificationStatus
    type: Optional[str] = "verification"
    role: Literal["user", "assistant", "tool", "event"] = "assistant"

    def to_text(self) -> str:
        parts = [f"Role: {self.role}"]
        parts.append(f"Verification: {self.verification.reason}")
        if not self.verification.status and self.verification.next_step:
            parts.append(f"Next Step: {self.verification.next_step}")
        if self.verification.confidence:
            parts.append(f"Confidence: {self.verification.confidence:.2f}")
        if self.content:
            parts.append(f"Content: {self.content}")
        if self.metadata:
            parts.append(f"Metadata: {self.metadata.model_dump()}")
        parts.append(f"Type: {self.type}")
        return "\n".join(parts)

class PlanMessage(BaseAgentMessage):
    """Message representing a planning action or proposal."""
    plan: Plan  # Now we can use Plan directly since it's defined above
    type: Optional[str] = "plan"
    role: Literal["user", "assistant", "tool", "event"] = "assistant"

    def to_text(self) -> str:
        parts = [f"Role: {self.role}"]
        if self.plan:
            parts.append(f"Plan: {len(self.plan.steps)} steps")
            for i, step in enumerate(self.plan.steps, 1):
                parts.append(f"  Step {i}: {step.task}")
        if self.content:
            parts.append(f"Content: {self.content}")
        if self.metadata:
            parts.append(f"Metadata: {self.metadata.model_dump()}")
        parts.append(f"Type: {self.type}")
        return "\n".join(parts)


# Define the abstract base class for all agents
class BaseAgent(ABC):
    """Abstract base class for language model agents."""

    @abstractmethod
    async def run(self, task: AgentTask) -> List[BaseAgentMessage]:
        """
        Runs the agent with the given task and returns a list of all messages
        generated during the execution, representing the full exchange.

        Args:
            task: The input task, which can be a string or a list containing
                  strings and PIL Image objects.

        Returns:
            A list of BaseAgentMessage objects. The list represents the sequence of
            messages, often including the initial input, any tool interactions,
            and the final agent response.
        """
        pass

    @abstractmethod
    async def run_stream(self, task: AgentTask) -> AsyncGenerator[BaseAgentMessage, None]:
        """
        Runs the agent with the given task and streams the response.

        Args:
            task: The input task, which can be a string or a list containing
                  strings and PIL Image objects.

        Yields:
            BaseAgentMessage objects as they are generated by the agent.
        """
        # The 'yield' statement is needed to make this an async generator method.
        # The actual implementation in subclasses will yield results.
        # This line is just a placeholder for type checking and abstract method definition.
        if False: # pragma: no cover
            yield AgentMessage()

