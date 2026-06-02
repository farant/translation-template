"""Proofreading viewer web app: generated HTML beside the source scan, with
one-click flagging.

Routes:
  GET  /                       -> viewer UI
  GET  /app.js, /style.css     -> UI assets
  GET  /api/works              -> [{name, has_latin}]
  GET  /output/<file>          -> a built HTML file (EN or LA)
  GET  /pages/<work>/pages/<f> -> a source page PNG
  POST /api/flag               -> append {work, page, block, note} to proofing-notes.yaml

Run:  python -m scripts.viewer [port]   (default 8001)
"""
import json
import sys
from pathlib import Path

from scripts.webserver import Response, file_response, json_response, safe_join, serve
from scripts.viewer_data import available_works
from scripts.proofing import add_flag

ASSETS = Path(__file__).resolve().parent.parent / "viewer"


def make_route(repo_root):
    repo_root = Path(repo_root)
    output_dir = repo_root / "output"
    work_dir = repo_root / "work"

    def route(method, path, body):
        clean = path.split("?")[0]
        if method == "GET" and clean == "/":
            return file_response(ASSETS / "index.html")
        if method == "GET" and clean in ("/app.js", "/style.css"):
            return file_response(ASSETS / clean.lstrip("/"))
        if method == "GET" and clean == "/api/works":
            return json_response(available_works(output_dir))
        if method == "GET" and clean.startswith("/output/"):
            target = safe_join(output_dir, clean[len("/output/"):])
            return file_response(target) if target else Response(403, "text/plain", b"forbidden")
        if method == "GET" and clean.startswith("/pages/"):
            target = safe_join(work_dir, clean[len("/pages/"):])
            return file_response(target) if target else Response(403, "text/plain", b"forbidden")
        if method == "POST" and clean == "/api/flag":
            try:
                data = json.loads(body or b"{}")
                safe_work = safe_join(work_dir, data["work"])
                if safe_work is None:
                    return Response(400, "text/plain", b"invalid work")
                add_flag(safe_work, data["page"], data["block"], data["note"])
            except (json.JSONDecodeError, KeyError, TypeError):
                return Response(400, "text/plain", b"invalid request")
            return json_response({"ok": True})
        return Response(404, "text/plain", b"not found")

    return route


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    serve(make_route(Path.cwd()), port)
