"""Phase 4: ElevenLabs voice integration.

Responsibilities:
- STT: Audio bytes -> text transcription
- TTS: Text -> audio stream
"""


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Convert audio to text via ElevenLabs STT."""
    raise NotImplementedError("Phase 4")


async def text_to_speech(text: str) -> bytes:
    """Convert text to audio via ElevenLabs TTS."""
    raise NotImplementedError("Phase 4")
