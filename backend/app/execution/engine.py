"""Execution engine abstractions and the default sequential implementation.

Architecture:
    ExecutionEngine (ABC)          — the stable contract for all engines
    ResearchExecutionEngine        — deterministic, sequential, placeholder output

Future engines (not implemented here):
    SequentialExecutionEngine      — same as current, with real tool calls
    ParallelExecutionEngine        — asyncio.gather across tasks
    DistributedExecutionEngine     — distributes tasks to worker queues

Engines must not:
    - Perform HTTP requests
    - Write to the database
    - Mutate the ResearchPlan they receive
    - Call the planner
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from loguru import logger

from app.execution.models import ResearchExecutionResult, ResearchTaskResult
from app.planning.models import ResearchPlan


class ExecutionEngine(ABC):
    """Abstract contract every execution engine must satisfy.

    Accepts a ResearchPlan and returns a ResearchExecutionResult.
    Implementations decide *how* tasks are executed; callers decide *when*.
    """

    @abstractmethod
    def execute(self, plan: ResearchPlan) -> ResearchExecutionResult:
        """Execute all tasks in *plan* and return the aggregated result."""


class ResearchExecutionEngine(ExecutionEngine):
    """Deterministic sequential engine.

    Executes every task in plan order, producing a placeholder output for each.
    No external I/O. No concurrency. Purpose: validate orchestration end-to-end
    before real agents, tool calls, or LLM completions are introduced.
    """

    def execute(self, plan: ResearchPlan) -> ResearchExecutionResult:
        """Run all tasks sequentially and collect their results."""
        started_at = datetime.utcnow()

        log = logger.bind(
            session_id=str(plan.session_id),
            task_count=len(plan.tasks),
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

            output = f"Execution placeholder for task: {task.title}"
            completed_at = datetime.utcnow()

            task_results.append(
                ResearchTaskResult(
                    task_id=task.id,
                    title=task.title,
                    output=output,
                    completed_at=completed_at,
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
