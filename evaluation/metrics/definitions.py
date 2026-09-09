"""Metric definitions and quality gate thresholds.

Defines:
- RAGAS metrics (faithfulness, relevancy, precision, recall, semantic similarity)
- Custom metrics (citation accuracy, grounded refusal, retrieval F1)
- Pass/fail logic and aggregation strategy
"""

from src import config


METRIC_DEFINITIONS = {
    "faithfulness": {
        "threshold": 0.85,
        "description": "No hallucinated facts in answer (0.0-1.0)",
        "implementation": "ragas",
        "required": True,
        "weight": 1.0,
        "rationale": "Strict: no hallucinations tolerated",
    },
    "answer_relevancy": {
        "threshold": 0.80,
        "description": "Answer directly addresses question (0.0-1.0)",
        "implementation": "ragas",
        "required": True,
        "weight": 1.0,
        "rationale": "High relevancy expected for grounded answers",
    },
    "context_precision": {
        "threshold": 0.75,
        "description": "% of retrieved chunks relevant to question (0.0-1.0)",
        "implementation": "ragas",
        "required": True,
        "weight": 1.0,
        "rationale": "Acceptable noise in top-5 results",
    },
    "context_recall": {
        "threshold": 0.75,
        "description": "Can all facts from ground truth be derived from context (0.0-1.0)",
        "implementation": "ragas",
        "required": True,
        "weight": 1.0,
        "rationale": "Most facts must be present in retrieved context",
    },
    "answer_semantic_similarity": {
        "threshold": 0.75,
        "description": "Semantic closeness to ground truth answer (0.0-1.0)",
        "implementation": "ragas",
        "required": True,
        "weight": 1.0,
        "rationale": "Meaning match without exact word match",
    },
    "citation_accuracy": {
        "threshold": 0.90,
        "description": "% of answer facts with valid citations (0.0-1.0)",
        "implementation": "custom",
        "required": True,
        "weight": 1.0,
        "rationale": "Strict: citations are binding for compliance",
    },
    "grounded_refusal": {
        "threshold": 1.0,
        "description": "Binary: system refuses when answer absent (0.0 or 1.0)",
        "implementation": "custom",
        "required": True,
        "weight": 1.0,
        "rationale": "No false answers on negative test cases",
    },
    "retrieval_f1": {
        "threshold": 0.70,
        "description": "IR metric: harmonic mean of precision & recall (0.0-1.0)",
        "implementation": "custom",
        "required": True,
        "weight": 1.0,
        "rationale": "Standard information retrieval evaluation",
    },
}


QUALITY_GATE_RULES = {
    "gate_type": "AND",
    "description": "All required metrics must pass for overall PASS",
    "required_metrics": list(
        k for k, v in METRIC_DEFINITIONS.items() if v["required"]
    ),
    "pass_condition": "all required metrics >= threshold",
    "fail_condition": "any required metric < threshold",
}


def get_metric_definition(metric_name: str) -> dict:
    """Get definition for a single metric."""
    if metric_name not in METRIC_DEFINITIONS:
        raise ValueError(f"Unknown metric: {metric_name}")
    return METRIC_DEFINITIONS[metric_name]


def get_threshold(metric_name: str) -> float:
    """Get threshold for a single metric."""
    return get_metric_definition(metric_name)["threshold"]


def is_metric_required(metric_name: str) -> bool:
    """Check if metric is required for gate."""
    return get_metric_definition(metric_name)["required"]


def get_required_metrics() -> list[str]:
    """Get list of required metrics."""
    return QUALITY_GATE_RULES["required_metrics"]


def format_metric_display(metric_name: str) -> str:
    """Format metric name for display (e.g., faithfulness -> Faithfulness)."""
    return " ".join(w.capitalize() for w in metric_name.split("_"))
