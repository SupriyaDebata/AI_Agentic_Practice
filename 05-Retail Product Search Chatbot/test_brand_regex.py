#!/usr/bin/env python
"""Test brand regex extraction with various queries."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.query_understanding.llm_parser import _regex_filters

test_queries = [
    "hopscotch brand under 1000",
    "hopscotch under 1000",
    "under 1000 hopscotch",
    "brand hopscotch below 1000 rs",
    "firstcry items under 500",
    "hrx brand below 800",
    "babyhug dress under 600",
    "hopscotch AND under 1000",
]

print("=== BRAND REGEX EXTRACTION TEST ===\n")
for query in test_queries:
    filters = _regex_filters(query)
    print(f"'{query}'")
    print(f"  → brand={filters.brand}, price_max={filters.price_max}")
    print()
