"""Loguru logging setup for the API process."""

from __future__ import annotations

import logging
import sys

from loguru import logger

from app.core.config import settings


LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    """Forward standard-library logging records to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging() -> None:
    """Configure console logging and intercept stdlib / Uvicorn loggers."""
    logger.remove()

    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format=LOG_FORMAT,
        serialize=settings.log_json,
        enqueue=True,
        backtrace=settings.environment != "production",
        diagnose=settings.environment != "production",
    )

    intercept_handler = InterceptHandler()
    logging.root.handlers = [intercept_handler]
    logging.root.setLevel(settings.log_level.upper())

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers = [intercept_handler]
        lib_logger.propagate = False
