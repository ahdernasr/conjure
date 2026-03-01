from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..services.voice import transcribe_audio, text_to_speech

router = APIRouter()


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Audio -> text via ElevenLabs STT."""
    try:
        audio_bytes = await audio.read()
        text = await transcribe_audio(audio_bytes)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SpeakRequest(BaseModel):
    text: str


@router.post("/speak")
async def speak(req: SpeakRequest):
    """Text -> audio via ElevenLabs TTS."""
    try:
        audio_bytes = await text_to_speech(req.text)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
