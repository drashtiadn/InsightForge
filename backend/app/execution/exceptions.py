"""Execution-layer exceptions.

Kept separate so callers can catch execution failures without importing
engine internals. New engines may introduce their own subclasses here.
"""

from __future__ import annotations


class ExecutionError(Exception):
    """Base class for all execution-layer failures."""


class TaskExecutionError(ExecutionError):
    """Raised when a single task fails during sequential execution."""

    def __init__(self, task_id: str, title: str, reason: str) -> None:
        super().__init__(
            f"Task '{title}' (id={task_id}) failed during execution: {reason}"
        )
        self.task_id = task_id
        self.title = title
        self.reason = reason
