"""src/embeddings.py — Sentence-transformer embeddings for documents and queries."""

from sentence_transformers import SentenceTransformer

from src import config

# Use st.cache_resource when running inside Streamlit so the model survives
# hot-reloads without re-loading from disk. Fall back to a plain module-level
# singleton for scripts and tests that don't run Streamlit.
try:
    import streamlit as st

    @st.cache_resource(show_spinner="Loading AI model…")
    def _get_model() -> SentenceTransformer:
        return SentenceTransformer(config.EMBEDDING_MODEL, device=config.EMBEDDING_DEVICE)

except ImportError:
    _model_instance: SentenceTransformer | None = None

    def _get_model() -> SentenceTransformer:
        global _model_instance
        if _model_instance is None:
            _model_instance = SentenceTransformer(config.EMBEDDING_MODEL, device=config.EMBEDDING_DEVICE)
        return _model_instance


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a batch of document chunks. Returns one vector per text."""
    return _get_model().encode(
        texts,
        batch_size=config.EMBEDDING_BATCH,
        show_progress_bar=False,
    ).tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return _get_model().encode([text.strip()], show_progress_bar=False)[0].tolist()
