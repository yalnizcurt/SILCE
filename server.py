import os
import json
import logging
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

from engine.recommender import generate_recommendation
from engine.feedback_logger import log_event, get_analytics_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SILCE.Server")

PORT = int(os.getenv("PORT", 8080))
BASE_DIR = Path(__file__).parent.resolve()

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

class SILCERequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path_clean = path.split('?')[0].split('#')[0]
        if path_clean == "/" or path_clean == "/index.html":
            return str(BASE_DIR / "static" / "index.html")
        elif path_clean.startswith("/static/"):
            rel_path = path_clean[len("/static/"):]
            return str(BASE_DIR / "static" / rel_path)
        return super().translate_path(path_clean)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/personas":
            self.send_json_response(PERSONAS)
            return
        elif self.path == "/api/catalog":
            self.send_json_response(CATALOG)
            return
        elif self.path == "/api/analytics":
            summary = get_analytics_summary()
            self.send_json_response(summary)
            return

        return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            try:
                body_bytes = self.rfile.read(content_length)
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                logger.warning(f"Error parsing POST payload: {e}")

        if self.path == "/api/recommend":
            cart_items = body.get("cart_items", [])
            user_id = body.get("user_id", "user_groceries_only")

            # Find matching persona
            user_persona = next((p for p in PERSONAS if p["user_id"] == user_id), PERSONAS[0] if PERSONAS else {})

            # Generate SILCE single recommendation
            result = generate_recommendation(cart_items, user_persona, CATALOG)

            # Log impression if recommendation was generated
            if result.get("has_recommendation"):
                log_event("impression", {
                    "user_id": user_id,
                    "product_id": result["product"]["id"],
                    "category": result["new_category"],
                    "intent": result["intent_inferred"]
                })

            self.send_json_response(result)
            return

        elif self.path == "/api/action":
            action_type = body.get("action", "accept") # accept / dismiss / checkout
            data = body.get("data", {})
            updated_analytics = log_event(action_type, data)
            self.send_json_response({"status": "success", "analytics": updated_analytics})
            return

        self.send_error(404, "Endpoint not found")

    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def run_server():
    global PORT
    for try_port in [8080, 8085, 8088, 8090, 8099]:
        try:
            server_address = ('', try_port)
            HTTPServer.allow_reuse_address = True
            httpd = HTTPServer(server_address, SILCERequestHandler)
            PORT = try_port
            logger.info(f"⚡ SILCE (Semantic Intent & Life Context Engine) running on http://localhost:{PORT}")
            httpd.serve_forever()
            break
        except OSError as e:
            if e.errno == 48:
                logger.info(f"Port {try_port} in use, trying next port...")
                continue
            else:
                raise e

if __name__ == "__main__":
    run_server()
