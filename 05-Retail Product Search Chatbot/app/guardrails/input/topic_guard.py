"""Topic/domain guard — ensures requests are about kids' clothing.

Two-pass approach:
  1. Fast blocklist: explicit off-topic keyword patterns → BLOCK immediately.
  2. Allowlist: if any kids-clothing keyword is present → ALLOW.
  3. Short queries get the benefit of the doubt (ALLOW).
  4. Anything remaining that looks unrelated → BLOCK.

No LLM call is made — pure deterministic logic keeps latency near zero.
"""
from __future__ import annotations

import re
from typing import List

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction

# ── Adult-context signals — block even when clothing keywords are present ─────
# These indicate the clothing request is for an adult, not for kids.
_ADULT_CONTEXT_RE = re.compile(
    r"(?i)\b("
    r"wife|husband|partner|spouse|girlfriend|boyfriend|fianc[eé]"
    r"|adult|men(?:\'s)?|women(?:\'s)?|ladies|gents|man|woman"
    r"|office\s+wear|formal\s+wear\s+(?:for\s+)?(?:office|work|meeting|interview)"
    r"|work\s+wear|business\s+(?:attire|wear|outfit)"
    r"|maternity|pregnancy|nursing"
    r")\b"
    # Adult dress sizing: numeric sizes like S/M/L/XL or size 8/10/12/14+
    r"|(?:size|sized?)\s*(?:xs|s\b|m\b|l\b|xl\b|xxl\b|[89]|1[0-9]|2[0-9]|3[0-9])"
    r"|\bsize\s+(?:small|medium|large|x-?large)\b"
)

# ── Financial/payment keywords — never get "benefit of the doubt" ────────────
# These override the short-query allowance because they signal payment data probing.
_FINANCIAL_KEYWORDS_RE = re.compile(
    r"(?i)\b(credit\s+card|debit\s+card|\bcard\b|cvv|cvc|payment\s+card|bank\s+account"
    r"|account\s+no|account\s+number|iban|swift|routing\s+number)\b"
)

# ── Explicit off-topic blocklist ──────────────────────────────────────────────
_BLOCKED_TOPIC_PATTERNS: List[str] = [
    r"\b(laptop|desktop|computer|monitor|keyboard|mouse|printer|router|wifi|broadband)\b",
    r"\b(smartphone|android|iphone|samsung|oneplus|tablet|ipad|headphone|earphone|airpod)\b",
    r"\b(stock\s+market|share\s+market|nifty|sensex|mutual\s+fund|sip|bitcoin|crypto|nft)\b",
    r"\bwrite\s+(?:a\s+)?(?:python|java|javascript|code|script|program|function|class)\b",
    r"\b(election|politics|vote|parliament|president|prime\s+minister|government\s+policy)\b",
    r"\b(book\s+(?:a\s+)?flight|hotel|travel|tour|holiday\s+package|bus\s+ticket|train\s+ticket)\b",
    r"\b(recipe|cooking|ingredient|bake|fry|boil|cuisine|restaurant|food\s+delivery)\b",
    r"\b(weather\s+forecast|temperature\s+today|will\s+it\s+rain)\b",
    r"\b(movie|film|web\s+series|netflix|amazon\s+prime|hotstar|song|music|playlist)\b",
    r"\b(math|calculus|algebra|equation|integral|derivative|solve\s+for\s+x)\b",
    r"\b(medical|diagnosis|medicine|symptoms?|doctor|hospital|prescription|disease)\b",
    r"\b(cricket|football|ipl|match\s+result|sports\s+score|live\s+score)\b",
    r"\btell\s+me\s+(?:a\s+)?(?:joke|story|poem|riddle)\b",
    r"\b(astrology|horoscope|zodiac|tarot|numerology)\b",
    r"\b(recommend\s+(?:a\s+)?(?:book|novel|manga|anime|game|gaming))\b",
    # Home/furniture — clearly off-topic even when "child"/"kids" appears in context
    r"\b(furniture|sofa|bed\s+frame|wardrobe|cupboard|cabinet|shelf|bookshelf"
    r"|mattress|pillow|bedding|curtain|rug|carpet|lamp|chandelier|table|chair"
    r"|bedroom|living\s+room|dining\s+room|bathroom|kitchen)\b",
    # Electronics / appliances
    r"\b(tv|television|refrigerator|washing\s+machine|microwave|air\s+conditioner|ac|fan|mixer|blender)\b",
    # Groceries / food items
    r"\b(grocery|groceries|food|cereal|cereals|vegetables?|fruits?|milk|rice|wheat|flour|oil|sugar|salt|snack|biscuit|chocolate|baby\s+food|formula|nutrition)\b",
    # Toys / non-clothing — these are distinct categories even for kids
    r"\b(toys?|lego|puzzle|board\s+game|video\s+game|bicycle|tricycle|scooter|cycle)\b",
    # Electronics (generic)
    r"\b(electronics|gadget|gadgets|camera|console|gaming\s+console)\b",
]

_BLOCKED_RE: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _BLOCKED_TOPIC_PATTERNS
]

# ── Kids-clothing allowlist keywords ─────────────────────────────────────────
_WORD_SPLIT_RE = re.compile(r"\W+")

_KIDS_CLOTHING_KEYWORDS = {
    "dress", "frock", "shirt", "t-shirt", "tshirt", "tee", "jeans", "shorts",
    "jacket", "skirt", "dungaree", "shoes", "clothing", "clothes", "outfit",
    "wear", "apparel", "kids", "children", "child", "toddler",
    "girl", "boy", "girls", "boys", "age", "size", "colour", "color",
    "brand", "babyhug", "firstcry", "hopscotch", "hrx", "myntra",
    "price", "budget", "under", "below", "cotton", "fabric",
    "birthday", "party", "school", "casual", "formal", "winter", "summer",
    "sleeve", "pink", "blue", "red", "white", "green", "yellow", "purple",
    "black", "orange", "grey", "multicolor", "multicolour",
    "₹", "rs", "rupees", "inr",
    "find", "search", "show", "recommend", "suggest", "looking",
}


def check_topic(text: str) -> GuardrailResult:
    """Return BLOCK if off-topic, ALLOW if kids-clothing related."""
    # 1. Fast blocklist
    for pattern in _BLOCKED_RE:
        if pattern.search(text):
            return GuardrailResult(
                passed=False,
                action=GuardAction.BLOCK,
                guardrail_name="TopicGuard",
                reason="Off-topic request: not related to kids' clothing",
                metadata={"matched_pattern": pattern.pattern[:80]},
            )

    # 1b. Adult context — block even when clothing keywords present
    if _ADULT_CONTEXT_RE.search(text):
        return GuardrailResult(
            passed=False,
            action=GuardAction.BLOCK,
            guardrail_name="TopicGuard",
            reason="Request appears to be for adult clothing — this catalog is kids only",
            metadata={"topic": "adult_clothing"},
        )

    # 2. Kids-clothing allowlist
    words = set(_WORD_SPLIT_RE.split(text.lower()))
    words.discard("")
    if words & _KIDS_CLOTHING_KEYWORDS:
        return GuardrailResult(
            passed=True,
            action=GuardAction.ALLOW,
            guardrail_name="TopicGuard",
            reason="Kids clothing domain keyword detected",
        )

    # 3. Short queries — allow with benefit of the doubt,
    #    UNLESS a financial/payment keyword is present (those are never clothing queries)
    if len(text.split()) <= 5:
        if _FINANCIAL_KEYWORDS_RE.search(text):
            return GuardrailResult(
                passed=False,
                action=GuardAction.BLOCK,
                guardrail_name="TopicGuard",
                reason="Financial/payment keyword in a non-clothing query",
                metadata={"topic": "payment_probe"},
            )
        return GuardrailResult(
            passed=True,
            action=GuardAction.ALLOW,
            guardrail_name="TopicGuard",
            reason="Short query — allowing (no explicit off-topic signals)",
        )

    # 4. No clothing signal in a longer query → likely off-topic
    return GuardrailResult(
        passed=False,
        action=GuardAction.BLOCK,
        guardrail_name="TopicGuard",
        reason="Query does not appear to be about kids' clothing products",
        metadata={"topic": "off_topic"},
    )
