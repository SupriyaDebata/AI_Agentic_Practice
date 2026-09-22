#!/usr/bin/env python
"""Direct SQL test - bypass LLM."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.repositories.sql_repository import SQLProductRepository
from app.models.filters import ProductFilter

# Initialize repo
print("Initializing SQL repository...")
repo = SQLProductRepository()

# Test 1: No filters
print("\n=== TEST 1: No filters ===")
products = repo.filter(ProductFilter(), top_k=100)
print(f"Total products: {len(products)}")

# Test 2: Price max = 1000
print("\n=== TEST 2: price_max = 1000 ===")
products = repo.filter(ProductFilter(price_max=1000), top_k=100)
print(f"Products with price <= 1000: {len(products)}")
for p in products[:5]:
    print(f"  - {p.product_name}: ₹{p.price} ({p.brand})")

# Test 3: Brand = Hopscotch
print("\n=== TEST 3: brand = Hopscotch ===")
products = repo.filter(ProductFilter(brand="Hopscotch"), top_k=100)
print(f"Hopscotch products: {len(products)}")
for p in products[:5]:
    print(f"  - {p.product_name}: ₹{p.price}")

# Test 4: Both filters
print("\n=== TEST 4: brand = Hopscotch AND price_max = 1000 ===")
products = repo.filter(ProductFilter(brand="Hopscotch", price_max=1000), top_k=100)
print(f"Hopscotch products under ₹1000: {len(products)}")
for p in products:
    print(f"  - {p.product_name}: ₹{p.price}")

# Test 5: Price max = 1000 only (all brands)
print("\n=== TEST 5: ALL brands with price_max = 1000 ===")
products = repo.filter(ProductFilter(price_max=1000), top_k=100)
print(f"Total products under ₹1000: {len(products)}")
for p in products[:10]:
    print(f"  - {p.product_name}: ₹{p.price} ({p.brand})")
