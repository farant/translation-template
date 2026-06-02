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
