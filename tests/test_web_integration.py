"""Boot each server on an ephemeral port in a thread and hit a real endpoint."""
import http.client
import json
import threading
import yaml

from scripts import webserver, dashboard, viewer


def _serve_in_thread(route):
    server = webserver.make_server(route, 0)  # port 0 = ephemeral
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _get(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", path)
    resp = conn.getresponse()
    return resp.status, resp.read()


def test_dashboard_status_over_http(tmp_path, monkeypatch):
    from scripts import checks
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    w = tmp_path / "work" / "alpha"
    w.mkdir(parents=True)
    (w / "status.yaml").write_text(yaml.safe_dump({"work": "alpha", "stages": {}}), encoding="utf-8")
    server = _serve_in_thread(dashboard.make_route(tmp_path))
    try:
        status, body = _get(server.server_address[1], "/api/status")
        assert status == 200
        assert json.loads(body)["works"][0]["work"] == "alpha"
    finally:
        server.shutdown()


def test_viewer_works_over_http(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "alpha.html").write_text("<p data-page='1'>x</p>", encoding="utf-8")
    server = _serve_in_thread(viewer.make_route(tmp_path))
    try:
        status, body = _get(server.server_address[1], "/api/works")
        assert status == 200
        assert json.loads(body)[0]["name"] == "alpha"
    finally:
        server.shutdown()
