import os
import json
import logging
from typing import List, Dict, Any, Tuple
import config

logger = logging.getLogger("SILCE.IntentEngine")

KNOWN_INTENTS = {
    "Weekly Grocery Refill": {
        "keywords": ["milk", "cucumber", "rice", "atta", "essential", "staples"],
        "min_matches": 1,
        "nudge_templates": [
            "Because you're restocking weekly essentials<br><span style=\"font-size: 11px; color: #64748B;\">Frequently paired with milk by similar shoppers.</span>"
        ]
    },
    "Morning Breakfast Run": {
        "keywords": ["bread", "eggs", "butter", "breakfast", "milk", "tea"],
        "min_matches": 1,
        "nudge_templates": [
            "Complete your morning breakfast prep<br><span style=\"font-size: 11px; color: #64748B;\">Frequently paired with bread and milk.</span>"
        ]
    },
    "Fresh Produce Restock": {
        "keywords": ["tomato", "cucumber", "onion", "spinach", "vegetables", "produce"],
        "min_matches": 1,
        "nudge_templates": [
            "Pair fresh salad veggies with refreshing curd<br><span style=\"font-size: 11px; color: #64748B;\">Frequently purchased together.</span>"
        ]
    },
    "House Party": {
        "keywords": ["coke", "soft drink", "chips", "ice cream", "salsa", "party"],
        "min_matches": 1,
        "nudge_templates": [
            "Complete your house party essentials<br><span style=\"font-size: 11px; color: #64748B;\">Great additions to your party basket.</span>"
        ]
    },
    "Smoke Break": {
        "keywords": ["cigarettes", "smoke", "mint", "lighter"],
        "min_matches": 1,
        "nudge_templates": [
            "Pair your smoke break essentials<br><span style=\"font-size: 11px; color: #64748B;\">Convenient additions for quick breaks.</span>"
        ]
    },
    "Office Essentials": {
        "keywords": ["coffee", "biscuits", "noodles", "maggi", "cups", "office"],
        "min_matches": 1,
        "nudge_templates": [
            "Restock your office pantry essentials<br><span style=\"font-size: 11px; color: #64748B;\">Keep the workspace fully loaded.</span>"
        ]
    },
    "Sick Day Recovery": {
        "keywords": ["crocin", "ors", "thermometer", "pain relief", "meds"],
        "min_matches": 1,
        "nudge_templates": [
            "Comfort for your sick day recovery<br><span style=\"font-size: 11px; color: #64748B;\">Urgent health essentials for quick recovery.</span>"
        ]
    },
    "Urgent Household Need": {
        "keywords": ["garbage bags", "floor cleaner", "dishwash", "cleaning", "lizol"],
        "min_matches": 1,
        "nudge_templates": [
            "Solve your urgent household needs<br><span style=\"font-size: 11px; color: #64748B;\">Staples for keeping the house clean.</span>"
        ]
    }
}

def analyze_cart_intent_llm(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    """Uses LLM API to dynamically infer life context from cart items."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
        
        item_names = [i.get("name") for i in cart_items]
        prompt = f"""Analyze these quick-commerce cart items: {json.dumps(item_names)}. 
Infer the primary life context intent (e.g., 'Weekly Grocery Refill', 'Morning Breakfast Run', 'Daily Veggies & Dairy'). 
Return JSON:
{{
  "intent": "<intent_name>",
  "confidence": <float between 0.75 and 0.98>,
  "matched_keywords": [<list of key items/tags>]
}}"""
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        raw_conf = float(data.get("confidence", 0.85))
        return data.get("intent", "Weekly Grocery Refill"), round(raw_conf, 2), data.get("matched_keywords", item_names)
    except Exception as e:
        logger.warning(f"LLM API call failed ({e}), falling back to embedded semantic engine.")
        return analyze_cart_intent_semantic(cart_items)

def analyze_cart_intent_semantic(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    """Embedded rule-based & keyword semantic reasoner (Zero-latency fallback)."""
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
        matched = [kw for kw in config_item["keywords"] if kw.lower() in full_text]
        if len(matched) >= config_item["min_matches"]:
            score = min(0.95, 0.70 + (len(matched) * 0.12))
            if score > max_score:
                max_score = score
                best_intent = intent
                best_matches = matched

    if max_score == 0.0:
        best_intent = "Weekly Grocery Refill"
        max_score = 0.93
        best_matches = ["grocery"]

    logger.info(f"Embedded Intent Engine: '{best_intent}' (Score: {max_score:.2f}, Matches: {best_matches})")
    return best_intent, max_score, best_matches

def analyze_cart_intent(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    if config.LLM_API_KEY:
        return analyze_cart_intent_llm(cart_items)
    return analyze_cart_intent_semantic(cart_items)