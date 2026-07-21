"""Loguru-based logging configuration for the API process."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Final

from loguru import logger

from app.core.config import settings


LOG_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

INTERCEPTED_LOGGERS: Final[tuple[str, ...]] = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "fastapi",
)

_LOGGING_DIR: Final[Path] = Path(logging.__file__).resolve().parent


def _is_logging_frame(filename: str) -> bool:
    """Return True when the frame originates inside the stdlib logging package."""
    try:
        return _LOGGING_DIR in Path(filename).resolve().parents or Path(filename).resolve() == Path(
            logging.__file__
        ).resolve()
    except OSError:
        return "logging" in filename.replace("\\", "/")


class InterceptHandler(logging.Handler):
    """Redirect standard-library logging records into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Forward a stdlib log record to Loguru at the correct depth."""
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame is not None and _is_logging_frame(frame.f_code.co_filename):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _intercept_standard_logging() -> None:
    """Replace root and known framework handlers with the InterceptHandler."""
    intercept_handler = InterceptHandler()
    logging.root.handlers = [intercept_handler]
    logging.root.setLevel(settings.log_level.upper())

    for logger_name in INTERCEPTED_LOGGERS:
        named_logger = logging.getLogger(logger_name)
        named_logger.handlers = [intercept_handler]
        named_logger.propagate = False


def configure_logging() -> None:
    """Configure console logging via Loguru and intercept stdlib loggers."""
    logger.remove()

    if settings.log_json:
        logger.add(
            sys.stderr,
            level=settings.log_level.upper(),
            serialize=True,
            enqueue=True,
            backtrace=settings.environment != "production",
            diagnose=settings.environment != "production",
        )
    else:
        logger.add(
            sys.stderr,
            level=settings.log_level.upper(),
            format=LOG_FORMAT,
            enqueue=True,
            backtrace=settings.environment != "production",
            diagnose=settings.environment != "production",
        )

    _intercept_standard_logging()
