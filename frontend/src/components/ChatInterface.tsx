import { useState, useCallback } from "react";
import type { ChatMessage, NFLResponse } from "../types";
import { chatNFL } from "../services/api";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";
import "./ChatInterface.css";

interface DisplayMessage extends ChatMessage {
  id: string;
  codeGenerated?: string | null;
  rawData?: Record<string, unknown> | null;
  isLoading?: boolean;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      const userMessage: DisplayMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim()
      };

      // Add user message and loading placeholder
      const loadingMessage: DisplayMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        isLoading: true
      };

      setMessages((prev) => [...prev, userMessage, loadingMessage]);
      setIsLoading(true);
      setError(null);

      try {
        // Build conversation history for API
        const conversationHistory: ChatMessage[] = [
          ...messages.map(({ role, content }) => ({ role, content })),
          { role: "user" as const, content: content.trim() }
        ];

        const response: NFLResponse = await chatNFL({ messages: conversationHistory });

        // Replace loading message with actual response
        const assistantMessage: DisplayMessage = {
          id: loadingMessage.id,
          role: "assistant",
          content: response.response,
          codeGenerated: response.code_generated,
          rawData: response.raw_data
        };

        setMessages((prev) => prev.map((msg) => (msg.id === loadingMessage.id ? assistantMessage : msg)));
      } catch (err) {
        // Remove loading message on error
        setMessages((prev) => prev.filter((msg) => msg.id !== loadingMessage.id));
        setError(err instanceof Error ? err.message : "An unexpected error occurred");
      } finally {
        setIsLoading(false);
      }
    },
    [messages, isLoading]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return (
    <div className="chat-interface">
      <header className="chat-header">
        <h1>🏈 Deep Shot</h1>
        <p>Ask me anything about NFL statistics</p>
        {messages.length > 0 && (
          <button className="clear-button" onClick={clearChat} disabled={isLoading}>
            Clear Chat
          </button>
        )}
      </header>

      <MessageList messages={messages} />

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <MessageInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
