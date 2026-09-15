"""Deleting a review or plan — the one board → document write there is.

Covered here because it is the only path that removes a versioned file, and because
the refusal is the point: an id another document names cannot simply stop existing.
"""

import json

import pytest

from tower import cycle


def write_doc(root, folder, workstream, name, *, doc_id, doc_type, status, **fields):
    """A cycle document with front-matter, filed the way the skill says."""
    path = root / folder / workstream
    path.mkdir(parents=True, exist_ok=True)
    lines = [f"id: {doc_id}", f"type: {doc_type}", f"status: {status}",
             f"workstream: {workstream}"]
    lines += [f"{k.replace('_', '-')}: {v}" for k, v in fields.items()]
    doc = path / name
    doc.write_text("---\n" + "\n".join(lines) + "\n---\n\n# " + workstream + "\n",
                   encoding="utf-8")
    return doc


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project with one review, its plan, and a card store the board would write."""
    import tower.config as cfg
    projects = tmp_path / "projects"
    root = projects / "magiq-media"
    (root / "reviews").mkdir(parents=True)
    (root / "plans").mkdir(parents=True)
    todos = tmp_path / "todos"
    todos.mkdir()
    monkeypatch.setattr(cfg, "PROJECTS_DIR", projects)
    monkeypatch.setattr(cfg, "TODOS_DATA_DIR", todos)

    review = write_doc(root, "reviews", "aggregate-design", "ad-review-2026-09-14.md",
                       doc_id="MM-042", doc_type="review", status="done")
    review.with_name(review.name + "-prompt.md").write_text("prompt\n", encoding="utf-8")
    plan = write_doc(root, "plans", "aggregate-design", "ad-review-2026-09-14.md",
                     doc_id="MM-043", doc_type="plan", status="active", consumes="MM-042")
    return {"root": root, "review": review, "plan": plan, "todos": todos}


def card_ids(project, slug="magiq-media"):
    store = project["todos"] / f"{slug}.json"
    if not store.exists():
        return []
    return [i["id"] for i in json.loads(store.read_text(encoding="utf-8"))]


def test_delete_removes_document_prompt_and_folder(project):
    result = cycle.delete_document("magiq-media", "MM-043")

    assert not project["plan"].exists()
    assert not project["plan"].parent.exists(), "emptied workstream folder should go too"
    assert result["removed"] == ["projects/magiq-media/plans/aggregate-design/"
                                 "ad-review-2026-09-14.md"]
    assert result["folderRemoved"] == "projects/magiq-media/plans/aggregate-design"
    assert "MM-043" not in cycle.index_documents("magiq-media")


def test_delete_takes_the_prompt_with_it(project):
    # The plan goes first: while it is there, MM-042 is referenced and undeletable.
    cycle.delete_document("magiq-media", "MM-043")
    result = cycle.delete_document("magiq-media", "MM-042")

    assert not project["review"].exists()
    assert not project["review"].with_name(project["review"].name + "-prompt.md").exists()
    assert len(result["removed"]) == 2


def test_referenced_document_is_refused(project):
    with pytest.raises(cycle.CycleViolation) as exc:
        cycle.delete_document("magiq-media", "MM-042")

    assert "MM-043" in str(exc.value)
    assert "consumes" in str(exc.value)
    assert project["review"].exists(), "nothing is removed when the check fails"


def test_unknown_id_is_not_found(project):
    with pytest.raises(cycle.DocumentNotFound):
        cycle.delete_document("magiq-media", "MM-999")


def test_card_goes_with_the_document(project):
    from tower.interrupts.store import load_interrupts, save_interrupts

    store = project["todos"] / "magiq-media.json"
    items, _ = cycle.reconcile("magiq-media", [])
    save_interrupts(store, items)
    todo_id = cycle.todo_id_for("magiq-media", "MM-043")
    assert todo_id in card_ids(project)

    result = cycle.delete_document("magiq-media", "MM-043")

    assert result["todoRemoved"] is True
    assert todo_id not in [i["id"] for i in load_interrupts(store)]


def test_a_deleted_document_does_not_come_back(project):
    """The card is a projection, so the file having gone is what makes it stay gone."""
    cycle.delete_document("magiq-media", "MM-043")
    items, _ = cycle.reconcile("magiq-media", [])
    assert cycle.todo_id_for("magiq-media", "MM-043") not in [i["id"] for i in items]


def test_api_maps_the_two_refusals_to_status_codes(project, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    import tower.config as cfg
    monkeypatch.setattr(cfg, "INTERRUPTS_FILE", tmp_path / "interrupts.json")
    from tower.server import app
    client = TestClient(app)

    assert client.delete("/api/projects/magiq-media/documents/MM-999").status_code == 404

    referenced = client.delete("/api/projects/magiq-media/documents/MM-042")
    assert referenced.status_code == 409
    assert "MM-043" in referenced.json()["detail"]

    ok = client.delete("/api/projects/magiq-media/documents/MM-043")
    assert ok.status_code == 200
    assert ok.json()["id"] == "MM-043"
    assert not project["plan"].exists()


def test_archived_documents_delete_the_same_way(project):
    archived = write_doc(project["root"], "_archive/reviews", "MM-050-old-thing",
                         "old-review.md", doc_id="MM-050", doc_type="review",
                         status="superseded")
    assert cycle.is_archived(cycle.index_documents("magiq-media")["MM-050"]["rel"])

    cycle.delete_document("magiq-media", "MM-050")

    assert not archived.exists()
    assert "MM-050" not in cycle.index_documents("magiq-media")
