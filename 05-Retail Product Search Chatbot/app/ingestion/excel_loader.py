"""
Load products.xlsx and return validated Product objects.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from app.ingestion.validators import validate_dataframe
from app.models.product import Product


def load_products(xlsx_path: Path) -> List[Product]:
    """Read the Excel file, validate every row, return Product list."""
    df = pd.read_excel(xlsx_path)
    products, errors = validate_dataframe(df)

    if errors:
        for e in errors:
            print(f"  [WARN] Row {e['row']} skipped: {e['errors']}")

    print(f"Loaded {len(products)} valid products ({len(errors)} errors).")
    return products
