import os

# ==========================================
# Myntra StyleProof Configuration & Groq AI Key
# ==========================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

LLM_API_KEY = (
    os.getenv("GROQ_API_KEY") or
    GROQ_API_KEY or 
    os.getenv("OPENAI_API_KEY") or 
    os.getenv("LLM_API_KEY") or 
    ""
)

# Active Endpoint & Best Model on Groq (openai/gpt-oss-120b with 1.4s LPU inference)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
