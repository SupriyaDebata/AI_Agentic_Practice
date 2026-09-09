"""Data filtering utilities for interactive dashboard filtering."""

from typing import Optional


def filter_results_by_status(results: list, status: str) -> list:
    """Filter question results by pass/fail status."""
    if status == "ALL":
        return results

    return [
        r for r in results
        if r.get("overall_question_status") == status
    ]


def filter_results_by_metric_threshold(results: list, metric: str, threshold: float) -> list:
    """Filter results where a specific metric falls below threshold."""
    return [
        r for r in results
        if r.get("metrics", {}).get(metric, 1.0) < threshold
    ]


def filter_results_by_question_text(results: list, search_text: str) -> list:
    """Filter results by question text (case-insensitive)."""
    if not search_text:
        return results

    search_lower = search_text.lower()
    return [
        r for r in results
        if search_lower in r.get("question", "").lower()
    ]


def filter_citations_by_relevance(citations: list, min_score: float = 0.0) -> list:
    """Filter citations by minimum relevance score."""
    return [
        c for c in citations
        if c.get("score", 0) >= min_score
    ]


def rank_results_by_metric(results: list, metric: str, ascending: bool = False) -> list:
    """Sort results by metric score."""
    return sorted(
        results,
        key=lambda r: r.get("metrics", {}).get(metric, 0),
        reverse=not ascending,
    )


def group_results_by_metric_status(results: list, metric: str, threshold: float) -> dict:
    """Group results by metric pass/fail status."""
    passed = []
    failed = []

    for result in results:
        score = result.get("metrics", {}).get(metric, 1.0)
        if score >= threshold:
            passed.append(result)
        else:
            failed.append(result)

    return {"passed": passed, "failed": failed}


def get_metric_distribution(results: list, metric: str) -> dict:
    """Get statistical distribution of a metric across results."""
    scores = [
        r.get("metrics", {}).get(metric)
        for r in results
        if r.get("metrics", {}).get(metric) is not None
    ]

    if not scores:
        return {}

    scores.sort()
    return {
        "min": min(scores),
        "max": max(scores),
        "mean": sum(scores) / len(scores),
        "median": scores[len(scores) // 2],
        "q25": scores[len(scores) // 4],
        "q75": scores[len(scores) * 3 // 4],
        "count": len(scores),
    }


def get_top_failing_questions(results: list, limit: int = 5) -> list:
    """Get top N questions with lowest overall performance."""
    scored = []

    for result in results:
        metrics = result.get("metrics", {})
        avg_score = (
            sum(v for v in metrics.values() if isinstance(v, (int, float)))
            / len([v for v in metrics.values() if isinstance(v, (int, float))])
            if metrics else 0
        )
        scored.append((result, avg_score))

    return [r for r, _ in sorted(scored, key=lambda x: x[1])[:limit]]


def get_questions_by_failure_reason(results: list) -> dict:
    """Group failing questions by primary failure reason (metric)."""
    failures_by_metric = {}

    for result in results:
        if result.get("overall_question_status") == "FAIL":
            metrics = result.get("metrics", {})
            # Find the metric with lowest score
            failed_metric = min(
                ((k, v) for k, v in metrics.items() if isinstance(v, (int, float))),
                key=lambda x: x[1],
                default=(None, None)
            )[0]

            if failed_metric:
                if failed_metric not in failures_by_metric:
                    failures_by_metric[failed_metric] = []
                failures_by_metric[failed_metric].append(result)

    return failures_by_metric


def extract_hallucinations(results: list) -> list:
    """Extract hallucinated answers from results."""
    hallucinations = []

    for result in results:
        metrics = result.get("metrics", {})
        # Flag hallucinations when faithfulness is low but answer is given
        if (metrics.get("faithfulness", 0) < 0.5 and
            result.get("generated_answer") != "I could not find this in the provided documents."):

            hallucinations.append({
                "question": result.get("question"),
                "answer": result.get("generated_answer"),
                "ground_truth": result.get("ground_truth_answer"),
                "faithfulness": metrics.get("faithfulness", 0),
                "relevancy": metrics.get("answer_relevancy", 0),
            })

    return hallucinations


def extract_performance_issues(results: list) -> list:
    """Extract questions with performance issues."""
    issues = []

    for result in results:
        metrics = result.get("metrics", {})
        status = result.get("overall_question_status")

        if status == "FAIL":
            failed_metrics = [
                k for k, v in metrics.items()
                if isinstance(v, (int, float)) and v < 0.5
            ]

            issues.append({
                "question": result.get("question"),
                "failed_metrics": failed_metrics,
                "key_issue": failed_metrics[0] if failed_metrics else "unknown",
            })

    return issues
