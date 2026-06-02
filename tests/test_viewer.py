from scripts import viewer_data


def test_available_works_lists_english_with_latin_flag(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    (out / "alpha.html").write_text("<html></html>", encoding="utf-8")
    (out / "alpha_la.html").write_text("<html></html>", encoding="utf-8")
    (out / "beta.html").write_text("<html></html>", encoding="utf-8")  # no latin
    (out / "index.html").write_text("<html></html>", encoding="utf-8")  # skipped
    works = viewer_data.available_works(out)
    assert works == [
        {"name": "alpha", "has_latin": True},
        {"name": "beta", "has_latin": False},
    ]


def test_available_works_empty_when_no_output(tmp_path):
    assert viewer_data.available_works(tmp_path / "output") == []


import json as _json
from scripts import viewer, proofing


def _repo(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "alpha.html").write_text(
        '<p data-page="001">x</p>', encoding="utf-8")
    pages = tmp_path / "work" / "alpha" / "pages"
    pages.mkdir(parents=True)
    (pages / "page-001.png").write_bytes(b"\x89PNG")
    return tmp_path


def test_viewer_lists_works(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/api/works", b"")
    assert resp.status == 200
    assert _json.loads(resp.body) == [{"name": "alpha", "has_latin": False}]


def test_viewer_serves_output_html(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/output/alpha.html", b"")
    assert resp.status == 200
    assert b"data-page" in resp.body


def test_viewer_serves_page_image(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/pages/alpha/pages/page-001.png", b"")
    assert resp.status == 200
    assert resp.content_type == "image/png"


def test_viewer_rejects_path_traversal(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/output/../work/alpha/pages/page-001.png", b"")
    assert resp.status == 403


def test_viewer_flag_post_writes_note(tmp_path):
    repo = _repo(tmp_path)
    route = viewer.make_route(repo)
    body = _json.dumps({"work": "alpha", "page": "001", "block": 0, "note": "typo"}).encode()
    resp = route("POST", "/api/flag", body)
    assert resp.status == 200
    flags = proofing.load_flags(repo / "work" / "alpha")
    assert flags == [{"page": "001", "block": 0, "note": "typo"}]


def test_viewer_unknown_is_404(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    assert route("GET", "/nope", b"").status == 404


def test_viewer_index_served_after_assets_exist(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/", b"")
    assert resp.status == 200
    assert b"Proofreading" in resp.body
    assert b"app.js" in resp.body


def test_viewer_flag_rejects_traversal_work(tmp_path):
    repo = _repo(tmp_path)
    route = viewer.make_route(repo)
    body = _json.dumps({"work": "../../etc", "page": "001", "block": 0, "note": "x"}).encode()
    resp = route("POST", "/api/flag", body)
    assert resp.status == 400
    # nothing written outside the work tree
    assert not (tmp_path.parent / "proofing-notes.yaml").exists()


def test_viewer_flag_rejects_malformed_body(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    assert route("POST", "/api/flag", b"not json").status == 400
    assert route("POST", "/api/flag", b"{}").status == 400  # missing keys


def test_viewer_flag_still_works_for_valid_request(tmp_path):
    repo = _repo(tmp_path)
    route = viewer.make_route(repo)
    body = _json.dumps({"work": "alpha", "page": "001", "block": 0, "note": "typo"}).encode()
    resp = route("POST", "/api/flag", body)
    assert resp.status == 200
    assert proofing.load_flags(repo / "work" / "alpha") == [{"page": "001", "block": 0, "note": "typo"}]


def test_viewer_rejects_pages_traversal(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    assert route("GET", "/pages/../../etc/passwd", b"").status == 403
