import re
from typing import Any


def read_decisions(limit: int = 10) -> list[dict[str, Any]]:
    """Parse decisions/log.md and return last `limit` entries, newest first."""
    from tower import config
    log_path = config.DECISIONS_LOG
    if not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    entries = []
    for block in re.split(r"(?=^## \d{4}-\d{2}-\d{2})", text, flags=re.MULTILINE):
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^## (\d{4}-\d{2}-\d{2})\s+[—–-]\s+(.+)$", block, re.MULTILINE)
        if not m:
            continue
        date, title = m.group(1), m.group(2).strip()
        project_m = re.search(r"\*Project:\s*(.+?)\*", block)
        entries.append({
            "date": date,
            "text": title,
            "project": project_m.group(1).strip() if project_m else "",
        })
    return entries[:limit]  # newest first (file is written newest-at-top)
