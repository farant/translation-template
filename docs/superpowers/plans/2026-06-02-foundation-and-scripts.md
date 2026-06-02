# Foundation & Helper Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the mechanical core of the translation template — config/status modules, page extraction, page cropping, HTML assembly (with proofreading markup), and an EN/LA verify script — all unit-tested against a small fixture, with no Claude/agent layer required.

**Architecture:** Plain Python 3 modules under `scripts/`, each with one responsibility and a thin `if __name__ == "__main__"` CLI. Heavy/judgment logic (transcription, translation, skills, web apps) is out of scope — those are later plans. The judgment steps produce on-disk data files in documented formats; the scripts here are pure-ish transformers over those files plus PDFs/images, so they can be tested deterministically. PIL/Pillow does image work in-process (so split/crop logic is testable without external binaries); `pdftoppm` is shelled out only in the thin CLI wrapper.

**Tech Stack:** Python 3.11+, `pytest`, `PyYAML`, `Pillow`. External runtime tools (invoked only by CLI wrappers, not unit tests): `pdftoppm` (poppler). Package manager: `uv` (with `pip` fallback documented).

---

## Data formats (referenced by multiple tasks)

**`project.yaml`** (per-project config, repo root):
```yaml
work_defaults:
  source_language: la            # "la" or "grc"
  transcription_mode: normalize  # "normalize" or "diplomatic"
  bible_reference_style: douay-rheims
  heading_format: "Chapter {n}: {title}"
translation:
  exclude_editorial_apparatus: true
  target_register: formal
html:
  simple_tags_only: true
```

**`work/<name>/status.yaml`** (per-work state):
```yaml
work: sample-work
title: "Sample Work"
source_pdf: source/sample.pdf
ocr_method: claude-vision
template_detached: false
stages:
  ingest:     { done: false }
  transcribe: { done: false }
  translate:  { done: false }
  build_html: { done: false }
  publish:    { done: false }
```

**`work/<name>/translation/section-NN.json`** (one array per section; carries BOTH source and english so `build_html` can emit both EN and LA from a single source of truth):
```json
[
  { "page": "001", "region": "q1_top_left", "type": "heading", "source": "CAPUT PRIMUM", "english": "Chapter One", "notes": [] },
  { "page": "001", "region": "q3_bottom_left", "type": "body", "source": "In principio...", "english": "In the beginning...", "notes": [] },
  { "page": "002", "type": "scripture", "source": "Fiat lux.", "english": "Let there be light.", "notes": [] },
  { "page": "002", "type": "footnote", "source": "Vide Augustinum.", "english": "See Augustine.", "notes": [{ "type": "uncertain", "text": "faded" }] }
]
```
- `type` ∈ `heading | body | scripture | footnote | marginal_note`.
- `region` is optional (best-effort crop anchor). `page` is always a zero-padded string.

**HTML output contract** (what `build_html` emits, what `verify` checks):
- Each block → one `<p>` carrying `data-page` (always) and `data-region` (when present).
- `heading` → `<p id="{kebab-id}" data-page="..."><b>{text}</b></p>`, preceded by `<hr />`.
- `scripture` and `footnote` text wrapped in `<em>`.
- A Table of Contents `<ul>` built from headings, each `<li><a href="#{kebab-id}">{text}</a></li>`.
- EN file uses the `english` field + `<html lang="en">`; LA file uses the `source` field + `<html lang="la">`. Same block count, same ids.

---

## File structure

- Create: `pyproject.toml` — Python project + deps + pytest config.
- Create: `scripts/__init__.py` — marks `scripts` importable as a package.
- Create: `scripts/config.py` — load/validate `project.yaml`, read/update `status.yaml`.
- Create: `scripts/imaging.py` — pure PIL helpers: book-spread split, quarter/half crops.
- Create: `scripts/extract_pages.py` — CLI: PDF → `pages/page-NNN.png` (uses poppler + `imaging.split_spread`).
- Create: `scripts/crop_page.py` — CLI: page PNG → crops in a target dir (uses `imaging.crops`).
- Create: `scripts/build_html.py` — translation sections → EN + LA HTML with proofreading markup + TOC.
- Create: `scripts/verify.py` — structural parity check EN vs LA + `data-page` presence.
- Create: `tests/conftest.py` — shared fixtures (sample PIL image, sample translation section, tmp work dir).
- Create: `tests/test_config.py`, `tests/test_imaging.py`, `tests/test_build_html.py`, `tests/test_verify.py`.
- Create: `.gitignore`, `README.md` (skeleton), `CLAUDE.md` (skeleton), `project.yaml`, `work/sample-work/status.yaml`.

---

### Task 1: Python project setup

**Files:**
- Create: `pyproject.toml`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "translation-template"
version = "0.1.0"
description = "Claude-driven template for Catholic Latin/Greek to English translation"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6.0", "Pillow>=10.0"]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create package markers**

`scripts/__init__.py` (empty file):
```python
```

`tests/__init__.py` (empty file):
```python
```

- [ ] **Step 3: Install deps and verify pytest runs**

Run: `uv sync && uv run pytest -q`
(Fallback if no `uv`: `python3 -m venv .venv && .venv/bin/pip install -e . pytest && .venv/bin/pytest -q`)
Expected: pytest runs and reports "no tests ran" (exit cleanly).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml scripts/__init__.py tests/__init__.py
git commit -m "chore: python project scaffold"
```

---

### Task 2: Config & status module

**Files:**
- Create: `scripts/config.py`
- Test: `tests/test_config.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write shared fixtures in `tests/conftest.py`**

```python
import json
from pathlib import Path
import pytest
from PIL import Image


@pytest.fixture
def sample_image():
    # 1200x900 white image with a black left half, so split halves differ.
    img = Image.new("RGB", (1200, 900), "white")
    for x in range(600):
        for y in range(0, 900, 10):
            img.putpixel((x, y), (0, 0, 0))
    return img


@pytest.fixture
def sample_section():
    return [
        {"page": "001", "region": "q1_top_left", "type": "heading",
         "source": "CAPUT PRIMUM", "english": "Chapter One", "notes": []},
        {"page": "001", "region": "q3_bottom_left", "type": "body",
         "source": "In principio creavit Deus.", "english": "In the beginning God created.", "notes": []},
        {"page": "002", "type": "scripture",
         "source": "Fiat lux.", "english": "Let there be light.", "notes": []},
    ]


@pytest.fixture
def work_dir(tmp_path, sample_section):
    work = tmp_path / "work" / "sample-work"
    (work / "translation").mkdir(parents=True)
    (work / "translation" / "section-01.json").write_text(
        json.dumps(sample_section), encoding="utf-8")
    return work
```

- [ ] **Step 2: Write the failing test for config loading**

`tests/test_config.py`:
```python
import yaml
from scripts import config


def test_load_project_defaults(tmp_path):
    (tmp_path / "project.yaml").write_text(
        "work_defaults:\n  source_language: la\n  transcription_mode: normalize\n",
        encoding="utf-8")
    cfg = config.load_project(tmp_path)
    assert cfg["work_defaults"]["source_language"] == "la"
    assert cfg["work_defaults"]["transcription_mode"] == "normalize"


def test_update_status_roundtrip(tmp_path):
    status_path = tmp_path / "status.yaml"
    status_path.write_text(
        yaml.safe_dump({"work": "w", "stages": {"ingest": {"done": False}}}),
        encoding="utf-8")
    config.update_status(status_path, ["stages", "ingest", "done"], True)
    reloaded = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    assert reloaded["stages"]["ingest"]["done"] is True
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: module 'scripts.config' has no attribute 'load_project'`.

- [ ] **Step 4: Write `scripts/config.py`**

```python
"""Load project config and read/update per-work status files."""
from pathlib import Path
import yaml


def load_project(root):
    """Load project.yaml from the given project root directory."""
    path = Path(root) / "project.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_status(status_path):
    with open(status_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def update_status(status_path, key_path, value):
    """Set a nested key (list of keys) in a status.yaml file and write it back."""
    data = load_status(status_path)
    node = data
    for key in key_path[:-1]:
        node = node.setdefault(key, {})
    node[key_path[-1]] = value
    with open(status_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return data
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add scripts/config.py tests/test_config.py tests/conftest.py
git commit -m "feat: config and status module"
```

---

### Task 3: Imaging helpers (split + crop)

**Files:**
- Create: `scripts/imaging.py`
- Test: `tests/test_imaging.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_imaging.py`:
```python
from scripts import imaging


def test_split_spread_returns_left_then_right(sample_image):
    left, right = imaging.split_spread(sample_image)
    assert left.size == (600, 900)
    assert right.size == (600, 900)
    # Left half has the black pattern; right half is pure white.
    assert left.getpixel((0, 0)) == (0, 0, 0)
    assert right.getpixel((0, 0)) == (255, 255, 255)


def test_crops_produces_eight_named_regions(sample_image):
    crops = imaging.crops(sample_image)
    assert set(crops.keys()) == {
        "q1_top_left", "q2_top_right", "q3_bottom_left", "q4_bottom_right",
        "top", "bottom", "left", "right",
    }
    # Quarters are native-resolution exact halves of each dimension.
    assert crops["q1_top_left"].size == (600, 450)
    # Halves cover a full dimension.
    assert crops["left"].size[1] == 900
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_imaging.py -v`
Expected: FAIL — `ModuleNotFoundError`/`AttributeError` for `imaging.split_spread`.

- [ ] **Step 3: Write `scripts/imaging.py`**

```python
"""Pure PIL helpers for splitting book-spread scans and cropping pages.

These operate on PIL.Image objects so they are unit-testable without any
external binaries. CLI wrappers (extract_pages, crop_page) call into these.
"""


def split_spread(image):
    """Split a two-page book-spread image into (left_page, right_page)."""
    w, h = image.size
    mid = w // 2
    left = image.crop((0, 0, mid, h))
    right = image.crop((mid, 0, w, h))
    return left, right


def crops(image):
    """Return 8 named crops: 4 native-resolution quarters + 4 halves.

    Quarters are best for dense body text/footnotes; halves give context
    that crosses quarter boundaries. Mirrors the baronius crop_page technique.
    """
    w, h = image.size
    mx, my = w // 2, h // 2
    return {
        "q1_top_left": image.crop((0, 0, mx, my)),
        "q2_top_right": image.crop((mx, 0, w, my)),
        "q3_bottom_left": image.crop((0, my, mx, h)),
        "q4_bottom_right": image.crop((mx, my, w, h)),
        "top": image.crop((0, 0, w, my)),
        "bottom": image.crop((0, my, w, h)),
        "left": image.crop((0, 0, mx, h)),
        "right": image.crop((mx, 0, w, h)),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_imaging.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/imaging.py tests/test_imaging.py
git commit -m "feat: imaging split and crop helpers"
```

---

### Task 4: `crop_page.py` CLI wrapper

**Files:**
- Create: `scripts/crop_page.py`
- Test: `tests/test_imaging.py` (add one test)

- [ ] **Step 1: Add a failing test for the file-writing wrapper**

Append to `tests/test_imaging.py`:
```python
from pathlib import Path
from scripts import crop_page
from PIL import Image


def test_write_crops_creates_eight_files(tmp_path, sample_image):
    src = tmp_path / "page-001.png"
    sample_image.save(src)
    out = tmp_path / "crops"
    written = crop_page.write_crops(src, out)
    assert len(written) == 8
    for p in written:
        assert Path(p).exists()
    assert (out / "page-001_q1_top_left.png").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_imaging.py::test_write_crops_creates_eight_files -v`
Expected: FAIL — `ModuleNotFoundError: scripts.crop_page`.

- [ ] **Step 3: Write `scripts/crop_page.py`**

```python
"""CLI: crop a page PNG into quarters + halves for Claude-vision reading."""
import sys
from pathlib import Path
from PIL import Image
from scripts import imaging


def write_crops(src_png, out_dir):
    """Write the 8 crops of src_png into out_dir; return list of paths."""
    src_png = Path(src_png)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    image = Image.open(src_png)
    stem = src_png.stem
    written = []
    for name, crop in imaging.crops(image).items():
        dest = out_dir / f"{stem}_{name}.png"
        crop.save(dest)
        written.append(str(dest))
    return written


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m scripts.crop_page <page.png> <out-dir>")
        sys.exit(1)
    paths = write_crops(sys.argv[1], sys.argv[2])
    print(f"wrote {len(paths)} crops to {sys.argv[2]}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_imaging.py::test_write_crops_creates_eight_files -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/crop_page.py tests/test_imaging.py
git commit -m "feat: crop_page CLI wrapper"
```

---

### Task 5: `extract_pages.py` CLI wrapper

**Files:**
- Create: `scripts/extract_pages.py`
- Test: `tests/test_imaging.py` (add one test for the spread-splitting file step)

This task wraps `pdftoppm` (shelled out, not unit-tested) but the testable part — splitting already-rendered page PNGs when `--spread` is set — is covered.

- [ ] **Step 1: Add a failing test for spread-splitting of rendered pages**

Append to `tests/test_imaging.py`:
```python
from scripts import extract_pages


def test_split_rendered_spreads(tmp_path, sample_image):
    raw = tmp_path / "raw"
    raw.mkdir()
    sample_image.save(raw / "page-1.png")  # one spread = two pages
    out = tmp_path / "pages"
    result = extract_pages.split_rendered(raw, out)
    # One spread -> page-001.png (left) and page-002.png (right)
    assert (out / "page-001.png").exists()
    assert (out / "page-002.png").exists()
    assert result == [str(out / "page-001.png"), str(out / "page-002.png")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_imaging.py::test_split_rendered_spreads -v`
Expected: FAIL — `ModuleNotFoundError: scripts.extract_pages`.

- [ ] **Step 3: Write `scripts/extract_pages.py`**

```python
"""CLI: PDF -> pages/page-NNN.png at 300dpi.

For normal single-page PDFs, each rendered page is kept as-is.
For book-spread scans (--spread), each rendered page is split left/right.
pdftoppm (poppler) is required at runtime; the split step is pure PIL.
"""
import subprocess
import sys
from pathlib import Path
from PIL import Image
from scripts import imaging


def render_pdf(pdf_path, raw_dir, dpi=300):
    """Render every PDF page to raw_dir/page-N.png via pdftoppm."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-r", str(dpi), "-png", str(pdf_path), str(raw_dir / "page")],
        check=True)
    return sorted(raw_dir.glob("page-*.png"))


def _renumber(out_dir, index, image):
    dest = out_dir / f"page-{index:03d}.png"
    image.save(dest)
    return str(dest)


def split_rendered(raw_dir, out_dir):
    """Split each rendered spread in raw_dir into two pages in out_dir."""
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written, index = [], 1
    for src in sorted(raw_dir.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[1])):
        left, right = imaging.split_spread(Image.open(src))
        written.append(_renumber(out_dir, index, left)); index += 1
        written.append(_renumber(out_dir, index, right)); index += 1
    return written


def copy_rendered(raw_dir, out_dir):
    """Renumber rendered single pages into out_dir as page-NNN.png."""
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, src in enumerate(
            sorted(raw_dir.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[1])), start=1):
        written.append(_renumber(out_dir, index, Image.open(src)))
    return written


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--spread"]
    spread = "--spread" in sys.argv
    if len(args) != 2:
        print("usage: python -m scripts.extract_pages [--spread] <file.pdf> <work-dir>")
        sys.exit(1)
    pdf, work = args
    raw = Path(work) / "_raw"
    pages = Path(work) / "pages"
    render_pdf(pdf, raw)
    written = split_rendered(raw, pages) if spread else copy_rendered(raw, pages)
    print(f"wrote {len(written)} pages to {pages}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_imaging.py::test_split_rendered_spreads -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_pages.py tests/test_imaging.py
git commit -m "feat: extract_pages CLI with spread splitting"
```

---

### Task 6: `build_html.py` — assembly with proofreading markup

This is the core artifact builder. Build it in three TDD increments: (6a) block rendering, (6b) TOC + document wrapping, (6c) EN+LA file writing.

**Files:**
- Create: `scripts/build_html.py`
- Test: `tests/test_build_html.py`

#### Task 6a: block → HTML

- [ ] **Step 1: Write failing tests for block rendering**

`tests/test_build_html.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build_html.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'kebab'`.

- [ ] **Step 3: Write the block-rendering part of `scripts/build_html.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_build_html.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/build_html.py tests/test_build_html.py
git commit -m "feat: build_html block rendering with proofreading markup"
```

#### Task 6b: sections → body (TOC + hr before headings)

- [ ] **Step 1: Add failing tests**

Append to `tests/test_build_html.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build_html.py -v`
Expected: FAIL — `AttributeError: ... 'load_sections'`.

- [ ] **Step 3: Add to `scripts/build_html.py`**

```python
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
            toc.append((kebab(block[field]), block[field]))
        parts.append(render_block(block, field))
    return "\n".join(parts), toc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_build_html.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_html.py tests/test_build_html.py
git commit -m "feat: build_html body assembly with toc and section hrs"
```

#### Task 6c: full document + EN/LA file writing

- [ ] **Step 1: Add failing tests**

Append to `tests/test_build_html.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_build_html.py::test_build_work_writes_en_and_la -v`
Expected: FAIL — `AttributeError: ... 'build_work'`.

- [ ] **Step 3: Add to `scripts/build_html.py`**

```python
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
<p><b>{toc_label}</b></p>
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
```

- [ ] **Step 4: Run all build_html tests**

Run: `uv run pytest tests/test_build_html.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add scripts/build_html.py tests/test_build_html.py
git commit -m "feat: build_html full EN+LA document assembly"
```

---

### Task 7: `verify.py` — EN/LA structural parity

**Files:**
- Create: `scripts/verify.py`
- Test: `tests/test_verify.py`

- [ ] **Step 1: Write failing tests**

`tests/test_verify.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_verify.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.verify`.

- [ ] **Step 3: Write `scripts/verify.py`**

```python
"""Structural parity check between an EN HTML file and its LA counterpart.

Checks matching counts of <p>, <hr />, <em>, anchor ids, and that every
<p> carries a data-page attribute (the proofreading anchor)."""
import re
import sys
from pathlib import Path


def count_tags(html):
    return {
        "p": len(re.findall(r"<p\b", html)),
        "hr": len(re.findall(r"<hr\b", html)),
        "em": len(re.findall(r"<em\b", html)),
        "data_page": len(re.findall(r"data-page=", html)),
        "ids": set(re.findall(r'<p id="([^"]+)"', html)),
    }


def verify_pair(en_path, la_path):
    """Return (ok, problems). ok is True iff no problems found."""
    en = count_tags(Path(en_path).read_text(encoding="utf-8"))
    la = count_tags(Path(la_path).read_text(encoding="utf-8"))
    problems = []
    for key in ("p", "hr", "em"):
        if en[key] != la[key]:
            problems.append(f"<{key}> count differs: EN={en[key]} LA={la[key]}")
    if en["ids"] != la["ids"]:
        problems.append(f"anchor ids differ: EN-only={en['ids'] - la['ids']} "
                        f"LA-only={la['ids'] - en['ids']}")
    for label, counts in (("EN", en), ("LA", la)):
        if counts["data_page"] != counts["p"]:
            problems.append(
                f"{label}: {counts['p'] - counts['data_page']} <p> missing data-page")
    return (not problems), problems


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m scripts.verify <english.html> <latin.html>")
        sys.exit(1)
    ok, problems = verify_pair(sys.argv[1], sys.argv[2])
    if ok:
        print("PASS")
    else:
        print("FAIL")
        for p in problems:
            print(" -", p)
        sys.exit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_verify.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/verify.py tests/test_verify.py
git commit -m "feat: verify EN/LA structural parity"
```

---

### Task 8: Scaffold files & end-to-end smoke test

**Files:**
- Create: `.gitignore`, `project.yaml`, `work/sample-work/status.yaml`, `work/sample-work/translation/section-01.json`, `README.md`, `CLAUDE.md`
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing end-to-end smoke test**

`tests/test_smoke.py`:
```python
"""End-to-end: bundled sample translation -> EN+LA HTML -> verify passes."""
from pathlib import Path
from scripts import build_html, verify

REPO = Path(__file__).resolve().parent.parent


def test_sample_work_builds_and_verifies(tmp_path):
    work = REPO / "work" / "sample-work"
    out = tmp_path / "output"
    en, la = build_html.build_work(work, "Sample Work", out)
    ok, problems = verify.verify_pair(en, la)
    assert ok, problems
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL — sample work files don't exist yet (`FileNotFoundError` on the translation dir).

- [ ] **Step 3: Create the bundled sample work**

`work/sample-work/translation/section-01.json`:
```json
[
  { "page": "001", "region": "q1_top_left", "type": "heading", "source": "CAPUT PRIMUM", "english": "Chapter One", "notes": [] },
  { "page": "001", "region": "q3_bottom_left", "type": "body", "source": "In principio creavit Deus caelum et terram.", "english": "In the beginning God created heaven and earth.", "notes": [] },
  { "page": "002", "type": "scripture", "source": "Dixitque Deus: Fiat lux. Et facta est lux.", "english": "And God said: Let there be light. And there was light.", "notes": [] },
  { "page": "002", "type": "footnote", "source": "Vide Augustinum, De Genesi ad litteram.", "english": "See Augustine, On the Literal Meaning of Genesis.", "notes": [] }
]
```

`work/sample-work/status.yaml`:
```yaml
work: sample-work
title: "Sample Work"
source_pdf: source/sample.pdf
ocr_method: claude-vision
template_detached: false
stages:
  ingest:     { done: true }
  transcribe: { done: true }
  translate:  { done: true }
  build_html: { done: false }
  publish:    { done: false }
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Write the remaining scaffold files**

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.DS_Store
source/*.pdf
work/**/pages/
work/**/_raw/
output/
!work/sample-work/
```

`project.yaml`:
```yaml
work_defaults:
  source_language: la
  transcription_mode: normalize
  bible_reference_style: douay-rheims
  heading_format: "Chapter {n}: {title}"
translation:
  exclude_editorial_apparatus: true
  target_register: formal
html:
  simple_tags_only: true
```

`README.md` (skeleton — full non-technical quickstart is finished in the skills plan):
```markdown
# Translation Template

A Claude-driven template for translating Catholic Latin/Greek texts into English
and publishing them as a website.

## Quickstart
1. Install Claude Code.
2. Click **Use this template** on GitHub to make your own copy, then download it.
3. Drop your PDF into the `source/` folder.
4. Open the folder in Claude Code and say **"let's get started."**

Claude walks you through the rest. (Detailed guide added with the skills layer.)
```

`CLAUDE.md` (skeleton — institutional knowledge is filled in by the skills plan):
```markdown
# Translation Template — notes for Claude

This project turns scanned Catholic Latin/Greek texts into English HTML.

Pipeline: ingest PDF → transcribe → translate → build HTML (EN + LA) → proofread → publish.
All state lives on disk in `work/<name>/status.yaml`; read it to know what's next.

Helper scripts (run these for mechanical steps):
- `python -m scripts.extract_pages [--spread] <file.pdf> <work-dir>`
- `python -m scripts.crop_page <page.png> <out-dir>`
- `python -m scripts.build_html <work-dir> <title> <out-dir>`
- `python -m scripts.verify <english.html> <latin.html>`

(Transcription/translation conventions, compaction heuristics, and the guided
skills are added in the skills implementation plan.)
```

- [ ] **Step 6: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS (all tests across config, imaging, build_html, verify, smoke).

- [ ] **Step 7: Commit**

```bash
git add .gitignore project.yaml work/sample-work README.md CLAUDE.md tests/test_smoke.py
git commit -m "feat: scaffold files and end-to-end smoke test"
```

---

## Self-review notes

**Spec coverage (this plan's slice):** config + status tracking ✓ (Task 2), Claude-vision crop technique ✓ (Tasks 3–4), PDF ingest incl. book-spread split ✓ (Task 5), HTML-first EN+LA output ✓ (Task 6), proofreading `data-page`/`data-region` markup ✓ (Task 6a), EN/LA structural verify ✓ (Task 7), bundled sample for end-to-end smoke test ✓ (Task 8), `project.yaml` knobs + `.gitignore` (incl. keeping the sample work, ignoring heavy artifacts) ✓ (Task 8). Out of scope by design (later plans): dashboard, viewer, the skills, `CLAUDE.md` institutional content, transcription/translation agent logic, publish flow.

**Placeholder scan:** none — every code/test step contains complete content.

**Type/name consistency:** `kebab`, `render_block(block, field)`, `build_body`, `load_sections`, `render_document`, `build_work`, `count_tags`, `verify_pair`, `split_spread`, `crops`, `write_crops`, `split_rendered`, `copy_rendered`, `render_pdf`, `load_project`, `update_status` — used consistently across tasks and tests.

**Known intentional limitations:** `verify_pair` compares aggregate counts (matches the lapide `verify-lt.py` approach), not per-section; finer per-section checks can come with the build-html skill. `render_block` HTML-escapes text, so transcription/translation must supply plain text (no inline markup) — consistent with the simple-tags convention.
```
