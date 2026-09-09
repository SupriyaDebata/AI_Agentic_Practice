"""Question-level analysis page."""

import streamlit as st
from evaluation.dashboards.utils.loaders import load_latest_report
from evaluation.dashboards.utils.filters import (
    filter_results_by_status,
    filter_results_by_question_text,
    rank_results_by_metric,
)
from evaluation.dashboards.components import tables, charts
from src import config


def render_questions():
    """Render question-level analysis page."""
    st.markdown("# ❓ Question-Level Analysis")

    report = load_latest_report(config.EVALUATION_REPORTS_PATH)
    if not report:
        st.warning("No evaluation report found")
        return

    eval_data = report.get("evaluation", {})
    results = eval_data.get("per_question_results", [])

    if not results:
        st.info("No question results available")
        return

    st.divider()

    # Filters
    st.markdown("## 🔍 Filter & Search")

    filter_cols = st.columns([2, 2, 1, 1])

    with filter_cols[0]:
        search_text = st.text_input("🔎 Search questions:", placeholder="e.g., customer, revenue, date")

    with filter_cols[1]:
        status_filter = st.selectbox("Filter by status:", ["ALL", "PASS", "FAIL"])

    with filter_cols[2]:
        sort_metric = st.selectbox(
            "Sort by metric:",
            ["faithfulness", "answer_relevancy", "context_precision"],
            key="sort_metric"
        )

    with filter_cols[3]:
        sort_order = st.radio("Order:", ["↓ DESC", "↑ ASC"], horizontal=True)

    # Apply filters
    filtered_results = filter_results_by_question_text(results, search_text)
    filtered_results = filter_results_by_status(filtered_results, status_filter)

    ascending = sort_order == "↑ ASC"
    filtered_results = rank_results_by_metric(filtered_results, sort_metric, ascending)

    st.divider()

    # Summary
    st.markdown(f"## 📊 Results ({len(filtered_results)} of {len(results)} questions)")

    col1, col2, col3 = st.columns(3)

    with col1:
        passed = sum(1 for r in filtered_results if r.get("overall_question_status") == "PASS")
        st.metric("Passed", passed)

    with col2:
        failed = len(filtered_results) - passed
        st.metric("Failed", failed)

    with col3:
        pass_rate = (passed / len(filtered_results) * 100) if filtered_results else 0
        st.metric("Pass Rate", f"{pass_rate:.0f}%")

    st.divider()

    # Results Table
    st.markdown("## 📋 Question Results Table")
    tables.question_results_table(filtered_results)

    st.divider()

    # Heatmap
    st.markdown("## 🔥 Metrics Heatmap (Top 15)")
    metrics_for_heatmap = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "citation_accuracy"]
    charts.per_question_heatmap(filtered_results[:15], metrics_for_heatmap)

    st.divider()

    # Detailed View
    st.markdown("## 🔍 Detailed Question View")

    with st.expander("Select a question to view details", expanded=False):
        question_options = [
            f"Q{idx+1}: {r.get('question', '')[:50]}..." for idx, r in enumerate(filtered_results)
        ]

        selected_idx = st.selectbox("Select question:", range(len(question_options)), format_func=lambda x: question_options[x])

        if selected_idx < len(filtered_results):
            selected_result = filtered_results[selected_idx]
            tables.detailed_question_view(selected_result)

    st.divider()

    # Pass/Fail Distribution
    st.markdown("## 📈 Pass/Fail Distribution")
    col1, col2 = st.columns(2)

    with col1:
        charts.cumulative_pass_chart(filtered_results)

    with col2:
        st.markdown("### Status Breakdown")

        passed = sum(1 for r in filtered_results if r.get("overall_question_status") == "PASS")
        failed = len(filtered_results) - passed

        st.markdown(f"""
        - **Passed:** {passed} questions ({passed/len(filtered_results)*100:.1f}%)
        - **Failed:** {failed} questions ({failed/len(filtered_results)*100:.1f}%)
        """)

        if failed > 0:
            st.warning(f"⚠️ {failed} questions need review")

    st.divider()

    # Top Performers
    st.markdown("## 🏆 Best Performing Questions")

    top_questions = rank_results_by_metric(filtered_results, "faithfulness", ascending=False)[:3]

    for idx, q in enumerate(top_questions, 1):
        with st.container(border=True):
            st.markdown(f"**#{idx}** {q.get('question', '')}")
            metrics = q.get("metrics", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Faithfulness", f"{metrics.get('faithfulness', 0):.2f}")
            with col2:
                st.metric("Relevancy", f"{metrics.get('answer_relevancy', 0):.2f}")
            with col3:
                st.metric("Citation Acc", f"{metrics.get('citation_accuracy', 0):.2f}")

    st.divider()

    # Worst Performing
    st.markdown("## 🔴 Lowest Scoring Questions")

    bottom_questions = rank_results_by_metric(filtered_results, "faithfulness", ascending=True)[:3]

    for idx, q in enumerate(bottom_questions, 1):
        with st.container(border=True):
            st.markdown(f"**#{idx}** {q.get('question', '')}")
            metrics = q.get("metrics", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Faithfulness", f"{metrics.get('faithfulness', 0):.2f}")
            with col2:
                st.metric("Relevancy", f"{metrics.get('answer_relevancy', 0):.2f}")
            with col3:
                st.metric("Citation Acc", f"{metrics.get('citation_accuracy', 0):.2f}")
