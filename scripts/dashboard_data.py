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
