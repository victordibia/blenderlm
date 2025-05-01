import React, { useState } from "react";
import { SendHorizontal, Loader2 } from "lucide-react";
import BlenderAPI from "../../../utils/blenderapi";

interface ChatPanelProps {
  connectionStatus: {
    connected: boolean;
    error?: string;
  };
}

const ChatPanel: React.FC<ChatPanelProps> = ({ connectionStatus }) => {
  const [query, setQuery] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<
    Array<{ role: string; content: string }>
  >([
    {
      role: "system",
      content:
        "Hello! I'm your Blender assistant. Try asking me to create objects like 'Add a red cube' or 'Create a blue sphere at position [1, 2, 0]'.",
    },
  ]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isProcessing || !connectionStatus.connected) return;

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
      setChatMessages((prev) => prev.filter((msg) => msg.id !== loadingId));

      if (response.status === "success") {
        // Add all messages from the agent
        const assistantMessages = response.messages.map((msg: any) => ({
          role: "assistant",
          content: msg.content,
        }));

        setChatMessages((prev) => [
          ...prev.filter((msg) => msg.id !== loadingId),
          ...assistantMessages,
        ]);
      } else {
        // Add error message
        setChatMessages((prev) => [
          ...prev.filter((msg) => msg.id !== loadingId),
          {
            role: "assistant",
            content: `Error: ${response.error || "Failed to process query"}`,
          },
        ]);
      }
    } catch (error) {
      // Add error message
      setChatMessages((prev) => [
        ...prev.filter((msg) => !("id" in msg)),
        { role: "assistant", content: `Error: ${error}` },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold dark:text-white">
          Chat with Blender
        </h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {connectionStatus.connected ? (
            <span className="text-green-500">Connected to Blender</span>
          ) : (
            <span className="text-red-500">Not connected to Blender</span>
          )}
        </div>
      </div>

      {/* Chat messages */}
      <div className="mb-4 max-h-64 overflow-y-auto space-y-2 p-2 border rounded dark:border-gray-700">
        {chatMessages.map((msg, index) => (
          <div
            key={index}
            className={`p-2 rounded ${
              msg.role === "user"
                ? "bg-blue-100 dark:bg-blue-900 ml-8"
                : msg.role === "system"
                ? "bg-gray-100 dark:bg-gray-700 italic text-sm"
                : "bg-gray-100 dark:bg-gray-700 mr-8"
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
          disabled={isProcessing || !connectionStatus.connected}
          placeholder={
            !connectionStatus.connected
              ? "Connect to Blender to chat"
              : isProcessing
              ? "Processing..."
              : "Ask me to create or modify objects..."
          }
          className="flex-1 p-2 border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        />
        <button
          type="submit"
          disabled={
            isProcessing || !connectionStatus.connected || !query.trim()
          }
          className={`p-2 rounded text-white ${
            isProcessing || !connectionStatus.connected || !query.trim()
              ? "bg-gray-400"
              : "bg-blue-500 hover:bg-blue-600"
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
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
          Try asking:
        </p>
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
              disabled={isProcessing || !connectionStatus.connected}
              className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
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
