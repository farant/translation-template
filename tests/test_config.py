import yaml
from scripts import config


def test_load_project_defaults(tmp_path):
    (tmp_path / "project.yaml").write_text(
        "work_defaults:\n  source_language: la\n  transcription_mode: normalize\n",
        encoding="utf-8")
    cfg = config.load_project(tmp_path)
    assert cfg["work_defaults"]["source_language"] == "la"
    assert cfg["work_defaults"]["transcription_mode"] == "normalize"


def test_update_status_roundtrip(tmp_path):
    status_path = tmp_path / "status.yaml"
    status_path.write_text(
        yaml.safe_dump({"work": "w", "stages": {"ingest": {"done": False}}}),
        encoding="utf-8")
    config.update_status(status_path, ["stages", "ingest", "done"], True)
    reloaded = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    assert reloaded["stages"]["ingest"]["done"] is True
