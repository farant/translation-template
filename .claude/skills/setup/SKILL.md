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
