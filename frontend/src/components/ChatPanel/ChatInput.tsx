import { useState } from "react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div style={{ display: "flex", gap: 8, padding: "1rem", borderTop: "1px solid #ddd" }}>
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder="Type your question or click the mic..."
        disabled={disabled}
        style={{
          flex: 1,
          padding: "0.6rem 0.8rem",
          borderRadius: 8,
          border: "1px solid #ccc",
          fontSize: "0.95rem",
        }}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
        style={{
          padding: "0.6rem 1.2rem",
          borderRadius: 8,
          border: "none",
          background: disabled ? "#ccc" : "#4a90d9",
          color: "#fff",
          cursor: disabled ? "default" : "pointer",
          fontSize: "0.95rem",
        }}
      >
        Send
      </button>
    </div>
  );
}
