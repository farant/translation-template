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
