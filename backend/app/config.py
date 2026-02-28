from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    MISTRAL_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    DATABASE_PATH: str = "conjure.db"
    APPS_DIR: str = "apps"

    # Phase 2+ model settings (defined now, used later)
    CODESTRAL_MODEL: str = "codestral-latest"
    MISTRAL_LARGE_MODEL: str = "mistral-large-latest"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Ensure apps directory exists
Path(settings.APPS_DIR).mkdir(parents=True, exist_ok=True)
