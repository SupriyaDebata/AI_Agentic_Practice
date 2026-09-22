"""Application initialization — call initialize_app() once at startup."""
from __future__ import annotations

import sys

from app.config import configure_logging, get_logger, settings
from app.repositories.sql_repository import create_tables

logger = get_logger(__name__)


def initialize_app() -> None:
    # 1. Logging first — all subsequent output uses ConsoleRenderer
    configure_logging()

    logger.info("app_startup", ollama_model=settings.ollama_model, log_level=settings.log_level)

    # 2. Ensure data directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)

    if not settings.products_xlsx.exists():
        logger.error("products_xlsx_missing", path=str(settings.products_xlsx),
                     hint="Run: python scripts/create_dataset.py")
        sys.exit(1)

    # 3. Create SQLite schema (idempotent)
    try:
        create_tables()
        logger.info("db_ready", path=settings.db_path)
    except Exception as e:
        logger.error("db_init_failed", error=str(e))
        sys.exit(1)

    logger.info("app_ready")


if __name__ == "__main__":
    initialize_app()
