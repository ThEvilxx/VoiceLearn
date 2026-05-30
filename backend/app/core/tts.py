"""
Text-to-speech using edge-tts (free, no API key required).
Returns MP3 audio bytes that the frontend can play directly.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

ZH_VOICE = "zh-CN-XiaoxiaoNeural"
EN_VOICE = "en-US-JennyNeural"


def _detect_voice(text: str) -> str:
    """Pick Chinese or English voice based on text content."""
    chinese_chars = sum(1 for c in text if "一" <= c <= "鿿")
    return ZH_VOICE if chinese_chars > len(text) * 0.3 else EN_VOICE


async def synthesize(text: str) -> bytes:
    """Convert text to MP3 audio bytes using edge-tts.

    Args:
        text: Text to synthesize.

    Returns:
        MP3 audio bytes, or empty bytes on failure.
    """
    if not text.strip():
        return b""

    import edge_tts  # type: ignore[import-untyped]

    voice = _detect_voice(text)
    communicate = edge_tts.Communicate(text, voice)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        await communicate.save(str(tmp_path))
        return tmp_path.read_bytes()
    except Exception:
        return b""
    finally:
        tmp_path.unlink(missing_ok=True)


async def synthesize_stream(text: str) -> bytes:
    """Streaming variant — same interface, single call for now."""
    return await synthesize(text)
