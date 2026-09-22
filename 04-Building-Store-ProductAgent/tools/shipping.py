import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent / "data" / "shipping.json"
DEFAULT_DELIVERY_DAYS = 7

# CACHE: Load shipping data once at module level (not on every function call)
_SHIPPING_CACHE = None


def _load_shipping_data() -> list[dict]:
    """Load shipping data from cache (or from file on first call)."""
    global _SHIPPING_CACHE
    if _SHIPPING_CACHE is None:
        try:
            with open(DATA_PATH) as f:
                _SHIPPING_CACHE = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load shipping data: {e}")
            _SHIPPING_CACHE = []
    return _SHIPPING_CACHE


def delivery_eta(pincode: str) -> dict:
    """Get estimated delivery days for a PIN code."""
    pincode = pincode.strip()
    shipping_data = _load_shipping_data()
    
    if not shipping_data:
        return {"error": True, "message": "Unable to check delivery availability right now."}

    record = next((s for s in shipping_data if s["pincode"] == pincode), None)
    if record:
        result = {"pincode": pincode, "estimated_delivery_days": record["delivery_days"], "available": True}
    else:
        result = {
            "pincode": pincode,
            "available": False,
            "message": f"Delivery is currently unavailable for PIN code {pincode}.",
        }

    logger.info(f"delivery_eta({pincode}) -> {result}")
    return result
