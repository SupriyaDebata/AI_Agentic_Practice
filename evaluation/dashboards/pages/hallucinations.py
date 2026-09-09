"""Hallucination detection and analysis page."""

import streamlit as st
from evaluation.dashboards.utils.loaders import load_latest_report
from evaluation.dashboards.utils.filters import (
    get_questions_by_failure_reason,
    extract_hallucinations,
)
from evaluation.dashboards.components import tables, charts
from src import config


def render_hallucinations():
    """Render hallucination detection page."""
    st.markdown("# 🚨 Hallucination & Refusal Analysis")

    report = load_latest_report(config.EVALUATION_REPORTS_PATH)
    if not report:
        st.warning("No evaluation report found")
        return

    eval_data = report.get("evaluation", {})
    metrics = eval_data.get("metrics", {})
    results = eval_data.get("per_question_results", [])

    st.divider()

    # Overview
    st.markdown("## 📊 Overview")

    col1, col2, col3, col4 = st.columns(4)

    faithfulness_score = metrics.get("faithfulness", 0)
    refusal_score = metrics.get("grounded_refusal", 0)

    with col1:
        threshold = config.QUALITY_GATE_THRESHOLDS["faithfulness"]
        status = "✅" if faithfulness_score >= threshold else "❌"
        st.metric("Faithfulness", f"{faithfulness_score:.2f}", delta=status)

    with col2:
        threshold = config.QUALITY_GATE_THRESHOLDS["grounded_refusal"]
        status = "✅" if refusal_score >= threshold else "❌"
        st.metric("Grounded Refusal", f"{refusal_score:.2f}", delta=status)

    with col3:
        # Count hallucinations
        hallucinations = extract_hallucinations(results)
        st.metric("Hallucinations Found", len(hallucinations))

    with col4:
        # Count refusals
        refusals = [r for r in results if r.get("generated_answer") == config.NO_ANSWER]
        st.metric("Refusals", len(refusals))

    st.divider()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Hallucinations", "Refusals", "Failure Analysis"])

    with tab1:
        st.markdown("## 🚨 Detected Hallucinations")

        hallucinations = extract_hallucinations(results)

        if not hallucinations:
            st.success("✅ No hallucinations detected!")
        else:
            st.warning(f"⚠️ {len(hallucinations)} potential hallucinations found")

            st.divider()

            # Hallucinations table
            st.markdown("### Hallucination Examples")
            tables.hallucination_table(hallucinations)

            st.divider()

            # Detailed view
            st.markdown("### Detailed Hallucination Analysis")

            for idx, h in enumerate(hallucinations[:5], 1):
                with st.container(border=True):
                    st.markdown(f"### #{idx} - Hallucination Example")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Question:**")
                        st.write(h.get("question", "N/A"))

                        st.markdown("**Generated Answer:**")
                        st.error(h.get("answer", "N/A"))

                    with col2:
                        st.markdown("**Expected Answer:**")
                        st.success(h.get("ground_truth", "N/A"))

                        st.markdown("**Metrics:**")
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            st.metric("Faithfulness", f"{h.get('faithfulness', 0):.2f}")
                        with col_m2:
                            st.metric("Relevancy", f"{h.get('relevancy', 0):.2f}")

    with tab2:
        st.markdown("## ✋ Refusal Analysis")

        should_refuse = [r for r in results if r.get("should_refuse", False)]
        actual_refusals = [r for r in results if r.get("generated_answer") == config.NO_ANSWER]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Should Refuse", len(should_refuse))

        with col2:
            st.metric("Did Refuse", len(actual_refusals))

        with col3:
            correct_refusals = len([r for r in actual_refusals if r.get("should_refuse", False)])
            st.metric("Correct Refusals", correct_refusals)

        st.divider()

        # Refusal accuracy
        if should_refuse:
            refusal_accuracy = correct_refusals / len(should_refuse)
            st.markdown(f"### Refusal Accuracy: {refusal_accuracy:.1%}")

            if refusal_accuracy == 1.0:
                st.success("✅ Perfect refusal accuracy!")
            elif refusal_accuracy >= 0.8:
                st.info("✅ Good refusal accuracy")
            else:
                st.warning("⚠️ Low refusal accuracy - system answering when it shouldn't")

        st.divider()

        # False positives (should not refuse but did)
        st.markdown("### False Positive Refusals")

        false_positives = [
            r for r in actual_refusals if not r.get("should_refuse", False)
        ]

        if false_positives:
            st.warning(f"⚠️ {len(false_positives)} false positive refusals")

            for result in false_positives[:3]:
                with st.container(border=True):
                    st.markdown(f"**Q:** {result.get('question', '')}")
                    st.error(f"**A:** {result.get('generated_answer', '')}")
                    st.info(f"**Expected:** {result.get('ground_truth_answer', '')}")
        else:
            st.success("✅ No false positive refusals")

        st.divider()

        # False negatives (should refuse but didn't)
        st.markdown("### False Negative Refusals (Unanswered Cases)")

        false_negatives = [
            r for r in results
            if r.get("should_refuse", False) and r.get("generated_answer") != config.NO_ANSWER
        ]

        if false_negatives:
            st.error(f"❌ {len(false_negatives)} false negative refusals")

            for result in false_negatives[:3]:
                with st.container(border=True):
                    st.markdown(f"**Q:** {result.get('question', '')}")
                    st.error(f"**A (shouldn't answer):** {result.get('generated_answer', '')[:100]}...")
        else:
            st.success("✅ No false negative refusals")

    with tab3:
        st.markdown("## 📊 Failure Analysis by Metric")

        failures = get_questions_by_failure_reason(results)

        if not failures:
            st.success("✅ No failures to analyze")
        else:
            st.warning(f"⚠️ Failures detected in {len(failures)} metrics")

            st.divider()

            # Failure breakdown
            st.markdown("### Failure Breakdown")
            tables.failure_analysis_table(failures)

            st.divider()

            # Top issues
            st.markdown("### Top Issues by Frequency")

            sorted_failures = sorted(
                failures.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )

            for metric_name, failed_results in sorted_failures:
                with st.expander(f"**{metric_name}** - {len(failed_results)} questions"):
                    st.markdown(f"### Questions failing on {metric_name}")

                    for result in failed_results[:5]:
                        score = result.get("metrics", {}).get(metric_name, 0)
                        st.write(f"""
                        - **Q:** {result.get('question', '')}
                        - **Score:** {score:.2f}
                        """)

    st.divider()

    # Recommendations
    st.markdown("## 💡 Recommendations")

    faithfulness = metrics.get("faithfulness", 0)
    refusal_acc = metrics.get("grounded_refusal", 0)

    recommendations = []

    if faithfulness < config.QUALITY_GATE_THRESHOLDS["faithfulness"]:
        recommendations.append("""
        **Reduce Hallucinations:**
        - Make system prompt stricter about ground truth
        - Increase evaluation threshold
        - Review context retrieval quality
        - Add fact-checking step
        """)

    if refusal_acc < config.QUALITY_GATE_THRESHOLDS["grounded_refusal"]:
        recommendations.append("""
        **Improve Refusals:**
        - Add confidence threshold check
        - Train on negative examples
        - Refine similarity threshold
        - Add explicit "not found" detection
        """)

    if not recommendations:
        st.success("✅ Hallucination metrics are good!")
    else:
        st.warning("### Action Items:")
        for rec in recommendations:
            st.info(rec)
