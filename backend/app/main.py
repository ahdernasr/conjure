from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .config import settings
from .database import init_db
from .routes import apps, chat, generate, command, voice


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Conjure API",
    description="Voice-to-App Generator",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (registered before static mount so they take priority)
app.include_router(apps.router, prefix="/api/apps", tags=["apps"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(generate.router, prefix="/api/generate", tags=["generate"])
app.include_router(command.router, prefix="/api/command", tags=["command"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])

# Static file serving for generated apps
app.mount("/apps", StaticFiles(directory=settings.APPS_DIR, html=True), name="generated-apps")
