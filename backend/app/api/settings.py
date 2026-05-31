"""Settings API — read and update LLM/embedding/chunking config at runtime."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.core.embeddings import reset_embeddings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMConfig(BaseModel):
    provider: str
    anthropic_api_key: str | None = None
    claude_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_base_url: str | None = None


class EmbeddingConfig(BaseModel):
    model: str
    device: str


class ChunkingConfig(BaseModel):
    chunk_size: int
    chunk_overlap: int


@router.get("/llm")
async def get_llm_config():
    return {
        "provider": settings.llm_provider,
        "claude_model": settings.claude_model,
        "openai_model": settings.openai_model,
    }


@router.put("/llm")
async def update_llm_config(config: LLMConfig):
    settings.llm_provider = config.provider
    if config.openai_api_key:
        settings.openai_api_key = config.openai_api_key
    if config.openai_model:
        settings.openai_model = config.openai_model
    if config.openai_base_url:
        settings.openai_base_url = config.openai_base_url
    return {"status": "ok", "provider": settings.llm_provider}


@router.get("/embedding")
async def get_embedding_config():
    return {"model": settings.embedding_model, "device": settings.embedding_device}


@router.put("/embedding")
async def update_embedding_config(config: EmbeddingConfig):
    settings.embedding_model = config.model
    settings.embedding_device = config.device
    reset_embeddings()
    return {"status": "ok"}


@router.get("/chunking")
async def get_chunking_config():
    return {"chunk_size": settings.chunk_size, "chunk_overlap": settings.chunk_overlap}


@router.put("/chunking")
async def update_chunking_config(config: ChunkingConfig):
    settings.chunk_size = config.chunk_size
    settings.chunk_overlap = config.chunk_overlap
    return {"status": "ok"}
