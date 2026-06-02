import pytest
import json
from tower.interrupts.store import (
    load_interrupts, save_interrupts, create_interrupt,
    update_interrupt, delete_interrupt, append_activity
)


def test_load_empty(tmp_path):
    f = tmp_path / "interrupts.json"
    f.write_text("[]")
    result = load_interrupts(f)
    assert result == []


def test_load_missing_file(tmp_path):
    result = load_interrupts(tmp_path / "missing.json")
    assert result == []


def test_create_interrupt(tmp_path):
    f = tmp_path / "interrupts.json"
    f.write_text("[]")
    item = create_interrupt(f, title="Fix export", source="Support",
                            due_date="2026-06-01", priority="urgent")
    assert item["title"] == "Fix export"
    assert item["source"] == "Support"
    assert item["status"] == "new"
    assert item["tags"] == []
    assert item["activity"] == []
    assert "id" in item
    stored = load_interrupts(f)
    assert len(stored) == 1


def test_update_interrupt_status(tmp_interrupts):
    item = update_interrupt(tmp_interrupts, "test-id-1", status="in-progress")
    assert item["status"] == "in-progress"
    stored = load_interrupts(tmp_interrupts)
    assert stored[0]["status"] == "in-progress"


def test_update_interrupt_not_found(tmp_interrupts):
    with pytest.raises(KeyError):
        update_interrupt(tmp_interrupts, "nonexistent-id", status="done")


def test_delete_interrupt(tmp_interrupts):
    delete_interrupt(tmp_interrupts, "test-id-1")
    stored = load_interrupts(tmp_interrupts)
    assert stored == []


def test_append_activity_comment(tmp_interrupts):
    item = append_activity(tmp_interrupts, "test-id-1",
                           entry_type="comment", author="Chase",
                           text="Looking into this now.")
    assert len(item["activity"]) == 1
    assert item["activity"][0]["type"] == "comment"
    assert item["activity"][0]["text"] == "Looking into this now."


def test_append_activity_event(tmp_interrupts):
    item = append_activity(tmp_interrupts, "test-id-1",
                           entry_type="event", text="Added tag: blocked")
    assert item["activity"][0]["type"] == "event"
    assert "timestamp" in item["activity"][0]
