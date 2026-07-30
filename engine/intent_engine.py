import os
import json
import logging
from typing import List, Dict, Any, Tuple
import config

logger = logging.getLogger("SILCE.IntentEngine")

KNOWN_INTENTS = {
    "Movie Night": {
        "keywords": ["nachos", "coke", "coca-cola", "chips", "popcorn", "soda", "ice cream", "dark chocolate", "snack"],
        "min_matches": 1,
        "nudge_templates": [
            "Complete your movie night setup with {product_name}!",
            "Elevate your binge watch experience with {product_name}.",
            "Perfect addition to your movie night basket!"
        ]
    },
    "Chai Time": {
        "keywords": ["tea", "chai", "masala tea", "biscuits", "parle-g", "rusk", "cookies", "milk"],
        "min_matches": 1,
        "nudge_templates": [
            "Pair your evening chai with {product_name}.",
            "Enhance your tea break with {product_name}.",
            "A cozy companion for your chai session!"
        ]
    },
    "Breakfast Meal Prep": {
        "keywords": ["milk", "butter", "bread", "eggs", "cheese", "oats", "cereal"],
        "min_matches": 1,
        "nudge_templates": [
            "Make your morning routine seamless with {product_name}.",
            "Great addition to your breakfast table: {product_name}.",
            "Upgrade your morning routine!"
        ]
    },
    "Late Night Gaming": {
        "keywords": ["nachos", "coke", "energy drink", "earphones", "chips", "chocolate"],
        "min_matches": 1,
        "nudge_templates": [
            "Level up your gaming session with {product_name}.",
            "Fuel your late-night session with {product_name}!"
        ]
    },
    "Sunday Cleaning": {
        "keywords": ["dishwash", "cleaning", "detergent", "sponge", "cleaner", "vim"],
        "min_matches": 1,
        "nudge_templates": [
            "Make house cleaning effortless with {product_name}.",
            "Handy tool for your cleaning routine: {product_name}."
        ]
    },
    "Pet Care Routine": {
        "keywords": ["dog food", "cat food", "pet", "lint roller", "pedigree", "whiskas"],
        "min_matches": 1,
        "nudge_templates": [
            "Care for your pet hassle-free with {product_name}.",
            "Your furry friend will love this addition: {product_name}!"
        ]
    }
}

def analyze_cart_intent_llm(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    """
    Uses an LLM API (Groq/Gemini/OpenAI) to dynamically infer life context from cart items.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
        
        item_names = [i.get("name") for i in cart_items]
        prompt = f"""Analyze these quick-commerce cart items: {json.dumps(item_names)}.
Infer the user's primary life context intent (e.g., 'Movie Night', 'Chai Time', 'Breakfast Meal Prep', 'Sunday Cleaning', 'Late Night Gaming', 'Pet Care Routine').
Return JSON:
{{
  "intent": "<intent_name>",
  "confidence": <float between 0.70 and 0.98 reflecting strength of evidence based on item count>,
  "matched_keywords": [<list of key items/tags>]
}}"""

        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        res_text = response.choices[0].message.content
        data = json.loads(res_text)
        
        raw_conf = float(data.get("confidence", 0.80))
        # Dynamically scale confidence based on basket size for realistic precision
        item_count = len(cart_items)
        if item_count >= 3:
            dynamic_conf = max(raw_conf, min(0.96, 0.88 + (item_count * 0.03)))
        elif item_count == 2:
            dynamic_conf = min(0.90, max(0.82, raw_conf))
        else:
            dynamic_conf = min(0.78, raw_conf)

        logger.info(f"✨ LLM API Inferred Intent: {data.get('intent')} (Confidence: {dynamic_conf:.2f})")
        return data.get("intent", "General Shopping Mission"), round(dynamic_conf, 2), data.get("matched_keywords", item_names)
    except Exception as e:
        logger.warning(f"LLM API call failed ({e}), falling back to embedded semantic engine.")
        return analyze_cart_intent_semantic(cart_items)

def analyze_cart_intent_semantic(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    """
    Embedded rule-based & keyword semantic reasoner (Zero-latency fallback).
    """
    if not cart_items:
        return "General Household", 0.0, []

    item_text_tokens = []
    for item in cart_items:
        name = item.get("name", "").lower()
        tags = [t.lower() for t in item.get("tags", [])]
        item_text_tokens.extend(name.split())
        item_text_tokens.extend(tags)
    
    full_text = " ".join(item_text_tokens)

    best_intent = "General Shopping Mission"
    max_score = 0.0
    best_matches = []

    for intent, config_item in KNOWN_INTENTS.items():
        matched = []
        for kw in config_item["keywords"]:
            if kw.lower() in full_text:
                matched.append(kw)
        
        if len(matched) >= config_item["min_matches"]:
            score = min(0.95, 0.65 + (len(matched) * 0.12))
            if score > max_score:
                max_score = score
                best_intent = intent
                best_matches = matched

    if max_score == 0.0:
        best_intent = "Daily Essentials"
        max_score = 0.60
        best_matches = ["grocery"]

    logger.info(f"Embedded Intent Engine: '{best_intent}' (Score: {max_score:.2f}, Matches: {best_matches})")
    return best_intent, max_score, best_matches

def analyze_cart_intent(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    """
    Main entry point: Uses LLM API if config.LLM_API_KEY is available, else uses Embedded Semantic Engine.
    """
    if config.LLM_API_KEY:
        return analyze_cart_intent_llm(cart_items)
    return analyze_cart_intent_semantic(cart_items)


