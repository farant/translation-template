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

## Web apps (localhost)

- Setup dashboard:  `.venv/bin/python -m scripts.dashboard [port]`  (default 8000)
  Shows dependency checklist + per-work progress. Read-only/informational.
- Proofreading viewer:  `.venv/bin/python -m scripts.viewer [port]`  (default 8001)
  Generated HTML beside the source scan; click a paragraph to see its page,
  click the flag (&#9873;) to record an issue into `work/<name>/proofing-notes.yaml`.
  Build a work's HTML first: `.venv/bin/python -m scripts.build_html work/<name> "<Title>" output`.
