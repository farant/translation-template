from scripts import webserver


def test_json_response_encodes_body_and_type():
    r = webserver.json_response({"a": 1})
    assert r.status == 200
    assert r.content_type == "application/json"
    assert r.body == b'{"a": 1}'


def test_safe_join_allows_inside(tmp_path):
    (tmp_path / "sub").mkdir()
    target = webserver.safe_join(tmp_path, "sub/file.png")
    assert target == (tmp_path / "sub" / "file.png").resolve()


def test_safe_join_rejects_traversal(tmp_path):
    assert webserver.safe_join(tmp_path, "../../etc/passwd") is None
    assert webserver.safe_join(tmp_path, "/etc/passwd") is None


def test_file_response_serves_known_type(tmp_path):
    f = tmp_path / "page.png"
    f.write_bytes(b"\x89PNG")
    r = webserver.file_response(f)
    assert r.status == 200
    assert r.content_type == "image/png"
    assert r.body == b"\x89PNG"


def test_file_response_missing_is_404(tmp_path):
    r = webserver.file_response(tmp_path / "nope.html")
    assert r.status == 404
