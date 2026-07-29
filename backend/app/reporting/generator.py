"""Report generator abstractions and the deterministic default implementation.

Architecture:
    ReportGenerator (ABC)     — the stable contract for all generators
    SimpleReportGenerator     — deterministic mapping; no LLM synthesis

Responsibility split:
    ExecutionEngine  — produces independent task results
    ReportGenerator  — synthesizes those results into one ResearchReport

The service injects a ReportGenerator at construction time. Generators must
not call the planner, execution engine, tools, or persistence layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from loguru import logger

from app.execution.models import ResearchExecutionResult
from app.reporting.models import ResearchReport, ResearchSection


class ReportGenerator(ABC):
    """Abstract contract every report generator must satisfy.

    Accepts a ResearchExecutionResult and returns a ResearchReport.
    Implementations decide *how* synthesis happens; callers decide *when*.
    """

    @abstractmethod
    def generate(self, execution_result: ResearchExecutionResult) -> ResearchReport:
        """Transform *execution_result* into a coherent research report."""


class SimpleReportGenerator(ReportGenerator):
    """Deterministic generator used before LLM-backed synthesis exists.

    Behaviour:
        title    — the original research query
        summary  — a brief introduction naming the task count
        sections — one ResearchSection per executed task (title + output)

    No prompts. No LLM calls. No external I/O.
    """

    def generate(self, execution_result: ResearchExecutionResult) -> ResearchReport:
        """Map each task result into a report section and assemble the report."""
        started_at = datetime.utcnow()
        section_count = len(execution_result.task_results)

        log = logger.bind(
            session_id=str(execution_result.session_id),
            section_count=section_count,
        )
        log.info("Report generation started")

        query = execution_result.plan.original_query
        sections = [
            ResearchSection(title=result.title, content=result.output)
            for result in execution_result.task_results
        ]

        report = ResearchReport(
            session_id=execution_result.session_id,
            title=query,
            summary=(
                f"This report consolidates findings from {section_count} "
                f"research task(s) addressing: {query}"
            ),
            sections=sections,
            generated_at=datetime.utcnow(),
        )

        duration_ms = (datetime.utcnow() - started_at).total_seconds() * 1000
        log.bind(
            section_count=len(report.sections),
            duration_ms=round(duration_ms, 2),
        ).info("Report generation completed")

        return report
