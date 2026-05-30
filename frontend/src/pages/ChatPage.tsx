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

  const loadConversation = useCallback(async (id: string) => {
    try {
      const detail = await getConversation(id);
      const msgs: ChatMessage[] = detail.messages.map((m) => ({
        role: m.role as "user" | "assistant",
        text: m.content,
      }));
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
        const res = await textChat(text, loadedConvId);
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
    [loadedConvId, onConvChange],
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
        }}
      >
        <VoiceButton onAudioReady={handleVoice} disabled={loading} />
        <span style={{ fontSize: "0.8rem", color: "#999" }}>or type below</span>
      </div>
      <ChatInput onSend={handleText} disabled={loading} />
    </div>
  );
}
