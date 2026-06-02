---
name: publish
description: Use to publish the finished site to GitHub Pages — the final stage. Triggered after proofreading, or when the user says "publish it" or "put it online".
---

# Publish to GitHub Pages

You do what you can; the user does the credential/browser steps. **Confirm before any public action.**

1. **Prereqs:** ensure `git` and `gh` are installed (setup skill / dashboard). If `gh` isn't authenticated, tell the user to run `! gh auth login` in the session, then wait.
2. **Build an index:** generate `output/index.html` linking each built work (title + link). For a single work, a simple landing page.
3. **Confirm:** "This will create a *public* GitHub repo named `<name>` and put the site online — proceed?" Explain public-vs-private (Pages needs a public repo or a paid plan).
4. **Create the publish repo** (separate from this project): in `output/`, `git init`, commit, then `gh repo create <name> --public --source=output --push`. If `gh` is unavailable, give the manual steps (create on github.com, add the remote, push).
5. **Enable Pages:** via `gh api`, or tell them: repo Settings → Pages → Source: `main` / root → Save. Report the live URL.
6. **Record** the repo + URL in `status.yaml` (`publish.done`). Re-publishing later is just `git add/commit/push` inside `output/`.

Never push the *project* repo to the template; the published site is its own repo. See CLAUDE.md "Git topology & publishing".
