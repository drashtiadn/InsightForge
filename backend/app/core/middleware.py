"""ASGI middleware components for the InsightForge API."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Final

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
REQUEST_DURATION_PRECISION: Final[int] = 4

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the request ID bound to the current context, if any."""
    return request_id_ctx.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID, measure duration, and emit structured access logs."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware with the wrapped ASGI application."""
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process one request with correlation ID and timing metadata."""
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id

        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            duration = round(time.perf_counter() - started_at, REQUEST_DURATION_PRECISION)
            logger.bind(
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration=duration,
                request_id=request_id,
            ).info(
                "{method} {path} -> {status} ({duration}s) request_id={request_id}",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration=duration,
                request_id=request_id,
            )
            request_id_ctx.reset(token)
