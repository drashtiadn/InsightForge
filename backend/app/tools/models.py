"""Immutable value objects for the tool layer.

ToolRequest  — carries a task into a tool
ToolResult   — carries the tool's output back to the caller

Neither model is persisted. Both are frozen dataclasses so they can be
passed across boundaries without risk of mutation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.planning.models import ResearchTask


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """The input a tool receives when asked to execute a task.

    Attributes:
        task:    The ResearchTask the tool must process.
        context: Optional caller-supplied metadata (e.g. session ID, flags).
                 Defaults to an empty dict so callers need not supply it.
    """

    task: ResearchTask
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolResult:
    """The output produced by a tool for one task.

    Attributes:
        task_id:      ID of the task that was executed.
        output:       The textual result the tool produced.
        metadata:     Optional dict of supplementary information (e.g. source
                      URLs, token counts). Defaults to an empty dict.
        completed_at: UTC timestamp recorded by the tool when it finished.
    """

    task_id: uuid.UUID
    output: str
    metadata: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.utcnow)
