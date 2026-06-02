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
