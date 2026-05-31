"""Document ingestion orchestration."""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from app.core.loader import load_file, load_url
from app.core.splitter import split_documents
from app.core.vector_store import get_vector_store

logger = logging.getLogger(__name__)


async def ingest_file(file_path: Path | str, original_name: str) -> dict:
    """Ingest a file: load → split → embed → store in ChromaDB."""
    path = Path(file_path)
    docs = load_file(path)
    if not docs:
        return {"status": "error", "message": "No content extracted"}

    chunks = split_documents(docs)
    doc_id = str(uuid.uuid4())
    file_type = docs[0].metadata.get("file_type", path.suffix.lower().lstrip("."))

    for chunk in chunks:
        chunk.metadata["document_id"] = doc_id
        chunk.metadata["source"] = original_name

    store = get_vector_store()
    logger.info(
        "Ingesting %s: %d chunks, generating embeddings (CPU)…",
        original_name, len(chunks),
    )
    await asyncio.to_thread(store.add_documents, chunks)
    logger.info("Ingesting %s: embeddings complete.", original_name)

    return {
        "status": "ready",
        "document_id": doc_id,
        "name": original_name,
        "file_type": file_type,
        "chunk_count": len(chunks),
    }


async def ingest_url(url: str) -> dict:
    """Ingest a web page."""
    docs = load_url(url)
    if not docs:
        return {"status": "error", "message": "No content extracted from URL"}

    chunks = split_documents(docs)
    doc_id = str(uuid.uuid4())

    for chunk in chunks:
        chunk.metadata["document_id"] = doc_id

    store = get_vector_store()
    logger.info("Ingesting URL %s: %d chunks…", url, len(chunks))
    await asyncio.to_thread(store.add_documents, chunks)
    logger.info("Ingesting URL %s: complete.", url)

    return {
        "status": "ready",
        "document_id": doc_id,
        "name": url,
        "file_type": "web",
        "chunk_count": len(chunks),
    }


def list_documents() -> list[dict]:
    """List all ingested documents with chunk counts."""
    store = get_vector_store()
    results = store.get()
    doc_map: dict[str, dict] = {}

    for meta in results.get("metadatas", []):
        if not meta:
            continue
        did = meta.get("document_id", "")
        if did not in doc_map:
            doc_map[did] = {
                "id": did,
                "name": meta.get("source", "unknown"),
                "file_type": meta.get("file_type", "unknown"),
                "chunk_count": 0,
                "status": "ready",
            }
        doc_map[did]["chunk_count"] += 1

    return list(doc_map.values())


def delete_document(doc_id: str) -> bool:
    """Delete a document and its vector chunks. Returns True if deleted."""
    store = get_vector_store()
    before_count = store.get(where={"document_id": doc_id}).get("ids", [])
    if not before_count:
        return False
    store.delete(where={"document_id": doc_id})
    return True
