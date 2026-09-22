import os
from dotenv import load_dotenv

load_dotenv()

# Ollama model — must support tool/function calling
# FAST MODELS: mistral (12B, fastest), neural-chat (7B, very fast), qwen2.5:7b (fast)
# SLOWER: llama3.1 (8B, slower), llama3.2 (11B/90B, slowest)
# Recommendation: Use "mistral" or "neural-chat" for <30 second responses
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")

# Ollama server host (change if Ollama runs on a remote machine)
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Agent safety limit — prevents infinite tool-call loops
# Reduced from 5 to 3 for faster failure (typical query needs only 1-3 steps)
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))
