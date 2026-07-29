"""In-memory report models.

These dataclasses represent a synthesized research report produced from a
ResearchExecutionResult. They are value objects — immutable, never persisted.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ResearchSection:
    """A single titled block within a research report."""

    title: str
    content: str


@dataclass(frozen=True, slots=True)
class ResearchReport:
    """The synthesized report for one research session."""

    session_id: uuid.UUID
    title: str
    summary: str
    sections: list[ResearchSection] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
