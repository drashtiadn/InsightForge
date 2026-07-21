"""Request ID and access-logging middleware."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


REQUEST_ID_HEADER = "X-Request-ID"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Assign a request ID, measure duration, and log each request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            duration = round(time.perf_counter() - started_at, 4)
            logger.info(
                "{method} {path} -> {status} ({duration}s) request_id={request_id}",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration=duration,
                request_id=request_id,
            )
