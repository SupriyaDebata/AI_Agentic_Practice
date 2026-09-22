import streamlit as st


@st.cache_data(show_spinner=False)
def _load_catalog():
    """Load all products once and cache for the session lifetime."""
    from app.repositories.sql_repository import SQLProductRepository
    return SQLProductRepository().get_all(top_k=500)


class SidebarManager:
    def render(self) -> None:
        st.title("👕 Kids Clothing")
        st.caption("Search & discover clothing for your kids")
        st.divider()

        tab_search, tab_catalog = st.tabs(["Search", "Catalog"])

        with tab_search:
            self._render_controls()

        with tab_catalog:
            self._render_catalog()

    def _render_controls(self) -> None:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.conversation_history = []
            st.rerun()
        st.caption(
            "Type any query. The system runs SQL + BM25 + ChromaDB vector search "
            "and merges results via RRF."
        )

    def _render_catalog(self) -> None:
        products = _load_catalog()
        if not products:
            st.warning("Catalog empty — run `python scripts/ingest.py` first.")
            return

        st.caption(f"{len(products)} products  ·  click any row to expand")

        for p in products:
            stock = "🟢" if p.stock else "🔴"
            with st.expander(
                f"{stock} [{p.id}] {p.product_name} — ₹{p.price}",
                expanded=False,
            ):
                st.caption(p.description)
                st.markdown(
                    f"**{p.category}** · {p.gender} · Age {p.kids_age} · "
                    f"{p.colour} · {p.brand}"
                )
