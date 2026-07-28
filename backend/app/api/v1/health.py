"""Health check endpoint."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.database.session import engine


router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
async def health_check() -> dict[str, str] | JSONResponse:
    """Report API and database connectivity status."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "version": settings.app_version,
                "environment": settings.environment,
            },
        )

    return {
        "status": "healthy",
        "database": "connected",
        "version": settings.app_version,
        "environment": settings.environment,
    }
