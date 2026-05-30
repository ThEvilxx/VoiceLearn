"""Chat data models."""

from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    use_hybrid: bool = True
    top_k: int = 5


class SourceDocument(BaseModel):
    document_id: str
    document_name: str
    content: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceDocument]
    conversation_id: str
