import asyncio
import json
import logging
import uuid
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..database import get_db
from ..config import settings
from ..services.mistral_client import MistralClientWrapper
from ..services.app_service import AppService
from ..services.generator import (
    generate_app_pipeline,
    iterate_app_pipeline,
    extract_app_name_from_spec,
    AUGMENTATION_SYSTEM_PROMPT,
    ITERATION_AUGMENTATION_SYSTEM_PROMPT,
)
from ..services import golden

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    golden_id: str | None = None  # "hiit", "poker", "packing" for golden templates


class IterateRequest(BaseModel):
    app_id: str
    instruction: str


class GenerateResponse(BaseModel):
    id: str
    name: str
    description: str
    theme_color: str


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


@router.post("/")
async def generate_app(request: GenerateRequest, db=Depends(get_db)):
    """Generate a new app from a text prompt. Returns SSE stream with progress events."""
    app_id = uuid.uuid4().hex[:12]

    # Use golden template if explicitly requested (no streaming needed)
    if request.golden_id and request.golden_id in golden.GOLDEN_TEMPLATES:
        app_name, theme_color, _ = golden.deploy_golden(request.golden_id, app_id)

        service = AppService(db)
        await service.create_app(app_id, app_name, request.prompt, theme_color)

        # Still return SSE for consistency
        async def golden_stream():
            yield _sse_event({"type": "status", "message": "Using template..."})
            yield _sse_event({"type": "complete", "data": {
                "id": app_id, "name": app_name,
                "description": request.prompt, "theme_color": theme_color,
                "version": 1,
            }})

        return StreamingResponse(golden_stream(), media_type="text/event-stream")

    # Streaming agentic pipeline
    queue: asyncio.Queue = asyncio.Queue()

    async def on_status(message: str):
        await queue.put({"type": "tool", "message": message})

    async def run_pipeline():
        """Run the full pipeline, pushing events to the queue."""
        client = MistralClientWrapper()

        try:
            # Pass 1: Augment prompt + generate name in parallel
            await queue.put({"type": "status", "message": "Understanding what you need..."})
            augmented_prompt, generated_name = await asyncio.gather(
                client.augment_prompt(request.prompt, AUGMENTATION_SYSTEM_PROMPT),
                client.generate_app_name(request.prompt),
            )
            # Prefer the spec-extracted name, fall back to LLM-generated name
            app_name = extract_app_name_from_spec(augmented_prompt, generated_name)
            logger.info(f"Augmented prompt for {app_id}: app_name={app_name}")

            # Pass 2: Generate
            try:
                success, theme_color = await generate_app_pipeline(
                    client, augmented_prompt, app_id, app_name, on_status=on_status
                )
            except Exception as e:
                logger.error(f"Pipeline exception for {app_id}: {e}")
                success = False
                theme_color = "#6366f1"

            # Fallback to golden template
            if not success:
                logger.warning(f"Pipeline failed for {app_id}, falling back to golden template")
                await queue.put({"type": "status", "message": "Grabbing a matching template..."})
                best_golden = golden.pick_best_golden(request.prompt)
                if best_golden:
                    app_name, theme_color, _ = golden.deploy_golden(best_golden, app_id)
                else:
                    await queue.put({"type": "error", "message": "Couldn't build that one — try describing it differently"})
                    return

            # Save to database with own connection (injected db closes with the SSE stream)
            async with aiosqlite.connect(settings.DATABASE_PATH) as pipeline_db:
                pipeline_db.row_factory = aiosqlite.Row
                service = AppService(pipeline_db)
                await service.create_app(app_id, app_name, request.prompt, theme_color)

            await queue.put({"type": "complete", "data": {
                "id": app_id, "name": app_name,
                "description": request.prompt, "theme_color": theme_color,
                "version": 1,
            }})
        except Exception as e:
            logger.error(f"Generate stream error: {e}")
            await queue.put({"type": "error", "message": "Something went wrong — try again"})

    async def event_stream():
        """SSE generator that reads from the queue while the pipeline runs."""
        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=300)
                    yield _sse_event(event)
                    if event["type"] in ("complete", "error"):
                        break
                except asyncio.TimeoutError:
                    yield _sse_event({"type": "error", "message": "Taking too long — try again with a simpler description"})
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/iterate")
async def iterate_app(request: IterateRequest, db=Depends(get_db)):
    """Refine an existing app. Returns SSE stream with progress events."""
    service = AppService(db)
    app = await service.get_app(request.app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    queue: asyncio.Queue = asyncio.Queue()

    async def on_status(message: str):
        await queue.put({"type": "tool", "message": message})

    current_version = app.get("version", 1) or 1

    async def run_pipeline():
        client = MistralClientWrapper()

        try:
            # Intent classification — skip full pipeline for questions
            await queue.put({"type": "status", "message": "Looking at your app..."})
            intent = await client.classify_intent(request.instruction)
            if intent == "text_response":
                answer = await client.answer_question(request.instruction, request.app_id)
                await queue.put({"type": "chat_response", "message": answer})
                return

            augmented_instruction = await client.augment_prompt(
                request.instruction, ITERATION_AUGMENTATION_SYSTEM_PROMPT
            )
            logger.info(f"Augmented iteration for {request.app_id}")

            # Load recent chat history so the refiner understands follow-ups
            async with aiosqlite.connect(settings.DATABASE_PATH) as hist_db:
                hist_db.row_factory = aiosqlite.Row
                hist_service = AppService(hist_db)
                all_msgs = await hist_service.get_messages(request.app_id)
            # Keep last 6 messages (3 turns) for context without bloating prompt
            chat_history = [{"role": m["role"], "content": m["content"]} for m in all_msgs[-6:]]

            try:
                success, theme_color, new_version = await iterate_app_pipeline(
                    client, augmented_instruction, request.app_id, app["name"],
                    on_status=on_status, current_version=current_version,
                    raw_instruction=request.instruction, chat_history=chat_history,
                )
            except Exception as e:
                logger.error(f"Iterate pipeline exception for {request.app_id}: {e}")
                logger.error(f"Iterate pipeline exception detail: {e}")
                await queue.put({"type": "error", "message": "Couldn't make that change — try rephrasing your request"})
                return

            if not success:
                await queue.put({"type": "error", "message": "That change was too tricky — try a smaller update"})
                return

            # Use own connection (injected db closes with the SSE stream)
            async with aiosqlite.connect(settings.DATABASE_PATH) as pipeline_db:
                pipeline_db.row_factory = aiosqlite.Row
                pipeline_service = AppService(pipeline_db)
                await pipeline_service.update_theme(request.app_id, theme_color)
                await pipeline_db.execute(
                    "UPDATE apps SET version = ? WHERE id = ?",
                    (new_version, request.app_id),
                )
                await pipeline_db.commit()

            summary = await client.summarize_changes(request.instruction)

            await queue.put({"type": "complete", "data": {
                "id": request.app_id, "name": app["name"],
                "description": request.instruction, "theme_color": theme_color,
                "version": new_version,
                "summary": summary,
            }})
        except Exception as e:
            logger.error(f"Iterate stream error: {e}")
            await queue.put({"type": "error", "message": "Something went wrong — try again"})

    async def event_stream():
        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=300)
                    yield _sse_event(event)
                    if event["type"] in ("complete", "error", "chat_response"):
                        break
                except asyncio.TimeoutError:
                    yield _sse_event({"type": "error", "message": "Taking too long — try a simpler change"})
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
