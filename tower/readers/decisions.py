import re
from typing import Any


def _split_log(text: str) -> tuple[str, list[str]]:
    """Split log into preamble + list of entry blocks."""
    parts = re.split(r"(?=^## \d{4}-\d{2}-\d{2})", text, flags=re.MULTILINE)
    preamble = parts[0] if parts and not re.match(r"^## \d{4}", parts[0]) else ""
    blocks = [p for p in parts if re.match(r"^## \d{4}-\d{2}-\d{2}", p)]
    return preamble, blocks


def _block_matches(block: str, date: str, title: str) -> bool:
    m = re.match(r"^## (\d{4}-\d{2}-\d{2})\s+[—–-]\s+(.+)$", block, re.MULTILINE)
    if not m:
        return False
    return m.group(1) == date and m.group(2).strip() == title.strip()


def delete_decision(date: str, title: str) -> bool:
    """Remove a decision block from log.md. Returns True if found and removed."""
    from tower import config
    log_path = config.DECISIONS_LOG
    if not log_path.exists():
        return False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    preamble, blocks = _split_log(text)
    new_blocks = [b for b in blocks if not _block_matches(b, date, title)]
    if len(new_blocks) == len(blocks):
        return False
    log_path.write_text(preamble + "".join(new_blocks), encoding="utf-8")
    return True


def rename_decision(date: str, old_title: str, new_title: str) -> bool:
    """Rename a decision title in log.md. Returns True if found and renamed."""
    from tower import config
    log_path = config.DECISIONS_LOG
    if not log_path.exists():
        return False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    preamble, blocks = _split_log(text)
    updated = False
    new_blocks = []
    for block in blocks:
        if _block_matches(block, date, old_title):
            block = re.sub(
                r"^(## \d{4}-\d{2}-\d{2}\s+[—–-]\s+).+$",
                lambda m: m.group(1) + new_title.strip(),
                block,
                count=1,
                flags=re.MULTILINE,
            )
            updated = True
        new_blocks.append(block)
    if not updated:
        return False
    log_path.write_text(preamble + "".join(new_blocks), encoding="utf-8")
    return True


def add_decision(date: str, title: str, project: str | None = None) -> bool:
    """Prepend a new decision block to log.md (newest at top)."""
    from tower import config
    log_path = config.DECISIONS_LOG
    if not log_path.exists():
        return False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    preamble, blocks = _split_log(text)
    project_line = f"**Project:** {project}\n\n" if project else "**Project:** \n\n"
    new_block = f"## {date} — {title}\n\n{project_line}**Decision:** \n\n**Why:** \n\n"
    log_path.write_text(preamble + new_block + "".join(blocks), encoding="utf-8")
    return True


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
        project_m = re.search(r"\*\*Project:\*\*\s*(.+)", block)
        entries.append({
            "date": date,
            "text": title,
            "project": project_m.group(1).strip() if project_m else "",
        })
    return entries[:limit]  # newest first (file is written newest-at-top)
