"""A small HTTP service with deterministic health and log fixtures."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


def route(path):
    if urlsplit(path).path == "/health":
        return 200, {"status": "ok", "service": "qa-demo"}
    return 404, {"error": "not_found"}


def emit(level, event):
    print(json.dumps({"level": level, "event": event}), flush=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, payload = route(self.path)
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        # Keep request metadata out of the synthetic fixture logs.
        pass


if __name__ == "__main__":
    with ThreadingHTTPServer(("0.0.0.0", 8080), Handler) as server:
        emit("INFO", "demo_ready")
        if os.getenv("DEMO_EMIT_ERROR") == "1":
            emit("ERROR", "intentional_test_fixture")
        server.serve_forever()
