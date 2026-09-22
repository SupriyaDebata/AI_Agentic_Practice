"""Logging configuration — human-readable console output for local use."""
from __future__ import annotations

import logging
import sys

import structlog

from app.config.settings import settings


def configure_logging() -> None:
    """Configure structlog with a readable console renderer. Call once at startup."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True, sort_keys=False),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(message)s",
        stream=sys.stdout,
    )

    # Suppress noisy third-party loggers
    for noisy in (
        "sentence_transformers",
        "transformers",          # kills the torchvision warnings flood
        "torch",
        "langchain",
        "sqlalchemy",
        "chromadb",
        "httpx",
        "httpcore",
    ):
        logging.getLogger(noisy).setLevel(logging.ERROR)


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
