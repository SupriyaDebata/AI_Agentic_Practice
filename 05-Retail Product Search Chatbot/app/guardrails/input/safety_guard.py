"""Input safety/abuse guard.

Detects clearly abusive, unsafe, or inappropriate input before it reaches the
LLM.  All patterns are deterministic — no LLM call needed.
"""
from __future__ import annotations

import re
from typing import List

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction

_ABUSE_PATTERNS: List[str] = [
    # Violence
    r"\b(kill|murder|bomb|weapon|gun|knife|shoot|stab|assault|terror|terrorist)\b",
    # Hacking/exploits
    r"\b(hack|exploit|malware|ransomware|phishing|sql\s+injection|xss|ddos|botnet)\b",
    # Explicit profanity
    r"\b(fuck(?:ing|ed|er)?|shit(?:ty)?|bitch(?:es)?|asshole|bastard|cunt|dick|nude|naked|porn)\b",
    # Child safety
    r"child\s+(?:abuse|porn|sexual|exploit|nude|naked)",
    # Self-harm
    r"\b(suicide|self[\s\-]harm|cut\s+myself|end\s+my\s+life|want\s+to\s+die)\b",
    # Discrimination
    r"\b(racist|sexist|homophobic|transphobic|islamophobic|antisemitic)\b",
    # Illegal activity
    r"\b(drug\s+deal|buy\s+drugs|sell\s+drugs|smuggle|launder\s+money|dark\s+web)\b",
]

_COMPILED: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _ABUSE_PATTERNS
]


def check_safety_input(text: str) -> GuardrailResult:
    """Return BLOCK if unsafe/abusive content detected, ALLOW otherwise."""
    for pattern in _COMPILED:
        if pattern.search(text):
            return GuardrailResult(
                passed=False,
                action=GuardAction.BLOCK,
                guardrail_name="InputSafetyGuard",
                reason="Unsafe or abusive content detected in request",
                metadata={"unsafe": True},
            )

    return GuardrailResult(
        passed=True,
        action=GuardAction.ALLOW,
        guardrail_name="InputSafetyGuard",
        reason="No unsafe content detected",
    )
