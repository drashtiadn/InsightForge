"""Execution engine abstractions and the default sequential implementation.

Architecture:
    ExecutionEngine (ABC)          — the stable contract for all engines
    ResearchExecutionEngine        — sequential engine; delegates to a Tool

Responsibility split:
    ExecutionEngine  — decides *when* and *in what order* tasks run
    Tool             — decides *how* each task is completed

The engine depends only on the Tool abstraction, never on a concrete tool.
Callers inject the tool at construction time (dependency injection).

Future engines (not implemented here):
    ParallelExecutionEngine        — asyncio.gather across tasks
    DistributedExecutionEngine     — distributes tasks to worker queues
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from loguru import logger

from app.execution.exceptions import TaskExecutionError
from app.execution.models import ResearchExecutionResult, ResearchTaskResult
from app.planning.models import ResearchPlan
from app.tools.base import Tool
from app.tools.exceptions import ToolError
from app.tools.models import ToolRequest


class ExecutionEngine(ABC):
    """Abstract contract every execution engine must satisfy.

    Accepts a ResearchPlan and returns a ResearchExecutionResult.
    Implementations decide *how* tasks are executed; callers decide *when*.
    """

    @abstractmethod
    def execute(self, plan: ResearchPlan) -> ResearchExecutionResult:
        """Execute all tasks in *plan* and return the aggregated result."""


class ResearchExecutionEngine(ExecutionEngine):
    """Sequential engine that delegates each task to an injected Tool.

    The engine orchestrates: it sequences tasks, records timing, aggregates
    results, and converts ToolErrors into TaskExecutionErrors.

    The tool works: it produces the output for each individual task.

    Args:
        tool: The Tool implementation to invoke for every task. Must be
              supplied by the caller — the engine never instantiates tools.
    """

    def __init__(self, tool: Tool) -> None:
        self._tool = tool

    def execute(self, plan: ResearchPlan) -> ResearchExecutionResult:
        """Run all tasks sequentially via the injected tool and collect results."""
        started_at = datetime.utcnow()

        log = logger.bind(
            session_id=str(plan.session_id),
            task_count=len(plan.tasks),
            tool=self._tool.__class__.__name__,
        )
        log.info("Execution started")

        task_results: list[ResearchTaskResult] = []

        for task in plan.tasks:
            task_log = logger.bind(
                session_id=str(plan.session_id),
                task_id=str(task.id),
                task_title=task.title,
            )
            task_log.info("Task execution started")

            try:
                tool_result = self._tool.execute(ToolRequest(task=task))
            except ToolError as exc:
                raise TaskExecutionError(
                    task_id=str(task.id),
                    title=task.title,
                    reason=exc.reason,
                ) from exc

            task_results.append(
                ResearchTaskResult(
                    task_id=task.id,
                    title=task.title,
                    output=tool_result.output,
                    completed_at=tool_result.completed_at,
                )
            )

            task_log.info("Task execution completed")

        completed_at = datetime.utcnow()
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        logger.bind(
            session_id=str(plan.session_id),
            task_count=len(task_results),
            duration_ms=round(duration_ms, 2),
        ).info("Execution completed")

        return ResearchExecutionResult(
            session_id=plan.session_id,
            plan=plan,
            task_results=task_results,
            started_at=started_at,
            completed_at=completed_at,
        )
