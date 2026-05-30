import { useCallback, useState } from "react";
import type { ChatMessage } from "../types";
import { textChat, voiceChat } from "../api/client";
import { ChatInput } from "../components/ChatPanel/ChatInput";
import { ChatWindow } from "../components/ChatPanel/ChatWindow";
import { VoiceButton } from "../components/ChatPanel/VoiceButton";

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const handleText = useCallback(async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await textChat(text);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, sources: res.sources },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleVoice = useCallback(async (blob: Blob) => {
    setLoading(true);
    try {
      const res = await voiceChat(blob);
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
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, voice processing failed." },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

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
