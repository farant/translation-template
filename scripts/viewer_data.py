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
