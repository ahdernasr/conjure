import uuid
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..database import get_db
from ..services.command_plane import CommandPlaneService

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory conversation store (hackathon-appropriate)
_conversations: dict[str, list[dict]] = {}


class CommandRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class CommandResponse(BaseModel):
    response: str
    conversation_id: str
    handoff_create: bool = False
    create_prompt: str | None = None


@router.post("/", response_model=CommandResponse)
async def command_plane(req: CommandRequest, db=Depends(get_db)):
    """Command Plane query across all apps."""
    # Resolve or create conversation
    conv_id = req.conversation_id or str(uuid.uuid4())
    history = _conversations.get(conv_id, [])

    service = CommandPlaneService(db)
    response_text, updated_history = await service.process_query(
        message=req.message,
        conversation_history=history,
    )

    # Store updated history
    _conversations[conv_id] = updated_history

    # Detect handoff sentinel
    handoff_create = False
    create_prompt = None
    if "__HANDOFF_CREATE__:" in response_text:
        handoff_create = True
        # Extract the prompt after the sentinel
        parts = response_text.split("__HANDOFF_CREATE__:", 1)
        create_prompt = parts[1].strip() if len(parts) > 1 else req.message
        # Clean the response for the user
        response_text = f"Sure, I'll create that for you!"

    return CommandResponse(
        response=response_text,
        conversation_id=conv_id,
        handoff_create=handoff_create,
        create_prompt=create_prompt,
    )
