"""Transport models for LLM client requests and responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """A single chat message sent to an LLM provider."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Provider-agnostic structured completion request."""

    messages: list[LLMMessage]
    model: str
    temperature: float
    json_schema: dict[str, Any] = field(default_factory=dict)
    schema_name: str = "response"


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Parsed JSON payload returned by a structured completion."""

    data: dict[str, Any]
