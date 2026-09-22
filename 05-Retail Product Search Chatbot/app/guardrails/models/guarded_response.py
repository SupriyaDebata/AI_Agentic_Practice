"""GuardedResponse — the output object after all output guardrails have run."""
from __future__ import annotations

from typing import Any, List
from pydantic import BaseModel

from app.guardrails.models.guardrail_result import GuardrailResult


class GuardedResponse(BaseModel):
    original_response: Any
    final_response: Any
    guardrail_results: List[GuardrailResult] = []
    blocked: bool = False
    fallback_used: bool = False
    retry_count: int = 0
