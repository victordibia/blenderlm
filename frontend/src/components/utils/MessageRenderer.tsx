import React from "react";
import {
  User,
  Bot,
  AlertCircle,
  Wrench,
  CheckCircle,
  XCircle,
  Info,
  Clock,
  Zap,
  ArrowRight,
  Terminal,
  Eye,
  ListChecks,
} from "lucide-react";
import {
  AnyAgentMessage,
  LegacyChatMessage,
  ToolCallMessage,
  ToolResultMessage,
  VerificationMessage,
  AgentEventMessage,
  PlanMessage,
} from "../types/AgentMessages";

interface MessageRendererProps {
  message: AnyAgentMessage | LegacyChatMessage;
  index: number;
}

// Helper function to format JSON arguments nicely
const formatArguments = (args: Record<string, any>): string => {
  return Object.entries(args)
    .map(([key, value]) => {
      if (typeof value === "string" && value.length > 50) {
        return `${key}: "${value.substring(0, 50)}..."`;
      }
      if (typeof value === "object") {
        return `${key}: ${JSON.stringify(value)}`;
      }
      return `${key}: ${value}`;
    })
    .join(", ");
};

// Helper function to determine if message is legacy format
const isLegacyMessage = (message: any): message is LegacyChatMessage => {
  return "role" in message && "content" in message && !("type" in message);
};

// Helper function to get message icon
const getMessageIcon = (message: AnyAgentMessage | LegacyChatMessage) => {
  if (isLegacyMessage(message)) {
    if (message.role === "user")
      return <User className="w-4 h-4 text-accent" />;
    if (message.error) return <AlertCircle className="w-4 h-4 text-red-500" />;
    return <Bot className="w-4 h-4 text-gray-600" />;
  }

  switch (message.type) {
    case "tool_call":
      return <Wrench className="w-4 h-4 text-blue-600" />;
    case "tool_result":
      const toolMsg = message as ToolResultMessage;
      return toolMsg.tool_result.success ? (
        <CheckCircle className="w-4 h-4 text-green-600" />
      ) : (
        <XCircle className="w-4 h-4 text-red-600" />
      );
    case "verification":
      const verifyMsg = message as VerificationMessage;
      return verifyMsg.verification.status ? (
        <CheckCircle className="w-4 h-4 text-green-600" />
      ) : (
        <Eye className="w-4 h-4 text-orange-600" />
      );
    case "plan":
      return <ListChecks className="w-4 h-4 text-indigo-600" />;
    case "event":
      return <Info className="w-4 h-4 text-purple-600" />;
    case "llm":
    default:
      if (message.role === "user")
        return <User className="w-4 h-4 text-accent" />;
      return <Bot className="w-4 h-4 text-gray-600" />;
  }
};

// Helper function to get message title
const getMessageTitle = (message: AnyAgentMessage | LegacyChatMessage) => {
  if (isLegacyMessage(message)) {
    if (message.role === "user") return "You";
    if (message.error) return "Error";
    return "Blender Assistant";
  }

  switch (message.type) {
    case "tool_call":
      const toolCallMsg = message as ToolCallMessage;
      return `Tool Call: ${toolCallMsg.tool_call.name}`;
    case "tool_result":
      const toolResultMsg = message as ToolResultMessage;
      return `Tool Result: ${toolResultMsg.tool_result.tool_name}`;
    case "verification":
      return "Task Verification";
    case "plan":
      return "Execution Plan";
    case "event":
      const eventMsg = message as AgentEventMessage;
      return eventMsg.event_type
        ? `Event: ${eventMsg.event_type}`
        : "System Event";
    case "llm":
    default:
      if (message.role === "user") return "You";
      return "Blender Assistant";
  }
};

// Helper function to get message styling
const getMessageStyling = (message: AnyAgentMessage | LegacyChatMessage) => {
  if (isLegacyMessage(message)) {
    if (message.role === "user") {
      return {
        container: "justify-start",
        bubble: "bg-accent text-white rounded-bl-md",
        showAvatar: true,
        avatarSide: "left",
      };
    }
    if (message.error) {
      return {
        container: "justify-end",
        bubble: "bg-red-100 text-red-700 border border-red-300 rounded-br-md",
        showAvatar: false,
        avatarSide: "right",
      };
    }
    return {
      container: "justify-end",
      bubble: "bg-gray-100 text-gray-800 border border-gray-200 rounded-br-md",
      showAvatar: false,
      avatarSide: "right",
    };
  }

  if (message.role === "user") {
    return {
      container: "justify-start",
      bubble: "bg-accent text-white rounded-bl-md",
      showAvatar: true,
      avatarSide: "left",
    };
  }

  // Assistant messages with different types
  switch (message.type) {
    case "tool_call":
      return {
        container: "justify-end",
        bubble: "bg-blue-50 text-blue-800 border border-blue-200 rounded-br-md",
        showAvatar: false,
        avatarSide: "right",
      };
    case "tool_result":
      const toolResultMsg = message as ToolResultMessage;
      return {
        container: "justify-end",
        bubble: toolResultMsg.tool_result.success
          ? "bg-green-50 text-green-800 border border-green-200 rounded-br-md"
          : "bg-red-50 text-red-800 border border-red-200 rounded-br-md",
        showAvatar: false,
        avatarSide: "right",
      };
    case "verification":
      const verifyMsg = message as VerificationMessage;
      return {
        container: "justify-end",
        bubble: verifyMsg.verification.status
          ? "bg-green-50 text-green-800 border border-green-200 rounded-br-md"
          : "bg-orange-50 text-orange-800 border border-orange-200 rounded-br-md",
        showAvatar: false,
        avatarSide: "right",
      };
    case "plan":
      return {
        container: "justify-end",
        bubble:
          "bg-indigo-50 text-indigo-800 border border-indigo-200 rounded-br-md",
        showAvatar: false,
        avatarSide: "right",
      };
    case "event":
      return {
        container: "justify-end",
        bubble:
          "bg-purple-50 text-purple-800 border border-purple-200 rounded-br-md",
        showAvatar: false,
        avatarSide: "right",
      };
    default:
      return {
        container: "justify-end",
        bubble:
          "bg-gray-100 text-gray-800 border border-gray-200 rounded-br-md",
        showAvatar: false,
        avatarSide: "right",
      };
  }
};

// Main message content renderer
const MessageContentRenderer: React.FC<{
  message: AnyAgentMessage | LegacyChatMessage;
}> = ({ message }) => {
  if (isLegacyMessage(message)) {
    return (
      <div className="whitespace-pre-line break-words overflow-wrap-anywhere">
        {message.content}
      </div>
    );
  }

  switch (message.type) {
    case "tool_call":
      const toolCallMsg = message as ToolCallMessage;
      return (
        <div className="space-y-2">
          <div className="bg-white/50 p-2 rounded text-xs font-mono">
            {formatArguments(toolCallMsg.tool_call.arguments)}
          </div>
        </div>
      );

    case "tool_result":
      const toolResultMsg = message as ToolResultMessage;
      return (
        <div className="space-y-2">
          <div className="bg-white/50 p-2 rounded text-sm">
            {toolResultMsg.tool_result.result.length > 200
              ? `${toolResultMsg.tool_result.result.substring(0, 200)}...`
              : toolResultMsg.tool_result.result}
          </div>
          {!toolResultMsg.tool_result.success &&
            toolResultMsg.tool_result.error && (
              <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                Error: {toolResultMsg.tool_result.error}
              </div>
            )}
        </div>
      );

    case "verification":
      const verifyMsg = message as VerificationMessage;
      return (
        <div className="space-y-2">
          <div className="text-sm">{verifyMsg.verification.reason}</div>
          {!verifyMsg.verification.status &&
            verifyMsg.verification.next_step && (
              <div className="flex items-center gap-2 text-sm bg-white/50 p-2 rounded">
                <ArrowRight className="w-3 h-3" />
                <span>Next: {verifyMsg.verification.next_step}</span>
              </div>
            )}
          {verifyMsg.verification.confidence && (
            <div className="text-xs opacity-70">
              Confidence: {(verifyMsg.verification.confidence * 100).toFixed(1)}
              %
            </div>
          )}
          {message.content && (
            <div className="text-sm opacity-80">{message.content}</div>
          )}
        </div>
      );

    case "event":
      const eventMsg = message as AgentEventMessage;
      return (
        <div>
          {message.content && (
            <div className="text-sm opacity-80">{message.content}</div>
          )}
        </div>
      );

    case "plan":
      const planMsg = message as PlanMessage;
      return (
        <div className="space-y-4">
          {/* Plan header with summary */}
          <div className="hidden bg-indigo-100/50 rounded-lg p-3 border border-indigo-200">
            <div className="flex items-center gap-2 text-sm font-medium text-indigo-900 mb-2">
              <ListChecks className="w-4 h-4" />
              <span>Execution Plan ({planMsg.plan.steps.length} steps)</span>
            </div>
            <div className="text-xs text-indigo-700">
              Sequential steps to complete the requested task
            </div>
          </div>

          {/* Plan steps - compact, single line, no left bar */}
          <div className="space-y-2">
            {planMsg.plan.steps.map((step, index) => (
              <div
                key={index}
                className="flex items-center gap-2 bg-white/70 rounded-lg p-2 border border-indigo-100 hover:bg-indigo-50/30 transition-colors"
              >
                <div className="w-6 h-6 bg-indigo-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                  {index + 1}
                </div>
                <div className="font-medium text-sm text-indigo-900 leading-relaxed">
                  {step.task}
                </div>
              </div>
            ))}
          </div>
        </div>
      );

    default:
      return (
        <div className="whitespace-pre-line break-words overflow-wrap-anywhere">
          {message.content || ""}
        </div>
      );
  }
};

const MessageRenderer: React.FC<MessageRendererProps> = ({
  message,
  index,
}) => {
  const styling = getMessageStyling(message);
  const icon = getMessageIcon(message);
  const title = getMessageTitle(message);

  // Determine max width based on message type
  const isPlanMessage = !isLegacyMessage(message) && message.type === "plan";
  const maxWidth = isPlanMessage ? "max-w-[85%]" : "max-w-[70%]";

  // Inline metadata for top right
  const metadata = !isLegacyMessage(message) ? message.metadata : undefined;

  return (
    <div className={`flex items-start gap-3 ${styling.container}`}>
      {styling.showAvatar && styling.avatarSide === "left" && (
        <div className="flex-shrink-0 w-8 h-8 bg-accent/20 rounded-full flex items-center justify-center">
          {icon}
        </div>
      )}

      <div
        className={`${maxWidth} px-4 py-3 rounded-2xl text-sm ${styling.bubble}`}
      >
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            {!styling.showAvatar && icon}
            <span className="text-xs font-medium opacity-75">{title}</span>
          </div>
          {metadata && (
            <div className="flex flex-wrap gap-3 text-xs opacity-60">
              {metadata.duration && (
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{metadata.duration.toFixed(2)}s</span>
                </div>
              )}
              {metadata.usage?.total_tokens && (
                <div className="flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  <span>{metadata.usage.total_tokens} tokens</span>
                </div>
              )}
              {metadata.finish_reason && (
                <div className="flex items-center gap-1">
                  <Terminal className="w-3 h-3" />
                  <span>{metadata.finish_reason}</span>
                </div>
              )}
            </div>
          )}
        </div>

        <MessageContentRenderer message={message} />
      </div>

      {styling.showAvatar && styling.avatarSide === "right" && (
        <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
          <Bot className="w-4 h-4 text-gray-600" />
        </div>
      )}
    </div>
  );
};

export default MessageRenderer;
