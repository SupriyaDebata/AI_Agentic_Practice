"""Plotly chart components for data visualization."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from evaluation.dashboards.utils.formatters import format_metric_name, format_percentage


@st.cache_data
def _build_bar_chart(metrics_tuple: tuple, thresholds_tuple: tuple, title: str):
    """Build bar chart (cached)."""
    metrics_dict = dict(metrics_tuple)
    thresholds_dict = dict(thresholds_tuple)
    metric_names = list(thresholds_dict.keys())
    scores = [metrics_dict.get(name, 0) for name in metric_names]
    threshold_vals = [thresholds_dict[name] for name in metric_names]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[format_metric_name(name) for name in metric_names],
        x=scores,
        orientation="h",
        name="Score",
        marker=dict(color=["#00AA00" if s >= t else "#FF0000" for s, t in zip(scores, threshold_vals)]),
        text=[f"{s:.2f}" for s in scores],
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        y=[format_metric_name(name) for name in metric_names],
        x=threshold_vals,
        mode="markers",
        name="Threshold",
        marker=dict(size=10, color="#FF9500", symbol="diamond"),
    ))
    fig.update_layout(title=title, xaxis_title="Score", yaxis_title="Metric", height=350, showlegend=True, hovermode="y unified", margin=dict(l=150))
    return fig


def metric_bar_chart(metrics: dict, thresholds: dict, title: str = "Metrics Performance") -> None:
    """Display metrics as horizontal bar chart with threshold lines."""
    metrics_tuple = tuple(sorted(metrics.items()))
    thresholds_tuple = tuple(sorted(thresholds.items()))
    fig = _build_bar_chart(metrics_tuple, thresholds_tuple, title)
    st.plotly_chart(fig, use_container_width=True)


def metric_gauge_chart(score: float, threshold: float, metric_name: str) -> None:
    """Display metric as gauge chart."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score * 100,
        title={"text": format_metric_name(metric_name)},
        delta={"reference": threshold * 100, "suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "navy"},
            "steps": [
                {"range": [0, threshold * 100], "color": "#FFE5E5"},
                {"range": [threshold * 100, 100], "color": "#E5FFE5"},
            ],
            "threshold": {
                "line": {"color": "#FF0000", "width": 3},
                "thickness": 0.75,
                "value": threshold * 100,
            }
        }
    ))

    fig.update_layout(height=300, margin=dict(l=20, r=20, t=70, b=20))
    st.plotly_chart(fig, use_container_width=True)


def metric_distribution_chart(results: list, metric: str, threshold: float = None) -> None:
    """Display distribution of metric values across questions."""
    scores = [
        r.get("metrics", {}).get(metric)
        for r in results
        if r.get("metrics", {}).get(metric) is not None
    ]

    if not scores:
        st.info("No data available for this metric")
        return

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=scores,
        nbinsx=20,
        name="Distribution",
        marker=dict(color="#0099FF"),
    ))

    if threshold:
        fig.add_vline(
            x=threshold,
            line_dash="dash",
            line_color="#FF0000",
            annotation_text=f"Threshold: {threshold:.2f}",
            annotation_position="top right",
        )

    fig.update_layout(
        title=f"Distribution: {format_metric_name(metric)}",
        xaxis_title="Score",
        yaxis_title="Count",
        height=300,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


def per_question_heatmap(results: list, metrics: list) -> None:
    """Display heatmap of metric scores per question."""
    data = []
    question_texts = []

    for result in results[:15]:  # Show top 15 for readability
        q_metrics = result.get("metrics", {})
        data.append([q_metrics.get(m, 0) for m in metrics])
        question_texts.append(result.get("question", "")[:30] + "...")

    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=[format_metric_name(m) for m in metrics],
        y=question_texts,
        colorscale="RdYlGn",
        zmid=0.5,
    ))

    fig.update_layout(
        title="Question-Level Metrics Heatmap",
        height=500,
        margin=dict(b=150),
    )

    st.plotly_chart(fig, use_container_width=True)


def cumulative_pass_chart(results: list) -> None:
    """Display cumulative pass rate chart."""
    total = len(results)
    passed = sum(1 for r in results if r.get("overall_question_status") == "PASS")

    fig = go.Figure()

    fig.add_trace(go.Pie(
        labels=["Passed", "Failed"],
        values=[passed, total - passed],
        marker=dict(colors=["#00AA00", "#FF0000"]),
        textposition="inside",
        textinfo="label+percent",
    ))

    fig.update_layout(
        title=f"Overall Pass Rate ({passed}/{total} questions)",
        height=350,
        showlegend=True,
    )

    st.plotly_chart(fig, use_container_width=True)


def metric_trend_chart(trend_data: list) -> None:
    """Display metric trends over time (multiple evaluations)."""
    if not trend_data or len(trend_data) < 2:
        st.info("Need at least 2 evaluations to show trends")
        return

    df = pd.DataFrame(trend_data)

    fig = go.Figure()

    for metric_name in df.columns[1:]:  # Skip timestamp column
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df[metric_name],
            mode="lines+markers",
            name=format_metric_name(metric_name),
        ))

    fig.update_layout(
        title="Metric Trends",
        xaxis_title="Time",
        yaxis_title="Score",
        height=400,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


def retrieval_precision_recall_chart(results: list) -> None:
    """Display precision vs recall scatter plot."""
    data = []

    for result in results:
        metrics = result.get("metrics", {})
        data.append({
            "precision": metrics.get("context_precision", 0),
            "recall": metrics.get("context_recall", 0),
            "question": result.get("question", "")[:30],
        })

    df = pd.DataFrame(data)

    fig = px.scatter(
        df,
        x="recall",
        y="precision",
        hover_data={"question": True},
        title="Precision vs Recall",
        labels={"precision": "Context Precision", "recall": "Context Recall"},
    )

    fig.update_layout(height=400)
    fig.add_hline(y=0.75, line_dash="dash", line_color="red", annotation_text="Threshold")
    fig.add_vline(x=0.75, line_dash="dash", line_color="red")

    st.plotly_chart(fig, use_container_width=True)


def metric_box_plot(results: list, metric: str) -> None:
    """Display box plot of metric distribution."""
    scores = [
        r.get("metrics", {}).get(metric)
        for r in results
        if r.get("metrics", {}).get(metric) is not None
    ]

    if not scores:
        st.info("No data available")
        return

    fig = go.Figure(data=[go.Box(y=scores, name=format_metric_name(metric))])

    fig.update_layout(
        title=f"Distribution: {format_metric_name(metric)}",
        height=300,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)
