"""Business orchestration for ResearchSession use cases."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_session import ResearchSession
from app.repositories.research_session_repository import ResearchSessionRepository
from app.schemas.research_session import ResearchSessionCreate
from app.services.exceptions import ResearchSessionNotFoundError


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
