"""
ui/components/chat.py

Chat interface component for the Streamlit app.

Manages:
- Message display (user and assistant)
- Chat input
- Conversation history state
- Message formatting
"""
from typing import Optional, Dict, Any
import streamlit as st
from app.config import get_logger

logger = get_logger(__name__)


class ChatInterface:
    """Handles chat display and user input."""

    @staticmethod
    def display_conversation_history() -> None:
        """Display all messages in the conversation history."""
        for i, message in enumerate(st.session_state.conversation_history):
            role = message.get("role", "user")
            content = message.get("content", "")
            metadata = message.get("metadata", {})

            if role == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(content)

            elif role == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content)

    @staticmethod
    def get_user_input() -> str:
        """Get user input from the chat input field."""
        user_input = st.chat_input(
            placeholder="What kids' clothing are you looking for? (e.g., 'white dress for 7-8 years')",
            key="chat_input",
        )
        return user_input or ""

    @staticmethod
    def add_message(
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a message to conversation history.

        Args:
            role: "user" or "assistant"
            content: The message text
            metadata: Optional debug information (intent, scores, etc.)
        """
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        st.session_state.conversation_history.append(message)
        logger.info("message added", role=role, has_metadata=bool(metadata))

    @staticmethod
    def display_products(
        products: list,
        title: str = "🛍️ Results",
    ) -> None:
        """
        Display a list of products in a grid layout.

        Args:
            products: List of product dictionaries
            title: Section title
        """
        if not products:
            st.warning("No products found matching your criteria.")
            return

        st.subheader(title)

        # Display as columns for responsive grid
        cols = st.columns(min(3, len(products)))

        for idx, product in enumerate(products):
            col = cols[idx % len(cols)]

            with col:
                ChatInterface._display_product_card(product)

    @staticmethod
    def _display_product_card(product: Dict[str, Any]) -> None:
        """
        Display a single product card.

        Args:
            product: Product dictionary from retriever
        """
        with st.container(border=True):
            # Product name
            st.markdown(f"### {product.get('product_name', 'Product')}")

            # Key details
            price = product.get("price", "N/A")
            stock_status = "✅ In Stock" if product.get("stock", False) else "❌ Out of Stock"
            st.markdown(f"**₹{price}** | {stock_status}")

            # Description
            description = product.get("description", "No description available")
            st.caption(description)

            # Details grid
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Age:** {product.get('kids_age', '—')}")
            with col2:
                st.markdown(f"**Colour:** {product.get('colour', '—')}")
            with col3:
                st.markdown(f"**Size:** {product.get('size', '—')}")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Gender:** {product.get('gender', '—')}")
            with col2:
                st.markdown(f"**Brand:** {product.get('brand', '—')}")

            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🛒 Add to Cart", key=f"cart_{product.get('id')}", use_container_width=True):
                    st.success(f"Added {product.get('product_name')} to cart!")

            with col2:
                if st.button("❤️ Save", key=f"save_{product.get('id')}", use_container_width=True):
                    st.success(f"Saved {product.get('product_name')}!")

    @staticmethod
    def display_search_intent(intent: Dict[str, Any]) -> None:
        """
        Display the parsed search intent (debug view).

        Args:
            intent: SearchIntent model as dict
        """
        if not intent:
            return

        with st.expander("🔍 How I understood your query", expanded=True):
            # Create two columns for better layout
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Structured Filters:**")
                structured = {
                    k: v for k, v in intent.items()
                    if v and k != "semantic_query" and k != "original_query"
                }
                if structured:
                    for key, value in structured.items():
                        st.markdown(f"- `{key}`: {value}")
                else:
                    st.caption("(none)")

            with col2:
                st.markdown("**Semantic Intent:**")
                semantic = intent.get("semantic_query", "")
                if semantic:
                    st.markdown(f"`{semantic}`")
                else:
                    st.caption("(none)")

    @staticmethod
    def display_retrieval_info(info: Dict[str, Any]) -> None:
        """
        Display retrieval strategy and statistics.

        Args:
            info: Retrieval metadata dict
        """
        if not info:
            return

        with st.expander("🎯 Retrieval Strategy", expanded=False):
            st.markdown(f"**Strategy**: {info.get('strategy', 'Unknown')}")
            st.markdown(f"**Retrieved**: {info.get('retrieved_count', 0)} candidates")
            st.markdown(f"**Reranked**: {info.get('reranked_count', 0)} results")

            if "latency_ms" in info:
                st.markdown(f"**Latency**: {info['latency_ms']:.0f}ms")

            if "details" in info:
                st.json(info["details"])
