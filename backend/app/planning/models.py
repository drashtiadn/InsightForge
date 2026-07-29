"""In-memory planning models for research decomposition.

These dataclasses are domain value objects. They are never persisted.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ResearchTask:
    """A single actionable step within a research plan."""

    id: uuid.UUID
    title: str
    description: str


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    """Deterministic (or later AI-produced) plan for one research session."""

    session_id: uuid.UUID
    original_query: str
    tasks: list[ResearchTask] = field(default_factory=list)
