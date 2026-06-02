import json
import re
from pathlib import Path
from typing import Any
from tower import config


def read_ado_pending() -> list[dict[str, Any]]:
    """Read Hermes ado-pending.json."""
    if not config.ADO_PENDING.exists():
        return []
    try:
        return json.loads(config.ADO_PENDING.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def read_adhoc_notes() -> list[dict[str, Any]]:
    """Parse adhoc-notes.md into list of {title, text, timestamp} dicts."""
    if not config.ADHOC_NOTES.exists():
        return []
    text = config.ADHOC_NOTES.read_text(encoding="utf-8", errors="replace")
    notes = []
    for block in re.split(r"(?=^## )", text, flags=re.MULTILINE):
        block = block.strip()
        if not block or block.startswith("# "):
            continue
        m = re.match(r"^## (\S+)\s+[-]\s+(.+)$", block, re.MULTILINE)
        if not m:
            continue
        body = re.sub(r"^## .+$", "", block, flags=re.MULTILINE).strip()
        body = re.sub(r"^---$", "", body, flags=re.MULTILINE).strip()
        notes.append({"timestamp": m.group(1), "title": m.group(2).strip(), "text": body})
    return notes


def read_hermes_project_captures() -> dict[str, dict[str, Any]]:
    """Read per-project Hermes captures. Returns {slug: {ideas, risks, decisions, questions}}."""
    result: dict[str, dict[str, Any]] = {}
    if not config.HERMES_PROJECTS.exists():
        return result
    for project_dir in config.HERMES_PROJECTS.iterdir():
        if not project_dir.is_dir():
            continue
        slug = project_dir.name
        result[slug] = {}
        for fname in ["ideas.md", "risks.md", "decisions.md", "questions.md"]:
            fpath = project_dir / fname
            key = fname.replace(".md", "")
            result[slug][key] = fpath.read_text(encoding="utf-8").strip() if fpath.exists() else ""
        for fname in ["updates.json", "removals.json"]:
            fpath = project_dir / fname
            key = fname.replace(".json", "")
            try:
                result[slug][key] = json.loads(fpath.read_text()) if fpath.exists() else []
            except json.JSONDecodeError:
                result[slug][key] = []
    return result
