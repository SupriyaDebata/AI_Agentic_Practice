"""Reusable metric card components for displaying key values and status."""

import streamlit as st
from evaluation.dashboards.utils.formatters import (
    format_metric_name,
    format_score,
    format_percentage,
    get_status_icon,
)


def metric_card(metric_name: str, score: float, threshold: float, description: str = "") -> None:
    """Display a single metric card with score and threshold."""
    status = "PASS" if score >= threshold else "FAIL"
    icon = get_status_icon(status)

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"**{format_metric_name(metric_name)}**")
        if description:
            st.caption(description)

    with col2:
        st.metric(label="Score", value=format_score(score), delta=format_score(threshold))

    with col3:
        if status == "PASS":
            st.success(f"{icon} PASS")
        else:
            st.error(f"{icon} FAIL")


def key_metric_row(metrics: dict, metric_names: list) -> None:
    """Display row of key metrics as columns."""
    cols = st.columns(len(metric_names))

    for col, metric_name in zip(cols, metric_names):
        with col:
            if metric_name in metrics:
                st.metric(
                    label=format_metric_name(metric_name),
                    value=format_percentage(metrics[metric_name]),
                )
            else:
                st.metric(label=format_metric_name(metric_name), value="N/A")


def metrics_grid(metrics: dict, thresholds: dict, cols: int = 4) -> None:
    """Display metrics in a grid layout."""
    grid_cols = st.columns(cols)

    for idx, metric_name in enumerate(thresholds.keys()):
        col = grid_cols[idx % cols]
        with col:
            score = metrics.get(metric_name, 0)
            threshold = thresholds[metric_name]
            status = "PASS" if score >= threshold else "FAIL"

            if status == "PASS":
                st.info(f"✅ {format_metric_name(metric_name)}: {format_score(score)}")
            else:
                st.warning(f"❌ {format_metric_name(metric_name)}: {format_score(score)}")
