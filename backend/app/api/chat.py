"""Voice + text chat API with SSE streaming."""

from __future__ import annotations

import json
import re

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
    """Text-based RAG chat with conversation memory."""
    if not req.question.strip():
        return {"answer": "Please enter a question.", "sources": [], "conversation_id": ""}

    answer, sources, conv_id = await generate_answer(
        req.question,
        conversation_id=req.conversation_id,
        top_k=req.top_k,
        use_hybrid=req.use_hybrid,
        mode=req.mode,
    )
    return {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
        "conversation_id": conv_id,
    }


@router.post("/voice")
async def chat_voice(
    request: Request,
    conversation_id: str | None = None,
):
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

    # Step 2: RAG (voice mode: concise spoken answers)
    answer, sources, conv_id = await generate_answer(
        question, conversation_id=conversation_id, mode="voice"
    )

    # Step 3: TTS (strip Markdown so TTS doesn't read "**" aloud)
    tts_text = _strip_markdown(answer)
    audio = await synthesize(tts_text)

    return {
        "question": question,
        "answer": answer,
        "conversation_id": conv_id,
        "audio_base64": _to_base64(audio) if audio else None,
        "sources": [s.model_dump() for s in sources],
    }


@router.post("/stream")
async def chat_text_stream(req: ChatRequest):
    """Text-based RAG chat with SSE streaming."""

    async def event_stream():
        answer, sources, conv_id = await generate_answer(
            req.question,
            conversation_id=req.conversation_id,
            top_k=req.top_k,
            use_hybrid=req.use_hybrid,
            mode=req.mode,
        )
        yield {"event": "conversation_id", "data": conv_id}
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
async def chat_voice_stream(
    request: Request,
    conversation_id: str | None = None,
):
    """Voice chat with SSE streaming.

    Returns events: 'conversation_id', 'question' (ASR text), 'sources',
    'message' (answer), and 'audio' (TTS base64).
    """
    audio_bytes: bytes = await request.body()

    async def event_stream():
        # ASR
        question = transcribe(audio_bytes)
        if not question:
            yield {"event": "error", "data": "Could not transcribe audio"}
            return

        yield {"event": "question", "data": question}

        # RAG (voice mode: concise spoken answers)
        answer, sources, conv_id = await generate_answer(
            question, conversation_id=conversation_id, mode="voice"
        )
        yield {"event": "conversation_id", "data": conv_id}
        yield {
            "event": "sources",
            "data": json.dumps([s.model_dump() for s in sources], ensure_ascii=False),
        }
        yield {"event": "message", "data": answer}

        # TTS (strip Markdown so TTS doesn't read "**" aloud)
        tts_text = _strip_markdown(answer)
        audio = await synthesize(tts_text)
        if audio:
            yield {"event": "audio", "data": _to_base64(audio)}

    return EventSourceResponse(event_stream())


def _strip_markdown(text: str) -> str:
    """Remove Markdown formatting tokens so TTS reads clean spoken text."""
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\|", " ", text)
    return text


def _to_base64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")
