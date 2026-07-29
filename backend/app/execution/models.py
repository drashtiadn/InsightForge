"""In-memory execution result models.

These dataclasses represent the outcome of running a ResearchPlan through an
ExecutionEngine. They are value objects — immutable, never persisted.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.planning.models import ResearchPlan


@dataclass(frozen=True, slots=True)
class ResearchTaskResult:
    """The outcome of executing a single ResearchTask."""

    task_id: uuid.UUID
    title: str
    output: str
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class ResearchExecutionResult:
    """The aggregate outcome of running every task in a ResearchPlan."""

    session_id: uuid.UUID
    plan: ResearchPlan
    task_results: list[ResearchTaskResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime = field(default_factory=datetime.utcnow)
