"""Input guardrail pipeline.

Runs all input guards in the order optimized for minimal latency:
  1. InputSafetyGuard  — cheapest: blocks obvious abuse immediately
  2. PII              — sanitize before anything touches LLM or LangSmith
  3. PromptInjection  — block before query parsing
  4. PriceManipulation — block before retrieval
  5. TopicGuard       — block off-topic before expensive retrieval


  All checks are deterministic regex — total pipeline latency is typically < 5 ms.
"""
from __future__ import annotations

import time
from typing import Tuple

from app.guardrails.models.guardrail_result import GuardrailResult, GuardAction
from app.guardrails.models.guarded_request import GuardedRequest
from app.guardrails.input.safety_guard import check_safety_input
from app.guardrails.input.pii_guard import check_pii
from app.guardrails.input.injection_guard import check_injection
from app.guardrails.input.price_manipulation_guard import check_price_manipulation
from app.guardrails.input.topic_guard import check_topic
from app.guardrails.pipeline._utils import _elapsed_ms
from app.config import get_logger

logger = get_logger(__name__)

# Human-readable block messages keyed by guardrail name
_BLOCK_MESSAGES: dict[str, str] = {
    "InputSafetyGuard": (
        "I'm unable to process that request. "
        "Please ask me about kids' clothing products."
    ),
    "PromptInjection": (
        "I can help you find kids' clothing products, "
        "but I can't provide internal instructions or override my configuration."
    ),
    "PriceManipulationGuard": (
        "I can search the catalog for you, but I cannot modify product prices, "
        "stock levels, or any other catalog data."
    ),
    "TopicGuard": (
        "I only help with kids' clothing products. "
        "Please ask me about dresses, shirts, sizes, age groups, brands, or prices."
    ),
}


def run_input_guardrails(text: str) -> Tuple[GuardedRequest, float]:
    """Run all input guardrails and return (GuardedRequest, latency_ms).

    The returned GuardedRequest carries:
    - sanitized_text: text safe to send to the LLM (PII replaced)
    - blocked: True if the request must not reach the agent
    - block_reason: user-facing message when blocked
    - guardrail_results: full audit trail of every guard
    """
    t0 = time.perf_counter()
    results: list[GuardrailResult] = []
    current_text = text

    # ── 1. Input Safety ──────────────────────────────────────────────────────
    r = check_safety_input(current_text)
    results.append(r)
    if not r.passed:
        elapsed = _elapsed_ms(t0)
        logger.info("input_blocked", guardrail=r.guardrail_name, reason=r.reason)
        return _blocked(text, current_text, results, r.guardrail_name), elapsed

    # ── 2. PII sanitization ──────────────────────────────────────────────────
    r = check_pii(current_text)
    results.append(r)
    if r.sanitized_text:
        current_text = r.sanitized_text  # work on sanitized text from here on

    # ── 3. Prompt Injection ──────────────────────────────────────────────────
    r = check_injection(current_text)
    results.append(r)
    if not r.passed:
        elapsed = _elapsed_ms(t0)
        logger.info("input_blocked", guardrail=r.guardrail_name, reason=r.reason)
        return _blocked(text, current_text, results, r.guardrail_name), elapsed

    # ── 4. Price / Catalog Manipulation ─────────────────────────────────────
    r = check_price_manipulation(current_text)
    results.append(r)
    if not r.passed:
        elapsed = _elapsed_ms(t0)
        logger.info("input_blocked", guardrail=r.guardrail_name, reason=r.reason)
        return _blocked(text, current_text, results, r.guardrail_name), elapsed

    # ── 5. Topic / Domain ────────────────────────────────────────────────────
    r = check_topic(current_text)
    results.append(r)
    if not r.passed:
        elapsed = _elapsed_ms(t0)
        logger.info("input_blocked", guardrail=r.guardrail_name, reason=r.reason)
        return _blocked(text, current_text, results, r.guardrail_name), elapsed

    elapsed = _elapsed_ms(t0)
    logger.info("input_guardrails_passed", latency_ms=elapsed, sanitized=(current_text != text))
    return GuardedRequest(
        original_text=text,
        sanitized_text=current_text,
        guardrail_results=results,
        blocked=False,
    ), elapsed


# ── helpers ──────────────────────────────────────────────────────────────────

def _blocked(
    original: str,
    sanitized: str,
    results: list[GuardrailResult],
    guardrail_name: str,
) -> GuardedRequest:
    return GuardedRequest(
        original_text=original,
        sanitized_text=sanitized,
        guardrail_results=results,
        blocked=True,
        block_reason=_BLOCK_MESSAGES.get(
            guardrail_name,
            "Your request could not be processed. Please try again.",
        ),
    )
