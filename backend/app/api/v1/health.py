"""Version 1 health endpoint."""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter

from app.core.config import APP_VERSION, settings


HEALTH_STATUS: Final[str] = "healthy"
HEALTH_TAG: Final[str] = "health"
HEALTH_PATH: Final[str] = "/health"

router = APIRouter(tags=[HEALTH_TAG])


@router.get(HEALTH_PATH)
async def health_check() -> dict[str, str]:
    """Report that the API process is running and able to receive requests."""
    return {
        "status": HEALTH_STATUS,
        "service": settings.app_name,
        "version": APP_VERSION,
    }
