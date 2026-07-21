"""Typed application configuration loaded from the environment."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]

APP_VERSION = "0.1.0"
APP_DESCRIPTION = "AI-powered research platform API"


class Settings(BaseSettings):
    """Runtime configuration for the API process."""

    app_name: str = "InsightForge API"
    environment: Literal["local", "development", "staging", "production"] = "local"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
