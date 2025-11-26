import { useRef, useEffect } from "react";
import type { ChatMessage } from "../types";
import CodeBlock from "./CodeBlock";
import "./MessageList.css";

interface DisplayMessage extends ChatMessage {
  id: string;
  codeGenerated?: string | null;
  rawData?: Record<string, unknown> | null;
  isLoading?: boolean;
}

interface MessageListProps {
  messages: DisplayMessage[];
}

export default function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list empty">
        <div className="empty-state">
          <span className="empty-icon">🏈</span>
          <h2>Welcome to Deep Shot!</h2>
          <p>Ask me anything about NFL statistics. Try:</p>
          <ul className="example-queries">
            <li>"Who led the league in passing yards in 2023?"</li>
            <li>"Show me Patrick Mahomes' stats this season"</li>
            <li>"Compare rushing yards between Derrick Henry and Josh Jacobs"</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <div key={message.id} className={`message ${message.role}`}>
          <div className="message-avatar">{message.role === "user" ? "👤" : "🏈"}</div>
          <div className="message-content">
            {message.isLoading ? (
              <div className="loading-indicator">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            ) : (
              <>
                <p className="message-text">{message.content}</p>
                {message.codeGenerated && (
                  <CodeBlock code={message.codeGenerated} language="python" title="Generated Code" />
                )}
                {message.rawData && Object.keys(message.rawData).length > 0 && (
                  <CodeBlock
                    code={JSON.stringify(message.rawData, null, 2)}
                    language="json"
                    title="Raw Data"
                    collapsible
                    defaultCollapsed
                  />
                )}
              </>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
