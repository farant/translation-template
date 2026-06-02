# Setup Dashboard & Proofreading Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the two localhost web apps from the design spec — an informational **setup dashboard** (dependency/OCR-method/works status) and a side-by-side **proofreading viewer** (generated HTML beside the source scan, with one-click flagging) — on top of the Plan 1 foundation.

**Architecture:** Stdlib-only Python `http.server` (no Node, no framework, no extra deps — preserves zero-setup for non-technical users). Each app is built around a pure `route(method, path, body) -> Response` function with a thin shared HTTP adapter (`webserver.py`), so all routing and data logic is unit-testable without opening sockets. Data comes from on-disk files already produced by Plan 1 (`work/*/status.yaml`, `output/*.html`, `work/*/pages/*.png`). The dashboard is read-only; the viewer's only write is appending human flags to `work/<name>/proofing-notes.yaml`.

**Tech Stack:** Python 3.11+ stdlib (`http.server`, `json`, `shutil`, `subprocess`, `mimetypes`), `PyYAML` (already a dep), `pytest`. Static UI is plain HTML/CSS/vanilla JS (no build step). Run tests with `.venv/bin/pytest` (the venv from Plan 1).

---

## Context from Plan 1 (already built, on `main`)

- `scripts/config.py` — `load_status(path)`, `load_project(root)`, `update_status(...)`.
- `scripts/build_html.py` — emits `output/<work>.html` + `output/<work>_la.html`; content blocks are `<p data-page="NNN" data-region="...">`.
- `scripts/verify.py` — EN/LA parity.
- `work/<name>/status.yaml` shape: `{ work, title, source_pdf, ocr_method, template_detached, stages: {ingest, transcribe, translate, build_html, publish} }`.
- A bundled `work/sample-work/` exists. `output/` is gitignored (generated).
- Tests live in `tests/`; shared fixtures in `tests/conftest.py`. Test runner: `.venv/bin/pytest`.

## File structure (this plan)

- Create: `scripts/webserver.py` — shared HTTP plumbing: `Response`, `json_response`, `safe_join`, `file_response`, `make_server`, `serve`.
- Create: `scripts/checks.py` — dependency detection (`check_tool`, `all_checks`).
- Create: `scripts/dashboard_data.py` — `works_overview`, `dashboard_state`.
- Create: `scripts/dashboard.py` — `make_route(repo_root)` + `__main__` (serves the dashboard).
- Create: `dashboard/index.html`, `dashboard/app.js`, `dashboard/style.css` — dashboard UI.
- Create: `scripts/proofing.py` — `load_flags`, `add_flag` (proofing-notes.yaml).
- Create: `scripts/viewer_data.py` — `available_works`.
- Create: `scripts/viewer.py` — `make_route(repo_root)` + `__main__` (serves the viewer).
- Create: `viewer/index.html`, `viewer/app.js`, `viewer/style.css` — viewer UI.
- Create: `tests/test_webserver.py`, `tests/test_checks.py`, `tests/test_dashboard.py`, `tests/test_proofing.py`, `tests/test_viewer.py`, `tests/test_web_integration.py`.

---

### Task 1: `webserver.py` — shared HTTP plumbing

**Files:**
- Create: `scripts/webserver.py`
- Test: `tests/test_webserver.py`

- [ ] **Step 1: Write failing tests**

`tests/test_webserver.py`:
```python
from scripts import webserver


def test_json_response_encodes_body_and_type():
    r = webserver.json_response({"a": 1})
    assert r.status == 200
    assert r.content_type == "application/json"
    assert r.body == b'{"a": 1}'


def test_safe_join_allows_inside(tmp_path):
    (tmp_path / "sub").mkdir()
    target = webserver.safe_join(tmp_path, "sub/file.png")
    assert target == (tmp_path / "sub" / "file.png").resolve()


def test_safe_join_rejects_traversal(tmp_path):
    assert webserver.safe_join(tmp_path, "../../etc/passwd") is None
    assert webserver.safe_join(tmp_path, "/etc/passwd") is None


def test_file_response_serves_known_type(tmp_path):
    f = tmp_path / "page.png"
    f.write_bytes(b"\x89PNG")
    r = webserver.file_response(f)
    assert r.status == 200
    assert r.content_type == "image/png"
    assert r.body == b"\x89PNG"


def test_file_response_missing_is_404(tmp_path):
    r = webserver.file_response(tmp_path / "nope.html")
    assert r.status == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_webserver.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.webserver`.

- [ ] **Step 3: Write `scripts/webserver.py`**

```python
"""Shared HTTP plumbing for the dashboard and viewer apps.

Each app supplies a pure ``route(method, path, body) -> Response`` function;
this module adapts it onto stdlib http.server. Keeping routing pure makes it
unit-testable without sockets.
"""
import http.server
import json
from collections import namedtuple
from pathlib import Path

Response = namedtuple("Response", "status content_type body")  # body is bytes

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript",
    ".css": "text/css",
    ".png": "image/png",
    ".json": "application/json",
}


def json_response(obj, status=200):
    return Response(status, "application/json", json.dumps(obj).encode("utf-8"))


def safe_join(base, rel):
    """Resolve ``rel`` under ``base``; return the Path only if it stays inside
    ``base`` (defends against ../ traversal and absolute paths). Else None."""
    base = Path(base).resolve()
    target = (base / rel.lstrip("/")).resolve()
    if target == base or base in target.parents:
        return target
    return None


def file_response(path):
    path = Path(path)
    if not path.is_file():
        return Response(404, "text/plain", b"not found")
    ctype = CONTENT_TYPES.get(path.suffix, "application/octet-stream")
    return Response(200, ctype, path.read_bytes())


def make_handler(route_fn):
    class Handler(http.server.BaseHTTPRequestHandler):
        def _dispatch(self, method):
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length else b""
            resp = route_fn(method, self.path, body)
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.content_type)
            self.send_header("Content-Length", str(len(resp.body)))
            self.end_headers()
            self.wfile.write(resp.body)

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def log_message(self, *args):
            pass  # quiet

    return Handler


def make_server(route_fn, port):
    """Build (but don't start) an HTTPServer bound to 127.0.0.1:port.
    Port 0 picks an ephemeral port (server.server_address[1] reveals it)."""
    return http.server.HTTPServer(("127.0.0.1", port), make_handler(route_fn))


def serve(route_fn, port):
    server = make_server(route_fn, port)
    print(f"Serving on http://127.0.0.1:{server.server_address[1]}  (Ctrl-C to stop)")
    server.serve_forever()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_webserver.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/webserver.py tests/test_webserver.py
git commit -m "feat: shared http.server plumbing for web apps"
```

---

### Task 2: `checks.py` — dependency detection

**Files:**
- Create: `scripts/checks.py`
- Test: `tests/test_checks.py`

- [ ] **Step 1: Write failing tests**

`tests/test_checks.py`:
```python
from scripts import checks


def test_check_tool_installed(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda name: "/usr/bin/" + name)

    class FakeProc:
        stdout = "git version 2.39.5\n"
        stderr = ""

    monkeypatch.setattr(checks.subprocess, "run", lambda *a, **k: FakeProc())
    tool = {"name": "git", "cmd": ["git", "--version"], "purpose": "vc", "install": "x"}
    result = checks.check_tool(tool)
    assert result["installed"] is True
    assert result["version"] == "git version 2.39.5"
    assert result["purpose"] == "vc"
    assert result["install"] == "x"


def test_check_tool_missing(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    tool = {"name": "gh", "cmd": ["gh", "--version"], "purpose": "p", "install": "brew install gh"}
    result = checks.check_tool(tool)
    assert result["installed"] is False
    assert result["version"] == ""
    assert result["install"] == "brew install gh"


def test_all_checks_covers_core_tools(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    names = [c["name"] for c in checks.all_checks()]
    assert {"python3", "pdftoppm", "magick", "git", "gh"}.issubset(set(names))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_checks.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.checks`.

- [ ] **Step 3: Write `scripts/checks.py`**

```python
"""Detect whether the pipeline's external tools are installed.

Used by the setup dashboard to show a live dependency checklist. Each tool
entry carries a human 'purpose' and a copy-paste 'install' command so the
dashboard (and Claude) can guide a non-technical user."""
import shutil
import subprocess

TOOLS = [
    {"name": "python3", "cmd": ["python3", "--version"],
     "purpose": "Runs the pipeline scripts", "install": "Pre-installed on macOS"},
    {"name": "pdftoppm", "cmd": ["pdftoppm", "-v"],
     "purpose": "Converts PDF pages to images", "install": "brew install poppler"},
    {"name": "magick", "cmd": ["magick", "--version"],
     "purpose": "Crops and processes page images", "install": "brew install imagemagick"},
    {"name": "git", "cmd": ["git", "--version"],
     "purpose": "Version control and publishing", "install": "xcode-select --install"},
    {"name": "gh", "cmd": ["gh", "--version"],
     "purpose": "Publishing to GitHub Pages", "install": "brew install gh"},
]


def check_tool(tool):
    """Return a status dict for one tool entry."""
    installed = shutil.which(tool["name"]) is not None
    version = ""
    if installed:
        try:
            proc = subprocess.run(tool["cmd"], capture_output=True, text=True, timeout=10)
            text = proc.stdout or proc.stderr  # some tools print version to stderr
            version = text.splitlines()[0].strip() if text.strip() else ""
        except Exception:
            version = ""
    return {
        "name": tool["name"],
        "installed": installed,
        "version": version,
        "purpose": tool["purpose"],
        "install": tool["install"],
    }


def all_checks():
    return [check_tool(t) for t in TOOLS]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_checks.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/checks.py tests/test_checks.py
git commit -m "feat: dependency detection for setup dashboard"
```

---

### Task 3: `dashboard_data.py` — works overview & dashboard state

**Files:**
- Create: `scripts/dashboard_data.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing tests**

`tests/test_dashboard.py`:
```python
import yaml
from scripts import dashboard_data


def _make_work(root, name, title, stages):
    d = root / "work" / name
    d.mkdir(parents=True)
    (d / "status.yaml").write_text(
        yaml.safe_dump({"work": name, "title": title, "ocr_method": "claude-vision",
                        "stages": stages}), encoding="utf-8")


def test_works_overview_reads_all_works(tmp_path):
    _make_work(tmp_path, "alpha", "Alpha", {"ingest": {"done": True}})
    _make_work(tmp_path, "beta", "Beta", {"ingest": {"done": False}})
    works = dashboard_data.works_overview(tmp_path / "work")
    assert [w["work"] for w in works] == ["alpha", "beta"]
    assert works[0]["title"] == "Alpha"
    assert works[0]["stages"]["ingest"]["done"] is True
    assert works[0]["ocr_method"] == "claude-vision"


def test_works_overview_empty_when_no_dir(tmp_path):
    assert dashboard_data.works_overview(tmp_path / "work") == []


def test_dashboard_state_has_checks_and_works(tmp_path, monkeypatch):
    from scripts import checks
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    _make_work(tmp_path, "alpha", "Alpha", {})
    state = dashboard_data.dashboard_state(tmp_path)
    assert "checks" in state and isinstance(state["checks"], list)
    assert [w["work"] for w in state["works"]] == ["alpha"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_dashboard.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.dashboard_data`.

- [ ] **Step 3: Write `scripts/dashboard_data.py`**

```python
"""Aggregate per-work status and dependency checks into the dashboard payload."""
from pathlib import Path
import yaml

from scripts import checks


def works_overview(work_root):
    """List each work's status (read from work/*/status.yaml), in name order."""
    work_root = Path(work_root)
    works = []
    if not work_root.is_dir():
        return works
    for status_path in sorted(work_root.glob("*/status.yaml")):
        data = yaml.safe_load(status_path.read_text(encoding="utf-8")) or {}
        works.append({
            "work": data.get("work", status_path.parent.name),
            "title": data.get("title", ""),
            "ocr_method": data.get("ocr_method", ""),
            "stages": data.get("stages", {}),
        })
    return works


def dashboard_state(repo_root):
    """Full dashboard JSON payload: dependency checks + works overview."""
    return {
        "checks": checks.all_checks(),
        "works": works_overview(Path(repo_root) / "work"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_dashboard.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard_data.py tests/test_dashboard.py
git commit -m "feat: dashboard data aggregation"
```

---

### Task 4: `dashboard.py` — route function

**Files:**
- Create: `scripts/dashboard.py`
- Test: `tests/test_dashboard.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `tests/test_dashboard.py`:
```python
import json as _json
from scripts import dashboard


def test_dashboard_route_status_endpoint(tmp_path, monkeypatch):
    from scripts import checks
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    _make_work(tmp_path, "alpha", "Alpha", {})
    route = dashboard.make_route(tmp_path)
    resp = route("GET", "/api/status", b"")
    assert resp.status == 200
    payload = _json.loads(resp.body)
    assert payload["works"][0]["work"] == "alpha"


def test_dashboard_route_serves_index(tmp_path):
    route = dashboard.make_route(tmp_path)
    resp = route("GET", "/", b"")
    # index.html is created in Task 5; here we only assert routing returns the
    # asset path's response (404 until the file exists, 200 after). Accept both
    # statuses but require the route to target text/html or 'not found'.
    assert resp.status in (200, 404)


def test_dashboard_route_unknown_is_404(tmp_path):
    route = dashboard.make_route(tmp_path)
    assert route("GET", "/nope", b"").status == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_dashboard.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.dashboard`.

- [ ] **Step 3: Write `scripts/dashboard.py`**

```python
"""Setup dashboard web app: serves a static UI + a /api/status JSON endpoint.

Run:  python -m scripts.dashboard [port]   (default 8000)
"""
import sys
from pathlib import Path

from scripts.webserver import Response, file_response, json_response, serve
from scripts.dashboard_data import dashboard_state

ASSETS = Path(__file__).resolve().parent.parent / "dashboard"


def make_route(repo_root):
    repo_root = Path(repo_root)

    def route(method, path, body):
        clean = path.split("?")[0]
        if method == "GET" and clean == "/":
            return file_response(ASSETS / "index.html")
        if method == "GET" and clean in ("/app.js", "/style.css"):
            return file_response(ASSETS / clean.lstrip("/"))
        if method == "GET" and clean == "/api/status":
            return json_response(dashboard_state(repo_root))
        return Response(404, "text/plain", b"not found")

    return route


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    serve(make_route(Path.cwd()), port)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_dashboard.py -v`
Expected: PASS (6 passed total in this file).

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard.py tests/test_dashboard.py
git commit -m "feat: dashboard route function"
```

---

### Task 5: Dashboard UI assets

**Files:**
- Create: `dashboard/index.html`, `dashboard/app.js`, `dashboard/style.css`
- Test: `tests/test_dashboard.py` (append one)

- [ ] **Step 1: Append a failing test that the index is now served**

Append to `tests/test_dashboard.py`:
```python
def test_dashboard_index_served_after_assets_exist(tmp_path):
    route = dashboard.make_route(tmp_path)
    resp = route("GET", "/", b"")
    assert resp.status == 200
    assert b"Setup Dashboard" in resp.body
    assert b"app.js" in resp.body
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/pytest tests/test_dashboard.py::test_dashboard_index_served_after_assets_exist -v`
Expected: FAIL — status 404 (index.html not created yet).

- [ ] **Step 3: Create the dashboard UI**

`dashboard/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Setup Dashboard — Translation Template</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
<h1>Setup Dashboard</h1>
<p class="sub">A quick look at what's installed and where your works stand. Claude does the installing &mdash; this page just shows status.</p>

<section>
<h2>Dependencies</h2>
<table id="checks"><tbody></tbody></table>
</section>

<section>
<h2>Your works</h2>
<div id="works"></div>
</section>

<script src="app.js"></script>
</body>
</html>
```

`dashboard/style.css`:
```css
body { font-family: -apple-system, system-ui, sans-serif; max-width: 60rem;
       margin: 2rem auto; padding: 0 1rem; color: #222; line-height: 1.5; }
h1 { margin-bottom: 0.25rem; }
.sub { color: #666; margin-top: 0; }
section { margin-top: 2rem; }
table { border-collapse: collapse; width: 100%; }
td, th { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; vertical-align: top; }
.ok { color: #1a7f37; font-weight: 600; }
.missing { color: #b3261e; font-weight: 600; }
code { background: #f4f4f4; padding: 0.1rem 0.3rem; border-radius: 3px; }
.bar { background: #eee; border-radius: 4px; height: 0.7rem; overflow: hidden; width: 14rem; display: inline-block; vertical-align: middle; }
.bar > span { display: block; height: 100%; background: #1a7f37; }
.work { margin-bottom: 1rem; }
.stage { display: inline-block; margin-right: 0.5rem; font-size: 0.85rem; }
.stage.done::before { content: "\2705 "; }
.stage.pending::before { content: "\2b1c "; }
```

`dashboard/app.js`:
```javascript
async function load() {
  const res = await fetch("/api/status");
  const data = await res.json();
  renderChecks(data.checks);
  renderWorks(data.works);
}

function renderChecks(checks) {
  const tbody = document.querySelector("#checks tbody");
  tbody.innerHTML = "";
  for (const c of checks) {
    const tr = document.createElement("tr");
    const status = c.installed
      ? `<span class="ok">&#10003; ${c.version || "installed"}</span>`
      : `<span class="missing">&#10007; missing</span>`;
    const install = c.installed ? "" : `<code>${c.install}</code>`;
    tr.innerHTML = `<td>${c.name}</td><td>${c.purpose}</td><td>${status}</td><td>${install}</td>`;
    tbody.appendChild(tr);
  }
}

function renderWorks(works) {
  const box = document.querySelector("#works");
  box.innerHTML = "";
  if (!works.length) {
    box.innerHTML = "<p>No works yet. Drop a PDF in <code>source/</code> and tell Claude “let’s get started.”</p>";
    return;
  }
  const order = ["ingest", "transcribe", "translate", "build_html", "publish"];
  for (const w of works) {
    const done = order.filter((s) => w.stages[s] && w.stages[s].done).length;
    const pct = Math.round((done / order.length) * 100);
    const stages = order
      .map((s) => `<span class="stage ${w.stages[s] && w.stages[s].done ? "done" : "pending"}">${s}</span>`)
      .join("");
    const div = document.createElement("div");
    div.className = "work";
    div.innerHTML =
      `<strong>${w.title || w.work}</strong> &middot; <span>${w.ocr_method || ""}</span><br />` +
      `<span class="bar"><span style="width:${pct}%"></span></span> ${done}/${order.length}<br />${stages}`;
    box.appendChild(div);
  }
}

load();
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_dashboard.py -v`
Expected: PASS (all in file).

- [ ] **Step 5: Manual smoke (optional but recommended)**

Run: `.venv/bin/python -m scripts.dashboard 8000` then open `http://127.0.0.1:8000` — confirm the dependency table and (for the bundled sample) a works row render. Ctrl-C to stop.

- [ ] **Step 6: Commit**

```bash
git add dashboard/ tests/test_dashboard.py
git commit -m "feat: dashboard UI assets"
```

---

### Task 6: `proofing.py` — flag read/write

**Files:**
- Create: `scripts/proofing.py`
- Test: `tests/test_proofing.py`

- [ ] **Step 1: Write failing tests**

`tests/test_proofing.py`:
```python
from scripts import proofing


def test_load_flags_empty_when_no_file(tmp_path):
    assert proofing.load_flags(tmp_path) == []


def test_add_flag_appends_and_persists(tmp_path):
    proofing.add_flag(tmp_path, "001", 3, "OCR dropped a line")
    proofing.add_flag(tmp_path, "002", 0, "wrong verse number")
    flags = proofing.load_flags(tmp_path)
    assert flags == [
        {"page": "001", "block": 3, "note": "OCR dropped a line"},
        {"page": "002", "block": 0, "note": "wrong verse number"},
    ]


def test_add_flag_round_trips_through_disk(tmp_path):
    proofing.add_flag(tmp_path, "005", 1, "faded")
    # fresh read proves it was written, not just held in memory
    assert proofing.load_flags(tmp_path)[0]["note"] == "faded"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_proofing.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.proofing`.

- [ ] **Step 3: Write `scripts/proofing.py`**

```python
"""Read/write human proofreading flags for a work.

Flags live in ``work/<name>/proofing-notes.yaml`` as a list of
``{page, block, note}`` entries. The viewer appends them on a button click;
the `proofread` skill later reads them and fixes the flagged blocks."""
from pathlib import Path
import yaml


def _notes_path(work_dir):
    return Path(work_dir) / "proofing-notes.yaml"


def load_flags(work_dir):
    path = _notes_path(work_dir)
    if not path.is_file():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def add_flag(work_dir, page, block, note):
    """Append a flag and persist. ``page`` is the data-page string, ``block``
    the 0-based index of the flagged content block on the page."""
    flags = load_flags(work_dir)
    flags.append({"page": page, "block": block, "note": note})
    _notes_path(work_dir).write_text(
        yaml.safe_dump(flags, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return flags
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_proofing.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/proofing.py tests/test_proofing.py
git commit -m "feat: proofreading flag read/write"
```

---

### Task 7: `viewer_data.py` — available works

**Files:**
- Create: `scripts/viewer_data.py`
- Test: `tests/test_viewer.py`

- [ ] **Step 1: Write failing tests**

`tests/test_viewer.py`:
```python
from scripts import viewer_data


def test_available_works_lists_english_with_latin_flag(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    (out / "alpha.html").write_text("<html></html>", encoding="utf-8")
    (out / "alpha_la.html").write_text("<html></html>", encoding="utf-8")
    (out / "beta.html").write_text("<html></html>", encoding="utf-8")  # no latin
    (out / "index.html").write_text("<html></html>", encoding="utf-8")  # skipped
    works = viewer_data.available_works(out)
    assert works == [
        {"name": "alpha", "has_latin": True},
        {"name": "beta", "has_latin": False},
    ]


def test_available_works_empty_when_no_output(tmp_path):
    assert viewer_data.available_works(tmp_path / "output") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_viewer.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.viewer_data`.

- [ ] **Step 3: Write `scripts/viewer_data.py`**

```python
"""List works that have built HTML available for proofreading."""
from pathlib import Path


def available_works(output_dir):
    """Return [{name, has_latin}] for each built English work in output_dir,
    skipping the Latin parallels and the index page."""
    output_dir = Path(output_dir)
    works = []
    if not output_dir.is_dir():
        return works
    for html in sorted(output_dir.glob("*.html")):
        name = html.stem
        if name.endswith("_la") or name == "index":
            continue
        works.append({"name": name, "has_latin": (output_dir / f"{name}_la.html").is_file()})
    return works
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_viewer.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/viewer_data.py tests/test_viewer.py
git commit -m "feat: viewer available-works listing"
```

---

### Task 8: `viewer.py` — route function (incl. file serving & flag POST)

**Files:**
- Create: `scripts/viewer.py`
- Test: `tests/test_viewer.py` (append)

- [ ] **Step 1: Append failing tests**

Append to `tests/test_viewer.py`:
```python
import json as _json
from scripts import viewer, proofing


def _repo(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "alpha.html").write_text(
        '<p data-page="001">x</p>', encoding="utf-8")
    pages = tmp_path / "work" / "alpha" / "pages"
    pages.mkdir(parents=True)
    (pages / "page-001.png").write_bytes(b"\x89PNG")
    return tmp_path


def test_viewer_lists_works(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/api/works", b"")
    assert resp.status == 200
    assert _json.loads(resp.body) == [{"name": "alpha", "has_latin": False}]


def test_viewer_serves_output_html(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/output/alpha.html", b"")
    assert resp.status == 200
    assert b"data-page" in resp.body


def test_viewer_serves_page_image(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/pages/alpha/pages/page-001.png", b"")
    assert resp.status == 200
    assert resp.content_type == "image/png"


def test_viewer_rejects_path_traversal(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/output/../work/alpha/pages/page-001.png", b"")
    assert resp.status == 403


def test_viewer_flag_post_writes_note(tmp_path):
    repo = _repo(tmp_path)
    route = viewer.make_route(repo)
    body = _json.dumps({"work": "alpha", "page": "001", "block": 0, "note": "typo"}).encode()
    resp = route("POST", "/api/flag", body)
    assert resp.status == 200
    flags = proofing.load_flags(repo / "work" / "alpha")
    assert flags == [{"page": "001", "block": 0, "note": "typo"}]


def test_viewer_unknown_is_404(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    assert route("GET", "/nope", b"").status == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_viewer.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.viewer`.

- [ ] **Step 3: Write `scripts/viewer.py`**

```python
"""Proofreading viewer web app: generated HTML beside the source scan, with
one-click flagging.

Routes:
  GET  /                       -> viewer UI
  GET  /app.js, /style.css     -> UI assets
  GET  /api/works              -> [{name, has_latin}]
  GET  /output/<file>          -> a built HTML file (EN or LA)
  GET  /pages/<work>/pages/<f> -> a source page PNG
  POST /api/flag               -> append {work, page, block, note} to proofing-notes.yaml

Run:  python -m scripts.viewer [port]   (default 8001)
"""
import json
import sys
from pathlib import Path

from scripts.webserver import Response, file_response, json_response, safe_join, serve
from scripts.viewer_data import available_works
from scripts.proofing import add_flag

ASSETS = Path(__file__).resolve().parent.parent / "viewer"


def make_route(repo_root):
    repo_root = Path(repo_root)
    output_dir = repo_root / "output"
    work_dir = repo_root / "work"

    def route(method, path, body):
        clean = path.split("?")[0]
        if method == "GET" and clean == "/":
            return file_response(ASSETS / "index.html")
        if method == "GET" and clean in ("/app.js", "/style.css"):
            return file_response(ASSETS / clean.lstrip("/"))
        if method == "GET" and clean == "/api/works":
            return json_response(available_works(output_dir))
        if method == "GET" and clean.startswith("/output/"):
            target = safe_join(output_dir, clean[len("/output/"):])
            return file_response(target) if target else Response(403, "text/plain", b"forbidden")
        if method == "GET" and clean.startswith("/pages/"):
            target = safe_join(work_dir, clean[len("/pages/"):])
            return file_response(target) if target else Response(403, "text/plain", b"forbidden")
        if method == "POST" and clean == "/api/flag":
            data = json.loads(body or b"{}")
            add_flag(work_dir / data["work"], data["page"], data["block"], data["note"])
            return json_response({"ok": True})
        return Response(404, "text/plain", b"not found")

    return route


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    serve(make_route(Path.cwd()), port)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_viewer.py -v`
Expected: PASS (8 passed total in file).

- [ ] **Step 5: Commit**

```bash
git add scripts/viewer.py tests/test_viewer.py
git commit -m "feat: viewer route function with file serving and flagging"
```

---

### Task 9: Viewer UI assets

**Files:**
- Create: `viewer/index.html`, `viewer/app.js`, `viewer/style.css`
- Test: `tests/test_viewer.py` (append one)

- [ ] **Step 1: Append a failing test that the index is served**

Append to `tests/test_viewer.py`:
```python
def test_viewer_index_served_after_assets_exist(tmp_path):
    route = viewer.make_route(_repo(tmp_path))
    resp = route("GET", "/", b"")
    assert resp.status == 200
    assert b"Proofreading" in resp.body
    assert b"app.js" in resp.body
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/pytest tests/test_viewer.py::test_viewer_index_served_after_assets_exist -v`
Expected: FAIL — status 404.

- [ ] **Step 3: Create the viewer UI**

`viewer/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Proofreading — Translation Template</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
<header>
  <strong>Proofreading</strong>
  <select id="work"></select>
  <label><input type="checkbox" id="latin" /> Latin</label>
  <span id="hint">Click a paragraph to see its source page. Use &#9873; to flag an issue.</span>
</header>
<main>
  <div id="left"><iframe id="frame" title="Generated text"></iframe></div>
  <div id="right"><img id="scan" alt="Source scan" /></div>
</main>
<script src="app.js"></script>
</body>
</html>
```

`viewer/style.css`:
```css
* { box-sizing: border-box; }
body { font-family: -apple-system, system-ui, sans-serif; margin: 0; height: 100vh;
       display: flex; flex-direction: column; }
header { padding: 0.5rem 1rem; border-bottom: 1px solid #ddd; display: flex;
         gap: 1rem; align-items: center; flex-wrap: wrap; }
#hint { color: #666; font-size: 0.85rem; }
main { flex: 1; display: flex; min-height: 0; }
#left, #right { width: 50%; overflow: auto; }
#left { border-right: 1px solid #ddd; }
#frame { width: 100%; height: 100%; border: 0; }
#scan { width: 100%; display: block; }
/* injected into the iframe document via app.js */
</style>
```

`viewer/app.js`:
```javascript
const frame = document.getElementById("frame");
const scan = document.getElementById("scan");
const workSel = document.getElementById("work");
const latin = document.getElementById("latin");

let currentWork = null;

async function init() {
  const works = await (await fetch("/api/works")).json();
  workSel.innerHTML = works
    .map((w) => `<option value="${w.name}" data-latin="${w.has_latin}">${w.name}</option>`)
    .join("");
  workSel.addEventListener("change", loadWork);
  latin.addEventListener("change", loadWork);
  if (works.length) loadWork();
}

function loadWork() {
  currentWork = workSel.value;
  const opt = workSel.selectedOptions[0];
  const wantLatin = latin.checked && opt && opt.dataset.latin === "true";
  const suffix = wantLatin ? "_la" : "";
  frame.src = `/output/${currentWork}${suffix}.html`;
}

frame.addEventListener("load", wireFrame);

function wireFrame() {
  const doc = frame.contentDocument;
  if (!doc) return;
  const blocks = Array.from(doc.querySelectorAll("[data-page]"));
  blocks.forEach((el, index) => {
    el.style.cursor = "pointer";
    el.addEventListener("click", () => showPage(el.dataset.page));
    const flag = doc.createElement("button");
    flag.textContent = "⚑";
    flag.title = "Flag an issue here";
    flag.style.cssText = "margin-left:.4rem;border:0;background:none;cursor:pointer;color:#b3261e;";
    flag.addEventListener("click", (e) => {
      e.stopPropagation();
      const note = doc.defaultView.prompt("What's wrong with this block?");
      if (note) sendFlag(el.dataset.page, index, note, flag);
    });
    el.appendChild(flag);
  });
}

function showPage(page) {
  scan.src = `/pages/${currentWork}/pages/page-${page}.png`;
}

async function sendFlag(page, block, note, btn) {
  await fetch("/api/flag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ work: currentWork, page, block, note }),
  });
  btn.textContent = "✓";
  btn.style.color = "#1a7f37";
}

init();
```

Note: the viewer uses the browser `prompt()` for the flag note. This is intentional (simple, no modal framework); it runs inside the iframe's own window, not the automation-controlled top window.

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_viewer.py -v`
Expected: PASS (all in file).

- [ ] **Step 5: Manual smoke (optional but recommended)**

First build the sample work's HTML so there's something to view:
```bash
.venv/bin/python -m scripts.build_html work/sample-work "Sample Work" output
.venv/bin/python -m scripts.viewer 8001
```
Open `http://127.0.0.1:8001`, pick `sample-work`, click a paragraph (the source pane will 404 since the sample has no real page PNGs — expected; real works will have them). Ctrl-C to stop.

- [ ] **Step 6: Commit**

```bash
git add viewer/ tests/test_viewer.py
git commit -m "feat: viewer UI assets"
```

---

### Task 10: Server integration smoke test & docs

**Files:**
- Create: `tests/test_web_integration.py`
- Modify: `CLAUDE.md` (append run commands)

- [ ] **Step 1: Write the failing integration test**

`tests/test_web_integration.py`:
```python
"""Boot each server on an ephemeral port in a thread and hit a real endpoint."""
import http.client
import json
import threading
import yaml

from scripts import webserver, dashboard, viewer


def _serve_in_thread(route):
    server = webserver.make_server(route, 0)  # port 0 = ephemeral
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _get(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", path)
    resp = conn.getresponse()
    return resp.status, resp.read()


def test_dashboard_status_over_http(tmp_path, monkeypatch):
    from scripts import checks
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    w = tmp_path / "work" / "alpha"
    w.mkdir(parents=True)
    (w / "status.yaml").write_text(yaml.safe_dump({"work": "alpha", "stages": {}}), encoding="utf-8")
    server = _serve_in_thread(dashboard.make_route(tmp_path))
    try:
        status, body = _get(server.server_address[1], "/api/status")
        assert status == 200
        assert json.loads(body)["works"][0]["work"] == "alpha"
    finally:
        server.shutdown()


def test_viewer_works_over_http(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "alpha.html").write_text("<p data-page='1'>x</p>", encoding="utf-8")
    server = _serve_in_thread(viewer.make_route(tmp_path))
    try:
        status, body = _get(server.server_address[1], "/api/works")
        assert status == 200
        assert json.loads(body)[0]["name"] == "alpha"
    finally:
        server.shutdown()
```

- [ ] **Step 2: Run it to verify it fails (then passes)**

Run: `.venv/bin/pytest tests/test_web_integration.py -v`
Expected: PASS — the modules already exist from prior tasks, so this should pass immediately. (If it fails, fix the integration issue it surfaces before continuing.)

- [ ] **Step 3: Append run commands to `CLAUDE.md`**

Add this section to the end of `CLAUDE.md`:
```markdown

## Web apps (localhost)

- Setup dashboard:  `.venv/bin/python -m scripts.dashboard [port]`  (default 8000)
  Shows dependency checklist + per-work progress. Read-only/informational.
- Proofreading viewer:  `.venv/bin/python -m scripts.viewer [port]`  (default 8001)
  Generated HTML beside the source scan; click a paragraph to see its page,
  click the flag (&#9873;) to record an issue into `work/<name>/proofing-notes.yaml`.
  Build a work's HTML first: `.venv/bin/python -m scripts.build_html work/<name> "<Title>" output`.
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (all Plan 1 + Plan 2 tests).

- [ ] **Step 5: Commit**

```bash
git add tests/test_web_integration.py CLAUDE.md
git commit -m "test: web server integration smoke test; document run commands"
```

---

## Self-review notes

**Spec coverage (this plan's slice):**
- Setup dashboard with dependency checklist (live status + purpose + install command) ✓ Tasks 2,3,4,5.
- OCR-method visibility / works overview with stage progress ✓ Tasks 3,5 (ocr_method shown per work; stage bars).
- Dashboard is informational only (no action buttons) ✓ — no POST endpoints on the dashboard.
- Proofreading markup consumed: viewer reads `data-page` to jump to the page image ✓ Task 9 (`app.js` querySelectorAll("[data-page]")).
- Side-by-side viewer (generated HTML left, scan right; toggle Latin) ✓ Tasks 8,9.
- One-click flag → `proofing-notes.yaml`; viewer is the single writer of flags, Claude fixes later ✓ Tasks 6,8,9.
- Both apps serve from on-disk state already produced by Plan 1 ✓.
Out of scope by design (later/other plans): the `proofread` skill that consumes flags, `data-region` zoom/highlight precision (v1 jumps to the page; region highlight is a future enhancement), dashboard action buttons.

**Known intentional limitations / decisions:**
- `data-region` is not yet used for zoom/highlight — the viewer jumps to the whole page PNG. Page-level is the guaranteed anchor per the spec; region precision is a documented future enhancement.
- Servers bind to `127.0.0.1` only (local-only, no external exposure).
- The flag note uses the in-iframe `prompt()` — simple and dependency-free; it lives in the iframe window, not the top automation-controlled window.
- Page images are served from `work/<name>/pages/page-NNN.png`; the sample work ships without real page PNGs, so its scan pane will 404 (expected — real ingested works have them).

**Placeholder scan:** none — every code/test step is complete.

**Type/name consistency:** `Response`, `json_response`, `safe_join`, `file_response`, `make_server`, `serve` (webserver); `check_tool`, `all_checks`, `TOOLS` (checks); `works_overview`, `dashboard_state` (dashboard_data); `make_route` (dashboard + viewer, distinct closures); `load_flags`, `add_flag` (proofing); `available_works` (viewer_data). The `/pages/<work>/pages/<file>` URL shape is consistent between `viewer.py` routing (`safe_join(work_dir, ...)`) and `app.js` (`/pages/${currentWork}/pages/page-${page}.png`).
```
