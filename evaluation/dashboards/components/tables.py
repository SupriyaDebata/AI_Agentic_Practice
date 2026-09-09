"""Interactive table components for dashboard."""

import streamlit as st
import pandas as pd
from evaluation.dashboards.utils.formatters import (
    format_metric_name,
    format_score,
    format_percentage,
    get_status_icon,
)


def metric_summary_table(metrics: dict, thresholds: dict) -> None:
    """Display metrics summary table."""
    rows = []

    for metric_name in sorted(thresholds.keys()):
        score = metrics.get(metric_name)
        threshold = thresholds[metric_name]

        if score is None:
            status = "MISSING"
            score_str = "N/A"
        else:
            status = "PASS" if score >= threshold else "FAIL"
            score_str = format_score(score)

        rows.append({
            "Metric": format_metric_name(metric_name),
            "Score": score_str,
            "Threshold": format_score(threshold),
            "Status": f"{get_status_icon(status)} {status}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def question_results_table(results: list, show_columns: list = None) -> None:
    """Display per-question evaluation results table."""
    if not results:
        st.info("No results available")
        return

    rows = []

    for idx, result in enumerate(results, 1):
        metrics = result.get("metrics", {})
        status = result.get("overall_question_status", "UNKNOWN")

        row = {
            "#": idx,
            "Question": result.get("question", "")[:50] + "...",
            "Faithfulness": format_percentage(metrics.get("faithfulness")),
            "Relevancy": format_percentage(metrics.get("answer_relevancy")),
            "Precision": format_percentage(metrics.get("context_precision")),
            "Recall": format_percentage(metrics.get("context_recall")),
            "Status": f"{get_status_icon(status)} {status}",
        }

        if show_columns:
            row = {k: v for k, v in row.items() if k in show_columns}

        rows.append(row)

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def detailed_question_view(result: dict) -> None:
    """Display detailed view of a single question result."""
    with st.container(border=True):
        # Question and Ground Truth
        st.subheader("Question & Ground Truth")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Question:**")
            st.write(result.get("question", "N/A"))

        with col2:
            st.markdown("**Expected Answer:**")
            st.write(result.get("ground_truth_answer", "N/A"))

        st.divider()

        # Generated Answer
        st.subheader("Generated Answer")
        st.info(result.get("generated_answer", "N/A"))

        st.divider()

        # Metrics
        st.subheader("Metrics")
        metrics = result.get("metrics", {})
        metric_cols = st.columns(len(metrics))

        for col, (metric_name, score) in zip(metric_cols, metrics.items()):
            with col:
                status = "✅" if score >= 0.75 else "❌"
                st.metric(
                    label=format_metric_name(metric_name),
                    value=format_percentage(score),
                    delta=status,
                )

        st.divider()

        # Citations
        st.subheader("Citations")
        citations = result.get("citations", [])
        if citations:
            citation_rows = []
            for c in citations:
                citation_rows.append({
                    "Source": c.get("source"),
                    "Page/Sheet": c.get("page"),
                    "Type": c.get("type"),
                    "Relevance": format_percentage(c.get("score", 0)),
                })
            df = pd.DataFrame(citation_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("No citations")

        st.divider()

        # Retrieved Context
        with st.expander("Retrieved Context"):
            st.text(result.get("retrieved_context", "N/A"))


def retrieval_quality_table(results: list) -> None:
    """Display retrieval quality metrics table."""
    rows = []

    for result in results:
        metrics = result.get("metrics", {})

        rows.append({
            "Question": result.get("question", "")[:40] + "...",
            "Top-K F1": format_percentage(metrics.get("retrieval_f1")),
            "Precision": format_percentage(metrics.get("context_precision")),
            "Recall": format_percentage(metrics.get("context_recall")),
            "Citation Acc": format_percentage(metrics.get("citation_accuracy")),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def hallucination_table(hallucinations: list) -> None:
    """Display hallucination examples table."""
    if not hallucinations:
        st.info("✅ No hallucinations detected")
        return

    rows = []

    for h in hallucinations:
        rows.append({
            "Question": h.get("question", "")[:40] + "...",
            "Faithfulness": format_percentage(h.get("faithfulness")),
            "Generated": h.get("answer", "")[:50] + "...",
            "Expected": h.get("ground_truth", "")[:50] + "...",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def failure_analysis_table(failures: dict) -> None:
    """Display failure analysis by metric."""
    if not failures:
        st.info("No failures to analyze")
        return

    rows = []

    for metric_name, results in failures.items():
        avg_score = (
            sum(r.get("metrics", {}).get(metric_name, 0) for r in results) / len(results)
            if results else 0
        )

        rows.append({
            "Metric": format_metric_name(metric_name),
            "Failed Questions": len(results),
            "Avg Score": format_score(avg_score),
            "Primary Issue": True,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


