import { useCallback, useState } from "react";
import type { ChatMessage } from "../types";
import { getConversation, textChat, voiceChat } from "../api/client";
import { ChatInput } from "../components/ChatPanel/ChatInput";
import { ChatWindow } from "../components/ChatPanel/ChatWindow";
import { VoiceButton } from "../components/ChatPanel/VoiceButton";

interface ChatPageProps {
  activeConvId: string | null;
  onConvChange: (id: string) => void;
}

export function ChatPage({ activeConvId, onConvChange }: ChatPageProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadedConvId, setLoadedConvId] = useState<string | null>(null);
  const [mode, setMode] = useState<"voice" | "text">("text");

  const loadConversation = useCallback(async (id: string) => {
    try {
      const detail = await getConversation(id);
      const msgs: ChatMessage[] = detail.messages.map((m) => {
        let sources = undefined;
        if (m.sources) {
          try {
            sources = JSON.parse(m.sources);
          } catch {
            /* sources JSON corrupted, ignore */
          }
        }
        return {
          role: m.role as "user" | "assistant",
          text: m.content,
          sources,
        };
      });
      setMessages(msgs);
      setLoadedConvId(id);
    } catch {
      setMessages([]);
    }
  }, []);

  // Reload when activeConvId changes
  if (activeConvId !== loadedConvId) {
    if (activeConvId) {
      loadConversation(activeConvId);
    } else {
      setMessages([]);
      setLoadedConvId(null);
    }
  }

  const handleText = useCallback(
    async (text: string) => {
      setMessages((prev) => [...prev, { role: "user", text }]);
      setLoading(true);
      try {
        const res = await textChat(text, loadedConvId, mode);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: res.answer, sources: res.sources },
        ]);
        if (res.conversation_id && res.conversation_id !== loadedConvId) {
          setLoadedConvId(res.conversation_id);
          onConvChange(res.conversation_id);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: "Sorry, something went wrong. Please try again.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loadedConvId, onConvChange, mode],
  );

  const handleVoice = useCallback(
    async (blob: Blob) => {
      setLoading(true);
      try {
        const res = await voiceChat(blob, loadedConvId);
        const msgs: ChatMessage[] = [];
        if (res.question) {
          msgs.push({ role: "user", text: res.question });
        }
        msgs.push({
          role: "assistant",
          text: res.answer,
          sources: res.sources,
          audioBase64: res.audio_base64,
        });
        setMessages((prev) => [...prev, ...msgs]);
        if (res.conversation_id && res.conversation_id !== loadedConvId) {
          setLoadedConvId(res.conversation_id);
          onConvChange(res.conversation_id);
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Sorry, voice processing failed." },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loadedConvId, onConvChange],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <ChatWindow messages={messages} loading={loading} />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "0 1rem 0.5rem",
          flexWrap: "wrap",
        }}
      >
        <VoiceButton onAudioReady={handleVoice} disabled={loading} />

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            background: "#eee",
            borderRadius: 20,
            padding: "3px 4px",
          }}
        >
          <button
            onClick={() => setMode("voice")}
            disabled={loading}
            style={{
              padding: "4px 12px",
              borderRadius: 16,
              border: "none",
              background: mode === "voice" ? "#4a90d9" : "transparent",
              color: mode === "voice" ? "#fff" : "#888",
              fontSize: "0.78rem",
              cursor: loading ? "default" : "pointer",
              fontWeight: mode === "voice" ? 600 : 400,
            }}
          >
            🎧 语音简答
          </button>
          <button
            onClick={() => setMode("text")}
            disabled={loading}
            style={{
              padding: "4px 12px",
              borderRadius: 16,
              border: "none",
              background: mode === "text" ? "#4a90d9" : "transparent",
              color: mode === "text" ? "#fff" : "#888",
              fontSize: "0.78rem",
              cursor: loading ? "default" : "pointer",
              fontWeight: mode === "text" ? 600 : 400,
            }}
          >
            📄 深度长文
          </button>
        </div>

        <span style={{ fontSize: "0.78rem", color: "#999" }}>
          or type below
        </span>
      </div>
      <ChatInput onSend={handleText} disabled={loading} />
    </div>
  );
}
