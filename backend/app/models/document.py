"""Document data models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DocumentInfo(BaseModel):
    id: str
    name: str
    file_type: str
    chunk_count: int
    status: str  # processing | ready | error
    created_at: datetime


class DocumentDetail(BaseModel):
    id: str
    name: str
    file_type: str
    chunk_count: int
    status: str
    chunks: list[ChunkPreview]
    created_at: datetime


class ChunkPreview(BaseModel):
    index: int
    content_preview: str
