"""src/chat.py — LLM interaction: build grounded prompt and stream answer from Ollama."""

import json
from typing import Iterator

import requests

from src import config
from src.retriever import get_context


def check_ollama() -> bool:
    """Return True if Ollama is reachable."""
    try:
        tags_url = config.OLLAMA_URL.replace("/api/generate", "/api/tags")
        return requests.get(tags_url, timeout=3).status_code == 200
    except Exception:
        return False


def _stream_ollama(prompt: str) -> Iterator[str]:
    try:
        response = requests.post(
            config.OLLAMA_URL,
            json={
                "model":   config.OLLAMA_MODEL,
                "prompt":  prompt,
                "stream":  True,
                "options": {
                    "temperature": config.OLLAMA_TEMPERATURE,
                    "num_predict": config.OLLAMA_MAX_TOKENS,
                },
            },
            stream=True,
            timeout=config.OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if chunk.get("response"):
                    yield chunk["response"]
                if chunk.get("done"):
                    break
    except requests.exceptions.ConnectionError:
        yield "\n\n[Ollama is offline — run: ollama serve]"
    except Exception as e:
        yield f"\n\n[Error: {e}]"


def get_answer(
    question: str,
    collection: str,
) -> tuple[Iterator[str], list[dict]]:
    """Retrieve context and stream a grounded answer from Ollama.

    Returns (token_stream, citations). If no relevant context is found,
    returns a no-answer generator with empty citations (no LLM call made).
    """
    context, citations = get_context(question, collection)

    if not context:
        def _no_context() -> Iterator[str]:
            yield config.NO_ANSWER
        return _no_context(), []

    prompt = config.PROMPT_TEMPLATE.format(
        system=config.SYSTEM_PROMPT,
        context=context,
        question=question,
    )
    return _stream_ollama(prompt), citations
