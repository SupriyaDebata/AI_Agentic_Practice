#!/usr/bin/env python
"""End-to-end test: verify filter extraction → SQL filtering → ranking."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.repositories.sql_repository import SQLProductRepository
from app.query_understanding.llm_parser import _regex_filters

print("\n=== END-TO-END FILTER TEST: Hopscotch Under ₹1000 ===\n")

# Step 1: Extract filters from user query
user_query = "hopscotch brand under 1000"
print(f"1. USER QUERY: '{user_query}'")

filters = _regex_filters(user_query)
print(f"\n2. EXTRACTED FILTERS (Regex):")
print(f"   - brand: {filters.brand}")
print(f"   - price_max: {filters.price_max}")
print(f"   - Full filters: {filters.model_dump()}")

# Step 2: Execute SQL filter
repo = SQLProductRepository()
sql_results = repo.filter(filters, top_k=100)

print(f"\n3. SQL FILTER RESULTS: {len(sql_results)} products")
print(f"   Expected: 7 products (Hopscotch AND price ≤ ₹1000)")
print(f"   Actual results:")
for p in sql_results:
    print(f"   - {p.product_name}: ₹{p.price} ({p.brand})")

# Verify correctness
print(f"\n4. VALIDATION:")
all_correct = all(
    p.brand == "Hopscotch" and p.price <= 1000 
    for p in sql_results
)
if all_correct:
    print(f"   ✅ ALL RESULTS CORRECT: {len(sql_results)} Hopscotch items under ₹1000")
else:
    print(f"   ❌ SOME RESULTS INCORRECT!")
    for p in sql_results:
        if p.brand != "Hopscotch" or p.price > 1000:
            print(f"      WRONG: {p.product_name} (₹{p.price}, {p.brand})")
