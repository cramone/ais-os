import hmac
import os
import shutil
import subprocess
import threading
import webbrowser
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tower import config
from tower.interrupts.ado_push import push_to_ado
from tower.interrupts.email import generate_email_draft
from tower.interrupts.store import (
    append_activity,
    create_interrupt,
    create_item,
    delete_activity,
    delete_interrupt,
    load_interrupts,
    make_item,
    save_interrupts,
    update_activity,
    update_interrupt,
)
from tower.readers.ado import (
    invalidate_cache as invalidate_ado_cache,
    read_ado_sprint,
    read_ado_cross_project,
)
from tower.readers.ado_update import update_work_item_state
from tower.readers.github import read_github_prs, read_github_review_requested
from tower.readers.decisions import add_decision, delete_decision, read_decisions, rename_decision
from tower.readers.claudia import send_to_claudia
from tower.readers.projects import read_projects
from tower.standup import generate_standup


@asynccontextmanager
async def lifespan(app: FastAPI):
    def _open():
        import time
        time.sleep(1)
        webbrowser.open(f"http://localhost:{config.PORT}")
    threading.Thread(target=_open, daemon=True).start()
    yield


app = FastAPI(title="AIS-OS Control Tower", lifespan=lifespan)

# Wildcard was fine for localhost-only dev. Now that Tower is reachable from
# other devices on the tailnet, scope it to known origins. Override/extend
# via TOWER_ALLOWED_ORIGINS (comma-separated) — set to the deployed hostname
# in Cortex's .env.
_default_origins = "http://localhost:8765,http://127.0.0.1:8765"
_allowed_origins = [
    o.strip()
    for o in os.getenv("TOWER_ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _token_auth(request: Request, call_next):
    """Gate /api/* with a shared bearer token when TOWER_TOKEN is set.

    Leaves /api/health open (proxy healthchecks) and lets CORS preflight through.
    """
    token = config.TOWER_TOKEN
    path = request.url.path
    if (
        token
        and request.method != "OPTIONS"
        and path.startswith("/api")
        and path != "/api/health"
    ):
        provided = request.headers.get("authorization", "")
        if not hmac.compare_digest(provided, f"Bearer {token}"):
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return await call_next(request)


# --- Health ---

def _hermes_container_up() -> bool:
    """True if Claudia is reachable.

    Cortex: probes the host-side HTTP bridge (CLAUDIA_BRIDGE_URL) fronting
    the bare-metal `claudia` CLI. Windows dev: falls back to checking for a
    running Docker container named 'hermes'.
    """
    bridge_url = os.getenv("CLAUDIA_BRIDGE_URL", "")
    if bridge_url:
        try:
            import httpx
            r = httpx.get(f"{bridge_url.rstrip('/')}/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(
            ["docker", "ps", "--filter", "name=hermes", "--format", "{{.Names}}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        )
        return "hermes" in r.stdout
    except Exception:
        return False


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Probe real source reachability, not just file existence."""
    sources = {
        "projects": config.PROJECTS_DIR.exists(),
        "decisions": config.DECISIONS_LOG.exists(),
        "interrupts": config.INTERRUPTS_FILE.exists(),
        "ado": config.ADO_SCRIPT.exists() and bool(os.getenv("AZURE_DEVOPS_PAT")),
        "github": shutil.which("gh") is not None,
        "claudia": _hermes_container_up(),
    }
    core_ok = all((sources["projects"], sources["decisions"], sources["interrupts"]))
    return {"status": "ok" if core_ok else "degraded", "sources": sources}


# --- Projects ---

@app.get("/api/projects")
def projects() -> list[dict[str, Any]]:
    return read_projects()


# --- Decisions ---

@app.get("/api/decisions")
def decisions(limit: int = 10) -> list[dict[str, Any]]:
    return read_decisions(limit=limit)


class DecisionDeleteRequest(BaseModel):
    date: str
    title: str


class DecisionRenameRequest(BaseModel):
    date: str
    old_title: str
    new_title: str


class DecisionAddRequest(BaseModel):
    date: str
    title: str
    project: str | None = None


@app.post("/api/decisions/add", status_code=201)
def decision_add(req: DecisionAddRequest) -> dict:
    if not add_decision(req.date, req.title, project=req.project):
        raise HTTPException(500, "Failed to add decision")
    return {"date": req.date, "title": req.title}


@app.delete("/api/decisions", status_code=204)
def decision_delete(req: DecisionDeleteRequest):
    if not delete_decision(req.date, req.title):
        raise HTTPException(404, "Decision not found")


@app.patch("/api/decisions")
def decision_rename(req: DecisionRenameRequest) -> dict:
    if not rename_decision(req.date, req.old_title, req.new_title):
        raise HTTPException(404, "Decision not found")
    return {"date": req.date, "title": req.new_title}


# --- ADO ---

@app.get("/api/ado/sprint")
def ado_sprint() -> dict[str, Any]:
    return read_ado_sprint()


@app.get("/api/ado/cross-project")
def ado_cross_project() -> dict[str, Any]:
    return read_ado_cross_project()


class AdoStateUpdate(BaseModel):
    state: str


@app.post("/api/ado/items/{item_id}/state")
def ado_update_state(item_id: int, body: AdoStateUpdate) -> dict[str, Any]:
    try:
        result = update_work_item_state(item_id, body.state)
        invalidate_ado_cache()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- GitHub ---

@app.get("/api/github/prs")
def github_prs() -> list[dict[str, Any]]:
    return read_github_prs()


@app.get("/api/github/review-requested")
def github_review_requested() -> list[dict[str, Any]]:
    return read_github_review_requested()


# --- Claudia ---

class ClaudiaMessage(BaseModel):
    message: str


@app.post("/api/claudia/send")
def claudia_send(body: ClaudiaMessage) -> dict[str, Any]:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message required")
    return send_to_claudia(body.message.strip())


# --- Standup ---

@app.post("/api/standup/generate")
def standup_generate() -> dict[str, list[str]]:
    ado = read_ado_sprint()
    interrupts = load_interrupts(config.INTERRUPTS_FILE)
    try:
        return generate_standup(ado.get("items", []), interrupts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Interrupts ---

class InterruptCreate(BaseModel):
    title: str
    source: str
    dueDate: str | None = None
    priority: str = "normal"
    zendeskTicket: str | None = None
    customer: str | None = None


class InterruptUpdate(BaseModel):
    title: str | None = None
    source: str | None = None
    dueDate: str | None = None
    priority: str | None = None
    status: str | None = None
    tags: list[str] | None = None
    adoItemId: int | None = None
    zendeskTicket: str | None = None
    customer: str | None = None


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
    return create_interrupt(
        config.INTERRUPTS_FILE,
        title=body.title,
        source=body.source,
        due_date=body.dueDate,
        priority=body.priority,
        zendesk_ticket=body.zendeskTicket,
        customer=body.customer,
    )


@app.patch("/api/interrupts/{interrupt_id}")
def patch_interrupt(interrupt_id: str, body: InterruptUpdate) -> dict[str, Any]:
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        return update_interrupt(config.INTERRUPTS_FILE, interrupt_id, **updates)
    except KeyError:
        raise HTTPException(404, f"Interrupt {interrupt_id!r} not found")


@app.delete("/api/interrupts/{interrupt_id}", status_code=204)
def del_interrupt(interrupt_id: str) -> Response:
    delete_interrupt(config.INTERRUPTS_FILE, interrupt_id)
    return Response(status_code=204)


@app.post("/api/interrupts/{interrupt_id}/activity")
def post_activity(interrupt_id: str, body: ActivityEntry) -> dict[str, Any]:
    try:
        return append_activity(
            config.INTERRUPTS_FILE,
            interrupt_id,
            entry_type=body.type,
            text=body.text,
            author=body.author,
        )
    except KeyError:
        raise HTTPException(404, f"Interrupt {interrupt_id!r} not found")


class ActivityEdit(BaseModel):
    text: str


@app.patch("/api/interrupts/{interrupt_id}/activity/{index}")
def patch_activity(interrupt_id: str, index: int, body: ActivityEdit) -> dict[str, Any]:
    try:
        return update_activity(config.INTERRUPTS_FILE, interrupt_id, index, body.text)
    except KeyError:
        raise HTTPException(404, f"Interrupt {interrupt_id!r} not found")
    except IndexError:
        raise HTTPException(404, f"Activity index {index} not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/interrupts/{interrupt_id}/activity/{index}")
def del_activity(interrupt_id: str, index: int) -> dict[str, Any]:
    try:
        return delete_activity(config.INTERRUPTS_FILE, interrupt_id, index)
    except KeyError:
        raise HTTPException(404, f"Interrupt {interrupt_id!r} not found")
    except IndexError:
        raise HTTPException(404, f"Activity index {index} not found")


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


# --- Spec viewer ---

@app.get("/api/projects/{slug}/spec")
def project_spec_tree(slug: str) -> dict:
    """Return the spec directory file tree for a project."""
    spec_dir = config.PROJECTS_DIR / slug / "spec"
    if not spec_dir.exists():
        return {"files": [], "error": "no spec directory"}

    files = []
    for root, dirs, filenames in os.walk(spec_dir):
        dirs.sort()
        for fname in sorted(filenames):
            if fname.endswith(('.md', '.json', '.txt')):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, spec_dir).replace('\\', '/')
                files.append({"path": rel, "name": fname})

    return {"files": files}


@app.get("/api/projects/{slug}/spec/file")
def project_spec_file(slug: str, path: str) -> dict:
    """Return the content of a single spec file."""
    spec_dir = config.PROJECTS_DIR / slug / "spec"
    target = (spec_dir / path).resolve()
    if not str(target).startswith(str(spec_dir.resolve())):
        raise HTTPException(400, "Invalid path")
    if not target.exists():
        raise HTTPException(404, "File not found")
    content = target.read_text(encoding="utf-8", errors="replace")
    return {"path": path, "content": content}


class FileWriteRequest(BaseModel):
    content: str

@app.put("/api/projects/{slug}/spec/file")
def write_spec_file(slug: str, path: str, body: FileWriteRequest) -> dict:
    """Overwrite a single spec file."""
    spec_dir = config.PROJECTS_DIR / slug / "spec"
    target = (spec_dir / path).resolve()
    if not str(target).startswith(str(spec_dir.resolve())):
        raise HTTPException(400, "Invalid path")
    if not target.exists():
        raise HTTPException(404, "File not found")
    target.write_text(body.content, encoding="utf-8")
    return {"ok": True}


# --- Plans viewer ---

@app.get("/api/projects/{slug}/plans")
def project_plans_tree(slug: str) -> dict:
    """Return the plans directory file tree for a project."""
    plans_dir = config.PROJECTS_DIR / slug / "plans"
    if not plans_dir.exists():
        return {"files": [], "error": "no plans directory"}

    files = []
    for root, dirs, filenames in os.walk(plans_dir):
        dirs.sort()
        for fname in sorted(filenames):
            if fname.endswith(('.md', '.json', '.txt')):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, plans_dir).replace('\\', '/')
                files.append({"path": rel, "name": fname})

    return {"files": files}


@app.get("/api/projects/{slug}/plans/file")
def project_plans_file(slug: str, path: str) -> dict:
    """Return the content of a single plans file."""
    plans_dir = config.PROJECTS_DIR / slug / "plans"
    target = (plans_dir / path).resolve()
    if not str(target).startswith(str(plans_dir.resolve())):
        raise HTTPException(400, "Invalid path")
    if not target.exists():
        raise HTTPException(404, "File not found")
    content = target.read_text(encoding="utf-8", errors="replace")
    return {"path": path, "content": content}

@app.put("/api/projects/{slug}/plans/file")
def write_plans_file(slug: str, path: str, body: FileWriteRequest) -> dict:
    """Overwrite a single plans file."""
    plans_dir = config.PROJECTS_DIR / slug / "plans"
    target = (plans_dir / path).resolve()
    if not str(target).startswith(str(plans_dir.resolve())):
        raise HTTPException(400, "Invalid path")
    if not target.exists():
        raise HTTPException(404, "File not found")
    target.write_text(body.content, encoding="utf-8")
    return {"ok": True}


# --- Todos ---
# Todos share the interrupt item schema and are stored per-project as JSON
# (tower/data/todos/{slug}.json). Legacy projects/{slug}/todos.md is migrated
# once on first read, then left in place as a human-readable backup.

_TODO_STATUS_MAP = {"todo": "new", "doing": "in-progress", "done": "done"}
_TODO_STATUSES = {"new", "in-progress", "deferred", "done"}


def _migrate_todos_md(slug: str) -> list[dict[str, Any]]:
    """Parse legacy projects/{slug}/todos.md into the shared item schema."""
    md = config.PROJECTS_DIR / slug / "todos.md"
    if not md.exists():
        return []
    import re
    content = md.read_text(encoding="utf-8", errors="replace")
    items: list[dict[str, Any]] = []
    for block in re.split(r'\n(?=## )', content):
        block = block.strip()
        if not block.startswith('## '):
            continue
        lines = block.split('\n')
        heading = lines[0][3:].strip()
        captured = None
        status = "todo"
        body_lines = []
        for line in lines[1:]:
            if line.startswith('_Captured:') and captured is None:
                captured = line.strip('_').replace('Captured:', '').strip()
            elif line.startswith('_Status:'):
                status = line.strip('_').replace('Status:', '').strip().lower() or "todo"
            elif line.strip() == '---':
                break
            else:
                body_lines.append(line)
        body = '\n'.join(body_lines).strip()
        activity = []
        if body:
            activity.append({
                "type": "comment", "text": body,
                "author": "Chase", "timestamp": _now_iso(),
            })
        # Normalise the captured date to a bare ISO date when possible.
        captured_at = _now_iso()
        if captured:
            m = re.match(r'\d{4}-\d{2}-\d{2}', captured)
            if m:
                captured_at = m.group(0)
        items.append(make_item(
            heading,
            status=_TODO_STATUS_MAP.get(status, "new"),
            captured_at=captured_at,
            activity=activity,
        ))
    return items


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _load_todos(slug: str) -> list[dict[str, Any]]:
    """Load a project's todos, migrating from todos.md on first access."""
    path = config.todos_file(slug)
    if not path.exists():
        migrated = _migrate_todos_md(slug)
        if migrated:
            save_interrupts(path, migrated)
        return migrated
    return load_interrupts(path)


@app.get("/api/projects/{slug}/todos")
def get_todos(slug: str) -> list[dict[str, Any]]:
    return _load_todos(slug)


@app.post("/api/projects/{slug}/todos", status_code=201)
def post_todo(slug: str, body: InterruptCreate) -> dict[str, Any]:
    path = config.todos_file(slug)
    _load_todos(slug)  # ensure migration has run before appending
    return create_item(
        path,
        title=body.title,
        due_date=body.dueDate,
        priority=body.priority,
    )


@app.patch("/api/projects/{slug}/todos/{todo_id}")
def patch_todo(slug: str, todo_id: str, body: InterruptUpdate) -> dict[str, Any]:
    path = config.todos_file(slug)
    _load_todos(slug)
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        return update_interrupt(path, todo_id, **updates)
    except KeyError:
        raise HTTPException(404, f"Todo {todo_id!r} not found")


@app.delete("/api/projects/{slug}/todos/{todo_id}", status_code=204)
def delete_todo(slug: str, todo_id: str) -> Response:
    path = config.todos_file(slug)
    _load_todos(slug)
    delete_interrupt(path, todo_id)
    return Response(status_code=204)


@app.post("/api/projects/{slug}/todos/{todo_id}/activity")
def post_todo_activity(slug: str, todo_id: str, body: ActivityEntry) -> dict[str, Any]:
    path = config.todos_file(slug)
    _load_todos(slug)
    try:
        return append_activity(
            path, todo_id,
            entry_type=body.type, text=body.text, author=body.author,
        )
    except KeyError:
        raise HTTPException(404, f"Todo {todo_id!r} not found")


@app.patch("/api/projects/{slug}/todos/{todo_id}/activity/{index}")
def patch_todo_activity(slug: str, todo_id: str, index: int, body: ActivityEdit) -> dict[str, Any]:
    path = config.todos_file(slug)
    _load_todos(slug)
    try:
        return update_activity(path, todo_id, index, body.text)
    except KeyError:
        raise HTTPException(404, f"Todo {todo_id!r} not found")
    except IndexError:
        raise HTTPException(404, f"Activity index {index} not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/projects/{slug}/todos/{todo_id}/activity/{index}")
def del_todo_activity(slug: str, todo_id: str, index: int) -> dict[str, Any]:
    path = config.todos_file(slug)
    _load_todos(slug)
    try:
        return delete_activity(path, todo_id, index)
    except KeyError:
        raise HTTPException(404, f"Todo {todo_id!r} not found")
    except IndexError:
        raise HTTPException(404, f"Activity index {index} not found")


class MemoryWriteRequest(BaseModel):
    content: str

@app.put("/api/projects/{slug}/memory")
def write_memory(slug: str, body: MemoryWriteRequest) -> dict:
    """Overwrite projects/{slug}/MEMORY.md with new content."""
    memory_file = config.PROJECTS_DIR / slug / "MEMORY.md"
    if not memory_file.exists():
        raise HTTPException(404, "No MEMORY.md for this project")
    memory_file.write_text(body.content, encoding="utf-8")
    return {"ok": True}


# --- Notes ---

import re as _re
import datetime as _datetime

@app.get("/api/projects/{slug}/notes")
def project_notes(slug: str) -> dict:
    """Return parsed note entries from projects/{slug}/notes.md."""
    notes_file = config.PROJECTS_DIR / slug / "notes.md"
    if not notes_file.exists():
        return {"notes": []}
    content = notes_file.read_text(encoding="utf-8", errors="replace")
    notes = []
    blocks = _re.split(r'\n(?=## )', content)
    for i, block in enumerate(blocks):
        block = block.strip()
        if not block.startswith('## '):
            continue
        lines = block.split('\n')
        title = lines[0][3:].strip()
        captured = None
        for l in lines[1:]:
            if l.startswith('_Captured:'):
                captured = l[len('_Captured:'):].strip().strip('_').strip()
                break
        body_lines = [l for l in lines[1:] if not l.startswith('_Captured:')]
        note_content = '\n'.join(body_lines).strip()
        notes.append({"id": str(i), "title": title, "content": note_content, "captured": captured})
    return {"notes": notes}


class NoteAddRequest(BaseModel):
    title: str

@app.post("/api/projects/{slug}/notes", status_code=201)
def add_note(slug: str, body: NoteAddRequest) -> dict:
    """Append a new note to projects/{slug}/notes.md."""
    notes_file = config.PROJECTS_DIR / slug / "notes.md"
    now = _datetime.datetime.now(_datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    new_block = f"\n## {body.title.strip()}\n_Captured: {now}_\n\n"
    if not notes_file.exists():
        notes_file.write_text(f"# Notes\n{new_block}", encoding="utf-8")
    else:
        content = notes_file.read_text(encoding="utf-8", errors="replace")
        notes_file.write_text(content.rstrip() + new_block, encoding="utf-8")
    return {"ok": True}


class NoteRenameRequest(BaseModel):
    title: str

@app.patch("/api/projects/{slug}/notes/{index}")
def rename_note(slug: str, index: int, body: NoteRenameRequest) -> dict:
    """Rename a note heading by index."""
    notes_file = config.PROJECTS_DIR / slug / "notes.md"
    if not notes_file.exists():
        raise HTTPException(404, "No notes file")
    content = notes_file.read_text(encoding="utf-8", errors="replace")
    blocks = _re.split(r'\n(?=## )', content)
    header_blocks = [b for b in blocks if not b.strip().startswith('## ')]
    note_blocks = [b for b in blocks if b.strip().startswith('## ')]
    if index < 0 or index >= len(note_blocks):
        raise HTTPException(404, "Note index out of range")
    note_blocks[index] = _re.sub(
        r'^## .+$', f'## {body.title.strip()}', note_blocks[index], count=1, flags=_re.MULTILINE
    )
    notes_file.write_text('\n'.join(header_blocks + note_blocks), encoding="utf-8")
    return {"ok": True}


@app.delete("/api/projects/{slug}/notes/{index}", status_code=204)
def delete_note(slug: str, index: int) -> Response:
    """Remove a note by index from projects/{slug}/notes.md."""
    notes_file = config.PROJECTS_DIR / slug / "notes.md"
    if not notes_file.exists():
        raise HTTPException(404, "No notes file")
    content = notes_file.read_text(encoding="utf-8", errors="replace")
    blocks = _re.split(r'\n(?=## )', content)
    header_blocks = [b for b in blocks if not b.strip().startswith('## ')]
    note_blocks = [b for b in blocks if b.strip().startswith('## ')]
    if index < 0 or index >= len(note_blocks):
        raise HTTPException(404, "Note index out of range")
    note_blocks.pop(index)
    notes_file.write_text('\n'.join(header_blocks + note_blocks), encoding="utf-8")
    return Response(status_code=204)


# --- Static (must be last) ---

app.mount(
    "/",
    StaticFiles(directory=str(config.TOWER_DIR / "static"), html=True),
    name="static",
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tower.server:app", host="0.0.0.0", port=config.PORT, reload=True)
