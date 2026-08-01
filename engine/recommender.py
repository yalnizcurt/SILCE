import json
import random
import time
import logging
from typing import List, Dict, Any, Optional
from engine.intent_engine import analyze_cart_intent, KNOWN_INTENTS

logger = logging.getLogger("SILCE.Recommender")

CONFIDENCE_THRESHOLD = 0.75

def generate_recommendation(
    cart_items: List[Dict[str, Any]],
    user_persona: Dict[str, Any],
    catalog: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Core SILCE logic (Part 4 PM Fellowship Specifications):
    1. Cart item count >= 2 active items.
    2. Cart subtotal >= ₹149 (excluding delivery/handling fees).
    3. Category Eligibility: Top-level category with 0 purchases in last 90 days.
    4. Price Ratio Guardrail: Candidate SKU price <= 40% of active cart subtotal.
    5. Exactly ONE recommendation card.
    6. Confidence Threshold >= 0.75.
    """
    start_time = time.time()

    # Calculate cart total item count and monetary subtotal
    total_qty = sum(item.get("qty", 1) for item in cart_items)
    cart_subtotal = sum(item.get("price", 0) * item.get("qty", 1) for item in cart_items)

    # 1. Infer intent
    intent_name, intent_score, matched_keywords = analyze_cart_intent(cart_items)

    # Trigger Gate 1: Cart item count must be >= 2
    if total_qty < 2:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "has_recommendation": False,
            "reason": f"Cart has {total_qty} items (minimum 2 active items required for SILCE inference).",
            "intent": intent_name,
            "intent_confidence": intent_score,
            "latency_ms": latency_ms,
            "diagnostics": {
                "cart_items_count": total_qty,
                "cart_subtotal": cart_subtotal,
                "rule_failed": "item_count_below_2"
            }
        }

    # Trigger Gate 2: Cart subtotal must be >= ₹149
    if cart_subtotal < 149:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "has_recommendation": False,
            "reason": f"Cart subtotal (₹{cart_subtotal}) is below ₹149 threshold.",
            "intent": intent_name,
            "intent_confidence": intent_score,
            "latency_ms": latency_ms,
            "diagnostics": {
                "cart_items_count": total_qty,
                "cart_subtotal": cart_subtotal,
                "rule_failed": "cart_subtotal_below_149"
            }
        }

    # 2. Extract user's unpurchased categories and items currently in cart
    purchased_categories = set(user_persona.get("purchased_categories", []))
    unexplored_categories = set(user_persona.get("unexplored_categories", []))
    cart_product_ids = set(item.get("id") for item in cart_items)

    # 3. Filter catalog candidates (Unexplored category + Price Ratio Guardrail <= 40% subtotal)
    max_allowed_price = 0.40 * cart_subtotal

    eligible_candidates = []
    for product in catalog:
        cat = product.get("category")
        pid = product.get("id")
        price = product.get("price", 0)
        in_stock = product.get("in_stock", True)

        # Must be in stock
        if not in_stock:
            continue

        # Must be from an UNEXPLORED category (0 purchases in 90 days)
        if cat in purchased_categories or (unexplored_categories and cat not in unexplored_categories):
            continue

        # Cannot be already in cart
        if pid in cart_product_ids:
            continue

        # Trigger Gate 4: Price Ratio Guardrail (Candidate Price <= 40% of Subtotal)
        if price > max_allowed_price:
            continue

        eligible_candidates.append(product)

    if not eligible_candidates:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "has_recommendation": False,
            "reason": f"No candidate products pass 40% price ratio guardrail (max ₹{max_allowed_price:.1f}) in unexplored categories.",
            "intent": intent_name,
            "intent_confidence": intent_score,
            "latency_ms": latency_ms,
            "diagnostics": {
                "cart_items_count": total_qty,
                "cart_subtotal": cart_subtotal,
                "max_allowed_price": max_allowed_price,
                "rule_failed": "price_guardrail_or_no_unexplored_candidates"
            }
        }

    # 4. Score candidates based on contextual alignment
    best_product = None
    best_score = 0.0

    for product in eligible_candidates:
        prod_contexts = product.get("life_contexts", [])
        score = 0.55 # base score

        # Intent match boost
        if intent_name in prod_contexts:
            score += 0.30
        
        # Tag match boost
        prod_tags = [t.lower() for t in product.get("tags", [])]
        for kw in matched_keywords:
            if kw.lower() in prod_tags:
                score += 0.10

        # Small tie-breaker
        score += random.uniform(0.01, 0.03)

        if score > best_score:
            best_score = score
            best_product = product

    latency_ms = round((time.time() - start_time) * 1000, 2)

    # Trigger Gate 6: Enforce Confidence Threshold >= 0.75
    if best_score < CONFIDENCE_THRESHOLD or not best_product:
        return {
            "has_recommendation": False,
            "reason": f"Confidence score ({best_score:.2f}) below threshold ({CONFIDENCE_THRESHOLD}). Recommendation suppressed to preserve trust.",
            "intent": intent_name,
            "intent_confidence": intent_score,
            "latency_ms": latency_ms,
            "diagnostics": {
                "cart_items_count": total_qty,
                "cart_subtotal": cart_subtotal,
                "best_score": best_score,
                "rule_failed": "confidence_below_0.75"
            }
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
