"""ElevenLabs voice integration: STT and TTS."""

import logging
import httpx
from ..config import settings

logger = logging.getLogger(__name__)

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Convert audio to text via ElevenLabs STT."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE}/speech-to-text",
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            files={"file": ("recording.webm", audio_bytes, "audio/webm")},
            data={"model_id": "scribe_v1"},
        )
        resp.raise_for_status()
        return resp.json()["text"]


async def text_to_speech(text: str) -> bytes:
    """Convert text to audio via ElevenLabs TTS."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE}/text-to-speech/{DEFAULT_VOICE_ID}",
            headers={
                "xi-api-key": settings.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
            },
            params={"output_format": "mp3_44100_128"},
        )
        resp.raise_for_status()
        return resp.content
