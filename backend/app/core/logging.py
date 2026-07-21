"""Loguru configuration for the API process."""

import sys

from loguru import logger

from app.core.config import settings


def configure_logging() -> None:
    """Replace Loguru's default handler with the application's configured sink."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        serialize=settings.log_json,
        backtrace=settings.environment != "production",
        diagnose=settings.environment != "production",
    )
