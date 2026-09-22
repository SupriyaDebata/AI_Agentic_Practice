"""
Core Product domain model.

Represents a single row in the catalog — the authoritative shape shared by
ingestion, the SQL ORM, BM25 indexing, and response serialization.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Controlled vocabulary for gender.
# "Unisex" is intentionally separate — routing logic expands it when needed.
GenderType = Literal["Boy", "Girl", "Unisex"]


class Product(BaseModel):
    """A single kids'-clothing product."""

    id: int = Field(..., description="Surrogate primary key")
    category: str = Field(..., description="Top-level category, e.g. Dress, T-Shirt")
    product_name: str
    description: str
    price: float = Field(..., gt=0, description="Price in INR, no currency symbol")
    size: str = Field(..., description="Size label, e.g. 3-4Y, 5-6Y")
    colour: str
    kids_age: str = Field(
        ...,
        description="Age range the product targets, e.g. '7-8' (years)",
    )
    gender: GenderType
    brand: str
    stock: bool = Field(..., description="True = in stock")

    @field_validator("price")
    @classmethod
    def round_price(cls, v: float) -> float:
        return round(v, 2)

    def searchable_text(self) -> str:
        """
        Concatenated text used for BM25 indexing.

        Includes product_name and description.  Structured attributes
        (colour, brand, category) are *not* added here — hard constraints
        are enforced by SQL, not BM25 scoring.
        """
        return f"{self.product_name} {self.description}"

    def to_embedding_text(self) -> str:
        """
        Text passed to the embedding model for vector indexing.

        Description carries the most semantic content; product_name anchors
        the category/style.  We avoid embedding price/size/colour because
        those are hard constraints enforced elsewhere.
        """
        return f"{self.product_name}. {self.description}"

    model_config = ConfigDict(from_attributes=True)
