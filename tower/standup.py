"""Generate a standup draft using Claude, given current sprint + interrupt data."""
import json
import os
from typing import Any

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def generate_standup(
    ado_items: list[dict[str, Any]],
    interrupts: list[dict[str, Any]],
) -> dict[str, list[str]]:
    my_items = [i for i in ado_items if "Chase" in (i.get("assignee") or "")]
    blocked = [i for i in ado_items if i.get("tags") and "blocked" in i.get("tags", [])]
    overdue_interrupts = [
        i for i in interrupts
        if i.get("dueDate") and i.get("status") != "done"
    ]

    context = json.dumps({
        "my_sprint_items": [
            {"title": i["title"], "state": i["state"], "type": i.get("type", "")}
            for i in my_items
        ],
        "blocked_items": [{"title": i["title"]} for i in blocked],
        "open_interrupts": [
            {"title": i["title"], "source": i.get("source", ""), "priority": i.get("priority", "")}
            for i in overdue_interrupts[:5]
        ],
    }, indent=2)

    prompt = f"""You are Chase Ramone's standup assistant. Based on the sprint data below, produce a concise standup for today.

Sprint data:
{context}

Respond with ONLY valid JSON in this exact shape:
{{
  "yesterday": ["bullet 1", "bullet 2"],
  "today": ["bullet 1", "bullet 2"],
  "blockers": ["bullet 1"]
}}

Rules:
- yesterday: items likely completed or progressed yesterday (Done/Closed state, or Code Review just entered). Max 4 bullets. If none, empty array.
- today: what Chase will focus on today — active items, next logical steps. Max 4 bullets.
- blockers: anything blocked, overdue, or waiting. Use plain language. Empty array if none.
- Each bullet is one concise sentence, no leading dashes or numbers.
- Do not mention item IDs or states verbatim."""

    client = _get_client()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
