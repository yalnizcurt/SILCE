import os

# ==========================================
# SILCE Engine Configuration & API Keys
# ==========================================

# Active LLM Key (Groq AI / Gemini API)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

LLM_API_KEY = (
    GROQ_API_KEY or 
    GEMINI_API_KEY or 
    OPENAI_API_KEY or 
    os.getenv("LLM_API_KEY") or 
    ""
)

# Active Endpoint & Model
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
