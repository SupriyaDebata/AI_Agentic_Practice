"""
scripts/ingest.py

Load products.xlsx → validate → insert into SQLite catalog.db

Usage:
    python scripts/ingest.py

This script:
1. Initializes logging and database schema
2. Loads products from data/products.xlsx
3. Validates each row against the Product Pydantic model
4. Inserts valid products into SQLite catalog.db
5. Reports statistics on success/failure
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import configure_logging, get_logger, settings
from app.ingestion.excel_loader import load_products
from app.repositories.sql_repository import SQLProductRepository, create_tables


logger = get_logger(__name__)


def main() -> None:
    # Initialize logging
    configure_logging()
    
    logger.info(
        "starting product ingestion",
        db_path=settings.db_path,
        xlsx_path=str(settings.products_xlsx),
    )

    # Ensure schema exists
    try:
        create_tables()
        logger.info("database schema created/verified")
    except Exception as e:
        logger.error("failed to create database schema", error=str(e))
        sys.exit(1)

    # Load and validate products
    try:
        products = load_products(settings.products_xlsx)
        logger.info("products loaded and validated", count=len(products))
    except Exception as e:
        logger.error("failed to load products", error=str(e))
        sys.exit(1)

    # Insert into DB
    try:
        repo = SQLProductRepository()
        repo.bulk_insert(products)
        logger.info(
            "ingestion complete",
            inserted=len(products),
            db_path=settings.db_path,
        )
    except Exception as e:
        logger.error("failed to insert products into database", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
