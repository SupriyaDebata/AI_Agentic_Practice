"""Product grounding guard — critical hallucination prevention.

Two checks:
  1. ID grounding: every product in the response must exist in the retrieved set.
  2. Query relevance: highly specific query keywords (e.g. "dragon", "unicorn")
     must appear in at least one returned product's name or description.
     If none match, the response is a semantic near-miss — treat as no-match
     rather than returning an unrelated product.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction

# Generic words that are too common to use as distinctiveness filters.
_GENERIC_WORDS = {
    "dress", "frock", "shirt", "tshirt", "tee", "jeans", "shorts", "jacket",
    "skirt", "dungaree", "shoes", "outfit", "wear", "apparel", "clothes",
    "clothing", "kids", "children", "child", "girl", "boy", "girls", "boys",
    "red", "blue", "green", "pink", "white", "black", "yellow", "orange",
    "grey", "purple", "gold", "navy", "ivory", "olive", "multicolor",
    "age", "size", "brand", "find", "show", "search", "need", "want",
    "for", "my", "the", "a", "an", "in", "on", "with", "and", "or",
    "cotton", "fabric", "print", "pattern", "style", "colour", "color",
}


def _product_text(p: Any) -> str:
    if isinstance(p, dict):
        return f"{p.get('name', '')} {p.get('description', '')}".lower()
    return f"{getattr(p, 'name', '')} {getattr(p, 'description', '')}".lower()


def _distinctive_query_keywords(query: str) -> List[str]:
    """Return words from *query* that are specific enough to be distinctive.

    Generic clothing/filter words are excluded so only meaningful product
    descriptors (e.g. "dragon", "unicorn", "safari") are checked.
    """
    words = re.findall(r"[a-z]{4,}", query.lower())
    return [w for w in words if w not in _GENERIC_WORDS]


def check_product_grounding(
    response_products: List[Any],
    retrieved_ids: List[int],
    query: str = "",
) -> GuardrailResult:
    """Validate that every product in *response_products* exists in *retrieved_ids*.

    Args:
        response_products: list of product dicts or objects returned by the search.
        retrieved_ids: authoritative product IDs from the retrieval layer.

    Returns:
        ALLOW if all products are grounded, FALLBACK if any are ungrounded.
    """
    if not response_products:
        return GuardrailResult(
            passed=True,
            action=GuardAction.ALLOW,
            guardrail_name="ProductGrounding",
            reason="No products in response — nothing to validate",
        )

    # ── Check 1: ID grounding ────────────────────────────────────────────────
    retrieved_set = set(retrieved_ids)
    ungrounded: List[int] = []

    for p in response_products:
        pid: Optional[int] = None
        if isinstance(p, dict):
            pid = p.get("id")
        else:
            pid = getattr(p, "id", None)

        if pid is not None and pid not in retrieved_set:
            ungrounded.append(pid)

    if ungrounded:
        return GuardrailResult(
            passed=False,
            action=GuardAction.FALLBACK,
            guardrail_name="ProductGrounding",
            reason=f"Response contains product IDs not in retrieval results: {ungrounded}",
            metadata={"ungrounded_ids": ungrounded, "retrieved_count": len(retrieved_ids)},
        )

    # ── Check 2: Query relevance (hallucination by semantic near-miss) ───────
    # If the query has specific distinctive keywords (e.g. "dragon", "unicorn"),
    # at least one returned product must mention them in name or description.
    if query:
        distinctive = _distinctive_query_keywords(query)
        if distinctive:
            matched_keywords = [
                kw for kw in distinctive
                if any(kw in _product_text(p) for p in response_products)
            ]
            if not matched_keywords:
                return GuardrailResult(
                    passed=False,
                    action=GuardAction.FALLBACK,
                    guardrail_name="ProductGrounding",
                    reason=(
                        f"Query keywords {distinctive} not found in any returned product — "
                        "likely a semantic near-miss, not a true match"
                    ),
                    metadata={"distinctive_keywords": distinctive, "matched": []},
                )

    return GuardrailResult(
        passed=True,
        action=GuardAction.ALLOW,
        guardrail_name="ProductGrounding",
        reason=f"All {len(response_products)} product(s) are grounded in retrieval results",
        metadata={"grounded_count": len(response_products)},
    )
