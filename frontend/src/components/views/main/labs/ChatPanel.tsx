import React, { useState, useRef, useEffect } from "react";
import {
  SendHorizontal,
  Loader2,
  User,
  Bot,
  AlertCircle,
  Square,
  Inbox,
} from "lucide-react";
import BlenderAPI, { ConnectionStatus } from "../../../utils/blenderapi";
import MessageRenderer from "../../../utils/MessageRenderer";
import {
  LegacyChatMessage,
  AnyAgentMessage,
  PlanMessage,
} from "../../../types/AgentMessages";

interface ChatPanelProps {
  connectionStatus: ConnectionStatus;
  refreshViewport: () => Promise<void>;
}

const ChatPanel: React.FC<ChatPanelProps> = ({
  connectionStatus,
  refreshViewport,
}) => {
  const [query, setQuery] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<
    Array<LegacyChatMessage | AnyAgentMessage>
  >([]);
  const [fileList, setFileList] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Plan progress tracking
  const [currentPlan, setCurrentPlan] = useState<PlanMessage | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [totalSteps, setTotalSteps] = useState<number>(0);
  const [planCompleted, setPlanCompleted] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Smooth scroll to bottom on new message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter((file) =>
        file.type.startsWith("image/")
      );
      setFileList((prev) => [...prev, ...files]);
    }
  };

  const handleRemoveFile = (index: number) => {
    setFileList((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter((file) =>
      file.type.startsWith("image/")
    );
    setFileList((prev) => [...prev, ...files]);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleDragOverInput = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeaveInput = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDropInput = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter((file) =>
      file.type.startsWith("image/")
    );
    setFileList((prev) => [...prev, ...files]);
  };

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        resolve(result.split(",")[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      (!query.trim() && fileList.length === 0) ||
      isProcessing ||
      connectionStatus.status !== "success"
    )
      return;

    const content: any[] = [];
    if (query.trim()) content.push(query.trim());

    for (const file of fileList) {
      const b64 = await fileToBase64(file);
      content.push({
        type: "image",
        b64,
        format: file.type.split("/")[1]?.toUpperCase() || "PNG",
      });
    }

    const userMessage = { role: "user", content: query };
    setChatMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setFileList([]);
    setIsProcessing(true);

    // Reset plan progress when starting a new task
    setCurrentPlan(null);
    setCurrentStep(0);
    setTotalSteps(0);

    // Auto-focus input after sending
    setTimeout(() => inputRef.current?.focus(), 100);

    // List of tools that modify the scene and should trigger viewport refresh
    const sceneModifyingTools = [
      "execute_code",
      "create_object",
      "create_blender_object",
      "modify_object",
      "delete_object",
      "delete_blender_object",
      "clear_blender_scene",
      "add_blender_camera",
      "set_material",
      "set_blender_material",
    ];

    // Start WebSocket streaming
    const { ws, sendCancel } = BlenderAPI.streamChatWS(
      content,
      (data) => {
        console.log("Received WebSocket message:", {
          type: data.type,
          event_type: data.event_type,
          finish_reason: data.metadata?.finish_reason,
          content: data.content?.substring(0, 100) + "...",
        });

        // Backend now sends structured messages directly, no transformation needed
        setChatMessages((prev) => [...prev, data]);

        // Track plan progress
        if (data.type === "plan") {
          const planMsg = data as PlanMessage;
          setCurrentPlan(planMsg);
          setTotalSteps(planMsg.plan.steps.length);
          setCurrentStep(0);
          setPlanCompleted(false);
        }

        // Update current step based on metadata
        if (
          data.metadata?.step_index !== undefined &&
          data.metadata?.total_steps !== undefined
        ) {
          setCurrentStep(data.metadata.step_index);
          setTotalSteps(data.metadata.total_steps);
        }

        // Update progress when steps complete
        if (
          data.event_type === "step_completed" &&
          data.metadata?.step_index !== undefined
        ) {
          // When a step completes, increment currentStep to show progress
          setCurrentStep(data.metadata.step_index + 1);
        }

        // Mark plan as completed when we receive the final completion message
        if (
          data.metadata?.finish_reason === "completed" ||
          data.metadata?.finish_reason === "partial"
        ) {
          setPlanCompleted(true);
        }

        // Refresh viewport after successful tool results for scene-modifying tools
        if (
          data.type === "tool_result" &&
          data.tool_result?.success &&
          sceneModifyingTools.includes(data.tool_result.tool_name)
        ) {
          console.log(
            `Refreshing viewport after successful ${data.tool_result.tool_name} execution`
          );
          if (refreshViewport) refreshViewport();
        }

        if (
          data.event_type === "error" ||
          data.event_type === "max_steps_exceeded" ||
          data.event_type === "cancelled" ||
          (data.metadata?.finish_reason === "stop" && data.type !== "plan") ||
          data.metadata?.finish_reason === "error" ||
          data.metadata?.finish_reason === "cancelled" ||
          data.metadata?.finish_reason === "completed" ||
          data.metadata?.finish_reason === "partial"
        ) {
          setIsProcessing(false);
          ws.close();
          console.log(
            "WebSocket closed due to:",
            data.event_type || data.metadata?.finish_reason
          );
          // Reset plan progress when done
          setCurrentPlan(null);
          setCurrentStep(0);
          setTotalSteps(0);
          setPlanCompleted(false);
          if (refreshViewport) refreshViewport();
        }
      },
      (err) => {
        console.error("Streaming error:", err);
        setChatMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${err}`,
            error: true,
          } as LegacyChatMessage,
        ]);
        setIsProcessing(false);
        ws.close();
        if (refreshViewport) refreshViewport();
      }
    );
    wsRef.current = ws;
  };

  // Optional: Cancel button handler
  const handleCancel = () => {
    if (wsRef.current && wsRef.current.readyState === 1) {
      wsRef.current.send(JSON.stringify({ type: "cancel" }));
    }
    setIsProcessing(false);
    // Reset plan progress when cancelled
    setCurrentPlan(null);
    setCurrentStep(0);
    setTotalSteps(0);
    setPlanCompleted(false);
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    if (isProcessing || connectionStatus.status !== "success") return;
    const items = e.clipboardData.items;
    const files: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === "file" && item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length > 0) {
      setFileList((prev) => [...prev, ...files]);
      e.preventDefault();
    }
  };

  return (
    <div className=" rounded-lg ">
      {/* Chat messages */}
      <div className="mb-4 max-h-96 overflow-y-auto space-y-3 p-3 border rounded border-primary/20">
        {chatMessages.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-center">
            <div className="text-secondary/70">
              <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Enter a task or select a task preset</p>
            </div>
          </div>
        ) : (
          chatMessages.map((msg, index) => (
            <MessageRenderer key={index} message={msg} index={index} />
          ))
        )}

        {/* Streaming indicator */}
        {isProcessing && (
          <div className="flex items-start gap-3 justify-end">
            <div className="max-w-[70%] px-4 py-3 rounded-2xl rounded-br-md bg-gray-100 border border-gray-200">
              <div className="flex items-center gap-2 mb-1">
                <Bot className="w-4 h-4 text-gray-600" />
                <span className="text-xs font-medium opacity-75">
                  Blender Assistant
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-sm text-gray-600">
                  {totalSteps > 0
                    ? `Processing... (step ${currentStep + 1}/${totalSteps})`
                    : "Processing..."}
                </span>
              </div>
            </div>
            <div className="flex-shrink-0 w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center">
              <Bot className="w-4 h-4 text-primary" />
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
      {/* Input form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <div
          className="relative"
          onDrop={handleDropInput}
          onDragOver={handleDragOverInput}
          onDragLeave={handleDragLeaveInput}
        >
          {isDragging && (
            <div className="absolute inset-0 z-10 bg-accent/10 border-2 border-accent flex flex-col items-center justify-center rounded-lg pointer-events-none">
              <Inbox className="w-8 h-8 text-accent mb-2" />
              <span className="text-primary font-medium">
                Drop images to attach
              </span>
            </div>
          )}
          <div className="flex gap-2 items-center bg-secondary/30 rounded-lg p-2 border border-primary/30">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded hover:bg-secondary/60 transition"
              title="Attach image"
              tabIndex={-1}
            >
              <Inbox className="w-5 h-5 text-accent" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onPaste={handlePaste}
              disabled={isProcessing || connectionStatus.status !== "success"}
              placeholder={
                connectionStatus.status === "fetching"
                  ? "Connecting to Blender..."
                  : connectionStatus.status === "failed"
                  ? "Connect to Blender to chat"
                  : isProcessing
                  ? "Processing..."
                  : "Ask me to create or modify objects..."
              }
              className="flex-1 p-3 border-none bg-transparent text-primary focus:outline-none"
            />
            {isProcessing ? (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="p-3 rounded-lg bg-red-500 hover:bg-red-600 text-white transition-all"
                >
                  <Square className="h-5 w-5" />
                </button>
                <div className="p-3 rounded-lg bg-gray-400 text-white flex items-center">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              </div>
            ) : (
              <button
                type="submit"
                disabled={
                  connectionStatus.status !== "success" ||
                  (!query.trim() && fileList.length === 0)
                }
                className={`p-3 rounded-lg text-white transition-all ${
                  connectionStatus.status !== "success" ||
                  (!query.trim() && fileList.length === 0)
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-accent hover:bg-accent/90 hover:scale-105"
                }`}
              >
                <SendHorizontal className="h-5 w-5" />
              </button>
            )}
          </div>
          {/* Show attached images as thumbnails with remove icon */}
          {fileList.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {fileList.map((file, idx) => (
                <div key={idx} className="relative group">
                  <img
                    src={URL.createObjectURL(file)}
                    alt={file.name}
                    className="w-10 h-10 object-cover rounded border border-primary/20"
                  />
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveFile(idx);
                    }}
                    className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-1 opacity-80 hover:opacity-100"
                    title="Remove"
                  >
                    <Square className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </form>
      {/* Examples */}
      <div className="mt-4">
        <p className="text-xs text-secondary mb-1">Try asking:</p>
        <div className="flex flex-wrap gap-2">
          {[
            "Create a simple donut with icing",
            "create a low poly well with two trees",
            "Add a red cube",
            "Create a blue sphere",
            "Add a green cone at [2, 0, 0]",
            "Clear the scene",
          ].map((example, index) => (
            <button
              key={index}
              onClick={() => setQuery(example)}
              disabled={isProcessing || connectionStatus.status !== "success"} // Disable if not 'success'
              className="text-xs bg-secondary px-3 py-2 rounded hover:bg-accent/10 hover:text-accent disabled:opacity-50 text-primary border border-primary/20 transition-all"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
