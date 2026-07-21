"""InsightForge FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import APP_DESCRIPTION, APP_VERSION, settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


ROOT_PATH: Final[str] = "/"
ROOT_WELCOME_MESSAGE: Final[str] = "Welcome to InsightForge API"
CORS_ALLOW_ORIGINS: Final[list[str]] = ["*"]
CORS_ALLOW_CREDENTIALS: Final[bool] = True
CORS_ALLOW_METHODS: Final[list[str]] = ["*"]
CORS_ALLOW_HEADERS: Final[list[str]] = ["*"]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Run startup and shutdown hooks for the API process lifetime."""
    configure_logging()
    logger.info(
        "Starting {app_name} v{version} in {environment} environment",
        app_name=settings.app_name,
        version=APP_VERSION,
        environment=settings.environment,
    )
    yield
    logger.info("Shutting down {app_name}", app_name=settings.app_name)


def create_application() -> FastAPI:
    """Create and configure the InsightForge API application."""
    application = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        description=APP_DESCRIPTION,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )
    application.add_middleware(RequestContextMiddleware)

    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.get(ROOT_PATH)
    async def root() -> dict[str, str]:
        """Return a simple welcome payload for the service root."""
        return {"message": ROOT_WELCOME_MESSAGE}

    return application


app = create_application()
