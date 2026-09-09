"""Quality gate logic and pass/fail determination.

Applies thresholds to metrics and determines overall gate status.
"""

from datetime import datetime
from typing import Any

from evaluation.metrics.definitions import (
    METRIC_DEFINITIONS,
    QUALITY_GATE_RULES,
    get_required_metrics,
)


def check_metric_pass(metric_name: str, score: float) -> bool:
    """Check if a single metric score passes its threshold."""
    if metric_name not in METRIC_DEFINITIONS:
        raise ValueError(f"Unknown metric: {metric_name}")
    threshold = METRIC_DEFINITIONS[metric_name]["threshold"]
    return score >= threshold


def apply_quality_gate(evaluation_report: dict) -> dict:
    """
    Apply quality gate logic to evaluation results.
    
    Args:
        evaluation_report: Dict with structure:
            {
                "overall_stats": {...},
                "metrics": {
                    "faithfulness": 0.88,
                    "answer_relevancy": 0.82,
                    ...
                },
                "per_question_results": [...]
            }
    
    Returns:
        {
            "gate_status": "PASS" | "FAIL",
            "timestamp": "2026-09-07T...",
            "passed_metrics": ["faithfulness", ...],
            "failed_metrics": [],
            "required_metrics": [...],
            "metric_details": {
                "faithfulness": {
                    "score": 0.88,
                    "threshold": 0.85,
                    "status": "PASS"
                },
                ...
            },
            "summary": {
                "total_metrics": 8,
                "passed": 8,
                "failed": 0,
                "pass_percentage": 100.0
            }
        }
    """
    metrics = evaluation_report.get("metrics", {})
    required = get_required_metrics()
    
    passed_metrics = []
    failed_metrics = []
    metric_details = {}
    
    # Check each required metric
    for metric_name in required:
        if metric_name not in metrics:
            failed_metrics.append(metric_name)
            metric_details[metric_name] = {
                "score": None,
                "threshold": METRIC_DEFINITIONS[metric_name]["threshold"],
                "status": "MISSING",
            }
            continue
        
        score = metrics[metric_name]
        passes = check_metric_pass(metric_name, score)
        threshold = METRIC_DEFINITIONS[metric_name]["threshold"]
        
        metric_details[metric_name] = {
            "score": score,
            "threshold": threshold,
            "status": "PASS" if passes else "FAIL",
            "description": METRIC_DEFINITIONS[metric_name]["description"],
        }
        
        if passes:
            passed_metrics.append(metric_name)
        else:
            failed_metrics.append(metric_name)
    
    # Determine gate status (AND logic: all required metrics must pass)
    gate_status = "PASS" if len(failed_metrics) == 0 else "FAIL"
    
    return {
        "gate_status": gate_status,
        "timestamp": datetime.now().isoformat(),
        "passed_metrics": passed_metrics,
        "failed_metrics": failed_metrics,
        "required_metrics": required,
        "metric_details": metric_details,
        "summary": {
            "total_metrics": len(required),
            "passed": len(passed_metrics),
            "failed": len(failed_metrics),
            "pass_percentage": (len(passed_metrics) / len(required) * 100) if required else 0,
        },
        "gate_rule": QUALITY_GATE_RULES["pass_condition"],
    }


def format_gate_result(gate_result: dict) -> str:
    """
    Format gate result for console output.
    
    Returns a human-readable summary.
    """
    status = gate_result["gate_status"]
    status_symbol = " PASS" if status == "PASS" else " FAIL"
    
    lines = [
        f"\n{'='*70}",
        f"QUALITY GATE RESULT: {status_symbol}",
        f"{'='*70}",
        f"Timestamp: {gate_result['timestamp']}",
        f"Metrics: {gate_result['summary']['passed']}/{gate_result['summary']['total_metrics']} passed",
        f"",
    ]
    
    # Show each metric
    for metric_name in gate_result["required_metrics"]:
        detail = gate_result["metric_details"][metric_name]
        if detail["status"] == "PASS":
            symbol = ""
        elif detail["status"] == "FAIL":
            symbol = ""
        else:
            symbol = "?"
        
        if detail["score"] is not None:
            lines.append(
                f"  {symbol} {metric_name:30s} {detail['score']:.3f} "
                f"(threshold: {detail['threshold']:.2f})"
            )
        else:
            lines.append(f"  {symbol} {metric_name:30s} MISSING")
    
    lines.append(f"{'='*70}\n")
    return "\n".join(lines)
