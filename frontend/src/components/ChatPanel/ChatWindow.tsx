import type { ChatMessage } from "../../types";

interface ChatWindowProps {
  messages: ChatMessage[];
  loading: boolean;
}

export function ChatWindow({ messages, loading }: ChatWindowProps) {
  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "1rem",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {messages.length === 0 && !loading && (
        <div style={{ textAlign: "center", color: "#999", marginTop: "3rem" }}>
          <p style={{ fontSize: "2rem" }}>🎤</p>
          <p>Upload a document, then ask a question — by voice or text.</p>
        </div>
      )}

      {messages.map((msg, i) => (
        <div
          key={i}
          style={{
            alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "75%",
            padding: "0.7rem 1rem",
            borderRadius: 12,
            background: msg.role === "user" ? "#4a90d9" : "#f0f0f0",
            color: msg.role === "user" ? "#fff" : "#333",
            fontSize: "0.95rem",
            lineHeight: 1.5,
          }}
        >
          <div>{msg.text}</div>

          {msg.audioBase64 && (
            <audio
              controls
              src={`data:audio/mp3;base64,${msg.audioBase64}`}
              style={{ marginTop: 8, width: "100%" }}
            />
          )}

          {msg.sources && msg.sources.length > 0 && (
            <details style={{ marginTop: 8, fontSize: "0.8rem" }}>
              <summary style={{ cursor: "pointer", opacity: 0.7 }}>
                Sources ({msg.sources.length})
              </summary>
              {msg.sources.map((s, j) => (
                <div key={j} style={{ marginTop: 4 }}>
                  [{s.document_name}] score: {s.relevance_score.toFixed(3)} — "
                  {s.content.slice(0, 120)}..."
                </div>
              ))}
            </details>
          )}
        </div>
      ))}

      {loading && (
        <div style={{ alignSelf: "flex-start", color: "#999", fontStyle: "italic" }}>
          VoiceLearn is thinking...
        </div>
      )}
    </div>
  );
}
