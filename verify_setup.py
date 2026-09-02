#!/usr/bin/env python3
"""verify_setup.py — Pre-demo health check: data files, ChromaDB, and Ollama."""

from pathlib import Path
import requests

from src import config

BASE = Path(__file__).parent

# ── 1. Data files ─────────────────────────────────────────────────────────────
print("── Data Files ──────────────────────────────────────────────────")
expected = [
    BASE / "data" / "pdf"   / "Company_Policy.pdf",
    BASE / "data" / "pdf"   / "Employee_Handbook.pdf",
    BASE / "data" / "pdf"   / "Product_Specification.pdf",
    BASE / "data" / "excel" / "Customer_Data.xlsx",
    BASE / "data" / "excel" / "Sales_Data.xlsx",
]
all_ok = True
for f in expected:
    status = "✅" if f.exists() else "❌ MISSING"
    size   = f"{f.stat().st_size // 1024} KB" if f.exists() else ""
    print(f"  {status}  {f.name}  {size}")
    if not f.exists():
        all_ok = False

# ── 2. ChromaDB ───────────────────────────────────────────────────────────────
print("\n── ChromaDB ────────────────────────────────────────────────────")
try:
    import chromadb
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    cols = client.list_collections()
    if cols:
        for c in cols:
            col = client.get_collection(c.name)
            print(f"  ✅  Collection '{c.name}' — {col.count()} chunks")
    else:
        print("  ⚠️  No collections found — upload documents first")
except Exception as e:
    print(f"  ❌  ChromaDB error: {e}")
    all_ok = False

# ── 3. Ollama ─────────────────────────────────────────────────────────────────
print("\n── Ollama LLM ──────────────────────────────────────────────────")
try:
    tags_url = config.OLLAMA_URL.replace("/api/generate", "/api/tags")
    r = requests.get(tags_url, timeout=5)
    if r.status_code == 200:
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"  ✅  Ollama running — models: {', '.join(models) or 'none pulled'}")
        if config.OLLAMA_MODEL not in " ".join(models):
            print(f"  ⚠️  Configured model '{config.OLLAMA_MODEL}' not found — run: ollama pull {config.OLLAMA_MODEL}")
    else:
        print(f"  ❌  Ollama returned HTTP {r.status_code}")
        all_ok = False
except Exception:
    print("  ❌  Ollama not reachable — run: ollama serve")
    all_ok = False

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n────────────────────────────────────────────────────────────────")
print("✅  All checks passed — ready for demo!" if all_ok else "❌  Fix the issues above before the demo.")
