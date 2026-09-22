#!/usr/bin/env python3
"""Integration test for store bot fixes."""

from tools.pricing import price_order
from tools.inventory import check_stock
from tools.shipping import delivery_eta
from agent.agent import _extract_pincode_from_text, _build_response_from_tools
from agent.state import AgentState

print("=" * 70)
print("INTEGRATION TEST: Store Bot Fixes")
print("=" * 70)
print()

# Test 1: Price calculation
print("TEST 1: Price Calculation")
print("-" * 70)
result = price_order('cotton t-shirt', 4)
print(f"4 Cotton T-Shirts: ₹{result['final_price']}")
assert abs(result['final_price'] - 1796.4) < 0.01, f"Price wrong! Got {result['final_price']}, expected 1796.4"
print("✅ PASS: Price calculation correct")
print()

# Test 2: Stock check
print("TEST 2: Stock Check")
print("-" * 70)
stock = check_stock('cotton t-shirt', 4)
print(f"Stock check: {stock}")
assert stock.get('available') == True, "Stock should be available"
print("✅ PASS: Stock check correct")
print()

# Test 3: Delivery ETA
print("TEST 3: Delivery ETA")
print("-" * 70)
delivery = delivery_eta('560001')
print(f"PIN 560001: {delivery['estimated_delivery_days']} days")
assert delivery.get('available') == True, "Delivery should be available for this PIN"
assert delivery.get('estimated_delivery_days') == 2, "Should be 2 days for PIN 560001"
print("✅ PASS: Delivery ETA correct")
print()

# Test 4: PIN extraction
print("TEST 4: PIN Extraction from Text")
print("-" * 70)
text = "can i get 4 cotton t-shirt with price and whether its available at 560001 pin?"
pin = _extract_pincode_from_text(text)
print(f"Extracted PIN: {pin}")
assert pin == '560001', f"Should extract 560001, got {pin}"
print("✅ PASS: PIN extraction correct")
print()

# Test 5: Response building
print("TEST 5: Response Building from Tool Results")
print("-" * 70)
state = AgentState()

# Simulate tool calls in trace
trace_data = [
    {
        "tool": "check_stock",
        "input": {"product_id": "cotton t-shirt", "quantity": 4},
        "result": {"available": True, "stock": 12, "product_name": "Cotton T-Shirt", "quantity": 4}
    },
    {
        "tool": "price_order",
        "input": {"product_id": "cotton t-shirt", "quantity": 4},
        "result": {
            "product_id": "TS-01",
            "product_name": "Cotton T-Shirt",
            "quantity": 4,
            "unit_price": 499,
            "subtotal": 1996,
            "discount_percentage": 10,
            "discount_amount": 199.6,
            "final_price": 1796.4,
            "currency": "INR",
        }
    },
    {
        "tool": "delivery_eta",
        "input": {"pincode": "560001"},
        "result": {"pincode": "560001", "available": True, "estimated_delivery_days": 2}
    },
]

state.trace = trace_data
response = _build_response_from_tools(state, trace_data)
print(f"Generated response:\n  {response}")

# Verify response contains correct info
assert "4" in response, "Should contain quantity"
assert "Cotton T-Shirt" in response or "cotton" in response.lower(), "Should mention product"
assert "1796" in response or "1796.4" in response, "Should contain correct price"
assert "560001" in response, "Should contain PIN"
assert "2" in response, "Should contain delivery days"

print("✅ PASS: Response building correct")
print()

print("=" * 70)
print("ALL TESTS PASSED! ✅")
print("=" * 70)
print()
print("Summary:")
print("  ✅ Price calculation: CORRECT (₹1796.40)")
print("  ✅ Stock check: WORKING")
print("  ✅ Delivery lookup: WORKING")
print("  ✅ PIN extraction: WORKING")
print("  ✅ Response building: WORKING")
print()
print("The store bot should now:")
print("  1. Calculate prices correctly (no hallucination)")
print("  2. Call all three tools in sequence")
print("  3. Combine results into one user-friendly sentence")
print("  4. Auto-detect and call delivery_eta when PIN provided")
