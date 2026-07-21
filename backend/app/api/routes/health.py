"""Operational health endpoint."""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Report that the API process is running and able to receive requests."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
    }
