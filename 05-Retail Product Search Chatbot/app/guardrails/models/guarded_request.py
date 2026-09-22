"""GuardedRequest — the input object after all input guardrails have run."""
from __future__ import annotations

from typing import List
from pydantic import BaseModel

from app.guardrails.models.guardrail_result import GuardrailResult


class GuardedRequest(BaseModel):
    original_text: str
    sanitized_text: str
    guardrail_results: List[GuardrailResult] = []
    blocked: bool = False
    block_reason: str = ""

    @property
    def was_sanitized(self) -> bool:
        from app.guardrails.models.guardrail_result import GuardAction
        return any(r.action == GuardAction.SANITIZE for r in self.guardrail_results)
