# AIS-OS Control Tower — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally-hosted browser dashboard (Python FastAPI + vanilla JS) that surfaces AIS-OS project status, ADO sprint data, Hermes inbox, interrupts, decisions, and team workload in real time.

**Architecture:** FastAPI backend serves a single `index.html` SPA at `/` and exposes REST endpoints at `/api/*`. The frontend polls all endpoints every 30s with `Promise.all` and re-renders panels independently. Interrupts are stored in `tower/data/interrupts.json`. Email drafts are generated on-demand via the Claude API (Haiku).

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, httpx, anthropic SDK, vanilla JS (ES2020), no build step.

---

## File Map

| File | Responsibility |
|------|---------------|
| `tower/config.py` | Path constants resolved from env vars with Windows defaults |
| `tower/server.py` | FastAPI app, all routes, CORS, static file mount, auto-open browser on start |
| `tower/readers/projects.py` | Parse `projects/*/MEMORY.md` → project summary dicts |
| `tower/readers/hermes.py` | Read `ado-pending.json`, per-project captures, `adhoc-notes.md` |
| `tower/readers/decisions.py` | Parse `decisions/log.md` → last N entries |
| `tower/readers/ado.py` | Subprocess-call `devops_summary.py`, parse its JSON/text output |
| `tower/interrupts/store.py` | CRUD on `interrupts.json`, activity append, tag management |
| `tower/interrupts/email.py` | Claude API call for email draft generation |
| `tower/interrupts/ado_push.py` | Create ADO Task from interrupt via ADO REST API |
| `tower/static/index.html` | Full SPA: layout, CSS, JS polling, all panels, drill-downs |
| `tower/data/interrupts.json` | Auto-created; persists interrupt records |
| `tower/requirements.txt` | fastapi, uvicorn, anthropic, httpx, pytest, httpx (test client) |
| `tests/conftest.py` | Shared fixtures: tmp paths, sample MEMORY.md, sample interrupts.json |
| `tests/test_readers.py` | Unit tests for all reader functions |
| `tests/test_interrupts_store.py` | Unit tests for store CRUD + activity |
| `tests/test_email.py` | Unit tests for email prompt construction (mock Claude API) |
| `tests/test_api.py` | Integration tests via FastAPI TestClient |

---

## Task 1: Scaffold + Config

**Files:**
- Create: `tower/__init__.py`
- Create: `tower/config.py`
- Create: `tower/requirements.txt`
- Create: `tower/readers/__init__.py`
- Create: `tower/interrupts/__init__.py`
- Create: `tower/data/.gitkeep`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p tower/readers tower/interrupts tower/static tower/data tests
touch tower/__init__.py tower/readers/__init__.py tower/interrupts/__init__.py tests/__init__.py
echo '[]' > tower/data/interrupts.json
```

- [ ] **Step 2: Write `tower/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
anthropic==0.26.0
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.6
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r tower/requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 4: Write `tower/config.py`**

```python
import os
from pathlib import Path

# Resolve AIS-OS root — env override for portability
AIOS_ROOT = Path(os.getenv("AIOS_ROOT", r"C:\Users\chase\OneDrive\Magiq\AIS-OS"))
HERMES_DATA = Path(os.getenv("HERMES_DATA", r"C:\Users\chase\.hermes\data"))
TOWER_DIR = AIOS_ROOT / "tower"
PROJECTS_DIR = AIOS_ROOT / "projects"
DECISIONS_LOG = AIOS_ROOT / "decisions" / "log.md"
ADO_SCRIPT = AIOS_ROOT / "references" / "devops_summary.py"
INTERRUPTS_FILE = TOWER_DIR / "data" / "interrupts.json"
ADO_PENDING = HERMES_DATA / "ado-pending.json"
ADHOC_NOTES = HERMES_DATA / "adhoc-notes.md"
HERMES_PROJECTS = HERMES_DATA / "projects"
PORT = int(os.getenv("TOWER_PORT", "8765"))
```

- [ ] **Step 5: Write `tests/conftest.py`**

```python
import pytest
from pathlib import Path
import json, shutil

@pytest.fixture
def tmp_aios(tmp_path):
    """Minimal AIS-OS directory structure for testing."""
    projects = tmp_path / "projects"
    projects.mkdir()
    # magiq-media with MEMORY.md
    mm = projects / "magiq-media"
    mm.mkdir()
    (mm / "MEMORY.md").write_text(
        "# magiq-media\n**Status**: Active delivery\n**Priority**: High\n"
    )
    # magiq-auth with MEMORY.md
    ma = projects / "magiq-auth"
    ma.mkdir()
    (ma / "MEMORY.md").write_text(
        "# magiq-auth\n**Status**: Draft\n**Priority**: High\n"
    )
    # decisions log
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    (decisions / "log.md").write_text(
        "## 2026-06-01 — Some decision\n*Project: magiq-media*\n\n## 2026-05-30 — Another decision\n*Project: aios*\n"
    )
    return tmp_path

@pytest.fixture
def tmp_hermes(tmp_path):
    """Minimal Hermes data directory for testing."""
    hermes = tmp_path / "hermes"
    hermes.mkdir()
    (hermes / "ado-pending.json").write_text(json.dumps([
        {"id": "1", "title": "Test item", "project": "magiq-media",
         "module": "Catalog", "type": "Story", "status": "pending",
         "priority": "Medium", "capturedAt": "2026-06-01T08:00:00Z"}
    ]))
    (hermes / "adhoc-notes.md").write_text(
        "# Adhoc Notes\n\n## 2026-06-01T08:00:00Z — Test note\n\nRemember this thing.\n\n---\n"
    )
    projects = hermes / "projects" / "magiq-media"
    projects.mkdir(parents=True)
    (projects / "ideas.md").write_text("- Consider caching layer\n")
    return hermes

@pytest.fixture
def tmp_interrupts(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    f = data / "interrupts.json"
    f.write_text(json.dumps([
        {
            "id": "test-id-1",
            "title": "Fix export bug",
            "source": "Support",
            "dueDate": "2026-06-01",
            "priority": "urgent",
            "status": "new",
            "tags": [],
            "adoItemId": None,
            "capturedAt": "2026-05-29T08:00:00Z",
            "updatedAt": "2026-05-29T08:00:00Z",
            "activity": []
        }
    ]))
    return f
```

- [ ] **Step 6: Commit scaffold**

```bash
git add tower/ tests/
git commit -m "feat(tower): scaffold project structure and config"
```

---

## Task 2: Project + Decisions Readers

**Files:**
- Create: `tower/readers/projects.py`
- Create: `tower/readers/decisions.py`
- Modify: `tests/test_readers.py` (create)

- [ ] **Step 1: Write failing tests for `projects.py`**

```python
# tests/test_readers.py
import pytest
from tower.readers.projects import read_projects

def test_read_projects_returns_list(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_aios / "projects")
    result = read_projects()
    assert isinstance(result, list)
    assert len(result) == 2

def test_read_projects_fields(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_aios / "projects")
    result = read_projects()
    mm = next(p for p in result if p["slug"] == "magiq-media")
    assert mm["status"] == "Active delivery"
    assert mm["priority"] == "High"

def test_read_projects_missing_memory_md(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_aios / "projects")
    # Add project folder with no MEMORY.md
    (tmp_aios / "projects" / "empty-project").mkdir()
    result = read_projects()
    # Should skip folders without MEMORY.md
    assert all(p["slug"] != "empty-project" for p in result)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_readers.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `tower.readers.projects` doesn't exist yet.

- [ ] **Step 3: Implement `tower/readers/projects.py`**

```python
import re
from pathlib import Path
from typing import Any
from tower import config

def read_projects() -> list[dict[str, Any]]:
    """Read all project MEMORY.md files and return summary dicts."""
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_readers.py::test_read_projects_returns_list tests/test_readers.py::test_read_projects_fields tests/test_readers.py::test_read_projects_missing_memory_md -v
```

Expected: all 3 PASS.

- [ ] **Step 5: Write failing tests for `decisions.py`**

```python
# append to tests/test_readers.py
from tower.readers.decisions import read_decisions

def test_read_decisions_returns_list(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "DECISIONS_LOG", tmp_aios / "decisions" / "log.md")
    result = read_decisions(limit=10)
    assert isinstance(result, list)
    assert len(result) == 2

def test_read_decisions_fields(tmp_aios, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "DECISIONS_LOG", tmp_aios / "decisions" / "log.md")
    result = read_decisions(limit=10)
    assert result[0]["date"] == "2026-06-01"
    assert "Some decision" in result[0]["text"]
    assert result[0]["project"] == "magiq-media"

def test_read_decisions_missing_file(tmp_path, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "DECISIONS_LOG", tmp_path / "nonexistent.md")
    result = read_decisions()
    assert result == []
```

- [ ] **Step 6: Run tests — verify they fail**

```bash
pytest tests/test_readers.py::test_read_decisions_returns_list -v
```

Expected: `ImportError`.

- [ ] **Step 7: Implement `tower/readers/decisions.py`**

```python
import re
from typing import Any
from tower import config

def read_decisions(limit: int = 10) -> list[dict[str, Any]]:
    """Parse decisions/log.md and return last `limit` entries."""
    if not config.DECISIONS_LOG.exists():
        return []
    text = config.DECISIONS_LOG.read_text(encoding="utf-8", errors="replace")
    entries = []
    # Each entry starts with ## YYYY-MM-DD — title
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
    return entries[-limit:][::-1]  # newest first
```

- [ ] **Step 8: Run all reader tests so far**

```bash
pytest tests/test_readers.py -v
```

Expected: all 6 PASS.

- [ ] **Step 9: Commit**

```bash
git add tower/readers/projects.py tower/readers/decisions.py tests/test_readers.py
git commit -m "feat(tower): project and decisions readers with tests"
```

---

## Task 3: Hermes Readers

**Files:**
- Create: `tower/readers/hermes.py`
- Modify: `tests/test_readers.py`

- [ ] **Step 1: Write failing tests**

```python
# append to tests/test_readers.py
from tower.readers.hermes import read_ado_pending, read_adhoc_notes, read_hermes_project_captures

def test_read_ado_pending(tmp_hermes, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "ADO_PENDING", tmp_hermes / "ado-pending.json")
    result = read_ado_pending()
    assert len(result) == 1
    assert result[0]["title"] == "Test item"
    assert result[0]["status"] == "pending"

def test_read_ado_pending_missing(tmp_path, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "ADO_PENDING", tmp_path / "missing.json")
    assert read_ado_pending() == []

def test_read_adhoc_notes(tmp_hermes, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "ADHOC_NOTES", tmp_hermes / "adhoc-notes.md")
    result = read_adhoc_notes()
    assert len(result) == 1
    assert result[0]["title"] == "Test note"
    assert "Remember this thing" in result[0]["text"]

def test_read_hermes_project_captures(tmp_hermes, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "HERMES_PROJECTS", tmp_hermes / "projects")
    result = read_hermes_project_captures()
    assert "magiq-media" in result
    assert result["magiq-media"]["ideas"]  # ideas.md was created
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/test_readers.py::test_read_ado_pending -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `tower/readers/hermes.py`**

```python
import json, re
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
        m = re.match(r"^## (\S+)\s+[—–-]\s+(.+)$", block, re.MULTILINE)
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
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_readers.py -v
```

Expected: all 10 PASS.

- [ ] **Step 5: Commit**

```bash
git add tower/readers/hermes.py tests/test_readers.py
git commit -m "feat(tower): Hermes readers for pending items, adhoc notes, project captures"
```

---

## Task 4: ADO Reader

**Files:**
- Create: `tower/readers/ado.py`
- Modify: `tests/test_readers.py`

- [ ] **Step 1: Inspect `devops_summary.py` output format**

```bash
python references/devops_summary.py 2>&1 | head -60
```

Note whether output is JSON or plain text. The reader must parse whichever format it produces. If JSON, use `json.loads`. If plain text, parse with regex. Record the format before implementing.

- [ ] **Step 2: Write failing tests**

```python
# append to tests/test_readers.py
from unittest.mock import patch
from tower.readers.ado import read_ado_sprint

SAMPLE_ADO_JSON = json.dumps({
    "items": [
        {"id": 1, "title": "Fix auth bug", "state": "Active",
         "type": "Story", "module": "Catalog", "assignee": "Chase Ramone",
         "daysInState": 2},
        {"id": 2, "title": "Add endpoint", "state": "Code Review",
         "type": "Story", "module": "General", "assignee": "Estelle Wu",
         "daysInState": 5}
    ]
})

def test_read_ado_sprint_returns_items():
    with patch("tower.readers.ado._run_script", return_value=SAMPLE_ADO_JSON):
        result = read_ado_sprint()
    assert len(result["items"]) == 2
    assert result["items"][0]["title"] == "Fix auth bug"

def test_read_ado_sprint_script_failure():
    with patch("tower.readers.ado._run_script", side_effect=Exception("timeout")):
        result = read_ado_sprint()
    assert result == {"items": [], "error": "timeout"}
```

- [ ] **Step 3: Run — verify fail**

```bash
pytest tests/test_readers.py::test_read_ado_sprint_returns_items -v
```

Expected: `ImportError`.

- [ ] **Step 4: Implement `tower/readers/ado.py`**

```python
import subprocess, json, sys
from typing import Any
from tower import config

def read_ado_sprint() -> dict[str, Any]:
    """Run devops_summary.py and return parsed sprint data."""
    try:
        raw = _run_script()
        return json.loads(raw)
    except json.JSONDecodeError:
        # Script outputs plain text — wrap it
        return {"items": [], "raw_text": raw}
    except Exception as e:
        return {"items": [], "error": str(e)}

def _run_script() -> str:
    if not config.ADO_SCRIPT.exists():
        raise FileNotFoundError(f"devops_summary.py not found at {config.ADO_SCRIPT}")
    result = subprocess.run(
        [sys.executable, str(config.ADO_SCRIPT)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "script exited non-zero")
    return result.stdout
```

> **Note:** After running the script inspection in Step 1, you may need to adjust the parser. If the script outputs plain text (not JSON), replace `json.loads(raw)` with a regex parser that extracts item rows. The key contract is: return `{"items": [...]}` where each item has at minimum `title`, `state`, `assignee`, `module`, `type`.

- [ ] **Step 5: Run all tests**

```bash
pytest tests/test_readers.py -v
```

Expected: all 12 PASS.

- [ ] **Step 6: Commit**

```bash
git add tower/readers/ado.py tests/test_readers.py
git commit -m "feat(tower): ADO reader wrapping devops_summary.py"
```

---

## Task 5: Interrupts Store

**Files:**
- Create: `tower/interrupts/store.py`
- Create: `tests/test_interrupts_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_interrupts_store.py
import pytest, json
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
    # persisted
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
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/test_interrupts_store.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `tower/interrupts/store.py`**

```python
import json, uuid
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
    for item in items:
        if item["id"] == interrupt_id:
            allowed = {"title", "source", "dueDate", "priority", "status", "tags", "adoItemId"}
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
    entry: dict[str, Any] = {"type": entry_type, "text": text, "timestamp": _now()}
    if author:
        entry["author"] = author
    return update_interrupt(path, interrupt_id,
                            **{"_activity_append": entry})  # handled below

# Override update_interrupt to handle activity append
_orig_update = update_interrupt.__wrapped__ if hasattr(update_interrupt, "__wrapped__") else None

def append_activity(  # noqa: F811
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_interrupts_store.py -v
```

Expected: all 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add tower/interrupts/store.py tests/test_interrupts_store.py
git commit -m "feat(tower): interrupts store with CRUD and activity feed"
```

---

## Task 6: Email Draft Generation

**Files:**
- Create: `tower/interrupts/email.py`
- Create: `tests/test_email.py`

- [ ] **Step 1: Ensure ANTHROPIC_API_KEY is set**

```bash
echo $ANTHROPIC_API_KEY
```

If empty, set it in `.env` or shell profile. The email endpoint will return a 503 if the key is missing — that is acceptable behaviour.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_email.py
import pytest
from unittest.mock import patch, MagicMock
from tower.interrupts.email import build_prompt, generate_email_draft

SAMPLE_INTERRUPT = {
    "id": "test-1",
    "title": "Fix NATA export",
    "source": "Support",
    "dueDate": "2026-06-01",
    "priority": "urgent",
    "status": "in-progress",
    "tags": ["waiting-for-feedback"],
    "activity": [
        {"type": "comment", "author": "Chase",
         "text": "Fix deployed. Waiting for NATA to confirm.",
         "timestamp": "2026-06-01T08:00:00Z"}
    ],
}

def test_build_prompt_contains_title():
    prompt = build_prompt(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert "Fix NATA export" in prompt

def test_build_prompt_contains_template():
    prompt = build_prompt(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert "complete" in prompt.lower() or "resolved" in prompt.lower()

def test_build_prompt_contains_comment():
    prompt = build_prompt(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert "Fix deployed" in prompt

def test_generate_email_draft_structure():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"to": "x@y.com", "subject": "Done", "body": "Hi"}')]
    with patch("tower.interrupts.email._call_claude", return_value=mock_response):
        result = generate_email_draft(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert result["to"] == "x@y.com"
    assert result["subject"] == "Done"
    assert result["body"] == "Hi"

def test_generate_email_draft_api_failure():
    with patch("tower.interrupts.email._call_claude", side_effect=Exception("API error")):
        result = generate_email_draft(SAMPLE_INTERRUPT, template="complete", tone="formal")
    assert "error" in result
```

- [ ] **Step 3: Run — verify fail**

```bash
pytest tests/test_email.py -v
```

Expected: `ImportError`.

- [ ] **Step 4: Implement `tower/interrupts/email.py`**

```python
import json, os, re
from typing import Any
import anthropic

_CLIENT: anthropic.Anthropic | None = None

def _get_client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT

def _call_claude(prompt: str) -> Any:
    return _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

_TEMPLATE_INSTRUCTIONS = {
    "complete": "The task is now complete. Write an email notifying the requester it is done.",
    "waiting": "You are waiting for the requester to take action or respond. Write an email chasing them.",
    "needs-info": "You need more information before you can proceed. Write an email requesting clarification.",
    "update": "Write a mid-task progress update email.",
}

_TONE_INSTRUCTIONS = {
    "formal": "Use professional, formal language.",
    "friendly": "Use warm, friendly but professional language.",
    "brief": "Be concise. 3 sentences maximum.",
}

def build_prompt(interrupt: dict[str, Any], template: str, tone: str) -> str:
    comments = "\n".join(
        f"- [{e['timestamp']}] {e.get('author','')}: {e['text']}"
        for e in interrupt.get("activity", [])
        if e["type"] == "comment"
    )
    tags = ", ".join(interrupt.get("tags", [])) or "none"
    template_instruction = _TEMPLATE_INSTRUCTIONS.get(template, _TEMPLATE_INSTRUCTIONS["complete"])
    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["formal"])

    return f"""You are drafting a work email for Chase Ramone at Magiq Software.

Task details:
- Title: {interrupt['title']}
- Source: {interrupt['source']}
- Status: {interrupt['status']}
- Tags: {tags}
- Due date: {interrupt.get('dueDate') or 'none'}

Activity / comments:
{comments or 'No comments yet.'}

Instructions:
{template_instruction}
{tone_instruction}
Sign off as: Chase Ramone, Magiq Software.

Infer the recipient email address from the comments if possible, otherwise leave "to" blank.

Respond with ONLY valid JSON in this exact format:
{{"to": "<email or empty string>", "subject": "<subject line>", "body": "<email body>"}}"""

def generate_email_draft(
    interrupt: dict[str, Any], template: str, tone: str
) -> dict[str, Any]:
    try:
        response = _call_claude(build_prompt(interrupt, template, tone))
        raw = response.content[0].text.strip()
        # Extract JSON even if Claude adds markdown fences
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError("No JSON in response")
        return json.loads(m.group())
    except Exception as e:
        return {"error": str(e), "to": "", "subject": "", "body": ""}
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_email.py -v
```

Expected: all 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add tower/interrupts/email.py tests/test_email.py
git commit -m "feat(tower): email draft generation via Claude API (Haiku)"
```

---

## Task 7: FastAPI Server + All API Routes

**Files:**
- Create: `tower/server.py`
- Create: `tower/interrupts/ado_push.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

```python
# tests/test_api.py
import pytest, json
from unittest.mock import patch
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_aios, tmp_hermes, tmp_interrupts, monkeypatch):
    import tower.config as cfg
    monkeypatch.setattr(cfg, "PROJECTS_DIR", tmp_aios / "projects")
    monkeypatch.setattr(cfg, "DECISIONS_LOG", tmp_aios / "decisions" / "log.md")
    monkeypatch.setattr(cfg, "ADO_PENDING", tmp_hermes / "ado-pending.json")
    monkeypatch.setattr(cfg, "ADHOC_NOTES", tmp_hermes / "adhoc-notes.md")
    monkeypatch.setattr(cfg, "HERMES_PROJECTS", tmp_hermes / "projects")
    monkeypatch.setattr(cfg, "INTERRUPTS_FILE", tmp_interrupts)
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

def test_get_hermes_inbox(client):
    r = client.get("/api/hermes/inbox")
    assert r.status_code == 200
    assert len(r.json()) == 1

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
```

- [ ] **Step 2: Run — verify fail**

```bash
pytest tests/test_api.py -v
```

Expected: `ImportError` — `tower.server` doesn't exist.

- [ ] **Step 3: Implement `tower/interrupts/ado_push.py`**

```python
"""Push an interrupt to ADO as a Task via the ADO REST API."""
import os
import httpx
from typing import Any

ADO_ORG = os.getenv("ADO_ORG", "")
ADO_PROJECT = os.getenv("ADO_PROJECT", "")
ADO_PAT = os.getenv("ADO_PAT", "")

def push_to_ado(interrupt: dict[str, Any]) -> dict[str, Any]:
    """Create an ADO Task for the given interrupt. Returns {"adoItemId": int}."""
    if not all([ADO_ORG, ADO_PROJECT, ADO_PAT]):
        raise EnvironmentError("ADO_ORG, ADO_PROJECT, ADO_PAT env vars required")

    comments = "\n".join(
        f"[{e['timestamp']}] {e.get('author','')}: {e['text']}"
        for e in interrupt.get("activity", [])
        if e["type"] == "comment"
    )
    url = (
        f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}/_apis/wit/workitems/$Task"
        "?api-version=7.1"
    )
    body = [
        {"op": "add", "path": "/fields/System.Title",
         "value": f"[Interrupt] {interrupt['title']}"},
        {"op": "add", "path": "/fields/System.Description",
         "value": f"Source: {interrupt['source']}. Captured: {interrupt['capturedAt']}.\n\n{comments}"},
        {"op": "add", "path": "/fields/System.AreaPath", "value": ADO_PROJECT},
    ]
    if interrupt.get("dueDate"):
        body.append({"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.DueDate",
                     "value": interrupt["dueDate"]})

    r = httpx.patch(url, json=body,
                    headers={"Content-Type": "application/json-patch+json"},
                    auth=("", ADO_PAT), timeout=15)
    r.raise_for_status()
    return {"adoItemId": r.json()["id"]}
```

- [ ] **Step 4: Implement `tower/server.py`**

```python
import webbrowser, threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any

from tower import config
from tower.readers.projects import read_projects
from tower.readers.decisions import read_decisions
from tower.readers.hermes import read_ado_pending, read_adhoc_notes, read_hermes_project_captures
from tower.readers.ado import read_ado_sprint
from tower.interrupts.store import (
    load_interrupts, create_interrupt, update_interrupt,
    delete_interrupt, append_activity
)
from tower.interrupts.email import generate_email_draft
from tower.interrupts.ado_push import push_to_ado

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-open browser after brief delay
    def _open():
        import time; time.sleep(1)
        webbrowser.open(f"http://localhost:{config.PORT}")
    threading.Thread(target=_open, daemon=True).start()
    yield

app = FastAPI(title="AIS-OS Control Tower", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# --- Health ---

@app.get("/api/health")
def health() -> dict[str, Any]:
    sources = {
        "projects": config.PROJECTS_DIR.exists(),
        "hermes_pending": config.ADO_PENDING.exists(),
        "adhoc_notes": config.ADHOC_NOTES.exists(),
        "decisions": config.DECISIONS_LOG.exists(),
        "interrupts": config.INTERRUPTS_FILE.exists(),
    }
    return {"status": "ok", "sources": sources}

# --- Projects ---

@app.get("/api/projects")
def projects() -> list[dict[str, Any]]:
    return read_projects()

# --- Decisions ---

@app.get("/api/decisions")
def decisions(limit: int = 10) -> list[dict[str, Any]]:
    return read_decisions(limit=limit)

# --- Hermes ---

@app.get("/api/hermes/inbox")
def hermes_inbox() -> list[dict[str, Any]]:
    return read_ado_pending()

@app.get("/api/hermes/adhoc")
def hermes_adhoc() -> list[dict[str, Any]]:
    return read_adhoc_notes()

@app.get("/api/hermes/sync")
def hermes_sync() -> dict[str, Any]:
    return read_hermes_project_captures()

# --- ADO ---

@app.get("/api/ado/sprint")
def ado_sprint() -> dict[str, Any]:
    return read_ado_sprint()

# --- Interrupts ---

class InterruptCreate(BaseModel):
    title: str
    source: str
    dueDate: str | None = None
    priority: str = "normal"

class InterruptUpdate(BaseModel):
    title: str | None = None
    source: str | None = None
    dueDate: str | None = None
    priority: str | None = None
    status: str | None = None
    tags: list[str] | None = None
    adoItemId: int | None = None

class ActivityEntry(BaseModel):
    type: str
    text: str
    author: str | None = None

class EmailDraftRequest(BaseModel):
    template: str = "complete"
    tone: str = "formal"

@app.get("/api/interrupts")
def get_interrupts() -> list[dict[str, Any]]:
    return load_interrupts(config.INTERRUPTS_FILE)

@app.post("/api/interrupts", status_code=201)
def post_interrupt(body: InterruptCreate) -> dict[str, Any]:
    return create_interrupt(config.INTERRUPTS_FILE,
                            title=body.title, source=body.source,
                            due_date=body.dueDate, priority=body.priority)

@app.patch("/api/interrupts/{interrupt_id}")
def patch_interrupt(interrupt_id: str, body: InterruptUpdate) -> dict[str, Any]:
    try:
        return update_interrupt(config.INTERRUPTS_FILE, interrupt_id,
                                **{k: v for k, v in body.model_dump().items() if v is not None})
    except KeyError:
        raise HTTPException(404, f"Interrupt {interrupt_id!r} not found")

@app.delete("/api/interrupts/{interrupt_id}", status_code=204)
def del_interrupt(interrupt_id: str) -> Response:
    delete_interrupt(config.INTERRUPTS_FILE, interrupt_id)
    return Response(status_code=204)

@app.post("/api/interrupts/{interrupt_id}/activity")
def post_activity(interrupt_id: str, body: ActivityEntry) -> dict[str, Any]:
    try:
        return append_activity(config.INTERRUPTS_FILE, interrupt_id,
                               entry_type=body.type, text=body.text, author=body.author)
    except KeyError:
        raise HTTPException(404, f"Interrupt {interrupt_id!r} not found")

@app.post("/api/interrupts/{interrupt_id}/email-draft")
def email_draft(interrupt_id: str, body: EmailDraftRequest) -> dict[str, Any]:
    items = load_interrupts(config.INTERRUPTS_FILE)
    item = next((i for i in items if i["id"] == interrupt_id), None)
    if not item:
        raise HTTPException(404, f"Interrupt {interrupt_id!r} not found")
    return generate_email_draft(item, template=body.template, tone=body.tone)

@app.post("/api/interrupts/{interrupt_id}/push-ado")
def push_ado(interrupt_id: str) -> dict[str, Any]:
    items = load_interrupts(config.INTERRUPTS_FILE)
    item = next((i for i in items if i["id"] == interrupt_id), None)
    if not item:
        raise HTTPException(404, f"Interrupt {interrupt_id!r} not found")
    try:
        result = push_to_ado(item)
        update_interrupt(config.INTERRUPTS_FILE, interrupt_id, adoItemId=result["adoItemId"])
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

# --- Static (must be last) ---

app.mount("/", StaticFiles(directory=str(config.TOWER_DIR / "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tower.server:app", host="0.0.0.0", port=config.PORT, reload=True)
```

- [ ] **Step 5: Run all API tests**

```bash
pytest tests/test_api.py -v
```

Expected: all 10 PASS. If `StaticFiles` mount fails (no `index.html` yet), that's fine — create an empty placeholder:

```bash
echo "<html><body>loading...</body></html>" > tower/static/index.html
```

Then re-run.

- [ ] **Step 6: Smoke-test the server**

```bash
python tower/server.py &
curl http://localhost:8765/api/health
curl http://localhost:8765/api/projects
```

Expected: JSON responses with no errors.

```bash
kill %1
```

- [ ] **Step 7: Commit**

```bash
git add tower/server.py tower/interrupts/ado_push.py tests/test_api.py tower/static/index.html
git commit -m "feat(tower): FastAPI server with all API routes"
```

---

## Task 8: Frontend Shell (Layout + CSS)

**Files:**
- Modify: `tower/static/index.html` (full rewrite)

This task builds the static shell — top bar, sidebar, main layout, CSS. No live data yet. Panels render placeholder content.

- [ ] **Step 1: Write `tower/static/index.html` — shell**

Replace the placeholder with the full shell. Use the approved v2 mockup (`docs/mockups/dashboard-layout-v2.html`) as the visual reference. The shell must include:

**CSS variables** (copy exact values from mockup):
```css
:root {
  --bg: #0d1117; --surface: #161b22; --surface2: #21262d; --border: #30363d;
  --accent: #58a6ff; --accent2: #3fb950; --warn: #d29922; --danger: #f85149;
  --purple: #bc8cff; --text: #e6edf3; --muted: #8b949e;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 13px;
}
```

**Top bar** (`<div id="topbar">`):
- Logo: "AIS-OS Control Tower"
- Status pills container (`<div id="status-pills">`) — populated by JS
- Refresh button (`<button id="refresh-btn">`)
- Last-refreshed text (`<span id="last-refresh">`)
- Clock (`<span id="clock">`)

**Sidebar** (`<nav id="sidebar">`):
Sections: My Work · Interrupts · Projects · Inbox · Team · History · Reference. Each `<a>` has a `data-view` attribute matching its panel ID. Badge spans with IDs for live counts (e.g. `id="badge-ado-pending"`).

**Main content** (`<main id="main">`):
Placeholder `<div>` elements with IDs for each section:
- `#focus-strip`
- `#blocked-banner` (hidden by default: `style="display:none"`)
- `#standup-strip`
- `#projects-row`
- `#panel-grid` (3-col grid: `#ado-panel`, `#hermes-panel`, `#adhoc-panel`)
- `#team-row`
- `#decisions-sync-row` (2-col: `#decisions-panel`, `#sync-panel`)
- `#cheatsheet` (collapsible)
- `#interrupts-section` (hidden by default, shown when sidebar "Interrupts" clicked)
- `#drilldown-panel` (hidden by default, full-width)

- [ ] **Step 2: Verify shell renders correctly**

```bash
python tower/server.py &
```

Open `http://localhost:8765` in browser. Verify layout matches v2 mockup structure. No JS errors in console.

```bash
kill %1
```

- [ ] **Step 3: Commit**

```bash
git add tower/static/index.html
git commit -m "feat(tower): frontend HTML shell and CSS layout"
```

---

## Task 9: Frontend Data Layer (JS Polling + Panel Rendering)

**Files:**
- Modify: `tower/static/index.html` (add `<script>` section)

- [ ] **Step 1: Add global state + fetch layer**

Add to `<script>` at bottom of `index.html`:

```javascript
// ── State ──────────────────────────────────────────────────────────────
const state = {
  projects: [], ado: {items:[]}, hermesInbox: [], adhoc: [],
  decisions: [], hermesSync: {}, interrupts: [], health: {}
};

let lastRefreshed = null;

// ── Fetch helpers ───────────────────────────────────────────────────────
async function fetchAll() {
  const endpoints = {
    projects:    '/api/projects',
    ado:         '/api/ado/sprint',
    hermesInbox: '/api/hermes/inbox',
    adhoc:       '/api/hermes/adhoc',
    decisions:   '/api/decisions',
    hermesSync:  '/api/hermes/sync',
    interrupts:  '/api/interrupts',
    health:      '/api/health',
  };
  const results = await Promise.allSettled(
    Object.entries(endpoints).map(([key, url]) =>
      fetch(url).then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => ({ key, data }))
    )
  );
  results.forEach(r => {
    if (r.status === 'fulfilled') state[r.value.key] = r.value.data;
  });
  lastRefreshed = new Date();
  renderAll();
}

// ── Render orchestrator ──────────────────────────────────────────────────
function renderAll() {
  renderClock();
  renderStatusPills();
  renderFocusStrip();
  renderBlockedBanner();
  renderStandupStrip();
  renderProjects();
  renderADOPanel();
  renderHermesPanel();
  renderAdhocPanel();
  renderTeamRow();
  renderDecisionsPanel();
  renderSyncPanel();
  renderInterruptsSection();
  updateBadges();
  document.getElementById('last-refresh').textContent =
    lastRefreshed ? `↻ ${_ago(lastRefreshed)}` : '';
}

// ── Clock ───────────────────────────────────────────────────────────────
function renderClock() {
  const d = new Date();
  document.getElementById('clock').textContent =
    d.toLocaleDateString('en-AU', {weekday:'short', day:'numeric', month:'short'}) +
    ' · ' + d.toLocaleTimeString('en-AU', {hour:'2-digit', minute:'2-digit'});
}

function _ago(date) {
  const s = Math.floor((Date.now() - date) / 1000);
  if (s < 60) return `${s}s ago`;
  return `${Math.floor(s/60)}m ago`;
}

// ── Auto-refresh ─────────────────────────────────────────────────────────
setInterval(fetchAll, 30000);   // full refresh every 30s
setInterval(renderClock, 10000); // clock update every 10s
document.getElementById('refresh-btn').addEventListener('click', fetchAll);

// Kick off on load
fetchAll();
```

- [ ] **Step 2: Implement `renderStatusPills()`**

```javascript
function renderStatusPills() {
  const h = state.health;
  const pending = (state.hermesInbox || []).filter(i => i.status === 'pending').length;
  const blocked = (state.ado.items || []).filter(i => i.state === 'Blocked').length;
  const overdue = (state.interrupts || []).filter(i => {
    return i.dueDate && new Date(i.dueDate) < new Date() && i.status !== 'done';
  }).length;

  const pills = [
    { label: 'Hermes', ok: h.sources?.hermes_pending !== false },
    { label: 'ADO', ok: !state.ado.error },
    pending > 0 ? { label: `${pending} pending flush`, warn: true } : null,
    blocked > 0 ? { label: `${blocked} blocked`, danger: true } : null,
    overdue > 0 ? { label: `${overdue} overdue`, danger: true } : null,
  ].filter(Boolean);

  document.getElementById('status-pills').innerHTML = pills.map(p => {
    const cls = p.danger ? 'danger' : p.warn ? 'warn' : p.ok ? 'green' : 'red';
    return `<div class="status-pill"><div class="dot ${cls}"></div>${p.label}</div>`;
  }).join('');
}
```

- [ ] **Step 3: Implement project card rendering**

```javascript
function renderProjects() {
  const el = document.getElementById('projects-row');
  if (!state.projects.length) {
    el.innerHTML = '<p class="muted">No projects found.</p>'; return;
  }
  el.innerHTML = state.projects.map(p => `
    <div class="project-card" onclick="openProjectDrilldown('${p.slug}')">
      <div class="card-top">
        <div class="card-name">${p.slug}</div>
        <div class="card-priority priority-${p.priority === 'High' ? 'high' : 'med'}">${p.priority || ''}</div>
      </div>
      <div class="card-status">${p.status}</div>
      <div class="card-meta">
        ${_adoCountChip(p.slug)}
      </div>
    </div>
  `).join('');
}

function _adoCountChip(slug) {
  const items = (state.ado.items || []).filter(i =>
    (i.project || '').toLowerCase().includes(slug.toLowerCase())
  );
  if (!items.length) return '';
  return `<div class="meta-chip accent">${items.length} ADO items</div>`;
}
```

- [ ] **Step 4: Implement ADO panel, Hermes panel, Adhoc panel**

```javascript
function renderADOPanel() {
  const items = state.ado.items || [];
  const myItems = items.filter(i => (i.assignee || '').includes('Chase'));
  renderItemList('ado-panel-body', myItems.slice(0, 8), i => `
    <div class="ado-row" onclick="openADODrilldown(${i.id})">
      <div class="ado-state ${_adoStateClass(i.state)}"></div>
      <div class="ado-body">
        <div class="ado-text">${i.title}</div>
        <div class="ado-meta">${i.module || ''} · ${i.type || ''} · ${i.state}</div>
      </div>
      ${i.state === 'Code Review' ? `<div class="review-age ${_ageClass(i.daysInState)}">${i.daysInState}d</div>` : ''}
    </div>
  `);
}

function _adoStateClass(state) {
  if (state === 'Active' || state === 'In Progress') return 'state-active';
  if (state === 'Code Review') return 'state-review';
  if (state === 'Blocked') return 'state-blocked';
  if (state === 'Done' || state === 'Closed') return 'state-done';
  return 'state-active';
}

function _ageClass(days) {
  if (days <= 2) return 'age-ok';
  if (days <= 5) return 'age-warn';
  return 'age-old';
}

function renderHermesPanel() {
  const items = state.hermesInbox || [];
  renderItemList('hermes-panel-body', items, i => `
    <div class="list-item">
      <div class="item-icon">📌</div>
      <div style="flex:1">
        <div class="item-title">${i.title}</div>
        <div class="item-meta">${i.project} · ${i.module} · ${i.type}</div>
      </div>
      <div class="item-tag">${i.status}</div>
    </div>
  `);
}

function renderAdhocPanel() {
  const items = (state.adhoc || []).slice(0, 5);
  renderItemList('adhoc-panel-body', items, i => `
    <div class="list-item">
      <div style="flex:1">
        <div class="item-title">${i.title}</div>
        <div class="item-meta">${_formatTs(i.timestamp)}</div>
      </div>
    </div>
  `);
}

function renderItemList(containerId, items, renderFn) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = items.length
    ? items.map(renderFn).join('')
    : '<div class="muted" style="padding:10px;font-size:11px">No items</div>';
}

function _formatTs(ts) {
  if (!ts) return '';
  try { return new Date(ts).toLocaleString('en-AU', {dateStyle:'short', timeStyle:'short'}); }
  catch { return ts; }
}
```

- [ ] **Step 5: Implement `renderFocusStrip()`, `renderBlockedBanner()`, `renderStandupStrip()`**

```javascript
function renderFocusStrip() {
  const items = state.ado.items || [];
  const myActive = items.filter(i =>
    (i.assignee || '').includes('Chase') &&
    ['Active', 'In Progress'].includes(i.state)
  );
  const el = document.getElementById('focus-strip');
  if (!myActive.length) { el.style.display = 'none'; return; }
  el.style.display = '';
  const item = myActive[0];
  el.querySelector('.focus-title').textContent = item.title;
  el.querySelector('.focus-meta').textContent =
    `${item.module || ''} · ${item.type || ''} · ${item.state}`;

  // Interrupt impact
  const overdue = (state.interrupts || []).filter(i =>
    i.dueDate && new Date(i.dueDate) < new Date() && i.status !== 'done'
  ).length;
  const dueToday = (state.interrupts || []).filter(i => {
    if (!i.dueDate || i.status === 'done') return false;
    const d = new Date(i.dueDate); const t = new Date();
    return d.toDateString() === t.toDateString();
  }).length;
  const impactEl = el.querySelector('.interrupt-impact-text');
  if (impactEl) {
    const total = overdue + dueToday;
    impactEl.style.display = total > 0 ? '' : 'none';
    if (total > 0) impactEl.textContent =
      `⚡ ${total} interrupt${total>1?'s':''} competing with sprint focus`;
  }
}

function renderBlockedBanner() {
  const blocked = (state.ado.items || []).filter(i => i.state === 'Blocked');
  const el = document.getElementById('blocked-banner');
  if (!blocked.length) { el.style.display = 'none'; return; }
  el.style.display = '';
  el.querySelector('.blocked-items').innerHTML = blocked.map(i => `
    <div class="blocked-item">
      <div class="blocked-who">${(i.assignee || '').split(' ')[0]}</div>
      <div class="blocked-reason">${i.title}</div>
      <div class="blocked-age">${i.daysInState || 0}d</div>
    </div>
  `).join('');
}

function renderStandupStrip() {
  const items = state.ado.items || [];
  const yesterday = items.filter(i =>
    ['Done','Closed'].includes(i.state) && i.daysInState <= 1
  ).slice(0,3);
  const today = items.filter(i =>
    (i.assignee||'').includes('Chase') &&
    ['Active','In Progress','Code Review'].includes(i.state)
  ).slice(0,3);
  const blockers = [
    ...(items.filter(i => i.state === 'Blocked').map(i => i.title)),
    ...((state.interrupts||[]).filter(i =>
      i.dueDate && new Date(i.dueDate) < new Date() && i.status !== 'done'
    ).map(i => `Overdue interrupt: ${i.title}`))
  ];

  const fmt = (arr, cls='') => arr.length
    ? arr.map(t => `<div class="standup-item ${cls}">${t.title||t}</div>`).join('')
    : '<div class="standup-item muted">None</div>';

  document.getElementById('standup-yesterday').innerHTML = fmt(yesterday);
  document.getElementById('standup-today').innerHTML = fmt(today);
  document.getElementById('standup-blockers').innerHTML = fmt(blockers, 'blocker');

  document.getElementById('standup-copy').onclick = () => {
    const text = [
      'Yesterday:\n' + yesterday.map(i=>`• ${i.title}`).join('\n'),
      'Today:\n' + today.map(i=>`• ${i.title}`).join('\n'),
      'Blockers:\n' + (blockers.length ? blockers.map(b=>`• ${b}`).join('\n') : '• None'),
    ].join('\n\n');
    navigator.clipboard.writeText(text);
  };
}
```

- [ ] **Step 6: Implement team row, decisions, sync panels**

```javascript
function renderTeamRow() {
  const items = state.ado.items || [];
  const members = [
    { name: 'Chase Ramone', role: 'Team Lead + Developer', match: 'Chase' },
    { name: 'Estelle Wu', role: 'API Layer', match: 'Estelle' },
    { name: 'Akshay Gaikwad', role: 'UI / Integrations', match: 'Akshay' },
  ];
  document.getElementById('team-row').innerHTML = members.map(m => {
    const mine = items.filter(i => (i.assignee||'').includes(m.match));
    const active = mine.filter(i => ['Active','In Progress'].includes(i.state)).length;
    const review = mine.filter(i => i.state === 'Code Review').length;
    const blocked = mine.filter(i => i.state === 'Blocked').length;
    const wip = mine.find(i => ['Active','In Progress'].includes(i.state));
    return `
      <div class="team-card">
        <div class="team-name">${m.name}</div>
        <div class="team-role">${m.role}</div>
        <div class="team-stats">
          <div class="team-stat stat-blue">${active} active</div>
          <div class="team-stat stat-warn">${review} in review</div>
          <div class="team-stat ${blocked?'stat-red':'stat-green'}">${blocked} blocked</div>
        </div>
        <div class="team-wip">WIP: <strong>${wip ? wip.title : '—'}</strong></div>
      </div>`;
  }).join('');
}

function renderDecisionsPanel() {
  const items = (state.decisions || []).slice(0, 5);
  renderItemList('decisions-body', items, d => `
    <div class="decision-row">
      <div class="decision-date">${d.date}</div>
      <div>
        <div class="decision-text">${d.text}</div>
        ${d.project ? `<div class="decision-tag">${d.project}</div>` : ''}
      </div>
    </div>
  `);
}

function renderSyncPanel() {
  const sync = state.hermesSync || {};
  const pending = (state.hermesInbox || []).filter(i => i.status === 'pending').length;
  const items = [
    ...Object.entries(sync).map(([slug, data]) => ({
      icon: '✅', text: `${slug} — synced`,
      meta: `${Object.values(data).filter(v=>v&&v.length).length} pending captures`
    })),
    pending > 0 ? { icon: '📥', text: `${pending} ADO items pending flush`,
      meta: 'Say "flush pending notes" to push to ADO' } : null
  ].filter(Boolean);
  renderItemList('sync-body', items, i => `
    <div class="list-item">
      <div class="item-icon">${i.icon}</div>
      <div style="flex:1">
        <div class="item-title">${i.text}</div>
        <div class="item-meta">${i.meta}</div>
      </div>
    </div>
  `);
}
```

- [ ] **Step 7: Implement `updateBadges()`**

```javascript
function updateBadges() {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('badge-interrupts', (state.interrupts||[]).filter(i=>i.status!=='done').length || '');
  set('badge-ado-pending', (state.hermesInbox||[]).filter(i=>i.status==='pending').length || '');
  set('badge-blocked', (state.ado.items||[]).filter(i=>i.state==='Blocked').length || '');
  const overdue = (state.interrupts||[]).filter(i=>
    i.dueDate && new Date(i.dueDate)<new Date() && i.status!=='done').length;
  set('badge-overdue', overdue || '');
  set('badge-due-today', (state.interrupts||[]).filter(i=>{
    if (!i.dueDate||i.status==='done') return false;
    return new Date(i.dueDate).toDateString()===new Date().toDateString();
  }).length || '');
}
```

- [ ] **Step 8: Test in browser**

```bash
python tower/server.py
```

Open `http://localhost:8765`. All panels should populate with real data within 30s. Check browser console for errors.

- [ ] **Step 9: Commit**

```bash
git add tower/static/index.html
git commit -m "feat(tower): frontend data layer, panel rendering, auto-refresh"
```

---

## Task 10: Interrupts UI

**Files:**
- Modify: `tower/static/index.html`

- [ ] **Step 1: Implement `renderInterruptsSection()`**

Add to script:

```javascript
function renderInterruptsSection() {
  const items = state.interrupts || [];
  const open = items.filter(i => i.status !== 'done');
  const overdue = open.filter(i => i.dueDate && new Date(i.dueDate) < new Date());
  const dueToday = open.filter(i => {
    if (!i.dueDate) return false;
    return new Date(i.dueDate).toDateString() === new Date().toDateString();
  });

  // Triage counts
  document.getElementById('triage-overdue').textContent = overdue.length;
  document.getElementById('triage-today').textContent = dueToday.length;
  document.getElementById('triage-open').textContent = open.length;
  document.getElementById('triage-done').textContent =
    items.filter(i=>i.status==='done').length;

  // List
  renderItemList('interrupts-list', open, i => `
    <div class="interrupt-row" onclick="openInterruptDrilldown('${i.id}')">
      <div class="priority-dot p-${i.priority}"></div>
      <div class="interrupt-body">
        <div class="interrupt-title">${i.title}</div>
        <div class="interrupt-meta">
          <span class="source-tag src-${i.source.toLowerCase()}">${i.source}</span>
          ${i.tags.map(t=>`<span class="tag tag-${t} active">${t}</span>`).join('')}
          <span class="interrupt-age">${_ago(new Date(i.capturedAt))}</span>
        </div>
      </div>
      ${i.dueDate ? `<div class="due-chip ${_dueClass(i.dueDate)}">${_dueLabel(i.dueDate)}</div>` : '<div class="due-none">No due date</div>'}
      <div class="status-tag status-${i.status}">${i.status}</div>
      <button class="action-btn" onclick="event.stopPropagation();pushToADO('${i.id}')">→ ADO</button>
      <button class="action-btn done" onclick="event.stopPropagation();markDone('${i.id}')">✓ Done</button>
    </div>
  `);
}

function _dueClass(dueDate) {
  const d = new Date(dueDate); const now = new Date();
  if (d < now) return 'due-today'; // overdue = red
  const diff = (d - now) / 86400000;
  if (diff <= 1) return 'due-today';
  if (diff <= 3) return 'due-soon';
  return 'due-none';
}

function _dueLabel(dueDate) {
  const d = new Date(dueDate); const now = new Date();
  if (d < now) return `Overdue · was ${d.toLocaleDateString('en-AU',{day:'numeric',month:'short'})}`;
  if (d.toDateString() === now.toDateString()) return 'Due today';
  return `Due ${d.toLocaleDateString('en-AU',{day:'numeric',month:'short'})}`;
}
```

- [ ] **Step 2: Wire quick-capture form**

```javascript
document.getElementById('interrupt-capture-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const body = {
    title: form.title.value,
    source: form.source.value,
    dueDate: form.dueDate.value || null,
    priority: form.priority?.value || 'normal',
  };
  await fetch('/api/interrupts', { method: 'POST',
    headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  form.reset();
  await fetchAll();
});
```

- [ ] **Step 3: Wire `markDone()` and `pushToADO()`**

```javascript
async function markDone(id) {
  await fetch(`/api/interrupts/${id}`, {
    method: 'PATCH',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({status:'done'})
  });
  await fetchAll();
}

async function pushToADO(id) {
  const r = await fetch(`/api/interrupts/${id}/push-ado`, {method:'POST'});
  if (r.ok) { alert('Pushed to ADO'); await fetchAll(); }
  else { const e = await r.json(); alert(`ADO push failed: ${e.detail}`); }
}
```

- [ ] **Step 4: Test interrupt capture and list**

Open `http://localhost:8765`. Navigate to Interrupts via sidebar. Capture a test interrupt. Verify it appears in the list. Mark it done. Verify it disappears from the open list.

- [ ] **Step 5: Commit**

```bash
git add tower/static/index.html
git commit -m "feat(tower): interrupts list, quick capture, triage counts"
```

---

## Task 11: Interrupt Drill-Down (Comments + Tags + Email Draft)

**Files:**
- Modify: `tower/static/index.html`

- [ ] **Step 1: Implement `openInterruptDrilldown(id)`**

```javascript
function openInterruptDrilldown(id) {
  const item = (state.interrupts || []).find(i => i.id === id);
  if (!item) return;
  const panel = document.getElementById('drilldown-panel');
  panel.style.display = '';
  panel.dataset.interruptId = id;

  // Header
  panel.querySelector('.dd-title').textContent = item.title;
  panel.querySelector('.dd-source').textContent = item.source;
  panel.querySelector('.dd-status').textContent = item.status;
  panel.querySelector('.dd-age').textContent = `Captured ${_ago(new Date(item.capturedAt))}`;

  // Tags
  renderDrilldownTags(panel, item);

  // Activity
  renderActivityFeed(panel, item);

  // Email draft panel — reset to template selector
  panel.querySelector('.email-preview').style.display = 'none';
  panel.querySelector('.email-actions').style.display = 'none';

  panel.scrollIntoView({behavior:'smooth'});
}

const BUILTIN_TAGS = ['blocked','waiting-for-feedback','requested-review','needs-more-info','complete'];

function renderDrilldownTags(panel, item) {
  const container = panel.querySelector('.tags-row');
  container.innerHTML = BUILTIN_TAGS.map(t => {
    const active = item.tags.includes(t);
    return `<div class="tag tag-${t} ${active?'active':''}"
      onclick="toggleTag('${item.id}','${t}')">${_tagLabel(t)}</div>`;
  }).join('') + `<div class="tag tag-add" onclick="promptCustomTag('${item.id}')">+ add tag</div>`;
}

function _tagLabel(t) {
  const map = {
    'blocked':'🚫 Blocked','waiting-for-feedback':'⏳ Waiting for feedback',
    'requested-review':'👁 Requested review','needs-more-info':'💬 Needs more info',
    'complete':'✅ Complete'
  };
  return map[t] || t;
}

async function toggleTag(id, tag) {
  const item = (state.interrupts||[]).find(i=>i.id===id);
  if (!item) return;
  const tags = item.tags.includes(tag) ? item.tags.filter(t=>t!==tag) : [...item.tags, tag];
  const eventText = item.tags.includes(tag) ? `Removed tag: ${tag}` : `Added tag: ${tag}`;
  await fetch(`/api/interrupts/${id}`, {
    method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({tags})
  });
  await fetch(`/api/interrupts/${id}/activity`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({type:'event', text:eventText})
  });
  await fetchAll();
  openInterruptDrilldown(id); // re-render drill-down
}

async function promptCustomTag(id) {
  const tag = prompt('Enter custom tag:');
  if (!tag) return;
  const item = (state.interrupts||[]).find(i=>i.id===id);
  if (!item) return;
  const tags = [...item.tags, tag.toLowerCase().replace(/\s+/g,'-')];
  await fetch(`/api/interrupts/${id}`, {
    method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({tags})
  });
  await fetchAll();
  openInterruptDrilldown(id);
}
```

- [ ] **Step 2: Implement `renderActivityFeed()`**

```javascript
function renderActivityFeed(panel, item) {
  const feed = panel.querySelector('.comment-feed');
  feed.innerHTML = item.activity.map(e => {
    if (e.type === 'comment') return `
      <div class="comment-item">
        <div class="comment-avatar">${(e.author||'?').slice(0,2).toUpperCase()}</div>
        <div class="comment-body">
          <div class="comment-header">
            <span class="comment-author">${e.author||''}</span>
            <span class="comment-time">${_formatTs(e.timestamp)}</span>
          </div>
          <div class="comment-text">${e.text}</div>
        </div>
      </div>`;
    return `
      <div class="event-item">
        <div class="event-dot"></div>
        <span>${e.text}</span>
        <span style="margin-left:auto">${_formatTs(e.timestamp)}</span>
      </div>`;
  }).join('') || '<div class="muted" style="padding:8px;font-size:11px">No activity yet.</div>';

  // Wire comment submit
  const form = panel.querySelector('.add-comment-form');
  form.onsubmit = async e => {
    e.preventDefault();
    const text = form.querySelector('textarea').value.trim();
    if (!text) return;
    await fetch(`/api/interrupts/${item.id}/activity`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({type:'comment', author:'Chase', text})
    });
    form.querySelector('textarea').value = '';
    await fetchAll();
    openInterruptDrilldown(item.id);
  };
}
```

- [ ] **Step 3: Implement email draft panel**

```javascript
function wireEmailDraftPanel(panel, itemId) {
  const templates = panel.querySelectorAll('.template-btn');
  const tones = panel.querySelectorAll('.tone-btn');
  let selectedTemplate = 'complete';
  let selectedTone = 'formal';

  templates.forEach(btn => {
    btn.addEventListener('click', () => {
      templates.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedTemplate = btn.dataset.template;
    });
  });

  tones.forEach(btn => {
    btn.addEventListener('click', () => {
      tones.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedTone = btn.dataset.tone;
    });
  });

  async function generateDraft() {
    const previewEl = panel.querySelector('.email-preview');
    const actionsEl = panel.querySelector('.email-actions');
    previewEl.innerHTML = '<div style="padding:12px;color:var(--muted)">Generating...</div>';
    previewEl.style.display = '';

    const r = await fetch(`/api/interrupts/${itemId}/email-draft`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({template:selectedTemplate, tone:selectedTone})
    });
    const draft = await r.json();
    if (draft.error) {
      previewEl.innerHTML = `<div style="color:var(--danger);padding:10px">Error: ${draft.error}</div>`;
      return;
    }

    previewEl.innerHTML = `
      <div class="email-field">
        <div class="email-field-label">To</div>
        <div class="email-field-value">${draft.to || '<not detected>'}</div>
      </div>
      <div class="email-field">
        <div class="email-field-label">Subject</div>
        <div class="email-field-value email-subject">${draft.subject}</div>
      </div>
      <hr class="email-divider">
      <div class="email-body-text" id="email-body-editable">${draft.body.replace(/\n/g,'<br>')}</div>`;

    actionsEl.style.display = '';
    actionsEl.querySelector('.email-btn-copy').onclick = () =>
      navigator.clipboard.writeText(draft.body);
    actionsEl.querySelector('.email-btn-outlook').onclick = () => {
      const mailto = `mailto:${draft.to}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`;
      window.location.href = mailto;
    };
  }

  panel.querySelector('.generate-draft-btn').addEventListener('click', generateDraft);
  panel.querySelector('.regen-btn')?.addEventListener('click', generateDraft);
}
```

- [ ] **Step 4: Wire close button and Esc key**

```javascript
document.getElementById('drilldown-close').addEventListener('click', () => {
  document.getElementById('drilldown-panel').style.display = 'none';
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.getElementById('drilldown-panel').style.display = 'none';
});
```

- [ ] **Step 5: Test drill-down end-to-end**

Open `http://localhost:8765`. Capture a test interrupt. Click its row. Verify:
- Tags render, clicking toggles them and appends event to activity
- Comment form saves and renders in feed
- Email draft generates (requires `ANTHROPIC_API_KEY`)
- "Open in Outlook" opens mailto link

- [ ] **Step 6: Commit**

```bash
git add tower/static/index.html
git commit -m "feat(tower): interrupt drill-down with comments, tags, activity feed, email draft"
```

---

## Task 12: Keyboard Shortcuts + Cheat Sheet + Final Polish

**Files:**
- Modify: `tower/static/index.html`

- [ ] **Step 1: Implement keyboard shortcuts**

```javascript
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.ctrlKey && e.key === 'r') { e.preventDefault(); fetchAll(); }
  if (e.ctrlKey && e.key === 'k') {
    e.preventDefault();
    document.getElementById('interrupt-title-input')?.focus();
  }
  if (e.key === 'Escape') document.getElementById('drilldown-panel').style.display = 'none';
  if (e.key === 'f' || e.key === 'F') toggleFocusMode();
  if (e.key === 's' || e.key === 'S') scrollTo('standup-strip');
  if (e.key === 'i' || e.key === 'I') switchView('interrupts');
});

function toggleFocusMode() {
  const main = document.getElementById('main');
  main.classList.toggle('focus-mode');
  // focus-mode CSS: hides everything except #focus-strip and #ado-panel
}

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({behavior:'smooth'});
}

function switchView(view) {
  // Show/hide sections based on sidebar nav clicks
  document.querySelectorAll('[data-view]').forEach(el => {
    el.style.display = el.dataset.view === view || view === 'dashboard' ? '' : 'none';
  });
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.navView === view);
  });
}

// Sidebar nav
document.querySelectorAll('.nav-item[data-nav-view]').forEach(el => {
  el.addEventListener('click', () => switchView(el.dataset.navView));
});
```

- [ ] **Step 2: Wire cheat sheet collapse**

```javascript
document.getElementById('cheatsheet-header').addEventListener('click', () => {
  const body = document.getElementById('cheatsheet-body');
  const collapsed = body.style.display === 'none';
  body.style.display = collapsed ? '' : 'none';
  document.getElementById('cheatsheet-toggle').textContent = collapsed ? '▼' : '▶';
  localStorage.setItem('cheatsheet-collapsed', collapsed ? 'false' : 'true');
});

// Restore state
if (localStorage.getItem('cheatsheet-collapsed') === 'true') {
  document.getElementById('cheatsheet-body').style.display = 'none';
  document.getElementById('cheatsheet-toggle').textContent = '▶';
}
```

- [ ] **Step 3: Add `tower/static/index.html` cheat sheet content**

The cheat sheet grid is static HTML (no API call needed). Copy the 4-column grid exactly from `docs/mockups/dashboard-layout-v2.html` cheat sheet section. Ensure all content matches `hermes-integration.md` for accuracy.

- [ ] **Step 4: Add startup script `tower/start.py`**

```python
#!/usr/bin/env python
"""Single-command launcher: python tower/start.py"""
import subprocess, sys
from pathlib import Path

here = Path(__file__).parent
subprocess.run(
    [sys.executable, "-m", "uvicorn", "tower.server:app",
     "--host", "0.0.0.0", "--port", "8765", "--reload"],
    cwd=here.parent
)
```

- [ ] **Step 5: Full end-to-end smoke test**

```bash
python tower/start.py
```

Open `http://localhost:8765`. Check:
- [ ] All panels load within 5s
- [ ] Projects row shows magiq-media and magiq-auth
- [ ] Hermes inbox shows pending items
- [ ] Interrupts list loads
- [ ] Capture new interrupt, verify it appears
- [ ] Open drill-down, add comment, toggle tag
- [ ] Generate email draft
- [ ] Keyboard shortcuts: F (focus mode), S (standup), Ctrl+R (refresh), Esc (close)
- [ ] Cheat sheet collapses and state persists on reload

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 7: Final commit**

```bash
git add tower/ tests/
git commit -m "feat(tower): keyboard shortcuts, cheat sheet, startup script — control tower complete"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Auto-refresh (30s polling) — Task 9
- [x] Focus strip with interrupt impact — Tasks 9, 11
- [x] Blocked banner — Task 9
- [x] Standup prep with copy — Task 9
- [x] Project cards + sprint health bar — Task 9 (note: sprint % requires ADO to return sprint data; if not available, bar renders at 0%)
- [x] ADO panel tabs (My/Review/Team) — Task 9
- [x] Review age badges — Task 9
- [x] Team workload row — Task 9
- [x] Hermes inbox panel — Task 9
- [x] Adhoc notes panel — Task 9
- [x] Decisions panel — Task 9
- [x] Hermes sync status — Task 9
- [x] Interrupt quick-capture — Task 10
- [x] Interrupt triage counts — Task 10
- [x] Interrupt list (priority, source, due date, status, age) — Task 10
- [x] Interrupt drill-down — Task 11
- [x] Tags (built-in + custom) — Task 11
- [x] Activity feed (comments + events) — Task 11
- [x] Email draft (4 templates, 3 tones, mailto, copy) — Task 11
- [x] ADO push for interrupts — Tasks 7, 10
- [x] Keyboard shortcuts — Task 12
- [x] Cheat sheet (collapsible, 4 sections) — Task 12
- [x] Single-command startup — Task 12
- [x] Sidebar with live badge counts — Tasks 8, 9

**Potential gap:** Sprint health bar % — depends on `devops_summary.py` returning sprint/epic progress data. If it doesn't, the bar renders at 0% without breaking anything. Can be enhanced once the ADO reader output is known (Task 4, Step 1).

**Type consistency:** All interrupt IDs are strings (UUIDs). `adoItemId` is `int | None` — server PATCH route accepts this. Store uses `str` for all IDs from `uuid.uuid4()`.

