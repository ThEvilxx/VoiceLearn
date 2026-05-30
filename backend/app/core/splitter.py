"""
Text chunking strategies.
Default: RecursiveCharacterTextSplitter with configurable size/overlap.
Alternative: SemanticChunker for semantic boundary detection.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


def split_documents(docs: list[Document]) -> list[Document]:
    """Split documents using recursive character splitting."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", "。", ".", "；", ";", "，", ",", " ", ""],
    )
    return splitter.split_documents(docs)


def split_semantic(docs: list[Document]) -> list[Document]:
    """Split documents using semantic chunking (requires langchain_experimental)."""
    from langchain_experimental.text_splitter import SemanticChunker

    from app.core.embeddings import get_embeddings

    splitter = SemanticChunker(get_embeddings())
    return splitter.split_documents(docs)
