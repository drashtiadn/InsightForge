"""TavilySearchTool — first production Tool implementation.

Calls the Tavily Search API for a research task and returns a ToolResult.
HTTP, authentication, and response parsing stay inside this module so the
execution engine never depends on Tavily specifics.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import httpx
from loguru import logger

from app.tools.base import Tool
from app.tools.exceptions import ToolError
from app.tools.models import ToolRequest, ToolResult

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_MAX_RESULTS = 5


class TavilySearchTool(Tool):
    """Web-search tool backed by the Tavily Search API.

    Args:
        api_key: Tavily API key from application settings.
        timeout: HTTP request timeout in seconds.
        max_results: Maximum number of search hits to request.
    """

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        max_results: int = _DEFAULT_MAX_RESULTS,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._max_results = max_results

    def execute(self, request: ToolRequest) -> ToolResult:
        """Search the web for *request.task.title* and return a ToolResult."""
        task = request.task
        query = task.title

        tool_log = logger.bind(
            tool=self.__class__.__name__,
            task_id=str(task.id),
            task_title=task.title,
            query=query,
        )
        tool_log.info("Search started")

        if not self._api_key:
            tool_log.error("Search failed: API key is not configured")
            raise ToolError(
                task_id=task.id,
                reason="Tavily API key is not configured",
            )

        started_at = datetime.utcnow()

        try:
            raw = self._search(query, task_id=task.id)
        except ToolError as exc:
            tool_log.bind(error=exc.reason).error("Search failed")
            raise

        sources = self._extract_sources(raw)
        output = self._build_summary(raw, sources)
        search_time = raw.get("response_time")
        completed_at = datetime.utcnow()
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        tool_log.bind(
            duration_ms=round(duration_ms, 2),
            result_count=len(sources),
        ).info("Search completed")

        return ToolResult(
            task_id=task.id,
            output=output,
            metadata={
                "query": query,
                "search_time": search_time,
                "urls": [source["url"] for source in sources],
                "titles": [source["title"] for source in sources],
            },
            completed_at=completed_at,
        )

    def _search(self, query: str, *, task_id: uuid.UUID) -> dict[str, Any]:
        """Call the Tavily Search API and return the parsed JSON body.

        Raises:
            ToolError: On HTTP, timeout, authentication, or invalid responses.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        payload = {
            "query": query,
            "max_results": self._max_results,
            "include_answer": True,
            "search_depth": "basic",
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    _TAVILY_SEARCH_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise ToolError(
                task_id=task_id,
                reason=f"Search request timed out: {exc}",
            ) from exc
        except httpx.RequestError as exc:
            raise ToolError(
                task_id=task_id,
                reason=f"Search request failed: {exc}",
            ) from exc

        if response.status_code in {401, 403}:
            raise ToolError(
                task_id=task_id,
                reason="Search authentication failed",
            )

        if response.status_code >= 400:
            raise ToolError(
                task_id=task_id,
                reason=f"Search HTTP error: status {response.status_code}",
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ToolError(
                task_id=task_id,
                reason="Search returned invalid JSON",
            ) from exc

        if not isinstance(data, dict):
            raise ToolError(
                task_id=task_id,
                reason="Search returned an unexpected response shape",
            )

        if "results" not in data or not isinstance(data["results"], list):
            raise ToolError(
                task_id=task_id,
                reason="Search response missing results",
            )

        return data

    def _extract_sources(self, raw: dict[str, Any]) -> list[dict[str, str]]:
        """Map provider results to generic title/url pairs."""
        sources: list[dict[str, str]] = []
        for item in raw.get("results", []):
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            url = item.get("url")
            if isinstance(title, str) and isinstance(url, str) and title and url:
                sources.append({"title": title, "url": url})
        return sources

    def _build_summary(
        self,
        raw: dict[str, Any],
        sources: list[dict[str, str]],
    ) -> str:
        """Build a short research summary without generating a full report."""
        answer = raw.get("answer")
        if isinstance(answer, str) and answer.strip():
            return answer.strip()

        snippets: list[str] = []
        for item in raw.get("results", []):
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                snippets.append(content.strip())
            if len(snippets) >= 3:
                break

        if snippets:
            return " ".join(snippets)

        if sources:
            titles = "; ".join(source["title"] for source in sources[:3])
            return f"Found {len(sources)} sources: {titles}"

        return "No search results found."
