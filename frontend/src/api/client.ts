import type {
  ChatResponse,
  ConversationDetail,
  ConversationMeta,
  DocumentInfo,
  GraphData,
  VoiceResponse,
} from "../types";

const BASE = "/api";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/documents`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json() as Promise<DocumentInfo>;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  return request<DocumentInfo[]>("/documents");
}

export async function deleteDocument(id: string): Promise<void> {
  await fetch(`${BASE}/documents/${id}`, { method: "DELETE" });
}

export async function textChat(
  question: string,
  conversation_id?: string | null,
  mode: "voice" | "text" = "text",
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ question, conversation_id, mode }),
  });
}

export async function voiceChat(
  audioBlob: Blob,
  conversation_id?: string | null,
): Promise<VoiceResponse> {
  const url = conversation_id
    ? `${BASE}/chat/voice?conversation_id=${conversation_id}`
    : `${BASE}/chat/voice`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "audio/webm" },
    body: audioBlob,
  });
  if (!res.ok) throw new Error(`Voice chat failed: ${res.status}`);
  return res.json() as Promise<VoiceResponse>;
}

export async function listConversations(): Promise<ConversationMeta[]> {
  return request<ConversationMeta[]>("/conversations");
}

export async function createConversation(): Promise<{ conversation_id: string }> {
  return request("/conversations", { method: "POST" });
}

export async function getConversation(
  id: string,
): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${id}`);
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/conversations/${id}`, { method: "DELETE" });
}

export async function getGraph(): Promise<GraphData> {
  return request<GraphData>("/graph");
}

export async function reloadGraph(): Promise<{ nodes: number; edges: number }> {
  return request("/graph/reload", { method: "POST" });
}

export function textChatStream(
  question: string,
  onSources: (sources: unknown[]) => void,
  onMessage: (chunk: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const controller = new AbortController();
  fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        onError(`Stream error: ${res.status}`);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("event: sources")) continue;
          if (line.startsWith("event: message")) continue;
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data);
              if (Array.isArray(parsed)) {
                onSources(parsed);
              }
            } catch {
              onMessage(data);
            }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(String(err));
      }
    });
  return controller;
}
