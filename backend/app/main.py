"""VoiceLearn — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, documents, knowledge_graph, settings
from app.config import settings as app_settings
from app.core.embeddings import get_embeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VoiceLearn starting up...")
    app_settings.data_dir.mkdir(parents=True, exist_ok=True)
    app_settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    app_settings.upload_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading embedding model (%s)...", app_settings.embedding_model)
    get_embeddings()
    logger.info("Embedding model loaded.")
    yield
    logger.info("VoiceLearn shutting down.")


app = FastAPI(
    title="VoiceLearn",
    description="语音交互式学习伴侣 — Upload materials, learn by speaking",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(knowledge_graph.router)
app.include_router(settings.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "VoiceLearn"}


# Serve frontend static files in production
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
