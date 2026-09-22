"""Per-request LLM cost calculator.

Tracks token usage and estimates cost per request.  Pricing is configurable
via settings and clearly marked as an estimate when exact rates are unknown.

For local Ollama models (llama3.x) cost is zero — the estimate is still
recorded so the monitoring report has a consistent structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from app.config import get_logger

logger = get_logger(__name__)

# ── Pricing table (USD per 1 000 tokens) ─────────────────────────────────────
# Ollama / local models have no per-token cost.
# Cloud model pricing as of 2025 — update here, not scattered in business logic.
_MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # Local (zero cost)
    "llama3.2": {"input": 0.0, "output": 0.0},
    "llama3.1": {"input": 0.0, "output": 0.0},
    "llama3": {"input": 0.0, "output": 0.0},
    "mistral": {"input": 0.0, "output": 0.0},
    # OpenAI
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    # Anthropic Claude (model IDs as registered in the API)
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
    "claude-opus-5": {"input": 0.015, "output": 0.075},
}

USD_TO_INR = 84.0  # approximate conversion rate — update periodically


@dataclass
class TokenUsage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def _model_key(self) -> str:
        return self.model.split(":")[0].lower()

    @property
    def _pricing(self) -> Dict[str, float]:
        return _MODEL_PRICING.get(self._model_key, {"input": 0.0, "output": 0.0})

    @property
    def is_free_local_model(self) -> bool:
        return self._model_key in _MODEL_PRICING and _MODEL_PRICING[self._model_key]["input"] == 0.0

    @property
    def estimated_cost_usd(self) -> float:
        p = self._pricing
        return round(
            (self.input_tokens / 1000) * p["input"]
            + (self.output_tokens / 1000) * p["output"],
            6,
        )

    @property
    def estimated_cost_inr(self) -> float:
        return round(self.estimated_cost_usd * USD_TO_INR, 4)

    @property
    def is_estimated(self) -> bool:
        """True when the model is not in the pricing table."""
        return self._model_key not in _MODEL_PRICING

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "estimated_cost_inr": self.estimated_cost_inr,
            "is_estimated": self.is_estimated,
            "is_free_local_model": self.is_free_local_model,
        }


