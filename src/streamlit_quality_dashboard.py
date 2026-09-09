"""src/streamlit_quality_dashboard.py -- Streamlit Quality Gate dashboard."""

import json
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config
from src.dataset_manager import DatasetManager
from src.evaluator import RAGEvaluator
from src.quality_gate import QualityGateEvaluator


# ── Helpers ────────────────────────────────────────────────────────────────────

def _avg_scores(evaluations: list[dict]) -> dict:
    """Average metric scores across a list of evaluate_qa_pair results."""
    if not evaluations:
        return {}
    keys = evaluations[0].get("scores", {}).keys()
    return {
        k: round(sum(e["scores"].get(k, 0) for e in evaluations) / len(evaluations), 4)
        for k in keys
    }


def _radar_chart(scores: dict, thresholds: dict) -> go.Figure:
    """Build a radar chart comparing scores vs. thresholds."""
    labels = [k.replace("_", " ").title() for k in scores]
    score_vals = [scores[k] for k in scores]
    thresh_vals = [thresholds.get(k, 0) for k in scores]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=score_vals + [score_vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name="Score",
        line_color="#2ecc71",
        fillcolor="rgba(46,204,113,0.25)",
    ))
    fig.add_trace(go.Scatterpolar(
        r=thresh_vals + [thresh_vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name="Threshold",
        line_color="#e74c3c",
        line_dash="dot",
        fillcolor="rgba(231,76,60,0.10)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        margin=dict(l=20, r=20, t=30, b=20),
        height=360,
    )
    return fig


def _bar_chart(scores: dict, thresholds: dict) -> go.Figure:
    """Build a horizontal bar chart of score vs. threshold per metric."""
    metrics = list(scores.keys())
    score_vals = [scores[m] for m in metrics]
    thresh_vals = [thresholds.get(m, 0) for m in metrics]
    colors = [
        "#2ecc71" if scores[m] >= thresholds.get(m, 0) else "#e74c3c"
        for m in metrics
    ]
    labels = [m.replace("_", " ").title() for m in metrics]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels,
        x=score_vals,
        orientation="h",
        name="Score",
        marker_color=colors,
        text=[f"{v:.0%}" for v in score_vals],
        textposition="auto",
    ))
    fig.add_trace(go.Scatter(
        y=labels,
        x=thresh_vals,
        mode="markers",
        name="Threshold",
        marker=dict(symbol="line-ns-open", size=14, color="#333", line_width=2),
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 1], tickformat=".0%"),
        margin=dict(l=20, r=20, t=20, b=20),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ── Main dashboard entry point ─────────────────────────────────────────────────

def render_quality_gate_dashboard(session_evaluations: list[dict] | None = None) -> None:
    """Render the RAG Quality Gate dashboard.

    Args:
        session_evaluations: Live per-question evaluation dicts collected during
            the current chat session (from evaluate_qa_pair). May be empty list.
    """
    session_evaluations = session_evaluations or []

    try:
        dataset_manager = DatasetManager()
        evaluator = RAGEvaluator()
        quality_gate = QualityGateEvaluator()
    except Exception as e:
        st.error(f"Failed to initialise dashboard components: {e}")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Live Metrics",
        "📋 Dataset",
        "🚀 Run Evaluation",
        "📈 History",
        "⚙️ Settings",
    ])

    # =========================================================================
    # TAB 1 — LIVE METRICS (session + last saved report)
    # =========================================================================
    with tab1:
        # ── Session metrics (always shown if there are any Q&A turns) ─────
        if session_evaluations:
            st.subheader("Session Metrics (Current Chat)")
            avg = _avg_scores(session_evaluations)
            gate_result = quality_gate.evaluate_metrics(avg)

            if gate_result.passed:
                st.success(f"### ✅ QUALITY GATE: PASS  ({len(session_evaluations)} questions evaluated)")
            else:
                st.error(f"### ❌ QUALITY GATE: FAIL  ({len(session_evaluations)} questions evaluated)")
            st.caption(gate_result.summary)

            # KPI row
            kpi_cols = st.columns(4)
            kpi_order = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
            for col, key in zip(kpi_cols, kpi_order):
                score = avg.get(key, 0)
                thresh = config.QUALITY_GATE_THRESHOLDS.get(key, 0)
                delta = score - thresh
                col.metric(
                    label=key.replace("_", " ").title(),
                    value=f"{score:.0%}",
                    delta=f"{delta:+.0%} vs threshold",
                    delta_color="normal",
                )

            col_radar, col_bar = st.columns(2)
            with col_radar:
                st.plotly_chart(_radar_chart(avg, config.QUALITY_GATE_THRESHOLDS), use_container_width=True)
            with col_bar:
                st.plotly_chart(_bar_chart(avg, config.QUALITY_GATE_THRESHOLDS), use_container_width=True)

            # Per-metric table
            rows = []
            for m in gate_result.metric_results:
                rows.append({
                    "Metric": m.name.replace("_", " ").title(),
                    "Score": f"{m.score:.2%}",
                    "Threshold": f"{m.threshold:.2%}",
                    "Status": "✅ PASS" if m.passed else "❌ FAIL",
                    "Gap": f"{m.score - m.threshold:+.2%}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Per-question breakdown
            with st.expander("Question-level detail"):
                q_rows = []
                for ev in session_evaluations:
                    sc = ev.get("scores", {})
                    q_rows.append({
                        "Question": ev.get("question", "")[:60] + "…",
                        "Faithfulness": f"{sc.get('faithfulness', 0):.2%}",
                        "Relevancy": f"{sc.get('answer_relevancy', 0):.2%}",
                        "Precision": f"{sc.get('context_precision', 0):.2%}",
                        "Recall": f"{sc.get('context_recall', 0):.2%}",
                        "Duration (ms)": f"{ev.get('duration_ms', 0):.0f}",
                    })
                st.dataframe(pd.DataFrame(q_rows), use_container_width=True, hide_index=True)

            # Download session results
            st.divider()
            json_bytes = json.dumps(session_evaluations, indent=2).encode()
            st.download_button(
                "📊 Download Session JSON",
                data=json_bytes,
                file_name=f"session_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

        else:
            st.info(
                "**No session data yet.**  "
                "Ask questions in Step 2 above — each answer is evaluated automatically."
            )

        # ── Last saved batch report ───────────────────────────────────────
        latest = evaluator.get_latest_report()
        if latest:
            st.divider()
            st.subheader("Last Batch Evaluation Report")
            qg = latest.get("quality_gate", {})
            passed = qg.get("passed", False)

            if passed:
                st.success(f"### ✅ {qg.get('status', 'PASS')}")
            else:
                st.error(f"### ❌ {qg.get('status', 'FAIL')}")
            st.caption(qg.get("summary", ""))

            col1, col2 = st.columns(2)
            col1.metric("Questions Evaluated", latest.get("evaluation_count", 0))
            col2.metric("Errors", latest.get("error_count", 0))

            if qg.get("metrics"):
                batch_scores = {m["name"]: m["score"] for m in qg["metrics"]}
                col_r, col_b = st.columns(2)
                with col_r:
                    st.plotly_chart(
                        _radar_chart(batch_scores, config.QUALITY_GATE_THRESHOLDS),
                        use_container_width=True,
                    )
                with col_b:
                    st.plotly_chart(
                        _bar_chart(batch_scores, config.QUALITY_GATE_THRESHOLDS),
                        use_container_width=True,
                    )

                batch_rows = [
                    {
                        "Metric": m["name"].replace("_", " ").title(),
                        "Score": f"{m['score']:.2%}",
                        "Threshold": f"{m['threshold']:.2%}",
                        "Status": "✅ PASS" if m["passed"] else "❌ FAIL",
                    }
                    for m in qg["metrics"]
                ]
                st.dataframe(pd.DataFrame(batch_rows), use_container_width=True, hide_index=True)

            # Download buttons
            st.divider()
            dl1, dl2, dl3 = st.columns(3)
            with dl1:
                st.download_button(
                    "📄 HTML Report",
                    data=evaluator.generate_html_report(latest),
                    file_name=f"quality_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                )
            with dl2:
                st.download_button(
                    "📊 JSON Report",
                    data=json.dumps(latest, indent=2),
                    file_name=f"quality_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )
            with dl3:
                csv_rows = [
                    {"Metric": m["name"], "Score": m["score"], "Threshold": m["threshold"], "Passed": m["passed"]}
                    for m in qg.get("metrics", [])
                ]
                if csv_rows:
                    st.download_button(
                        "📈 CSV Metrics",
                        data=pd.DataFrame(csv_rows).to_csv(index=False),
                        file_name=f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )

    # =========================================================================
    # TAB 2 — DATASET MANAGEMENT
    # =========================================================================
    with tab2:
        st.subheader("Golden QA Dataset")

        stats = dataset_manager.get_dataset_stats()
        validation = dataset_manager.validate_dataset()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Questions", stats.get("total_questions", 0))
        c2.metric("With Answers", stats.get("questions_with_answers", 0))
        c3.metric("With Contexts", stats.get("questions_with_contexts", 0))

        st.divider()
        st.subheader("Dataset Actions")

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("📥 Import Sample Dataset"):
                if dataset_manager.import_sample_dataset():
                    st.success("Sample dataset imported!")
                    st.rerun()

        with b2:
            if st.button("🗑️ Clear Dataset"):
                confirm = st.checkbox("Confirm delete all questions")
                if confirm:
                    dataset_manager.save_dataset([])
                    st.success("Dataset cleared!")
                    st.rerun()

        with b3:
            ds = dataset_manager.load_dataset()
            if ds:
                st.download_button(
                    "💾 Export JSON",
                    data=json.dumps(ds, indent=2),
                    file_name=f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )

        st.divider()
        st.subheader("Current Questions")
        ds = dataset_manager.load_dataset()
        if ds:
            df = pd.DataFrame([
                {
                    "ID": q.get("id"),
                    "Question": (q.get("question") or "")[:60] + "…",
                    "Has Answer": "✓" if q.get("expected_answer") else "✗",
                    "Added": (q.get("added_at") or "")[:10],
                }
                for q in ds
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No questions yet. Import a sample dataset or add questions via the API.")

        st.divider()
        st.subheader("Validation")
        if validation["is_valid"]:
            st.success("✅ Dataset is valid and ready for evaluation!")
        else:
            st.warning("⚠️ Dataset has issues:")
            for issue in validation["issues"][:5]:
                st.write(f"- {issue}")

    # =========================================================================
    # TAB 3 — RUN EVALUATION
    # =========================================================================
    with tab3:
        st.subheader("Run Batch Evaluation")
        st.info("Runs every question in your golden dataset through the RAG pipeline and scores all metrics.")

        ds = dataset_manager.load_dataset()
        if not ds:
            st.warning("No golden dataset loaded. Go to **Dataset** tab and import a sample first.")
        else:
            st.write(f"**{len(ds)} questions** in dataset.")

            if st.button("🚀 Run Full Evaluation", type="primary"):
                from src.chat import get_answer as _get_answer

                def _rag_fn(question: str):
                    stream, citations, ctx_texts = _get_answer(question, config.COLLECTION_NAME)
                    answer = "".join(stream)
                    return answer, ctx_texts

                progress = st.progress(0)
                status = st.empty()
                total_q = len(ds)

                def _cb(current: int, total: int):
                    progress.progress(current / total)
                    status.info(f"Evaluating question {current}/{total}…")

                with st.spinner("Running evaluation — this may take a few minutes…"):
                    try:
                        report = evaluator.evaluate_dataset(_rag_fn, progress_callback=_cb)
                        evaluator.save_report(report)
                        progress.empty()
                        status.empty()

                        passed = report.get("quality_gate", {}).get("passed", False)
                        if passed:
                            st.success(f"✅ Evaluation complete — QUALITY GATE PASS ({report.get('evaluation_count', 0)} questions)")
                        else:
                            st.error(f"❌ Evaluation complete — QUALITY GATE FAIL ({report.get('evaluation_count', 0)} questions)")

                        st.info("Switch to **Live Metrics** tab to see the full report.")
                        st.rerun()
                    except Exception as exc:
                        progress.empty()
                        status.empty()
                        st.error(f"Evaluation failed: {exc}")
                        with st.expander("Details"):
                            st.code(traceback.format_exc())

    # =========================================================================
    # TAB 4 — HISTORY
    # =========================================================================
    with tab4:
        st.subheader("Evaluation History")
        reports = evaluator.list_reports()

        if not reports:
            st.info("No evaluation history yet. Run a batch evaluation from the **Run Evaluation** tab.")
        else:
            for rep in reports[:10]:
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(rep["timestamp"][:19])
                c2.write(str(rep["evaluation_count"]))
                c3.write("✅ PASS" if rep["passed"] else "❌ FAIL")
                with c4:
                    if st.button("View", key=f"view_{rep['filename']}"):
                        full = evaluator.load_report(rep["filename"])
                        if full:
                            st.json(full)

    # =========================================================================
    # TAB 5 — SETTINGS
    # =========================================================================
    with tab5:
        st.subheader("Quality Gate Thresholds")
        st.caption("Edit `config.py → QUALITY_GATE_THRESHOLDS` to change these values.")

        rows = [
            {
                "Metric": k.replace("_", " ").title(),
                "Threshold": f"{v:.0%}",
                "Description": quality_gate.get_metric_details(k).get("description", ""),
            }
            for k, v in config.QUALITY_GATE_THRESHOLDS.items()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Active Configuration")
        cfg = {
            "OLLAMA_MODEL": config.OLLAMA_MODEL,
            "EMBEDDING_MODEL": config.EMBEDDING_MODEL,
            "CHUNK_SIZE": config.CHUNK_SIZE,
            "CHUNK_OVERLAP": config.CHUNK_OVERLAP,
            "TOP_K": config.TOP_K,
            "SIMILARITY_THRESHOLD": config.SIMILARITY_THRESHOLD,
        }
        st.json(cfg)
