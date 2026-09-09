"""Retrieval quality analysis page."""

import streamlit as st
from evaluation.dashboards.utils.loaders import load_latest_report
from evaluation.dashboards.utils.filters import get_metric_distribution
from evaluation.dashboards.components import charts, tables
from src import config


def render_retrieval():
    """Render retrieval quality analysis page."""
    st.markdown("# 🔎 Retrieval Quality")

    report = load_latest_report(config.EVALUATION_REPORTS_PATH)
    if not report:
        st.warning("No evaluation report found")
        return

    eval_data = report.get("evaluation", {})
    metrics = eval_data.get("metrics", {})
    results = eval_data.get("per_question_results", [])

    st.divider()

    # Overview
    st.markdown("## 📊 Retrieval Metrics Overview")

    col1, col2, col3, col4 = st.columns(4)

    retrieval_metrics = {
        "retrieval_f1": "Top-K F1 Score",
        "context_precision": "Context Precision",
        "context_recall": "Context Recall",
        "citation_accuracy": "Citation Accuracy"
    }

    metric_values = [
        metrics.get("retrieval_f1", 0),
        metrics.get("context_precision", 0),
        metrics.get("context_recall", 0),
        metrics.get("citation_accuracy", 0),
    ]

    for col, (metric_key, metric_label), value in zip(
        [col1, col2, col3, col4], retrieval_metrics.items(), metric_values
    ):
        with col:
            threshold = config.QUALITY_GATE_THRESHOLDS.get(metric_key, 0)
            status = "✅" if value >= threshold else "❌"
            st.metric(metric_label, f"{value:.2f}", delta=status)

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["F1 Score", "Precision vs Recall", "Citation Accuracy", "Details"])

    with tab1:
        st.markdown("## Top-K F1 Score")

        f1_threshold = config.QUALITY_GATE_THRESHOLDS["retrieval_f1"]

        st.markdown(f"""
        **Threshold:** {f1_threshold:.2f}
        **Current Score:** {metrics.get('retrieval_f1', 0):.3f}
        """)

        charts.metric_distribution_chart(results, "retrieval_f1", f1_threshold)

        st.divider()

        st.markdown("### Distribution Statistics")
        dist = get_metric_distribution(results, "retrieval_f1")

        if dist:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Min", f"{dist['min']:.3f}")
            with col2:
                st.metric("Q1 (25%)", f"{dist['q25']:.3f}")
            with col3:
                st.metric("Median", f"{dist['median']:.3f}")
            with col4:
                st.metric("Max", f"{dist['max']:.3f}")

    with tab2:
        st.markdown("## Context Precision vs Recall")

        st.markdown("""
        - **Precision:** % of retrieved chunks relevant to the question
        - **Recall:** % of necessary information present in retrieved chunks
        """)

        charts.retrieval_precision_recall_chart(results)

        st.divider()

        st.markdown("### Interpretation Guide")

        col1, col2 = st.columns(2)

        with col1:
            st.info("""
            **High Precision, Low Recall:**
            - Retrieving relevant docs but missing some
            - Solution: Improve embedding or chunk strategy
            """)

        with col2:
            st.warning("""
            **Low Precision, High Recall:**
            - Finding all relevant docs but with noise
            - Solution: Improve similarity threshold or filtering
            """)

    with tab3:
        st.markdown("## Citation Accuracy")

        citation_threshold = config.QUALITY_GATE_THRESHOLDS["citation_accuracy"]
        citation_score = metrics.get("citation_accuracy", 0)

        st.markdown(f"""
        **Threshold:** {citation_threshold:.2f}
        **Current Score:** {citation_score:.3f}
        """)

        charts.metric_distribution_chart(results, "citation_accuracy", citation_threshold)

        st.divider()

        st.markdown("### Definition")
        st.info("""
        Citation Accuracy measures what percentage of factual claims in the generated
        answer are properly cited from the retrieved context. This is critical for
        trust and compliance.
        """)

        st.divider()

        st.markdown("### High-Accuracy Questions")

        high_accuracy = [
            r for r in results
            if r.get("metrics", {}).get("citation_accuracy", 0) >= citation_threshold
        ]

        st.markdown(f"**{len(high_accuracy)} of {len(results)} questions** have high citation accuracy")

        if high_accuracy:
            with st.expander("View examples"):
                for result in high_accuracy[:5]:
                    st.markdown(f"**Q:** {result.get('question', '')}")
                    st.caption(f"**A:** {result.get('generated_answer', '')[:100]}...")

    with tab4:
        st.markdown("## Retrieval Quality Details")

        st.markdown("### Metrics Table")
        tables.retrieval_quality_table(results)

        st.divider()

        st.markdown("### Retrieval Metrics Breakdown")

        breakdown_cols = st.columns(2)

        with breakdown_cols[0]:
            st.markdown("### Context Precision")
            precision_dist = get_metric_distribution(results, "context_precision")
            if precision_dist:
                st.write(f"""
                - **Mean:** {precision_dist['mean']:.3f}
                - **Median:** {precision_dist['median']:.3f}
                - **Threshold:** {config.QUALITY_GATE_THRESHOLDS['context_precision']:.3f}
                """)

        with breakdown_cols[1]:
            st.markdown("### Context Recall")
            recall_dist = get_metric_distribution(results, "context_recall")
            if recall_dist:
                st.write(f"""
                - **Mean:** {recall_dist['mean']:.3f}
                - **Median:** {recall_dist['median']:.3f}
                - **Threshold:** {config.QUALITY_GATE_THRESHOLDS['context_recall']:.3f}
                """)

    st.divider()

    # Recommendations
    st.markdown("## 💡 Recommendations")

    f1_score = metrics.get("retrieval_f1", 0)
    precision = metrics.get("context_precision", 0)
    recall = metrics.get("context_recall", 0)

    issues = []

    if f1_score < config.QUALITY_GATE_THRESHOLDS["retrieval_f1"]:
        issues.append("❌ Retrieval F1 score below threshold")

    if precision < config.QUALITY_GATE_THRESHOLDS["context_precision"]:
        issues.append("❌ Retrieve too many irrelevant chunks")

    if recall < config.QUALITY_GATE_THRESHOLDS["context_recall"]:
        issues.append("❌ Missing relevant information in retrieval")

    if not issues:
        st.success("✅ Retrieval quality is good!")
    else:
        st.warning("### Issues Detected")
        for issue in issues:
            st.write(issue)

        st.info("""
        ### Action Items
        1. Review chunk size and overlap settings
        2. Check embedding model quality
        3. Analyze similarity threshold
        4. Verify document preprocessing
        5. Test with different TOP_K values
        """)
