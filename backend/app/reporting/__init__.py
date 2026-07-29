"""Reporting layer — transforms execution results into research reports.

The reporting layer sits after the execution engine and before any future
export or presentation concerns. It synthesizes independent task outputs
into one coherent ResearchReport.

Exports:
    ReportGenerator       — abstract base class all generators must implement
    SimpleReportGenerator — deterministic implementation used before LLM reports
    ResearchReport        — immutable aggregate report value object
    ResearchSection       — immutable section within a report
    ReportGenerationError — base exception for reporting failures
"""

from app.reporting.exceptions import ReportGenerationError
from app.reporting.generator import ReportGenerator, SimpleReportGenerator
from app.reporting.models import ResearchReport, ResearchSection

__all__ = [
    "ReportGenerationError",
    "ReportGenerator",
    "SimpleReportGenerator",
    "ResearchReport",
    "ResearchSection",
]
