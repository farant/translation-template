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
