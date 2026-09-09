"""app.py -- Streamlit UI: upload documents, chat, and live Quality Gate dashboard."""

import re
import tempfile
from pathlib import Path

import streamlit as st

from src import config
from src.chat import check_ollama, get_answer
from src.chunker import chunk_text
from src.document_processor import extract_excel, extract_pdf
from src.embeddings import embed_documents, embed_query
from src.vector_store import collection_count, delete_collection, is_stored, store_chunks
from src.evaluation_metrics import evaluate_qa_pair
from src.streamlit_quality_dashboard import render_quality_gate_dashboard

st.set_page_config(page_title="Chat on Document", page_icon="📄", layout="wide")

# ── Session state ──────────────────────────────────────────────────────────────
for _key, _default in [
    ("history", []),
    ("qa_evaluations", []),   # inline per-question evaluation results
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("📄 Chat on Document")
st.markdown("Upload documents and ask questions. Get answers with sources.")

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


@st.cache_resource(show_spinner=False)
def _warmup_model() -> None:
    embed_query("warmup")


_warmup_model()


@st.cache_data(ttl=300)
def _ollama_ok() -> bool:
    return check_ollama()


@st.cache_data(ttl=30)
def _chunk_count(collection: str) -> int:
    return collection_count(collection)


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
            if elem["type"] == "text":
                for i, piece in enumerate(chunk_text(elem["text"])):
                    chunks.append({**elem, "idx": i, "text": piece})
            else:
                chunks.append({**elem, "idx": elem.get("idx", 0)})

        vecs = embed_documents([c["text"] for c in chunks])
        return store_chunks(chunks, vecs, collection)

    finally:
        tmp_path.unlink(missing_ok=True)


# ============================================================================
# STEP 1: UPLOAD DOCUMENTS
# ============================================================================

st.subheader("📤 Upload Your Documents")

with st.container(border=True):
    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded = st.file_uploader(
            "Choose PDF or Excel files (supports multiple files)",
            type=["pdf", "xlsx", "xls"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

    with col2:
        chunks = _chunk_count(COLLECTION)
        st.metric("Total Chunks Indexed", chunks)

    col_upload, col_clear = st.columns(2)

    with col_upload:
        upload_btn = st.button("🚀 Upload & Process", type="primary", use_container_width=True)

    with col_clear:
        reset_btn = st.button("🗑️ Clear All Documents", use_container_width=True)

    if reset_btn:
        try:
            delete_collection(COLLECTION)
            _chunk_count.clear()
            st.session_state.history = []
            st.session_state.qa_evaluations = []
            st.success("✅ All documents cleared!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Clear failed: {e}")

    if uploaded and upload_btn:
        progress_bar = st.progress(0)
        status_msg = st.empty()
        total = len(uploaded)

        for idx, uf in enumerate(uploaded):
            try:
                status_msg.info(f"📋 Processing {idx + 1}/{total}: {uf.name}...")
                with st.spinner(f"Extracting & embedding {uf.name}..."):
                    n = _ingest(uf, COLLECTION)

                if n == 0:
                    st.info(f"⏭️ {uf.name} already indexed, skipped.")
                else:
                    st.success(f"✅ {uf.name} — {n} chunks indexed!")
                    _chunk_count.clear()
                    st.session_state.qa_evaluations = []

                progress_bar.progress((idx + 1) / total)
            except Exception as e:
                st.error(f"❌ Failed to process {uf.name}: {str(e)}")

        status_msg.empty()
        progress_bar.empty()

st.divider()

# ============================================================================
# STEP 2: CHAT WITH YOUR DOCUMENTS
# ============================================================================

st.subheader("💬 Chat with Your Documents")

if not _ollama_ok():
    st.error("❌ Ollama is NOT running!")
    st.warning(
        "**Fix:** Open a terminal and run:\n"
        "```bash\nollama serve\n```\n"
        "Keep it running, then refresh this page."
    )
elif chunks == 0:
    st.info("📁 **No documents uploaded yet.** Please upload documents above to get started.")
else:
    st.success(f"✅ Ready! {chunks} chunks loaded. Ask away!")

    question = st.text_input(
        "Your question:",
        placeholder="Example: What are the main topics in the document?",
        label_visibility="collapsed",
    )

    col_ask, col_clear = st.columns([3, 1])

    with col_ask:
        ask_btn = st.button(
            "🔍 Ask Question",
            type="primary",
            use_container_width=True,
            disabled=not question.strip(),
        )

    with col_clear:
        if st.button("Clear History", use_container_width=True):
            st.session_state.history = []
            st.session_state.qa_evaluations = []
            st.rerun()

    history_slot = st.empty()

    if ask_btn and question.strip():
        history_slot.empty()

        try:
            stream, citations, context_texts = get_answer(question.strip(), COLLECTION)
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            stream, citations, context_texts = None, [], []

        if stream is not None:
            box = st.empty()
            answer = ""
            for token in stream:
                answer += token
                box.markdown(answer + "|")
            box.empty()

            low = answer.lower()
            is_refusal = any(p.lower() in low for p in _REFUSAL_PHRASES)
            if is_refusal:
                citations = []
                context_texts = []
                answer = config.NO_ANSWER
            else:
                answer = _SOURCE_TAG_RE.sub("", answer).strip()

            # ── Inline quality evaluation ──────────────────────────────────
            if not is_refusal and context_texts:
                citation_scores = [c["score"] for c in citations] if citations else []
                try:
                    eval_result = evaluate_qa_pair(
                        question=question.strip(),
                        answer=answer,
                        contexts=context_texts,
                        citation_scores=citation_scores,
                    )
                    st.session_state.qa_evaluations.append(eval_result)
                except Exception:
                    pass  # Don't break the chat flow on eval error

            st.session_state.history.append({
                "q": question.strip(),
                "a": answer,
                "c": citations,
            })

    # Display conversation history
    with history_slot.container():
        if st.session_state.history:
            st.markdown("### 📝 Conversation History")
            for entry in reversed(st.session_state.history):
                st.markdown(f"**Q:** {entry['q']}")
                st.markdown(f"**A:** {entry['a']}")
                if entry["c"]:
                    with st.expander(f"📎 View Sources ({len(entry['c'])})"):
                        for c in entry["c"]:
                            st.markdown(
                                f"• **{c['source']}** | Page/Sheet: {c['page']} | "
                                f"Relevance: {c['score']:.0%}"
                            )
                st.divider()

st.divider()

# ============================================================================
# STEP 3: RAG QUALITY GATE DASHBOARD
# ============================================================================

st.subheader("📊 RAG Quality Gate")

render_quality_gate_dashboard(session_evaluations=st.session_state.get("qa_evaluations", []))
