import json
import logging
import ollama
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent / "data" / "shipping.json"
DEFAULT_DELIVERY_DAYS = 7

def delivery_eta(pincode: str) -> dict:
    """Get estimated delivery days for a PIN code."""
    pincode = pincode.strip()

    try:
        with open(DATA_PATH) as f:
            shipping_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load shipping data: {e}")
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
