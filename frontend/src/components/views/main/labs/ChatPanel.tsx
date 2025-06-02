import React, { useState, useRef, useEffect } from "react";
import { SendHorizontal, Loader2, User, Bot, AlertCircle } from "lucide-react";
import BlenderAPI, { ConnectionStatus } from "../../../utils/blenderapi";

interface ChatPanelProps {
  connectionStatus: ConnectionStatus;
  onChatComplete?: () => void; // Optional callback prop
}

const ChatPanel: React.FC<ChatPanelProps> = ({
  connectionStatus,
  onChatComplete,
}) => {
  const [query, setQuery] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<
    Array<{ role: string; content: string; id?: string; error?: boolean }>
  >([]);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isProcessing || connectionStatus.status !== "success")
      return;

    const userMessage = { role: "user", content: query };
    setChatMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setIsProcessing(true);

    // Auto-focus input after sending
    setTimeout(() => inputRef.current?.focus(), 100);

    // Start WebSocket streaming
    const { ws, sendCancel } = BlenderAPI.streamChatWS(
      query,
      (data) => {
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.content },
        ]);
        if (
          data.event_type === "error" ||
          data.metadata?.finish_reason === "stop" ||
          data.metadata?.finish_reason === "error"
        ) {
          setIsProcessing(false);
          ws.close();
          if (onChatComplete) onChatComplete();
        }
      },
      (err) => {
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${err}`, error: true },
        ]);
        setIsProcessing(false);
        ws.close();
        if (onChatComplete) onChatComplete();
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
  };

  return (
    <div className="  rounded-lg shadow-sm border border-primary/20 p-4">
      <div className="flex justify-between items-center mb-4">
        <div className="text-sm text-secondary">
          {connectionStatus.status === "fetching" && (
            <span className="text-blue-500">Connecting...</span>
          )}
          {connectionStatus.status === "success" && (
            <span className="text-accent">Connected to Blender</span>
          )}
          {connectionStatus.status === "failed" && (
            <span className="text-primary/70">Not connected to Blender</span>
          )}
        </div>
      </div>

      {/* Chat messages */}
      <div className="mb-4 max-h-64 overflow-y-auto space-y-3 p-3 border rounded border-primary/20 bg-white/50 dark:bg-black/20">
        {chatMessages.map((msg, index) => (
          <div
            key={index}
            className={`flex items-start gap-3 ${
              msg.role === "user" ? "justify-start" : "justify-end"
            }`}
          >
            {msg.role === "user" && (
              <div className="flex-shrink-0 w-8 h-8 bg-accent/20 rounded-full flex items-center justify-center">
                <User className="w-4 h-4 text-accent" />
              </div>
            )}

            <div
              className={`max-w-[70%] px-4 py-3 rounded-2xl text-sm ${
                msg.role === "user"
                  ? "bg-accent text-white rounded-bl-md"
                  : msg.error
                  ? "bg-red-100 text-red-700 border border-red-300 rounded-br-md"
                  : "bg-gray-100 text-gray-800 border border-gray-200 rounded-br-md"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                {msg.role === "assistant" && msg.error && (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                )}
                {msg.role === "assistant" && !msg.error && (
                  <Bot className="w-4 h-4 text-gray-600" />
                )}
                <span className="text-xs font-medium opacity-75">
                  {msg.role === "user"
                    ? "You"
                    : msg.error
                    ? "Error"
                    : "Blender Assistant"}
                </span>
              </div>
              <div className="whitespace-pre-line">{msg.content}</div>
            </div>

            {msg.role === "assistant" && !msg.error && (
              <div className="flex-shrink-0 w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary" />
              </div>
            )}
            {msg.role === "assistant" && msg.error && (
              <div className="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                <AlertCircle className="w-4 h-4 text-red-500" />
              </div>
            )}
          </div>
        ))}

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
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                ></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                ></div>
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
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={isProcessing || connectionStatus.status !== "success"} // Disable if not 'success'
          placeholder={
            connectionStatus.status === "fetching"
              ? "Connecting to Blender..."
              : connectionStatus.status === "failed"
              ? "Connect to Blender to chat"
              : isProcessing
              ? "Processing..."
              : "Ask me to create or modify objects..."
          }
          className="flex-1 p-3 border rounded-lg border-primary/30 bg-secondary text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-all"
        />
        <button
          type="submit"
          disabled={
            isProcessing ||
            connectionStatus.status !== "success" ||
            !query.trim() // Disable if not 'success'
          }
          className={`p-3 rounded-lg text-white transition-all ${
            isProcessing ||
            connectionStatus.status !== "success" ||
            !query.trim()
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-accent hover:bg-accent/90 hover:scale-105"
          }`}
        >
          {isProcessing ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <SendHorizontal className="h-5 w-5" />
          )}
        </button>
      </form>

      {/* Cancel button (optional) */}
      {isProcessing && (
        <div className="mt-2">
          <button
            onClick={handleCancel}
            disabled={!isProcessing}
            className="w-full p-3 rounded-lg bg-red-500 hover:bg-red-600 text-white transition-all disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Examples */}
      <div className="mt-4">
        <p className="text-xs text-secondary mb-1">Try asking:</p>
        <div className="flex flex-wrap gap-2">
          {[
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
