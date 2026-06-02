from scripts import verify


def test_counts_tags():
    html = '<p data-page="1"><em>a</em></p><hr /><p id="x" data-page="2"><b>h</b></p>'
    c = verify.count_tags(html)
    assert c["p"] == 2
    assert c["hr"] == 1
    assert c["em"] == 1
    assert c["data_page"] == 2
    assert c["ids"] == {"x"}


def test_verify_pair_passes_on_matching(tmp_path):
    en = tmp_path / "w.html"
    la = tmp_path / "w_la.html"
    common = '<p data-page="1">x</p><hr /><p id="h" data-page="2"><b>H</b></p>'
    en.write_text(common, encoding="utf-8")
    la.write_text(common, encoding="utf-8")
    ok, problems = verify.verify_pair(en, la)
    assert ok is True
    assert problems == []


def test_verify_pair_flags_mismatch_and_missing_data_page(tmp_path):
    en = tmp_path / "w.html"
    la = tmp_path / "w_la.html"
    en.write_text('<p data-page="1">x</p><p data-page="2">y</p>', encoding="utf-8")
    la.write_text('<p data-page="1">x</p><p>y</p>', encoding="utf-8")  # one <p> missing data-page
    ok, problems = verify.verify_pair(en, la)
    assert ok is False
    assert any("data-page" in p for p in problems)
