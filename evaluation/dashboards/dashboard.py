"""RAG Quality Gate Dashboard - Main Entry Point.

Run with: streamlit run evaluation/dashboards/dashboard.py
"""

import streamlit as st
from pathlib import Path
import sys
import plotly.express as px

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src import config

# Page configuration (must be first)
st.set_page_config(
    page_title="RAG Quality Gate",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1em;
    }
    .metric-card {
        padding: 20px;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"

# Sidebar Navigation
with st.sidebar:
    st.markdown("# 🎯 RAG Quality Gate")
    st.divider()

    st.markdown("## 📍 Navigation")

    # Main navigation buttons
    if st.button("🏠 Home", use_container_width=True, key="nav_home"):
        st.session_state.page = "home"

    if st.button("📈 Metrics", use_container_width=True, key="nav_metrics"):
        st.session_state.page = "metrics"

    if st.button("❓ Questions", use_container_width=True, key="nav_questions"):
        st.session_state.page = "questions"

    if st.button("🔎 Retrieval", use_container_width=True, key="nav_retrieval"):
        st.session_state.page = "retrieval"

    if st.button("🚨 Hallucinations", use_container_width=True, key="nav_hallucinations"):
        st.session_state.page = "hallucinations"

    if st.button("⏱️ Latency", use_container_width=True, key="nav_latency"):
        st.session_state.page = "latency"

    st.divider()

    # Configuration Info
    st.markdown("## ⚙️ Configuration")

    with st.expander("Quality Gate Thresholds", expanded=False):
        for metric, threshold in config.QUALITY_GATE_THRESHOLDS.items():
            st.metric(metric.replace("_", " ").title(), f"{threshold:.2f}")

    st.divider()

    # Help & Info
    st.markdown("## ℹ️ Help")

    with st.expander("About Quality Gate", expanded=False):
        st.markdown("""
        The RAG Quality Gate evaluates your document retrieval system on:

        - **Faithfulness** - No hallucinated facts
        - **Relevancy** - Answers address the question
        - **Precision** - Retrieved chunks are relevant
        - **Recall** - All needed info is retrieved
        - **Citations** - Facts are properly cited
        - **Refusal** - System refuses when answer absent

        All metrics must pass for **QUALITY GATE: PASS**
        """)

    with st.expander("Quick Start", expanded=False):
        st.markdown("""
        1. **Home** - View overall pass/fail status
        2. **Metrics** - Inspect each metric in detail
        3. **Questions** - Review per-question results
        4. **Retrieval** - Analyze search quality
        5. **Hallucinations** - Find false statements
        6. **Latency** - Profile performance

        💡 **Tip:** Start on Home, then dive into specific areas.
        """)

    with st.expander("Troubleshooting", expanded=False):
        st.markdown("""
        **No data showing?**
        - Run evaluation with `/batch` command
        - Check `evaluation/reports/` folder
        - Verify golden dataset loaded

        **Low metric scores?**
        - Check document quality
        - Review chunk size/overlap
        - Verify LLM prompt grounding
        - Test similarity threshold

        **Performance issues?**
        - See Latency page for optimization tips
        - Check if Ollama is running
        - Monitor system resources
        """)

    st.divider()

    # Footer
    st.caption("""
    RAG Quality Gate Dashboard
    Phase 4 Implementation
    """)

# Page routing (lazy import only when needed)
st.divider()

try:
    page = st.session_state.get("page", "home")

    if page == "home":
        from evaluation.dashboards.pages import home
        home.render_home()
    elif page == "metrics":
        from evaluation.dashboards.pages import metrics
        metrics.render_metrics()
    elif page == "questions":
        from evaluation.dashboards.pages import questions
        questions.render_questions()
    elif page == "retrieval":
        from evaluation.dashboards.pages import retrieval
        retrieval.render_retrieval()
    elif page == "hallucinations":
        from evaluation.dashboards.pages import hallucinations
        hallucinations.render_hallucinations()
    elif page == "latency":
        from evaluation.dashboards.pages import latency
        latency.render_latency()
    else:
        from evaluation.dashboards.pages import home
        home.render_home()

except Exception as e:
    # Better error handling: show exception type and message
    import traceback
    error_msg = f"{type(e).__name__}: {str(e)}"
    st.error(f"❌ Error rendering page: {error_msg}")
    
    with st.expander("Debug Traceback"):
        st.code(traceback.format_exc())
    
    st.divider()
    st.info("""
    **Troubleshooting:**
    - Ensure evaluation report exists in `evaluation/reports/`
    - Run evaluation with: `python -m evaluation.pipelines.batch_evaluate --split all`
    - Check that the report JSON is valid
    - Try refreshing the page (Ctrl+F5)
    """)
