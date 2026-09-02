"""app.py — ChatOnDocument  (simplified: upload → pick strategy → chat → evaluate)"""

import json
import tempfile
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

from ingest import ingest_file
from retriever import list_collections, collection_count, delete_collection, init_collection
from chat import check_ollama, prepare_stream
from evaluator import load_test_questions, _score_one, score_by_type


# ── Cached helpers — prevent re-calling on every Streamlit rerender ───────────

@st.cache_data(ttl=10)
def _ollama_ok() -> bool:
    return check_ollama()


@st.cache_data(ttl=3)
def _collections() -> list[str]:
    return list_collections()

st.set_page_config(
    page_title="ChatOnDocument",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* ── Dark theme — charcoal background, white text ── */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section[data-testid="stSidebar"] {
    background: #1a1f2e !important;
}
[data-testid="stHeader"] { background: #1a1f2e !important; }

body, p, label, div, span,
.stMarkdown, .stCaption, .stText { color: #f1f5f9 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px; background: #1a1f2e;
    border-bottom: 2px solid #334155;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600; font-size: 15px; color: #94a3b8 !important;
    background: #242938; border-radius: 8px 8px 0 0; padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    color: #a5b4fc !important; background: #1a1f2e;
    border-bottom: 2px solid #6366f1;
}

/* Answer / refusal */
.answer-box {
    background: #0d2518; border: 1px solid #166534; border-radius: 10px;
    padding: 16px; color: #bbf7d0; font-size: 14px; line-height: 1.8;
    white-space: pre-wrap;
}
.refusal-box {
    background: #2d1a0e; border: 1px solid #78350f; border-radius: 10px;
    padding: 14px; color: #fde68a; font-size: 14px;
}

/* Citation card */
.citation-card {
    background: #242938; border: 1px solid #334155;
    border-left: 4px solid #6366f1; border-radius: 8px;
    padding: 10px 14px; margin: 4px 0; font-size: 13px; color: #cbd5e1;
}
.chunk-badge {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 11px; font-weight: 700; margin-right: 8px;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
}

/* Inputs */
input, textarea, [data-testid="stTextInput"] input {
    background: #242938 !important; border: 1px solid #475569 !important;
    color: #f1f5f9 !important; border-radius: 8px !important;
}

/* Radio labels */
.stRadio label, .stSelectbox label { color: #f1f5f9 !important; }

/* Info / success / error boxes */
[data-testid="stAlert"] { background: #242938 !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────

STRATEGIES = {
    "fixed":         ("Fixed",         "Splits every 500 chars — fast baseline",                    "#6366f1"),
    "recursive":     ("Recursive",     "Respects paragraph & sentence boundaries",                  "#0ea5e9"),
    "section_aware": ("Section-aware", "Groups content by headings / document structure",           "#10b981"),
}

TYPE_COLORS = {
    "text": "#6366f1", "table": "#0ea5e9",
    "excel": "#10b981", "image_placeholder": "#f59e0b",
}

# ── Sidebar (minimal status only) ─────────────────────────────────────────────

with st.sidebar:
    ollama_ok = _ollama_ok()           # cached — no HTTP call on every rerender
    st.markdown("**Ollama**")
    if ollama_ok:
        st.success("Connected (llama3.1)")
    else:
        st.error("Offline — run `ollama serve`")

    st.divider()
    st.markdown("**Collections**")
    for c in _collections():           # cached — no ChromaDB round-trip per render
        col1, col2 = st.columns([3, 1])
        col1.caption(f"{c} ({collection_count(c)} chunks)")
        if col2.button("✕", key=f"del_{c}"):
            delete_collection(c)
            _collections.clear()       # invalidate cache after deletion
            st.rerun()

    st.divider()
    n_results = st.slider("Top-K results", 1, 10, 5)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("## 📄 ChatOnDocument")
st.caption("Upload a document, choose a chunking strategy, then ask questions.")

tab_upload, tab_chat, tab_eval = st.tabs(["📤 Upload & Ingest", "💬 Chat", "📊 Evaluate"])

# ── Tab 1 — Upload & Ingest ───────────────────────────────────────────────────

with tab_upload:

    st.markdown("#### 1 — Choose chunking strategy to test")

    strategy_key = st.radio(
        "strategy",
        options=list(STRATEGIES.keys()),
        format_func=lambda k: STRATEGIES[k][0],
        horizontal=True,
        label_visibility="collapsed",
    )

    name, desc, color = STRATEGIES[strategy_key]
    st.markdown(
        f'<div style="background:{color}18;border-left:4px solid {color};'
        f'border-radius:6px;padding:10px 14px;font-size:13px;color:#cbd5e1;margin-bottom:12px">'
        f'<strong style="color:{color}">{name}</strong> — {desc}</div>',
        unsafe_allow_html=True,
    )

    # ── Excel serialisation format (only relevant when uploading .xlsx/.xls) ──
    st.markdown("#### 1b — Excel serialisation format")
    st.caption("Controls how spreadsheet rows are converted to text before embedding")

    EXCEL_FORMATS = {
        "row_as_text":    ("Row-as-Text",     "key=value pairs per row  →  best for record lookups (salary, status…)",  "#6366f1"),
        "markdown_table": ("Markdown Table",  "full grid layout  →  best for row comparisons (highest / lowest…)",      "#0ea5e9"),
        "column_wise":    ("Column-Wise",     "one chunk per column  →  best for aggregates (total, average…)",         "#10b981"),
    }

    excel_format = st.radio(
        "excel_format",
        options=list(EXCEL_FORMATS.keys()),
        format_func=lambda k: EXCEL_FORMATS[k][0],
        horizontal=True,
        label_visibility="collapsed",
    )

    ef_name, ef_desc, ef_color = EXCEL_FORMATS[excel_format]
    st.markdown(
        f'<div style="background:{ef_color}18;border-left:4px solid {ef_color};'
        f'border-radius:6px;padding:8px 14px;font-size:12px;color:#cbd5e1;margin-bottom:14px">'
        f'<strong style="color:{ef_color}">{ef_name}</strong> — {ef_desc}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### 2 — Upload your document")
    uploaded = st.file_uploader(
        "PDF or Excel",
        type=["pdf", "xlsx", "xls"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    collection_name = st.text_input(
        "Save to collection:",
        value="documents",
        help="Give it a name so you can compare runs with different strategies",
    )

    if st.button("⚡ Ingest", disabled=not uploaded, use_container_width=True, type="primary"):
        target = collection_name.strip() or "documents"
        init_collection(target)
        bar = st.progress(0)
        log = st.empty()

        for i, uf in enumerate(uploaded):
            log.info(f"Processing {uf.name} …")
            suffix = Path(uf.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uf.getbuffer())
                tmp_path = tmp.name
            try:
                t0 = time.time()
                n = ingest_file(
                    tmp_path,
                    chunk_strategy=strategy_key,
                    serialization_format=excel_format,
                    collection_name=target,
                    original_filename=uf.name,
                )
                log.success(f"✓ {uf.name} → {n} chunks ({time.time()-t0:.1f}s)")
            except Exception as exc:
                log.error(f"✗ {uf.name}: {exc}")
            finally:
                Path(tmp_path).unlink(missing_ok=True)
            bar.progress((i + 1) / len(uploaded))

        bar.empty()
        st.success(
            f"Ready! **{target}** ingested with "
            f"chunking=**{strategy_key}** · excel=**{excel_format}**. "
            f"Switch to Chat to ask questions."
        )
        st.rerun()

# ── Tab 2 — Chat ──────────────────────────────────────────────────────────────

with tab_chat:

    chat_cols = _collections()           # cached

    if not chat_cols:
        st.info("No documents ingested yet — go to the Upload tab first.")
    else:
        active = st.selectbox("Collection to query:", chat_cols)
        st.caption(f"{collection_count(active)} chunks in **{active}**")

        if not ollama_ok:
            st.warning("Ollama is offline. Run `ollama serve` in a terminal.")

        if "history" not in st.session_state:
            st.session_state.history = []

        q = st.text_input(
            "Ask a question:",
            placeholder='e.g. "What is the total revenue?" or "Who is the author?"',
        )

        col_ask, col_clear = st.columns([4, 1])
        with col_ask:
            ask = st.button("💬 Ask", disabled=not q.strip() or not ollama_ok,
                            use_container_width=True, type="primary")
        with col_clear:
            if st.button("Clear", use_container_width=True):
                st.session_state.history = []
                st.rerun()

        if ask and q.strip():
            # ── Phase 1: retrieve context (instant spinner) ────────────────
            with st.spinner("Searching relevant chunks…"):
                try:
                    token_stream, citations = prepare_stream(
                        q.strip(), collection_name=active, n_results=n_results
                    )
                except Exception as exc:
                    st.error(str(exc))
                    token_stream, citations = None, []

            # ── Phase 2: stream LLM tokens into a live placeholder ─────────
            if token_stream is not None:
                answer_box = st.empty()
                full_text  = ""
                try:
                    for token in token_stream:
                        full_text += token
                        answer_box.markdown(
                            f'<div class="answer-box">{full_text}'
                            f'<span style="opacity:.4">▌</span></div>',
                            unsafe_allow_html=True,
                        )
                except Exception as exc:
                    st.error(f"Stream error: {exc}")

                # ── Phase 3: final render + save to history ────────────────
                is_refusal = "could not find sufficient evidence" in full_text.lower()
                if is_refusal:
                    answer_box.markdown(
                        f'<div class="refusal-box">🚫 {full_text}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    answer_box.markdown(
                        f'<div class="answer-box">{full_text}</div>',
                        unsafe_allow_html=True,
                    )

                st.session_state.history.append({
                    "q": q.strip(),
                    "r": {
                        "answer":     full_text,
                        "citations":  citations,
                        "is_refusal": is_refusal,
                    },
                })

        for entry in reversed(st.session_state.history):
            st.markdown(f"**Q:** {entry['q']}")
            r = entry["r"]
            if r["is_refusal"]:
                st.markdown(
                    f'<div class="refusal-box">🚫 {r["answer"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f'<div class="answer-box">{r["answer"]}</div>', unsafe_allow_html=True)

            if r["citations"]:
                with st.expander(f"📎 {len(r['citations'])} source(s)", expanded=False):
                    for cite in r["citations"]:
                        c = TYPE_COLORS.get(cite["type"], "#6b7280")
                        st.markdown(
                            f'<div class="citation-card">'
                            f'<span class="chunk-badge" style="background:{c}22;color:{c};border:1px solid {c}44">'
                            f'{cite["type"]}</span>'
                            f'<strong>{cite["source"]}</strong> · Page/Sheet: {cite["page"]}'
                            f' · Relevance: {cite["score"]:.2f}</div>',
                            unsafe_allow_html=True,
                        )
            st.divider()

# ── Tab 3 — Evaluate ──────────────────────────────────────────────────────────

with tab_eval:
    st.markdown("### 📊 15-Question Accuracy Evaluation")
    st.caption("Scores answers per source type: text, table, image, excel")

    eval_collections = list_collections()
    if not eval_collections:
        st.info("Ingest documents first, then run evaluation.")
    else:
        eval_col = st.selectbox("Collection to evaluate:", eval_collections, key="eval_col")

        if st.button("▶ Run Evaluation", type="primary", use_container_width=True):
            if not ollama_ok:
                st.error("Ollama is offline — start it first.")
            else:
                try:
                    questions = load_test_questions()
                except FileNotFoundError as e:
                    st.error(str(e))
                    questions = []

                if questions:
                    results = []
                    bar  = st.progress(0)
                    log  = st.empty()

                    for i, q in enumerate(questions):
                        log.caption(f"[{i+1}/{len(questions)}] {q['question'][:70]}…")
                        results.append(_score_one(q, eval_col))
                        bar.progress((i + 1) / len(questions))

                    bar.empty()
                    log.empty()

                    by_type = score_by_type(results)
                    total   = len(results)
                    passed  = sum(1 for r in results if r["passed"])

                    # ── Overall score ──────────────────────────────────────
                    pct = passed / total * 100
                    color = "#16a34a" if pct >= 70 else "#d97706" if pct >= 40 else "#dc2626"
                    st.markdown(
                        f'<div style="background:{color}18;border-left:4px solid {color};'
                        f'border-radius:8px;padding:12px 16px;font-size:16px;color:#1e293b;margin-bottom:16px">'
                        f'<strong>Overall: {passed}/{total} passed — {pct:.0f}%</strong></div>',
                        unsafe_allow_html=True,
                    )

                    # ── Per source-type breakdown ──────────────────────────
                    st.markdown("#### Accuracy by Source Type")
                    cols = st.columns(len(by_type))
                    TYPE_ICON = {"text": "📝", "table": "📋", "image": "🖼️", "excel": "📊"}
                    for col, (stype, s) in zip(cols, sorted(by_type.items())):
                        icon = TYPE_ICON.get(stype, "📄")
                        acc_pct = s["accuracy"] * 100
                        tile_color = "#16a34a" if acc_pct >= 70 else "#d97706" if acc_pct >= 40 else "#dc2626"
                        col.markdown(
                            f'<div style="background:{tile_color}12;border:1px solid {tile_color}44;'
                            f'border-radius:8px;padding:12px;text-align:center;color:#1e293b">'
                            f'<div style="font-size:22px">{icon}</div>'
                            f'<div style="font-weight:700;font-size:15px">{stype}</div>'
                            f'<div style="font-size:24px;font-weight:800;color:{tile_color}">{acc_pct:.0f}%</div>'
                            f'<div style="font-size:11px;color:#64748b">{s["passed"]}/{s["total"]} passed</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # ── Per-question detail ────────────────────────────────
                    st.markdown("#### Question Details")
                    for r in results:
                        status_color = "#16a34a" if r["passed"] else "#dc2626"
                        status_text  = "PASS" if r["passed"] else "FAIL"
                        with st.expander(
                            f"{status_text} [{r['id']}] {r['source_type'].upper()} — {r['question'][:65]}…",
                            expanded=False,
                        ):
                            st.markdown(
                                f'<span style="background:{status_color}22;color:{status_color};'
                                f'border:1px solid {status_color}44;border-radius:4px;'
                                f'padding:2px 8px;font-weight:700;font-size:12px">{status_text}</span>'
                                f' Score: **{r["score"]}** &nbsp;|&nbsp; Time: {r["elapsed_s"]}s',
                                unsafe_allow_html=True,
                            )
                            st.markdown(f"**Q:** {r['question']}")
                            st.markdown(
                                f'<div class="answer-box">{r["answer"]}</div>',
                                unsafe_allow_html=True,
                            )
                            if r["expected_keywords"]:
                                st.caption(f"Expected keywords: {', '.join(r['expected_keywords'])}")
                            if r.get("error"):
                                st.error(f"Error: {r['error']}")

                    # ── Save report ────────────────────────────────────────
                    report_dir = Path("reports")
                    report_dir.mkdir(exist_ok=True)
                    stamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
                    report = report_dir / f"eval_{stamp}.json"
                    report.write_text(
                        json.dumps({
                            "timestamp":        datetime.now().isoformat(),
                            "collection":       eval_col,
                            "overall_accuracy": round(passed / total, 2),
                            "total": total, "passed": passed,
                            "by_type":   by_type,
                            "questions": results,
                        }, indent=2),
                        encoding="utf-8",
                    )
                    st.success(f"Report saved: {report}")
