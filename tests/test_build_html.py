from scripts import build_html


def test_kebab_id():
    assert build_html.kebab("CAPUT PRIMUM") == "caput-primum"
    assert build_html.kebab("On the  Work!") == "on-the-work"


def test_render_body_block_has_data_page_and_region():
    block = {"page": "001", "region": "q3_bottom_left", "type": "body",
             "english": "In the beginning.", "source": "In principio."}
    html = build_html.render_block(block, "english")
    assert html == '<p data-page="001" data-region="q3_bottom_left">In the beginning.</p>'


def test_render_body_block_without_region_omits_attr():
    block = {"page": "002", "type": "body", "english": "Text.", "source": "Textus."}
    assert build_html.render_block(block, "english") == '<p data-page="002">Text.</p>'


def test_render_scripture_is_emphasized():
    block = {"page": "002", "type": "scripture", "english": "Let there be light.", "source": "Fiat lux."}
    assert build_html.render_block(block, "source") == '<p data-page="002"><em>Fiat lux.</em></p>'


def test_render_heading_has_id_and_bold():
    block = {"page": "001", "type": "heading", "english": "Chapter One", "source": "CAPUT PRIMUM"}
    assert build_html.render_block(block, "english") == \
        '<p id="chapter-one" data-page="001"><b>Chapter One</b></p>'


def test_load_sections_sorted(work_dir):
    blocks = build_html.load_sections(work_dir / "translation")
    assert [b["page"] for b in blocks] == ["001", "001", "002"]


def test_build_body_puts_hr_before_headings_and_builds_toc(sample_section):
    body, toc = build_html.build_body(sample_section, "english")
    assert toc == [("chapter-one", "Chapter One")]
    # hr precedes the heading
    assert "<hr />\n<p id=\"chapter-one\"" in body
    # the scripture block is emphasized in the body
    assert "<em>Let there be light.</em>" in body


def test_build_work_writes_en_and_la(tmp_path, work_dir):
    out = tmp_path / "output"
    en, la = build_html.build_work(work_dir, "Sample Work", out)
    en_html = en.read_text(encoding="utf-8")
    la_html = la.read_text(encoding="utf-8")
    assert '<html lang="en">' in en_html
    assert '<html lang="la">' in la_html
    # English file uses english text; Latin file uses source text.
    assert "In the beginning God created." in en_html
    assert "In principio creavit Deus." in la_html
    # TOC anchor present in both.
    assert 'href="#chapter-one"' in en_html
    assert 'href="#chapter-one"' in la_html
    # Same number of data-page attributes in both (block parity).
    assert en_html.count("data-page=") == la_html.count("data-page=") == 3
