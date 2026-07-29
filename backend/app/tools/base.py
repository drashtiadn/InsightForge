"""Abstract base class for all tools.

A Tool has exactly one responsibility: given a ToolRequest, produce a
ToolResult. Tools must not:
    - Call the planner
    - Call the execution engine
    - Write to the database
    - Mutate the ToolRequest they receive

The interface is intentionally minimal. Future tools (Tavily, vector
retrieval, calculator) will each implement this single method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.tools.models import ToolRequest, ToolResult


class Tool(ABC):
    """Contract every tool implementation must satisfy."""

    @abstractmethod
    def execute(self, request: ToolRequest) -> ToolResult:
        """Process *request* and return a result.

        Args:
            request: Contains the task to execute and optional context.

        Returns:
            A ToolResult with the output and metadata for the task.

        Raises:
            ToolError: If the tool cannot complete the task.
        """
