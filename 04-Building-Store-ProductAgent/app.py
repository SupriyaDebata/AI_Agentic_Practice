import streamlit as st

from agent.agent import run_agent
from agent.state import AgentState

st.set_page_config(page_title="Store Assistant", page_icon="🛍️", layout="wide")

# ── Session state initialisation ──────────────────────────────────────────────
if "agent_state" not in st.session_state:
    st.session_state.agent_state = AgentState()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of (role, text)
if "last_trace" not in st.session_state:
    st.session_state.last_trace = []

# ── Layout ────────────────────────────────────────────────────────────────────
st.title("🛍️ Store Assistant")
st.caption("Check stock, calculate prices and get delivery estimates.")

col_chat, col_side = st.columns([2, 1])

# ── Chat area ─────────────────────────────────────────────────────────────────
with col_chat:
    for role, text in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(text)

    user_input = st.chat_input("Ask about products, pricing, stock or delivery…")

    if user_input:
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(user_input)

        state = st.session_state.agent_state
        trace_before = len(state.trace)

        with st.chat_message("assistant"):
            with st.spinner(""):
                reply = run_agent(user_input, state)
            st.markdown(reply)

        st.session_state.last_trace = state.trace[trace_before:]
        st.session_state.chat_history.append(("assistant", reply))
        st.rerun()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with col_side:
    state = st.session_state.agent_state

    # Current Order card
    st.subheader("🧾 Current Order")
    if state.order_items:
        for item in state.order_items:
            cols = st.columns([3, 1])
            cols[0].write(f"**{item.product_name}** × {item.quantity}")
            cols[1].write(f"₹{item.final_price:,.0f}")
            if item.discount_percentage > 0:
                st.caption(
                    f"₹{item.unit_price} × {item.quantity}"
                    f" — {item.discount_percentage:.0f}% discount applied"
                )

        st.divider()
        st.markdown(f"### Total: ₹{state.order_total:,.2f}")

        if state.destination_pincode:
            st.caption(f"📦 Delivering to PIN: {state.destination_pincode}")

        if st.button("🗑️ Clear Order", use_container_width=True):
            st.session_state.agent_state = AgentState()
            st.session_state.chat_history = []
            st.session_state.last_trace = []
            st.rerun()
    else:
        st.caption("No items in your order yet.")

    st.divider()

    # Agent Trace — for learning/debugging, collapsed by default
    with st.expander("🔍 Agent Trace", expanded=False):
        if st.session_state.last_trace:
            for i, step in enumerate(st.session_state.last_trace):
                st.markdown(f"**Step {i + 1} — `{step['tool']}`**")

                inp = step["input"]
                res = step["result"]

                # Friendly input summary
                if step["tool"] == "check_stock":
                    st.caption(f"Checked: {inp.get('product_id')} × {inp.get('quantity')}")
                elif step["tool"] == "price_order":
                    st.caption(f"Priced: {inp.get('product_id')} × {inp.get('quantity')}")
                elif step["tool"] == "delivery_eta":
                    st.caption(f"PIN: {inp.get('pincode')}")

                # Friendly result summary
                if step["tool"] == "check_stock":
                    if res.get("available"):
                        st.success(
                            f"✅ {res.get('product_name')} — "
                            f"{res.get('available_quantity')} in stock"
                        )
                    else:
                        st.warning(
                            f"⚠️ {res.get('product_name', inp.get('product_id'))} — "
                            f"{res.get('message', 'unavailable')}"
                        )

                elif step["tool"] == "price_order":
                    if not res.get("error"):
                        disc = res.get("discount_percentage", 0)
                        disc_note = f" ({disc:.0f}% off)" if disc else ""
                        st.success(
                            f"₹{res.get('final_price'):,.2f}{disc_note}"
                        )
                    else:
                        st.error(res.get("message"))

                elif step["tool"] == "delivery_eta":
                    if res.get("available", True) and not res.get("error"):
                        st.success(
                            f"🚚 {res.get('estimated_delivery_days')} day(s) delivery"
                        )
                    else:
                        st.warning(res.get("message", "Delivery unavailable"))

                if i < len(st.session_state.last_trace) - 1:
                    st.markdown("↓")
        else:
            st.caption("No tool calls were made for the last message.")
