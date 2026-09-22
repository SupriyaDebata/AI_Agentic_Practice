"""LangSmith observability integration.

Provides a thin wrapper around LangSmith tracing.  All tracing is
opt-in via the LANGSMITH_TRACING environment variable.

When disabled (default in local/dev), all calls are no-ops so the
application works without LangSmith credentials.

NEVER send raw PII to LangSmith — always pass sanitized_text.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from app.config import get_logger

logger = get_logger(__name__)

_ENABLED: bool = os.getenv("LANGSMITH_TRACING", "false").lower() in ("true", "1", "yes")
_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "retail-chatbot-week7")

# Lazy import — only attempt if enabled
_ls_client: Any = None


def _get_client() -> Any:
    global _ls_client
    if _ls_client is not None:
        return _ls_client
    try:
        from langsmith import Client  # type: ignore[import-not-found]
        _ls_client = Client()
        logger.info("langsmith_client_ready", project=_PROJECT)
        return _ls_client
    except Exception as exc:
        logger.warning("langsmith_client_init_failed", error=str(exc))
        return None


def is_enabled() -> bool:
    return _ENABLED


@contextmanager
def trace_request(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    """Context manager that wraps a request in a LangSmith run.

    Yields the run object if LangSmith is available, otherwise yields None.
    The caller can pass extra metadata or tags via the returned run object.

    Example:
        with trace_request("RetailChatRequest", {"request_id": rid}) as run:
            do_work()
            if run:
                add_metadata_to_run(run, {"guardrail_result": ...})
    """
    if not _ENABLED:
        yield None
        return

    try:
        from langsmith import trace as ls_trace  # type: ignore[import-not-found]
        with ls_trace(
            name=name,
            project_name=_PROJECT,
            metadata=metadata or {},
        ) as run:
            yield run
    except ImportError:
        logger.warning("langsmith_not_installed")
        yield None
    except Exception as exc:
        logger.warning("langsmith_trace_failed", error=str(exc))
        yield None


def add_run_metadata(run: Any, extra: Dict[str, Any]) -> None:
    """Safely add metadata to an active LangSmith run."""
    if run is None:
        return
    try:
        run.add_metadata(extra)
    except Exception as exc:
        logger.debug("langsmith_add_metadata_failed", error=str(exc))


def log_guardrail_decisions(run: Any, guardrail_results: list) -> None:
    """Serialize guardrail decisions and attach to the run."""
    if run is None or not guardrail_results:
        return
    decisions = {
        r.guardrail_name: {
            "action": r.action.value,
            "passed": r.passed,
            "reason": r.reason,
        }
        for r in guardrail_results
    }
    add_run_metadata(run, {"guardrail_decisions": decisions})


def log_latency_and_cost(run: Any, latency_dict: dict, cost_dict: dict) -> None:
    """Attach latency and cost info to the run."""
    add_run_metadata(run, {"latency": latency_dict, "cost": cost_dict})


def log_retrieval_info(run: Any, route: str, candidate_count: int, result_count: int) -> None:
    add_run_metadata(run, {
        "retrieval": {
            "route": route,
            "candidates": candidate_count,
            "results_returned": result_count,
        }
    })
