"""Typed application configuration loaded from the environment."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

DEFAULT_APP_NAME: str = "InsightForge API"
DEFAULT_ENVIRONMENT: Literal["local", "development", "staging", "production"] = "local"
DEFAULT_API_PREFIX: str = "/api/v1"
DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_HOST: str = "0.0.0.0"
DEFAULT_PORT: int = 8000
APP_VERSION: str = "0.1.0"
APP_DESCRIPTION: str = "AI-powered research platform API"


class Settings(BaseSettings):
    """Runtime configuration for the API process."""

    app_name: str = Field(default=DEFAULT_APP_NAME, description="Human-readable service name.")
    environment: Literal["local", "development", "staging", "production"] = Field(
        default=DEFAULT_ENVIRONMENT,
        description="Deployment environment name.",
    )
    api_prefix: str = Field(
        default=DEFAULT_API_PREFIX,
        description="URL prefix for versioned API routes.",
    )
    log_level: str = Field(default=DEFAULT_LOG_LEVEL, description="Minimum Loguru log level.")
    log_json: bool = Field(default=False, description="Emit logs as JSON when true.")
    host: str = Field(default=DEFAULT_HOST, description="Bind host for the ASGI server.")
    port: int = Field(default=DEFAULT_PORT, description="Bind port for the ASGI server.")

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
