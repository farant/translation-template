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
