"""End-to-end: bundled sample translation -> EN+LA HTML -> verify passes."""
from pathlib import Path
from scripts import build_html, verify

REPO = Path(__file__).resolve().parent.parent


def test_sample_work_builds_and_verifies(tmp_path):
    work = REPO / "work" / "sample-work"
    out = tmp_path / "output"
    en, la = build_html.build_work(work, "Sample Work", out)
    ok, problems = verify.verify_pair(en, la)
    assert ok, problems
