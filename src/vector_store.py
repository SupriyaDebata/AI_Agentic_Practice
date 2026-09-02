"""src/vector_store.py — ChromaDB operations: store, search, manage collections."""

from pathlib import Path

import chromadb

from src import config

try:
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def _get_client() -> chromadb.PersistentClient:
        Path(config.CHROMA_PATH).mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=config.CHROMA_PATH)

except ImportError:
    _client_instance: chromadb.PersistentClient | None = None

    def _get_client() -> chromadb.PersistentClient:
        global _client_instance
        if _client_instance is None:
            Path(config.CHROMA_PATH).mkdir(parents=True, exist_ok=True)
            _client_instance = chromadb.PersistentClient(path=config.CHROMA_PATH)
        return _client_instance


def _get_collection(name: str) -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": config.CHROMA_METRIC},
    )


def is_stored(file_id: str, collection: str) -> bool:
    """Return True if this file has already been ingested into the collection."""
    col = _get_collection(collection)
    result = col.get(where={"file_id": file_id}, limit=1, include=["documents"])
    return bool(result.get("ids"))


def store_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
    collection: str,
) -> int:
    """Upsert chunks and their embeddings into ChromaDB. Returns number of chunks stored."""
    col = _get_collection(collection)
    ids = [
        f"{c['file_id']}__{c['page']}__{c.get('strategy', c['type'])}__{c['idx']}__{i}"
        [:100].replace(" ", "_").replace("/", "-")
        for i, c in enumerate(chunks)
    ]
    metas = [
        {
            "source":  c["source"],
            "page":    str(c["page"]),
            "type":    c["type"],
            "file_id": c["file_id"],
        }
        for c in chunks
    ]
    texts = [c["text"] for c in chunks]
    col.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas)
    return len(chunks)


def search_chunks(
    query_vec: list[float],
    collection: str,
    top_k: int,
) -> list[dict]:
    """Search ChromaDB and return top-k results with similarity scores."""
    col = _get_collection(collection)
    n = min(top_k, col.count())
    if n == 0:
        return []

    raw = col.query(
        query_embeddings=[query_vec],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    for doc, meta, dist in zip(
        raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
    ):
        results.append({
            "text":   doc,
            "source": meta.get("source", ""),
            "page":   meta.get("page", ""),
            "type":   meta.get("type", ""),
            "score":  round(max(0.0, 1.0 - float(dist)), 4),
        })
    return results


def collection_count(collection: str) -> int:
    """Return total number of chunks stored in the collection."""
    try:
        return _get_collection(collection).count()
    except Exception:
        return 0


def delete_collection(collection: str) -> None:
    """Delete the entire collection from ChromaDB."""
    _get_client().delete_collection(name=collection)
