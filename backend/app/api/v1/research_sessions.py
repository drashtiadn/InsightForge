"""Research session REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.planning.planner import ResearchPlanner, SimpleResearchPlanner
from app.repositories.research_session_repository import ResearchSessionRepository
from app.schemas.research_session import (
    ResearchSessionCreate,
    ResearchSessionResponse,
    ResearchSessionStatusUpdate,
)
from app.services.exceptions import (
    InvalidResearchStateTransition,
    ResearchAlreadyCompleted,
    ResearchAlreadyRunning,
    ResearchSessionNotFoundError,
)
from app.services.research_session_service import ResearchSessionService


router = APIRouter(prefix="/research-sessions", tags=["research-sessions"])


def get_research_planner() -> ResearchPlanner:
    """Provide the default deterministic research planner."""
    return SimpleResearchPlanner()


def get_research_session_service(
    db: AsyncSession = Depends(get_db),
    planner: ResearchPlanner = Depends(get_research_planner),
) -> ResearchSessionService:
    """Build a request-scoped service with its repository and planner."""
    return ResearchSessionService(
        session=db,
        repository=ResearchSessionRepository(db),
        planner=planner,
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


@router.post("/{session_id}/start", response_model=ResearchSessionResponse)
async def start_research_session(
    session_id: uuid.UUID,
    service: ResearchSessionService = Depends(get_research_session_service),
) -> ResearchSessionResponse:
    """Move a pending research session into planning and generate a plan."""
    try:
        research_session, _plan = await service.start_research(session_id)
    except ResearchSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ResearchAlreadyCompleted, ResearchAlreadyRunning) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except InvalidResearchStateTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Plan is generated in memory for architecture validation; not exposed yet.
    return ResearchSessionResponse.model_validate(research_session)


@router.patch("/{session_id}/status", response_model=ResearchSessionResponse)
async def update_research_session_status(
    session_id: uuid.UUID,
    payload: ResearchSessionStatusUpdate,
    service: ResearchSessionService = Depends(get_research_session_service),
) -> ResearchSessionResponse:
    """Move a research session to the next valid workflow state."""
    try:
        research_session = await service.update_status(session_id, payload.status)
    except ResearchSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ResearchAlreadyCompleted, ResearchAlreadyRunning) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except InvalidResearchStateTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ResearchSessionResponse.model_validate(research_session)
