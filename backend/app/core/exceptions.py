"""Global exception handlers that return a consistent JSON error envelope."""

from __future__ import annotations

from typing import Any, Final

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.middleware import get_request_id


ERROR_KEY_SUCCESS: Final[str] = "success"
ERROR_KEY_ERROR: Final[str] = "error"
ERROR_KEY_TYPE: Final[str] = "type"
ERROR_KEY_MESSAGE: Final[str] = "message"
ERROR_KEY_REQUEST_ID: Final[str] = "request_id"

ERROR_TYPE_HTTP: Final[str] = "http_error"
ERROR_TYPE_VALIDATION: Final[str] = "validation_error"
ERROR_TYPE_INTERNAL: Final[str] = "internal_server_error"

DEFAULT_INTERNAL_MESSAGE: Final[str] = "An unexpected error occurred."
DEFAULT_VALIDATION_MESSAGE: Final[str] = "Request validation failed."


def _resolve_request_id(request: Request) -> str:
    """Resolve the correlation ID from request state or context."""
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return get_request_id()


def _error_payload(*, error_type: str, message: str, request_id: str) -> dict[str, Any]:
    """Build the standard error response body."""
    return {
        ERROR_KEY_SUCCESS: False,
        ERROR_KEY_ERROR: {
            ERROR_KEY_TYPE: error_type,
            ERROR_KEY_MESSAGE: message,
            ERROR_KEY_REQUEST_ID: request_id,
        },
    }


def _http_exception_message(exc: StarletteHTTPException) -> str:
    """Normalize an HTTPException detail into a single string message."""
    detail = exc.detail
    if isinstance(detail, str):
        return detail
    return str(detail)


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle FastAPI/Starlette HTTPException with a consistent envelope."""
    request_id = _resolve_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            error_type=ERROR_TYPE_HTTP,
            message=_http_exception_message(exc),
            request_id=request_id,
        ),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle request body/query validation failures."""
    request_id = _resolve_request_id(request)
    logger.bind(request_id=request_id, errors=exc.errors()).warning(
        "Request validation failed for {method} {path}",
        method=request.method,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_payload(
            error_type=ERROR_TYPE_VALIDATION,
            message=DEFAULT_VALIDATION_MESSAGE,
            request_id=request_id,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions without exposing internal details."""
    request_id = _resolve_request_id(request)
    logger.bind(request_id=request_id).exception(
        "Unhandled exception for {method} {path}: {error}",
        method=request.method,
        path=request.url.path,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_payload(
            error_type=ERROR_TYPE_INTERNAL,
            message=DEFAULT_INTERNAL_MESSAGE,
            request_id=request_id,
        ),
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI application."""
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
