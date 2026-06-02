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
