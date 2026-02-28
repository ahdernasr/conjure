from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.mistral_client import MistralClientWrapper

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/", response_model=ChatResponse)
async def send_chat(request: ChatRequest):
    """Phase 1 milestone: send text, get Mistral response."""
    client = MistralClientWrapper()
    try:
        response = await client.chat(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
