import pytest
import json
from tower.readers.projects import read_projects
from tower.readers.decisions import read_decisions


def test_read_projects_returns_list(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_aios / "projects")
    result = read_projects()
    assert isinstance(result, list)
    assert len(result) == 2


def test_read_projects_fields(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_aios / "projects")
    result = read_projects()
    mm = next(p for p in result if p["slug"] == "magiq-media")
    assert mm["status"] == "Active delivery"
    assert mm["priority"] == "High"


def test_read_projects_missing_memory_md(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_aios / "projects")
    (tmp_aios / "projects" / "empty-project").mkdir()
    result = read_projects()
    assert all(p["slug"] != "empty-project" for p in result)


def test_read_decisions_returns_list(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "DECISIONS_LOG", tmp_aios / "decisions" / "log.md")
    result = read_decisions(limit=10)
    assert isinstance(result, list)
    assert len(result) == 2


def test_read_decisions_fields(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "DECISIONS_LOG", tmp_aios / "decisions" / "log.md")
    result = read_decisions(limit=10)
    assert result[0]["date"] == "2026-06-01"
    assert "Some decision" in result[0]["text"]
    assert result[0]["project"] == "magiq-media"


def test_read_decisions_missing_file(tmp_path, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "DECISIONS_LOG", tmp_path / "nonexistent.md")
    result = read_decisions()
    assert result == []


def test_read_ado_pending(tmp_hermes, monkeypatch):
    from tower.readers.hermes import read_ado_pending
    import tower.config as cfg
    monkeypatch.setattr(cfg, "ADO_PENDING", tmp_hermes / "ado-pending.json")
    result = read_ado_pending()
    assert len(result) == 1
    assert result[0]["title"] == "Test item"
    assert result[0]["status"] == "pending"


def test_read_ado_pending_missing(tmp_path, monkeypatch):
    from tower.readers.hermes import read_ado_pending
    import tower.config as cfg
    monkeypatch.setattr(cfg, "ADO_PENDING", tmp_path / "missing.json")
    assert read_ado_pending() == []


def test_read_adhoc_notes(tmp_hermes, monkeypatch):
    from tower.readers.hermes import read_adhoc_notes
    import tower.config as cfg
    monkeypatch.setattr(cfg, "ADHOC_NOTES", tmp_hermes / "adhoc-notes.md")
    result = read_adhoc_notes()
    assert len(result) == 1
    assert result[0]["title"] == "Test note"
    assert "Remember this thing" in result[0]["text"]


def test_read_hermes_project_captures(tmp_hermes, monkeypatch):
    from tower.readers.hermes import read_hermes_project_captures
    import tower.config as cfg
    monkeypatch.setattr(cfg, "HERMES_PROJECTS", tmp_hermes / "projects")
    result = read_hermes_project_captures()
    assert "magiq-media" in result
    assert result["magiq-media"]["ideas"]
