"""Aggregate router for API version 1 endpoints."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.research_sessions import router as research_sessions_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(research_sessions_router)
