import json
import logging
import re

import ollama

from agent.prompts import SYSTEM_PROMPT
from agent.state import AgentState, OrderItem, StopReason
from config import MAX_ITERATIONS, OLLAMA_MODEL
from tools.inventory import check_stock
from tools.pricing import price_order
from tools.shipping import delivery_eta

logger = logging.getLogger(__name__)

# Ollama uses OpenAI-style tool schema — NOT Anthropic's "input_schema" format
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": (
                "Check whether the requested quantity of a product is available in stock. "
                "Pass the product name exactly as the user said it "
                "(e.g. 'polo t-shirt', 'denim jeans', 'running shoes'). "
                "The tool resolves the name automatically. "
                "If the user does not specify a quantity, use 1."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product name or product ID as given by the user",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity requested. Default to 1 if not specified.",
                    },
                },
                "required": ["product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "price_order",
            "description": (
                "⚠️ PREREQUISITE: check_stock MUST be called first and return available=true. "
                "Calculate the total price for a product quantity, including any applicable discount. "
                "NEVER call this before confirming stock availability. "
                "Use the EXACT same product name or ID that was passed to check_stock."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product name or ID — MUST be the exact same value used in check_stock call",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity to order (must match check_stock quantity)",
                    },
                },
                "required": ["product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delivery_eta",
            "description": (
                "🚫 ONLY call this when the user explicitly provides an actual 6-digit numeric PIN code. "
                "Do NOT guess, calculate, or infer PIN codes from city/location names. "
                "If the user says 'Bhubaneswar' or 'Delhi' instead of a PIN: "
                "Ask FIRST: 'Could you please share the 6-digit PIN code for [location]?' "
                "Then WAIT for the user's response before calling this tool. "
                "Only then call this tool with the actual PIN code the user provided."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pincode": {
                        "type": "string",
                        "description": "6-digit numeric Indian PIN code (MUST be provided explicitly by user, never guessed)",
                    },
                },
                "required": ["pincode"],
            },
        },
    },
]

TOOL_MAP = {
    "check_stock": check_stock,
    "price_order": price_order,
    "delivery_eta": delivery_eta,
}

_NOISE_RE = re.compile(
    r"("
    r"corrected tool call"
    r"|tool call:"
    r"|calling tool"
    r"|let me (?:try|call|use|check)"
    r"|check_stock\s*[\(\{]"
    r"|price_order\s*[\(\{]"
    r"|delivery_eta\s*[\(\{]"
    r"|unfortunately.*unable to determine"
    r"|please wait for the result"
    r"|it seems there.{0,30}issue with the tool"
    r"|tool is not available"
    r"|not properly configured"
    r"|i.ll try again"
    r"|please check the tools"
    r'|"name"\s*:\s*"(?:check_stock|price_order|delivery_eta)"'
    r")",
    re.IGNORECASE,
)


def _is_out_of_scope(text: str) -> bool:
    """Detect if the model recognized a request as out-of-scope."""
    text_lower = text.lower()
    out_of_scope_markers = (
        "out of scope",
        "not related to",
        "not about store",
        "can't help with that",
        "only help with",
        "limited to",
        "only assist",
        "i can only",
        "outside my scope",
        "unrelated to",
    )
    return any(marker in text_lower for marker in out_of_scope_markers)


def _clean_response(text: str) -> str:
    """Strip internal tool-call reasoning and hallucinated raw data from user-facing text."""
    lines = text.splitlines()
    clean = []
    for ln in lines:
        if _NOISE_RE.search(ln):
            continue
        stripped = ln.strip()
        # Drop JSON tool-call blobs (double-quoted keys)
        if stripped.startswith("{") and any(
            k in stripped
            for k in ('"check_stock"', '"price_order"', '"delivery_eta"',
                      '"parameters"', '"arguments"', '"product_id"',
                      '"product_name"', '"final_price"')
        ):
            continue
        # Drop Python dict blobs (single-quoted keys) e.g. {'product_id': ...}
        if stripped.startswith("{") and any(
            k in stripped
            for k in ("'product_id'", "'product_name'", "'final_price'",
                      "'check_stock'", "'price_order'", "'delivery_eta'",
                      "'available'", "'unit_price'", "'price':")
        ):
            continue
        clean.append(ln)
    result = "\n".join(clean).strip()
    return result or "I'm sorry, I couldn't complete that request. Please try again."


def _parse_text_tool_call(text: str) -> tuple[str, dict] | None:
    """
    Fallback: detect when the model outputs a tool call as JSON text instead of
    using the function-calling API. Handles formats like:
      {"name": "check_stock", "parameters": {"product_id": "Polo T-Shirt", "quantity": "1"}}
      {"name": "check_stock", "arguments": {...}}
    Returns (tool_name, tool_input) or None.
    """
    # Try to find any JSON blob in the text
    json_matches = re.findall(r"\{[^{}]*\}", text)
    for blob in json_matches:
        try:
            obj = json.loads(blob)
        except json.JSONDecodeError:
            # Try to extract larger nested JSON
            continue
        tool_name = obj.get("name") or obj.get("function")
        args = obj.get("parameters") or obj.get("arguments") or obj.get("input") or {}
        if tool_name and tool_name in TOOL_MAP and isinstance(args, dict):
            return tool_name, args

    # Also try larger JSON blocks (nested braces)
    try:
        start = text.index("{")
        obj = json.loads(text[start:])
        tool_name = obj.get("name") or obj.get("function")
        args = obj.get("parameters") or obj.get("arguments") or obj.get("input") or {}
        if tool_name and tool_name in TOOL_MAP and isinstance(args, dict):
            return tool_name, args
    except (ValueError, json.JSONDecodeError):
        pass

    return None


def _coerce_tool_input(tool_name: str, raw_input: dict) -> dict:
    """
    Coerce argument types to match tool signatures.
    Models sometimes return quantity as a string "1" instead of integer 1.
    """
    result = dict(raw_input)
    if tool_name in ("check_stock", "price_order"):
        if "quantity" in result:
            try:
                result["quantity"] = int(result["quantity"])
            except (ValueError, TypeError):
                result["quantity"] = 1
    return result


def _validate_tool_call(tool_name: str, state: AgentState) -> dict | None:
    """
    Validate that tool call respects the mandatory sequence:
    1. check_stock must be called first
    2. price_order only after successful check_stock
    3. delivery_eta only when stock checked (and user provided PIN)
    Returns error dict if invalid, None if valid.
    """
    trace = state.trace

    if tool_name == "price_order":
        if not any(t["tool"] == "check_stock" and not t["result"].get("error") for t in trace):
            return {
                "error": True,
                "message": (
                    "❌ You must call check_stock FIRST to verify stock availability before pricing. "
                    "Please call check_stock first with the product name/ID and quantity."
                ),
            }

    if tool_name == "delivery_eta":
        if not any(t["tool"] == "check_stock" and not t["result"].get("error") for t in trace):
            return {
                "error": True,
                "message": (
                    "❌ You must check stock first before asking for delivery estimates. "
                    "Please call check_stock with the product name/ID and quantity first."
                ),
            }

    return None


def _execute_tool(tool_name: str, tool_input: dict, state: AgentState) -> dict:
    validation_error = _validate_tool_call(tool_name, state)
    if validation_error:
        logger.warning(f"Tool call rejected: {tool_name} — {validation_error['message']}")
        return validation_error

    fn = TOOL_MAP.get(tool_name)
    if not fn:
        return {"error": True, "message": f"Unknown tool: {tool_name}"}
    tool_input = _coerce_tool_input(tool_name, tool_input)
    try:
        return fn(**tool_input)
    except Exception as e:
        logger.error(f"Tool {tool_name} raised: {e}")
        return {"error": True, "message": f"Tool {tool_name} failed: {str(e)}"}


def _update_state_from_tool(
    state: AgentState, tool_name: str, tool_input: dict, result: dict
) -> None:
    if tool_name == "check_stock" and not result.get("error"):
        state.pending_product = result.get("product_name") or tool_input.get("product_id")
        state.pending_quantity = tool_input.get("quantity")

    if tool_name == "price_order" and not result.get("error"):
        item = OrderItem(
            product_id=result["product_id"],
            product_name=result["product_name"],
            quantity=result["quantity"],
            unit_price=result["unit_price"],
            final_price=result["final_price"],
            discount_percentage=result["discount_percentage"],
        )
        state.add_order_item(item)
        state.pending_product = None
        state.pending_quantity = None

    if tool_name == "delivery_eta" and not result.get("error"):
        state.destination_pincode = tool_input.get("pincode", "")

    state.add_trace_step(tool_name, tool_input, result)


def _build_context_message(state: AgentState) -> dict | None:
    summary = state.order_summary()
    if summary == "No items in the current order.":
        return None
    return {
        "role": "system",
        "content": f"CURRENT ORDER STATE (use this as context for the conversation):\n{summary}",
    }


def run_agent(user_message: str, state: AgentState) -> str:
    """Run the ReAct agent loop for one user turn. Returns clean final text."""
    state.messages.append({"role": "user", "content": user_message})
    state.iteration_count = 0
    state.stop_reason = StopReason.UNKNOWN
    state.refusal_message = None

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    ctx = _build_context_message(state)
    if ctx:
        messages.append(ctx)
    messages.extend(state.messages)

    while state.iteration_count < MAX_ITERATIONS:
        state.iteration_count += 1
        logger.info(f"Agent iteration {state.iteration_count}")

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )

        msg = response["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            raw = msg.get("content", "") or ""

            # Fallback: model may have output a tool call as JSON text
            text_tc = _parse_text_tool_call(raw)
            if text_tc:
                tool_name, tool_input = text_tc
                logger.info(f"[text-fallback] Detected tool call in text: {tool_name}({tool_input})")
                result = _execute_tool(tool_name, tool_input, state)
                _update_state_from_tool(state, tool_name, tool_input, result)
                # Feed result back as a plain user message (text-fallback path)
                messages.append({
                    "role": "user",
                    "content": (
                        f"Tool '{tool_name}' was called and returned this result:\n"
                        f"{json.dumps(result, indent=2)}\n"
                        "Please use this result to continue helping the customer."
                    ),
                })
                continue  # loop — let LLM decide next step

            # Genuine final text response
            final_text = _clean_response(raw)
            state.messages.append({"role": "assistant", "content": final_text})
            
            # Detect stop reason based on response content
            if _is_out_of_scope(raw):
                state.stop_reason = StopReason.OUT_OF_SCOPE
                state.refusal_message = final_text
                logger.info(f"Agent stopped: out-of-scope request detected")
            else:
                state.stop_reason = StopReason.SUCCESS
                logger.info(f"Agent stopped: request completed successfully")
            
            return final_text

        # Execute API-level tool calls
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_input = tc["function"]["arguments"]
            if isinstance(tool_input, str):
                tool_input = json.loads(tool_input)

            call_id = tc.get("id", "")
            logger.info(f"[api] Calling tool: {tool_name}({tool_input})")
            result = _execute_tool(tool_name, tool_input, state)
            _update_state_from_tool(state, tool_name, tool_input, result)

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result),
            })

    # Max iterations reached - grounded refusal with explanation
    state.stop_reason = StopReason.MAX_ITERATIONS
    fallback = (
        "I apologize, but I'm having difficulty processing your request after several attempts. "
        "This usually means the request may be too complex or outside my store assistance capabilities. "
        "I can help you with:\n"
        "• Checking product stock availability\n"
        "• Calculating prices with discounts\n"
        "• Estimating delivery times\n"
        "• Managing your order\n\n"
        "Could you please rephrase your question or ask about a specific product?"
    )
    state.refusal_message = fallback
    state.messages.append({"role": "assistant", "content": fallback})
    logger.info(f"Agent stopped: max iterations reached ({MAX_ITERATIONS})")
    return fallback
