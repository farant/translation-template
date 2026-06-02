# Translation Template

A Claude-driven template for turning scanned **Catholic Latin (or Greek) texts** into **English** — and publishing them as a clean website. You mostly just talk to Claude; it does the technical work and even helps you install what's missing.

## What you need first

- **[Claude Code](https://claude.com/claude-code)** installed. (This is the one thing Claude can't install for you — you need it to talk to Claude.)

That's it. Claude helps with everything else (PDF tools, image tools, GitHub).

## Quickstart

1. **Make your own copy.** On this repo's GitHub page, click the green **Use this template** button → it creates a fresh copy under your account. Download or clone it to your computer.
2. **Add your PDF.** Put your scanned Latin/Greek PDF into the `source/` folder.
3. **Open the folder in Claude Code** and say **"let's get started."**

From there Claude will:
- open a **setup dashboard** (a web page showing what's installed) and help install anything missing,
- help you pick how to read the scans,
- then walk you through: read the pages → translate to English → build the web pages → **proofread side-by-side with the original scans** → publish.

4. **Proofread.** Claude opens a viewer where the generated text sits next to the original scan. Click a paragraph to see its page; click the flag (⚑) to mark anything wrong — Claude fixes the flagged spots for you.
5. **Publish (optional).** Say "let's publish it" and Claude sets up a free GitHub Pages website with you.

## Tips

- It's always safe to run `/compact` when Claude suggests it — everything is saved to disk, so nothing is lost.
- You can hold several books in one project; each lives under `work/<name>/`.

## For the curious (how it's built)

Plain Python helper scripts under `scripts/` do the mechanical steps (PDF → images, image cropping, HTML assembly). The judgment steps (reading, translating, formatting) are done by Claude. Two small local web apps (the setup dashboard and the proofreading viewer) are stdlib-only — no heavy setup. The guidance Claude follows lives in `CLAUDE.md` and `.claude/skills/`.
