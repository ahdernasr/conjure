import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..database import get_db
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


@router.post("/", response_model=GenerateResponse)
async def generate_app(request: GenerateRequest, db=Depends(get_db)):
    """Generate a new app from a text prompt."""
    app_id = uuid.uuid4().hex[:12]

    # Use golden template if explicitly requested
    if request.golden_id and request.golden_id in golden.GOLDEN_TEMPLATES:
        app_name, theme_color, _ = golden.deploy_golden(request.golden_id, app_id)

        service = AppService(db)
        await service.create_app(app_id, app_name, request.prompt, theme_color)

        return GenerateResponse(
            id=app_id,
            name=app_name,
            description=request.prompt,
            theme_color=theme_color,
        )

    # Agentic pipeline
    client = MistralClientWrapper()

    # Pass 1: Augment terse prompt into full spec
    augmented_prompt = await client.augment_prompt(
        request.prompt, AUGMENTATION_SYSTEM_PROMPT
    )
    app_name = extract_app_name_from_spec(
        augmented_prompt, request.prompt.strip()[:50]
    )
    logger.info(f"Augmented prompt for {app_id}: app_name={app_name}")

    try:
        # Pass 2: Generate app from augmented spec
        success, theme_color = await generate_app_pipeline(
            client, augmented_prompt, app_id, app_name
        )
    except Exception as e:
        logger.error(f"Pipeline exception for {app_id}: {e}")
        success = False
        theme_color = "#6366f1"

    # If pipeline failed, fall back to best golden template
    if not success:
        logger.warning(f"Pipeline failed for {app_id}, falling back to golden template")
        best_golden = golden.pick_best_golden(request.prompt)
        if best_golden:
            app_name, theme_color, _ = golden.deploy_golden(best_golden, app_id)
        else:
            raise HTTPException(status_code=500, detail="Generation failed")

    # Save to database
    service = AppService(db)
    await service.create_app(app_id, app_name, request.prompt, theme_color)

    return GenerateResponse(
        id=app_id,
        name=app_name,
        description=request.prompt,
        theme_color=theme_color,
    )


@router.post("/iterate", response_model=GenerateResponse)
async def iterate_app(request: IterateRequest, db=Depends(get_db)):
    """Refine an existing app based on user instruction."""
    service = AppService(db)
    app = await service.get_app(request.app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    client = MistralClientWrapper()

    # Augment iteration instruction into detailed spec
    augmented_instruction = await client.augment_prompt(
        request.instruction, ITERATION_AUGMENTATION_SYSTEM_PROMPT
    )
    logger.info(f"Augmented iteration for {request.app_id}")

    try:
        success, theme_color = await iterate_app_pipeline(
            client, augmented_instruction, request.app_id, app["name"]
        )
    except Exception as e:
        logger.error(f"Iterate pipeline exception for {request.app_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Iteration failed: {e}")

    if not success:
        raise HTTPException(status_code=500, detail="Build failed after retries")

    # Update DB
    await service.update_theme(request.app_id, theme_color)

    return GenerateResponse(
        id=request.app_id,
        name=app["name"],
        description=request.instruction,
        theme_color=theme_color,
    )
