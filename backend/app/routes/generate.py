from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def generate_app():
    """Phase 2: Accept prompt, generate PWA, return app metadata."""
    return {"status": "not_implemented", "phase": 2}
