from pydantic import BaseModel
from datetime import datetime


class AppBase(BaseModel):
    name: str
    description: str = ""
    theme_color: str = "#6366f1"


class AppCreate(AppBase):
    """Used internally by Phase 2 generator when creating an app entry."""
    pass


class AppResponse(AppBase):
    """Returned from GET endpoints."""
    id: str
    created_at: datetime
    updated_at: datetime
    status: str = "active"
    version: int = 1

    model_config = {"from_attributes": True}


class AppListResponse(BaseModel):
    """Wraps a list of apps for the gallery."""
    apps: list[AppResponse]
    count: int
