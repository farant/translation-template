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
        return f'<p id="{kebab(block[field])}"{attrs}><b>{text}</b></p>'
    if btype in ("scripture", "footnote"):
        return f"<p{attrs}><em>{text}</em></p>"
    return f"<p{attrs}>{text}</p>"
