"""
Validate raw rows from products.xlsx against the Product Pydantic model.

Returns (valid_products, errors) so the caller can decide whether to abort
or proceed with partial data.
"""
from __future__ import annotations

from typing import List, Tuple

import pandas as pd
from pydantic import ValidationError

from app.models.product import Product


def validate_dataframe(
    df: pd.DataFrame,
) -> Tuple[List[Product], List[dict]]:
    """
    Validate every row.  Returns (valid list, error list).

    Errors include the row index and the validation messages so they can
    be logged or surfaced in a report.
    """
    valid: List[Product] = []
    errors: List[dict] = []

    for idx, row in df.iterrows():
        raw = row.to_dict()
        # Excel may load booleans as 0/1 integers
        if "stock" in raw:
            raw["stock"] = bool(raw["stock"])
        try:
            product = Product(**raw)
            valid.append(product)
        except ValidationError as exc:
            errors.append({"row": idx, "data": raw, "errors": exc.errors()})

    return valid, errors
