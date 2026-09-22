"""
app/config/__init__.py

Exports the main configuration entry points.
"""
from app.config.settings import settings
from app.config.logging_config import configure_logging, get_logger

__all__ = [
    "settings",
    "configure_logging",
    "get_logger",
]
