from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging


def create_application() -> FastAPI:
    """Create and configure the InsightForge API application."""
    configure_logging()

    application = FastAPI(title=settings.app_name)
    application.include_router(health_router)
    return application


app = create_application()
