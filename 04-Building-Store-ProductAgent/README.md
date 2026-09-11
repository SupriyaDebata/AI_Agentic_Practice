# Store Assistant Agent

A simple educational agent demonstrating Week 4 "Building Agents" concepts.  
Runs **fully locally** using [Ollama](https://ollama.com) — no API key required.

## Prerequisites

1. Install [Ollama](https://ollama.com/download) and pull a tool-calling model:
   ```bash
   ollama pull llama3.1
   ```
   Other supported models: `llama3.2`, `mistral`, `qwen2.5`

2. Make sure Ollama is running:
   ```bash
   ollama serve
   ```

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Copy `.env.example` to `.env` to change the model:
   ```bash
   copy .env.example .env
   # Edit OLLAMA_MODEL=llama3.1 if you want a different model
   ```

3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Example Requests

- "I want 3 cotton t-shirts, deliver to 700001. Total?"
- "Are denim jeans in stock?"
- "Add 2 slim fit jeans to my order."
- "What's the delivery time for PIN 560001?"
- "I need 5 baseball caps."

## Discount System

The agent automatically applies volume-based discounts when you meet the minimum quantity for a product category:

| Product | Min Qty | Discount |
|---------|---------|----------|
| T-Shirts | 3 | 10% |
| Jeans | 2 | 5% |
| Jackets | 2 | 8% |
| Shoes | 2 | 7% |
| Caps | 5 | 15% |

**Example Calculation (2 Casual Jackets):**
- Unit price: ₹2,499 × 2 = ₹4,998 (subtotal)
- Discount (8%): 4,998 × 8 ÷ 100 = ₹399.84
- Final price: ₹4,998 - ₹399.84 = **₹4,598.16**

## Why an Agent?

A plain LLM prompt cannot answer these questions reliably because:

- **Product data is dynamic** — prices, stock levels, and discounts live in JSON files, not in the prompt.
- **Multiple steps are required** — the agent must check stock, then price, then delivery, in order.
- **Business rules must be deterministic** — discounts and pricing are calculated by Python, never by the LLM.
- **State must persist** — the order accumulates across multiple conversation turns.
- **Graceful boundaries needed** — the agent must recognize out-of-scope requests and refuse clearly.

An agent solves this by deciding which tool to call, observing the result, updating state, and deciding the next step — all dynamically. It also tracks **stop reasons** to ensure every response is grounded in what actually happened.

## Project Structure

```
04-Building-Store-ProductAgent/
├── app.py              Streamlit UI
├── .env.example        Reference config (no secrets needed)
├── agent/
│   ├── agent.py        ReAct loop + tool dispatch (uses Ollama)
│   ├── state.py        AgentState dataclass
│   └── prompts.py      System prompt
├── tools/
│   ├── inventory.py    check_stock tool
│   ├── pricing.py      price_order tool
│   └── shipping.py     delivery_eta tool
├── data/
│   ├── inventory.json
│   ├── discounts.json
│   └── shipping.json
└── tests/
    └── test_agent.py
```
