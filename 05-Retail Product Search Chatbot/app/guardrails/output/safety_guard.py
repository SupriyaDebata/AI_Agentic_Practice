"""Output safety guard — prevents internal information leakage in responses.

Detects if the LLM accidentally reveals:
  - System prompt contents
  - Internal tool configurations
  - MCP server details
  - Internal instructions or rules
"""
from __future__ import annotations

import re
from typing import List

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction

_UNSAFE_OUTPUT_PATTERNS: List[str] = [
    # System prompt leakage
    r"(?:my\s+)?system\s+prompt\s*(?:is|says?|reads?|contains?)\s*[:\-]",
    r"my\s+(?:instructions?|rules?|constraints?)\s+(?:are|say|tell\s+me)\s*[:\-]",
    # MCP/tool configuration leakage
    r"mcp\s+(?:server|tool|configuration|config)\s*[:\-=\s]",
    r"tool\s+(?:schema|configuration|definition)\s*[:\-]",
    # Internal system details
    r"internal\s+(?:instructions?|rules?|config|system|prompt)\s*[:\-]",
    r"i\s+(?:was\s+)?(?:programmed|trained|instructed|told)\s+to\s+(?:never|always|keep|hide)",
    # SQL/database schema exposure
    r"(?:table|column|schema)\s+(?:name|structure)\s+(?:is|are)\s*[:\-]",
    r"(?:database|db)\s+(?:password|credentials?|connection\s+string)\s*[:\-=]",
]

_COMPILED: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _UNSAFE_OUTPUT_PATTERNS
]


def check_safety_output(text: str) -> GuardrailResult:
    """Return FALLBACK if output contains potentially leaked internal info, ALLOW otherwise."""
    for pattern in _COMPILED:
        if pattern.search(text):
            return GuardrailResult(
                passed=False,
                action=GuardAction.FALLBACK,
                guardrail_name="OutputSafetyGuard",
                reason="Output may contain leaked internal system information",
                metadata={"pattern": pattern.pattern[:80]},
            )

    return GuardrailResult(
        passed=True,
        action=GuardAction.ALLOW,
        guardrail_name="OutputSafetyGuard",
        reason="Output safety check passed",
    )
