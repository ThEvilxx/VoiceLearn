export interface ConversationMeta {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  conversation_id: string;
  messages: {
    role: string;
    content: string;
    sources?: string | null;
    created_at: string;
  }[];
}

export interface DocumentInfo {
  id: string;
  name: string;
  file_type: string;
  chunk_count: number;
  status: string;
}

export interface SourceDocument {
  document_id: string;
  document_name: string;
  content: string;
  relevance_score: number;
}

export interface ChatResponse {
  answer: string;
  sources: SourceDocument[];
  conversation_id: string;
}

export interface VoiceResponse {
  question: string;
  answer: string;
  conversation_id: string;
  audio_base64?: string;
  sources: SourceDocument[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
  document_ids: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  sources?: SourceDocument[];
  audioBase64?: string;
}
