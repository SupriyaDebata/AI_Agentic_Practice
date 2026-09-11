import os
from dotenv import load_dotenv

load_dotenv()

# Ollama model — must support tool/function calling
# Recommended options: llama3.1, llama3.2, mistral, qwen2.5
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")

# Ollama server host (change if Ollama runs on a remote machine)
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Agent safety limit — prevents infinite tool-call loops
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
