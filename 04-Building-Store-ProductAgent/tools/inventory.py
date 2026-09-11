import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent / "data" / "inventory.json"


def _load_inventory() -> list[dict]:
    with open(DATA_PATH) as f:
        return json.load(f)


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation/hyphens for comparison."""
    return text.lower().replace("-", " ").replace("_", " ").strip()


def _meaningful_words(text: str) -> set[str]:
    """Return words longer than 1 character (avoids 't', 'a', etc. causing false matches)."""
    return {w for w in _normalise(text).split() if len(w) > 1}


def _find_product(inventory: list[dict], query: str) -> dict | None:
    """
    Find a product by:
      1. Exact product_id match          (highest priority)
      2. Exact full name match           (case-insensitive)
      3. Query is a substring of name    (e.g. 'polo' in 'Polo T-Shirt')
      4. Name is a substring of query
      5. All meaningful query words found in product name (AND match)
      6. Category match as last resort   (only if single product in that category)
    Returns the best single match, or None.
    """
    q = _normalise(query)
    q_words = _meaningful_words(query)

    # 1. Exact product_id
    for p in inventory:
        if p["product_id"].lower() == q:
            return p

    # 2. Exact name
    for p in inventory:
        if _normalise(p["name"]) == q:
            return p

    # 3. Query is contained in the product name
    for p in inventory:
        if q in _normalise(p["name"]):
            return p

    # 4. Product name is contained in the query
    for p in inventory:
        if _normalise(p["name"]) in q:
            return p

    # 5. ALL meaningful words in query appear in the product name (AND logic)
    if q_words:
        matched = []
        for p in inventory:
            name_words = _meaningful_words(p["name"])
            if q_words <= name_words:          # subset: all query words present
                matched.append(p)
        if len(matched) == 1:
            return matched[0]
        if len(matched) > 1:
            # Prefer the product whose name most closely matches (fewest extra words)
            return min(matched, key=lambda p: len(_meaningful_words(p["name"]) - q_words))

    # 6. Category match — only if exactly one product belongs to that category
    cat_matches = [p for p in inventory if _normalise(p["category"]) == q]
    if len(cat_matches) == 1:
        return cat_matches[0]

    return None


def check_stock(product_id: str, quantity: int) -> dict:
    """
    Check whether the requested quantity of a product is available.
    Accepts a product name (e.g. 'polo t-shirt'), product_id (e.g. 'TS-02'),
    or any reasonable partial name.
    """
    if quantity <= 0:
        return {"error": True, "message": "Quantity must be greater than zero."}

    try:
        inventory = _load_inventory()
    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")
        return {"error": True, "message": "Unable to check stock right now. Please try again."}

    product = _find_product(inventory, product_id)
    if not product:
        # Help the LLM by listing available product names
        names = ", ".join(p["name"] for p in inventory)
        return {
            "error": True,
            "message": (
                f"Product '{product_id}' was not found in the store catalog. "
                f"Available products: {names}."
            ),
        }

    available = product["stock"] >= quantity
    result = {
        "product_id": product["product_id"],
        "product_name": product["name"],
        "category": product["category"],
        # unit_price intentionally NOT included — always call price_order for pricing
        "available": available,
        "requested_quantity": quantity,
        "available_quantity": product["stock"],
    }
    if not available and product["stock"] > 0:
        result["message"] = (
            f"Only {product['stock']} unit(s) of {product['name']} available, "
            f"but you requested {quantity}."
        )
    elif not available:
        result["message"] = f"{product['name']} is currently out of stock."

    logger.info(
        f"check_stock({product_id!r}, {quantity}) -> "
        f"resolved='{product['product_id']}', available={available}"
    )
    return result
