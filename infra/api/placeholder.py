from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        payload = json.dumps({"status": "ok", "service": "api-placeholder"}).encode()
        healthy = self.path in {"/health/live", "/health/ready"}
        self.send_response(200 if healthy else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if healthy:
            self.wfile.write(payload)

    def log_message(self, *_args: object) -> None:
        pass


HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
