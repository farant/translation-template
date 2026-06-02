# Skills & Guidance Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the conversational guided layer — eight project skills (`start`, `setup`, `ingest-pdf`, `transcribe`, `translate`, `build-html`, `proofread`, `publish`), a full `CLAUDE.md` of institutional knowledge, and a non-technical `README.md` — so a non-technical user drives the whole pipeline by talking to Claude.

**Architecture:** Each pipeline stage is a Claude Code project skill at `.claude/skills/<name>/SKILL.md` (YAML frontmatter `name` + `description`, then a focused instruction body). The `start` skill is the entry point that reads `work/*/status.yaml` and routes to the next stage. Skills orchestrate the Plan 1 helper scripts (mechanical steps) and fan out subagents (judgment steps). A small `validate_skills.py` + tests give a structural gate so skills can't silently break. `CLAUDE.md` holds the conventions every stage references; `README.md` is the front door.

**Tech Stack:** Markdown (skills/docs), Python 3 stdlib + PyYAML for the validator, `pytest`. Run tests with `.venv/bin/pytest`.

---

## Context from Plans 1 & 2 (already on `main`)

Helper scripts (run as `.venv/bin/python -m scripts.<name>`):
- `extract_pages [--spread] <file.pdf> work/<name>` → `work/<name>/pages/page-NNN.png`
- `crop_page <page.png> <out-dir>` → 8 crops `<stem>_<region>.png`
- `build_html work/<name> "<Title>" output` → `output/<name>.html` + `output/<name>_la.html`
- `verify <en.html> <la.html>` → EN/LA parity (`PASS`/`FAIL`)
- `dashboard [8000]`, `viewer [8001]` → the two localhost web apps
- `config.update_status(path, key_path, value)` — programmatic status updates
- `proofing.load_flags(work_dir)` / flags live in `work/<name>/proofing-notes.yaml`

Data formats: `work/<name>/status.yaml` (stages: ingest/transcribe/translate/build_html/publish); `translation/section-NN.json` blocks `{page, region?, type, source, english, notes}`. HTML build derives anchor ids from the **English** text for both EN and LA files. Test runner: `.venv/bin/pytest`.

## File structure (this plan)

- Create: `scripts/validate_skills.py` — `parse_frontmatter`, `validate_skill`, `validate_all`.
- Create: `tests/test_validate_skills.py` — validator unit tests + a real-skills gate (added in the last task).
- Create: `.claude/skills/start/SKILL.md`
- Create: `.claude/skills/setup/SKILL.md`
- Create: `.claude/skills/ingest-pdf/SKILL.md`
- Create: `.claude/skills/transcribe/SKILL.md`
- Create: `.claude/skills/translate/SKILL.md`
- Create: `.claude/skills/build-html/SKILL.md`
- Create: `.claude/skills/proofread/SKILL.md`
- Create: `.claude/skills/publish/SKILL.md`
- Modify (replace): `CLAUDE.md` — full institutional knowledge.
- Modify (replace): `README.md` — full non-technical quickstart.

---

### Task 1: Skills validator

**Files:**
- Create: `scripts/validate_skills.py`
- Test: `tests/test_validate_skills.py`

- [ ] **Step 1: Write failing tests**

`tests/test_validate_skills.py`:
```python
from scripts import validate_skills as v


def test_parse_frontmatter_reads_name_and_description():
    text = "---\nname: start\ndescription: do things\n---\n\nbody"
    fm = v.parse_frontmatter(text)
    assert fm == {"name": "start", "description": "do things"}


def test_parse_frontmatter_none_when_absent():
    assert v.parse_frontmatter("no frontmatter here") is None


def test_validate_skill_ok(tmp_path):
    d = tmp_path / "start"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: start\ndescription: x\n---\nbody", encoding="utf-8")
    assert v.validate_skill(d) == []


def test_validate_skill_name_mismatch(tmp_path):
    d = tmp_path / "start"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: wrong\ndescription: x\n---\n", encoding="utf-8")
    problems = v.validate_skill(d)
    assert any("name" in p for p in problems)


def test_validate_skill_empty_description(tmp_path):
    d = tmp_path / "start"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: start\ndescription: ''\n---\n", encoding="utf-8")
    assert any("description" in p for p in v.validate_skill(d))


def test_validate_skill_missing_file(tmp_path):
    d = tmp_path / "start"
    d.mkdir()
    assert any("missing SKILL.md" in p for p in v.validate_skill(d))


def test_validate_all_collects_per_skill(tmp_path):
    for name in ("a", "b"):
        d = tmp_path / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n", encoding="utf-8")
    results = v.validate_all(tmp_path)
    assert results == {"a": [], "b": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_validate_skills.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.validate_skills`.

- [ ] **Step 3: Write `scripts/validate_skills.py`**

```python
"""Validate project skill files.

Each skill is `.claude/skills/<name>/SKILL.md` with YAML frontmatter carrying
a `name` (matching the directory) and a non-empty `description`. This guards
against silently broken skills."""
from pathlib import Path
import yaml


def parse_frontmatter(text):
    """Return the frontmatter dict, or None if absent/malformed."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None


def validate_skill(skill_dir):
    """Return a list of problem strings for one skill directory (empty = valid)."""
    skill_dir = Path(skill_dir)
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]
    fm = parse_frontmatter(md.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{skill_dir.name}: missing or malformed frontmatter"]
    problems = []
    if fm.get("name") != skill_dir.name:
        problems.append(f"{skill_dir.name}: frontmatter name {fm.get('name')!r} != directory")
    if not (fm.get("description") or "").strip():
        problems.append(f"{skill_dir.name}: empty description")
    return problems


def validate_all(skills_root):
    """Map each skill directory name to its list of problems."""
    skills_root = Path(skills_root)
    results = {}
    for md in sorted(skills_root.glob("*/SKILL.md")):
        results[md.parent.name] = validate_skill(md.parent)
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_validate_skills.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/validate_skills.py tests/test_validate_skills.py
git commit -m "feat: skill file validator"
```

---

### Task 2: `start` skill

**Files:**
- Create: `.claude/skills/start/SKILL.md`

- [ ] **Step 1: Create the skill file** (exact content)

````markdown
---
name: start
description: Use at the start of a session, or when the user says "let's get started", "what's next", or opens the project. Orients them, detects pipeline state from work/*/status.yaml, and routes to the next step. Triggered before any other pipeline skill when the current stage is unknown.
---

# Start / orient

You are the friendly guide for a Catholic Latin/Greek → English translation project. The user is non-technical — be warm and concrete, never assume they know stage names, and always offer to do the next step rather than asking them to. Read `CLAUDE.md` for conventions.

When invoked:

1. **Check setup.** If `.venv` is missing or core tools aren't installed, hand off to the **setup** skill first. You can offer to open the dashboard: `.venv/bin/python -m scripts.dashboard` → http://127.0.0.1:8000.

2. **Check template link.** If `git remote get-url origin` points at `farant/translation-template` and the project hasn't been detached, mention it and offer the **setup** skill's detach step (so it doesn't surprise them later).

3. **Find works.** List `work/*/status.yaml` and read each one's `stages`:
   - **No works, but a PDF is in `source/`** → offer to ingest it (**ingest-pdf**).
   - **No works and no PDF** → "Drop your PDF into the `source/` folder and tell me when it's there — or ask me to explain how this works first."
   - **A work is mid-pipeline** → say where it stands ("Genesis is transcribed through page 40 of 92") and offer the next stage.

4. **Route** to the matching skill: ingest-pdf → transcribe → translate → build-html → proofread → publish.

After a `/compact` you reconstruct everything from `status.yaml`, so it is always safe to compact between stages — reassure the user of this.
````

- [ ] **Step 2: Validate the skill**

Run: `.venv/bin/python -c "from scripts import validate_skills as v; print(v.validate_skill('.claude/skills/start'))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/start/SKILL.md
git commit -m "feat: start skill (entry point / router)"
```

---

### Task 3: `setup` skill

**Files:**
- Create: `.claude/skills/setup/SKILL.md`

- [ ] **Step 1: Create the skill file** (exact content)

````markdown
---
name: setup
description: Use to set up the project for a non-technical user — create the Python venv, install missing dependencies, open the setup dashboard, choose an OCR method, and detach a cloned project from the template repo. Triggered on first run or when something is "not installed" or "won't run".
---

# Setup

1. **Create the venv** if `.venv` is missing:
   `python3 -m venv .venv && .venv/bin/pip install -e . pytest`

2. **Open the dashboard** so the user can see status:
   `.venv/bin/python -m scripts.dashboard` → http://127.0.0.1:8000
   It lists each tool with a copy-paste install command.

3. **Install missing tools** (offer to run these for them). Core: poppler (`brew install poppler`), imagemagick (`brew install imagemagick`), git, gh (`brew install gh`). If Homebrew itself is missing, point them to https://brew.sh.

4. **Detach from the template (clone case).** If `git remote get-url origin` is `farant/translation-template` (https or ssh), this project is still linked to the template. Offer: "Want me to detach this so it's fully yours? Your work won't be affected." → `git remote remove origin`, then record `template_detached: true` in each work's `status.yaml`. If they used GitHub's **Use this template** button, origin already points at their own repo — nothing to do.

5. **Choose OCR method (per work).** Default **claude-vision** (no install — you read the page crops directly). Suggest **surya** only for very dense/multi-column/footnoted pages (heavier ML install). Record the choice as `ocr_method` in the work's `status.yaml`. See CLAUDE.md "OCR methods".

The dashboard is informational — you do the installing.
````

- [ ] **Step 2: Validate the skill**

Run: `.venv/bin/python -c "from scripts import validate_skills as v; print(v.validate_skill('.claude/skills/setup'))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/setup/SKILL.md
git commit -m "feat: setup skill"
```

---

### Task 4: `ingest-pdf` skill

**Files:**
- Create: `.claude/skills/ingest-pdf/SKILL.md`

- [ ] **Step 1: Create the skill file** (exact content)

````markdown
---
name: ingest-pdf
description: Use to turn a source PDF into page images — the first pipeline stage. Triggered when a PDF is in source/ and not yet ingested, or the user says "start this book" or "ingest the PDF".
---

# Ingest a PDF

1. **Pick the PDF** in `source/` and choose a short kebab-case work name (e.g. `in-genesin`).
2. **Ask: is it a book-spread scan?** If each PDF page is a photo of an open book (two pages at once), use `--spread`; otherwise omit it.
3. **Extract pages:**
   `.venv/bin/python -m scripts.extract_pages [--spread] source/<file>.pdf work/<name>`
   → writes `work/<name>/pages/page-NNN.png`.
4. **Pre-crop for Claude vision** (when `ocr_method` is claude-vision). You can crop on demand during transcription, or upfront:
   `.venv/bin/python -m scripts.crop_page work/<name>/pages/page-NNN.png work/<name>/pages/crops`
5. **Create `work/<name>/status.yaml`** with `work`, `title`, `source_pdf`, `ocr_method`, `template_detached`, and `stages` (set `ingest: {done: true}` with the page count; the rest `{done: false}`).

Then suggest moving to transcription. This is a good moment to `/compact`.
````

- [ ] **Step 2: Validate the skill**

Run: `.venv/bin/python -c "from scripts import validate_skills as v; print(v.validate_skill('.claude/skills/ingest-pdf'))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/ingest-pdf/SKILL.md
git commit -m "feat: ingest-pdf skill"
```

---

### Task 5: `transcribe` skill

**Files:**
- Create: `.claude/skills/transcribe/SKILL.md`

- [ ] **Step 1: Create the skill file** (exact content)

````markdown
---
name: transcribe
description: Use to transcribe page images into the source language (Latin/Greek) text — the second pipeline stage. Triggered after ingest, or when the user says "transcribe the pages" or "read the scans".
---

# Transcribe pages → source text

Goal: produce `work/<name>/transcription/section-NN.json` files. Each is a JSON array of blocks:
`{ "page": "001", "region": "q3_bottom_left", "type": "body", "source": "Latin text...", "notes": [] }`
Types: `heading | body | scripture | footnote | marginal_note`. `region` is the crop you read it from (optional).

**Claude-vision method (default).** Fan out subagents, ~6 pages per batch, in parallel — this keeps the main thread lean (see CLAUDE.md "Token efficiency & compaction"). Instruct each subagent to:
- Read the page crops (`work/<name>/pages/crops/page-NNN_*.png`) — quarters for dense body/footnotes, halves for context across a quarter boundary.
- Transcribe the Latin/Greek faithfully. If `transcription_mode` is `normalize` (default), silently correct OCR-style artifacts — especially long-s (ſ→s) and obvious scan errors. If `diplomatic`, preserve original orthography.
- Tag each block's `type`; record uncertain readings in `notes` as `{"type":"uncertain","text":"..."}`.
- If text seems missing, open the full page PNG directly — vision sometimes drops marginal notes or faded lines.
- Write its batch as one or more `section-NN.json` files.

**Surya method (optional):** see CLAUDE.md "OCR methods".

Update `status.yaml` (`transcribe.completed_pages` / `done`). Suggest `/compact` after every couple of batches and before translation.
````

- [ ] **Step 2: Validate the skill**

Run: `.venv/bin/python -c "from scripts import validate_skills as v; print(v.validate_skill('.claude/skills/transcribe'))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/transcribe/SKILL.md
git commit -m "feat: transcribe skill"
```

---

### Task 6: `translate` skill

**Files:**
- Create: `.claude/skills/translate/SKILL.md`

- [ ] **Step 1: Create the skill file** (exact content)

````markdown
---
name: translate
description: Use to translate transcribed source text into English — the third pipeline stage. Triggered after transcription, or when the user says "translate it" or "into English".
---

# Translate → English

Goal: produce `work/<name>/translation/section-NN.json` — the transcription blocks plus an `english` field:
`{ "page":"001", "region":"...", "type":"body", "source":"...", "english":"...", "notes":[] }`

Fan out subagents per section (parallel). Each reads one transcription section and writes the matching translation section. Carry these conventions (full list in CLAUDE.md "Translation conventions"):
- **Trinity pronouns capitalized:** He, Him, His, Himself for the Father, Son, and Holy Spirit.
- **Scripture quotations** keep `type: scripture` (italicized in HTML). Use **Douay-Rheims** wording for Vulgate quotations unless `project.yaml`'s `bible_reference_style` says otherwise.
- **Editorial apparatus:** if `exclude_editorial_apparatus` is true, still translate later-editor footnotes but keep them tagged so the HTML stage can drop them.
- Keep paragraph numbers; formal register; carry `notes`; flag anything `uncertain`.

Update `status.yaml` (`translate.done`). Good moment to `/compact` before building HTML.
````

- [ ] **Step 2: Validate the skill**

Run: `.venv/bin/python -c "from scripts import validate_skills as v; print(v.validate_skill('.claude/skills/translate'))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/translate/SKILL.md
git commit -m "feat: translate skill"
```

---

### Task 7: `build-html` skill

**Files:**
- Create: `.claude/skills/build-html/SKILL.md`

- [ ] **Step 1: Create the skill file** (exact content)

````markdown
---
name: build-html
description: Use to assemble translated text into English + Latin HTML with proofreading markup — the fourth pipeline stage. Triggered after translation, or when the user says "build the pages" or "make the HTML".
---

# Build HTML (EN + LA)

1. **Run the builder:**
   `.venv/bin/python -m scripts.build_html work/<name> "<Work Title>" output`
   → `output/<name>.html` (English) and `output/<name>_la.html` (Latin). Each block carries `data-page` (and `data-region`) for proofreading; anchor ids derive from the English text so EN and LA share them.
2. **Verify parity:**
   `.venv/bin/python -m scripts.verify output/<name>.html output/<name>_la.html`
   Fix any reported mismatch (usually `<em>` count or a missing `data-page`) by editing the `translation/section-NN.json`, then rebuild.
3. **Stylesheet:** ensure `output/style.css` exists (simple: max-width ~70ch, centered, generous line-height and padding).
4. Update `status.yaml` (`build_html.done`).

HTML uses simple tags only (`<p>`, `<hr />`, `<b>`, `<em>`) — see CLAUDE.md "HTML conventions". Then suggest proofreading.
````

- [ ] **Step 2: Validate the skill**

Run: `.venv/bin/python -c "from scripts import validate_skills as v; print(v.validate_skill('.claude/skills/build-html'))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/build-html/SKILL.md
git commit -m "feat: build-html skill"
```

---

### Task 8: `proofread` skill

**Files:**
- Create: `.claude/skills/proofread/SKILL.md`

- [ ] **Step 1: Create the skill file** (exact content)

````markdown
---
name: proofread
description: Use to proofread generated pages against the source scans and apply the user's flagged fixes — the fifth pipeline stage. Triggered after build-html, or when the user says "let me check it" or "proofread".
---

# Proofread

1. **Launch the viewer:** have the user run `.venv/bin/python -m scripts.viewer` and open http://127.0.0.1:8001. Left pane = generated English/Latin; right pane = the source scan. They click a paragraph to see its page and click the ⚑ button to flag an issue.
2. **Apply flags.** Read `work/<name>/proofing-notes.yaml` (a list of `{page, block, note}`). For each flag: look at the page PNG, fix the underlying `translation/section-NN.json` block, then remove the resolved note.
3. **Rebuild** with the build-html skill and re-run `verify`.
4. Repeat until the user is satisfied. The human only spots problems; you do the fixing.

Flags and fixes are all on disk, so `/compact` between rounds is safe.
````

- [ ] **Step 2: Validate the skill**

Run: `.venv/bin/python -c "from scripts import validate_skills as v; print(v.validate_skill('.claude/skills/proofread'))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/proofread/SKILL.md
git commit -m "feat: proofread skill"
```

---

### Task 9: `publish` skill

**Files:**
- Create: `.claude/skills/publish/SKILL.md`

- [ ] **Step 1: Create the skill file** (exact content)

````markdown
---
name: publish
description: Use to publish the finished site to GitHub Pages — the final stage. Triggered after proofreading, or when the user says "publish it" or "put it online".
---

# Publish to GitHub Pages

You do what you can; the user does the credential/browser steps. **Confirm before any public action.**

1. **Prereqs:** ensure `git` and `gh` are installed (setup skill / dashboard). If `gh` isn't authenticated, tell the user to run `! gh auth login` in the session, then wait.
2. **Build an index:** generate `output/index.html` linking each built work (title + link). For a single work, a simple landing page.
3. **Confirm:** "This will create a *public* GitHub repo named `<name>` and put the site online — proceed?" Explain public-vs-private (Pages needs a public repo or a paid plan).
4. **Create the publish repo** (separate from this project): in `output/`, `git init`, commit, then `gh repo create <name> --public --source=output --push`. If `gh` is unavailable, give the manual steps (create on github.com, add the remote, push).
5. **Enable Pages:** via `gh api`, or tell them: repo Settings → Pages → Source: `main` / root → Save. Report the live URL.
6. **Record** the repo + URL in `status.yaml` (`publish.done`). Re-publishing later is just `git add/commit/push` inside `output/`.

Never push the *project* repo to the template; the published site is its own repo. See CLAUDE.md "Git topology & publishing".
````

- [ ] **Step 2: Validate the skill**

Run: `.venv/bin/python -c "from scripts import validate_skills as v; print(v.validate_skill('.claude/skills/publish'))"`
Expected: `[]`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/publish/SKILL.md
git commit -m "feat: publish skill"
```

---

### Task 10: Full `CLAUDE.md`

**Files:**
- Modify (replace entirely): `CLAUDE.md`

- [ ] **Step 1: Replace `CLAUDE.md`** with this exact content

`````markdown
# Translation Template — notes for Claude

This project turns scanned **Catholic Latin/Greek** texts into **English** HTML and publishes them as a website. It is driven conversationally: a non-technical user drops a PDF in `source/`, opens Claude Code, and says "let's get started." You walk them through everything — installing tools included.

## Pipeline

ingest PDF → transcribe → translate → build HTML (EN + LA) → proofread → publish

Each stage is a skill in `.claude/skills/<stage>/`. The entry point is the **start** skill — invoke it to orient and route. **All state lives on disk** in `work/<name>/status.yaml`; read it to know what's next. Run every script with the project venv: `.venv/bin/python -m scripts.<name>`.

## Helper scripts (mechanical steps)

- `.venv/bin/python -m scripts.extract_pages [--spread] <file.pdf> work/<name>` — PDF → `work/<name>/pages/page-NNN.png`. `--spread` for book-spread scans (two pages per PDF page).
- `.venv/bin/python -m scripts.crop_page <page.png> <out-dir>` — crop a page into 4 quarters + 4 halves for Claude-vision reading.
- `.venv/bin/python -m scripts.build_html work/<name> "<Title>" output` — translation JSON → `output/<name>.html` + `output/<name>_la.html`.
- `.venv/bin/python -m scripts.verify <en.html> <la.html>` — EN/LA structural parity.
- `.venv/bin/python -m scripts.dashboard [8000]` — setup dashboard.
- `.venv/bin/python -m scripts.viewer [8001]` — proofreading viewer.

## Data formats

`work/<name>/status.yaml`:
```yaml
work: <name>
title: "..."
source_pdf: source/<file>.pdf
ocr_method: claude-vision   # or surya
template_detached: false
stages:
  ingest: {done: false}
  transcribe: {done: false}
  translate: {done: false}
  build_html: {done: false}
  publish: {done: false}
```

`work/<name>/transcription/section-NN.json` — source text per section (array):
`{ "page":"001", "region":"q3_bottom_left", "type":"body", "source":"Latin...", "notes":[] }`

`work/<name>/translation/section-NN.json` — adds the English:
`{ "page":"001", "region":"...", "type":"body", "source":"...", "english":"...", "notes":[] }`

Block `type`: `heading | body | scripture | footnote | marginal_note`. `region` optional. `notes` entries: `{"type":"uncertain","text":"..."}` or `{"type":"ocr_correction","text":"..."}`. Update status programmatically with `scripts.config.update_status(path, key_path, value)` or by editing the file.

## OCR methods

- **claude-vision (default):** crop each page (`crop_page`) and have subagents read the crops — quarters for dense body/footnotes, halves for context that crosses a quarter boundary. No install. Best for clean print; fine for most Catholic Latin.
- **surya (optional):** local ML OCR for very dense/multi-column/footnoted pages. Heavier install (a Python ML stack) — set it up only if a work needs it, and record `ocr_method: surya`.

Known issue for both: the long-s (ſ) reads as 'f' — correct to 's' in `normalize` mode.

## Transcription conventions

- `transcription_mode: normalize` (default) — correct OCR artifacts (long-s ſ→s, obvious scan errors) for a readable result. `diplomatic` — preserve original orthography (u/v, æ/œ, etc.).
- If text looks missing, open the full page PNG directly — vision sometimes drops marginal notes or faded lines.
- Two-column pages: read each column in order; keep reading order in the JSON.
- Flag uncertain readings in `notes` rather than guessing silently.

## Translation conventions

- **Trinity pronouns capitalized:** He, Him, His, Himself for the Father, Son, and Holy Spirit.
- **Scripture quotations:** tag `type: scripture` (italicized in HTML). For Vulgate quotations use **Douay-Rheims** English unless `project.yaml`'s `bible_reference_style` says otherwise.
- **Editorial apparatus:** later-editor (post-author) footnotes — if `exclude_editorial_apparatus` is true, translate them but keep them tagged (`type: footnote` + a note) so the HTML stage can drop them. Signals: citations of scholars who died after the author, out-of-sequence verse references, numbered italic glosses.
- Preserve paragraph numbers; keep a formal register; carry `notes`.

## HTML conventions

- Simple tags only: `<p>`, `<hr />`, `<b>`, `<em>`. No classes or complex markup.
- Headings: `<p id="kebab-id"><b>Title</b></p>`, with `<hr />` before each. Anchor ids derive from the **English** text so EN and LA files share them (cross-referencing).
- Scripture and footnotes wrapped in `<em>`.
- Every content block carries `data-page` (and `data-region` when known) — invisible in normal viewing, used by the proofreading viewer.
- Heading format from `project.yaml` (default `Chapter IV: Title` — title case, Roman numeral, no trailing period, never ALL CAPS).

## Token efficiency & compaction

All state is on disk, so the conversation is disposable — after `/compact` you reload from `status.yaml` and the section files. Use this deliberately:
- **Fan out subagents** for transcription/translation/HTML so the heavy context (page images, long Latin) lives in their context, not the main thread; they return a written file + a one-line summary.
- **Suggest `/compact`** at stage boundaries (once a stage's files are written), after every 2–3 batches in a long stage, and before a large fan-out. Reassure the user it's always safe — nothing important lives only in the chat.

## Web apps (localhost)

- Setup dashboard: `.venv/bin/python -m scripts.dashboard` (:8000) — dependency checklist + per-work progress. Read-only.
- Proofreading viewer: `.venv/bin/python -m scripts.viewer` (:8001) — generated HTML beside the source scan; click a paragraph to see its page, ⚑ to flag into `work/<name>/proofing-notes.yaml`.

## Git topology & publishing

Three independent git contexts: (1) the template repo `farant/translation-template`; (2) this project (the user's copy); (3) the **published site**, created from `output/` by the publish skill as a *separate* repo under the user's account. The published site is always its own repo, so publishing never touches the template. If the project still points at `farant/translation-template` (a plain clone), the setup skill offers to detach (`git remote remove origin`). Recommend users start via GitHub's **Use this template** button so origin is already theirs.
`````

- [ ] **Step 2: Sanity-check it's valid markdown and mentions the key conventions**

Run: `.venv/bin/python -c "t=open('CLAUDE.md',encoding='utf-8').read(); assert 'Trinity pronouns' in t and 'data-page' in t and 'compact' in t.lower() and 'claude-vision' in t; print('ok', len(t), 'chars')"`
Expected: `ok <N> chars`

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: full CLAUDE.md institutional knowledge"
```

---

### Task 11: Full `README.md`

**Files:**
- Modify (replace entirely): `README.md`

- [ ] **Step 1: Replace `README.md`** with this exact content

`````markdown
# Translation Template

A Claude-driven template for turning scanned **Catholic Latin (or Greek) texts** into **English** — and publishing them as a clean website. You mostly just talk to Claude; it does the technical work and even helps you install what's missing.

## What you need first

- **[Claude Code](https://claude.com/claude-code)** installed. (This is the one thing Claude can't install for you — you need it to talk to Claude.)

That's it. Claude helps with everything else (PDF tools, image tools, GitHub).

## Quickstart

1. **Make your own copy.** On this repo's GitHub page, click the green **Use this template** button → it creates a fresh copy under your account. Download or clone it to your computer.
2. **Add your PDF.** Put your scanned Latin/Greek PDF into the `source/` folder.
3. **Open the folder in Claude Code** and say **"let's get started."**

From there Claude will:
- open a **setup dashboard** (a web page showing what's installed) and help install anything missing,
- help you pick how to read the scans,
- then walk you through: read the pages → translate to English → build the web pages → **proofread side-by-side with the original scans** → publish.

4. **Proofread.** Claude opens a viewer where the generated text sits next to the original scan. Click a paragraph to see its page; click the flag (⚑) to mark anything wrong — Claude fixes the flagged spots for you.
5. **Publish (optional).** Say "let's publish it" and Claude sets up a free GitHub Pages website with you.

## Tips

- It's always safe to run `/compact` when Claude suggests it — everything is saved to disk, so nothing is lost.
- You can hold several books in one project; each lives under `work/<name>/`.

## For the curious (how it's built)

Plain Python helper scripts under `scripts/` do the mechanical steps (PDF → images, image cropping, HTML assembly). The judgment steps (reading, translating, formatting) are done by Claude. Two small local web apps (the setup dashboard and the proofreading viewer) are stdlib-only — no heavy setup. The guidance Claude follows lives in `CLAUDE.md` and `.claude/skills/`.
`````

- [ ] **Step 2: Sanity-check key onboarding phrases are present**

Run: `.venv/bin/python -c "t=open('README.md',encoding='utf-8').read(); assert 'Use this template' in t and 'Claude Code' in t and \"let's get started\" in t and 'source/' in t; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: full non-technical README"
```

---

### Task 12: Real-skills gate & full-suite check

**Files:**
- Modify: `tests/test_validate_skills.py` (append)

- [ ] **Step 1: Append the real-skills test**

Append to `tests/test_validate_skills.py`:
```python
from pathlib import Path

EXPECTED_SKILLS = {
    "start", "setup", "ingest-pdf", "transcribe",
    "translate", "build-html", "proofread", "publish",
}


def test_all_project_skills_present_and_valid():
    skills_root = Path(__file__).resolve().parent.parent / ".claude" / "skills"
    results = v.validate_all(skills_root)
    # every expected skill exists
    assert EXPECTED_SKILLS.issubset(set(results)), EXPECTED_SKILLS - set(results)
    # and none has problems
    problems = {name: probs for name, probs in results.items() if probs}
    assert problems == {}, problems
```

- [ ] **Step 2: Run it to verify it passes**

Run: `.venv/bin/pytest tests/test_validate_skills.py::test_all_project_skills_present_and_valid -v`
Expected: PASS (all 8 skills exist and validate).

- [ ] **Step 3: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (all Plan 1 + Plan 2 + Plan 3 tests).

- [ ] **Step 4: Commit**

```bash
git add tests/test_validate_skills.py
git commit -m "test: gate that all eight project skills exist and validate"
```

---

## Self-review notes

**Spec coverage (this plan's slice):**
- Guided entry point that detects state and routes ✓ Task 2 (`start`).
- Setup (deps, dashboard, OCR-method choice, template detach) ✓ Task 3 (`setup`).
- All six pipeline stages as skills ✓ Tasks 4–9 (ingest-pdf, transcribe, translate, build-html, proofread, publish).
- Transcription conventions (normalize/diplomatic, long-s, open-PNG-if-missing, uncertain notes) ✓ Task 5 + CLAUDE.md (Task 10).
- Translation conventions (Trinity pronouns, scripture/Douay-Rheims, editorial-apparatus exclusion) ✓ Task 6 + CLAUDE.md.
- HTML conventions + proofreading markup ✓ Task 7 + CLAUDE.md.
- Proofread loop (viewer → flags → fix → rebuild) ✓ Task 8.
- Publish (gh-first, manual fallback, confirm before public, separate publish repo) ✓ Task 9 + CLAUDE.md git topology.
- Compaction heuristics ✓ CLAUDE.md "Token efficiency & compaction" + reminders in each stage skill.
- Distribution / "Use this template" + non-technical onboarding ✓ Task 11 (README).
- Structural integrity gate so skills can't silently break ✓ Tasks 1, 12.

**Placeholder scan:** none — every skill, CLAUDE.md, and README is written out in full.

**Type/name consistency:** validator API `parse_frontmatter`, `validate_skill`, `validate_all` used consistently in Tasks 1 and 12. Skill directory names exactly match their frontmatter `name` (start, setup, ingest-pdf, transcribe, translate, build-html, proofread, publish) and `EXPECTED_SKILLS` in Task 12. Script invocations in the skills match the real modules from Plans 1–2 (`extract_pages`, `crop_page`, `build_html`, `verify`, `dashboard`, `viewer`). Data-format references (`transcription/section-NN.json` source-only; `translation/section-NN.json` adds `english`) are consistent across transcribe/translate/build-html skills and CLAUDE.md.

**Known intentional decisions:**
- Skills are invoked by their `description` (natural-language triggers) — no slash commands needed; the user just talks.
- The validator checks structure (frontmatter + name), not prose quality — content quality is covered by the task author + review.
- Surya OCR is documented, not scripted, in v1 (claude-vision is the built path) — consistent with the design spec.
- `transcription/` holds source-only blocks; `translate` enriches them into `translation/` (which `build_html` consumes) — this split keeps each stage's output a clean, resumable artifact.
