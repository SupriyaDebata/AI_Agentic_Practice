#!/usr/bin/env python
"""Quick test of extractor module"""
import sys
from pathlib import Path

# Test 1: Load first invoice
print("=" * 60)
print("TEST 1: Loading sample invoice...")
test_invoice = Path("invoices/01-valid-values-inr.txt").read_text()
print(f"✓ Loaded {len(test_invoice)} chars")
print(f"First 100 chars: {test_invoice[:100]}")

# Test 2: Import extractor
print("\n" + "=" * 60)
print("TEST 2: Importing extractor...")
try:
    from extractor import extract
    print("✓ Imported extractor.extract()")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 3: Check if Ollama is available
print("\n" + "=" * 60)
print("TEST 3: Checking Ollama availability...")
try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=2)
    if r.status_code == 200:
        print("✓ Ollama is running!")
        print(f"Response: {r.text[:200]}")
    else:
        print(f"✗ Ollama returned status {r.status_code}")
except Exception as e:
    print(f"✗ Ollama not running: {e}")
    print("  To fix: Run 'ollama serve' in another terminal")

print("\n" + "=" * 60)
print("Note: Extraction requires a running LLM provider (Ollama, Gemini, Claude, or OpenAI)")
print("Set .env file with API keys or start Ollama locally")
