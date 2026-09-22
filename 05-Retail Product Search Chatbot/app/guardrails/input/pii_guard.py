"""PII detection and sanitization guard.

Detects credit card numbers, CVV, phone numbers, email addresses,
Aadhaar, PAN, bank account numbers, and replaces them with safe tokens
before the text reaches the LLM or LangSmith.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction

# (pattern, replacement_token, pii_type)
_PII_PATTERNS: List[Tuple[str, str, str]] = [
    # Visa card (full 16-digit)
    (r"\b4[0-9]{3}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b", "[CARD]", "CARD"),
    # Mastercard (full 16-digit)
    (r"\b5[1-5][0-9]{2}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b", "[CARD]", "CARD"),
    # Amex (full 15-digit)
    (r"\b3[47][0-9]{2}[\s\-]?[0-9]{6}[\s\-]?[0-9]{5}\b", "[CARD]", "CARD"),
    # Generic 16-digit card-like numbers (fallback)
    (r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b", "[CARD]", "CARD"),
    # Partial Visa — catches truncated input like "4111-1111-" or "4111 1111 1111"
    (r"\b4[0-9]{3}[\s\-][0-9]{4}[\s\-][0-9]{0,4}", "[CARD]", "CARD"),
    # Partial Mastercard — e.g. "5111-1111-"
    (r"\b5[1-5][0-9]{2}[\s\-][0-9]{4}[\s\-][0-9]{0,4}", "[CARD]", "CARD"),
    # Partial generic — any two or more groups of 4 digits separated by dash/space
    (r"\b\d{4}[\s\-]\d{4}[\s\-]\d{1,4}", "[CARD]", "CARD"),
    # "card"/"credit card"/"debit card" keyword near any digit sequence (handles unseparated input)
    # e.g. "Card 11123455----"  or  "my card 4111111111111111"
    (r"(?:credit\s+card|debit\s+card|\bcard\b)\s*[:\-]?\s*([\d][\d\s\-]{5,})", "[CARD]", "CARD"),
    # Long continuous digit strings that look like card numbers (13-19 digits, no separators)
    # e.g. "4111111111111111" or "11123455678901234"
    (r"\b\d{13,19}\b", "[CARD]", "CARD"),
    # CVV near keyword
    (r"(?i)(?:cvv|cvc|security\s+code)\s*[:\-]?\s*\d{3,4}", "[CVV]", "CVV"),
    # Indian mobile numbers (10-digit starting with 6-9)
    (r"\b[6-9]\d{9}\b", "[PHONE]", "PHONE"),
    # PAN card (ABCDE1234F format)
    (r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", "[PAN]", "PAN"),
    # Aadhaar (12-digit, may be space-separated)
    (r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[AADHAAR]", "AADHAAR"),
    # Email addresses
    (r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "[EMAIL]", "EMAIL"),
    # Bank account numbers (9-18 digits near account keywords)
    (r"(?i)(?:account|acc(?:ount)?|bank)\s*(?:no\.?|number|num)?\s*[:\-]?\s*(\d{9,18})", "[ACCOUNT]", "ACCOUNT"),
]

_COMPILED: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(p, re.IGNORECASE), repl, ptype)
    for p, repl, ptype in _PII_PATTERNS
]


def check_pii(text: str) -> GuardrailResult:
    """Detect and sanitize PII in *text*. Returns SANITIZE if PII found, ALLOW otherwise."""
    sanitized = text
    detected_types: List[str] = []

    for pattern, replacement, pii_type in _COMPILED:
        new_text, count = pattern.subn(replacement, sanitized)
        if count > 0:
            sanitized = new_text
            if pii_type not in detected_types:
                detected_types.append(pii_type)

    if detected_types:
        return GuardrailResult(
            passed=True,  # Not blocked — sanitized and allowed
            action=GuardAction.SANITIZE,
            guardrail_name="PII",
            reason=f"PII detected and sanitized: {', '.join(detected_types)}",
            sanitized_text=sanitized,
            metadata={"detected": True, "types": detected_types},
        )

    return GuardrailResult(
        passed=True,
        action=GuardAction.ALLOW,
        guardrail_name="PII",
        reason="No PII detected",
        sanitized_text=text,
        metadata={"detected": False},
    )
