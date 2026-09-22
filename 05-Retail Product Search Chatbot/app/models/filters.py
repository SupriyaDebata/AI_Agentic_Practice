"""
ProductFilter — structured hard constraints extracted from a user query.

These are enforced by SQL, never by LLM inference.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.product import GenderType


class ProductFilter(BaseModel):
    category: Optional[str] = None
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    size: Optional[str] = None
    colour: Optional[str] = None
    kids_age: Optional[str] = None
    gender: Optional[GenderType] = None
    brand: Optional[str] = None
    stock: Optional[bool] = None

    def gender_values(self) -> Optional[List[str]]:
        """
        Expand gender to include Unisex.

        Business rule: a query for 'Boy' should also return Unisex products.
        A query for 'Girl' should also return Unisex products.
        """
        if self.gender == "Boy":
            return ["Boy", "Unisex"]
        if self.gender == "Girl":
            return ["Girl", "Unisex"]
        if self.gender == "Unisex":
            return ["Unisex"]
        return None

    def has_any_filter(self) -> bool:
        return any(v is not None for v in self.model_dump().values())
