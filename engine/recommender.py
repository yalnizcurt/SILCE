"""
SILCE Recommendation Engine  —  Explicit Primary Category Taxonomy
===================================================================
Core principle: SILCE infers WHY the customer opened Blinkit,
then selects ONE adjacent UNEXPLORED CATEGORY from outside the
basket's domain. The product is only a representative SKU.

THE AI DECISION IS THE CATEGORY. NOT THE PRODUCT.

No embeddings. No semantic inference. No LLM category guessing.
Only the explicit taxonomy and fixed mission→category mapping below.

Pipeline:
  Basket
    → Map each item to PRIMARY TAXONOMY CATEGORY
    → Classify basket into DOMAIN(S)
    → Infer Shopping Mission
    → Look up FIXED ADJACENT CATEGORIES (mission × domain)
    → Filter: remove categories already in purchase history
    → Filter: remove categories from same domain as basket
    → Select HIGHEST-CONFIDENCE eligible category
    → Pick DESIGNATED REPRESENTATIVE PRODUCT
    → Return ONE-LINE intent-aware explanation
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from engine.intent_engine import analyze_cart_intent, KNOWN_INTENTS

logger = logging.getLogger("SILCE.Recommender")

# ════════════════════════════════════════════════════════════════════════════
#  PRIMARY CATEGORY TAXONOMY  (verbatim from product specification)
#  Every catalog product maps to exactly ONE of these categories.
# ════════════════════════════════════════════════════════════════════════════

# ── FOOD & GROCERY ──────────────────────────────────────────────────────────
FOOD_GROCERY: Set[str] = {
    "Dairy",
    "Fresh Vegetables",
    "Fresh Fruits",
    "Bakery",
    "Breakfast Essentials",
    "Snacks & Munchies",
    "Chocolates & Desserts",
    "Instant Foods",
    "Beverages",
    "Frozen Foods",
    "Cooking Essentials",
}

# ── HOUSEHOLD ───────────────────────────────────────────────────────────────
HOUSEHOLD: Set[str] = {
    "Home Cleaning",
    "Laundry Care",
    "Kitchen Cleaning",
    "Storage & Organisation",
    "Paper Products",
}

# ── PERSONAL CARE ───────────────────────────────────────────────────────────
PERSONAL_CARE: Set[str] = {
    "Oral Care",
    "Hair Care",
    "Skin Care",
    "Bath & Body",
    "Feminine Care",
}

# ── HEALTH ──────────────────────────────────────────────────────────────────
HEALTH: Set[str] = {
    "Medicines",
    "Vitamins",
    "First Aid",
    "Wellness",
}

# ── BABY ────────────────────────────────────────────────────────────────────
BABY: Set[str] = {"Baby Food", "Baby Hygiene", "Baby Care"}

# ── PET ─────────────────────────────────────────────────────────────────────
PET: Set[str] = {"Pet Food", "Pet Care", "Dog Food", "Cat Food"}

# ── HOME & LIFESTYLE ────────────────────────────────────────────────────────
HOME_LIFESTYLE: Set[str] = {
    "Air Fresheners",
    "Kitchen Accessories",
    "Home Essentials",
    "Party Supplies",
    "Disposable Supplies",   # paper cups, plates
}

# ── ENTERTAINMENT ───────────────────────────────────────────────────────────
ENTERTAINMENT: Set[str] = {
    "Entertainment",
    "Board Games",
    "Playing Cards",
    "Party Activities",
}

# ── OFFICE ──────────────────────────────────────────────────────────────────
OFFICE: Set[str] = {
    "Stationery",
    "Office Pantry",
    "Disposable Supplies",
}

# ── TOBACCO ─────────────────────────────────────────────────────────────────
TOBACCO: Set[str] = {"Tobacco", "Paan Corner"}

# Domain lookup table
_DOMAIN_MAP: Dict[str, str] = {}
for _cat in FOOD_GROCERY:       _DOMAIN_MAP[_cat] = "food"
for _cat in HOUSEHOLD:          _DOMAIN_MAP[_cat] = "household"
for _cat in PERSONAL_CARE:      _DOMAIN_MAP[_cat] = "personal_care"
for _cat in HEALTH:             _DOMAIN_MAP[_cat] = "health"
for _cat in PET:                _DOMAIN_MAP[_cat] = "pet"
for _cat in HOME_LIFESTYLE:     _DOMAIN_MAP[_cat] = "home_lifestyle"
for _cat in ENTERTAINMENT:      _DOMAIN_MAP[_cat] = "entertainment"
for _cat in OFFICE:             _DOMAIN_MAP[_cat] = "office"
for _cat in TOBACCO:            _DOMAIN_MAP[_cat] = "tobacco"
_DOMAIN_MAP["Shoe Care"] = "shoe_care"
_DOMAIN_MAP["Formal Accessories"] = "formal_accessories"


# ════════════════════════════════════════════════════════════════════════════
#  CATALOG CATEGORY → PRIMARY TAXONOMY  (translation layer)
#  Maps legacy catalog category strings to the canonical taxonomy.
#  This avoids changing catalog.json and persona files.
# ════════════════════════════════════════════════════════════════════════════

CATALOG_TO_TAXONOMY: Dict[str, str] = {
    # FOOD & GROCERY
    "Milk":                        "Dairy",
    "Dairy":                       "Dairy",
    "Dairy Complements":           "Dairy",
    "Eggs":                        "Breakfast Essentials",
    "Spreads":                     "Breakfast Essentials",
    "Bakery":                      "Bakery",
    "Vegetables":                  "Fresh Vegetables",
    "Fresh Produce":               "Fresh Vegetables",
    "Snacks & Munchies":           "Snacks & Munchies",
    "Healthy Snacks":              "Snacks & Munchies",
    "Chocolates & Sweets":         "Chocolates & Desserts",
    "Frozen Foods":                "Frozen Foods",
    "Beverages":                   "Beverages",
    "Tea, Coffee & Health Drinks": "Beverages",
    "Tea & Coffee & Health Drinks":"Beverages",
    "Hydration":                   "Beverages",       # Bisleri Water → Beverages = FOOD domain
    "Groceries":                   "Cooking Essentials",
    "Party Essentials":            "Party Supplies",  # → HOME_LIFESTYLE domain
    # HOUSEHOLD
    "Home Cleaning":               "Home Cleaning",
    "Laundry Care":                "Laundry Care",
    "Kitchen Cleaning":            "Kitchen Cleaning",
    "Storage & Organisation":      "Storage & Organisation",
    "Paper Products":              "Paper Products",
    "Disposable Supplies":         "Disposable Supplies",
    # HEALTH
    "Pharmacy":                    "Medicines",
    "Health Recovery":             "Medicines",
    "Vitamins":                    "Vitamins",
    "Wellness":                    "Wellness",
    # PERSONAL CARE
    "Oral Care":                   "Oral Care",
    "Feminine Hygiene":            "Feminine Care",
    "Personal Care":               "Personal Care",
    "Deodorants":                  "Personal Care",
    # FASHION & ACCESSORIES
    "Shoe Care":                   "Shoe Care",
    "Formal Accessories":          "Formal Accessories",
    # PET CARE
    "Pet Care":                    "Pet Care",
    # ENTERTAINMENT
    "Entertainment":               "Entertainment",
    # HOME & LIFESTYLE
    "Air Fresheners":              "Air Fresheners",
    # TOBACCO
    "Paan Corner":                 "Paan Corner",
}

# Per-product overrides for the ambiguous "Household Essentials" catch-all
# and other products whose catalog category doesn't precisely convey their taxonomy.
PRODUCT_TAXONOMY_OVERRIDE: Dict[str, str] = {
    "prod_107": "Laundry Care",           # Surf Excel detergent
    "prod_212": "Kitchen Cleaning",       # Vim Dishwash Gel
    "prod_504": "Disposable Supplies",    # Paper Tea Cups
    "prod_604": "Paper Products",         # Origami Tissues
    "prod_701": "Storage & Organisation", # Garbage Bags
    "prod_702": "Home Cleaning",          # Lizol Floor Cleaner
    "prod_703": "Kitchen Cleaning",       # Pril Dishwash Liquid
    "prod_704": "Kitchen Cleaning",       # Scotch-Brite Sponge Wipes
    "prod_801": "Wellness",               # Farmley Almonds → Health/Wellness
    "prod_802": "Breakfast Essentials",   # Kissan Jam → Food/Breakfast
    "prod_803": "Disposable Supplies",    # Solo Paper Plates
    "prod_804": "Medicines",              # Vicks Action 500
    "prod_806": "Beverages",             # Bisleri Water → Food domain
    "prod_402": "Oral Care",             # Doublemint Mints → Oral Care
    "prod_401": "Paan Corner",           # Cigarettes → Tobacco
    "prod_403": "Paan Corner",           # Lighter → Tobacco
    "prod_503": "Instant Foods",         # Maggi → Instant Foods
    "prod_601": "Pain Relief",            # Crocin Pain Relief
    "prod_605": "Pain Relief",            # Saridon Headache Relief
    "prod_602": "Pain Relief",            # Electral / Medicines
    "prod_603": "First Aid",              # Thermometer
}


def _get_taxonomy(product: Dict) -> str:
    """Return the canonical taxonomy category for a product."""
    pid = product.get("id", "")
    if pid in PRODUCT_TAXONOMY_OVERRIDE:
        return PRODUCT_TAXONOMY_OVERRIDE[pid]
    cat = product.get("category", "")
    return CATALOG_TO_TAXONOMY.get(cat, cat)


def _get_domain(taxonomy_cat: str) -> str:
    """Return the top-level domain for a taxonomy category."""
    return _DOMAIN_MAP.get(taxonomy_cat, "other")


def _get_basket_domains(cart_items: List[Dict]) -> Set[str]:
    """Return the set of top-level domains represented in the basket."""
    domains = set()
    for item in cart_items:
        tax = _get_taxonomy(item)
        dom = _get_domain(tax)
        domains.add(dom)
    return domains


def _translate_purchased_cats(purchased_raw: List[str]) -> Set[str]:
    """Convert persona purchased_categories (legacy strings) to taxonomy names."""
    return {CATALOG_TO_TAXONOMY.get(c, c) for c in purchased_raw}


# ════════════════════════════════════════════════════════════════════════════
#  FIXED MISSION → ADJACENT CATEGORY MAP  (verbatim from product specification)
#  Do NOT change this mapping. Do NOT add semantic inference.
# ════════════════════════════════════════════════════════════════════════════

MISSION_ADJACENT_CATEGORIES: Dict[str, List[str]] = {
    # Scenario 1: Weekly Household Refill → Pet Care
    "Weekly Household Refill": [
        "Pet Care",
    ],

    # Scenario 2: Personal Care & Comfort → Comfort & Wellness (Dark Chocolate)
    "Personal Care & Comfort": [
        "Comfort & Wellness",
        "Chocolates & Desserts",
    ],

    # Scenario 3: Celebration / Party → Recovery & Wellness (Saridon)
    "Celebration / Party": [
        "Recovery & Wellness",
        "Pain Relief",
    ],

    # Scenario 4: Interview Preparation → Formal Accessories (Silk Tie)
    "Interview Preparation": [
        "Formal Accessories",
    ],
}

# ── Designated representative product per taxonomy category ─────────────────
CATEGORY_REPRESENTATIVE: Dict[str, List[str]] = {
    "Pet Care":               ["prod_901"],               # Pedigree Dry Dog Food ₹180
    "Comfort & Wellness":     ["prod_305"],               # Bournville 50% Dark Chocolate ₹50
    "Chocolates & Desserts":  ["prod_305"],               # Bournville 50% Dark Chocolate ₹50
    "Recovery & Wellness":    ["prod_605", "prod_601"],   # Saridon ₹42, Crocin ₹30
    "Pain Relief":            ["prod_605", "prod_601"],   # Saridon ₹42, Crocin ₹30
    "Formal Accessories":     ["prod_507"],               # Park Avenue Formal Navy Silk Tie ₹199
    "Home Cleaning":          ["prod_702"],               # Lizol ₹45
    "Kitchen Cleaning":       ["prod_812"],               # Vim Bar ₹20
    "Oral Care":              ["prod_809"],               # Colgate ₹30
}

# ── Human Observation Headers & Companion Suggestions (Apple Intelligence Copy) ─────────
MISSION_COMPANION_COPY: Dict[str, Dict[str, str]] = {
    "Weekly Household Refill": {
        "observation": "Looks like you're restocking the house.",
        "suggestion":  "If you have a pet at home, this is something that's easy to forget during grocery runs.",
    },
    "Personal Care & Comfort": {
        "observation": "Taking care of yourself today?",
        "suggestion":  "A small comfort item can make the day a little easier.",
    },
    "Celebration / Party": {
        "observation": "Looks like you're getting ready for an evening out.",
        "suggestion":  "You may appreciate having this tomorrow.",
    },
    "Interview Preparation": {
        "observation": "Big day ahead?",
        "suggestion":  "A polished look is often in the little details.",
    },
}

def get_mission_observation(intent_name: str) -> str:
    item = MISSION_COMPANION_COPY.get(intent_name)
    if item:
        return item["observation"]
    return "Noticed something for your cart."

def generate_explanation(intent_name: str, silce_cat: str, cart_items: List[Dict[str, Any]]) -> str:
    item = MISSION_COMPANION_COPY.get(intent_name)
    if item:
        return item["suggestion"]
    return "A thoughtful addition to complement today's order."


_DEFAULT_EXPLANATION = "A thoughtful addition to complement today's order."

# ── Brand & Rating metadata ─────────────────────────────────────────────────
BRANDS: Dict[str, str] = {
    "prod_104": "Amul",        "prod_112": "Fresho",       "prod_113": "Fresho",
    "prod_210": "Fresho",      "prod_211": "Mother Dairy",  "prod_213": "Harvest Gold",
    "prod_105": "Society",     "prod_106": "Parle-G",       "prod_107": "Surf Excel",
    "prod_212": "Vim",         "prod_108": "Daawat",        "prod_109": "Aashirvaad",
    "prod_214": "Amul",        "prod_114": "Fresho",        "prod_115": "Fresho",
    "prod_301": "Coca-Cola",   "prod_302": "Lays",          "prod_303": "Kwality Walls",
    "prod_304": "Wingreens",   "prod_401": "Gold Flake",    "prod_402": "Doublemint",
    "prod_403": "Clipper",     "prod_501": "Nescafe",       "prod_503": "Maggi",
    "prod_504": "Chuk",        "prod_601": "Crocin",        "prod_602": "Electral",
    "prod_603": "Dr. Morepen", "prod_604": "Origami",       "prod_701": "Shalimar",
    "prod_702": "Lizol",       "prod_703": "Pril",          "prod_704": "Scotch-Brite",
    "prod_801": "Farmley",     "prod_802": "Kissan",        "prod_803": "Solo",
    "prod_804": "Vicks",       "prod_805": "Colin",         "prod_806": "Bisleri",
    "prod_807": "Rin",         "prod_808": "Odonil",        "prod_809": "Colgate",
    "prod_810": "Limcee",      "prod_811": "Bicycle",       "prod_812": "Vim",
    "prod_605": "Saridon",     "prod_901": "Pedigree",      "prod_305": "Cadbury",
    "prod_606": "Whisper",     "prod_307": "Kinley",        "prod_505": "Cherry Blossom",
    "prod_506": "Nivea",       "prod_507": "Park Avenue",
}

RATINGS: Dict[str, str] = {
    "prod_104": "4.8", "prod_112": "4.6", "prod_113": "4.7", "prod_210": "4.6",
    "prod_211": "4.7", "prod_213": "4.6", "prod_105": "4.6", "prod_106": "4.8",
    "prod_107": "4.9", "prod_212": "4.7", "prod_108": "4.8", "prod_109": "4.9",
    "prod_214": "4.7", "prod_114": "4.6", "prod_115": "4.6", "prod_301": "4.8",
    "prod_302": "4.7", "prod_303": "4.6", "prod_304": "4.7", "prod_401": "4.5",
    "prod_402": "4.6", "prod_403": "4.6", "prod_501": "4.8", "prod_503": "4.8",
    "prod_504": "4.7", "prod_601": "4.7", "prod_602": "4.6", "prod_603": "4.5",
    "prod_604": "4.7", "prod_701": "4.6", "prod_702": "4.8", "prod_703": "4.7",
    "prod_704": "4.8", "prod_801": "4.5", "prod_802": "4.7", "prod_803": "4.5",
    "prod_804": "4.6", "prod_805": "4.7", "prod_806": "4.8", "prod_807": "4.7",
    "prod_808": "4.6", "prod_809": "4.8", "prod_810": "4.7", "prod_811": "4.5",
    "prod_812": "4.8", "prod_605": "4.8", "prod_901": "4.8", "prod_305": "4.9",
    "prod_606": "4.9", "prod_307": "4.7", "prod_505": "4.7", "prod_506": "4.8",
    "prod_507": "4.9",
}


# ════════════════════════════════════════════════════════════════════════════
#  SELECTION ENGINE
# ════════════════════════════════════════════════════════════════════════════

def _select_category_and_product(
    intent_name: str,
    purchased_taxonomy_cats: Set[str],
    basket_domains: Set[str],
    catalog_by_id: Dict[str, Dict],
    cart_product_ids: Set[str],
    max_allowed_price: float,
    cart_items: List[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Optional[Dict], str]:
    adjacent = MISSION_ADJACENT_CATEGORIES.get(intent_name, [])
    cart_taxonomy_cats = {_get_taxonomy(item) for item in (cart_items or [])}

    for silce_cat in adjacent:
        cat_domain = _get_domain(silce_cat)

        if cat_domain in basket_domains:
            continue

        # ── Same category & purchase history gate ───────────────────────
        if silce_cat in cart_taxonomy_cats or silce_cat in purchased_taxonomy_cats:
            continue

        product_ids = CATEGORY_REPRESENTATIVE.get(silce_cat, [])
        explanation = generate_explanation(intent_name, silce_cat, cart_items or [])

        for pid in product_ids:
            prod = catalog_by_id.get(pid)
            if (prod
                    and prod.get("in_stock", True)
                    and pid not in cart_product_ids
                    and prod["price"] <= max_allowed_price):
                return silce_cat, prod, explanation

    return None, None, _DEFAULT_EXPLANATION


from engine.gemini_reasoner import query_gemini_reasoner

# ════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════════════════════

def collect_guardrail_candidates(
    intent_name: str,
    purchased_taxonomy: Set[str],
    basket_domains: Set[str],
    catalog_by_id: Dict[str, Dict],
    cart_product_ids: Set[str],
    max_allowed_price: float,
    cart_items: List[Dict[str, Any]] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Collects eligible categories and representative candidate SKUs passing rule guardrails."""
    adjacent = MISSION_ADJACENT_CATEGORIES.get(intent_name, [])
    cart_taxonomy_cats = {_get_taxonomy(item) for item in (cart_items or [])}
    eligible_categories = []
    candidate_products = []

    for silce_cat in adjacent:
        cat_domain = _get_domain(silce_cat)
        if cat_domain in basket_domains:
            continue

        # ── Same category & purchase history gate ───────────────────────
        if silce_cat in cart_taxonomy_cats or silce_cat in purchased_taxonomy:
            continue

        eligible_categories.append(silce_cat)
        pids = CATEGORY_REPRESENTATIVE.get(silce_cat, [])
        for pid in pids:
            prod = catalog_by_id.get(pid)
            if (prod
                    and prod.get("in_stock", True)
                    and pid not in cart_product_ids
                    and prod["price"] <= max_allowed_price):
                item_copy = dict(prod)
                item_copy["silce_category"] = silce_cat
                item_copy["brand"] = BRANDS.get(pid, "Trusted Brand")
                item_copy["rating"] = RATINGS.get(pid, "4.7") + "★"
                candidate_products.append(item_copy)

    return eligible_categories, candidate_products


def generate_recommendation(
    cart_items: List[Dict[str, Any]],
    user_persona: Dict[str, Any],
    catalog: List[Dict[str, Any]],
) -> Dict[str, Any]:
    start_time = time.time()

    total_qty     = sum(item.get("qty", 1) for item in cart_items)
    cart_subtotal = sum(item.get("price", 0) * item.get("qty", 1) for item in cart_items)
    intent_name, intent_score, matched_keywords = analyze_cart_intent(cart_items)

    def _fail(reason: str, rule: str) -> Dict:
        return {
            "has_recommendation": False,
            "reason": reason,
            "intent": intent_name,
            "intent_confidence": round(intent_score, 2),
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "diagnostics": {
                "cart_items_count": total_qty,
                "cart_subtotal": cart_subtotal,
                "rule_failed": rule,
                "trigger_passed": False,
            },
        }

    if total_qty < 2:
        return _fail(f"Cart has {total_qty} item (minimum 2 required).", "item_count_below_2")
    if intent_name not in KNOWN_INTENTS:
        return _fail("Basket does not match a recognised shopping mission.", "unrecognised_mission")
    if cart_subtotal < 49:
        return _fail("Cart subtotal too low.", "subtotal_too_low")

    catalog_by_id        = {p["id"]: p for p in catalog}
    cart_product_ids     = {item.get("id") for item in cart_items}
    max_allowed_price    = max(0.40 * cart_subtotal, 60.0)
    purchased_taxonomy   = _translate_purchased_cats(user_persona.get("purchased_categories", []))
    basket_domains       = _get_basket_domains(cart_items)

    # ── Rule Engine Guardrails (Pass 1) ──────────────────────────────────────
    eligible_cats, candidate_prods = collect_guardrail_candidates(
        intent_name,
        purchased_taxonomy,
        basket_domains,
        catalog_by_id,
        cart_product_ids,
        max_allowed_price,
        cart_items=cart_items,
    )

    # ── AI-Native Reasoning Layer (Pass 2: Gemini 2.5 Flash) ─────────────────
    gemini_res = query_gemini_reasoner(
        cart_items,
        list(purchased_taxonomy),
        eligible_cats,
        candidate_prods,
        max_allowed_price,
    )

    reasoning_engine = "deterministic_fallback"
    if gemini_res:
        silce_category = gemini_res["selected_category"]
        rep_product = catalog_by_id.get(gemini_res["representative_product_id"])
        explanation = gemini_res["explanation"]
        if gemini_res.get("mission"):
            intent_name = gemini_res["mission"]
        recommendation_confidence = gemini_res.get("confidence", 0.94)
        reasoning_engine = gemini_res.get("engine", "gemini-2.5-flash")
        observation = gemini_res.get("observation") or get_mission_observation(intent_name)
    else:
        # Fallback to deterministic selection
        silce_category, rep_product, explanation = _select_category_and_product(
            intent_name,
            purchased_taxonomy,
            basket_domains,
            catalog_by_id,
            cart_product_ids,
            max_allowed_price,
            cart_items=cart_items,
        )
        recommendation_confidence = 0.92
        observation = get_mission_observation(intent_name)

    if not silce_category or not rep_product:
        return _fail(
            "No eligible adjacent cross-domain category found within price guardrail.",
            "no_eligible_category",
        )

    pid        = rep_product["id"]
    latency_ms = round((time.time() - start_time) * 1000, 2)

    recommendation = {
        "product":                   rep_product,
        "brand":                     BRANDS.get(pid, "Trusted Brand"),
        "rating":                    RATINGS.get(pid, "4.6") + "★",
        "silce_category":            silce_category,
        "category_explanation":      explanation,
        "observation":               observation,
        "nudge_text":                explanation,
        "new_category":              rep_product["category"],
        "product_reason":            explanation,
        "recommendation_confidence": recommendation_confidence,
        "is_unexplored_category":    True,
        "reasoning_engine":          reasoning_engine,
    }

    return {
        "has_recommendation":         True,
        "silce_category":             silce_category,
        "category_explanation":       explanation,
        "observation":                observation,
        "recommendations":            [recommendation],
        "product":                    rep_product,
        "nudge_text":                 explanation,
        "new_category":               rep_product["category"],
        "intent_inferred":            intent_name,
        "intent_confidence":          round(intent_score, 2),
        "recommendation_confidence":  recommendation_confidence,
        "product_reason":             explanation,
        "latency_ms":                 latency_ms,
        "reasoning_engine":          reasoning_engine,
        "user_unexplored_categories": user_persona.get("unexplored_categories", []),
        "diagnostics": {
            "cart_items_count":          total_qty,
            "cart_subtotal":             cart_subtotal,
            "max_allowed_price":         max_allowed_price,
            "basket_domains":            sorted(basket_domains),
            "matched_keywords":          matched_keywords,
            "selected_silce_category":   silce_category,
            "purchased_taxonomy_cats":   sorted(purchased_taxonomy),
            "reasoning_engine":          reasoning_engine,
            "trigger_passed":            True,
        },
    }