# Translation Template — Design Spec

**Date:** 2026-06-02
**Status:** Approved (design), pending implementation plan
**Distribution home:** `github.com/farant/translation-template`

## Purpose

A reusable, **Claude-driven** project template for translating **Catholic texts from Latin (and some Greek) into English**, producing a publishable HTML site. It is aimed at **non-technical users**: someone drops a PDF into a folder, opens Claude Code, says "let's get started," and Claude walks them through the entire pipeline — installing tools, transcribing, translating, building HTML, proofreading, and publishing.

The template distills the institutional knowledge from two existing projects:
- **`old-hebrew-bible/lapide`** — a pragmatic, agent-driven PDF→OCR(Surya)→translate→HTML→publish pipeline (source of HTML conventions, translation JSON format, agent fan-out, publishing model).
- **`baronius`** — a structured, Claude-vision OCR approach using page cropping (`crop_page.sh`), diplomatic transcription, uncertainty tokens, and per-language convention docs (source of the Claude-vision OCR technique and transcription discipline).

## Goals & non-goals

**Goals (v1):**
- Self-guiding, conversational flow for a non-technical user.
- Catholic Latin/Greek → English, opinionated about the domain but not hardcoded to any one work (no Lapide/Genesis/Crampon specifics baked in).
- Setup dashboard (localhost) showing dependency/install status and OCR-method choice.
- OCR by **Claude vision** (default, zero install) or **Surya** (optional accuracy upgrade), chosen per-work with Claude's help.
- Output: **English HTML + Latin (parallel source) HTML**, with **proofreading markup** that ties each block to its source page image, plus a **local side-by-side proofreading viewer**.
- **Token-efficiency / compaction heuristics** so Claude prompts the user at good moments to `/compact`.
- Claude-guided **GitHub repo + GitHub Pages** publishing.

**Non-goals (v1, documented as later extensions):**
- Multi-language fan-out beyond English + Latin parallel (e.g. Spanish, French, etc.).
- Fully automated (non-agent) end-to-end runs.
- A queryable structured data model (baronius-style typed-unit YAML); v1 is HTML-first.
- Dashboard buttons that *trigger* Claude actions (v1 dashboard is informational only).

## Architecture overview

Delivery model (chosen approach **A**): a **skill-driven template repo**. The template is a folder the user copies; it contains `CLAUDE.md` (institutional knowledge), one Claude Code **skill per pipeline stage** (the guided judgment steps), **helper scripts** (mechanical steps Claude runs), a **`project.yaml`** config, and two localhost web apps (setup dashboard + proofreading viewer).

**Two clean separations:**
- **Mechanical vs. judgment** — scripts do deterministic conversions (PDF→pages, cropping, HTML assembly, serving web apps); skills + fanned-out agents do reading, transcription, translation, and HTML shaping.
- **Per-work isolation** — everything for one book/work lives under `work/<name>/`, so a project can hold multiple works without tangling.

**Core data flow:**
```
source/*.pdf
  → work/<name>/pages/page-NNN.png      (ingest-pdf)
  → work/<name>/transcription/          (transcribe)
  → work/<name>/translation/            (translate)
  → output/<name>.html + <name>_la.html (build-html)
  → proofing loop (proofread)
  → published GitHub Pages site         (publish)
```
Each arrow is one skill. **All state lives on disk** (see Compaction), so the conversation is disposable and resumable.

## Repo layout

```
translation-template/
├── CLAUDE.md                  # Distilled institutional knowledge (the "brain")
├── README.md                  # Non-technical quickstart (see Distribution)
├── project.yaml               # Per-project config (title, author, languages, conventions)
├── .gitignore                 # Ignores .venv/, source/*.pdf, work/**/*.png, output/
│
├── .claude/
│   └── skills/
│       ├── start/             # Entry point: orients user, detects state, routes
│       ├── setup/             # Dependency dashboard + OCR-method choice + template detach
│       ├── ingest-pdf/        # PDF → page images (+ crops for vision)
│       ├── transcribe/        # Latin/Greek source → transcription
│       ├── translate/         # source → English
│       ├── build-html/        # transcription+translation → EN + LA HTML (proof markup)
│       ├── proofread/         # launch viewer; apply flagged fixes
│       └── publish/           # guided GitHub repo + Pages setup
│
├── scripts/
│   ├── extract_pages.py       # PDF → page-NNN.png (handles book-spread split)
│   ├── crop_page.py           # page → quarters+halves for Claude vision (from baronius)
│   ├── build_html.py          # assemble HTML from stage data
│   ├── dashboard.py           # serves the localhost setup dashboard
│   └── viewer.py              # serves the localhost proofreading viewer
│
├── dashboard/                 # Setup dashboard web assets (localhost)
├── viewer/                    # Proofreading viewer web assets (localhost)
│
├── source/                    # User drops PDFs here
├── work/                      # Per-work pipeline data
│   └── <work-name>/
│       ├── pages/             # page-NNN.png (+ crops)
│       ├── transcription/     # per-page/section transcription
│       ├── translation/       # per-page/section English
│       ├── proofing-notes.yaml# human flags from the viewer
│       └── status.yaml        # per-work state (single source of truth)
└── output/                    # Generated EN + LA HTML + style.css + index.html
```

## Components

### 1. `project.yaml` (per-project config)

Holds the choices that vary per project/work, so skills stay generic:
- Work metadata: title, author display name + Latin name, source language (`la` / `grc`).
- Transcription mode: `normalize` (default — correct OCR artifacts, long-s → s) vs `diplomatic`.
- Translation conventions: target register, Bible-reference style (**Douay-Rheims default**), proper-name handling, exclude-editorial-apparatus flag (generalized Crampon mechanism).
- HTML conventions: heading format (default `Chapter IV: Title`), simple-tags policy.
- Publish config (filled in by `publish`): repo name, visibility, Pages URL.

### 2. `status.yaml` (per-work state)

Single source of truth Claude reads on `start` to know what's done and what's next. Example:
```yaml
work: in-genesin-i-iii
title: "Commentary on Genesis I–III"
source_pdf: source/in_genesin.pdf
ocr_method: claude-vision        # or "surya"
template_detached: true
stages:
  ingest:     { done: true,  pages: 92 }
  transcribe: { done: false, completed_pages: 40, total: 92 }
  translate:  { done: false }
  build_html: { done: false }
  publish:    { done: false }
```
Both the dashboard and viewer render from this file.

### 3. The guided flow (`start` skill)

Runs whenever the user opens Claude / says "let's get started":
1. Checks global setup (reads dashboard check results).
2. Scans `source/` and `work/` to find works + their `status.yaml`.
3. **Brand-new project** (no work folders): friendly orientation — "Welcome! Do you have a PDF ready, or want me to explain how this works first?"
4. **New PDF in `source/` with no work folder:** offers to ingest it.
5. **In-progress work:** "Work X is transcribed through page 40 of 92. Continue?" → hands off to the right stage skill.
6. On resume after a `/compact`, reconstructs state purely from `status.yaml` (seamless).

### 4. Setup dashboard (`scripts/dashboard.py` → localhost)

Informational only (Claude does the installing/work). Shows:
- **Dependency checklist** with live status (✅/❌/⏳ optional): Python, `pdftoppm` (poppler), ImageMagick, optional Surya venv, `git`, `gh`. Each row: what it's for + copy-paste install command.
- **OCR method card:** whether Surya is installed, which method this project uses, and a "which should I pick?" explainer. Default **Claude vision**; Surya offered when page complexity (dense multi-column footnotes) warrants and the user will install it.
- **Works overview:** stage progress bars per work, read from `status.yaml`.

### 5. Pipeline stages

**`ingest-pdf`** (mechanical): `extract_pages.py` (PDF → `pages/page-NNN.png` @ 300dpi; book-spread split for two-page scans). For Claude vision, pre-generates crops (quarters + halves, baronius technique). Writes page count to `status.yaml`.

**`transcribe`** (judgment, agent fan-out): page images → source text.
- *Claude vision:* fan out agents per batch (~6 pages), reading crops, transcribing Latin/Greek.
- *Surya:* run OCR + optional de-column, agents clean up.
- Transcription discipline from baronius (long-s, u/v, æ/œ, rejoin hyphenated line breaks); `normalize` mode (default) corrects OCR artifacts, `diplomatic` preserves them — a `project.yaml` setting.
- Output: per-page transcription, each block tagged with its `page` (for later anchoring).
- Encodes pitfalls: long-s→s misreads, two-column de-interleaving, "open the PNG directly if a section looks missing from OCR."

**`translate`** (judgment, agent fan-out): source → English.
- Per-page/section JSON: `{ page, type, source, english, notes }`; types `heading/body/footnote/scripture/marginal_note`.
- Rules carried over: **Trinity pronoun capitalization** (He/Him/Himself), scripture quotations flagged for `<em>`, editorial-apparatus tagging (generalized Crampon exclusion), `uncertain` notes for human review.
- Conventions from `project.yaml` (register, Douay-Rheims references, proper names) — inspired by baronius `docs/lang_conventions/`.

**`build-html`** (assembly): transcription + translation → `output/<work>.html` (English) + `output/<work>_la.html` (Latin parallel).
- lapide simple-tags convention (`<p>`, `<hr />`, `<b>`, `<em>`), TOC with anchor IDs, `<hr />` before each section, scripture/footnotes in `<em>`, consistent heading format from `project.yaml`.
- Threads **page provenance** through to proofreading markup (see below).
- Agent fan-out by logical section, ~6 pages/batch, with documented boundary-overlap handling.

### 6. Proofreading markup & viewer

**Markup:** every content block carries source-page provenance, invisible in normal viewing:
```html
<p data-page="007" data-region="q3_bottom_left">78. Therefore Moses says…</p>
```
- `data-page` always present (guaranteed anchor).
- `data-region` optional/best-effort (the crop Claude vision read, or Surya bbox). Applied to both EN and LA files (both built from the same page-tagged data).

**Viewer (`scripts/viewer.py` → localhost):** two-pane proofreading page.
- Left: generated HTML (English; toggle to Latin).
- Right: source scan. Scrolling/clicking a block jumps the right pane to that page's PNG (via `data-page`); highlights/zooms the crop if `data-region` exists.
- **Flag button** per block → user types a quick note → written to `work/<name>/proofing-notes.yaml` keyed by page+block.

**Proofing loop:** build HTML → open viewer → user skims scan-vs-translation → one-click flags issues → `proofread` skill reads `proofing-notes.yaml` and fixes flagged blocks (re-checking the scan) → rebuild. Human only *spots*; Claude *fixes*. The viewer is read-mostly (only writes flags); Claude stays the single writer of content.

### 7. Compaction & token efficiency

The enabler: **all state lives on disk**, so context is disposable — after `/compact`, Claude re-reads `status.yaml` + relevant files and resumes exactly.

- **Architectural (passive):** agent fan-out is the primary token strategy — each agent burns heavy context (page images, OCR cleanup, long Latin) in its *own* subagent context and returns only a written file + one-line summary. The main thread never accumulates the heavy stuff. Stages communicate through files, not history.
- **Process (active):** Claude prompts for `/compact` at good moments, written as named heuristics in `CLAUDE.md` + inline reminders at the end of each stage skill:
  - At every **stage boundary** (just-finished details are now on disk).
  - After each **committed batch** within a long stage (~every 2–3 batches on a 90-page book).
  - **Before a large fan-out** (start orchestration from a clean baseline).
  - On a **size signal** (long session) — proactively, before auto-compaction.
- `start` reconstructs from `status.yaml` on resume, so mid-project compaction is seamless. The user is reassured: "safe to compact anytime — I keep everything on disk."

### 8. Publishing (`publish` skill — Claude-guided GitHub Pages)

Hybrid: Claude does what it can via `git`/`gh`; the user does only the steps requiring their credentials/clicks.
1. **Check prerequisites** from dashboard (`git`, `gh` installed + authed). If `gh` not authed, Claude prints `gh auth login` and tells the user to run it with the `!` prefix, then waits.
2. **Build index** — generate `output/index.html` linking all works (lapide index pattern); simple landing page for a single-work project.
3. **Init the publish repo** — `git init` inside `output/` (separate from the project clone), commit the site.
4. **Create GitHub repo** — `gh repo create <name> --public --source=output --push`; manual fallback (create on github.com, paste remote URL back) if `gh` unavailable.
5. **Enable Pages** — via `gh api`, or the exact click-path (Settings → Pages → Source: main / root → Save) with the resulting URL.
6. **Report live URL** and write `publish.done: true` + URL to `status.yaml`.
- **Re-publishing:** detects existing publish config → just `git add/commit/push`; Pages redeploys.
- **Outward-action stance:** Claude confirms before any public/outward action ("This will create a *public* repo named X and put the site online — proceed?"), and explains the public-vs-private/Pages tradeoff.

## Git topology & detaching from the template

Three independent git contexts:
1. **Template repo** — `farant/translation-template` (what users start from).
2. **User's project** — their copy of the template (PDFs + work data).
3. **Published site** — created from `output/` by `publish`, a *separate* repo under the user's account.

What keeps it safe: **the published site is always its own repo** (`git init` in `output/` → `gh repo create`), independent of the project's `origin`. So publishing never targets `farant/translation-template`, and a stray push there is rejected for lack of write access anyway.

Two layers to remove confusion:
- **(a) Recommend "Use this template"** — mark `farant/translation-template` as a GitHub **template repository**; README leads with the green **Use this template** button → fresh repo under the user's account, `origin` already theirs, nothing to detach.
- **(b) Detach-on-clone** — if a user `git clone`s instead, `setup`/`start` detects `origin` pointing at `farant/translation-template` and offers: "This project is still linked to the original template repo. Want me to detach it so it's fully yours?" → `git remote remove origin` (+ optional fresh `git init`). Recorded as `template_detached: true` so it asks once.
- **`.gitignore`** keeps heavy/generated artifacts (`.venv/`, `source/*.pdf`, `work/**/*.png`, `output/`) out of the project repo; the published site comes from the separate `publish` flow.

## Distribution

**One-paragraph share message:**
> "Translating a Latin (or Greek) Catholic text into English: go to **github.com/farant/translation-template** and click the green **Use this template** button to make your own copy. Download it, drop your PDF into the `source/` folder, then open the folder in **Claude Code** and say *'let's get started.'* Claude walks you through the rest — it'll even help you install anything that's missing."

**README quickstart (numbered):**
1. **Install Claude Code** — the one prerequisite Claude can't do for them.
2. **Get your copy** — "Use this template" → download/clone.
3. **Add your PDF** — drop in `source/`.
4. **Open in Claude Code, say "let's get started."** Claude opens the dashboard, helps install missing tools, helps choose OCR method, then walks ingest → transcribe → translate → build → proofread → publish.
5. **(Optional) Publish** — say "let's publish it"; Claude sets up GitHub Pages.

README is written for a non-technical reader (no jargon, dashboard/viewer screenshots). Fallback for non-GitHub users: "download ZIP" from the green Code button.

## Error handling & edge cases

- **Missing dependencies:** dashboard shows ❌ with the install command; Claude offers to run it. Pipeline stages check for what they need before starting and route the user to `setup` if missing.
- **OCR gaps:** if a section looks missing from OCR, agents open the page PNG/crop directly (carried convention). Uncertain readings flagged as notes for the proofing loop.
- **Page/section boundary overlap:** documented handling — agents coordinate at boundaries; duplicates removed at HTML assembly; only complete logical sections published.
- **Resuming mid-stage:** `completed_pages` in `status.yaml` lets `transcribe`/`translate` pick up where they left off.
- **`gh` not authenticated / no GitHub account:** manual fallbacks throughout publish; Claude never blocks on an action only the user can take — it instructs and waits.
- **Stale template link:** detach-on-clone handles it; separate publish repo prevents damage regardless.

## Testing strategy

- **Scripts** (`extract_pages`, `crop_page`, `build_html`): unit-tested on a small fixture PDF (a 2–3 page sample) — correct page count, crop outputs, well-formed HTML with expected `data-page` attributes.
- **HTML structural checks:** a `verify` script (adapting lapide's `verify-lt.py`) compares EN vs LA parity (`<p>`, `<hr />`, `<em>`, anchor counts) and checks every block has a `data-page`.
- **End-to-end smoke test:** a tiny bundled sample work (a few public-domain Latin pages) run through ingest → transcribe → translate → build, asserting `output/` produces valid EN + LA HTML.
- **Skills:** validated by running the guided flow against the sample work and confirming `status.yaml` transitions correctly and the viewer/dashboard render.

## Open questions / future extensions

- Multi-language fan-out beyond EN + LA (Spanish, French, etc.) — `translate`/`build-html` already structure data per-block, so adding languages is additive.
- Dashboard action buttons (trigger Claude) — deferred; informational in v1.
- Structured/queryable data model (baronius-style) — deferred; HTML-first in v1.
- Surya bbox → `data-region` precision for the viewer.
```
