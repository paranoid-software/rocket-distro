"""Minimal Zookeeper emulator: POST (any path) -> print body to stdout, return JSON {success: true}. No deps, stdlib only."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

PORT = 30079
SUCCESS_JSON = json.dumps({"success": True}).encode("utf-8")


class ZookeeperHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            print(body.decode("utf-8", errors="replace"), flush=True)
        except Exception:
            print(body, flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(SUCCESS_JSON))
        self.end_headers()
        self.wfile.write(SUCCESS_JSON)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("", PORT), ZookeeperHandler).serve_forever()
