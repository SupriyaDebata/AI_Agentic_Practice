"""Data formatting and styling utilities for dashboard display."""

import pandas as pd
from typing import Any


def format_metric_name(name: str) -> str:
    """Format metric name for display (e.g., faithfulness -> Faithfulness)."""
    return " ".join(w.capitalize() for w in name.split("_"))


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format decimal as percentage."""
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def format_score(value: float, decimals: int = 3) -> str:
    """Format metric score."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def format_time_ms(ms: float) -> str:
    """Format milliseconds to readable string."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms / 1000:.2f}s"


def get_status_icon(status: str) -> str:
    """Get emoji icon for status."""
    icons = {
        "PASS": "✅",
        "FAIL": "❌",
        "MISSING": "⚠️",
        "WARNING": "⚠️",
    }
    return icons.get(status, "•")


def get_status_color(status: str) -> str:
    """Get color for status indicator."""
    colors = {
        "PASS": "#00AA00",
        "FAIL": "#FF0000",
        "MISSING": "#FFAA00",
        "WARNING": "#FFAA00",
    }
    return colors.get(status, "#999999")


def build_metrics_dataframe(metrics: dict, thresholds: dict) -> pd.DataFrame:
    """Build formatted metrics dataframe for display."""
    rows = []

    for metric_name, threshold in thresholds.items():
        if metric_name not in metrics:
            score = None
            status = "MISSING"
        else:
            score = metrics[metric_name]
            status = "PASS" if score >= threshold else "FAIL"

        rows.append({
            "Metric": format_metric_name(metric_name),
            "Score": format_score(score) if score is not None else "N/A",
            "Threshold": format_score(threshold),
            "Status": status,
            "Pass/Fail": f"{get_status_icon(status)} {status}",
        })

    return pd.DataFrame(rows)


def build_question_results_dataframe(results: list) -> pd.DataFrame:
    """Build dataframe from per-question evaluation results."""
    rows = []

    for result in results:
        metrics = result.get("metrics", {})
        overall_status = result.get("overall_question_status", "UNKNOWN")

        rows.append({
            "Question ID": result.get("q_id", "N/A"),
            "Question": result.get("question", "")[:60] + "...",
            "Faithfulness": format_score(metrics.get("faithfulness")),
            "Relevancy": format_score(metrics.get("answer_relevancy")),
            "Context Precision": format_score(metrics.get("context_precision")),
            "Citation Accuracy": format_score(metrics.get("citation_accuracy")),
            "Status": f"{get_status_icon(overall_status)} {overall_status}",
        })

    return pd.DataFrame(rows)


def build_retrieval_dataframe(results: list) -> pd.DataFrame:
    """Build retrieval quality metrics dataframe."""
    rows = []

    for result in results:
        metrics = result.get("metrics", {})

        rows.append({
            "Question": result.get("question", "")[:50] + "...",
            "Top-K Accuracy": format_percentage(metrics.get("retrieval_f1")),
            "Context Precision": format_percentage(metrics.get("context_precision")),
            "Context Recall": format_percentage(metrics.get("context_recall")),
            "Citation Accuracy": format_percentage(metrics.get("citation_accuracy")),
        })

    return pd.DataFrame(rows)


