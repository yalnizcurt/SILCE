import os

# ==========================================
# SILCE Engine Configuration & API Keys
# ==========================================

# Option 1: Load API keys from environment variables (e.g. Groq, Gemini, or OpenAI)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Option 2: Resolved API key from variable or environment
LLM_API_KEY = (
    GROQ_API_KEY or 
    GEMINI_API_KEY or 
    OPENAI_API_KEY or 
    os.getenv("GROQ_API_KEY") or 
    os.getenv("GEMINI_API_KEY") or 
    os.getenv("OPENAI_API_KEY") or 
    os.getenv("LLM_API_KEY") or 
    ""
)

# LLM Endpoint & Model Selection
# For Groq: https://api.groq.com/openai/v1 (Model: llama-3.1-8b-instant or llama-3.3-70b-versatile)
# For OpenAI: https://api.openai.com/v1 (Model: gpt-4o-mini)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
