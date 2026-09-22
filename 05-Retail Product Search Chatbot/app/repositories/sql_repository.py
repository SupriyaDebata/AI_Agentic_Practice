"""
SQL repository for the product catalog.

Design decisions
----------------
1. LLM → ProductFilter → SQLAlchemy (never LLM → raw SQL)
   The LLM extracts structured filters; this class translates them to
   parameterized queries.  No arbitrary SQL ever enters from outside.

2. Indexes on category, price, colour, kids_age, gender, brand, stock
   These are the fields users filter on most.  SQLite uses B-tree indexes,
   so range queries on price and equality checks on gender/colour are fast.

3. kids_age stored as VARCHAR (e.g. "7-8")
   The catalog uses human-readable age bands, not integer ranges.
   Filtering is by exact match on the band string.  If we need range
   queries later (age >= 5) we'd add age_min/age_max integer columns.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Float, Integer, String,
    create_engine,
)
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import settings
from app.models.filters import ProductFilter
from app.models.product import Product


# ── ORM definition ────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class ProductRow(Base):
    """SQLAlchemy ORM model — maps to the 'products' table."""
    __tablename__ = "products"

    id         = Column(Integer, primary_key=True)
    category   = Column(String, nullable=False, index=True)
    product_name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price      = Column(Float, nullable=False, index=True)
    size       = Column(String, nullable=False)
    colour     = Column(String, nullable=False, index=True)
    kids_age   = Column(String, nullable=False, index=True)
    gender     = Column(String, nullable=False, index=True)
    brand      = Column(String, nullable=False, index=True)
    stock      = Column(Boolean, nullable=False, index=True)


# ── Engine / session factory ──────────────────────────────────────────────────

def _make_engine(db_url: Optional[str] = None):
    db_file = Path(db_url if db_url else settings.db_path).resolve()
    # Use URL.create to bypass string parsing — handles Windows backslash paths
    url = URL.create("sqlite", database=str(db_file))
    return create_engine(url, connect_args={"check_same_thread": False})


def create_tables(engine=None) -> None:
    """Create the products table (idempotent)."""
    eng = engine or _make_engine()
    Base.metadata.create_all(eng)


# ── Repository ────────────────────────────────────────────────────────────────

class SQLProductRepository:
    """
    Translates ProductFilter → parameterized SQL via SQLAlchemy.

    Never accepts raw SQL strings from external callers.
    """

    def __init__(self, db_url: Optional[str] = None):
        self._engine = _make_engine(db_url)
        self._Session = sessionmaker(bind=self._engine)

    # ── Write ──────────────────────────────────────────────────────────────

    def bulk_insert(self, products: List[Product]) -> None:
        """Insert a list of Product objects, replacing any existing rows."""
        with self._Session() as session:
            session.query(ProductRow).delete()
            for p in products:
                session.add(ProductRow(**p.model_dump()))
            session.commit()

    # ── Read ───────────────────────────────────────────────────────────────

    def filter(
        self,
        filters: ProductFilter,
        top_k: int = 50,
    ) -> List[Product]:
        """
        Apply hard constraints and return matching products.

        All predicates are constructed by SQLAlchemy — no string
        interpolation, no LLM-generated SQL.
        """
        with self._Session() as session:
            q = session.query(ProductRow)

            if filters.category:
                q = q.filter(ProductRow.category == filters.category)

            if filters.price_min is not None:
                q = q.filter(ProductRow.price >= filters.price_min)

            if filters.price_max is not None:
                q = q.filter(ProductRow.price <= filters.price_max)


            if filters.size:
                q = q.filter(ProductRow.size == filters.size)

            if filters.colour:
                q = q.filter(ProductRow.colour == filters.colour)

            if filters.kids_age:
                q = q.filter(ProductRow.kids_age == filters.kids_age)

            # Gender: Boy → ['Boy','Unisex'], Girl → ['Girl','Unisex']
            gender_values = filters.gender_values()
            if gender_values:
                q = q.filter(ProductRow.gender.in_(gender_values))

            if filters.brand:
                q = q.filter(ProductRow.brand == filters.brand)

            if filters.stock is not None:
                q = q.filter(ProductRow.stock == filters.stock)

            rows = q.limit(top_k).all()
            return [Product.model_validate(row) for row in rows]

    def get_all(self, top_k: int = 200) -> List[Product]:
        with self._Session() as session:
            rows = session.query(ProductRow).limit(top_k).all()
            return [Product.model_validate(row) for row in rows]

