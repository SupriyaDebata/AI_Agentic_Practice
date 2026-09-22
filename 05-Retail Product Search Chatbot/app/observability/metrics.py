"""In-process production monitoring metrics.

Records per-request metrics in an in-memory list and exposes a
get_monitoring_report() summary.  For a real deployment, persist these
to a time-series store (Prometheus, CloudWatch, etc.) instead.

Usage:
    from app.observability.metrics import RequestMetrics, record, get_monitoring_report
    metrics = RequestMetrics(request_id="abc")
    # ... fill in fields ...
    record(metrics)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RequestMetrics:
    request_id: str
    timestamp: float = field(default_factory=time.time)

    # Guardrail decisions
    allowed: bool = True
    blocked: bool = False
    sanitized: bool = False
    guardrail_triggered: str = ""   # name of the first guardrail that fired

    # Latency (all in milliseconds)
    total_latency_ms: float = 0.0
    guardrail_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    sql_latency_ms: float = 0.0
    vector_latency_ms: float = 0.0
    bm25_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    output_guardrail_latency_ms: float = 0.0

    # Token / cost
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_inr: float = 0.0

    # Response quality
    no_match: bool = False
    hallucination_prevented: bool = False
    fallback_used: bool = False
    retry_count: int = 0

    # Errors
    error: str = ""


# In-memory store (replace with persistent backend in production)
_request_log: List[RequestMetrics] = []


def record(metrics: RequestMetrics) -> None:
    _request_log.append(metrics)


def get_monitoring_report() -> dict:
    """Return aggregated production monitoring statistics."""
    if not _request_log:
        return {"total_requests": 0, "message": "No requests recorded yet"}

    total = len(_request_log)
    allowed = sum(1 for r in _request_log if r.allowed)
    blocked = sum(1 for r in _request_log if r.blocked)
    sanitized = sum(1 for r in _request_log if r.sanitized)
    no_match = sum(1 for r in _request_log if r.no_match)
    hallucination = sum(1 for r in _request_log if r.hallucination_prevented)
    fallback = sum(1 for r in _request_log if r.fallback_used)
    errors = sum(1 for r in _request_log if r.error)
    retries = sum(r.retry_count for r in _request_log)

    latencies = [r.total_latency_ms for r in _request_log if r.total_latency_ms > 0]
    llm_lat = [r.llm_latency_ms for r in _request_log if r.llm_latency_ms > 0]
    ret_lat = [r.retrieval_latency_ms for r in _request_log if r.retrieval_latency_ms > 0]
    costs = [r.estimated_cost_inr for r in _request_log]

    def _avg(lst: list) -> float:
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    def _p95(lst: list) -> float:
        if not lst:
            return 0.0
        return round(sorted(lst)[max(0, int(len(lst) * 0.95) - 1)], 1)

    return {
        "total_requests": total,
        "allowed_requests": allowed,
        "blocked_requests": blocked,
        "sanitized_requests": sanitized,
        "guardrail_block_rate_pct": round(blocked / total * 100, 1) if total else 0.0,
        "avg_total_latency_ms": _avg(latencies),
        "p95_total_latency_ms": _p95(latencies),
        "avg_llm_latency_ms": _avg(llm_lat),
        "avg_retrieval_latency_ms": _avg(ret_lat),
        "avg_cost_inr_per_request": _avg(costs),
        "total_cost_inr": round(sum(costs), 4),
        "no_match_rate_pct": round(no_match / total * 100, 1) if total else 0.0,
        "hallucination_prevention_count": hallucination,
        "error_rate_pct": round(errors / total * 100, 1) if total else 0.0,
        "total_retries": retries,
        "fallback_rate_pct": round(fallback / total * 100, 1) if total else 0.0,
    }
