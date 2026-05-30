"""Voice + text chat API with SSE streaming."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.core.asr import transcribe
from app.core.tts import synthesize
from app.models.chat import ChatRequest
from app.services.chat_service import generate_answer

router = APIRouter(prefix="/api/chat", tags=["chat"])


class VoiceRequest(BaseModel):
    audio_base64: str | None = None


@router.post("")
async def chat_text(req: ChatRequest):
    """Text-based RAG chat."""
    answer, sources = await generate_answer(
        req.question,
        top_k=req.top_k,
        use_hybrid=req.use_hybrid,
    )
    return {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
    }


@router.post("/voice")
async def chat_voice(request: Request):
    """Voice-based RAG chat.

    Accepts audio bytes (multipart or raw), runs ASR → RAG → TTS,
    returns transcribed text, answer text, and audio bytes.
    """
    audio_bytes: bytes = await request.body()

    if not audio_bytes:
        return {"error": "No audio data received"}

    # Step 1: ASR
    question = transcribe(audio_bytes)
    if not question:
        return {"error": "Could not transcribe audio. Please try again."}

    # Step 2: RAG
    answer, sources = await generate_answer(question)

    # Step 3: TTS
    audio = await synthesize(answer)

    return {
        "question": question,
        "answer": answer,
        "audio_base64": _to_base64(audio) if audio else None,
        "sources": [s.model_dump() for s in sources],
    }


@router.post("/stream")
async def chat_text_stream(req: ChatRequest):
    """Text-based RAG chat with SSE streaming."""

    async def event_stream():
        answer, sources = await generate_answer(
            req.question,
            top_k=req.top_k,
            use_hybrid=req.use_hybrid,
        )
        yield {
            "event": "sources",
            "data": json.dumps([s.model_dump() for s in sources], ensure_ascii=False),
        }
        yield {
            "event": "message",
            "data": answer,
        }

    return EventSourceResponse(event_stream())


@router.post("/voice/stream")
async def chat_voice_stream(request: Request):
    """Voice chat with SSE streaming.

    Returns events: 'question' (ASR text), 'sources', 'message' (answer),
    and 'audio' (TTS base64).
    """
    audio_bytes: bytes = await request.body()

    async def event_stream():
        # ASR
        question = transcribe(audio_bytes)
        if not question:
            yield {"event": "error", "data": "Could not transcribe audio"}
            return

        yield {"event": "question", "data": question}

        # RAG
        answer, sources = await generate_answer(question)
        yield {
            "event": "sources",
            "data": json.dumps([s.model_dump() for s in sources], ensure_ascii=False),
        }
        yield {"event": "message", "data": answer}

        # TTS
        audio = await synthesize(answer)
        if audio:
            yield {"event": "audio", "data": _to_base64(audio)}

    return EventSourceResponse(event_stream())


def _to_base64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")
