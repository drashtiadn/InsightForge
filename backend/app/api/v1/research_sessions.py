"""Research session REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger

from app.core.config import settings
from app.database.session import get_db
from app.execution.engine import ExecutionEngine, ResearchExecutionEngine
from app.llm import GeminiLLMClient, LLMConnectionError
from app.planning.exceptions import LLMUnavailable
from app.planning.llm_planner import LLMResearchPlanner
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
    """Select the configured research planner implementation."""
    logger.bind(planner_type=settings.planner_type).info("Planner selected")

    if settings.planner_type == "llm":
        try:
            llm_client = GeminiLLMClient(api_key=settings.gemini_api_key)
        except LLMConnectionError as exc:
            logger.warning("LLM planner requested but provider is not configured")
            raise LLMUnavailable(str(exc)) from exc

        return LLMResearchPlanner(
            llm_client=llm_client,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )

    return SimpleResearchPlanner()


def get_execution_engine() -> ExecutionEngine:
    """Provide the default sequential execution engine."""
    return ResearchExecutionEngine()


def get_research_session_service(
    db: AsyncSession = Depends(get_db),
    planner: ResearchPlanner = Depends(get_research_planner),
    execution_engine: ExecutionEngine = Depends(get_execution_engine),
) -> ResearchSessionService:
    """Build a request-scoped service with its repository, planner, and engine."""
    return ResearchSessionService(
        session=db,
        repository=ResearchSessionRepository(db),
        planner=planner,
        execution_engine=execution_engine,
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
        research_session, _plan, _execution_result = await service.start_research(session_id)
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
