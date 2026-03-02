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
    handoff_iterate: bool = False
    iterate_app_id: str | None = None
    iterate_instruction: str | None = None


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

    # Detect handoff sentinels
    handoff_create = False
    create_prompt = None
    handoff_iterate = False
    iterate_app_id = None
    iterate_instruction = None

    if "__HANDOFF_ITERATE__:" in response_text:
        handoff_iterate = True
        # Format: __HANDOFF_ITERATE__:<app_id>:<instruction>
        parts = response_text.split("__HANDOFF_ITERATE__:", 1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        segments = payload.split(":", 1)
        iterate_app_id = segments[0].strip() if len(segments) > 0 else None
        iterate_instruction = segments[1].strip() if len(segments) > 1 else req.message
        response_text = "Sure, I'll update that for you!"
    elif "__HANDOFF_CREATE__:" in response_text:
        handoff_create = True
        parts = response_text.split("__HANDOFF_CREATE__:", 1)
        create_prompt = parts[1].strip() if len(parts) > 1 else req.message
        response_text = "Sure, I'll create that for you!"

    return CommandResponse(
        response=response_text,
        conversation_id=conv_id,
        handoff_create=handoff_create,
        create_prompt=create_prompt,
        handoff_iterate=handoff_iterate,
        iterate_app_id=iterate_app_id,
        iterate_instruction=iterate_instruction,
    )
