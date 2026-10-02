#!/usr/bin/env python3
"""Live dashboard server for repo-house-keeping.

Run:   python scripts/serve_dashboard.py          (or double-click start-dashboard.bat)
Opens: http://localhost:8765

- Serves the dashboard with data read fresh from spec/*.csv, risks.md, decisions/log.md.
- Edits made in the browser are written straight to spec/repo-register.csv, spec/tasks.csv and spec/notes/<source>.md.
- Every write: validates values, checks the row wasn't changed on disk meanwhile (conflict -> rejected),
  copies the old file to spec/.backups/, then replaces the file atomically.
- Rows are never deleted and ids never change. Only an allow-list of fields is editable.
- Binds to 127.0.0.1 only. Standard library only, no pip installs.
"""
import csv, io, json, os, shutil, sys, threading, time, webbrowser, urllib.request, argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_dashboard as bd  # noqa: E402

ROOT, SPEC = bd.ROOT, bd.SPEC
BACKUPS = SPEC / ".backups"
REG, TASKS = SPEC / "repo-register.csv", SPEC / "tasks.csv"

ENUMS = {
    "disposition": {"pending", "update-then-migrate", "archive-in-place", "migrate", "decommission", "tbd"},
    "classification": {"active", "stable", "stale", "deprecated", "unknown"},
    "migration_status": {"not-started", "in-progress", "migrated", "verified", "decommissioned", "skipped"},
    "backup_2loc": {"", "yes", "no", "not-required"},
    "status": {"todo", "doing", "blocked", "done"},          # tasks
    "priority": {"urgent", "high", "medium", "low"},         # tasks
}
REG_EDITABLE = {"disposition", "classification", "migration_status", "owner", "notes", "backup_2loc", "destination_url",
                "confirmed_by", "confirmed_date"}
TASK_EDITABLE = {"title", "owner", "phase", "status", "priority", "due", "linked", "notes"}
LOCK = threading.Lock()
PORT_BASE = 8765


class ApiError(Exception):
    def __init__(self, status, payload):
        self.status, self.payload = status, payload


# ---------------------------------------------------------------- csv io
def load_table(path):
    raw = Path(path).read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    eol = "\r\n" if b"\r\n" in raw else "\n"
    rdr = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    rows = [r for r in rdr]
    return list(rdr.fieldnames), rows, bom, eol


def write_table(path, cols, rows, bom, eol):
    path = Path(path)
    BACKUPS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(path, BACKUPS / f"{path.stem}.{stamp}{path.suffix}")
    old = sorted(BACKUPS.glob(f"{path.stem}.*{path.suffix}"))
    for f in old[:-60]:                       # keep the newest 60 backups per file
        try:
            f.unlink()
        except OSError:
            pass
    out = io.StringIO(newline="")
    w = csv.DictWriter(out, cols, lineterminator=eol)
    w.writeheader()
    w.writerows(rows)
    data = (b"\xef\xbb\xbf" if bom else b"") + out.getvalue().encode("utf-8")
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    try:
        os.replace(tmp, path)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise ApiError(423, {"error": f"{path.name} is locked (open in Excel?). Close it and retry."})


def log_change(kind, payload, assigned=None):
    BACKUPS.mkdir(exist_ok=True)
    with open(BACKUPS / "change-log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "file": kind,
                            "edits": payload.get("edits", []), "adds": payload.get("adds", []),
                            "assigned": assigned or {}}, ensure_ascii=False) + "\n")


def norm(field, val):
    val = "" if val is None else str(val).strip() if field != "notes" else str(val)
    if val == "hold" and field == "disposition":
        val = "pending"
    if field == "confirmed_date" and val:
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except ValueError:
            raise ApiError(400, {"error": f"Invalid date (use YYYY-MM-DD): {val!r}"})
    if field in ENUMS and val not in ENUMS[field]:
        raise ApiError(400, {"error": f"Invalid {field}: {val!r}"})
    return val


# ---------------------------------------------------------------- mutations
def apply(path, kind, editable, payload, id_field, new_id, required):
    cols, rows, bom, eol = load_table(path)
    byid = {r[id_field]: r for r in rows}
    conflicts, plan = [], []
    for e in payload.get("edits", []):
        rid = str(e.get("id"))
        row = byid.get(rid)
        if row is None:
            conflicts.append({"id": rid, "field": "*", "current": None})
            continue
        for f, ch in (e.get("fields") or {}).items():
            if f not in editable:
                raise ApiError(400, {"error": f"Field not editable: {f}"})
            new = norm(f, ch.get("new"))
            cur = row.get(f, "")
            if f == "disposition":
                cur = norm(f, cur) if cur else cur
            if cur != norm(f, ch.get("old")):
                conflicts.append({"id": rid, "field": f, "current": cur, "yours_was": ch.get("old"), "new": new})
            else:
                plan.append((row, f, new))
    if conflicts:
        raise ApiError(409, {"error": "conflict", "conflicts": conflicts})
    for row, f, new in plan:
        row[f] = new
    assigned = {}
    existing = {r.get("source_url", "").lower() for r in rows} if kind == "register" else set()
    for a in payload.get("adds", []):
        if any(not str(a.get(k, "")).strip() for k in required):
            raise ApiError(400, {"error": f"New row missing one of {required}"})
        if kind == "register" and a["source_url"].lower() in existing:
            continue                                   # already merged - idempotent
        row = {c: "" for c in cols}
        for c in cols:
            if c in a and c != id_field:
                row[c] = norm(c, a[c]) if c in ENUMS else ("" if a[c] is None else str(a[c]))
        row[id_field] = new_id(rows)
        rows.append(row)
        assigned[a.get("source_url") or a.get("title", "")] = row[id_field]
        existing.add(row.get("source_url", "").lower())
    if plan or assigned:
        write_table(path, cols, rows, bom, eol)
        log_change(kind, payload, assigned)
    return {"ok": True, "assigned": assigned}


def save_note(payload):
    src = payload.get("source")
    if src not in bd.NOTE_SOURCES:
        raise ApiError(400, {"error": f"Unknown source: {src!r}"})
    path = SPEC / "notes" / f"{src}.md"
    cur = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else ""
    if cur != (payload.get("old") or "").replace("\r\n", "\n"):
        raise ApiError(409, {"error": "conflict", "current": cur})
    new = (payload.get("new") or "").replace("\r\n", "\n")
    if new == cur:
        return {"ok": True}
    path.parent.mkdir(exist_ok=True)
    BACKUPS.mkdir(exist_ok=True)
    if path.exists():
        shutil.copy2(path, BACKUPS / f"notes-{src}.{datetime.now():%Y%m%d-%H%M%S-%f}.md")
        old = sorted(BACKUPS.glob(f"notes-{src}.*.md"))
        for f in old[:-60]:
            f.unlink(missing_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(new.encode("utf-8"))
    try:
        os.replace(tmp, path)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise ApiError(423, {"error": f"{path.name} is locked by another program."})
    return {"ok": True}


def next_reg_id(rows):
    return str(max([int(r["id"]) for r in rows if str(r["id"]).isdigit()] + [0]) + 1)


def next_task_id(rows):
    n = max([int(r["id"].split("-")[-1]) for r in rows if r["id"].split("-")[-1].isdigit()] + [0]) + 1
    return f"T-{n:02d}"


# ---------------------------------------------------------------- http
def page_data():
    d = bd.collect()
    d["live"] = True
    d["rev"] = bd.rev()
    return d


class H(BaseHTTPRequestHandler):
    server_version = "rhk-dashboard"

    def log_message(self, fmt, *a):          # quiet: only log writes + errors
        if self.command == "POST" or (a and str(a[1]).startswith(("4", "5"))):
            print(f"[{datetime.now():%H:%M:%S}] {self.command} {self.path} -> {a[1] if len(a) > 1 else ''}")

    def _send(self, status, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("localhost", "127.0.0.1")

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, '{"error":"bad host"}')
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html", "/dashboard.html"):
                return self._send(200, bd.render_html(page_data()), "text/html; charset=utf-8")
            if path == "/api/data":
                return self._send(200, json.dumps(page_data(), ensure_ascii=False))
            if path == "/api/rev":
                return self._send(200, json.dumps({"rev": bd.rev()}))
            if path == "/api/ping":
                return self._send(200, "rhk-dashboard", "text/plain")
        except Exception as ex:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(ex)}))
        self._send(404, '{"error":"not found"}')

    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-RHK") != "1":
            return self._send(403, '{"error":"forbidden"}')
        origin = self.headers.get("Origin")
        if origin and (origin.split("//")[-1].split(":")[0] not in ("localhost", "127.0.0.1")):
            return self._send(403, '{"error":"forbidden origin"}')
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
            with LOCK:
                if self.path == "/api/register":
                    res = apply(REG, "register", REG_EDITABLE, payload, "id", next_reg_id, ["name", "source", "source_url"])
                elif self.path == "/api/tasks":
                    res = apply(TASKS, "tasks", TASK_EDITABLE, payload, "id", next_task_id, ["title", "owner"])
                elif self.path == "/api/notes":
                    res = save_note(payload)
                else:
                    raise ApiError(404, {"error": "not found"})
            self._send(200, json.dumps(res))
        except ApiError as e:
            self._send(e.status, json.dumps(e.payload))
        except Exception as ex:  # noqa: BLE001
            self._send(500, json.dumps({"error": str(ex)}))


def already_running(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
            return r.read().decode() == "rhk-dashboard"
    except Exception:  # noqa: BLE001
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT_BASE)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    if not REG.exists():
        print(f"ERROR: {REG} not found"); return 1
    for port in range(a.port, a.port + 10):
        if already_running(port):
            print(f"Dashboard already running on port {port} - opening it.")
            if not a.no_browser:
                webbrowser.open(f"http://localhost:{port}")
            return 0
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), H)
            break
        except OSError:
            continue
    else:
        print("No free port found (8765-8774)."); return 1
    url = f"http://localhost:{port}"
    print("=" * 60)
    print(" Repo House Keeping - live dashboard")
    print(f" {url}")
    print(f" Writing to: {SPEC}")
    print(f" Backups:    {BACKUPS}")
    print(" Keep this window open. Close it (or Ctrl+C) to stop.")
    print("=" * 60)
    if not a.no_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
