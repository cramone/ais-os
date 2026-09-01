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
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def make_item(
    title: str, *,
    source: str = "",
    due_date: str | None = None,
    priority: str = "normal",
    status: str = "new",
    tags: list[str] | None = None,
    zendesk_ticket: str | None = None,
    customer: str | None = None,
    captured_at: str | None = None,
    activity: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an item dict with the canonical schema shared by interrupts and todos."""
    now = _now()
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "source": source,
        "dueDate": due_date,
        "priority": priority,
        "status": status,
        "tags": tags or [],
        "adoItemId": None,
        "zendeskTicket": zendesk_ticket,
        "customer": customer,
        "capturedAt": captured_at or now,
        "updatedAt": now,
        # When the item first reached `done`. Distinct from updatedAt, which any edit
        # moves — a "finished on" date has to survive later comments and retags.
        "doneAt": now if status == "done" else None,
        # Set when the item is filed away. Archived items keep every field and stay in
        # the same store; they are excluded from the board rather than deleted.
        "archivedAt": None,
        # Manual position within a status column. None means "unordered" and sorts
        # after everything explicitly placed, so a new item lands at the bottom
        # without disturbing an order someone arranged by hand.
        "order": None,
        "activity": activity or [],
    }


def stamp_done(item: dict[str, Any], previous_status: str | None = None) -> None:
    """Maintain `doneAt` across a status change. Idempotent.

    Set on the first transition into `done` and cleared on the way out, so an item
    reopened and finished again carries the date that is actually true.
    """
    if item.get("status") == "done":
        if not item.get("doneAt"):
            item["doneAt"] = _now()
    elif previous_status == "done" or item.get("doneAt"):
        item["doneAt"] = None


def set_archived(item: dict[str, Any], archived: bool) -> None:
    """Archive or restore an item. Only a `done` item may be archived."""
    if archived:
        if item.get("status") != "done":
            raise ValueError(
                f"{item.get('title', 'item')!r} is {item.get('status')!r}, not done. "
                "Only a done item can be archived."
            )
        item["archivedAt"] = item.get("archivedAt") or _now()
    else:
        item["archivedAt"] = None
    item["updatedAt"] = _now()


def create_item(path: Path, **fields: Any) -> dict[str, Any]:
    """Append a new item (built via make_item) to the store at path."""
    items = load_interrupts(path)
    item = make_item(**fields)
    items.append(item)
    save_interrupts(path, items)
    return item


def create_interrupt(
    path: Path, title: str, source: str,
    due_date: str | None = None, priority: str = "normal",
    zendesk_ticket: str | None = None,
    customer: str | None = None,
) -> dict[str, Any]:
    return create_item(
        path, title=title, source=source, due_date=due_date,
        priority=priority, zendesk_ticket=zendesk_ticket, customer=customer,
    )


def update_interrupt(path: Path, interrupt_id: str, **kwargs: Any) -> dict[str, Any]:
    items = load_interrupts(path)
    allowed = {"title", "source", "dueDate", "priority", "status", "tags", "adoItemId",
               "zendeskTicket", "customer", "archivedAt", "order"}
    for item in items:
        if item["id"] == interrupt_id:
            previous_status = item.get("status")
            for k, v in kwargs.items():
                if k in allowed:
                    item[k] = v
            if "status" in kwargs:
                stamp_done(item, previous_status)
            item["updatedAt"] = _now()
            save_interrupts(path, items)
            return item
    raise KeyError(f"Interrupt {interrupt_id!r} not found")


def delete_interrupt(path: Path, interrupt_id: str) -> None:
    items = load_interrupts(path)
    items = [i for i in items if i["id"] != interrupt_id]
    save_interrupts(path, items)


def update_activity(
    path: Path, interrupt_id: str, index: int, text: str
) -> dict[str, Any]:
    items = load_interrupts(path)
    for item in items:
        if item["id"] == interrupt_id:
            activity = item.get("activity", [])
            if index < 0 or index >= len(activity):
                raise IndexError(f"Activity index {index} out of range")
            if activity[index].get("type") != "comment":
                raise ValueError("Only comments can be edited")
            activity[index]["text"] = text
            activity[index]["editedAt"] = _now()
            item["updatedAt"] = _now()
            save_interrupts(path, items)
            return item
    raise KeyError(f"Interrupt {interrupt_id!r} not found")


def delete_activity(
    path: Path, interrupt_id: str, index: int
) -> dict[str, Any]:
    items = load_interrupts(path)
    for item in items:
        if item["id"] == interrupt_id:
            activity = item.get("activity", [])
            if index < 0 or index >= len(activity):
                raise IndexError(f"Activity index {index} out of range")
            activity.pop(index)
            item["updatedAt"] = _now()
            save_interrupts(path, items)
            return item
    raise KeyError(f"Interrupt {interrupt_id!r} not found")


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


def reorder(path: Path, ordered_ids: list[str]) -> list[dict[str, Any]]:
    """Assign `order` 0..n-1 to the given ids, in the order given.

    Takes the whole column at once rather than one item at a time: a drag moves one
    card but changes every position after it, and n PATCHes would leave the store
    briefly inconsistent if any of them failed.

    Ids not present are ignored; items not named keep the order they had.
    """
    items = load_interrupts(path)
    position = {item_id: index for index, item_id in enumerate(ordered_ids)}
    now = _now()
    for item in items:
        if item["id"] in position:
            item["order"] = position[item["id"]]
            item["updatedAt"] = now
    save_interrupts(path, items)
    return items
