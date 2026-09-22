"""Core guardrail result model shared by all guardrail components."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class GuardAction(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    SANITIZE = "SANITIZE"
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"


class GuardrailResult(BaseModel):
    passed: bool
    action: GuardAction
    guardrail_name: str
    reason: str = ""
    sanitized_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
