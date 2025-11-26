import { useState } from "react";
import "./CodeBlock.css";

interface CodeBlockProps {
  code: string;
  language: string;
  title?: string;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
}

export default function CodeBlock({
  code,
  language,
  title,
  collapsible = false,
  defaultCollapsed = false
}: CodeBlockProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block">
      <div className="code-header">
        <div className="code-title">
          {collapsible && (
            <button className="collapse-toggle" onClick={() => setIsCollapsed(!isCollapsed)}>
              {isCollapsed ? "▶" : "▼"}
            </button>
          )}
          <span className="language-badge">{language}</span>
          {title && <span className="title-text">{title}</span>}
        </div>
        <button className="copy-button" onClick={handleCopy}>
          {copied ? "✓ Copied!" : "Copy"}
        </button>
      </div>
      {!isCollapsed && (
        <pre className="code-content">
          <code>{code}</code>
        </pre>
      )}
    </div>
  );
}
