"""Persistence operations for ResearchReport aggregates.

Maps between domain value objects (ResearchReport / ResearchSection) and ORM
models (ResearchReportModel / ResearchSectionModel). Callers never see ORM
types — only domain objects enter and leave this repository.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.research_report import ResearchReportModel, ResearchSectionModel
from app.reporting.models import ResearchReport, ResearchSection


def _section_to_model(
    section: ResearchSection,
    *,
    report_id: uuid.UUID,
    order_index: int,
) -> ResearchSectionModel:
    """Map a domain section to an ORM row."""
    return ResearchSectionModel(
        report_id=report_id,
        title=section.title,
        content=section.content,
        order_index=order_index,
    )


def _section_to_domain(model: ResearchSectionModel) -> ResearchSection:
    """Map an ORM section row to a domain section."""
    return ResearchSection(title=model.title, content=model.content)


def _report_to_model(report: ResearchReport) -> ResearchReportModel:
    """Map a domain report (with ordered sections) to an ORM aggregate."""
    return ResearchReportModel(
        id=report.report_id,
        session_id=report.session_id,
        title=report.title,
        summary=report.summary,
        generated_at=report.generated_at,
        sections=[
            _section_to_model(
                section,
                report_id=report.report_id,
                order_index=index,
            )
            for index, section in enumerate(report.sections)
        ],
    )


def _report_to_domain(model: ResearchReportModel) -> ResearchReport:
    """Map an ORM report aggregate to a domain ResearchReport."""
    ordered_sections = sorted(model.sections, key=lambda s: s.order_index)
    return ResearchReport(
        report_id=model.id,
        session_id=model.session_id,
        title=model.title,
        summary=model.summary,
        sections=[_section_to_domain(section) for section in ordered_sections],
        generated_at=model.generated_at,
    )


class ResearchReportRepository:
    """Data-access layer for research reports. No business rules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: ResearchReport) -> ResearchReport:
        """Persist a research report and its sections; return the domain report."""
        started_at = datetime.utcnow()
        log = logger.bind(
            report_id=str(report.report_id),
            session_id=str(report.session_id),
        )
        log.info("Saving report")

        model = _report_to_model(report)
        self._session.add(model)
        await self._session.flush()

        duration_ms = (datetime.utcnow() - started_at).total_seconds() * 1000
        log.bind(duration_ms=round(duration_ms, 2)).info("Report save completed")
        return report

    async def get_by_report_id(self, report_id: uuid.UUID) -> ResearchReport | None:
        """Return a report by primary key, or None if missing."""
        result = await self._session.execute(
            select(ResearchReportModel)
            .where(ResearchReportModel.id == report_id)
            .options(selectinload(ResearchReportModel.sections))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _report_to_domain(model)

    async def get_by_session_id(
        self,
        session_id: uuid.UUID,
    ) -> list[ResearchReport]:
        """Return all reports for a session, newest first."""
        result = await self._session.execute(
            select(ResearchReportModel)
            .where(ResearchReportModel.session_id == session_id)
            .options(selectinload(ResearchReportModel.sections))
            .order_by(ResearchReportModel.generated_at.desc())
        )
        return [_report_to_domain(model) for model in result.scalars().all()]
