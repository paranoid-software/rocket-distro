"""Minimal Logy emulator: POST /messages -> print body to stdout. No deps, stdlib only."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

PORT = 30077


class LogyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") != "/messages":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            print(body.decode("utf-8", errors="replace"), flush=True)
        except Exception:
            print(body, flush=True)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("", PORT), LogyHandler).serve_forever()
