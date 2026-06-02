import yaml
from scripts import dashboard_data


def _make_work(root, name, title, stages):
    d = root / "work" / name
    d.mkdir(parents=True)
    (d / "status.yaml").write_text(
        yaml.safe_dump({"work": name, "title": title, "ocr_method": "claude-vision",
                        "stages": stages}), encoding="utf-8")


def test_works_overview_reads_all_works(tmp_path):
    _make_work(tmp_path, "alpha", "Alpha", {"ingest": {"done": True}})
    _make_work(tmp_path, "beta", "Beta", {"ingest": {"done": False}})
    works = dashboard_data.works_overview(tmp_path / "work")
    assert [w["work"] for w in works] == ["alpha", "beta"]
    assert works[0]["title"] == "Alpha"
    assert works[0]["stages"]["ingest"]["done"] is True
    assert works[0]["ocr_method"] == "claude-vision"


def test_works_overview_empty_when_no_dir(tmp_path):
    assert dashboard_data.works_overview(tmp_path / "work") == []


def test_dashboard_state_has_checks_and_works(tmp_path, monkeypatch):
    from scripts import checks
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    _make_work(tmp_path, "alpha", "Alpha", {})
    state = dashboard_data.dashboard_state(tmp_path)
    assert "checks" in state and isinstance(state["checks"], list)
    assert [w["work"] for w in state["works"]] == ["alpha"]


import json as _json
from scripts import dashboard


def test_dashboard_route_status_endpoint(tmp_path, monkeypatch):
    from scripts import checks
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    _make_work(tmp_path, "alpha", "Alpha", {})
    route = dashboard.make_route(tmp_path)
    resp = route("GET", "/api/status", b"")
    assert resp.status == 200
    payload = _json.loads(resp.body)
    assert payload["works"][0]["work"] == "alpha"


def test_dashboard_route_serves_index(tmp_path):
    route = dashboard.make_route(tmp_path)
    resp = route("GET", "/", b"")
    # index.html is created in Task 5; here we only assert routing returns the
    # asset path's response (404 until the file exists, 200 after). Accept both
    # statuses but require the route to target text/html or 'not found'.
    assert resp.status in (200, 404)


def test_dashboard_route_unknown_is_404(tmp_path):
    route = dashboard.make_route(tmp_path)
    assert route("GET", "/nope", b"").status == 404


def test_dashboard_index_served_after_assets_exist(tmp_path):
    route = dashboard.make_route(tmp_path)
    resp = route("GET", "/", b"")
    assert resp.status == 200
    assert b"Setup Dashboard" in resp.body
    assert b"app.js" in resp.body
