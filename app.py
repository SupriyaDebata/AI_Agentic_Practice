"""app.py — Streamlit UI: upload documents and chat with them."""

import tempfile
from pathlib import Path

import streamlit as st

from src import config
from src.chat import check_ollama, get_answer
from src.chunker import chunk_text
from src.document_processor import extract_excel, extract_pdf
from src.embeddings import embed_documents, embed_query
from src.vector_store import collection_count, delete_collection, is_stored, store_chunks

st.set_page_config(page_title="ChatOnDocument", page_icon="📄", layout="centered")
st.title("📄 Chat On Document")

COLLECTION = config.COLLECTION_NAME

# Trigger @st.cache_resource model load at page open (not on first question).
# The spinner "Loading AI model…" is shown automatically by the decorator.
embed_query("warmup")  # fast after first load — model is held by st.cache_resource


# ── Cached helpers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def _ollama_ok() -> bool:
    return check_ollama()


@st.cache_data(ttl=5)
def _chunk_count(collection: str) -> int:
    return collection_count(collection)


# ── Ingest pipeline ───────────────────────────────────────────────────────────

def _ingest(uploaded_file, collection: str) -> int:
    """Extract → chunk → embed → store. Returns chunk count or 0 if already ingested."""
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

        # Dedup: skip if this file is already stored
        if is_stored(elements[0]["file_id"], collection):
            return 0

        # Chunk text elements; keep tables / images / excel rows as-is
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


# ── Upload section ─────────────────────────────────────────────────────────────

with st.container(border=True):
    uploaded = st.file_uploader(
        "Upload a PDF or Excel file",
        type=["pdf", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    col_upload, col_reset = st.columns([4, 1])
    upload_btn = col_upload.button("Upload & Process", type="primary", use_container_width=True)
    reset_btn  = col_reset.button("Reset", use_container_width=True)

    if reset_btn:
        try:
            delete_collection(COLLECTION)
            _chunk_count.clear()
            st.session_state.history = []
            st.success("All documents cleared. You can upload again.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not reset: {e}")

    if uploaded and upload_btn:
        for uf in uploaded:
            try:
                with st.spinner(f"Processing {uf.name}…"):
                    n = _ingest(uf, COLLECTION)
                if n == 0:
                    st.info(f"{uf.name} — already indexed, skipped.")
                else:
                    st.success(f"✓ {uf.name} — {n} chunks indexed.")
                    _chunk_count.clear()
            except Exception as e:
                st.error(f"Could not process {uf.name}: {e}")

chunks = _chunk_count(COLLECTION)
if chunks:
    st.caption(f"📂 {chunks} chunks indexed — ask your question below.")

st.divider()

# ── Chat section ───────────────────────────────────────────────────────────────

if not _ollama_ok():
    st.warning("Ollama is not running. Open a terminal and run: `ollama serve`")
    st.stop()

if chunks == 0:
    st.info("👆 Upload a document above to start chatting.")
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []

col1, col2 = st.columns([5, 1])
question  = col1.text_input(
    "Ask a question:",
    placeholder="e.g. Which region had the highest sales?",
    label_visibility="collapsed",
)
clear_btn = col2.button("Clear", use_container_width=True)

st.button("Ask", type="primary", use_container_width=True, key="ask_btn", disabled=not question.strip())

if clear_btn:
    st.session_state.history = []
    st.rerun()

# History slot — created here so we can clear it before streaming starts,
# preventing the previous run's entries from showing during the stream.
history_slot = st.empty()

if st.session_state.get("ask_btn") and question.strip():
    history_slot.empty()   # wipe old history from screen immediately

    try:
        stream, citations = get_answer(question.strip(), COLLECTION)
    except Exception as e:
        st.error(str(e))
        stream, citations = None, []

    if stream is not None:
        box = st.empty()
        answer = ""
        for token in stream:
            answer += token
            box.markdown(answer + "▌")
        box.empty()

        # Strip citations on refusal
        if config.NO_ANSWER in answer:
            citations = []
            answer = config.NO_ANSWER

        st.session_state.history.append({"q": question.strip(), "a": answer, "c": citations})

# ── History ────────────────────────────────────────────────────────────────────

with history_slot.container():
    for entry in reversed(st.session_state.history):
        st.markdown(f"**You:** {entry['q']}")
        st.markdown(entry["a"])
        if entry["c"]:
            with st.expander(f"Sources ({len(entry['c'])})"):
                for c in entry["c"]:
                    st.markdown(
                        f"- **{c['source']}** · Page/Sheet: {c['page']} "
                        f"· {c['type']} · relevance: {c['score']:.0%}"
                    )
        st.divider()
