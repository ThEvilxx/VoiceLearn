"""
Speech-to-text using faster-whisper (local, offline).
Accepts audio bytes and returns transcribed text.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.config import settings

BLACKLIST = (
    "谢谢观看",
    "字幕由",
    "感谢观看",
    "请订阅",
    "一键三连",
    "点赞投币",
    "关注",
)

_model: object | None = None
_model_size: str = ""

_converter: object | None = None


def _get_converter() -> object:
    global _converter
    if _converter is None:
        from opencc import OpenCC

        _converter = OpenCC("t2s")
    return _converter


def _get_model() -> object:
    global _model, _model_size
    if _model is None or _model_size != settings.whisper_model:
        from faster_whisper import WhisperModel

        _model = WhisperModel(
            settings.whisper_model,
            device="cpu",
            compute_type="int8",
        )
        _model_size = settings.whisper_model
    return _model


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe audio bytes (WAV/MP3/WebM) to text.

    Args:
        audio_bytes: Raw audio file content.

    Returns:
        Transcribed text string, or empty string on failure.
    """
    model = _get_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = Path(tmp.name)

    try:
        segments, _info = model.transcribe(str(tmp_path), beam_size=5)  # type: ignore[union-attr]
        text = " ".join(seg.text.strip() for seg in segments).strip()
        for phrase in BLACKLIST:
            if phrase in text:
                return ""
        text = _get_converter().convert(text)  # type: ignore[union-attr]
        return text
    except Exception:
        return ""
    finally:
        tmp_path.unlink(missing_ok=True)


def transcribe_file(file_path: Path) -> str:
    """Transcribe an audio file from disk."""
    audio_bytes = file_path.read_bytes()
    return transcribe(audio_bytes)
