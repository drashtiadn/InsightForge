"""InsightForge FastAPI application factory and ASGI entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import APP_DESCRIPTION, APP_VERSION, settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Configure logging and log startup / shutdown."""
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
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Welcome to InsightForge API"}

    return application


app = create_application()
