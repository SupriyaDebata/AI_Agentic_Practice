"""Search page — Streamlit UI with integrated guardrails and observability.

Flow:
  User Input
    → Input Guardrail Pipeline  (PII, injection, topic, safety, price)
    → CatalogSearchService      (SQL + BM25 + Vector + RRF)
    → Output Guardrail Pipeline (grounding, safety, tone)
    → LangSmith Trace           (latency, tokens, cost, guardrail decisions)
    → Render to user
"""
import streamlit as st

from app.config import get_logger, settings

logger = get_logger(__name__)


@st.cache_resource(show_spinner="Loading catalog and building indexes...")
def _get_service():
    from app.services.catalog_service import CatalogSearchService
    svc = CatalogSearchService()
    svc.initialize()
    return svc


def _format_sql_filters(filters) -> str:
    parts = []
    if filters.colour:
        parts.append(f"colour={filters.colour}")
    if filters.gender:
        parts.append(f"gender={filters.gender}")
    if filters.kids_age:
        parts.append(f"kids_age={filters.kids_age}")
    if filters.category:
        parts.append(f"category={filters.category}")
    if filters.brand:
        parts.append(f"brand={filters.brand}")
    if filters.price_min is not None:
        parts.append(f"price ≥ ₹{filters.price_min}")
    if filters.price_max is not None:
        parts.append(f"price ≤ ₹{filters.price_max}")
    if filters.stock:
        parts.append("in_stock=True")
    return " AND ".join(parts) if parts else "—"


def _render_product(p: dict, idx: int) -> None:
    stock = "✅ In Stock" if p.get("stock") else "❌ Out of Stock"
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{idx}. {p['product_name']}**")
            st.caption(p.get("description", ""))
            st.markdown(
                f"Age: `{p.get('kids_age','—')}` &nbsp;|&nbsp; "
                f"Size: `{p.get('size','—')}` &nbsp;|&nbsp; "
                f"Colour: `{p.get('colour','—')}` &nbsp;|&nbsp; "
                f"Gender: `{p.get('gender','—')}` &nbsp;|&nbsp; "
                f"Brand: `{p.get('brand','—')}`"
            )
        with col2:
            st.markdown(f"### ₹{p['price']}")
            st.caption(stock)


def _render_guardrail_badge(action: str, name: str) -> None:
    color = {"BLOCK": "🔴", "SANITIZE": "🟡", "ALLOW": "🟢", "FALLBACK": "🟠"}.get(action, "⚪")
    st.caption(f"{color} {name}: {action}")


def show_search_page() -> None:
    st.header("🛍️ Find Your Perfect Outfit")
    st.caption("Describe what you're looking for, and we'll find the best matches.")
    st.divider()

    service = _get_service()

    # Replay conversation history
    for msg in st.session_state.get("conversation_history", []):
        role = msg["role"]
        avatar = "👤" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])
            for p in msg.get("products", []):
                _render_product(p, msg["products"].index(p) + 1)

    user_input = st.chat_input(
        "What are you looking for? e.g. 'white dress for 7-8 years' or 'birthday outfit'"
    )

    if not user_input:
        return

    # Show user bubble immediately
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # ── Observability: per-request tracking ──────────────────────────────────
    from app.observability.latency_tracker import LatencyTracker
    from app.observability.cost_calculator import TokenUsage
    from app.observability.metrics import RequestMetrics, record as record_metrics
    from app.observability.langsmith_tracer import (
        trace_request, log_guardrail_decisions, log_latency_and_cost,
        log_retrieval_info,
    )

    tracker = LatencyTracker()
    req_metrics = RequestMetrics(request_id=tracker.request_id)

    with trace_request(
        "RetailChatRequest",
        metadata={"request_id": tracker.request_id, "query_len": len(user_input)},
    ) as ls_run:

        # ── INPUT GUARDRAILS ──────────────────────────────────────────────────
        from app.guardrails.pipeline.input_guardrail_pipeline import run_input_guardrails

        tracker.start_span("input_guardrails")
        guarded_req, guard_ms = run_input_guardrails(user_input)
        tracker.record_span("input_guardrails", guard_ms)

        req_metrics.guardrail_latency_ms = guard_ms
        req_metrics.sanitized = guarded_req.was_sanitized
        if guarded_req.was_sanitized:
            blocked_guard = next(
                (r for r in guarded_req.guardrail_results if r.action.value == "SANITIZE"), None
            )
            if blocked_guard:
                req_metrics.guardrail_triggered = blocked_guard.guardrail_name

        log_guardrail_decisions(ls_run, guarded_req.guardrail_results)

        if guarded_req.blocked:
            # Find which guardrail blocked
            blocking = next(
                (r for r in guarded_req.guardrail_results if not r.passed), None
            )
            req_metrics.blocked = True
            req_metrics.allowed = False
            req_metrics.guardrail_triggered = blocking.guardrail_name if blocking else "unknown"
            req_metrics.total_latency_ms = tracker.total_ms
            record_metrics(req_metrics)

            with st.chat_message("assistant", avatar="🤖"):
                st.warning(guarded_req.block_reason)
                if st.session_state.get("debug_mode"):
                    st.caption(f"🛡️ Blocked by: {req_metrics.guardrail_triggered} | {guard_ms} ms")

            _persist_history(user_input, guarded_req.block_reason, [], tracker, blocked=True)
            st.rerun()
            return

        # ── RETRIEVAL ────────────────────────────────────────────────────────
        history = st.session_state.get("conversation_history", [])
        context = "\n".join(
            f"user: {m['content']}" for m in history[-6:] if m["role"] == "user"
        )

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Searching..."):
                tracker.start_span("retrieval")
                intent = service.parse_query(guarded_req.sanitized_text, context)
                
                # Log extracted filters for debugging
                logger.info(
                    "filters_extracted",
                    brand=intent.hard_filters.brand,
                    price_min=intent.hard_filters.price_min,
                    price_max=intent.hard_filters.price_max,
                    category=intent.hard_filters.category,
                    colour=intent.hard_filters.colour,
                    gender=intent.hard_filters.gender,
                    kids_age=intent.hard_filters.kids_age,
                )
                
                response = service.search(intent)
                ret_ms = tracker.end_span("retrieval")

        req_metrics.retrieval_latency_ms = ret_ms
        if response.latency_ms:
            req_metrics.sql_latency_ms = response.latency_ms.get("sql_ms", 0.0)
            req_metrics.vector_latency_ms = response.latency_ms.get("vector_ms", 0.0)
            req_metrics.bm25_latency_ms = response.latency_ms.get("bm25_ms", 0.0)

        retrieved_ids = [sr.product.id for sr in response.results]

        products = [
            {
                "id": sr.product.id,
                "product_name": sr.product.product_name,
                "description": sr.product.description,
                "price": sr.product.price,
                "size": sr.product.size,
                "colour": sr.product.colour,
                "kids_age": sr.product.kids_age,
                "gender": sr.product.gender,
                "brand": sr.product.brand,
                "stock": sr.product.stock,
            }
            for sr in response.results
        ]

        # ── Token/cost estimation ────────────────────────────────────────────
        # Ollama local model: input = query + context, output = reply
        raw_reply = (
            f"✨ Found **{len(products)} product(s)** for you!"
            if products
            else "😔 No products matched. Try adjusting your search."
        )

        token_usage = TokenUsage(
            model=settings.ollama_model,
            input_tokens=max(1, len(guarded_req.sanitized_text + context) // 4),
            output_tokens=max(1, len(raw_reply) // 4),
        )
        req_metrics.input_tokens = token_usage.input_tokens
        req_metrics.output_tokens = token_usage.output_tokens
        req_metrics.estimated_cost_inr = token_usage.estimated_cost_inr

        # ── OUTPUT GUARDRAILS ────────────────────────────────────────────────
        from app.guardrails.pipeline.output_guardrail_pipeline import run_output_guardrails

        tracker.start_span("output_guardrails")
        guarded_resp, out_guard_ms = run_output_guardrails(raw_reply, products, retrieved_ids, query=user_input)
        tracker.record_span("output_guardrails", out_guard_ms)

        req_metrics.output_guardrail_latency_ms = out_guard_ms
        req_metrics.fallback_used = guarded_resp.fallback_used
        if guarded_resp.fallback_used:
            hallucination_guard = next(
                (r for r in guarded_resp.guardrail_results if r.guardrail_name == "ProductGrounding" and not r.passed),
                None,
            )
            req_metrics.hallucination_prevented = hallucination_guard is not None

        log_guardrail_decisions(ls_run, guarded_resp.guardrail_results)

        final_reply = str(guarded_resp.final_response)

        # ── Render response ──────────────────────────────────────────────────
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(final_reply)
            for i, p in enumerate(products, 1):
                _render_product(p, i)

            if st.session_state.get("debug_mode"):
                with st.expander("🔍 Debug: Guardrails + Observability"):
                    st.json(tracker.to_dict())
                    st.json(token_usage.to_dict())
                    for r in guarded_req.guardrail_results + guarded_resp.guardrail_results:
                        _render_guardrail_badge(r.action.value, r.guardrail_name)

        # ── Finalize metrics ─────────────────────────────────────────────────
        req_metrics.no_match = len(products) == 0
        req_metrics.total_latency_ms = tracker.total_ms

        log_latency_and_cost(ls_run, tracker.to_dict(), token_usage.to_dict())
        log_retrieval_info(
            ls_run,
            str(response.route_used),
            response.total_candidates,
            len(products),
        )

        record_metrics(req_metrics)

        sql_summary = _format_sql_filters(intent.hard_filters)
        _persist_history(
            user_input, final_reply, products, tracker,
            sql_summary=sql_summary,
            vector_query=intent.semantic_query or "",
            route=str(response.route_used),
            candidates=response.total_candidates,
        )

    st.rerun()


def _persist_history(
    user_input: str,
    reply: str,
    products: list,
    tracker,
    blocked: bool = False,
    sql_summary: str = "—",
    vector_query: str = "",
    route: str = "",
    candidates: int = 0,
) -> None:
    history = st.session_state.get("conversation_history", [])
    history.append({"role": "user", "content": user_input, "products": []})
    history.append({
        "role": "assistant",
        "content": reply,
        "sql_summary": sql_summary,
        "vector_query": vector_query,
        "route": route,
        "candidates": candidates,
        "result_count": len(products),
        "latency_ms": tracker.total_ms,
        "blocked": blocked,
        "products": products,
    })
    st.session_state.conversation_history = history
