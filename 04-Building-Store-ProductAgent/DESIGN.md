# Store Assistant Agent — Design Document

## Architecture

```
Streamlit UI (app.py)
       |
       v
   Agent Loop (agent/agent.py)
       |
       v
   Ollama LLM — tool calling
       |
   ┌───┴──────────────────────────┐
   ↓            ↓                 ↓
check_stock  price_order    delivery_eta
inventory.json  inventory.json   shipping.json
                + discounts.json
```

## Tool Contracts

### check_stock
- **Purpose**: Verify product availability before pricing
- **Input**: `product_id: str`, `quantity: int`
- **Output**: `{available, available_quantity, product_name, ...}`
- **Failure**: Returns `{error: true, message: "..."}` for unknown product or qty ≤ 0

### price_order
- **Purpose**: Calculate final price with volume-based discounts
- **Input**: `product_id: str`, `quantity: int`
- **Output**: `{subtotal, discount_percentage, discount_amount, final_price, currency}`
- **Discount Logic**:
  - Discounts are applied based on product category and minimum quantity threshold
  - When quantity meets or exceeds the minimum threshold, the discount percentage is applied to the subtotal
  - Calculation: `discount_amount = round(subtotal × discount_pct / 100, 2)` then `final_price = subtotal - discount_amount`
  - Example for Jackets (₹2499 each, 2 units, 8% discount):
    - Subtotal: 2499 × 2 = ₹4998
    - Discount: 4998 × 8 / 100 = ₹399.84
    - Final Price: 4998 - 399.84 = ₹4598.16
- **Failure**: Returns error if product not found

### delivery_eta
- **Purpose**: Look up delivery days for a PIN code
- **Input**: `pincode: str`
- **Output**: `{estimated_delivery_days}` or `{available: false, message}`
- **Failure**: Unknown PIN returns controlled unavailable response

## Agent State

| Field | Purpose |
|---|---|
| `messages` | Full conversation history passed to LLM each turn |
| `order_items` | List of items added to current order |
| `order_total` | Sum of final_price for all order items |
| `destination_pincode` | Remembered PIN across turns |
| `trace` | Execution log shown in UI |
| `iteration_count` | Guards against infinite loops |
| `stop_reason` | Why the agent stopped (StopReason enum) |
| `refusal_message` | Grounded explanation if stopped due to error/out-of-scope |

## Stop Reasons

The agent tracks why it stopped via the `StopReason` enum:

| Reason | When | Response |
|--------|------|----------|
| `SUCCESS` | Request completed normally | Final answer provided |
| `OUT_OF_SCOPE` | Request outside store scope (e.g., "What's the weather?") | Grounded refusal explaining scope limits |
| `MAX_ITERATIONS` | Exceeded MAX_ITERATIONS loop limit | Grounded refusal + list of what we CAN help with |
| `PRODUCT_NOT_FOUND` | All tools failed to find product | Apology + offer to search for different item |
| `UNKNOWN` | Default/unclassified | Should not reach user |

## Agent Loop (ReAct)

```
User message
    ↓
Reason: LLM reads conversation + state
    ↓
Act: LLM emits tool_use block (or final text)
    ↓
Observe: tool executes, result returned
    ↓
Update state: order_items, trace updated
    ↓
Decide: LLM sees result, chooses next action
    ↓ (repeat up to MAX_ITERATIONS=10)
Stop: LLM returns text → final response
```

## Stopping Conditions

1. **Text Response (No Tool Calls)** — LLM returns natural language answer (normal completion)
   - `stop_reason = SUCCESS` (or `OUT_OF_SCOPE` if marked as unrelated)
   - Response is cleaned and returned to user

2. **Out-of-Scope Request** — User asks about something unrelated to store (e.g., weather, jokes, general knowledge)
   - Detected via markers in LLM output ("out of scope", "not related", "only help with", etc.)
   - `stop_reason = OUT_OF_SCOPE`
   - Grounded refusal explaining that only store assistance is available

3. **Max Iterations Reached** — Loop exceeded MAX_ITERATIONS (safety limit)
   - `stop_reason = MAX_ITERATIONS`
   - Grounded refusal + **list of what we CAN help with** (products, pricing, stock, delivery)
   - Invites user to rephrase or ask about specific products

4. **Tool Exception** — Tool returns error (product not found, invalid PIN, etc.)
   - Caught gracefully; error returned to LLM as tool result
   - LLM explains error to user; agent may loop or stop
   - If persistent, eventually hits MAX_ITERATIONS

## Error Handling

| Scenario | Behavior |
|---|---|
| Product not found | Tool returns `{error, message}` → LLM tells user |
| qty ≤ 0 | Tool returns validation error |
| Out of stock | `available=false` → LLM skips price_order |
| Unknown PIN | Controlled unavailable response |
| Tool exception | Caught, returns safe error dict |

## Why an Agent?

A single LLM prompt cannot:
- Query live JSON files dynamically
- Chain multiple dependent lookups (stock → price → delivery)
- Maintain order state across conversation turns
- Apply deterministic business rules (Python does the math)

The agent pattern solves all of these by separating: LLM reasoning, tool execution, and state management.
