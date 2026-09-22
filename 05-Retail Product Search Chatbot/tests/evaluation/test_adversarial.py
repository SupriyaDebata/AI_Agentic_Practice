"""Automated adversarial test runner.

Runs every case in adversarial.json through the input guardrail pipeline
and validates the actual action against the expected action.

Usage:
    pytest tests/evaluation/test_adversarial.py -v

Or standalone:
    python tests/evaluation/test_adversarial.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

_ADVERSARIAL_FILE = Path(__file__).parent / "adversarial.json"

_CASES: list[dict] = json.loads(_ADVERSARIAL_FILE.read_text(encoding="utf-8"))


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    """Execute one adversarial case through the input guardrail pipeline."""
    from app.guardrails.pipeline.input_guardrail_pipeline import run_input_guardrails

    t0 = time.perf_counter()
    guarded, _ = run_input_guardrails(case["input"])
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    # Determine actual action
    if guarded.blocked:
        actual_action = "BLOCK"
        triggered_guardrail = next(
            (r.guardrail_name for r in guarded.guardrail_results if not r.passed), "unknown"
        )
    elif guarded.was_sanitized:
        actual_action = "SANITIZE"
        triggered_guardrail = next(
            (r.guardrail_name for r in guarded.guardrail_results if r.action.value == "SANITIZE"),
            "PII",
        )
    else:
        actual_action = "ALLOW"
        triggered_guardrail = None

    passed = actual_action == case["expectedAction"]

    return {
        "id": case["id"],
        "category": case["category"],
        "expected_action": case["expectedAction"],
        "actual_action": actual_action,
        "passed": passed,
        "guardrail_triggered": triggered_guardrail,
        "latency_ms": latency_ms,
        "input_preview": case["input"][:60] + ("…" if len(case["input"]) > 60 else ""),
    }


@pytest.mark.parametrize("case", _CASES, ids=[c["id"] for c in _CASES])
def test_adversarial_case(case: dict[str, Any]) -> None:
    result = _run_case(case)
    assert result["passed"], (
        f"{result['id']} [{result['category']}]: "
        f"expected {result['expected_action']}, got {result['actual_action']}. "
        f"Guardrail triggered: {result['guardrail_triggered']}. "
        f"Input: {result['input_preview']}"
    )


# ── Standalone runner ─────────────────────────────────────────────────────────

def run_all_and_report() -> None:
    """Run all adversarial cases and print a formatted report."""
    results = [_run_case(c) for c in _CASES]

    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed

    col_w = [6, 16, 10, 10, 6, 22, 10]
    header = (
        f"{'ID':<{col_w[0]}} {'Category':<{col_w[1]}} "
        f"{'Expected':<{col_w[2]}} {'Actual':<{col_w[3]}} "
        f"{'Pass':<{col_w[4]}} {'Guardrail':<{col_w[5]}} {'ms':>{col_w[6]}}"
    )
    sep = "─" * (sum(col_w) + len(col_w))

    print(f"\n{'='*72}")
    print("  Adversarial Guardrail Test Report — Week 7")
    print(f"{'='*72}")
    print(header)
    print(sep)

    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(
            f"{r['id']:<{col_w[0]}} {r['category']:<{col_w[1]}} "
            f"{r['expected_action']:<{col_w[2]}} {r['actual_action']:<{col_w[3]}} "
            f"{status:<{col_w[4]+2}} {(r['guardrail_triggered'] or '—'):<{col_w[5]}} "
            f"{r['latency_ms']:>{col_w[6]}}"
        )

    print(sep)
    print(f"\n  Results: {passed}/{len(results)} passed  |  {failed} failed")

    if failed > 0:
        print("\n  ── Failed cases ──")
        for r in results:
            if not r["passed"]:
                print(f"  {r['id']}: expected {r['expected_action']}, got {r['actual_action']}")
                print(f"         Input: {r['input_preview']}")

    avg_ms = round(sum(r["latency_ms"] for r in results) / len(results), 1)
    print(f"\n  Average guardrail latency: {avg_ms} ms")
    print(f"{'='*72}\n")

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    run_all_and_report()
