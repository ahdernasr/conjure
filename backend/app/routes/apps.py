from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from ..database import get_db
from ..models.app import AppResponse, AppListResponse
from ..services.app_service import AppService


class ChatMessageRequest(BaseModel):
    role: str
    content: str
    version: int | None = None

router = APIRouter()


@router.get("/", response_model=AppListResponse)
async def list_apps(db=Depends(get_db)):
    """List all apps for the gallery."""
    service = AppService(db)
    apps = await service.list_apps()
    return AppListResponse(apps=apps, count=len(apps))


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(app_id: str, db=Depends(get_db)):
    """Get single app metadata."""
    service = AppService(db)
    app = await service.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.delete("/{app_id}")
async def delete_app(app_id: str, db=Depends(get_db)):
    """Delete an app and its files."""
    service = AppService(db)
    success = await service.delete_app(app_id)
    if not success:
        raise HTTPException(status_code=404, detail="App not found")
    return {"status": "deleted", "id": app_id}


@router.get("/{app_id}/data")
async def get_app_data(app_id: str, db=Depends(get_db)):
    """Return app's data.json. Used by apps to pull Command Plane mutations."""
    service = AppService(db)
    return await service.get_app_data(app_id)


@router.get("/{app_id}/messages")
async def get_messages(app_id: str, db=Depends(get_db)):
    """Get all chat messages for an app."""
    service = AppService(db)
    messages = await service.get_messages(app_id)
    return {"messages": messages}


@router.post("/{app_id}/messages")
async def add_message(app_id: str, msg: ChatMessageRequest, db=Depends(get_db)):
    """Add a chat message for an app."""
    service = AppService(db)
    result = await service.add_message(app_id, msg.role, msg.content, msg.version)
    return result


@router.post("/{app_id}/sync")
async def sync_app_data(app_id: str, request: Request, db=Depends(get_db)):
    """Receive localStorage snapshot from a generated app.
    Reads raw body because navigator.sendBeacon sends text/plain."""
    service = AppService(db)
    body = await request.body()
    await service.sync_data(app_id, body)
    return {"status": "ok"}
