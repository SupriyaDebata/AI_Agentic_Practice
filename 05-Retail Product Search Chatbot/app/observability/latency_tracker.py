"""Per-request latency tracker with named spans.

Usage:
    tracker = LatencyTracker()
    tracker.start_span("input_guardrails")
    # ... do work ...
    tracker.end_span("input_guardrails")
    print(tracker.to_dict())
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class LatencyTracker:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    _wall_start: float = field(default_factory=time.perf_counter)
    _span_starts: Dict[str, float] = field(default_factory=dict)
    _span_ms: Dict[str, float] = field(default_factory=dict)

    def start_span(self, name: str) -> None:
        self._span_starts[name] = time.perf_counter()

    def end_span(self, name: str) -> float:
        if name not in self._span_starts:
            return 0.0
        elapsed = round((time.perf_counter() - self._span_starts.pop(name)) * 1000, 1)
        self._span_ms[name] = elapsed
        return elapsed

    def record_span(self, name: str, ms: float) -> None:
        """Record a pre-measured duration (e.g. from an external sub-call)."""
        self._span_ms[name] = round(ms, 1)

    @property
    def total_ms(self) -> float:
        return round((time.perf_counter() - self._wall_start) * 1000, 1)

    def get_span(self, name: str, default: float = 0.0) -> float:
        return self._span_ms.get(name, default)

    def to_dict(self) -> dict:
        result: dict = {"request_id": self.request_id, "total_ms": self.total_ms}
        result.update(self._span_ms)
        return result
