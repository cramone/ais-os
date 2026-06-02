import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_interrupts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_interrupts(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def create_interrupt(
    path: Path, title: str, source: str,
    due_date: str | None = None, priority: str = "normal"
) -> dict[str, Any]:
    items = load_interrupts(path)
    now = _now()
    item: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "title": title,
        "source": source,
        "dueDate": due_date,
        "priority": priority,
        "status": "new",
        "tags": [],
        "adoItemId": None,
        "capturedAt": now,
        "updatedAt": now,
        "activity": [],
    }
    items.append(item)
    save_interrupts(path, items)
    return item


def update_interrupt(path: Path, interrupt_id: str, **kwargs: Any) -> dict[str, Any]:
    items = load_interrupts(path)
    allowed = {"title", "source", "dueDate", "priority", "status", "tags", "adoItemId"}
    for item in items:
        if item["id"] == interrupt_id:
            for k, v in kwargs.items():
                if k in allowed:
                    item[k] = v
            item["updatedAt"] = _now()
            save_interrupts(path, items)
            return item
    raise KeyError(f"Interrupt {interrupt_id!r} not found")


def delete_interrupt(path: Path, interrupt_id: str) -> None:
    items = load_interrupts(path)
    items = [i for i in items if i["id"] != interrupt_id]
    save_interrupts(path, items)


def append_activity(
    path: Path, interrupt_id: str,
    entry_type: str, text: str, author: str | None = None
) -> dict[str, Any]:
    items = load_interrupts(path)
    for item in items:
        if item["id"] == interrupt_id:
            entry: dict[str, Any] = {"type": entry_type, "text": text, "timestamp": _now()}
            if author:
                entry["author"] = author
            item["activity"].append(entry)
            item["updatedAt"] = _now()
            save_interrupts(path, items)
            return item
    raise KeyError(f"Interrupt {interrupt_id!r} not found")
