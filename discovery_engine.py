import json
import logging
from pathlib import Path
from typing import List, Dict, Any

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
        "trigger_intent": "Chai Time & Evening Snacks",
        "example_basket": ["Tea 250g", "Parle-G 100g"],
        "latent_opportunity_category": "Home & Kitchen",
        "recommended_skus": ["Stainless Steel Tea Strainer", "Ceramic Tea Mug"],
        "user_need": "Unmet cookware & kitchen accessories pairing during routine tea orders"
    },
    {
        "trigger_intent": "Weekend Hosting / Party",
        "example_basket": ["Doritos Nachos 150g", "Coca-Cola Zero 300ml"],
        "latent_opportunity_category": "Toys & Games",
        "recommended_skus": ["UNO Playing Cards", "Disposable Party Cups"],
        "user_need": "Social entertainment and hosting accessories during impulse snack orders"
    },
    {
        "trigger_intent": "Household Cleaning Blitz",
        "example_basket": ["Surf Excel Matic Liquid", "Vim Dishwash Gel"],
        "latent_opportunity_category": "Personal Care / Cleaning Accessories",
        "recommended_skus": ["Ergonomic Rubber Gloves", "Microfiber Cleaning Cloth"],
        "user_need": "Forgotten utility items during routine household cleaning restocking"
    },
    {
        "trigger_intent": "Emergency Work / Tech Setup",
        "example_basket": ["Coffee", "Energy Drink"],
        "latent_opportunity_category": "Electronics & Accessories",
        "recommended_skus": ["Boat BassHeads Wired Earphones", "AA Alkaline Battery 4-Pack"],
        "user_need": "High-urgency electronics accessories delivered in under 10 minutes"
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
    review_clusters = []

    for rev in reviews:
        text = rev.get("review_text", "").lower()
        
        # Classify Explicit Complaints
        matched_complaints = []
        for category, keywords in COMPLAINT_PATTERNS.items():
            if any(kw in text for kw in keywords):
                explicit_complaints[category] += 1
                matched_complaints.append(category)

        # Extract Implicit Habits
        matched_habits = []
        for habit, keywords in HABIT_PATTERNS.items():
            if any(kw in text for kw in keywords):
                implicit_habits[habit] += 1
                matched_habits.append(habit)

        review_clusters.append({
            "review_id": rev["review_id"],
            "source": rev["source"],
            "rating": rev["rating"],
            "user_segment": rev["user_segment"],
            "matched_complaints": matched_complaints,
            "matched_habits": matched_habits
        })

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
            "SILCE captures 2-item cart pairings (e.g. Tea + Biscuits, Nachos + Coke) to recommend 1 relevant non-grocery item "
            "(Tea Strainer, UNO Cards) under a 40% price guardrail, breaking category inertia without introducing cart friction."
        )
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(structured_output, f, indent=2)

    # Also save to root artifacts directory for Antigravity system
    root_artifact_path = Path("/Users/srikarvuyyuru/.gemini/antigravity-ide/brain/06c9bfb8-d75f-4460-a8a8-f26a037d355f/discovery_insights.json")
    try:
        with open(root_artifact_path, "w", encoding="utf-8") as f:
            json.dump(structured_output, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not copy to root artifacts path: {e}")

    logger.info(f"✨ Opportunity Discovery Pipeline successfully generated insights at {OUTPUT_FILE}")
    return structured_output

if __name__ == "__main__":
    run_discovery_pipeline()
