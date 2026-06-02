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
