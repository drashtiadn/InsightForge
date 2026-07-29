"""Tool layer exceptions.

All failures originating inside a Tool implementation raise ToolError or a
subclass of it. The execution engine catches these and converts them to
TaskExecutionError so callers above the engine never see tool internals.
"""

from __future__ import annotations

import uuid


class ToolError(Exception):
    """Base exception for all tool failures.

    Attributes:
        task_id: The ID of the task the tool was processing when it failed.
        reason:  Human-readable description of what went wrong.
    """

    def __init__(self, task_id: uuid.UUID, reason: str) -> None:
        self.task_id = task_id
        self.reason = reason
        super().__init__(f"Tool failed for task {task_id}: {reason}")
