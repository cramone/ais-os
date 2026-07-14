import pytest
import json
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_aios, tmp_interrupts, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_aios / "projects")
    monkeypatch.setattr(cfg, "DECISIONS_LOG", tmp_aios / "decisions" / "log.md")
    monkeypatch.setattr(cfg, "INTERRUPTS_FILE", tmp_interrupts)
    # Import AFTER monkeypatching config
    from tower.server import app
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "sources" in r.json()


def test_get_projects(client):
    r = client.get("/api/projects")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    slugs = [p["slug"] for p in data]
    assert "magiq-media" in slugs


def test_get_decisions(client):
    r = client.get("/api/decisions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_interrupts(client):
    r = client.get("/api/interrupts")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_create_interrupt(client):
    r = client.post("/api/interrupts", json={
        "title": "New task", "source": "Finance",
        "dueDate": None, "priority": "normal"
    })
    assert r.status_code == 201
    assert r.json()["title"] == "New task"


def test_update_interrupt(client):
    r = client.patch("/api/interrupts/test-id-1", json={"status": "in-progress"})
    assert r.status_code == 200
    assert r.json()["status"] == "in-progress"


def test_delete_interrupt(client):
    r = client.delete("/api/interrupts/test-id-1")
    assert r.status_code == 204


def test_append_comment(client):
    r = client.post("/api/interrupts/test-id-1/activity", json={
        "type": "comment", "author": "Chase", "text": "Working on it."
    })
    assert r.status_code == 200
    assert len(r.json()["activity"]) == 1


def test_update_interrupt_not_found(client):
    r = client.patch("/api/interrupts/bad-id", json={"status": "done"})
    assert r.status_code == 404
