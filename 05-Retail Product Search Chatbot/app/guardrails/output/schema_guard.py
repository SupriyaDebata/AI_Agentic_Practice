"""Output schema guard — validates the structured response against a Pydantic model.

The chatbot builds its response as a structured dict before rendering it.
This guard ensures the structure is complete and well-typed so malformed
output never reaches the user.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ValidationError, field_validator

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction


class ProductOutput(BaseModel):
    id: int
    product_name: str
    price: float
    kids_age: Optional[str] = None
    gender: Optional[str] = None
    size: Optional[str] = None
    colour: Optional[str] = None
    brand: Optional[str] = None
    stock: Optional[bool] = None

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class ProductSearchResponse(BaseModel):
    message: str
    products: List[ProductOutput] = []
    no_match: bool = False
    confidence: float = 1.0


def check_output_schema(data: Dict[str, Any]) -> GuardrailResult:
    """Validate *data* against ProductSearchResponse schema.

    Returns ALLOW on success, RETRY on validation failure.
    """
    try:
        ProductSearchResponse(**data)
        return GuardrailResult(
            passed=True,
            action=GuardAction.ALLOW,
            guardrail_name="SchemaGuard",
            reason="Output schema validation passed",
        )
    except ValidationError as exc:
        return GuardrailResult(
            passed=False,
            action=GuardAction.RETRY,
            guardrail_name="SchemaGuard",
            reason=f"Output schema validation failed: {exc.error_count()} error(s)",
            metadata={"errors": exc.errors()},
        )
    except Exception as exc:
        return GuardrailResult(
            passed=False,
            action=GuardAction.FALLBACK,
            guardrail_name="SchemaGuard",
            reason=f"Unexpected schema check error: {exc}",
        )
