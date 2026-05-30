export function SettingsPage() {
  return (
    <div style={{ padding: "2rem", height: "100%", overflowY: "auto" }}>
      <h2>Settings</h2>
      <p style={{ color: "#666" }}>
        LLM provider, embedding model, and chunking parameters can be configured here.
      </p>
      <p style={{ color: "#999", fontStyle: "italic" }}>
        Settings UI coming soon. For now, edit <code>backend/.env</code> directly.
      </p>
    </div>
  );
}
