"""Tone guard — ensures the response is professional and parent-friendly.

Detects:
  - Insults or aggressive language
  - Manipulative sales language (FOMO, false urgency)
  - Overconfident/misleading claims
  - Inappropriate content for a parenting audience
"""
from __future__ import annotations

import re
from typing import List

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction

_TONE_ISSUE_PATTERNS: List[str] = [
    # Insults / aggression
    r"\b(idiot|stupid|fool|dumb|moron|ridiculous\s+choice|terrible\s+taste)\b",
    # Manipulative urgency
    r"\b(limited\s+time\s+offer|act\s+now|don'?t\s+miss\s+out|hurry|selling\s+fast|last\s+chance)\b",
    # False guarantees
    r"\b(guaranteed|100%\s+perfect|never\s+fails?|absolutely\s+the\s+best|best\s+in\s+the\s+world)\b",
    # Hate / discrimination
    r"\b(hate|disgusting|filthy|gross)\b",
    # Inappropriate for a parenting chatbot
    r"\b(sexy|hot\s+deal|sexy\s+style|adult\s+content)\b",
]

_COMPILED: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _TONE_ISSUE_PATTERNS
]


def check_tone(text: str) -> GuardrailResult:
    """Return FALLBACK if tone is inappropriate, ALLOW otherwise."""
    for pattern in _COMPILED:
        if pattern.search(text):
            return GuardrailResult(
                passed=False,
                action=GuardAction.FALLBACK,
                guardrail_name="ToneGuard",
                reason="Response tone is inappropriate for a parenting audience",
                metadata={"pattern": pattern.pattern[:80]},
            )

    return GuardrailResult(
        passed=True,
        action=GuardAction.ALLOW,
        guardrail_name="ToneGuard",
        reason="Response tone is professional and appropriate",
    )
