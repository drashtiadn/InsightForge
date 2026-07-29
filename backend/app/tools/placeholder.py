"""PlaceholderTool — the first concrete Tool implementation.

Purpose:
    Validate the Tool abstraction, dependency injection wiring, and
    structured logging end-to-end before any real data source is integrated.

Behaviour:
    Accepts a ToolRequest containing a ResearchTask and returns a ToolResult
    whose output is a deterministic placeholder string.

Replacement path:
    When Tavily (or any real tool) is ready, inject it in place of this class.
    Nothing else in the system changes.
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger

from app.tools.base import Tool
from app.tools.models import ToolRequest, ToolResult


class PlaceholderTool(Tool):
    """Deterministic tool that returns a fixed placeholder output.

    No network I/O. No external dependencies. Safe to use in every
    environment — development, CI, and early integration testing.
    """

    def execute(self, request: ToolRequest) -> ToolResult:
        """Return a placeholder output for *request.task*.

        Args:
            request: Contains the ResearchTask to process.

        Returns:
            ToolResult with a deterministic placeholder string.
        """
        task = request.task

        tool_log = logger.bind(
            tool=self.__class__.__name__,
            task_id=str(task.id),
            task_title=task.title,
        )
        tool_log.info("Tool started")

        started_at = datetime.utcnow()
        output = f"Placeholder execution for: {task.title}"
        completed_at = datetime.utcnow()

        duration_ms = (completed_at - started_at).total_seconds() * 1000

        tool_log.bind(duration_ms=round(duration_ms, 4)).info("Tool completed")

        return ToolResult(
            task_id=task.id,
            output=output,
            metadata={"tool": self.__class__.__name__},
            completed_at=completed_at,
        )
