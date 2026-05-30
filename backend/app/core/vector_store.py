"""
Vector store with hybrid search (dense + sparse).
ChromaDB for dense vector search, BM25 for sparse keyword matching.
"""

from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.embeddings import get_embeddings

_store: Chroma | None = None
_bm25_docs: list[str] = []
_bm25_index: BM25Okapi | None = None


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def get_vector_store() -> Chroma:
    global _store
    if _store is None:
        _store = Chroma(
            collection_name="voicelearn",
            embedding_function=get_embeddings(),
            persist_directory=str(settings.chroma_dir),
        )
    return _store


def _get_bm25_index(all_docs: list[str]) -> BM25Okapi:
    global _bm25_docs, _bm25_index
    if _bm25_docs != all_docs:
        _bm25_docs = all_docs
        tokenized = [_tokenize(d) for d in all_docs]
        _bm25_index = BM25Okapi(tokenized)
    return _bm25_index


def search_similar(
    query: str, top_k: int | None = None
) -> list[tuple[Document, float]]:
    """Dense vector similarity search only."""
    k = top_k or settings.top_k
    store = get_vector_store()
    return store.similarity_search_with_relevance_scores(query, k=k)


def search_hybrid(
    query: str,
    top_k: int | None = None,
    dense_weight: float = 0.7,
) -> list[tuple[Document, float]]:
    """Hybrid search: 70% dense + 30% sparse by default."""
    k = top_k or settings.top_k
    search_k = k * 2

    # Dense search
    store = get_vector_store()
    dense_results = store.similarity_search_with_relevance_scores(query, k=search_k)

    # Sparse (BM25) search
    all_docs = [doc.page_content for doc in store.get().get("documents", [])]
    if not all_docs:
        return [(doc, score) for doc, score in dense_results[:k]]

    bm25 = _get_bm25_index(all_docs)
    tokenized_query = _tokenize(query)
    bm25_scores = bm25.get_scores(tokenized_query)
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
    bm25_normalized = [s / max_bm25 for s in bm25_scores]

    merged: dict[str, tuple[Document, float]] = {}
    for doc, score in dense_results:
        merged[doc.page_content] = (doc, score * dense_weight)

    for i, score in enumerate(bm25_normalized):
        if i < len(all_docs) and score > 0:
            content = all_docs[i]
            sparse_score = score * (1 - dense_weight)
            if content in merged:
                doc, existing = merged[content]
                merged[content] = (doc, existing + sparse_score)
            else:
                doc = Document(page_content=content)
                merged[content] = (doc, sparse_score)

    ranked = sorted(merged.values(), key=lambda x: x[1], reverse=True)
    return ranked[:k]
