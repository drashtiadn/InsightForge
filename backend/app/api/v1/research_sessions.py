"""Research session REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.repositories.research_session_repository import ResearchSessionRepository
from app.schemas.research_session import ResearchSessionCreate, ResearchSessionResponse
from app.services.exceptions import ResearchSessionNotFoundError
from app.services.research_session_service import ResearchSessionService


router = APIRouter(prefix="/research-sessions", tags=["research-sessions"])


def get_research_session_service(
    db: AsyncSession = Depends(get_db),
) -> ResearchSessionService:
    """Build a request-scoped service with its repository."""
    return ResearchSessionService(
        session=db,
        repository=ResearchSessionRepository(db),
    )


@router.post(
    "",
    response_model=ResearchSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_research_session(
    payload: ResearchSessionCreate,
    service: ResearchSessionService = Depends(get_research_session_service),
) -> ResearchSessionResponse:
    """Create a new research session."""
    research_session = await service.create_session(payload)
    return ResearchSessionResponse.model_validate(research_session)


@router.get("", response_model=list[ResearchSessionResponse])
async def list_research_sessions(
    service: ResearchSessionService = Depends(get_research_session_service),
) -> list[ResearchSessionResponse]:
    """Return all research sessions, newest first."""
    sessions = await service.list_sessions()
    return [ResearchSessionResponse.model_validate(session) for session in sessions]


@router.get("/{session_id}", response_model=ResearchSessionResponse)
async def get_research_session(
    session_id: uuid.UUID,
    service: ResearchSessionService = Depends(get_research_session_service),
) -> ResearchSessionResponse:
    """Return a single research session by ID."""
    try:
        research_session = await service.get_session(session_id)
    except ResearchSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ResearchSessionResponse.model_validate(research_session)
