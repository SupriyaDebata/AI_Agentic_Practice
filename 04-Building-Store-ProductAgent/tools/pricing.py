import json
import logging
from pathlib import Path

from tools.inventory import _find_product

logger = logging.getLogger(__name__)

INVENTORY_PATH = Path(__file__).parent.parent / "data" / "inventory.json"
DISCOUNTS_PATH = Path(__file__).parent.parent / "data" / "discounts.json"


def _load_inventory() -> list[dict]:
    with open(INVENTORY_PATH) as f:
        return json.load(f)


def _load_discounts() -> list[dict]:
    with open(DISCOUNTS_PATH) as f:
        return json.load(f)


def price_order(product_id: str, quantity: int) -> dict:
    """Calculate order price with applicable discounts."""
    if quantity <= 0:
        return {"error": True, "message": "Quantity must be greater than zero."}

    try:
        inventory = _load_inventory()
        discounts = _load_discounts()
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return {"error": True, "message": "Unable to calculate price right now. Please try again."}

    # Accept product name or product_id
    product = _find_product(inventory, product_id)
    if not product:
        return {"error": True, "message": f"Product '{product_id}' was not found."}

    unit_price = product["price"]
    subtotal = unit_price * quantity

    discount_pct = 0.0
    for rule in discounts:
        if rule["product_category"] == product["category"] and quantity >= rule["minimum_quantity"]:
            discount_pct = rule["discount_percentage"]
            break

    # Calculate discount: apply percentage to subtotal and round to 2 decimals
    discount_amount = round(subtotal * discount_pct / 100, 2)
    # Calculate final price: ensure we don't have floating point precision issues
    final_price = subtotal - discount_amount

    result = {
        "product_id": product["product_id"],
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": unit_price,
        "subtotal": subtotal,
        "discount_percentage": discount_pct,
        "discount_amount": discount_amount,
        "final_price": final_price,
        "currency": "INR",
    }
    logger.info(f"price_order({product['product_id']}, {quantity}) -> final_price={final_price}")
    return result
