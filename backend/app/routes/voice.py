from fastapi import APIRouter

router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio():
    """Phase 4: Audio -> text via ElevenLabs STT."""
    return {"status": "not_implemented", "phase": 4}


@router.post("/speak")
async def text_to_speech():
    """Phase 4: Text -> audio via ElevenLabs TTS."""
    return {"status": "not_implemented", "phase": 4}
