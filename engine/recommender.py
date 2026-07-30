import json
import random
import time
import logging
from typing import List, Dict, Any, Optional
from engine.intent_engine import analyze_cart_intent, KNOWN_INTENTS

logger = logging.getLogger("SILCE.Recommender")

CONFIDENCE_THRESHOLD = 0.70

def generate_recommendation(
    cart_items: List[Dict[str, Any]],
    user_persona: Dict[str, Any],
    catalog: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Core SILCE logic:
    1. Infer intent from active cart items.
    2. Filter catalog to categories the user has NEVER purchased from.
    3. Exclude products already in the cart.
    4. Rank candidates based on life_contexts alignment and semantic tag matching.
    5. Output EXACTLY ONE high-confidence recommendation + contextual micro-copy nudge.
    """
    start_time = time.time()

    # Calculate cart total item count and monetary value
    total_qty = sum(item.get("qty", 1) for item in cart_items)
    cart_value = sum(item.get("price", 0) * item.get("qty", 1) for item in cart_items)

    # 1. Infer intent
    intent_name, intent_score, matched_keywords = analyze_cart_intent(cart_items)

    # Strict Rule 1: Cart item count must be >= 3
    if total_qty < 3:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "has_recommendation": False,
            "reason": f"Cart has {total_qty} items (minimum 3 required for SILCE inference).",
            "intent": intent_name,
            "intent_confidence": intent_score,
            "latency_ms": latency_ms,
            "diagnostics": {
                "cart_items_count": total_qty,
                "cart_value": cart_value,
                "rule_failed": "item_count_below_3"
            }
        }

    # Strict Rule 2: Cart value must be >= ₹199
    if cart_value < 199:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "has_recommendation": False,
            "reason": f"Cart value (₹{cart_value}) is below ₹199 threshold.",
            "intent": intent_name,
            "intent_confidence": intent_score,
            "latency_ms": latency_ms,
            "diagnostics": {
                "cart_items_count": total_qty,
                "cart_value": cart_value,
                "rule_failed": "cart_value_below_199"
            }
        }

    # 2. Extract user's unpurchased categories and items currently in cart
    purchased_categories = set(user_persona.get("purchased_categories", []))
    unexplored_categories = set(user_persona.get("unexplored_categories", []))
    cart_product_ids = set(item.get("id") for item in cart_items)

    # 3. Filter catalog candidates
    eligible_candidates = []
    for product in catalog:
        cat = product.get("category")
        pid = product.get("id")
        in_stock = product.get("in_stock", True)

        # Must be in stock
        if not in_stock:
            continue

        # Must be from an UNEXPLORED category
        if cat in purchased_categories or cat not in unexplored_categories:
            continue

        # Cannot be already in cart
        if pid in cart_product_ids:
            continue

        eligible_candidates.append(product)

    if not eligible_candidates:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "has_recommendation": False,
            "reason": "No candidate products available in unexplored categories.",
            "intent": intent_name,
            "intent_confidence": intent_score,
            "latency_ms": latency_ms,
            "diagnostics": {
                "cart_items_count": total_qty,
                "cart_value": cart_value,
                "rule_failed": "no_eligible_candidates"
            }
        }

    # 4. Score candidates based on contextual alignment
    best_product = None
    best_score = 0.0

    for product in eligible_candidates:
        prod_contexts = product.get("life_contexts", [])
        score = 0.50 # base score

        # Intent match boost
        if intent_name in prod_contexts:
            score += 0.35
        
        # Tag match boost
        prod_tags = [t.lower() for t in product.get("tags", [])]
        for kw in matched_keywords:
            if kw.lower() in prod_tags:
                score += 0.10

        # Small tie-breaker boost for popular subcategories
        score += random.uniform(0.01, 0.05)

        if score > best_score:
            best_score = score
            best_product = product

    latency_ms = round((time.time() - start_time) * 1000, 2)

    # Enforce Confidence Threshold (Trust Through Relevance)
    if best_score < CONFIDENCE_THRESHOLD or not best_product:
        return {
            "has_recommendation": False,
            "reason": f"Confidence score ({best_score:.2f}) below threshold ({CONFIDENCE_THRESHOLD}). Recommendation suppressed to preserve trust.",
            "intent": intent_name,
            "intent_confidence": intent_score,
            "latency_ms": latency_ms
        }

    # 5. Format micro-copy nudge
    nudge_templates = KNOWN_INTENTS.get(intent_name, {}).get("nudge_templates", [
        "Try something new today: {product_name}!"
    ])
    selected_template = random.choice(nudge_templates)
    nudge_text = selected_template.format(product_name=best_product["name"])

    return {
        "has_recommendation": True,
        "product": best_product,
        "nudge_text": nudge_text,
        "new_category": best_product["category"],
        "intent_inferred": intent_name,
        "intent_confidence": round(intent_score, 2),
        "recommendation_confidence": round(best_score, 2),
        "latency_ms": latency_ms,
        "user_unexplored_categories": user_persona.get("unexplored_categories", []),
        "diagnostics": {
            "cart_items_count": len(cart_items),
            "matched_keywords": matched_keywords,
            "eligible_candidates_evaluated": len(eligible_candidates),
            "purchased_categories_filtered": list(purchased_categories)
        }
    }
