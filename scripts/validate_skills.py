"""Validate project skill files.

Each skill is `.claude/skills/<name>/SKILL.md` with YAML frontmatter carrying
a `name` (matching the directory) and a non-empty `description`. This guards
against silently broken skills."""
from pathlib import Path
import yaml


def parse_frontmatter(text):
    """Return the frontmatter dict, or None if absent/malformed."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None


def validate_skill(skill_dir):
    """Return a list of problem strings for one skill directory (empty = valid)."""
    skill_dir = Path(skill_dir)
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]
    fm = parse_frontmatter(md.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{skill_dir.name}: missing or malformed frontmatter"]
    problems = []
    if fm.get("name") != skill_dir.name:
        problems.append(f"{skill_dir.name}: frontmatter name {fm.get('name')!r} != directory")
    if not (fm.get("description") or "").strip():
        problems.append(f"{skill_dir.name}: empty description")
    return problems


def validate_all(skills_root):
    """Map each skill directory name to its list of problems."""
    skills_root = Path(skills_root)
    results = {}
    for md in sorted(skills_root.glob("*/SKILL.md")):
        results[md.parent.name] = validate_skill(md.parent)
    return results
