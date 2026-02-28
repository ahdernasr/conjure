import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..database import get_db
from ..services.mistral_client import MistralClientWrapper
from ..services.app_service import AppService
from ..services.generator import process_generated_html, write_app_files
from ..services import golden


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

    # Use golden template if requested
    if request.golden_id and request.golden_id in golden.GOLDEN_TEMPLATES:
        raw_html = golden.GOLDEN_TEMPLATES[request.golden_id]
        app_name = golden.GOLDEN_NAMES[request.golden_id]
    else:
        # Call Codestral
        client = MistralClientWrapper()
        try:
            raw_html = await client.generate_app(request.prompt, app_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Generation failed: {e}")
        # Derive app name from prompt (first few words)
        app_name = request.prompt.strip()[:50]

    # Process: parse, replace placeholders, inject sync script
    html, theme_color = process_generated_html(raw_html, app_id)

    # Write files to disk
    write_app_files(app_id, html, app_name, theme_color)

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

    # Read existing HTML
    existing_html = service.get_app_html(request.app_id)
    if not existing_html:
        raise HTTPException(status_code=404, detail="App HTML not found")

    # Call refiner
    client = MistralClientWrapper()
    try:
        raw_html = await client.refine_app(existing_html, request.instruction, request.app_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refinement failed: {e}")

    # Process the refined HTML
    html, theme_color = process_generated_html(raw_html, request.app_id)

    # Overwrite files
    write_app_files(request.app_id, html, app["name"], theme_color)

    # Update DB
    await service.update_theme(request.app_id, theme_color)

    return GenerateResponse(
        id=request.app_id,
        name=app["name"],
        description=request.instruction,
        theme_color=theme_color,
    )
