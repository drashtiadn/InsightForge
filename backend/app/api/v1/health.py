"""Health check endpoint."""

from fastapi import APIRouter

from app.core.config import APP_VERSION, settings


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Report that the API is running."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": APP_VERSION,
    }
