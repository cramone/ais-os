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


import json as _json2
from unittest.mock import patch
from tower.readers.ado import read_ado_sprint

SAMPLE_ADO_JSON = _json2.dumps({
    "items": [
        {"id": 1, "title": "Fix auth bug", "state": "Active",
         "type": "Story", "module": "Catalog", "assignee": "Chase Ramone",
         "daysInState": 2},
        {"id": 2, "title": "Add endpoint", "state": "Code Review",
         "type": "Story", "module": "General", "assignee": "Estelle Wu",
         "daysInState": 5}
    ]
})


def test_read_ado_sprint_returns_items():
    with patch("tower.readers.ado._run_script", return_value=SAMPLE_ADO_JSON):
        result = read_ado_sprint()
    assert len(result["items"]) == 2
    assert result["items"][0]["title"] == "Fix auth bug"


def test_read_ado_sprint_script_failure():
    with patch("tower.readers.ado._run_script", side_effect=Exception("timeout")):
        result = read_ado_sprint()
    assert result == {"items": [], "error": "timeout"}
