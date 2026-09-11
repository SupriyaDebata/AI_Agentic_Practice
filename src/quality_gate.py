"""src/quality_gate.py -- Quality gate logic: evaluate metrics against thresholds."""

from dataclasses import dataclass
from typing import Optional

from src import config


@dataclass
class MetricResult:
    """Result for a single metric."""
    name: str
    score: float
    threshold: float
    passed: bool

    @property
    def status(self) -> str:
        return "[PASS]" if self.passed else "[FAIL]"


@dataclass
class QualityGateResult:
    """Overall quality gate evaluation result."""
    overall_status: str
    passed: bool
    metric_results: list[MetricResult]
    summary: str

    @property
    def status_emoji(self) -> str:
        return "[PASS]" if self.passed else "[FAIL]"


class QualityGateEvaluator:
    """Evaluate RAG quality against configured thresholds."""

    def __init__(self, thresholds: Optional[dict] = None):
        self.thresholds = thresholds or config.QUALITY_GATE_THRESHOLDS

    def evaluate_metrics(self, scores: dict) -> QualityGateResult:
        """Evaluate metrics against thresholds.

        Args:
            scores: dict of {metric_name: score (0-1)}

        Returns:
            QualityGateResult with pass/fail status and details
        """
        metric_results = []

        # Evaluate each metric against its threshold.
        # Skip metrics absent from scores — they are batch-only (grounded_refusal)
        # or RAGAS-only (answer_semantic_similarity) and not computed in live sessions.
        # Treating an absent metric as 0.0 would cause permanent false FAILs.
        for metric_name, threshold in self.thresholds.items():
            if metric_name not in scores:
                continue
            score = scores[metric_name]
            if score is None:
                continue
            passed = score >= threshold
            metric_results.append(
                MetricResult(
                    name=metric_name,
                    score=score,
                    threshold=threshold,
                    passed=passed,
                )
            )

        # Overall status: all metrics must pass
        all_passed = all(m.passed for m in metric_results)
        overall_status = "[PASS]" if all_passed else "[FAIL]"

        summary = self._build_summary(metric_results, all_passed)

        return QualityGateResult(
            overall_status=overall_status,
            passed=all_passed,
            metric_results=metric_results,
            summary=summary,
        )

    def _build_summary(self, metric_results: list[MetricResult], all_passed: bool) -> str:
        """Build a human-readable summary of the evaluation."""
        if all_passed:
            return "All quality metrics passed. RAG system is production-ready."

        failed_metrics = [m for m in metric_results if not m.passed]
        failed_names = ", ".join(m.name for m in failed_metrics)

        largest_gap = max((m.threshold - m.score) for m in failed_metrics)
        needs = f"Improve {failed_names} (gap: {largest_gap:.2%})"

        return f"Quality gate FAILED. {needs}"

