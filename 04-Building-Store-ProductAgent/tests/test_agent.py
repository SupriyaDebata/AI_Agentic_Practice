"""
15 Test Cases for Store Assistant Agent
=======================================

TC01 — Single available product
  Request: "I want 1 cotton t-shirt"
  Expected tools: check_stock, price_order
  Expected: ₹499 (no discount for qty < 3)

TC02 — Single unavailable product
  Request: "I want 1 denim jeans"
  Expected tools: check_stock
  Expected: Out of stock message, no price_order called

TC03 — Quantity exceeds stock
  Request: "I want 20 casual jackets"
  Expected tools: check_stock
  Expected: Only 3 available message

TC04 — Product with discount applied
  Request: "I want 3 cotton t-shirts"
  Expected tools: check_stock, price_order
  Expected: 10% discount applied, ₹1,347.30

TC05 — Product without discount (qty below threshold)
  Request: "I want 2 cotton t-shirts"
  Expected tools: check_stock, price_order
  Expected: No discount, ₹998

TC06 — Delivery with known PIN
  Request: "Delivery to 700001, how long?"
  Expected tools: delivery_eta
  Expected: 3 days

TC07 — Delivery with unknown PIN
  Request: "Deliver to 999999"
  Expected tools: delivery_eta
  Expected: Unavailable message

TC08 — Multiple products
  Request: "I want 3 cotton t-shirts and 2 slim fit jeans"
  Expected tools: check_stock×2, price_order×2
  Expected: Both priced with discounts

TC09 — One available + one unavailable
  Request: "I want 3 polo t-shirts and 2 denim jeans"
  Expected tools: check_stock×2, price_order×1
  Expected: Polo priced, denim out of stock

TC10 — Follow-up add product
  Turn 1: "I want 3 cotton t-shirts"
  Turn 2: "Add 2 slim fit jeans"
  Expected: Order accumulates across turns

TC11 — Follow-up ask total
  After TC10: "What's my current total?"
  Expected tools: none (state already has total)
  Expected: Reads from order_total in state

TC12 — Stock check only
  Request: "Are running shoes in stock?"
  Expected tools: check_stock
  Expected: 7 available, no price_order

TC13 — Price check only
  Request: "How much for 2 baseball caps?"
  Expected tools: check_stock, price_order
  Expected: ₹698 (no discount, qty < 5)

TC14 — Delivery check only
  Request: "Can you deliver to 560001?"
  Expected tools: delivery_eta
  Expected: 2 days

TC15 — Unrelated request
  Request: "What's the weather today?"
  Expected tools: none
  Expected: Polite out-of-scope message
"""

import pytest
from tools.inventory import check_stock
from tools.pricing import price_order
from tools.shipping import delivery_eta


class TestCheckStock:
    def test_available_product(self):
        result = check_stock("TS-01", 3)
        assert result["available"] is True
        assert result["available_quantity"] == 12
        assert result["product_name"] == "Cotton T-Shirt"

    def test_out_of_stock(self):
        result = check_stock("JN-04", 1)
        assert result["available"] is False
        assert result["available_quantity"] == 0

    def test_quantity_exceeds_stock(self):
        result = check_stock("JK-07", 10)
        assert result["available"] is False
        assert result["available_quantity"] == 3

    def test_product_not_found(self):
        result = check_stock("XX-99", 1)
        assert result.get("error") is True

    def test_zero_quantity(self):
        result = check_stock("TS-01", 0)
        assert result.get("error") is True

    def test_negative_quantity(self):
        result = check_stock("TS-01", -1)
        assert result.get("error") is True


class TestPriceOrder:
    def test_price_with_discount(self):
        result = price_order("TS-01", 3)
        assert result["discount_percentage"] == 10
        assert result["final_price"] == 1347.30

    def test_price_no_discount(self):
        result = price_order("TS-01", 2)
        assert result["discount_percentage"] == 0
        assert result["final_price"] == 998

    def test_currency_is_inr(self):
        result = price_order("TS-01", 1)
        assert result["currency"] == "INR"

    def test_product_not_found(self):
        result = price_order("XX-99", 1)
        assert result.get("error") is True


class TestDeliveryEta:
    def test_known_pincode(self):
        result = delivery_eta("700001")
        assert result["estimated_delivery_days"] == 3
        assert result["available"] is True

    def test_unknown_pincode(self):
        result = delivery_eta("999999")
        assert result["available"] is False
        assert "message" in result

    def test_pincode_with_spaces(self):
        result = delivery_eta("  700001  ")
        assert result["available"] is True
