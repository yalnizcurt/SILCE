import os
import json
import logging
from pathlib import Path
from http.server import BaseHTTPRequestHandler

# Import SILCE engine modules
import sys
BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.append(str(BASE_DIR))

from engine.recommender import generate_recommendation
from engine.feedback_logger import log_event, get_analytics_summary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SILCE.VercelAPI")

def load_data_files():
    catalog_path = BASE_DIR / "data" / "catalog.json"
    personas_path = BASE_DIR / "data" / "user_personas.json"

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
        url_path = self.path.split("?")[0]

        if url_path == "/api/personas":
            self.send_json_response(PERSONAS)
            return
        elif url_path == "/api/catalog":
            self.send_json_response(CATALOG)
            return
        elif url_path == "/api/analytics":
            summary = get_analytics_summary()
            self.send_json_response(summary)
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

        url_path = self.path.split("?")[0]

        if url_path == "/api/recommend":
            cart_items = body.get("cart_items", [])
            user_id = body.get("user_id", "user_groceries_only")

            user_persona = next((p for p in PERSONAS if p["user_id"] == user_id), PERSONAS[0] if PERSONAS else {})
            result = generate_recommendation(cart_items, user_persona, CATALOG)

            if result.get("has_recommendation"):
                log_event("impression", {
                    "user_id": user_id,
                    "product_id": result["product"]["id"],
                    "category": result["new_category"],
                    "intent": result["intent_inferred"]
                })

            self.send_json_response(result)
            return

        elif url_path == "/api/action":
            action_type = body.get("action", "accept")
            data = body.get("data", {})
            updated_analytics = log_event(action_type, data)
            self.send_json_response({"status": "success", "analytics": updated_analytics})
            return

        self.send_json_response({"error": "Endpoint not found"}, status_code=404)

    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
