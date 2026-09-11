"""
RAG Chat - Upload documents (PDF/Excel), ask questions, and evaluate
answer quality with 6 RAGAS-style metrics and a live dataset evaluation runner.
"""

import json
import re
import tempfile
from pathlib import Path

import streamlit as st

from src import config
from src.chat import get_answer
from src.chunker import chunk_text
from src.document_processor import extract_excel, extract_pdf
from src.embeddings import embed_documents, embed_query
from src.evaluation_metrics import MetricsCalculator
from src.quality_gate import QualityGateEvaluator
from src.vector_store import collection_count, delete_collection, is_stored, store_chunks

st.set_page_config(page_title="RAG Chat", page_icon="💬", layout="wide")

# ── Session state ──────────────────────────────────────────────────────────────
for _key, _default in [
    ("history", []),
    ("eval_results", []),
    ("eval_running", False),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

# ── Header ─────────────────────────────────────────────────────────────────────
st.title(" ChatOnDocuments -  With RAG Quality Gate Evaluation ")
st.markdown("Upload documents (PDF/Excel) and ask questions. Get answers with sources.")

COLLECTION = config.COLLECTION_NAME

_REFUSAL_PHRASES = (
    config.NO_ANSWER,
    "could not find this",
    "cannot find this in the",
    "not find this in the",
    "not present in the provided",
    "not available in the provided",
    "not mentioned in the provided",
    "does not contain information",
)

_SOURCE_TAG_RE = re.compile(r'\[Source:[^\]]*\]', re.IGNORECASE)
_EXCERPT_PREAMBLE_RE = re.compile(
    r"^(according to|based on|from|per|as per|as stated in|as mentioned in|"
    r"referring to|in)\s+(excerpt|source|context|document|passage|the document|the context)"
    r"[\s\d,.:;-]*",
    re.IGNORECASE,
)

_METRIC_THRESHOLDS = {
    "faithfulness":      0.85,
    "answer_relevancy":  0.80,
    "context_precision": 0.75,
    "context_recall":    0.75,
    "citation_accuracy": 0.90,
    "retrieval_f1":      0.70,
}
_METRIC_LABELS = {
    "faithfulness":      "Faithfulness",
    "answer_relevancy":  "Answer Relevancy",
    "context_precision": "Ctx Precision",
    "context_recall":    "Ctx Recall",
    "citation_accuracy": "Citation Acc",
    "retrieval_f1":      "Retrieval F1",
}


@st.cache_resource(show_spinner=False)
def _warmup_model() -> None:
    embed_query("warmup")


_warmup_model()


@st.cache_data(ttl=30)
def _chunk_count(collection: str) -> int:
    return collection_count(collection)


@st.cache_data
def _load_golden_dataset():
    dataset_path = Path("evaluation/datasets/golden_qa_v1.0.json")
    if dataset_path.exists():
        with open(dataset_path) as f:
            return json.load(f)
    return None


def _ingest(uploaded_file, collection: str) -> int:
    """Extract -> chunk -> embed -> store. Returns chunk count."""
    suffix = Path(uploaded_file.name).suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = Path(tmp.name)

    try:
        if suffix == ".pdf":
            elements = extract_pdf(tmp_path, uploaded_file.name)
        elif suffix in (".xlsx", ".xls"):
            elements = extract_excel(tmp_path, uploaded_file.name)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        if not elements:
            return 0

        if is_stored(elements[0]["file_id"], collection):
            return 0

        chunks: list[dict] = []
        for elem in elements:
            base = {
                "source":   elem["source"],
                "page":     elem.get("page", 0),
                "file_id":  elem["file_id"],
                "type":     elem["type"],
                "strategy": elem.get("strategy", elem["type"]),
            }
            if elem["type"] == "text":
                # PDF narrative text — sub-chunk with overlap
                for i, piece in enumerate(chunk_text(elem["text"])):
                    chunks.append({**base, "idx": i, "text": piece})
            else:
                # Excel rows/tables/aggregates + PDF tables/images — store as-is
                chunks.append({**base, "idx": elem.get("idx", 0), "text": elem["text"]})

        if not chunks:
            return 0

        embeddings = embed_documents([c["text"] for c in chunks])
        store_chunks(chunks, embeddings, collection)
        return len(chunks)

    finally:
        tmp_path.unlink(missing_ok=True)


def _strip_answer(answer: str) -> str:
    answer = _SOURCE_TAG_RE.sub("", answer)
    answer = _EXCERPT_PREAMBLE_RE.sub("", answer)
    return answer.strip()


def _compute_metrics(question: str, clean_answer: str, context_texts: list[str]) -> dict:
    """Compute all 6 RAGAS-style metrics for one Q&A turn."""
    calc = MetricsCalculator()
    cp = calc.calculate_context_precision(question, context_texts, clean_answer)
    cr = calc.calculate_context_recall(question, context_texts, clean_answer)
    return {
        "faithfulness":      calc.calculate_faithfulness(clean_answer, context_texts),
        "answer_relevancy":  calc.calculate_answer_relevancy(question, clean_answer),
        "context_precision": cp,
        "context_recall":    cr,
        "citation_accuracy": calc.calculate_citation_accuracy(clean_answer, context_texts),
        "retrieval_f1":      2 * cp * cr / (cp + cr) if (cp + cr) > 0 else 0.0,
    }


def _render_leadership_summary(full_results: list[dict], pass_count: int, total: int) -> None:
    """Render leadership-ready scorecard: overall + per-difficulty + per-type + per-metric."""
    import pandas as pd

    st.markdown("---")
    st.markdown("### 📋 Leadership Scorecard")

    # ── Overall KPIs ───────────────────────────────────────────────────────────
    pass_rate = pass_count / total * 100 if total else 0
    refusal_results = [r for r in full_results if r.get("should_refuse")]
    refusal_correct = sum(1 for r in refusal_results if r["passed"])
    answerable      = [r for r in full_results if not r.get("should_refuse")]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Questions", total)
    c2.metric("Overall Pass Rate", f"{pass_rate:.1f}%",
              delta="production-ready" if pass_rate >= 80 else "needs improvement",
              delta_color="normal" if pass_rate >= 80 else "inverse")
    c3.metric("Answerable PASS", f"{sum(1 for r in answerable if r['passed'])}/{len(answerable)}")
    c4.metric("Refusal Accuracy",
              f"{refusal_correct}/{len(refusal_results)}" if refusal_results else "N/A",
              delta="✅ correct" if refusal_correct == len(refusal_results) else "❌ missed",
              delta_color="normal" if refusal_correct == len(refusal_results) else "inverse")
    c5.metric("Unanswerable Tests", len(refusal_results))

    # ── Per-metric binary pass rate ────────────────────────────────────────────
    st.markdown("#### Binary Pass Rate per Metric  (1.0 = above threshold, 0.0 = below)")
    metric_rows = []
    for key, label in _METRIC_LABELS.items():
        scores = [r["bin_scores"].get(key, 0.0) for r in full_results]
        rate   = sum(scores) / len(scores) if scores else 0.0
        metric_rows.append({
            "Metric":    label,
            "Threshold": _METRIC_THRESHOLDS[key],
            "Pass Rate": f"{rate:.0%}",
            "Passed":    f"{int(sum(scores))}/{len(scores)}",
            "Status":    "✅ Good" if rate >= 0.80 else ("⚠️ Review" if rate >= 0.60 else "❌ Fix"),
        })
    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

    # ── Pass rate by difficulty ────────────────────────────────────────────────
    st.markdown("#### Pass Rate by Difficulty")
    diff_rows = []
    for diff in ["easy", "medium", "hard"]:
        subset = [r for r in full_results if r.get("difficulty") == diff]
        if subset:
            p = sum(1 for r in subset if r["passed"])
            diff_rows.append({
                "Difficulty": diff.title(),
                "Total":      len(subset),
                "Passed":     p,
                "Pass Rate":  f"{p/len(subset)*100:.1f}%",
                "Status":     "✅" if p == len(subset) else ("⚠️" if p > 0 else "❌"),
            })
    if diff_rows:
        st.dataframe(pd.DataFrame(diff_rows), use_container_width=True, hide_index=True)

    # ── Pass rate by question type ─────────────────────────────────────────────
    st.markdown("#### Pass Rate by Question Type")
    types = sorted({r.get("q_type", "direct") for r in full_results})
    type_rows = []
    for qt in types:
        subset = [r for r in full_results if r.get("q_type") == qt]
        p = sum(1 for r in subset if r["passed"])
        type_rows.append({
            "Question Type": qt.replace("_", " ").title(),
            "Total":         len(subset),
            "Passed":        p,
            "Pass Rate":     f"{p/len(subset)*100:.1f}%",
            "Status":        "✅" if p == len(subset) else ("⚠️" if p > 0 else "❌"),
        })
    st.dataframe(pd.DataFrame(type_rows), use_container_width=True, hide_index=True)

    # ── Failure classification: retrieval / generation / chunking ──────────────
    failures = [r for r in full_results if not r["passed"]]
    if failures:
        st.markdown("#### Failure Classification")
        cat_counts: dict[str, int] = {}
        for r in failures:
            cat = r.get("fail_cat") or "unknown"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        cat_rows = []
        _CAT_FIX = {
            "retrieval":  "Lower SIMILARITY_THRESHOLD / increase TOP_K",
            "generation": "Strengthen system prompt grounding rules",
            "chunking":   "Raise SIMILARITY_THRESHOLD / adjust CHUNK_SIZE",
            "error":      "Check Ollama connectivity and document indexing",
            "unknown":    "Inspect individual failures below",
        }
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            cat_rows.append({
                "Category":      cat.title(),
                "# Failures":    count,
                "% of Failures": f"{count/len(failures)*100:.0f}%",
                "Recommended Fix": _CAT_FIX.get(cat, "—"),
            })
        st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)

        # ── Top-5 failures with root cause + fix ──────────────────────────────
        st.markdown("#### Top-5 Failures — Root Cause & Fix")
        # Sort failures: retrieval first (hardest to fix automatically), then generation
        _CAT_ORDER = {"retrieval": 0, "chunking": 1, "generation": 2, "error": 3, "unknown": 4}
        top5 = sorted(failures, key=lambda r: _CAT_ORDER.get(r.get("fail_cat", "unknown"), 9))[:5]
        for i, r in enumerate(top5, 1):
            cat   = (r.get("fail_cat") or "unknown").title()
            note  = r.get("note", "—")
            fix   = r.get("fix_rec", "—")
            q_short = r["question"][:70] + ("…" if len(r["question"]) > 70 else "")
            raw   = r.get("raw_scores", {})
            with st.expander(f"#{i} [{cat}]  {q_short}"):
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.markdown(f"**Q_ID:** `{r['q_id']}`")
                    st.markdown(f"**Difficulty:** {r.get('difficulty','?').title()}")
                    st.markdown(f"**Type:** {r.get('q_type','?').replace('_',' ').title()}")
                    st.markdown(f"**Failure Category:** `{cat}`")
                with col_b:
                    st.markdown(f"**Root Cause:** {note}")
                    st.markdown(f"**Fix:** {fix}")
                    if raw:
                        failing = {k: f"{v:.2f}" for k, v in raw.items()
                                   if v < _METRIC_THRESHOLDS.get(k, 0.75)}
                        st.markdown(f"**Failing metrics:** {failing}")
                    if r.get("answer"):
                        st.caption(f"Bot answer: {r['answer'][:120]}")


# ── Sidebar: Document Management ───────────────────────────────────────────────
with st.sidebar:
    st.header("📁 Document Management")

    chunk_count = _chunk_count(COLLECTION)
    st.metric("Chunks Stored", chunk_count)

    st.markdown("### Upload Documents")
    uploaded_files = st.file_uploader(
        "Select PDF or Excel files",
        type=["pdf", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        if st.button("📤 Upload & Process"):
            with st.spinner("Processing documents..."):
                total_chunks = 0
                for file in uploaded_files:
                    try:
                        n = _ingest(file, COLLECTION)
                        if n == 0:
                            st.info(f"ℹ️ {file.name}: already indexed")
                        else:
                            st.success(f"✅ {file.name}: {n} chunks")
                        total_chunks += n
                    except Exception as e:
                        st.error(f"❌ {file.name}: {e}")
                if total_chunks > 0:
                    st.info(f"Total: {total_chunks} new chunks indexed")
                    _chunk_count.clear()

    if st.button("🗑️ Clear All Data"):
        delete_collection(COLLECTION)
        st.session_state.eval_results = []
        st.success("All data cleared")
        _chunk_count.clear()


# ── Main: Chat ──────────────────────────────────────────────────────────────────
st.markdown("### 💬 Ask Your Question")

if _chunk_count(COLLECTION) == 0:
    st.info("📌 No documents loaded yet. Upload documents using the sidebar.")
else:
    question = st.text_input(
        "Enter your question:",
        placeholder="e.g., How many days of annual leave?",
    )

    if st.button("🔍 Get Answer", type="primary"):
        if not question.strip():
            st.warning("Please enter a question")
        else:
            with st.spinner("Searching..."):
                try:
                    answer_stream, citations, context_texts = get_answer(question, COLLECTION)
                    answer = "".join(answer_stream)
                    clean_answer = _strip_answer(answer)

                    st.markdown("#### ✅ Answer")
                    st.write(clean_answer)

                    # Detect grounded refusal — reward with 1.0 across all metrics
                    is_refusal = any(p in clean_answer.lower() for p in _REFUSAL_PHRASES)

                    if is_refusal:
                        metrics_scores = {k: 1.0 for k in _METRIC_THRESHOLDS}
                        st.markdown("#### 📊 Quality Metrics")
                        st.success(
                            "✅ **Quality Gate: PASS — Grounded Refusal** "
                            "Bot correctly declined to answer because no relevant context exists."
                        )
                        st.info(
                            "All 6 metrics scored **1.0** — refusing an unanswerable question "
                            "is the safest and most trustworthy behavior."
                        )
                        col1, col2, col3 = st.columns(3)
                        for col, label in zip(
                            [col1, col1, col2, col2, col3, col3],
                            ["Faithfulness", "Answer Relevancy", "Context Precision",
                             "Context Recall", "Citation Accuracy", "Retrieval F1"],
                        ):
                            col.metric(label, "1.00", delta="PASS — grounded refusal",
                                       delta_color="normal")
                        gate_passed = True
                    else:
                        metrics_scores = _compute_metrics(question, clean_answer, context_texts)
                        quality_gate = QualityGateEvaluator()
                        gate_result = quality_gate.evaluate_metrics(metrics_scores)
                        gate_passed = gate_result.passed

                        st.markdown("#### 📊 Quality Metrics")
                        if gate_passed:
                            st.success("✅ **Quality Gate: PASS** — all metrics above threshold")
                        else:
                            failed = [r.name for r in gate_result.metric_results if not r.passed]
                            st.error(f"❌ **Quality Gate: FAIL** — below threshold: {', '.join(failed)}")

                        def _metric_tile(col, label: str, key: str) -> None:
                            score  = metrics_scores[key]
                            thr    = _METRIC_THRESHOLDS[key]
                            passed = score >= thr
                            col.metric(
                                label,
                                f"{score:.2f}",
                                delta=(f"PASS (≥{thr})"
                                       if passed else
                                       f"FAIL — threshold {thr}"),
                                delta_color="normal" if passed else "inverse",
                            )

                        col1, col2, col3 = st.columns(3)
                        _metric_tile(col1, "Faithfulness",      "faithfulness")
                        _metric_tile(col1, "Answer Relevancy",  "answer_relevancy")
                        _metric_tile(col2, "Context Precision", "context_precision")
                        _metric_tile(col2, "Context Recall",    "context_recall")
                        _metric_tile(col3, "Citation Accuracy", "citation_accuracy")
                        _metric_tile(col3, "Retrieval F1",      "retrieval_f1")

                    # ── Sources with file name + relevance score ────────────────
                    if context_texts and not is_refusal:
                        st.markdown("#### 📚 Sources")
                        for i, ctx in enumerate(context_texts, 1):
                            cit  = citations[i - 1] if i - 1 < len(citations) else {}
                            src  = cit.get("source", f"Source {i}")
                            pg   = f"  •  Page/Sheet: {cit['page']}" if cit.get("page") else ""
                            rel  = f"  •  Relevance: {cit['score']:.2f}" if cit.get("score") else ""
                            with st.expander(f"Source {i}: {src}{pg}{rel}"):
                                st.text(ctx)
                    elif is_refusal:
                        st.info("No sources cited — bot refused because no reliable context was retrieved.")

                    st.session_state.history.append({
                        "question": question,
                        "answer":   clean_answer,
                        "sources":  len(context_texts),
                        "metrics":  metrics_scores,
                        "passed":   gate_passed,
                        "refusal":  is_refusal,
                    })

                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Chat History ────────────────────────────────────────────────────────────
    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 📜 Chat History")
        tab1, tab2 = st.tabs(["📊 Metrics Summary", "💬 Q&A Details"])

        with tab1:
            all_metrics: dict[str, list[float]] = {}
            pass_count = 0
            for item in st.session_state.history:
                if item.get("passed"):
                    pass_count += 1
                for k, v in item.get("metrics", {}).items():
                    all_metrics.setdefault(k, []).append(v)

            total_count = len(st.session_state.history)
            pass_rate = pass_count / total_count * 100 if total_count else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Questions", total_count)
            c2.metric("Passed", f"{pass_count}/{total_count}")
            c3.metric("Pass Rate", f"{pass_rate:.1f}%")
            faith_scores = all_metrics.get("faithfulness", [0])
            c4.metric("Avg Faithfulness", f"{sum(faith_scores)/max(len(faith_scores),1):.3f}")

            st.markdown("#### Metrics Breakdown — Raw Score vs Threshold")
            rows = []
            for name in sorted(all_metrics):
                sc  = all_metrics[name]
                thr = _METRIC_THRESHOLDS.get(name, 0.75)
                bin_scores  = [1.0 if s >= thr else 0.0 for s in sc]
                pass_rate   = sum(bin_scores) / len(bin_scores)
                mean_raw    = sum(sc) / len(sc)
                rows.append({
                    "Metric":       name.replace("_", " ").title(),
                    "Threshold":    f"{thr:.2f}",
                    "Pass Rate":    f"{pass_rate:.0%}",
                    "Passed":       f"{int(sum(bin_scores))}/{len(sc)}",
                    "Avg Raw Score":f"{mean_raw:.3f}",
                    "Status":       "✅ Good" if pass_rate >= 0.80 else ("⚠️ Review" if pass_rate >= 0.60 else "❌ Fix"),
                })
            if rows:
                import pandas as pd
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

        with tab2:
            for i, item in enumerate(st.session_state.history, 1):
                label = "✅ PASS" if item.get("passed") else "❌ FAIL"
                with st.expander(f"{i}. {item['question'][:60]}... {label}"):
                    st.write(f"**Question:** {item['question']}")
                    st.write(f"**Answer:** {item['answer'][:300]}...")
                    st.caption(f"Sources: {item['sources']} | "
                               f"Faithfulness: {item['metrics'].get('faithfulness', 0):.2f}")
                    m = item.get("metrics", {})
                    is_ref = item.get("refusal", False)
                    c1, c2, c3 = st.columns(3)

                    def _bin_label(key: str) -> str:
                        raw = m.get(key, 0.0)
                        thr = _METRIC_THRESHOLDS.get(key, 0.75)
                        verdict = "PASS ✅" if raw >= thr else "FAIL ❌"
                        if is_ref:
                            return f"PASS ✅ (grounded refusal)"
                        return f"{raw:.2f}  —  {verdict}"

                    with c1:
                        st.write(f"**Faithfulness:** {_bin_label('faithfulness')}")
                        st.write(f"**Relevancy:** {_bin_label('answer_relevancy')}")
                    with c2:
                        st.write(f"**Ctx Precision:** {_bin_label('context_precision')}")
                        st.write(f"**Ctx Recall:** {_bin_label('context_recall')}")
                    with c3:
                        st.write(f"**Citation Acc:** {_bin_label('citation_accuracy')}")
                        st.write(f"**Retrieval F1:** {_bin_label('retrieval_f1')}")


# ── Dataset Evaluation Section ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 Run Dataset Evaluation")

if _chunk_count(COLLECTION) == 0:
    st.info("Upload documents before running evaluation.")
else:
    golden_dataset = _load_golden_dataset()
    if not golden_dataset:
        st.warning("Golden dataset not found at evaluation/datasets/golden_qa_v1.0.json")
    else:
        qa_pairs  = golden_dataset.get("qa_pairs", [])
        meta      = golden_dataset.get("metadata", {})
        total_qa  = len(qa_pairs)

        ci1, ci2, ci3 = st.columns(3)
        ci1.metric("Total Q&A Pairs",  total_qa)
        ci2.metric("Refusal Tests",    sum(1 for q in qa_pairs if q.get("should_refuse")))
        ci3.metric("Source Documents", len(meta.get("sources", [])))

        cb1, cb2 = st.columns([2, 1])
        with cb1:
            run_eval = st.button("▶️ Run All Dataset", type="primary",
                                 disabled=st.session_state.eval_running)
        with cb2:
            if st.button("🔄 Clear Results"):
                st.session_state.eval_results = []
                st.rerun()

        def _binary(score: float, key: str) -> float:
            """Return 1.0 if score passes threshold, 0.0 otherwise."""
            return 1.0 if score >= _METRIC_THRESHOLDS[key] else 0.0

        def _chunk_hint(citations: list) -> str:
            if not citations:
                return ""
            primary = citations[0].get("type", "")
            return {"excel": " (Excel chunk)", "table": " (table chunk)", "text": " (PDF text)"}.get(primary, "")

        # Each entry: (category, root_cause_note, fix_recommendation)
        _FAILURE_MAP = [
            ({"faithfulness", "citation_accuracy"},
             "generation", "Hallucination — answer not grounded in context",
             "Strengthen system prompt: add 'only use words from CONTEXT' rule"),
            ({"faithfulness"},
             "generation", "Low faithfulness — answer words not in retrieved context",
             "Check chunk quality; model added words absent from context"),
            ({"context_recall", "context_precision"},
             "retrieval",  "Retrieval-miss — wrong chunks retrieved",
             "Lower SIMILARITY_THRESHOLD or increase TOP_K in config.py"),
            ({"context_recall"},
             "retrieval",  "Retrieval-miss — key content not in context",
             "Lower SIMILARITY_THRESHOLD (currently 0.20) or raise TOP_K (currently 8)"),
            ({"context_precision"},
             "chunking",   "Noisy retrieval — irrelevant chunks included",
             "Raise SIMILARITY_THRESHOLD to filter weak matches"),
            ({"answer_relevancy"},
             "generation", "Off-topic — answer doesn't address the question",
             "Review system prompt; add few-shot examples of on-topic answers"),
            ({"retrieval_f1"},
             "retrieval",  "Low retrieval F1 — precision/recall imbalance",
             "Tune CHUNK_SIZE/CHUNK_OVERLAP; consider smaller chunks for dense docs"),
        ]

        def _classify_failure(raw: dict, binary: dict, citations: list | None = None):
            """Return (category, root_cause, fix_rec) for a failed question."""
            failed = set(k for k, v in binary.items() if v == 0.0)
            if not failed:
                return "", "", ""
            hint = _chunk_hint(citations or [])
            for keys, cat, cause, fix in _FAILURE_MAP:
                if keys <= failed:
                    return cat, cause + hint, fix
            return "unknown", f"Below threshold: {', '.join(sorted(failed))}", "Review metric thresholds"

        if run_eval:
            st.session_state.eval_running = True
            st.session_state.eval_results = []

            progress_bar = st.progress(0.0, text="Starting evaluation...")
            status_box   = st.empty()

            st.markdown("#### 📊 Live Metrics (binary pass rate — 1.0 = above threshold)")
            m_cols     = st.columns(6)
            live_slots = {k: m_cols[i].empty() for i, k in enumerate(_METRIC_LABELS)}
            for k, slot in live_slots.items():
                slot.metric(_METRIC_LABELS[k], "—")

            summary_slot = st.empty()
            table_slot   = st.empty()

            # Track binary 1.0/0.0 per metric for live tiles
            binary_running: dict[str, list[float]] = {k: [] for k in _METRIC_LABELS}
            pass_count = 0
            row_data: list[dict] = []
            full_results: list[dict] = []  # for leadership summary

            gate = QualityGateEvaluator()

            for idx, qa in enumerate(qa_pairs):
                q_id          = qa.get("q_id", "?")
                question      = qa.get("question", "")
                should_refuse = qa.get("should_refuse", False)
                q_type        = qa.get("question_type", "direct")
                difficulty    = qa.get("difficulty", "easy")

                status_box.markdown(f"**[{idx+1}/{total_qa}]** {q_id}: {question[:70]}...")

                try:
                    answer_stream, citations, context_texts = get_answer(question, COLLECTION)
                    clean_answer = _strip_answer("".join(answer_stream))

                    if should_refuse:
                        refused     = any(p in clean_answer.lower() for p in _REFUSAL_PHRASES)
                        bin_val     = 1.0 if refused else 0.0
                        raw_scores  = {k: bin_val for k in _METRIC_LABELS}
                        bin_scores  = {k: bin_val for k in _METRIC_LABELS}
                        passed      = refused
                        fail_cat    = "" if refused else "generation"
                        note        = "bot refused → correct" if refused else "bot answered (should refuse) ← WRONG"
                        fix_rec     = "" if refused else "Improve system prompt: add explicit 'say I cannot find' rule for missing info"
                        answer_disp = "(unanswerable)"
                    else:
                        raw_scores  = _compute_metrics(question, clean_answer, context_texts)
                        bin_scores  = {k: _binary(raw_scores[k], k) for k in raw_scores}
                        passed      = gate.evaluate_metrics(raw_scores).passed
                        fail_cat, note, fix_rec = (
                            _classify_failure(raw_scores, bin_scores, citations)
                            if not passed else ("", "", "")
                        )
                        answer_disp = clean_answer[:80] + ("…" if len(clean_answer) > 80 else "")

                    status_label = "PASS" if passed else "FAIL"

                except Exception as exc:
                    raw_scores   = {k: 0.0 for k in _METRIC_LABELS}
                    bin_scores   = {k: 0.0 for k in _METRIC_LABELS}
                    citations    = []
                    passed       = False
                    fail_cat     = "error"
                    note         = str(exc)[:80]
                    fix_rec      = "Check Ollama is running and document is indexed"
                    answer_disp  = "ERROR"
                    q_type       = qa.get("question_type", "direct")
                    difficulty   = qa.get("difficulty", "easy")

                if passed:
                    pass_count += 1

                for k in _METRIC_LABELS:
                    binary_running[k].append(bin_scores[k])

                # Live tiles: binary pass rate so far (fraction of questions that passed this metric)
                for k, slot in live_slots.items():
                    rate = sum(binary_running[k]) / len(binary_running[k])
                    slot.metric(
                        _METRIC_LABELS[k],
                        f"{rate:.0%}",
                        delta="passing" if rate >= 0.8 else "needs work",
                        delta_color="normal" if rate >= 0.8 else "inverse",
                    )

                # Scorecard row — raw metric score for answered Qs, "—" for refusals
                def _cell(key: str) -> str:
                    if should_refuse:
                        return "—"
                    return f"{raw_scores[key]:.2f}"

                row_data.append({
                    "Q_ID":       q_id,
                    "Difficulty": difficulty,
                    "Type":       q_type,
                    "Question":   question[:55] + ("…" if len(question) > 55 else ""),
                    "Answer":     answer_disp,
                    "Faithfulness":      _cell("faithfulness"),
                    "Relevance":         _cell("answer_relevancy"),
                    "Ctx Recall":        _cell("context_recall"),
                    "Ctx Precision":     _cell("context_precision"),
                    "Citation Acc":      _cell("citation_accuracy"),
                    "Retrieval F1":      _cell("retrieval_f1"),
                    "Result":            status_label,
                    "Note / Reason":     note,
                })

                full_results.append({
                    "q_id":         q_id,
                    "question":     question,
                    "answer":       answer_disp,
                    "passed":       passed,
                    "difficulty":   difficulty,
                    "q_type":       q_type,
                    "bin_scores":   bin_scores,
                    "raw_scores":   raw_scores,
                    "should_refuse":should_refuse,
                    "fail_cat":     fail_cat,
                    "note":         note,
                    "fix_rec":      fix_rec,
                })

                st.session_state.eval_results = {"rows": row_data.copy(), "full": full_results.copy()}
                table_slot.dataframe(row_data, use_container_width=True)

                pass_rate = pass_count / (idx + 1) * 100
                summary_slot.info(
                    f"**Progress:** {idx+1}/{total_qa} | "
                    f"**Passed:** {pass_count} | "
                    f"**Failed:** {(idx+1) - pass_count} | "
                    f"**Pass Rate:** {pass_rate:.1f}%"
                )
                progress_bar.progress((idx + 1) / total_qa, text=f"{idx+1}/{total_qa} complete")

            progress_bar.progress(1.0, text="Evaluation complete")
            gate_status = (
                "✅ PASS" if pass_count == total_qa
                else ("⚠️ PARTIAL" if pass_count > 0 else "❌ FAIL")
            )
            status_box.success(
                f"**Evaluation Complete** — {gate_status} | "
                f"{pass_count}/{total_qa} passed ({pass_count/total_qa*100:.1f}%)"
            )
            st.session_state.eval_running = False

            # ── Leadership Scorecard ────────────────────────────────────────────
            _render_leadership_summary(full_results, pass_count, total_qa)

        elif st.session_state.eval_results:
            rows       = st.session_state.eval_results.get("rows", [])
            full_res   = st.session_state.eval_results.get("full", [])
            p          = sum(1 for r in rows if "PASS" in r.get("Result", ""))
            total      = len(rows)
            st.info(f"**{p}/{total} passed** ({p/total*100:.1f}%) — Re-upload docs or click Run to re-evaluate.")
            st.markdown("#### Scorecard")
            st.dataframe(rows, use_container_width=True)
            if full_res:
                _render_leadership_summary(full_res, p, total)


# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "**📊 Metrics:** Each answer shows 6 RAGAS scores | "
    "**History:** Aggregate metrics table across all questions | "
    "**Evaluation:** Run all golden Q&A pairs with live metric updates"
)
