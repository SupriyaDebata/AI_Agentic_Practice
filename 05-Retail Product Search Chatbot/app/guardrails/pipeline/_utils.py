"""Shared utilities for guardrail pipelines."""
import time


def _elapsed_ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)
