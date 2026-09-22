"""Prompt injection detection guard.

Uses a list of deterministic regex patterns to detect common prompt injection
attempts before the request reaches the LLM.  No LLM call is made here —
cheap and fast.
"""
from __future__ import annotations

import re
from typing import List

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction

_INJECTION_PATTERNS: List[str] = [
    r"ignore\s+(your\s+)?(previous|all|prior|above|earlier)\s+(instructions?|prompts?|rules?|context|constraints?)",
    r"ignore\s+(?:the\s+)?system\s+prompt",
    r"print\s+(your\s+)?(system\s+prompt|internal\s+instructions?|hidden\s+rules?|prompt)",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions?|hidden|internal|mcp|tools?|configuration|secrets?)",
    r"show\s+(?:me\s+)?(?:your\s+)?(tools?|system\s+prompt|instructions?|mcp\s+config)",
    r"what\s+(are\s+)?your\s+(instructions?|system\s+prompt|rules?|constraints?|hidden)",
    r"you\s+are\s+now\s+(unrestricted|jailbroken|free|dan|without\s+rules?)",
    r"act\s+as\s+(dan|an?\s+unrestricted|developer\s+mode|jailbreak|evil|bad)",
    r"\bdeveloper\s+mode\b",
    r"\bjailbreak\b",
    r"bypass\s+(your\s+)?(restrictions?|filters?|safety|guardrails?|rules?)",
    r"pretend\s+(you\s+(are|have\s+no)|to\s+be\s+(?:a\s+)?(?:different|unrestricted|evil))",
    r"disregard\s+(previous|all|prior|your)\s+(instructions?|rules?|constraints?|prompts?)",
    r"from\s+now\s+on\s+(you\s+are|ignore|forget|discard)",
    r"new\s+(?:system\s+)?(?:instructions?|rules?|prompt)\s*[:=]",
    r"override\s+(?:your\s+)?(instructions?|rules?|system|constraints?)",
    r"forget\s+(?:all\s+)?(?:previous|your)\s+(instructions?|rules?|training)",
    r"you\s+(?:must\s+)?(?:now\s+)?(?:obey|follow)\s+(?:only\s+)?(?:my|these\s+new)\s+(instructions?|rules?|commands?)",
    r"sudo\s+mode",
    r"admin\s+(?:mode|override|access|password)",
    r"(?:encode|base64|hex)\s+(?:your|the)\s+(?:instructions?|prompt|rules?)",
]

_COMPILED: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS
]


def check_injection(text: str) -> GuardrailResult:
    """Return BLOCK result if prompt injection pattern found, ALLOW otherwise."""
    for pattern in _COMPILED:
        if pattern.search(text):
            return GuardrailResult(
                passed=False,
                action=GuardAction.BLOCK,
                guardrail_name="PromptInjection",
                reason="Prompt injection attempt detected",
                metadata={"matched_pattern": pattern.pattern[:80]},
            )

    return GuardrailResult(
        passed=True,
        action=GuardAction.ALLOW,
        guardrail_name="PromptInjection",
        reason="No injection patterns detected",
    )
