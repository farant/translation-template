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
