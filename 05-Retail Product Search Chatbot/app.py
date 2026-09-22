"""
app.py  —  Retail Product Search Chatbot
Usage:  streamlit run app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from app.config import configure_logging, settings
from ui.components.sidebar import SidebarManager
from ui.pages.search import show_search_page

st.set_page_config(
    page_title="Kids Clothing Search",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded",
)

configure_logging()


def _init_session() -> None:
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.conversation_history = []
        st.session_state.current_filters = {
            "price_range": [0, 2000],
            "age_group": [],
            "gender": [],
            "colour": [],
            "category": [],
        }
        st.session_state.debug_mode = False
        st.session_state.last_search_intent = None
        st.session_state.last_retrieval_strategy = None
        st.session_state.ollama_model = settings.ollama_model


def main() -> None:
    _init_session()
    
    # Render sidebar using class-based approach
    with st.sidebar:
        sidebar = SidebarManager()
        sidebar.render()
    
    show_search_page()


if __name__ == "__main__":
    main()
