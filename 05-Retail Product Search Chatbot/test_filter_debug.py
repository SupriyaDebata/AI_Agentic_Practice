#!/usr/bin/env python
"""Debug script to test filter extraction."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.query_understanding.llm_parser import _regex_filters, LLMQueryParser
from app.models.filters import ProductFilter

query = "hopscotch brand under 1000"
print(f"\n=== Testing Query: '{query}' ===\n")

# Test regex fallback
print("1. REGEX FALLBACK:")
filters = _regex_filters(query)
print(f"   - brand: {filters.brand}")
print(f"   - price_max: {filters.price_max}")
print(f"   - price_min: {filters.price_min}")
print(f"   - Full: {filters.model_dump()}")

# Test with LLM parser
print("\n2. LLM PARSER (if Ollama available):")
try:
    parser = LLMQueryParser()
    intent = parser.parse(query)
    print(f"   - brand: {intent.hard_filters.brand}")
    print(f"   - price_max: {intent.hard_filters.price_max}")
    print(f"   - price_min: {intent.hard_filters.price_min}")
    print(f"   - Full: {intent.hard_filters.model_dump()}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test related queries
print("\n3. TESTING VARIATIONS:")
test_queries = [
    "under 1000",
    "hopscotch",
    "hopscotch under 1000",
    "brand hopscotch price under 1000",
    "items below 1000",
    "less than 1000 rs",
]

for q in test_queries:
    f = _regex_filters(q)
    print(f"   '{q}' → price_max={f.price_max}, brand={f.brand}")
