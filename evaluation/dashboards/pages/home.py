"""Home page: overall quality gate status and key metrics."""

import streamlit as st
from evaluation.dashboards.utils.loaders import load_latest_report, compute_gate_status
from evaluation.dashboards.components import metric_cards, charts, tables
from src import config


def render_home():
    """Render home page with overall status and summary."""
    st.markdown("# 🏠 Quality Gate Status")

    # Load report
    report = load_latest_report(config.EVALUATION_REPORTS_PATH)
    if not report:
        st.warning("📭 No evaluation report found. Please run an evaluation first.")
        st.info("""
        To generate an evaluation report:
        1. Upload documents to the main ChatOnDocument app
        2. Run `/batch` command from .claude/commands/
        3. Report will appear here
        """)
        return

    eval_data = report.get("evaluation", {})
    metrics = eval_data.get("metrics", {})
    results = eval_data.get("per_question_results", [])

    # Compute gate status
    gate_status = compute_gate_status(metrics, config.QUALITY_GATE_THRESHOLDS)
    overall_status = gate_status["overall_status"]

    # Header: Pass/Fail Banner
    st.divider()
    if overall_status == "PASS":
        st.success("✅ **QUALITY GATE: PASS**")
    else:
        st.error("❌ **QUALITY GATE: FAIL**")

    st.divider()

    # Key Metrics at a Glance
    st.markdown("## 📊 Key Metrics")

    key_metrics = ["faithfulness", "answer_relevancy", "citation_accuracy"]
    metric_cards.key_metric_row(metrics, key_metrics)

    st.divider()

    # Summary Statistics
    st.markdown("## 📈 Summary Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Questions", len(results))

    with col2:
        passed = sum(1 for r in results if r.get("overall_question_status") == "PASS")
        st.metric("Passed Questions", passed)

    with col3:
        failed = len(results) - passed
        st.metric("Failed Questions", failed)

    with col4:
        pass_rate = (passed / len(results) * 100) if results else 0
        st.metric("Pass Rate", f"{pass_rate:.1f}%")

    st.divider()

    # Metric Performance Overview
    st.markdown("## 🎯 Metrics Overview")

    # Bar chart
    charts.metric_bar_chart(metrics, config.QUALITY_GATE_THRESHOLDS)

    st.divider()

    # Pass/Fail by Metric
    st.markdown("## ✅ Metric-Level Status")

    metric_cols = st.columns(2)

    with metric_cols[0]:
        st.markdown("### Passed Metrics")
        if gate_status["passed"]:
            for metric in gate_status["passed"]:
                st.success(f"✅ {metric}")
        else:
            st.info("None")

    with metric_cols[1]:
        st.markdown("### Failed Metrics")
        if gate_status["failed"]:
            for metric in gate_status["failed"]:
                st.error(f"❌ {metric}")
        else:
            st.success("None")

    st.divider()

    # Overall Metrics Table
    st.markdown("## 📋 Detailed Metrics Table")
    tables.metric_summary_table(metrics, config.QUALITY_GATE_THRESHOLDS)

    st.divider()

    # Pass Rate Pie Chart
    st.markdown("## 🥧 Pass Rate Distribution")
    charts.cumulative_pass_chart(results)

    st.divider()

    # Top Issues (if failing)
    if overall_status == "FAIL":
        st.markdown("## 🚨 Key Issues")

        failed_metrics = gate_status["failed"]
        for metric in failed_metrics:
            score = metrics.get(metric, 0)
            threshold = config.QUALITY_GATE_THRESHOLDS.get(metric, 0)
            gap = threshold - score

            st.warning(f"""
            **{metric.replace('_', ' ').title()}**
            - Current: {score:.3f}
            - Threshold: {threshold:.3f}
            - Gap: {gap:.3f}
            """)

    st.divider()

    # Quick Navigation
    st.markdown("## 🔍 Quick Navigation")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 View All Metrics", use_container_width=True):
            st.session_state.page = "metrics"
            st.rerun()

    with col2:
        if st.button("❓ Question Analysis", use_container_width=True):
            st.session_state.page = "questions"
            st.rerun()

    with col3:
        if st.button("🚨 Hallucinations", use_container_width=True):
            st.session_state.page = "hallucinations"
            st.rerun()

    st.divider()

    # Report Info
    st.caption(f"""
    📌 **Evaluation ID:** {eval_data.get('evaluation_id', 'N/A')}
    | **Dataset:** {eval_data.get('dataset', 'N/A')}
    | **Split:** {eval_data.get('split', 'N/A')}
    """)
