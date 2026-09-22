#!/usr/bin/env python
"""Test the complete search flow with logging."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.catalog_service import CatalogSearchService
from app.models.search import SearchIntent
from app.config import settings

# Initialize service
print("Initializing catalog service...")
service = CatalogSearchService()
service.initialize()

# Test query
query = "hopscotch brand under 1000"
print(f"\n=== SEARCHING: '{query}' ===\n")

# Parse intent
intent = service.parse_query(query)
print(f"PARSED INTENT:")
print(f"  - Lexical Query: {intent.lexical_query}")
print(f"  - Semantic Query: {intent.semantic_query}")
print(f"  - Hard Filters: {intent.hard_filters.model_dump()}")
print(f"  - Route: {intent.route}")

# Execute search
response = service.search(intent)
print(f"\nSEARCH RESULTS: {len(response.results)} products")
for i, result in enumerate(response.results, 1):
    print(f"  {i}. {result.product.product_name} - ₹{result.product.price} ({result.product.brand})")

print(f"\nLATENCY: {response.latency_ms}")
print(f"ROUTE USED: {response.route_used}")
print(f"TOTAL CANDIDATES: {response.total_candidates}")
