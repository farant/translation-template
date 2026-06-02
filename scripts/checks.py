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
