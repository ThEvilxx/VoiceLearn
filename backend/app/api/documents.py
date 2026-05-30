"""Document upload and management API."""

from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, HTTPException, UploadFile

from app.config import settings
from app.services.document_service import delete_document, ingest_file, list_documents

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def get_documents():
    return list_documents()


@router.post("")
async def upload_document(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_id = uuid.uuid4().hex
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._-")
    dest = settings.upload_dir / f"{file_id}_{safe_name}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    result = await ingest_file(dest, file.filename)
    return result


@router.delete("/{doc_id}")
async def remove_document(doc_id: str):
    if not delete_document(doc_id):
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return {"status": "deleted", "document_id": doc_id}
