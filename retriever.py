"""retriever.py — ChromaDB vector store with sentence-transformers embeddings."""

from pathlib import Path
from typing import Any, Optional

import chromadb

CHROMA_PATH = "./chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"
DEFAULT_COLLECTION = "documents"

_client: Optional[chromadb.PersistentClient] = None
_embedder: Optional[Any] = None   # SentenceTransformer — lazy-loaded on first use


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def _get_embedder():
    """Load SentenceTransformer on first call only — avoids PyTorch startup cost."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer  # lazy import
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def init_collection(name: str = DEFAULT_COLLECTION) -> chromadb.Collection:
    """Get or create a ChromaDB collection using cosine similarity (HNSW index)."""
    return _get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(chunks: list[dict], collection_name: str = DEFAULT_COLLECTION) -> int:
    """
    Embed and upsert chunks into ChromaDB.
    Required keys per chunk: text, source, page, chunk_type, chunk_index.
    Returns number of chunks stored.
    """
    if not chunks:
        return 0

    collection = init_collection(collection_name)
    embedder = _get_embedder()

    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()

    ids: list[str] = []
    metadatas: list[dict] = []

    for i, chunk in enumerate(chunks):
        raw_id = (
            f"{chunk.get('source', 'unknown')}"
            f"__p{chunk.get('page', 0)}"
            f"__t{chunk.get('chunk_type', 'text')}"
            f"__c{chunk.get('chunk_index', i)}"
        )
        safe_id = raw_id.replace(" ", "_").replace("/", "-").replace("\\", "-")
        if safe_id in ids:
            safe_id = f"{safe_id}_{i}"
        ids.append(safe_id)

        metadatas.append({
            "source":      str(chunk.get("source", "unknown")),
            "page":        str(chunk.get("page", "0")),
            "chunk_type":  str(chunk.get("chunk_type", "text")),
            "chunk_index": int(chunk.get("chunk_index", i)),
        })

    collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(chunks)


def search(
    query: str,
    collection_name: str = DEFAULT_COLLECTION,
    n_results: int = 5,
) -> list[dict]:
    """
    Semantic search. Returns list of hit dicts:
      text, source, page, chunk_type, chunk_index, score (0–1, higher = more relevant).
    """
    collection = init_collection(collection_name)
    count = collection.count()
    if count == 0:
        return []

    embedder = _get_embedder()
    query_vec = embedder.encode([query], show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=query_vec,
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"],
    )

    hits: list[dict] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text":        doc,
            "source":      meta.get("source", "unknown"),
            "page":        meta.get("page", "0"),
            "chunk_type":  meta.get("chunk_type", "text"),
            "chunk_index": int(meta.get("chunk_index", 0)),
            "score":       round(1.0 - float(dist), 4),
        })

    return hits


def list_collections() -> list[str]:
    """Return names of all existing collections."""
    return [c.name for c in _get_client().list_collections()]


def delete_collection(name: str) -> None:
    """Delete a collection by name."""
    _get_client().delete_collection(name=name)


def collection_count(collection_name: str = DEFAULT_COLLECTION) -> int:
    """Return chunk count, or 0 if the collection doesn't exist."""
    try:
        return init_collection(collection_name).count()
    except Exception:
        return 0
