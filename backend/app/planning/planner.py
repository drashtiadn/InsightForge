"""Research planner abstractions and a deterministic default implementation."""

from __future__ import annotations

import re
import uuid
from abc import ABC, abstractmethod

from loguru import logger

from app.models.research_session import ResearchSession
from app.planning.models import ResearchPlan, ResearchTask


class ResearchPlanner(ABC):
    """Converts a research session into an executable plan.

    Implementations may be deterministic today and LLM-backed later.
    Planners must not perform HTTP, persistence, or workflow transitions.
    """

    @abstractmethod
    def create_plan(self, session: ResearchSession) -> ResearchPlan:
        """Build a research plan from the session's query and identity."""


class SimpleResearchPlanner(ResearchPlanner):
    """Deterministic planner used as the first AI-facing seam.

    No prompts, no LLM calls, no external APIs — only local heuristics so the
    architecture can be validated before real agent planning is introduced.
    """

    _COMPARISON_MARKERS = (
        "compare",
        "comparison",
        " vs ",
        " versus ",
        " vs. ",
    )
    _SPLIT_PATTERN = re.compile(
        r"\s+(?:and|vs\.?|versus|compared to|compared with)\s+",
        re.IGNORECASE,
    )
    _LEADING_NOISE = re.compile(
        r"^(?:compare|comparison of|compare between)\s+",
        re.IGNORECASE,
    )

    def create_plan(self, session: ResearchSession) -> ResearchPlan:
        """Derive a small, ordered task list from the session query."""
        query = session.query.strip()
        subjects = self._extract_subjects(query)
        tasks = self._build_tasks(query=query, subjects=subjects)

        plan = ResearchPlan(
            session_id=session.id,
            original_query=query,
            tasks=tasks,
        )

        logger.bind(
            session_id=str(session.id),
            task_count=len(plan.tasks),
        ).info("Plan generated")

        return plan

    def _extract_subjects(self, query: str) -> list[str]:
        """Pull comparison subjects when the query looks comparative."""
        normalized = f" {query.lower()} "
        if not any(marker in normalized for marker in self._COMPARISON_MARKERS):
            return []

        cleaned = self._LEADING_NOISE.sub("", query).strip()
        parts = [
            part.strip(" ?.,;:\"'")
            for part in self._SPLIT_PATTERN.split(cleaned)
            if part.strip(" ?.,;:\"'")
        ]
        # Keep only short subject labels so noisy sentences do not explode.
        return [part for part in parts if 0 < len(part.split()) <= 4][:4]

    def _build_tasks(
        self,
        *,
        query: str,
        subjects: list[str],
    ) -> list[ResearchTask]:
        """Assemble understand / compare / summarize steps."""
        tasks: list[ResearchTask] = []

        if subjects:
            for subject in subjects:
                tasks.append(
                    self._task(
                        title=f"Understand {subject}",
                        description=(
                            f"Gather core concepts, strengths, and limitations "
                            f"of {subject} relevant to: {query}"
                        ),
                    )
                )
            if len(subjects) >= 2:
                joined = " and ".join(subjects)
                tasks.append(
                    self._task(
                        title="Compare features",
                        description=(
                            f"Compare {joined} across features, trade-offs, "
                            f"and suitability for the original request."
                        ),
                    )
                )
        else:
            tasks.append(
                self._task(
                    title="Investigate the topic",
                    description=(
                        f"Research the key concepts, sources, and facts needed "
                        f"to answer: {query}"
                    ),
                )
            )

        tasks.append(
            self._task(
                title="Summarize findings",
                description=(
                    "Synthesize the research into clear conclusions that "
                    f"address: {query}"
                ),
            )
        )
        return tasks

    @staticmethod
    def _task(*, title: str, description: str) -> ResearchTask:
        return ResearchTask(
            id=uuid.uuid4(),
            title=title,
            description=description,
        )
