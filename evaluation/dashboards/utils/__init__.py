"""Dashboard utility modules."""

from .loaders import (
    load_latest_report,
    load_golden_dataset,
    get_report_summary,
    compute_gate_status,
)
from .formatters import (
    format_metric_name,
    format_percentage,
    format_score,
    format_time_ms,
    get_status_icon,
    get_status_color,
    build_metrics_dataframe,
    build_question_results_dataframe,
    build_retrieval_dataframe,
)
from .filters import (
    filter_results_by_status,
    filter_results_by_metric_threshold,
    filter_results_by_question_text,
    filter_citations_by_relevance,
    rank_results_by_metric,
    group_results_by_metric_status,
    get_metric_distribution,
    get_top_failing_questions,
    get_questions_by_failure_reason,
    extract_hallucinations,
    extract_performance_issues,
)

__all__ = [
    "load_latest_report",
    "load_golden_dataset",
    "get_report_summary",
    "compute_gate_status",
    "format_metric_name",
    "format_percentage",
    "format_score",
    "format_time_ms",
    "get_status_icon",
    "get_status_color",
    "build_metrics_dataframe",
    "build_question_results_dataframe",
    "build_retrieval_dataframe",
    "filter_results_by_status",
    "filter_results_by_metric_threshold",
    "filter_results_by_question_text",
    "filter_citations_by_relevance",
    "rank_results_by_metric",
    "group_results_by_metric_status",
    "get_metric_distribution",
    "get_top_failing_questions",
    "get_questions_by_failure_reason",
    "extract_hallucinations",
    "extract_performance_issues",
]
