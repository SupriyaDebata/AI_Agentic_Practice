"""
extractor.py — calls LLM providers with the unified invoice extraction prompt.
Supports: Ollama (local), Google Gemini, Claude (Anthropic), GPT (OpenAI)
Optimized with connection pooling for faster responses.
"""

import re, json, hashlib, requests
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_exponential

OLLAMA_URL    = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.1"
TIMEOUT       = 120  # Reduced from 300 for faster feedback

_prompt_cache = {}
_result_cache = {}

# Session pooling for faster requests
_session = None

def _get_session():
    """Reuse a requests session with connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
        retry_strategy = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
    return _session


def warmup():
    """Pre-warm Ollama model so first extraction is fast."""
    _load_prompt()
    session = _get_session()
    r = session.post(OLLAMA_URL, json={
        "model": DEFAULT_MODEL, "prompt": "Reply with the single word: ready",
        "stream": False, "options": {"temperature": 0, "num_predict": 5},
    }, timeout=60)
    r.raise_for_status()


def _load_prompt() -> str:
    if "unified" in _prompt_cache:
        return _prompt_cache["unified"]
    text   = Path("prompts/invoiceExtractor.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL)
    if not blocks:
        raise ValueError("No fenced code block found in prompts/invoiceExtractor.md")
    _prompt_cache["unified"] = blocks[0].strip()
    return _prompt_cache["unified"]


# ── LLM provider calls ────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
def _call_ollama(prompt: str, model: str = None) -> str:
    model = model or DEFAULT_MODEL
    session = _get_session()
    r = session.post(OLLAMA_URL, json={
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0, "num_predict": 600},
    }, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("response", "").strip()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=3))
def _call_gemini(prompt: str, model: str = "gemini-2.0-flash", api_key: str = "") -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    session = _get_session()
    r = session.post(url, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 600},
    }, timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=3))
def _call_claude(prompt: str, model: str = "claude-3-5-sonnet-20241022", api_key: str = "") -> str:
    model_map = {
        "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3-opus":     "claude-3-opus-20240229",
        "claude-3-haiku":    "claude-3-haiku-20240307",
    }
    model = model_map.get(model, model)
    session = _get_session()
    r = session.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": 600, "temperature": 0,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"].strip()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=3))
def _call_openai(prompt: str, model: str = "gpt-4o", api_key: str = "") -> str:
    session = _get_session()
    r = session.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0, "max_tokens": 600,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _call_llm(prompt: str, provider: str = "ollama",
              model: str = None, api_key: str = None) -> str:
    if provider == "ollama":
        return _call_ollama(prompt, model=model)
    elif provider == "gemini":
        return _call_gemini(prompt, model=model or "gemini-2.0-flash", api_key=api_key or "")
    elif provider == "claude":
        return _call_claude(prompt, model=model or "claude-3-5-sonnet-20241022", api_key=api_key or "")
    elif provider == "openai":
        return _call_openai(prompt, model=model or "gpt-4o", api_key=api_key or "")
    else:
        raise ValueError(f"Unknown provider '{provider}'. Choose: ollama, gemini, claude, openai")


# ── JSON helpers ──────────────────────────────────────────────────────────────

def _clean_json(raw: str) -> str:
    raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"```[a-zA-Z]*\s*\n?", "", raw)
    raw = re.sub(r"\n?```\s*", "", raw)
    xml_match = re.search(r"<output>(.*?)</output>", raw, re.DOTALL)
    if xml_match:
        raw = xml_match.group(1)
    return raw.strip()


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return ""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return ""


def _parse_json(raw: str) -> dict:
    for candidate in [_clean_json(raw), _extract_json_object(_clean_json(raw)),
                      _extract_json_object(raw)]:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            # Model sometimes wraps the object in a list — unwrap first element
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                return parsed[0]
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    return {"_parsing_error": f"Failed to parse JSON. Raw: {raw[:200]}"}


def _ensure_fields(result) -> dict:
    # Guard: if model returned non-dict (list, string, etc.) start fresh
    if not isinstance(result, dict):
        result = {}
    for field in ["invoice_number", "invoice_date", "vendor", "bill_to",
                  "subtotal", "tax", "total", "payment_terms", "currency"]:
        if field not in result:
            result[field] = None
    # Ensure _confidence is always a flat string-keyed dict
    conf = result.get("_confidence")
    if not isinstance(conf, dict):
        result["_confidence"] = {}
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def extract(invoice_text: str, provider: str = "ollama",
            model: str = None, api_key: str = None) -> dict:
    cache_key = hashlib.sha256(f"{invoice_text}{provider}{model}".encode()).hexdigest()[:20]
    if cache_key in _result_cache:
        return _result_cache[cache_key]

    template = _load_prompt()
    prompt   = template.replace("{{invoice_text}}", invoice_text)
    raw      = _call_llm(prompt, provider=provider, model=model, api_key=api_key)
    result   = _parse_json(raw)
    result   = _ensure_fields(result)

    _result_cache[cache_key] = result
    return result
