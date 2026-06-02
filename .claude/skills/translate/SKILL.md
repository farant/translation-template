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
