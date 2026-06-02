import re
from pathlib import Path
from typing import Any


def read_projects() -> list[dict[str, Any]]:
    """Read all project MEMORY.md files and return summary dicts."""
    from tower import config
    results = []
    if not config.PROJECTS_DIR.exists():
        return results
    for project_dir in sorted(config.PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        memory_file = project_dir / "MEMORY.md"
        if not memory_file.exists():
            continue
        text = memory_file.read_text(encoding="utf-8", errors="replace")
        results.append({
            "slug": project_dir.name,
            "status": _extract(text, r"^\*\*Status\*\*:\s*(.+)$") or "unknown",
            "priority": _extract(text, r"^\*\*Priority\*\*:\s*(.+)$") or "",
            "raw": text,
        })
    return results


def _extract(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else None
