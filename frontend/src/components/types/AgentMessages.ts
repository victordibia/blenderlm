export interface AgentMessageMetadata {
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  finish_reason?: string; // "stop", "length", "tool_calls", "error"
  error?: string;
  duration?: number; // Duration in seconds

  // Step tracking fields for planned execution
  step_index?: number; // Current step index (0-based) in planned execution
  total_steps?: number; // Total number of steps in the plan

  [key: string]: any; // Allow additional fields
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ToolResult {
  tool_call_id: string;
  tool_name: string;
  result: string;
  success: boolean;
  error?: string;
}

export interface VerificationStatus {
  status: boolean;
  reason: string;
  next_step?: string;
  confidence?: number;
}

export interface PlanStep {
  task: string;
  reasoning: string;
}

export interface Plan {
  steps: PlanStep[];
}

export type MessageRole = "user" | "assistant" | "tool" | "event";
export type MessageType =
  | "llm"
  | "event"
  | "tool_call"
  | "tool_result"
  | "verification"
  | "plan";

export interface BaseAgentMessage {
  content?: string;
  role: MessageRole;
  metadata?: AgentMessageMetadata;
  type?: MessageType;
}

export interface AgentMessage extends BaseAgentMessage {
  tool_calls?: Array<Record<string, any>>;
  type?: "llm";
}

export interface AgentEventMessage extends BaseAgentMessage {
  event_type?: string; // "system", "notification", etc.
  type?: "event";
}

export interface ToolCallMessage extends BaseAgentMessage {
  tool_call: ToolCall;
  type?: "tool_call";
  role: "assistant";
}

export interface ToolResultMessage extends BaseAgentMessage {
  tool_result: ToolResult;
  type?: "tool_result";
  role: "tool";
}

export interface VerificationMessage extends BaseAgentMessage {
  verification: VerificationStatus;
  type?: "verification";
  role: "assistant";
}

export interface PlanMessage extends BaseAgentMessage {
  plan: Plan;
  type?: "plan";
  role: "assistant";
}

export type AnyAgentMessage =
  | AgentMessage
  | AgentEventMessage
  | ToolCallMessage
  | ToolResultMessage
  | VerificationMessage
  | PlanMessage;

// Legacy message format for backward compatibility
export interface LegacyChatMessage {
  role: string;
  content: string;
  id?: string;
  error?: boolean;
  // Additional fields from streaming
  event_type?: string;
  metadata?: AgentMessageMetadata;
}
