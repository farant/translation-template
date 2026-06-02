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
