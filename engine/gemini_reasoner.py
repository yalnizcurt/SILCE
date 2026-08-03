"""
SILCE AI-Native Reasoning Engine (Gemini 2.5 Flash / Groq AI)
=============================================================
Performs live AI context reasoning over deterministic rule engine guardrails.

Target Architecture:
  Checkout Session
       ↓
  Rule Engine Guardrails (Filters eligible categories & candidate products)
       ↓
  AI Reasoning Engine (Infers mission, selects category, selects SKU, generates explanation)
       ↓
  Structured JSON Output
       ↓
  Recommendation Card / UI

Fallback: If API key is missing or network times out, seamlessly falls back to
the deterministic rule engine.
"""

import os
import json
import ssl
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

logger = logging.getLogger("SILCE.AIReasoner")


def _get_api_credentials() -> Tuple[str, str, str]:
    """Retrieve API key, base URL, and model from config or environment."""
    try:
        import config
        key = getattr(config, "LLM_API_KEY", "") or getattr(config, "GROQ_API_KEY", "") or getattr(config, "GEMINI_API_KEY", "")
        base_url = getattr(config, "LLM_BASE_URL", "https://api.groq.com/openai/v1")
        model = getattr(config, "LLM_MODEL", "llama-3.3-70b-versatile")
    except ImportError:
        key = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    return key.strip(), base_url.strip(), model.strip()


def query_gemini_reasoner(
    cart_items: List[Dict[str, Any]],
    purchased_taxonomy_cats: List[str],
    eligible_categories: List[str],
    candidate_products: List[Dict[str, Any]],
    max_allowed_price: float,
) -> Optional[Dict[str, Any]]:
    """
    Executes AI-native reasoning over deterministic guardrail candidates.

    Returns structured JSON dict if successful:
    {
        "mission": str,
        "selected_category": str,
        "representative_product_id": str,
        "product_justification": str,
        "explanation": str,
        "confidence": float,
        "engine": "gemini-2.5-flash"
    }

    Returns None on failure or missing API key to trigger deterministic fallback.
    """
    api_key, base_url, model = _get_api_credentials()
    if not api_key:
        logger.info("No API key found. Using deterministic reasoning fallback.")
        return None

    # Format cart items for prompt
    basket_summary = [
        {"name": item.get("name"), "qty": item.get("qty", 1), "price": f"₹{item.get('price')}"}
        for item in cart_items
    ]

    # Format candidates for prompt
    candidate_summary = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "category": p.get("silce_category", p.get("category")),
            "price": f"₹{p.get('price')}",
            "brand": p.get("brand", ""),
            "rating": p.get("rating", "4.7"),
        }
        for p in candidate_products
    ]

    system_instruction = (
        "You are a calm, minimal, human quick-commerce shopping companion (like Apple Intelligence).\n"
        "Your role is to understand the customer's intent and offer ONE thoughtful suggestion.\n"
        "FORBIDDEN WORDS: Do NOT use technical/algorithmic words ('category', 'AI', 'selected', 'closest', 'adjacent', 'fits your basket', 'opportunity', 'popular', 'trending').\n\n"
        "Return ONLY a valid JSON object with NO markdown formatting, NO extra text:\n"
        "{\n"
        '  "mission": "<Inferred Shopping Mission: Weekly Household Refill | Personal Care & Comfort | Celebration / Party | Interview Preparation>",\n'
        '  "observation": "<Calm human observation, e.g. Looks like you\'re restocking the house. | Taking care of yourself today? | Looks like you\'re getting ready for an evening out. | Big day ahead?>",\n'
        '  "suggestion": "<1 short, warm, human suggestion. E.g. If you have a pet at home, this is something that\'s easy to forget during grocery runs. | A small comfort item can make the day a little easier. | You may appreciate having this tomorrow. | A polished look is often in the little details.>",\n'
        '  "selected_category": "<EXACT category name chosen from ELIGIBLE_CATEGORIES>",\n'
        '  "representative_product_id": "<EXACT product id chosen from CANDIDATE_PRODUCTS for selected_category>",\n'
        '  "product_justification": "<1 sentence why this product represents the category>",\n'
        '  "explanation": "<Same content as suggestion>",\n'
        '  "confidence": <float between 0.85 and 0.98>\n'
        "}"
    )

    user_prompt = f"""ANALYSIS INPUT:
- Current Basket: {json.dumps(basket_summary)}
- User Purchased Categories (Explored/Excluded): {json.dumps(list(purchased_taxonomy_cats))}
- Eligible Unexplored Adjacent Categories: {json.dumps(eligible_categories)}
- Candidate Representative Products: {json.dumps(candidate_summary)}
- Price Cap: ₹{max_allowed_price}

Task: Perform reasoning to infer mission, select 1 adjacent category, select 1 representative product ID, and generate 1 conversational explanation sentence."""

    # SSL Context helper for macOS compatibility
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # 1. Try OpenAI-compatible API (Groq / OpenAI)
    if "groq.com" in base_url or "openai.com" in base_url or api_key.startswith("gsk_") or api_key.startswith("sk-"):
        url = f"{base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 400,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, context=ctx, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                result = json.loads(content)

                selected_cat = result.get("selected_category")
                prod_id = result.get("representative_product_id")
                valid_prod_ids = {p["id"] for p in candidate_products}

                if selected_cat in eligible_categories and prod_id in valid_prod_ids:
                    result["engine"] = f"{model} (Groq AI)"
                    result["confidence"] = float(result.get("confidence", 0.94))
                    logger.info(f"AI Reasoning succeeded via {model}: {result['mission']} -> {selected_cat} ({prod_id})")
                    return result
        except Exception as e:
            logger.warning(f"Groq API error ({e}). Trying Gemini REST endpoint...")

    # 2. Try native Gemini REST API if Gemini key or fallback
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": system_instruction + "\n\n" + user_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2, "maxOutputTokens": 400},
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=3.5) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            candidates = resp_data.get("candidates", [])
            if candidates:
                text = candidates[0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()
                result = json.loads(text)
                selected_cat = result.get("selected_category")
                prod_id = result.get("representative_product_id")
                valid_prod_ids = {p["id"] for p in candidate_products}
                if selected_cat in eligible_categories and prod_id in valid_prod_ids:
                    result["engine"] = "gemini-2.5-flash"
                    result["confidence"] = float(result.get("confidence", 0.94))
                    return result
    except Exception as e:
        logger.warning(f"Gemini REST API call failed ({e}). Using deterministic engine fallback.")

    return None
