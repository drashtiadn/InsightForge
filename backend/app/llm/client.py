"""LLM client abstraction and Gemini provider implementation."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx
from google import genai
from google.genai import errors, types
from loguru import logger

from app.llm.models import LLMMessage, LLMRequest, LLMResponse


class LLMClientError(Exception):
    """Base error for LLM transport failures."""


class LLMConnectionError(LLMClientError):
    """Raised when the provider cannot be reached."""


class LLMResponseError(LLMClientError):
    """Raised when the provider returns an unusable response."""


class LLMClient(ABC):
    """Isolates provider-specific SDK calls from planners and services."""

    @abstractmethod
    def complete_json(self, request: LLMRequest) -> LLMResponse:
        """Request a JSON object matching the supplied schema."""


class GeminiLLMClient(LLMClient):
    """Google Gemini client with JSON-schema structured output."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise LLMConnectionError("Gemini API key is not configured")
        self._client = genai.Client(api_key=api_key)

    def complete_json(self, request: LLMRequest) -> LLMResponse:
        """Call Gemini and return parsed JSON from the model response."""
        system_instruction: str | None = None
        user_content = ""

        for message in request.messages:
            if message.role == "system":
                system_instruction = message.content
            elif message.role == "user":
                user_content = message.content

        config = types.GenerateContentConfig(
            temperature=request.temperature,
            response_mime_type="application/json",
            response_json_schema=request.json_schema,
        )
        if system_instruction is not None:
            config.system_instruction = system_instruction

        try:
            response = self._client.models.generate_content(
                model=request.model,
                contents=user_content,
                config=config,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.bind(provider="gemini").warning("LLM connection failed")
            raise LLMConnectionError(str(exc)) from exc
        except errors.ClientError as exc:
            logger.bind(
                provider="gemini",
                status_code=exc.code,
            ).warning("LLM provider returned a client error")
            raise LLMResponseError(str(exc)) from exc
        except errors.ServerError as exc:
            logger.bind(
                provider="gemini",
                status_code=exc.code,
            ).warning("LLM provider returned a server error")
            raise LLMResponseError(str(exc)) from exc
        except errors.APIError as exc:
            logger.bind(provider="gemini").warning("LLM provider request failed")
            raise LLMClientError(str(exc)) from exc

        content = response.text
        if not content:
            raise LLMResponseError("LLM returned an empty response")

        try:
            data: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMResponseError("LLM response was not valid JSON") from exc

        return LLMResponse(data=data)
