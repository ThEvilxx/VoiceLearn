import { useCallback, useEffect, useState } from "react";

interface LLMConfig {
  provider: string;
  openai_model: string;
  openai_api_key: string;
  openai_base_url: string;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json() as Promise<T>;
}

export function SettingsPage() {
  const [config, setConfig] = useState<LLMConfig>({
    provider: "openai",
    openai_model: "",
    openai_api_key: "",
    openai_base_url: "",
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await request<LLMConfig>("/api/settings/llm");
      setConfig({
        provider: data.provider || "openai",
        openai_model: data.openai_model || "",
        openai_api_key: "",
        openai_base_url: "",
      });
    } catch {
      setMsg({ type: "error", text: "Failed to load settings" });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    setMsg(null);
    try {
      const body: Record<string, string> = { provider: config.provider };
      if (config.openai_api_key) body.openai_api_key = config.openai_api_key;
      if (config.openai_model) body.openai_model = config.openai_model;
      if (config.openai_base_url) body.openai_base_url = config.openai_base_url;
      await request("/api/settings/llm", { method: "PUT", body: JSON.stringify(body) });
      setMsg({ type: "success", text: "Saved. Restart required for full effect." });
    } catch {
      setMsg({ type: "error", text: "Failed to save settings" });
    } finally {
      setSaving(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.5rem 0.7rem",
    borderRadius: 6,
    border: "1px solid #ccc",
    fontSize: "0.9rem",
    boxSizing: "border-box",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    marginBottom: 4,
    fontSize: "0.85rem",
    fontWeight: 600,
    color: "#444",
  };

  const fieldStyle: React.CSSProperties = { marginBottom: "1rem" };

  return (
    <div style={{ padding: "2rem", maxWidth: 560, height: "100%", overflowY: "auto" }}>
      <h2 style={{ margin: "0 0 0.3rem" }}>Settings</h2>
      <p style={{ color: "#666", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
        Configure the LLM provider and credentials. Changes take effect after restart.
      </p>

      <div
        style={{
          background: "#fff",
          border: "1px solid #e0e0e0",
          borderRadius: 10,
          padding: "1.2rem 1.5rem",
        }}
      >
        <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>LLM Provider</h3>

        <div style={fieldStyle}>
          <label style={labelStyle}>Provider</label>
          <select
            value={config.provider}
            onChange={(e) => setConfig((c) => ({ ...c, provider: e.target.value }))}
            style={inputStyle}
          >
            <option value="openai">OpenAI-compatible (DeepSeek)</option>
            <option value="claude">Claude (Anthropic)</option>
            <option value="ollama">Ollama (local)</option>
          </select>
        </div>

        {config.provider !== "ollama" && (
          <>
            <div style={fieldStyle}>
              <label style={labelStyle}>API Key</label>
              <input
                type="password"
                value={config.openai_api_key}
                onChange={(e) => setConfig((c) => ({ ...c, openai_api_key: e.target.value }))}
                placeholder="sk-... (leave empty to keep current)"
                style={inputStyle}
              />
            </div>

            <div style={fieldStyle}>
              <label style={labelStyle}>Model</label>
              <input
                type="text"
                value={config.openai_model}
                onChange={(e) => setConfig((c) => ({ ...c, openai_model: e.target.value }))}
                placeholder={config.provider === "openai" ? "deepseek-v4-pro" : "claude-sonnet-4-6"}
                style={inputStyle}
              />
            </div>

            <div style={fieldStyle}>
              <label style={labelStyle}>Base URL</label>
              <input
                type="text"
                value={config.openai_base_url}
                onChange={(e) => setConfig((c) => ({ ...c, openai_base_url: e.target.value }))}
                placeholder={config.provider === "openai" ? "https://api.deepseek.com/v1" : ""}
                style={inputStyle}
              />
            </div>
          </>
        )}

        {msg && (
          <p
            style={{
              color: msg.type === "success" ? "#27ae60" : "#e74c3c",
              fontSize: "0.85rem",
              margin: "0.5rem 0",
            }}
          >
            {msg.text}
          </p>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            width: "100%",
            padding: "0.6rem",
            borderRadius: 8,
            border: "none",
            background: saving ? "#ccc" : "#4a90d9",
            color: "#fff",
            fontSize: "0.95rem",
            cursor: saving ? "default" : "pointer",
            marginTop: "0.5rem",
          }}
        >
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
