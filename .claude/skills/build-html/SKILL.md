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
