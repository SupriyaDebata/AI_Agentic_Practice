"""Price and catalog manipulation guard.

Protects catalog integrity: the LLM must never be tricked into modifying or
overriding product prices, names, stock, or any other catalog attribute.
All checks are deterministic regex — no LLM call.
"""
from __future__ import annotations

import re
from typing import List

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction

_MANIPULATION_PATTERNS: List[str] = [
    r"change\s+(?:the\s+)?(?:product\s+)?price",
    r"set\s+(?:the\s+)?price(?:\s+to|\s+at|\s+accordingly|\s+as)?(?:\s|$)",
    r"make\s+(?:it|this|the\s+product)\s+(?:cost|price|worth)",
    r"ignore\s+(?:the\s+)?(?:database\s+)?price",
    r"pretend\s+(?:this|the)\s+product\s+costs?",
    r"give\s+me\s+(?:a\s+)?discount\s+that\s+doesn'?t\s+exist",
    r"show\s+.{0,40}at\s+₹?\d+\s+instead",
    r"override\s+(?:the\s+)?price",
    r"modify\s+(?:(?:the|all|any|every)\s+)*(?:product|catalog|database|prices?|stock|inventory)",
    r"update\s+(?:the\s+)?(?:product|catalog|price|stock)\s+(?:to|with|from)",
    r"delete\s+(?:this\s+|the\s+)?product",
    r"add\s+(?:a\s+)?new\s+product\s+(?:to|in|into)\s+(?:the\s+)?(?:catalog|database|db)",
    r"insert\s+(?:a\s+)?(?:product|row|record|entry)\s+(?:into|in)\s+(?:the\s+)?(?:db|database|catalog)",
    r"drop\s+(?:table|database|catalog)",
    r"(?:increase|decrease|reduce|raise)\s+(?:the\s+)?price",
    r"apply\s+(?:a\s+)?(?:\d+%?\s+)?discount",
    r"product\s+(?:price\s+)?is\s+(?:actually|really|now)\s+₹?\d+",
    r"the\s+real\s+price\s+is",
    r"buy\s+\d+\s+\w+\s+at\s+₹?\d+",
    r"(?:increase|decrease|reduce|raise|lower)\s+(?:all\s+)?prices?\s+by\s+\d+%?",
    r"catalog\s+(?:says?|shows?)\s+wrong",
    r"database\s+(?:is\s+)?(?:wrong|incorrect|lying)",
]

_COMPILED: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _MANIPULATION_PATTERNS
]


def check_price_manipulation(text: str) -> GuardrailResult:
    """Return BLOCK if catalog/price manipulation is detected, ALLOW otherwise."""
    for pattern in _COMPILED:
        if pattern.search(text):
            return GuardrailResult(
                passed=False,
                action=GuardAction.BLOCK,
                guardrail_name="PriceManipulationGuard",
                reason="Catalog/price manipulation attempt detected",
                metadata={"manipulation": True, "matched": pattern.pattern[:80]},
            )

    return GuardrailResult(
        passed=True,
        action=GuardAction.ALLOW,
        guardrail_name="PriceManipulationGuard",
        reason="No price/catalog manipulation detected",
    )
