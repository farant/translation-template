"""Load project config and read/update per-work status files."""
from pathlib import Path
import yaml


def load_project(root):
    """Load project.yaml from the given project root directory."""
    path = Path(root) / "project.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_status(status_path):
    with open(status_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def update_status(status_path, key_path, value):
    """Set a nested key (list of keys) in a status.yaml file and write it back."""
    data = load_status(status_path)
    node = data
    for key in key_path[:-1]:
        node = node.setdefault(key, {})
    node[key_path[-1]] = value
    with open(status_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return data
