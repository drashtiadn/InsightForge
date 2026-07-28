"""Persistence operations for ResearchSession aggregates."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_session import ResearchSession, ResearchSessionStatus


class ResearchSessionRepository:
    """Data-access layer for ResearchSession rows. No business rules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(
        self,
        *,
        title: str,
        query: str,
        status: ResearchSessionStatus = ResearchSessionStatus.PENDING,
    ) -> ResearchSession:
        """Stage a new research session in the current unit of work."""
        research_session = ResearchSession(
            title=title,
            query=query,
            status=status,
        )
        self._session.add(research_session)
        return research_session

    async def get_by_id(self, session_id: uuid.UUID) -> ResearchSession | None:
        """Return a research session by primary key, or None if missing."""
        return await self._session.get(ResearchSession, session_id)

    async def list(self) -> list[ResearchSession]:
        """Return all research sessions ordered by newest first."""
        result = await self._session.execute(
            select(ResearchSession).order_by(ResearchSession.created_at.desc())
        )
        return list(result.scalars().all())
