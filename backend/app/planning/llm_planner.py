"""LLM-backed research planner using structured JSON output."""

from __future__ import annotations

import time
import uuid

from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from app.llm.client import (
    LLMClient,
    LLMClientError,
    LLMConnectionError,
    LLMResponseError,
)
from app.llm.models import LLMMessage, LLMRequest
from app.models.research_session import ResearchSession
from app.planning.exceptions import (
    InvalidPlannerResponse,
    LLMUnavailable,
    PlanningFailed,
)
from app.planning.models import ResearchPlan, ResearchTask
from app.planning.planner import ResearchPlanner


PLANNING_SYSTEM_PROMPT = (
    "You are a research planning assistant for InsightForge. "
    "Your job is to decompose a research question into a logical sequence "
    "of research tasks. You plan research — you do not perform it. "
    "Do not search the web, cite sources, or write final reports. "
    "Return only structured JSON matching the provided schema."
)

PLANNING_USER_PROMPT = (
    "Create a research plan for the following question.\n\n"
    "Research question: {query}\n\n"
    "Requirements:\n"
    "- Understand the question and its scope\n"
    "- Break the problem into logical, ordered research tasks\n"
    "- Each task must have a short title and a clear description\n"
    "- Include 3 to 6 tasks\n"
    "- End with a synthesis or summary task\n"
    "- Return JSON only"
)


class _PlanTaskSchema(BaseModel):
    """Expected shape of each task in the LLM JSON response."""

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class _PlanSchema(BaseModel):
    """Expected top-level JSON shape returned by the LLM."""

    tasks: list[_PlanTaskSchema] = Field(min_length=1)


class LLMResearchPlanner(ResearchPlanner):
    """Generates research plans by delegating decomposition to an LLM.

    Prompt engineering lives here. Provider SDK calls live in LLMClient.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        *,
        model: str,
        temperature: float,
    ) -> None:
        self._llm_client = llm_client
        self._model = model
        self._temperature = temperature

    def create_plan(self, session: ResearchSession) -> ResearchPlan:
        """Ask the LLM to produce a structured plan for the session query."""
        query = session.query.strip()
        session_id = str(session.id)

        logger.bind(session_id=session_id).info("Planning started")
        started_at = time.perf_counter()

        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=PLANNING_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=PLANNING_USER_PROMPT.format(query=query),
                ),
            ],
            model=self._model,
            temperature=self._temperature,
            json_schema=_PlanSchema.model_json_schema(),
            schema_name="research_plan",
        )

        try:
            response = self._llm_client.complete_json(request)
        except LLMConnectionError as exc:
            raise LLMUnavailable(str(exc)) from exc
        except LLMResponseError as exc:
            raise InvalidPlannerResponse(str(exc)) from exc
        except LLMClientError as exc:
            raise PlanningFailed(str(exc)) from exc

        try:
            parsed = _PlanSchema.model_validate(response.data)
        except ValidationError as exc:
            raise InvalidPlannerResponse("LLM response failed schema validation") from exc

        tasks = [
            ResearchTask(
                id=uuid.uuid4(),
                title=task.title.strip(),
                description=task.description.strip(),
            )
            for task in parsed.tasks
        ]

        plan = ResearchPlan(
            session_id=session.id,
            original_query=query,
            tasks=tasks,
        )

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.bind(
            session_id=session_id,
            task_count=len(plan.tasks),
            duration_ms=duration_ms,
        ).info("Planning completed")

        return plan
