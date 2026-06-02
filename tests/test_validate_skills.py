from scripts import validate_skills as v


def test_parse_frontmatter_reads_name_and_description():
    text = "---\nname: start\ndescription: do things\n---\n\nbody"
    fm = v.parse_frontmatter(text)
    assert fm == {"name": "start", "description": "do things"}


def test_parse_frontmatter_none_when_absent():
    assert v.parse_frontmatter("no frontmatter here") is None


def test_validate_skill_ok(tmp_path):
    d = tmp_path / "start"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: start\ndescription: x\n---\nbody", encoding="utf-8")
    assert v.validate_skill(d) == []


def test_validate_skill_name_mismatch(tmp_path):
    d = tmp_path / "start"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: wrong\ndescription: x\n---\n", encoding="utf-8")
    problems = v.validate_skill(d)
    assert any("name" in p for p in problems)


def test_validate_skill_empty_description(tmp_path):
    d = tmp_path / "start"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: start\ndescription: ''\n---\n", encoding="utf-8")
    assert any("description" in p for p in v.validate_skill(d))


def test_validate_skill_missing_file(tmp_path):
    d = tmp_path / "start"
    d.mkdir()
    assert any("missing SKILL.md" in p for p in v.validate_skill(d))


def test_validate_all_collects_per_skill(tmp_path):
    for name in ("a", "b"):
        d = tmp_path / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n", encoding="utf-8")
    results = v.validate_all(tmp_path)
    assert results == {"a": [], "b": []}
