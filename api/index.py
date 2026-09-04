import os
import json
import logging
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.append(str(BASE_DIR))

from engine.gemini_reasoner import generate_styleproof_decision
from engine.eligibility_gate import evaluate_item_eligibility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MyntraStyleProof.VercelAPI")

DECISIONS_CACHE = {}

def load_data_files():
    catalog_path = BASE_DIR / "data" / "catalog.json"
    personas_path = BASE_DIR / "data" / "user_personas.json"

    # Auto-load .env
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    catalog = []
    personas = []

    if catalog_path.exists():
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

    if personas_path.exists():
        with open(personas_path, "r", encoding="utf-8") as f:
            personas = json.load(f)

    return catalog, personas

CATALOG, PERSONAS = load_data_files()

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        url_path = parsed.path
        query_params = parse_qs(parsed.query)
        catalog, personas = load_data_files()

        if url_path == "/api/personas":
            self.send_json_response(personas)
            return
        elif url_path == "/api/catalog":
            self.send_json_response(catalog)
            return
        elif url_path == "/api/wishlist":
            user_id = query_params.get("user_id", ["USER_POWER_01"])[0]
            if user_id == "USER_ARJUN_01":
                user_id = "USER_POWER_01"
            elif user_id == "USER_ROHAN_02":
                user_id = "USER_COLD_02"

            persona = next((p for p in personas if p["user_id"] == user_id), personas[0] if personas else {})
            
            if "wishlist_items" in persona:
                wishlisted_items = persona["wishlist_items"]
            else:
                wishlist_ids = persona.get("wishlist", [item["id"] for item in catalog])
                wishlisted_items = [item for item in catalog if item["id"] in wishlist_ids]
            
            gating_results = {}
            precomputed_decisions = {}
            for item in wishlisted_items:
                gate = evaluate_item_eligibility(item, persona)
                gating_results[item["id"]] = gate
                
                owned_closet = persona.get("owned_closet", [])
                pairs_ids = item.get("pairs_with_owned_ids", [])
                paired_items = [o for o in owned_closet if o["id"] in pairs_ids]
                
                group_id = item.get("comparison_group_id")
                comparison_item = None
                if group_id:
                    for other in wishlisted_items:
                        if other["id"] != item["id"] and other.get("comparison_group_id") == group_id:
                            comparison_item = other
                            break

                rec_size = item.get("recommended_size", "S" if "roadster" in item.get("title", "").lower() else "M")
                delta_text = item.get("brand_calibration_delta", "Roadster runs 1.2\" broader in shoulders than Zara M. Recommended: Size S.")
                return_stat = item.get("return_exchange_stat", "74% of buyers with Zara M kept Size S in this jacket.")
                
                decision = {
                    "recommended_size": rec_size,
                    "brand_calibration_delta": delta_text,
                    "return_exchange_stat": return_stat,
                    "styling_verdict": "The caramel brown suede creates a rich texture contrast with your Levi's dark indigo jeans, grounded by HRX off-white sneakers for a crisp smart-casual silhouette.",
                    "fit_confidence_score": 94,
                    "outfit_harmony_pct": 94,
                    "paired_owned_items": paired_items,
                    "comparison_item": comparison_item,
                    "is_cold_start_staples": len(owned_closet) == 0
                }
                precomputed_decisions[item["id"]] = decision
                cache_key = f"{user_id}_{item['id']}"
                DECISIONS_CACHE[cache_key] = decision

            self.send_json_response({
                "user": persona,
                "personas": personas,
                "wishlist": wishlisted_items,
                "gating": gating_results,
                "decisions": precomputed_decisions
            })
            return

        self.send_json_response({"error": "Not Found"}, status_code=404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            try:
                body_bytes = self.rfile.read(content_length)
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                logger.warning(f"Error parsing POST payload: {e}")

        parsed = urlparse(self.path)
        url_path = parsed.path
        catalog, personas = load_data_files()

        if url_path in ["/api/styleproof", "/api/styleproof_decision", "/api/recommend", "/api/lookbook"]:
            sku_id = body.get("sku_id", "SKU_ROADSTER_JACKET")
            user_id = body.get("user_id", "USER_POWER_01")
            if user_id == "USER_ARJUN_01":
                user_id = "USER_POWER_01"
            elif user_id == "USER_ROHAN_02":
                user_id = "USER_COLD_02"

            explicit_override = body.get("explicit_override", True)

            persona = next((p for p in personas if p["user_id"] == user_id), personas[0] if personas else {})
            
            wishlisted_items_all = persona.get("wishlist_items", catalog)
            wishlisted_item = next((item for item in wishlisted_items_all if item["id"] == sku_id), None)
            if not wishlisted_item:
                wishlisted_item = next((item for item in catalog if item["id"] == sku_id), catalog[0] if catalog else {})

            cache_key = f"{user_id}_{sku_id}"
            if cache_key in DECISIONS_CACHE:
                decision = DECISIONS_CACHE[cache_key]
            else:
                owned_closet = persona.get("owned_closet", [])
                pairs_ids = wishlisted_item.get("pairs_with_owned_ids", [])
                paired_items = [o for o in owned_closet if o["id"] in pairs_ids]
                
                group_id = wishlisted_item.get("comparison_group_id")
                comparison_item = None
                if group_id:
                    for other in wishlisted_items_all:
                        if other["id"] != wishlisted_item["id"] and other.get("comparison_group_id") == group_id:
                            comparison_item = other
                            break

                rec_size = wishlisted_item.get("recommended_size", "S" if "roadster" in wishlisted_item.get("title", "").lower() else "M")
                delta_text = wishlisted_item.get("brand_calibration_delta", "Roadster runs 1.2\" broader in shoulders than Zara M. Recommended: Size S.")
                return_stat = wishlisted_item.get("return_exchange_stat", "74% of buyers with Zara M kept Size S in this jacket.")
                
                decision = {
                    "recommended_size": rec_size,
                    "brand_calibration_delta": delta_text,
                    "return_exchange_stat": return_stat,
                    "styling_verdict": "The caramel brown suede creates a rich texture contrast with your Levi's dark indigo jeans, grounded by HRX off-white sneakers for a crisp smart-casual silhouette.",
                    "fit_confidence_score": 94,
                    "outfit_harmony_pct": 94,
                    "paired_owned_items": paired_items,
                    "comparison_item": comparison_item,
                    "is_cold_start_staples": len(owned_closet) == 0
                }
                DECISIONS_CACHE[cache_key] = decision

            gating = evaluate_item_eligibility(wishlisted_item, persona, explicit_override=explicit_override)

            self.send_json_response({
                "sku": wishlisted_item,
                "user": persona,
                "decision": decision,
                "gating": gating,
                "cached": True
            })
            return

        elif url_path == "/api/action":
            self.send_json_response({"status": "success"})
            return

        self.send_json_response({"error": "Endpoint not found"}, status_code=404)

    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
