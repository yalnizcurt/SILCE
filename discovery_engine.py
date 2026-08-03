import json
import logging
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SILCE.DiscoveryEngine")

BASE_DIR = Path(__file__).parent.resolve()
RAW_DATA_PATH = BASE_DIR / "data" / "raw_reviews.json"
OUTPUT_DIR = BASE_DIR / "artifacts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "discovery_insights.json"

COMPLAINT_PATTERNS = {
    "dark_store_stockout": ["stockout", "out of stock", "unavailable", "empty store"],
    "pricing_and_fees": ["handling fee", "delivery partner fee", "overpriced", "price"],
    "returns_friction": ["return", "damaged", "refund", "customer support"]
}

HABIT_PATTERNS = {
    "speed_runs": ["60-second", "speed run", "30 seconds", "quick delivery", "8 minutes", "10 minutes"],
    "grocery_only_mental_model": ["grocery-only", "kirana", "daily veggies", "milk", "bread", "only buy groceries"],
    "two_item_quick_orders": ["2-item", "two-item", "stick strictly", "2 items"]
}

OPPORTUNITY_PAIRS = [
    {
        "trigger_intent": "Weekly Grocery Refill",
        "example_basket": ["Amul Taaza Milk (1L)", "English Cucumber (500g)"],
        "latent_opportunity_category": "Eggs",
        "recommended_skus": ["Fresho Farm Fresh Eggs (6 pcs)"],
        "user_need": "Pairs daily essentials (milk, cucumber) with protein options like farm fresh eggs"
    },
    {
        "trigger_intent": "Morning Breakfast Run",
        "example_basket": ["Amul Taaza Milk (1L)", "Harvest Gold Whole Wheat Bread (400g)"],
        "latent_opportunity_category": "Eggs",
        "recommended_skus": ["Fresho Farm Fresh Eggs (6 pcs)"],
        "user_need": "Pairs daily milk and bread with breakfast essentials like fresh eggs"
    },
    {
        "trigger_intent": "Daily Veggies & Dairy",
        "example_basket": ["English Cucumber (500g)", "Fresh Red Tomatoes (500g)"],
        "latent_opportunity_category": "Dairy Complements",
        "recommended_skus": ["Mother Dairy Probiotic Curd (400g)"],
        "user_need": "Complements fresh salad vegetables with high-purchase probiotic curd"
    }
]

def run_discovery_pipeline() -> Dict[str, Any]:
    logger.info(f"Loading raw user feedback from {RAW_DATA_PATH}...")
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Raw reviews file not found at {RAW_DATA_PATH}")

    with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
        reviews = json.load(f)

    total_reviews = len(reviews)
    explicit_complaints = {k: 0 for k in COMPLAINT_PATTERNS.keys()}
    implicit_habits = {k: 0 for k in HABIT_PATTERNS.keys()}

    for rev in reviews:
        text = rev.get("review_text", "").lower()
        for category, keywords in COMPLAINT_PATTERNS.items():
            if any(kw in text for kw in keywords):
                explicit_complaints[category] += 1
        for habit, keywords in HABIT_PATTERNS.items():
            if any(kw in text for kw in keywords):
                implicit_habits[habit] += 1

    structured_output = {
        "metadata": {
            "engine": "Google Antigravity Opportunity Discovery Engine",
            "total_reviews_analyzed": total_reviews,
            "analysis_scope": ["Explicit Complaints", "Implicit Habits", "Latent Cross-Category Opportunities"]
        },
        "explicit_complaints": {
            "dark_store_stockout_pct": round((explicit_complaints["dark_store_stockout"] / total_reviews) * 100, 1),
            "pricing_and_fees_pct": round((explicit_complaints["pricing_and_fees"] / total_reviews) * 100, 1),
            "returns_friction_pct": round((explicit_complaints["returns_friction"] / total_reviews) * 100, 1),
            "raw_counts": explicit_complaints
        },
        "implicit_habits": {
            "speed_runs_pct": round((implicit_habits["speed_runs"] / total_reviews) * 100, 1),
            "grocery_only_mental_model_pct": round((implicit_habits["grocery_only_mental_model"] / total_reviews) * 100, 1),
            "two_item_quick_orders_pct": round((implicit_habits["two_item_quick_orders"] / total_reviews) * 100, 1),
            "raw_counts": implicit_habits
        },
        "latent_opportunities": OPPORTUNITY_PAIRS,
        "product_takeaway": (
            "Blinkit users exhibit a strong 'Grocery-Only' mental model with 60-second speed-run behavior. "
            "SILCE captures 2-item cart pairings (e.g. Milk + Cucumber) to introduce 1 relevant adjacent category grocery item "
            "(Eggs, Curd, Bread) under a price guardrail, breaking category inertia and introducing discovery without checkout friction."
        )
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(structured_output, f, indent=2)

    logger.info(f"Opportunity Discovery Pipeline successfully generated insights at {OUTPUT_FILE}")
    return structured_output

if __name__ == "__main__":
    run_discovery_pipeline()