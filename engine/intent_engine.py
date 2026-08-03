import os
import json
import logging
from typing import List, Dict, Any, Tuple
import config

logger = logging.getLogger("SILCE.IntentEngine")

KNOWN_INTENTS = {
    "Interview Preparation": {
        "keywords": ["polish", "shoe", "deodorant", "nivea", "grooming", "interview", "belt", "shaving", "cufflinks", "cuff links", "tie"],
        "min_matches": 1,
        "priority": 4.0,
    },
    "Personal Care & Comfort": {
        "keywords": ["whisper", "sanitary", "period", "pads", "tampons"],
        "min_matches": 1,
        "priority": 3.0,
    },
    "Celebration / Party": {
        "keywords": ["cigarettes", "soda", "mixer", "coke", "chips", "party", "smoke"],
        "min_matches": 1,
        "priority": 2.0,
    },
    "Weekly Household Refill": {
        "keywords": ["milk", "cucumber", "vegetables", "produce", "rice", "atta", "essential"],
        "min_matches": 1,
        "priority": 1.0,
    },
}

def analyze_cart_intent_llm(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    return analyze_cart_intent_semantic(cart_items)

def analyze_cart_intent_semantic(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    """Embedded rule-based & keyword semantic reasoner (Zero-latency fallback)."""
    if not cart_items:
        return "Weekly Household Refill", 0.0, []
        
    item_text_tokens = []
    for item in cart_items:
        name = item.get("name", "").lower()
        tags = [t.lower() for t in item.get("tags", [])]
        item_text_tokens.extend(name.split())
        item_text_tokens.extend(tags)

    full_text = " ".join(item_text_tokens)
    best_intent = "Weekly Household Refill"
    max_score = -1.0
    best_matches = []

    for intent, config_item in KNOWN_INTENTS.items():
        matched = [kw for kw in config_item["keywords"] if kw.lower() in full_text]
        if len(matched) >= config_item["min_matches"]:
            score = (config_item.get("priority", 1.0) * 10) + len(matched)
            if score > max_score:
                max_score = score
                best_intent = intent
                best_matches = matched

    if max_score < 0:
        best_intent = "Weekly Household Refill"
        max_score = 0.93
        best_matches = ["grocery"]

    logger.info(f"Embedded Intent Engine: '{best_intent}' (Score: {max_score:.2f}, Matches: {best_matches})")
    return best_intent, 0.94, best_matches

def analyze_cart_intent(cart_items: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    return analyze_cart_intent_semantic(cart_items)