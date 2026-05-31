import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../../types";

interface ChatWindowProps {
  messages: ChatMessage[];
  loading: boolean;
}

const markdownStyles: Record<string, React.CSSProperties> = {
  p: { margin: "0.4em 0" },
  ul: { margin: "0.3em 0", paddingLeft: "1.4em" },
  ol: { margin: "0.3em 0", paddingLeft: "1.4em" },
  li: { margin: "0.1em 0" },
  blockquote: {
    margin: "0.4em 0",
    paddingLeft: "0.8em",
    borderLeft: "3px solid #bbb",
    color: "#555",
  },
  code: {
    background: "#e8e8e8",
    padding: "0.15em 0.35em",
    borderRadius: 4,
    fontSize: "0.88em",
    fontFamily: "Consolas, Monaco, monospace",
  },
  pre: {
    background: "#2d2d2d",
    color: "#f8f8f2",
    padding: "0.8em",
    borderRadius: 6,
    overflowX: "auto",
    fontSize: "0.85em",
  },
  h1: { margin: "0.6em 0 0.2em", fontSize: "1.3em", fontWeight: 700 },
  h2: { margin: "0.6em 0 0.2em", fontSize: "1.15em", fontWeight: 700 },
  h3: { margin: "0.5em 0 0.2em", fontSize: "1.05em", fontWeight: 700 },
  h4: { margin: "0.4em 0 0.1em", fontSize: "1em", fontWeight: 700 },
  strong: { fontWeight: 700 },
  em: { fontStyle: "italic" },
  hr: { margin: "0.6em 0", border: "none", borderTop: "1px solid #ddd" },
  table: { borderCollapse: "collapse", margin: "0.4em 0", fontSize: "0.9em" },
  th: {
    border: "1px solid #ccc",
    padding: "0.3em 0.6em",
    background: "#f5f5f5",
    fontWeight: 700,
  },
  td: { border: "1px solid #ccc", padding: "0.3em 0.6em" },
};

function MarkdownContent({ content }: { content: string }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p style={markdownStyles.p}>{children}</p>,
        ul: ({ children }) => <ul style={markdownStyles.ul}>{children}</ul>,
        ol: ({ children }) => <ol style={markdownStyles.ol}>{children}</ol>,
        li: ({ children }) => <li style={markdownStyles.li}>{children}</li>,
        blockquote: ({ children }) => (
          <blockquote style={markdownStyles.blockquote}>{children}</blockquote>
        ),
        code: ({ children, className }) => {
          const isInline = !className;
          if (isInline) {
            return <code style={markdownStyles.code}>{children}</code>;
          }
          return (
            <pre style={markdownStyles.pre}>
              <code className={className}>{children}</code>
            </pre>
          );
        },
        h1: ({ children }) => <h1 style={markdownStyles.h1}>{children}</h1>,
        h2: ({ children }) => <h2 style={markdownStyles.h2}>{children}</h2>,
        h3: ({ children }) => <h3 style={markdownStyles.h3}>{children}</h3>,
        h4: ({ children }) => <h4 style={markdownStyles.h4}>{children}</h4>,
        strong: ({ children }) => (
          <strong style={markdownStyles.strong}>{children}</strong>
        ),
        em: ({ children }) => <em style={markdownStyles.em}>{children}</em>,
        hr: () => <hr style={markdownStyles.hr} />,
        table: ({ children }) => (
          <table style={markdownStyles.table}>{children}</table>
        ),
        th: ({ children }) => <th style={markdownStyles.th}>{children}</th>,
        td: ({ children }) => <td style={markdownStyles.td}>{children}</td>,
      }}
    >
      {content}
    </Markdown>
  );
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
            lineHeight: 1.6,
          }}
        >
          {msg.role === "user" ? (
            <div>{msg.text}</div>
          ) : (
            <MarkdownContent content={msg.text} />
          )}

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
