"""
Application settings loaded from environment variables or .env file.

Keeping configuration here (rather than scattered constants) means changing
a DB path or model name requires editing one file and nothing else.
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve project root regardless of working directory
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Paths ──────────────────────────────────────────────────────────────
    project_root: Path = _PROJECT_ROOT
    data_dir: Path = _PROJECT_ROOT / "data"
    db_path: str = str(_PROJECT_ROOT / "data" / "catalog.db")
    chroma_persist_dir: Path = _PROJECT_ROOT / "data" / "chroma_store"
    bm25_index_path: Path = _PROJECT_ROOT / "data" / "bm25_index.pkl"
    products_xlsx: Path = _PROJECT_ROOT / "data" / "products.xlsx"

    # ── LLM (Ollama) ──────────────────────────────────────────────────────────
    # Using Ollama for local LLM inference (no API key needed)
    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    ollama_model: str = "llama3.2"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024
    llm_timeout: int = 30  # Timeout in seconds for LLM requests

    # ── Embeddings ─────────────────────────────────────────────────────────
    # all-MiniLM-L6-v2: fast, 384-dim, good quality for short product text
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # ── Retrieval ──────────────────────────────────────────────────────────
    default_top_k: int = 10
    # BM25 candidate pool fed to vector/fusion stage
    bm25_candidate_k: int = 20
    vector_candidate_k: int = 20
    sql_candidate_k: int = 50
    # RRF constant — 60 is the standard BM25/vector literature default
    rrf_k: int = 60
    # Maximum products returned to the user after reranking
    final_top_k: int = 5

    # ── MCP ────────────────────────────────────────────────────────────────
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765

    # ── API ────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    # ── Logging ────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── LangSmith Observability ───────────────────────────────────────────────
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "retail-chatbot-week7"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # ── Guardrails (all enabled by default) ──────────────────────────────────
    guardrail_pii_enabled: bool = True
    guardrail_injection_enabled: bool = True
    guardrail_topic_enabled: bool = True
    guardrail_safety_enabled: bool = True
    guardrail_price_manipulation_enabled: bool = True
    guardrail_product_grounding_enabled: bool = True
    guardrail_output_schema_enabled: bool = True
    guardrail_tone_enabled: bool = True
    guardrail_output_safety_enabled: bool = True

    # ── Content Safety Provider ───────────────────────────────────────────────
    # Supported: "mock" (no external API, default), "azure"
    content_safety_provider: str = "mock"
    azure_content_safety_endpoint: str = ""
    azure_content_safety_key: str = ""


# Single shared instance — import this everywhere
settings = Settings()
