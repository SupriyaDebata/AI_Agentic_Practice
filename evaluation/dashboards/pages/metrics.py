"""Comprehensive metrics analysis page."""

import streamlit as st
from evaluation.dashboards.utils.loaders import load_latest_report
from evaluation.dashboards.utils.filters import get_metric_distribution
from evaluation.dashboards.components import metric_cards, charts, tables
from src import config


def render_metrics():
    """Render detailed metrics page."""
    st.markdown("# 📈 Metrics & Performance")

    report = load_latest_report(config.EVALUATION_REPORTS_PATH)
    if not report:
        st.warning("No evaluation report found")
        return

    eval_data = report.get("evaluation", {})
    metrics = eval_data.get("metrics", {})
    results = eval_data.get("per_question_results", [])

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Individual Metrics", "Distribution", "Comparison"])

    with tab1:
        st.markdown("## 📊 All Metrics Overview")

        # Metrics grid
        metric_cards.metrics_grid(metrics, config.QUALITY_GATE_THRESHOLDS, cols=4)

        st.divider()

        # Bar chart
        charts.metric_bar_chart(metrics, config.QUALITY_GATE_THRESHOLDS)

        st.divider()

        # Summary table
        st.markdown("## 📋 Metrics Summary Table")
        tables.metric_summary_table(metrics, config.QUALITY_GATE_THRESHOLDS)

    with tab2:
        st.markdown("## 🎯 Individual Metric Details")

        # Select metric
        selected_metric = st.selectbox(
            "Select a metric to analyze:",
            list(config.QUALITY_GATE_THRESHOLDS.keys()),
            key="metric_select"
        )

        # Show metric details
        metric_def = config.QUALITY_GATE_THRESHOLDS
        score = metrics.get(selected_metric, 0)
        threshold = metric_def[selected_metric]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Score", f"{score:.3f}")

        with col2:
            st.metric("Threshold", f"{threshold:.3f}")

        with col3:
            status = "PASS" if score >= threshold else "FAIL"
            if status == "PASS":
                st.success(f"✅ {status}")
            else:
                st.error(f"❌ {status}")

        st.divider()

        # Distribution chart
        st.markdown("### Distribution Across Questions")
        charts.metric_distribution_chart(results, selected_metric, threshold)

        st.divider()

        # Box plot
        st.markdown("### Statistical Distribution")
        charts.metric_box_plot(results, selected_metric)

        st.divider()

        # Distribution stats
        st.markdown("### Distribution Statistics")
        dist = get_metric_distribution(results, selected_metric)

        if dist:
            stat_cols = st.columns(4)

            with stat_cols[0]:
                st.metric("Min", f"{dist['min']:.3f}")

            with stat_cols[1]:
                st.metric("Mean", f"{dist['mean']:.3f}")

            with stat_cols[2]:
                st.metric("Median", f"{dist['median']:.3f}")

            with stat_cols[3]:
                st.metric("Max", f"{dist['max']:.3f}")

    with tab3:
        st.markdown("## 📊 Metric Distributions")

        # Show distribution for all metrics
        metric_cols = st.columns(2)

        for idx, metric_name in enumerate(list(config.QUALITY_GATE_THRESHOLDS.keys())[:4]):
            with metric_cols[idx % 2]:
                threshold = config.QUALITY_GATE_THRESHOLDS[metric_name]
                charts.metric_distribution_chart(results, metric_name, threshold)

    with tab4:
        st.markdown("## 🔄 Metric Comparison")

        st.info("💡 Comparison feature allows tracking improvements across evaluation runs.")

        # Create hypothetical comparison data
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Current Run")
            tables.metric_summary_table(metrics, config.QUALITY_GATE_THRESHOLDS)

        with col2:
            st.markdown("### Previous Run (Hypothetical)")
            st.info("Previous run data not available. Run multiple evaluations to see trends.")

    st.divider()

    # Metric Details Panel
    st.markdown("## 📝 Metric Definitions")

    with st.expander("Expand to see metric descriptions", expanded=False):
        for metric_name, threshold in config.QUALITY_GATE_THRESHOLDS.items():
            with st.container(border=True):
                st.markdown(f"**{metric_name.replace('_', ' ').title()}**")
                st.caption(f"Threshold: {threshold:.3f}")

                if metric_name == "faithfulness":
                    st.write("Measures whether the generated answer contains hallucinated facts not present in the retrieved context.")

                elif metric_name == "answer_relevancy":
                    st.write("Measures how well the generated answer directly addresses the question.")

                elif metric_name == "context_precision":
                    st.write("Measures the percentage of retrieved context chunks that are relevant to answering the question.")

                elif metric_name == "context_recall":
                    st.write("Measures whether all necessary information to answer the question is present in the retrieved context.")

                elif metric_name == "answer_semantic_similarity":
                    st.write("Measures semantic similarity between the generated answer and the ground truth answer.")

                elif metric_name == "citation_accuracy":
                    st.write("Measures what percentage of factual claims in the answer are properly cited from the retrieved context.")

                elif metric_name == "grounded_refusal":
                    st.write("Binary metric: system should refuse when answer is not found in context.")

                elif metric_name == "retrieval_f1":
                    st.write("F1 score for retrieval quality (harmonic mean of precision and recall).")
