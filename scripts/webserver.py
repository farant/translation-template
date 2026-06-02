"""Shared HTTP plumbing for the dashboard and viewer apps.

Each app supplies a pure ``route(method, path, body) -> Response`` function;
this module adapts it onto stdlib http.server. Keeping routing pure makes it
unit-testable without sockets.
"""
import http.server
import json
from collections import namedtuple
from pathlib import Path

Response = namedtuple("Response", "status content_type body")  # body is bytes

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".json": "application/json",
}


def json_response(obj, status=200):
    return Response(status, "application/json", json.dumps(obj).encode("utf-8"))


def safe_join(base, rel):
    """Resolve ``rel`` under ``base``; return the Path only if it stays inside
    ``base`` (defends against ../ traversal and absolute paths). Else None."""
    # Reject absolute paths outright
    if Path(rel).is_absolute():
        return None
    base = Path(base).resolve()
    target = (base / rel).resolve()
    if target == base or base in target.parents:
        return target
    return None


def file_response(path):
    path = Path(path)
    if not path.is_file():
        return Response(404, "text/plain", b"not found")
    ctype = CONTENT_TYPES.get(path.suffix, "application/octet-stream")
    return Response(200, ctype, path.read_bytes())


def make_handler(route_fn):
    class Handler(http.server.BaseHTTPRequestHandler):
        def _dispatch(self, method):
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length else b""
            resp = route_fn(method, self.path, body)
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.content_type)
            self.send_header("Content-Length", str(len(resp.body)))
            self.end_headers()
            self.wfile.write(resp.body)

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def log_message(self, *args):
            pass  # quiet

    return Handler


def make_server(route_fn, port):
    """Build (but don't start) an HTTPServer bound to 127.0.0.1:port.
    Port 0 picks an ephemeral port (server.server_address[1] reveals it)."""
    return http.server.HTTPServer(("127.0.0.1", port), make_handler(route_fn))


def serve(route_fn, port):
    server = make_server(route_fn, port)
    print(f"Serving on http://127.0.0.1:{server.server_address[1]}  (Ctrl-C to stop)")
    server.serve_forever()
