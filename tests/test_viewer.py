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
