"""Global exception handlers with a consistent JSON error envelope."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "") or ""


def _error_body(*, error_type: str, message: str, request_id: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": {
            "type": error_type,
            "message": message,
            "request_id": request_id,
        },
    }


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(
            error_type="http_error",
            message=detail,
            request_id=_request_id(request),
        ),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id = _request_id(request)
    logger.bind(request_id=request_id, errors=exc.errors()).warning(
        "Request validation failed for {method} {path}",
        method=request.method,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            error_type="validation_error",
            message="Request validation failed.",
            request_id=request_id,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = _request_id(request)
    logger.bind(request_id=request_id).exception(
        "Unhandled exception for {method} {path}: {error}",
        method=request.method,
        path=request.url.path,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            error_type="internal_server_error",
            message="An unexpected error occurred.",
            request_id=request_id,
        ),
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Attach global exception handlers to the application."""
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
