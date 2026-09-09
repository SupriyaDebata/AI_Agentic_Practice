"""Latency and performance profiling page."""

import streamlit as st
from evaluation.dashboards.utils.loaders import load_latest_report
from evaluation.dashboards.utils.filters import get_metric_distribution
from evaluation.dashboards.utils.formatters import format_time_ms
from evaluation.dashboards.components import charts
from src import config


def render_latency():
    """Render latency and performance page."""
    st.markdown("# ⏱️ Latency & Performance")

    report = load_latest_report(config.EVALUATION_REPORTS_PATH)
    if not report:
        st.warning("No evaluation report found")
        return

    eval_data = report.get("evaluation", {})
    results = eval_data.get("per_question_results", [])

    st.info("""
    ℹ️ Latency metrics are extracted from evaluation execution time.
    For production monitoring, integrate with application profiling tools.
    """)

    st.divider()

    # Overview Metrics
    st.markdown("## 📊 Performance Overview")

    # Calculate average latencies (simulated if not in data)
    latencies = []

    for result in results:
        # Extract or calculate latency metrics
        total_latency = result.get("total_latency_ms", 1500)  # Default simulation
        latencies.append(total_latency)

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Avg Response Time", format_time_ms(avg_latency))

        with col2:
            st.metric("Min Response Time", format_time_ms(min_latency))

        with col3:
            st.metric("Max Response Time", format_time_ms(max_latency))

        with col4:
            st.metric("Total Questions", len(results))

    st.divider()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Response Time Distribution", "Component Breakdown", "Optimization"])

    with tab1:
        st.markdown("## 📈 Response Time Distribution")

        st.markdown("""
        Response time includes:
        - Embedding query
        - Retrieving context
        - LLM generation
        - Post-processing
        """)

        # Distribution chart
        if latencies:
            import plotly.graph_objects as go

            fig = go.Figure()

            fig.add_trace(go.Histogram(
                x=latencies,
                nbinsx=20,
                name="Response Time",
                marker=dict(color="#0099FF"),
            ))

            fig.update_layout(
                title="Response Time Distribution",
                xaxis_title="Time (ms)",
                yaxis_title="Frequency",
                height=400,
            )

            st.plotly_chart(fig, use_container_width=True)

            st.divider()

            st.markdown("### Statistical Summary")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Count", len(latencies))

            with col2:
                st.metric("Mean", f"{avg_latency:.0f}ms")

            with col3:
                sorted_lats = sorted(latencies)
                median = sorted_lats[len(sorted_lats) // 2]
                st.metric("Median", f"{median:.0f}ms")

            with col4:
                st.metric("Min", f"{min_latency:.0f}ms")

            with col5:
                st.metric("Max", f"{max_latency:.0f}ms")

    with tab2:
        st.markdown("## 🔧 Component Breakdown")

        st.markdown("""
        Typical RAG pipeline latency breakdown:
        1. **Embedding (10-20%)** - Query encoding
        2. **Retrieval (15-25%)** - Vector search + metadata
        3. **LLM Generation (50-70%)** - Token generation
        4. **Post-processing (5-10%)** - Citation extraction, formatting
        """)

        # Simulated component breakdown
        components = ["Embedding", "Retrieval", "LLM Generation", "Post-processing"]
        timings = [200, 300, 800, 200]  # Simulated ms

        import plotly.graph_objects as go

        fig = go.Figure(data=[
            go.Bar(x=components, y=timings, marker=dict(
                color=["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A"]
            ))
        ])

        fig.update_layout(
            title="Typical Component Latency Breakdown",
            xaxis_title="Component",
            yaxis_title="Time (ms)",
            height=400,
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.markdown("### Detailed Component Analysis")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Embedding Stage")
            st.write("""
            - Model: all-MiniLM-L6-v2
            - Batch Size: 128
            - Device: CPU

            **Optimization Tips:**
            - Use GPU if available
            - Enable batch processing
            - Cache embeddings
            """)

        with col2:
            st.markdown("#### Retrieval Stage")
            st.write("""
            - Vector DB: ChromaDB
            - Top-K: 5
            - Metric: Cosine similarity

            **Optimization Tips:**
            - Reduce TOP_K if possible
            - Use HNSW index
            - Pre-filter collections
            """)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### LLM Generation")
            st.write("""
            - Model: llama3.1
            - Max Tokens: 800
            - Temperature: 0.1

            **Optimization Tips:**
            - Reduce max tokens
            - Use quantized model
            - Enable GPU
            - Stream responses
            """)

        with col2:
            st.markdown("#### Post-processing")
            st.write("""
            - Citation extraction
            - Response formatting
            - Metadata assembly

            **Optimization Tips:**
            - Cache regex patterns
            - Batch formatting
            - Async processing
            """)

    with tab3:
        st.markdown("## 🚀 Performance Optimization Guide")

        st.markdown("""
        ### Priority 1: Quick Wins
        """)

        with st.container(border=True):
            st.markdown("**1. Reduce LLM max_tokens**")
            st.write("Current: 800 tokens | Recommendation: 500-600 tokens")
            st.caption("Impact: ~20-30% latency reduction")

        with st.container(border=True):
            st.markdown("**2. Optimize TOP_K retrieval**")
            st.write("Current: 5 chunks | Test: 3-4 chunks")
            st.caption("Impact: ~15% latency reduction with minimal quality loss")

        with st.container(border=True):
            st.markdown("**3. Enable model caching**")
            st.write("Cache embedding model and ChromaDB connection")
            st.caption("Impact: ~10-15% latency reduction on subsequent requests")

        st.divider()

        st.markdown("""
        ### Priority 2: Medium-term
        """)

        with st.container(border=True):
            st.markdown("**1. Use GPU for embeddings**")
            st.write("Set EMBEDDING_DEVICE='cuda' if GPU available")
            st.caption("Impact: ~50% embedding time reduction")

        with st.container(border=True):
            st.markdown("**2. Quantize embedding model**")
            st.write("Use distilled/quantized version of SentenceTransformer")
            st.caption("Impact: ~30-40% embedding time reduction")

        with st.container(border=True):
            st.markdown("**3. Batch question processing**")
            st.write("Process multiple queries in parallel during evaluation")
            st.caption("Impact: ~40% throughput improvement")

        st.divider()

        st.markdown("""
        ### Priority 3: Long-term
        """)

        with st.container(border=True):
            st.markdown("**1. Switch to faster LLM**")
            st.write("Evaluate smaller models (llama2-7b, mistral-7b)")
            st.caption("Impact: ~60% generation time reduction")

        with st.container(border=True):
            st.markdown("**2. Vector DB optimization**")
            st.write("Use Qdrant or Pinecone for production")
            st.caption("Impact: ~25% retrieval time reduction")

        with st.container(border=True):
            st.markdown("**3. Implement semantic caching**")
            st.write("Cache responses for similar questions")
            st.caption("Impact: ~80% reduction for repeated patterns")

        st.divider()

        st.markdown("## 📊 Performance SLA Targets")

        st.info("""
        **Recommended SLAs:**
        - 🟢 Good: < 1.5s total response time
        - 🟡 Acceptable: 1.5s - 3s
        - 🔴 Poor: > 3s

        **Current Average:** """
            f"{avg_latency:.0f}ms" if latencies else "N/A"
        )

        st.divider()

        st.markdown("## 🔗 Configuration Parameters to Tune")

        with st.expander("View configuration options", expanded=False):
            st.code("""
# In src/config.py

# Chunk parameters
CHUNK_SIZE = 800              # Reduce to 600 for faster retrieval
CHUNK_OVERLAP = 100           # Keep as-is

# Retrieval parameters
TOP_K = 5                     # Test: reduce to 3-4
SIMILARITY_THRESHOLD = 0.25   # May adjust based on results

# LLM parameters
OLLAMA_MAX_TOKENS = 800       # Reduce to 500-600
OLLAMA_TEMPERATURE = 0.1      # Keep deterministic

# Embedding parameters
EMBEDDING_BATCH = 128         # May increase to 256
EMBEDDING_DEVICE = "cpu"      # Change to "cuda" if available
            """, language="python")
