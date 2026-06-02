"""Setup dashboard web app: serves a static UI + a /api/status JSON endpoint.

Run:  python -m scripts.dashboard [port]   (default 8000)
"""
import sys
from pathlib import Path

from scripts.webserver import Response, file_response, json_response, serve
from scripts.dashboard_data import dashboard_state

ASSETS = Path(__file__).resolve().parent.parent / "dashboard"


def make_route(repo_root):
    repo_root = Path(repo_root)

    def route(method, path, body):
        clean = path.split("?")[0]
        if method == "GET" and clean == "/":
            return file_response(ASSETS / "index.html")
        if method == "GET" and clean in ("/app.js", "/style.css"):
            return file_response(ASSETS / clean.lstrip("/"))
        if method == "GET" and clean == "/api/status":
            return json_response(dashboard_state(repo_root))
        return Response(404, "text/plain", b"not found")

    return route


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    serve(make_route(Path.cwd()), port)
