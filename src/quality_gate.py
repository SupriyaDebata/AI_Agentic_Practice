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

        # Evaluate each metric against its threshold
        for metric_name, threshold in self.thresholds.items():
            score = scores.get(metric_name, 0.0)
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

    def evaluate_batch(self, batch_scores: list[dict]) -> dict:
        """Evaluate a batch of evaluation results.

        Args:
            batch_scores: list of evaluation dicts with 'scores' key

        Returns:
            dict with aggregate metrics and pass/fail status
        """
        if not batch_scores:
            return {"status": "NO_DATA", "message": "No evaluation data available"}

        # Aggregate scores across batch
        metric_aggregates = {}
        for eval_result in batch_scores:
            scores = eval_result.get("scores", {})
            for metric_name, score in scores.items():
                if metric_name not in metric_aggregates:
                    metric_aggregates[metric_name] = []
                metric_aggregates[metric_name].append(score)

        # Calculate averages
        aggregated_scores = {}
        for metric_name, scores in metric_aggregates.items():
            aggregated_scores[metric_name] = sum(scores) / len(scores)

        # Evaluate overall
        result = self.evaluate_metrics(aggregated_scores)

        return {
            "status": result.overall_status,
            "passed": result.passed,
            "summary": result.summary,
            "aggregate_scores": aggregated_scores,
            "metric_results": [
                {
                    "name": m.name,
                    "score": round(m.score, 4),
                    "threshold": m.threshold,
                    "passed": m.passed,
                    "gap": round(m.threshold - m.score, 4) if not m.passed else 0.0,
                }
                for m in result.metric_results
            ],
            "sample_count": len(batch_scores),
        }

    def _build_summary(self, metric_results: list[MetricResult], all_passed: bool) -> str:
        """Build a human-readable summary of the evaluation."""
        if all_passed:
            return "All quality metrics passed. RAG system is production-ready."

        failed_metrics = [m for m in metric_results if not m.passed]
        failed_names = ", ".join(m.name for m in failed_metrics)

        largest_gap = max((m.threshold - m.score) for m in failed_metrics)
        needs = f"Improve {failed_names} (gap: {largest_gap:.2%})"

        return f"Quality gate FAILED. {needs}"

    def get_metric_details(self, metric_name: str) -> dict:
        """Get details about a specific metric."""
        descriptions = {
            "faithfulness": "Answer stays grounded in context without hallucinations",
            "answer_relevancy": "Answer directly addresses the question",
            "context_precision": "Retrieved context is relevant to the question",
            "context_recall": "All relevant information is in retrieved context",
            "citation_accuracy": "Cited facts are present in source documents",
            "hallucination_score": "Answer doesn't invent facts (1.0 = no hallucinations)",
            "retrieval_f1": "Balance of retrieval precision and recall",
            "response_completeness": "Answer is sufficiently detailed and complete",
        }

        return {
            "name": metric_name,
            "description": descriptions.get(metric_name, "Unknown metric"),
            "threshold": self.thresholds.get(metric_name, 0.0),
            "min": 0.0,
            "max": 1.0,
        }
