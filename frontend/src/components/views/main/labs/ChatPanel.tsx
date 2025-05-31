import React, { useState } from "react";
import { SendHorizontal, Loader2 } from "lucide-react";
import BlenderAPI, {
  ConnectionStatus as ConnectionStatusType,
} from "../../../utils/blenderapi"; // Import ConnectionStatusType

interface ChatPanelProps {
  connectionStatus: ConnectionStatusType; // Use the imported tri-state type
}

const ChatPanel: React.FC<ChatPanelProps> = ({ connectionStatus }) => {
  const [query, setQuery] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<
    Array<{ role: string; content: string; id?: string }>
  >([
    {
      role: "system",
      content:
        "Hello! I'm your Blender assistant. Try asking me to create objects like 'Add a red cube' or 'Create a blue sphere at position [1, 2, 0]'.",
    },
  ]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isProcessing || connectionStatus.status !== "success")
      return; // Check for 'success'

    // Add user message to chat
    const userMessage = { role: "user", content: query };
    setChatMessages((prev) => [...prev, userMessage]);

    // Clear input and set processing state
    setQuery("");
    setIsProcessing(true);

    try {
      // Add a temporary loading message
      const loadingId = Date.now().toString();
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Thinking...", id: loadingId },
      ]);

      // Process the query
      const response = await BlenderAPI.processChat(query);

      // Remove the loading message
      setChatMessages((prev) =>
        prev.filter((msg) => !msg.id || msg.id !== loadingId)
      );

      if (response.status === "success") {
        // Add all messages from the agent
        const assistantMessages = response.messages.map((msg: any) => ({
          role: "assistant",
          content: msg.content,
        }));

        setChatMessages((prev) => [
          ...prev.filter((msg) => !msg.id || msg.id !== loadingId),
          ...assistantMessages,
        ]);
      } else {
        // Add error message
        setChatMessages((prev) => [
          ...prev.filter((msg) => !msg.id || msg.id !== loadingId),
          {
            role: "assistant",
            content: `Error: ${response.error || "Failed to process query"}`,
          },
        ]);
      }
    } catch (error) {
      // Add error message
      setChatMessages((prev) => [
        ...prev.filter((msg) => !msg.id),
        { role: "assistant", content: `Error: ${error}` },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-secondary rounded-lg shadow-sm border border-primary/20 p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-primary">
          Chat with Blender
        </h2>
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
      <div className="mb-4 max-h-64 overflow-y-auto space-y-2 p-2 border rounded border-primary/20">
        {chatMessages.map((msg, index) => (
          <div
            key={index}
            className={`p-2 rounded ${
              msg.role === "user"
                ? "bg-accent/10 text-accent ml-8"
                : msg.role === "system"
                ? "bg-primary/5 text-primary/70 italic text-sm"
                : "bg-primary/10 text-primary mr-8"
            }`}
          >
            <div className="text-xs font-bold mb-1">
              {msg.role === "user"
                ? "You"
                : msg.role === "system"
                ? "System"
                : "Blender Assistant"}
            </div>
            <div>{msg.content}</div>
          </div>
        ))}
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
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
          className="flex-1 p-2 border rounded border-primary/30 bg-secondary text-primary focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <button
          type="submit"
          disabled={
            isProcessing ||
            connectionStatus.status !== "success" ||
            !query.trim() // Disable if not 'success'
          }
          className={`p-2 rounded text-secondary ${
            isProcessing ||
            connectionStatus.status !== "success" ||
            !query.trim()
              ? "bg-primary/40"
              : "bg-primary hover:bg-primary/80"
          }`}
        >
          {isProcessing ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <SendHorizontal className="h-5 w-5" />
          )}
        </button>
      </form>

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
              className="text-xs bg-secondary px-2 py-1 rounded hover:bg-primary/10 disabled:opacity-50 text-primary border border-primary/20"
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
