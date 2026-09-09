"""Utilities for loading evaluation reports and datasets."""

import json
from pathlib import Path
from typing import Optional
import streamlit as st


@st.cache_data(ttl=30)  # Reduced from 120s to 30s for fresher data
def load_latest_report(reports_dir: str) -> Optional[dict]:
    """Load the most recent evaluation report from reports directory.
    
    Cache TTL: 30 seconds (reduced from 120s for faster data refresh)
    To clear cache: call load_latest_report.clear() after generating new reports
    """
    path = Path(reports_dir)
    if not path.exists():
        return None

    try:
        json_files = list(path.glob("evaluation_report*.json"))
        if not json_files:
            return None
        latest = max(json_files, key=lambda p: p.stat().st_mtime)
        with open(latest) as f:
            data = json.load(f)
            return data
    except Exception as e:
        # Log error but don't crash
        return None


@st.cache_data(ttl=60)
def load_golden_dataset(dataset_path: str) -> Optional[dict]:
    """Load golden Q&A dataset."""
    path = Path(dataset_path)
    if not path.exists():
        return None

    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load dataset: {e}")
        return None


def get_report_summary(report: dict) -> dict:
    """Extract summary metrics from evaluation report."""
    if not report or "evaluation" not in report:
        return {}

    eval_data = report["evaluation"]
    metrics = eval_data.get("metrics", {})

    return {
        "evaluation_id": eval_data.get("evaluation_id", "N/A"),
        "dataset": eval_data.get("dataset", "N/A"),
        "test_count": eval_data.get("test_count", 0),
        "metrics": metrics,
        "per_question_results": eval_data.get("per_question_results", []),
    }


def compute_gate_status(metrics: dict, thresholds: dict) -> dict:
    """Determine pass/fail status for each metric."""
    results = {
        "passed": [],
        "failed": [],
        "details": {}
    }

    for metric_name, threshold in thresholds.items():
        if metric_name not in metrics:
            results["details"][metric_name] = {
                "score": None,
                "threshold": threshold,
                "status": "MISSING",
            }
            results["failed"].append(metric_name)
            continue

        score = metrics[metric_name]
        status = "PASS" if score >= threshold else "FAIL"

        results["details"][metric_name] = {
            "score": score,
            "threshold": threshold,
            "status": status,
        }

        if status == "PASS":
            results["passed"].append(metric_name)
        else:
            results["failed"].append(metric_name)

    results["overall_status"] = "PASS" if not results["failed"] else "FAIL"
    results["pass_rate"] = len(results["passed"]) / len(thresholds) if thresholds else 0

    return results
