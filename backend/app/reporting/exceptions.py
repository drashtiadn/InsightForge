"""Reporting-layer exceptions.

Kept separate so callers can catch report-generation failures without
importing generator internals. Future generators may introduce subclasses.
"""

from __future__ import annotations


class ReportGenerationError(Exception):
    """Base class for all reporting-layer failures."""
