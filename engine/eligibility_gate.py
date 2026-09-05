"""
Strict Purchase Intent & Category Eligibility Gate for Myntra StyleProof™
Evaluates whether a wishlisted product meets the strict criteria for surfacing
FitTwin biometric proofs and Wardrobe Lookbook pairings.
"""
from typing import Dict, Any, Tuple

# Categories strictly excluded from FitTwin/StyleProof (Innerwear, Socks, Accessories, Beauty)
EXCLUDED_CATEGORIES = [
    "innerwear", "briefs", "boxers", "trunks", "vests", "lingerie", "bras", "panties",
    "socks", "accessories", "eyewear", "sunglasses", "jewellery", "jewelry",
    "beauty", "cosmetics", "fragrance", "perfume", "wallet", "belt", "handbag", "caps", "hats"
]

# Universal neutral staples for cold-start personas (0 past orders)
COLD_START_NEUTRAL_STAPLES = [
    {
        "id": "STAPLE_01",
        "title": "Classic 220 GSM Organic Cotton Crew Tee",
        "brand": "Roadster Essentials",
        "category": "Topwear - T-Shirts",
        "color": "Optic White",
        "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&q=80",
        "is_staple": True
    },
    {
        "id": "STAPLE_02",
        "title": "Washed Raw Black Slim Tapered Jeans",
        "brand": "Levi's Essentials",
        "category": "Bottomwear - Jeans",
        "color": "Washed Black",
        "image_url": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=500&q=80",
        "is_staple": True
    },
    {
        "id": "STAPLE_03",
        "title": "Clean Minimalist Leather Court Sneakers",
        "brand": "HRX Clean Basics",
        "category": "Footwear - Sneakers",
        "color": "Triple White",
        "image_url": "https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=500&q=80",
        "is_staple": True
    }
]

def evaluate_item_eligibility(
    sku: Dict[str, Any],
    persona: Dict[str, Any],
    explicit_override: bool = False
) -> Dict[str, Any]:
    """
    Evaluates an item against the Intent + Category Gate:
    1. Category Eligibility Gate: Excludes commodity/innerwear/accessories
    2. Purchase Intent Signal: Dwell >= 10s or Repeat Views >= 2 or explicit card tap
    3. Model Confidence Score: Must be >= 0.80
    4. System Action determination
    """
    sku_id = sku.get("id", "")
    category = sku.get("category", "").lower()
    main_cat = sku.get("main_category", "").lower()

    # --- 1. CATEGORY ELIGIBILITY GATE ---
    is_category_blocked = False
    for exc in EXCLUDED_CATEGORIES:
        if exc in category or exc in main_cat:
            is_category_blocked = True
            break
            
    if sku.get("is_category_eligible") is False:
        is_category_blocked = True

    if is_category_blocked:
        return {
            "sku_id": sku_id,
            "is_eligible": False,
            "category_gate": "BLOCKED",
            "category_detail": sku.get("category", "Excluded Category"),
            "intent_level": "N/A (Blocked)",
            "intent_detail": "Commodity / Non-Apparel SKU",
            "confidence_score": 0.0,
            "system_action": "CATEGORY_EXCLUDED",
            "badge_visible": False,
            "pill_badge_text": "",
            "diagnostic_summary": "[CATEGORY GATE: BLOCKED] Innerwear/Accessories do not require FitTwin matching."
        }

    # --- 2. INTENT SIGNAL MATCHING ---
    intent_signals = persona.get("intent_signals", {}).get(sku_id, {})
    repeat_views = intent_signals.get("repeat_views", 1)
    dwell_seconds = intent_signals.get("dwell_seconds", 3)
    explicit_intent = intent_signals.get("explicit_intent", False) or explicit_override

    # High intent criterion: Dwell >= 10s OR Repeat views >= 2 OR Explicit interaction
    is_high_intent = (dwell_seconds >= 10) or (repeat_views >= 2) or explicit_intent

    # --- 3. MODEL CONFIDENCE CALCULATION ---
    # Confidence is calculated based on UGC reviews matching and closet compatibility
    ugc_reviews = sku.get("ugc_reviews", [])
    user_height = persona.get("body_profile", {}).get("height", "5'9\"")
    has_exact_height_ugc = any(rev.get("reviewer_height") == user_height for rev in ugc_reviews)

    if has_exact_height_ugc:
        confidence_score = 0.94
    elif ugc_reviews:
        confidence_score = 0.88
    else:
        confidence_score = 0.65

    # Confidence Threshold Rule: Must be >= 0.80
    confidence_passed = confidence_score >= 0.80

    # --- 4. SYSTEM ACTION DETERMINATION ---
    closet_items = persona.get("past_purchases_closet") or persona.get("owned_closet") or []
    closet_count = len(closet_items)
    is_cold_start = closet_count == 0

    if not is_high_intent:
        return {
            "sku_id": sku_id,
            "is_eligible": False,
            "category_gate": "ELIGIBLE",
            "category_detail": sku.get("category", "Apparel"),
            "intent_level": "LOW",
            "intent_detail": f"Dwell {dwell_seconds}s (<10s) • {repeat_views} View(s)",
            "confidence_score": confidence_score,
            "system_action": "SILENT_NO_INTENT",
            "badge_visible": False,
            "pill_badge_text": "",
            "diagnostic_summary": f"[INTENT: LOW] Passive save (Dwell {dwell_seconds}s). Engine remains non-intrusive."
        }

    if not confidence_passed:
        return {
            "sku_id": sku_id,
            "is_eligible": False,
            "category_gate": "ELIGIBLE",
            "category_detail": sku.get("category", "Apparel"),
            "intent_level": "HIGH",
            "intent_detail": f"Dwell {dwell_seconds}s • {repeat_views} Views",
            "confidence_score": confidence_score,
            "system_action": "SILENT_LOW_CONFIDENCE",
            "badge_visible": False,
            "pill_badge_text": "",
            "diagnostic_summary": f"[CONFIDENCE: {confidence_score:.2f} < 0.80] Kept silent to prevent false fit advice."
        }

    # High Intent + Category Eligible + Confidence >= 0.80
    if is_cold_start:
        system_action = "FALLBACK_NEUTRAL_STAPLES"
        pill_text = f"✨ Neutral Staples Lookbook • {int(confidence_score * 100)}% Fit Match"
        diagnostic_text = f"[ACTION: FALLBACK] High Intent + 0 Orders -> Adaptive Neutral Staples + {int(confidence_score * 100)}% StyleProof™."
    else:
        system_action = "FULL_FITTWIN_UNLOCKED"
        paired_count = min(2, closet_count)
        pill_text = f"✨ Pairs with {paired_count} closet items • {int(confidence_score * 100)}% Fit Match"
        diagnostic_text = f"[ACTION: UNLOCKED] High Intent + {closet_count} Owned Orders -> Full Lookbook & {int(confidence_score * 100)}% StyleProof™."

    return {
        "sku_id": sku_id,
        "is_eligible": True,
        "category_gate": "ELIGIBLE",
        "category_detail": sku.get("category", "Apparel"),
        "intent_level": "HIGH",
        "intent_detail": f"Dwell {dwell_seconds}s (≥10s) • {repeat_views} Views",
        "confidence_score": confidence_score,
        "system_action": system_action,
        "badge_visible": True,
        "pill_badge_text": pill_text,
        "diagnostic_summary": diagnostic_text
    }

def batch_evaluate_catalog_for_persona(
    catalog: list,
    persona: dict
) -> Dict[str, Dict[str, Any]]:
    """Evaluates the entire catalog against the given persona's intent signals."""
    results = {}
    for item in catalog:
        results[item["id"]] = evaluate_item_eligibility(item, persona)
    return results
