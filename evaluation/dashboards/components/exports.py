"""Export and download functionality for evaluation reports."""

import json
import csv
import io
from datetime import datetime
import streamlit as st
import pandas as pd


def export_metrics_json(metrics: dict, evaluation_id: str = None) -> str:
    """Export metrics as JSON string."""
    return json.dumps({
        "export_timestamp": datetime.now().isoformat(),
        "evaluation_id": evaluation_id or "manual_export",
        "metrics": metrics,
    }, indent=2)


def export_metrics_csv(metrics: dict, thresholds: dict) -> str:
    """Export metrics as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Score", "Threshold", "Status"])

    for metric_name, threshold in thresholds.items():
        score = metrics.get(metric_name)
        status = "PASS" if score and score >= threshold else "FAIL"
        writer.writerow([metric_name, score or "N/A", threshold, status])

    return output.getvalue()


def export_results_csv(results: list) -> str:
    """Export per-question results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Question ID", "Question", "Faithfulness", "Answer Relevancy",
        "Context Precision", "Context Recall", "Citation Accuracy", "Status"
    ])

    for result in results:
        metrics = result.get("metrics", {})
        writer.writerow([
            result.get("q_id", ""),
            result.get("question", ""),
            metrics.get("faithfulness", ""),
            metrics.get("answer_relevancy", ""),
            metrics.get("context_precision", ""),
            metrics.get("context_recall", ""),
            metrics.get("citation_accuracy", ""),
            result.get("overall_question_status", ""),
        ])

    return output.getvalue()


def export_full_report_json(report: dict) -> str:
    """Export complete evaluation report as JSON."""
    return json.dumps(report, indent=2, default=str)


def create_download_section() -> None:
    """Create download buttons for various report formats."""
    st.subheader("📥 Download Reports")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**JSON Format**")
        if st.button("📄 Download JSON", key="btn_json"):
            st.info("JSON export not yet integrated")

    with col2:
        st.write("**CSV Format**")
        if st.button("📊 Download CSV", key="btn_csv"):
            st.info("CSV export not yet integrated")

    with col3:
        st.write("**HTML Report**")
        if st.button("🌐 Download HTML", key="btn_html"):
            st.info("HTML export not yet integrated")


def download_button(label: str, data: str, filename: str, file_type: str = "text/plain") -> None:
    """Create a download button for given data."""
    st.download_button(label=label, data=data, file_name=filename, mime=file_type)


def export_to_csv_file(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes."""
    return df.to_csv(index=False).encode()


def export_to_json_file(data: dict) -> bytes:
    """Convert dict to JSON bytes."""
    return json.dumps(data, indent=2, default=str).encode()
