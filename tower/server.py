import threading
import webbrowser
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tower import config
from tower.interrupts.ado_push import push_to_ado
from tower.interrupts.email import generate_email_draft
from tower.interrupts.store import (
    append_activity,
    create_interrupt,
    delete_interrupt,
    load_interrupts,
    update_interrupt,
)
from tower.readers.ado import read_ado_sprint
from tower.readers.decisions import read_decisions
from tower.readers.hermes import (
    read_adhoc_notes,
    read_ado_pending,
    read_hermes_project_captures,
)
from tower.readers.projects import read_projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    def _open():
        import time
        time.sleep(1)
        webbrowser.open(f"http://localhost:{config.PORT}")
    threading.Thread(target=_open, daemon=True).start()
    yield


app = FastAPI(title="AIS-OS Control Tower", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return create_interrupt(
        config.INTERRUPTS_FILE,
        title=body.title,
        source=body.source,
        due_date=body.dueDate,
        priority=body.priority,
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

app.mount(
    "/",
    StaticFiles(directory=str(config.TOWER_DIR / "static"), html=True),
    name="static",
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tower.server:app", host="0.0.0.0", port=config.PORT, reload=True)
