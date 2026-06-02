"""Assemble translation sections into EN + LA HTML with proofreading markup."""
import html as html_lib
import json
import re
from pathlib import Path


def kebab(text):
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")


def _text(block, field):
    return html_lib.escape(block[field])


def render_block(block, field):
    """Render one translation block as a <p>, using the given field
    ('english' or 'source'). Adds data-page (always) and data-region (if present)."""
    attrs = f' data-page="{block["page"]}"'
    if block.get("region"):
        attrs += f' data-region="{block["region"]}"'
    text = _text(block, field)
    btype = block["type"]
    if btype == "heading":
        return f'<p id="{kebab(block["english"])}"{attrs}><b>{text}</b></p>'
    if btype in ("scripture", "footnote"):
        return f"<p{attrs}><em>{text}</em></p>"
    return f"<p{attrs}>{text}</p>"


def load_sections(translation_dir):
    """Load and concatenate all section-*.json arrays, in filename order."""
    blocks = []
    for path in sorted(Path(translation_dir).glob("section-*.json")):
        blocks.extend(json.loads(path.read_text(encoding="utf-8")))
    return blocks


def build_body(blocks, field):
    """Return (body_html, toc) where toc is a list of (id, title)."""
    parts, toc = [], []
    for block in blocks:
        if block["type"] == "heading":
            parts.append("<hr />")
            toc.append((kebab(block["english"]), block[field]))
        parts.append(render_block(block, field))
    return "\n".join(parts), toc


_DOC = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
<h1>{title}</h1>
<hr />
<h2>{toc_label}</h2>
<ul>
{toc}
</ul>
{body}
</body>
</html>
"""


def _toc_html(toc):
    return "\n".join(f'<li><a href="#{i}">{html_lib.escape(t)}</a></li>' for i, t in toc)


def render_document(blocks, title, field, lang, toc_label):
    body, toc = build_body(blocks, field)
    return _DOC.format(lang=lang, title=html_lib.escape(title),
                       toc_label=toc_label, toc=_toc_html(toc), body=body)


def build_work(work_dir, title, out_dir):
    """Write <work>.html (EN) and <work>_la.html (LA); return both paths."""
    work_dir, out_dir = Path(work_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    blocks = load_sections(work_dir / "translation")
    name = work_dir.name
    en_path = out_dir / f"{name}.html"
    la_path = out_dir / f"{name}_la.html"
    en_path.write_text(
        render_document(blocks, title, "english", "en", "Table of Contents"),
        encoding="utf-8")
    la_path.write_text(
        render_document(blocks, title, "source", "la", "Index"),
        encoding="utf-8")
    return en_path, la_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("usage: python -m scripts.build_html <work-dir> <title> <out-dir>")
        sys.exit(1)
    en, la = build_work(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"wrote {en} and {la}")
