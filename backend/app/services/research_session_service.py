"""Business orchestration for ResearchSession use cases."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_session import ResearchSession, ResearchSessionStatus
from app.repositories.research_session_repository import ResearchSessionRepository
from app.schemas.research_session import ResearchSessionCreate
from app.services.exceptions import (
    InvalidResearchStateTransition,
    ResearchAlreadyCompleted,
    ResearchAlreadyRunning,
    ResearchSessionNotFoundError,
)


ALLOWED_STATUS_TRANSITIONS: dict[
    ResearchSessionStatus, set[ResearchSessionStatus]
] = {
    ResearchSessionStatus.PENDING: {ResearchSessionStatus.PLANNING},
    ResearchSessionStatus.PLANNING: {ResearchSessionStatus.RESEARCHING},
    ResearchSessionStatus.RESEARCHING: {
        ResearchSessionStatus.REPORT_GENERATION,
        ResearchSessionStatus.FAILED,
    },
    ResearchSessionStatus.REPORT_GENERATION: {
        ResearchSessionStatus.COMPLETED,
        ResearchSessionStatus.FAILED,
    },
    ResearchSessionStatus.COMPLETED: set(),
    ResearchSessionStatus.FAILED: set(),
}


class ResearchSessionService:
    """Coordinates validation, transactions, and repository access."""

    def __init__(
        self,
        session: AsyncSession,
        repository: ResearchSessionRepository,
    ) -> None:
        self._session = session
        self._repository = repository

    async def create_session(self, data: ResearchSessionCreate) -> ResearchSession:
        """Validate input, persist a new session, and commit the transaction."""
        title = data.title.strip()
        query = data.query.strip()
        if not title or not query:
            raise ValueError("title and query must not be empty")

        research_session = self._repository.add(title=title, query=query)
        await self._session.commit()
        await self._session.refresh(research_session)
        return research_session

    async def get_session(self, session_id: uuid.UUID) -> ResearchSession:
        """Return a session by ID or raise if it does not exist."""
        research_session = await self._repository.get_by_id(session_id)
        if research_session is None:
            raise ResearchSessionNotFoundError(session_id)
        return research_session

    async def list_sessions(self) -> list[ResearchSession]:
        """Return all research sessions ordered by newest first."""
        return await self._repository.list()

    async def start_research(self, session_id: uuid.UUID) -> ResearchSession:
        """Start a pending research session by moving it into planning."""
        research_session = await self.get_session(session_id)

        if research_session.status == ResearchSessionStatus.COMPLETED:
            raise ResearchAlreadyCompleted(session_id)

        if research_session.status in {
            ResearchSessionStatus.PLANNING,
            ResearchSessionStatus.RESEARCHING,
            ResearchSessionStatus.REPORT_GENERATION,
        }:
            raise ResearchAlreadyRunning(session_id, research_session.status)

        return await self._apply_status_transition(
            research_session,
            ResearchSessionStatus.PLANNING,
        )

    async def update_status(
        self,
        session_id: uuid.UUID,
        status: ResearchSessionStatus,
    ) -> ResearchSession:
        """Move a research session to its next valid workflow state."""
        research_session = await self.get_session(session_id)
        return await self._apply_status_transition(research_session, status)

    async def _apply_status_transition(
        self,
        research_session: ResearchSession,
        target_status: ResearchSessionStatus,
    ) -> ResearchSession:
        """Validate and persist a workflow status change."""
        self._validate_transition(research_session.status, target_status)
        research_session.status = target_status
        self._repository.update(research_session)

        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        await self._session.refresh(research_session)
        return research_session

    def _validate_transition(
        self,
        current_status: ResearchSessionStatus,
        target_status: ResearchSessionStatus,
    ) -> None:
        """Ensure the requested status change follows the workflow."""
        allowed_statuses = ALLOWED_STATUS_TRANSITIONS[current_status]
        if target_status not in allowed_statuses:
            raise InvalidResearchStateTransition(current_status, target_status)
