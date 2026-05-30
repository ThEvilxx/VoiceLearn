"""
Local embedding model management (BGE-large-zh-v1.5).
Lazy singleton to avoid reloading the model on every request.
"""

from langchain_huggingface import HuggingFaceEmbeddings

from app.config import settings

_embedding_model: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": settings.embedding_device},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model


def reset_embeddings() -> None:
    """Reset the embedding model (used when switching models via settings API)."""
    global _embedding_model
    _embedding_model = None
