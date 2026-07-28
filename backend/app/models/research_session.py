"""ResearchSession ORM model and lifecycle status enum."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ResearchSessionStatus(str, enum.Enum):
    """Allowed lifecycle states for a research session."""

    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    REPORT_GENERATION = "REPORT_GENERATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ResearchSession(Base):
    """Persistent record of a single research request and its progress."""

    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ResearchSessionStatus] = mapped_column(
        Enum(
            ResearchSessionStatus,
            name="research_session_status",
            native_enum=True,
        ),
        nullable=False,
        default=ResearchSessionStatus.PENDING,
        server_default=ResearchSessionStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
