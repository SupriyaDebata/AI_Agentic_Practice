"""
app.py — Invoice Field Extractor (Simplified)
Fast, lean Streamlit app for invoice extraction.
"""

import json, time, os, traceback
import streamlit as st
from dotenv import load_dotenv
from extractor import extract
from document_processor import extract_text

load_dotenv()

st.set_page_config(page_title="Invoice Extractor", page_icon="🧾", layout="wide")

PROVIDER_MAP = {
    "Ollama": "ollama",
    "Gemini": "gemini",
    "Claude": "claude",
    "OpenAI": "openai",
}

FIELDS = ["invoice_number", "invoice_date", "vendor", "bill_to",
          "subtotal", "tax", "total", "payment_terms", "currency"]


@st.cache_resource
def _check_ollama():
    """Check Ollama connection once per session."""
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except:
        return False


ollama_ok = _check_ollama()


def _normalize_confidence(clean: dict, raw_conf) -> dict:
    """Ensure invalid/absent fields are null."""
    if not isinstance(raw_conf, dict):
        raw_conf = {}
    conf = {k: v for k, v in raw_conf.items()
            if isinstance(k, str) and isinstance(v, str) and v in ("absent", "invalid", "low", "conflicted")}
    for field, label in conf.items():
        if label in ("invalid", "absent") and clean.get(field) is not None:
            clean[field] = None
    for f in FIELDS:
        if clean.get(f) is None and f not in conf:
            conf[f] = "absent"
    return conf


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
# Initialize sidebar state once
if "sidebar_provider" not in st.session_state:
    st.session_state.sidebar_provider = "Ollama"
if "sidebar_model" not in st.session_state:
    st.session_state.sidebar_model = "llama3.1"
if "sidebar_api_key" not in st.session_state:
    st.session_state.sidebar_api_key = None

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    provider = st.selectbox("LLM Provider", list(PROVIDER_MAP.keys()), 
                            key="provider_select")
    provider_code = PROVIDER_MAP[provider]

    api_key = None
    model = None
    ready = False

    if provider == "Ollama":
        model = st.selectbox("Model", ["llama3.1", "llama3.2", "mistral"], key="model_select_ollama")
        if ollama_ok:
            st.success("🟢 Ollama connected")
            ready = True
        else:
            st.error("🔴 Ollama offline\nRun: ollama serve")
    
    elif provider == "Gemini":
        model = st.selectbox("Model", ["gemini-2.0-flash", "gemini-1.5-pro"], key="model_select_gemini")
        api_key = os.getenv("GEMINI_API_KEY", "").strip() or st.text_input("API Key", type="password", key="key_gemini")
        ready = bool(api_key)
        if model == "gemini-2.0-flash":
            st.caption("⚡ Fastest cloud model (~5-10s)")
    
    elif provider == "Claude":
        model = st.selectbox("Model", ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"], key="model_select_claude")
        api_key = os.getenv("CLAUDE_API_KEY", "").strip() or st.text_input("API Key", type="password", key="key_claude")
        ready = bool(api_key)
    
    else:  # OpenAI
        model = st.selectbox("Model", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"], key="model_select_openai")
        api_key = os.getenv("OPENAI_API_KEY", "").strip() or st.text_input("API Key", type="password", key="key_openai")
        ready = bool(api_key)

    st.caption("Set API keys in .env or enter above")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
st.title("🧾 Invoice Extractor")
st.markdown("Upload invoice file → View content → Extract to JSON")

st.write("")
st.markdown("### 📂 Upload Invoice File")
st.caption("📄 Supported formats: PDF, JPEG, PNG, BMP, TIFF, TXT")
uploaded = st.file_uploader(
    "Choose an invoice file",
    type=["pdf", "jpg", "jpeg", "png", "bmp", "tiff", "gif", "txt"],
    key="file_uploader"
)

if uploaded:
    file_bytes = uploaded.read()
    
    # Extract text based on file type
    with st.spinner("📖 Extracting text from file..."):
        invoice_text = extract_text(file_bytes, uploaded.name)
    
    st.success(f"✅ File loaded: {uploaded.name}")
    
    st.write("")
    st.markdown("### 📄 Extracted Content")
    st.text_area("Content", value=invoice_text, height=250, disabled=True, key="display_area")
    
    st.write("")
    if st.button("⚡ Extract to JSON", type="primary", use_container_width=True, 
                 disabled=not ready):
        st.divider()
        
        # Real-time status updates
        status_container = st.container()
        result_container = st.container()
        
        try:
            with status_container:
                st.info("⏳ **Processing invoice…** Sending to LLM (may take 5-60 seconds depending on model)")
            
            t0 = time.time()
            result = extract(invoice_text, provider=provider_code, model=model, api_key=api_key)
            elapsed = time.time() - t0
            
            # Normalize
            clean = {f: result.get(f) for f in FIELDS}
            clean["_confidence"] = _normalize_confidence(clean, result.get("_confidence"))
            
            # Clear status and show result
            status_container.empty()
            
            with result_container:
                st.success(f"✅ **Done in {elapsed:.1f}s**")
                st.caption("💡 Tip: Re-uploading same file will use cache (instant!)")
                
                # Display
                col_json, col_download = st.columns([4, 1])
                with col_json:
                    st.json(clean)
                with col_download:
                    st.download_button(
                        "📥 Download",
                        json.dumps(clean, indent=2, ensure_ascii=False),
                        f"{uploaded.name.replace('.txt', '')}_extraction.json",
                        "application/json"
                    )
        
        except Exception as e:
            status_container.empty()
            with result_container:
                st.error(f"❌ Error: {str(e)}")
                with st.expander("Debug"):
                    st.code(traceback.format_exc())

else:
    st.info("👆 Upload an invoice file to begin")

