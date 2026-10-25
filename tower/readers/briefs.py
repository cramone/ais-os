"""ado-flow briefs, projected read-only from each repo onto the Control Tower.

The briefs live in the code repo (`docs/briefs/` on `origin/<base>`), not in AIS-OS.
Same rule as `cycle.py`: **one writer, one reader, no sync state.** ado-flow writes the
briefs and the board; Tower reads both and derives every status on read. Nothing is
stored here except a disposable mirror and an in-memory cache, and nothing is written
back — a status changes by running the ado-flow skill the row suggests.

Where the state comes from

  brief files   a depth-1 **sparse** clone per repo in `tower/data/repos/<slug>/`, holding
                only `.claude/` and the briefs path. One batched fetch per refresh, then
                plain file reads. Tower runs on Cortex and can't see the developer's
                clones, so it reads the remote. Delete the folder and it is rebuilt.
  board         ADO REST (`AZURE_DEVOPS_PAT` from `.env`): the repo's Epics and Features,
                matched by `plan-id:` tags (ado-flow conventions § 1, § 6).
  brief PRs     `gh pr list`, heads `brief/<user>/<ID>-…` (conventions § 12).

The repo's own committed `.claude/ado.json` supplies project, area, prefix, base and
briefs path, so a project opts in with two lines in its `MEMORY.md`:

    **Repo**: Sprbrk-Standard/mgq-magiq-media
    **Brief source**: repo

The mirror fetches over HTTPS with `gh` as git's credential helper — the same login the
PR reader uses — because the Cortex image has git and gh but no SSH client. Optional:
`**Repo remote**: <url>` to fetch from elsewhere (an SSH URL needs `openssh-client` in
the image), and
`**Repo base**: develop` when the default branch carries no `.claude/ado.json`.

What is deliberately NOT computed here: request satisfaction (deps.md) and evidence
staleness (conventions § 13). Rows show the cheap facets — revision, pushed revision,
Phase progress, waits — and link to `/ado-flow:brief status` / `deps` for the rest.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from tower import config

TTL_SECONDS = 300
REPOS_DIR = config.TOWER_DIR / "data" / "repos"
_GIT_TIMEOUT = 120

_FOLDER_RE = re.compile(r"^([A-Z]{2,5}-\d+)-[a-z0-9][a-z0-9-]*$")
_REV_FILE_RE = re.compile(r"^(review|plan)-r(\d+)\.md$")
_PHASE_RE = re.compile(r"^## Phase (\d+) [—–-] (.+?)\s*$", re.MULTILINE)
_ITEM_RE = re.compile(r"^- \[ \] ([RT]\d+) [—–-] ", re.MULTILINE)
_QUESTION_RE = re.compile(r"^- \*\*Q\d+", re.MULTILINE)
_MARKER_RE = re.compile(r"\((satisfies|blocked:[^)]*)\)")

_locks: dict[str, threading.Lock] = {}
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


# --- project registry ---------------------------------------------------------


@dataclass(frozen=True)
class BriefProject:
    slug: str
    repo: str                 # <owner>/<name>
    remote: str               # git URL the container can fetch
    base: str | None          # optional; else the default branch's ado.json decides

    @property
    def mirror(self) -> Path:
        return REPOS_DIR / self.slug


def brief_project(slug: str) -> BriefProject | None:
    """The project's brief source, or None when it doesn't read briefs from a repo."""
    memory = config.PROJECTS_DIR / slug / "MEMORY.md"
    if not memory.exists():
        return None
    text = memory.read_text(encoding="utf-8", errors="replace")
    source = (_field(text, "Brief source") or "").split()
    if not source or source[0].lower() != "repo":      # first word; the rest is a note
        return None
    repo = _field(text, "Repo")
    if not repo or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return None
    remote = _field(text, "Repo remote") or f"https://github.com/{repo}.git"
    return BriefProject(slug=slug, repo=repo, remote=remote, base=_field(text, "Repo base"))


def _field(text: str, name: str) -> str | None:
    m = re.search(rf"\*\*{re.escape(name)}\*\*:\s*(.+)", text)
    return m.group(1).strip().strip("`") if m else None


# --- front-matter and brief files (pure; unit-tested) ---------------------------


def front_matter(text: str) -> dict[str, str]:
    """Flat key -> raw value map of the leading `---` block. ado-flow's front-matter
    isn't strict YAML (`superseded-by: -`), so it is read line by line."""
    if not text.startswith("---"):
        return {}
    out: dict[str, str] = {}
    for line in text.split("\n")[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([a-z][a-z-]*):\s*(.*?)\s*(?:#.*)?$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def list_field(raw: str | None) -> list[str]:
    raw = (raw or "").strip()
    if raw in ("", "-", "[]"):
        return []
    return [p.strip() for p in raw.strip("[]").split(",") if p.strip()]


def latest_revision(files: list[str]) -> int:
    """Highest r with both review-rN.md and plan-rN.md (format.md § Layout). 0 = none."""
    seen: dict[int, set[str]] = {}
    for name in files:
        m = _REV_FILE_RE.match(name)
        if m:
            seen.setdefault(int(m.group(2)), set()).add(m.group(1))
    full = [r for r, kinds in seen.items() if kinds == {"review", "plan"}]
    return max(full, default=0)


def section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


def plan_phases(plan_text: str) -> list[dict[str, Any]]:
    """Phases of a plan: number, name (markers stripped), markers, item ids."""
    phases = []
    matches = list(_PHASE_RE.finditer(plan_text))
    for i, m in enumerate(matches):
        body = plan_text[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(plan_text)]
        heading = m.group(2)
        markers = _MARKER_RE.findall(heading)
        phases.append({
            "n": int(m.group(1)),
            "name": _MARKER_RE.sub("", heading).strip(),
            "satisfies": "satisfies" in markers,
            "blocked": [b.split(":", 1)[1].strip() for b in markers if b.startswith("blocked:")],
            "items": _ITEM_RE.findall(body),
        })
    return phases


@dataclass
class Brief:
    id: str
    folder: str
    title: str
    kind: str
    status: str
    superseded_by: str | None
    depends_on: list[str]
    origin: str
    revision: int
    imported: bool
    open_questions: int
    phases: list[dict[str, Any]]
    external_requests: list[str]
    files: list[str]
    board: dict[str, Any] = field(default_factory=dict)
    prs: list[dict[str, Any]] = field(default_factory=list)
    chip: str = ""
    next: str = ""


def parse_brief(folder: str, files: dict[str, str]) -> Brief | None:
    """One brief from its folder name and {filename: text}. None when not a brief."""
    m = _FOLDER_RE.match(folder)
    if not m or "brief.md" not in files:
        return None
    fm = front_matter(files["brief.md"])
    n = latest_revision(list(files))
    review = files.get(f"review-r{n}.md", "")
    plan = files.get(f"plan-r{n}.md", "")
    rfm = front_matter(review)
    superseded_by = fm.get("superseded-by")
    return Brief(
        id=fm.get("id") or m.group(1),
        folder=folder,
        title=fm.get("title", folder),
        kind=fm.get("kind", ""),
        status=fm.get("status", "active"),
        superseded_by=None if superseded_by in (None, "", "-") else superseded_by,
        depends_on=list_field(fm.get("depends-on")),
        origin=fm.get("origin", "-"),
        revision=n,
        imported=rfm.get("imported", "-") not in ("", "-"),
        open_questions=len(_QUESTION_RE.findall(section(review, "Open questions"))),
        phases=plan_phases(plan),
        external_requests=re.findall(r"^### (X\d+) ", section(review, "External requests"), re.MULTILINE),
        files=sorted(files),
    )


# --- repo mirror ----------------------------------------------------------------


# HTTPS auth through gh (`gh auth git-credential`), scoped to these calls only: the
# container's global git config is left alone.
_GIT_AUTH = ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]


def _git(cwd: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *_GIT_AUTH, *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=_GIT_TIMEOUT)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def _sync_mirror(p: BriefProject) -> tuple[dict[str, Any], str]:
    """Bring the sparse mirror to origin/<base>. Returns (ado.json, base sha)."""
    d = p.mirror
    if not (d / ".git").exists():
        if d.exists():
            shutil.rmtree(d)
        d.parent.mkdir(parents=True, exist_ok=True)
        branch = ["--branch", p.base] if p.base else []
        _git(d.parent, "clone", "--depth", "1", "--filter=blob:none", "--no-checkout", "--quiet", *branch, p.remote, d.name)
        _git(d, "sparse-checkout", "set", "--no-cone", "/.claude/ado.json")
        _git(d, "checkout", "--quiet")
    # The base comes from the repo's own config; read it from whatever is checked out,
    # then follow it. First run: default branch; afterwards: the recorded base.
    cfg_file = d / ".claude" / "ado.json"
    if not cfg_file.exists():
        raise RuntimeError(f"no .claude/ado.json on {p.base or 'the default branch'} — set **Repo base** in MEMORY.md")
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    base = cfg.get("git", {}).get("baseBranch") or "main"
    briefs_path = cfg.get("briefs", {}).get("path") or "docs/briefs"
    _git(d, "sparse-checkout", "set", "--no-cone", "/.claude/ado.json", f"/{briefs_path.strip('/')}/")
    _git(d, "fetch", "--depth", "1", "--quiet", "origin", f"+refs/heads/{base}:refs/remotes/origin/{base}")
    _git(d, "checkout", "--quiet", "--force", "-B", base, f"origin/{base}")
    cfg = json.loads((d / ".claude" / "ado.json").read_text(encoding="utf-8"))
    return cfg, _git(d, "rev-parse", "HEAD").strip()


def _read_briefs(p: BriefProject, cfg: dict[str, Any]) -> list[Brief]:
    root = p.mirror / (cfg.get("briefs", {}).get("path") or "docs/briefs")
    out = []
    if not root.exists():
        return out
    for folder in sorted(x for x in root.iterdir() if x.is_dir()):
        files = {f.name: f.read_text(encoding="utf-8", errors="replace")
                 for f in folder.iterdir() if f.is_file() and f.suffix == ".md"}
        b = parse_brief(folder.name, files)
        if b:
            out.append(b)
    return out


# --- board ------------------------------------------------------------------------


def _env(name: str) -> str | None:
    v = os.environ.get(name)
    if v:
        return v
    env_file = config.AIOS_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip('"')
    return None


def _ado(org: str, path: str, body: dict[str, Any] | None = None) -> Any:
    pat = _env("AZURE_DEVOPS_PAT")
    if not pat:
        raise RuntimeError("AZURE_DEVOPS_PAT not set")
    token = base64.b64encode(f":{pat}".encode()).decode()
    req = urllib.request.Request(
        f"https://dev.azure.com/{org}/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _names(v: Any) -> set[str]:
    if v is None:
        return set()
    return {v} if isinstance(v, str) else set(v)


def read_board(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per plan id: Epic and Phase facets from the board. Lookups by plan id are
    project-wide (conventions § 2 exception), with the area checked client-side."""
    ado = cfg.get("ado", {})
    org = ado.get("organization") or _env("AZURE_DEVOPS_ORG")
    project = ado["project"]
    prefix = cfg["planId"]["prefix"]
    area = ado.get("areaPath") or project
    proc = cfg.get("process", {})
    types = proc.get("workItemTypes", {})
    states = proc.get("states", {})
    epic_t, feat_t = types.get("epic", "Epic"), types.get("feature", "Feature")
    feat_done = _names(states.get("feature", {}).get("resolved")) | _names(states.get("feature", {}).get("closed"))
    feat_removed = _names(states.get("feature", {}).get("removed"))

    ids: list[int] = []
    last = 0
    while True:   # page by id (conventions § 2, paging)
        wiql = (f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{project}' "
                f"AND [System.WorkItemType] IN ('{epic_t}', '{feat_t}') AND [System.Id] > {last} "
                f"ORDER BY [System.Id]")
        res = _ado(org, f"{project}/_apis/wit/wiql?$top=20000&api-version=7.1", {"query": wiql})
        page = [w["id"] for w in res.get("workItems", [])]
        ids += page
        if len(page) < 20000:
            break
        last = page[-1]

    fields = ["System.Id", "System.WorkItemType", "System.Title", "System.State", "System.Tags", "System.AreaPath"]
    rows: list[dict[str, Any]] = []
    for i in range(0, len(ids), 200):
        res = _ado(org, "_apis/wit/workitemsbatch?api-version=7.1", {"ids": ids[i:i + 200], "fields": fields})
        rows += [w["fields"] for w in res.get("value", []) if w]

    out: dict[str, dict[str, Any]] = {}
    tag_re = re.compile(rf"^plan-id:({re.escape(prefix)}-\d+)$", re.IGNORECASE)
    for f in rows:
        tags = [t.strip() for t in (f.get("System.Tags") or "").split(";") if t.strip()]
        plan_id = next((tag_re.match(t).group(1).upper() for t in tags if tag_re.match(t)), None)
        if not plan_id:
            continue
        b = out.setdefault(plan_id, {"epic": None, "pushedRev": None, "withdrawn": False, "phases": {},
                                      "outOfArea": []})
        item_area = f.get("System.AreaPath") or ""
        if not (item_area == area or item_area.startswith(area + "\\")):
            b["outOfArea"].append({"id": f["System.Id"], "area": item_area})
        if f["System.WorkItemType"] == epic_t:
            b["epic"] = {"id": f["System.Id"], "state": f["System.State"]}
            revs = [int(t.split(":", 1)[1]) for t in tags if re.fullmatch(r"brief-rev:\d+", t)]
            b["pushedRev"] = max(revs) if revs else None
            b["withdrawn"] = "withdrawn" in tags
        else:
            m = re.search(r"Phase (\d+)", f.get("System.Title") or "", re.IGNORECASE)
            if not m:
                continue
            state = f["System.State"]
            excluded = state in feat_removed or "cancelled" in tags
            b["phases"][int(m.group(1))] = {
                "id": f["System.Id"], "state": state,
                "done": state in feat_done and not excluded, "excluded": excluded,
                "inReview": "in-review" in tags or "pr-draft" in tags,
                "blocked": "blocked" in tags,
                "waits": [t.split(":", 1)[1] for t in tags if t.startswith("xreq-wait:")],
            }
    return out


# --- brief PRs ----------------------------------------------------------------------


def read_brief_prs(repo: str) -> dict[str, list[dict[str, Any]]]:
    r = subprocess.run(["gh", "pr", "list", "--repo", repo, "--state", "open", "--limit", "200",
                        "--json", "number,title,url,headRefName,author"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "gh pr list failed")
    out: dict[str, list[dict[str, Any]]] = {}
    for pr in json.loads(r.stdout or "[]"):
        head = pr.get("headRefName", "")
        if not head.startswith("brief/"):
            continue
        m = re.match(r"([A-Za-z]{2,5}-\d+)-", head.rsplit("/", 1)[-1])
        if m:
            out.setdefault(m.group(1).upper(), []).append({
                "number": pr["number"], "title": pr["title"], "url": pr["url"],
                "needsAnswers": pr["title"].startswith("[needs-answers]"),
                "author": (pr.get("author") or {}).get("login"),
            })
    return out


# --- derivation (pure; unit-tested) ------------------------------------------------------


def derive(b: Brief) -> None:
    """Set the status chip and the next command. First match wins; mirrors what
    `/ado-flow:brief status` shows for the same facets."""
    board, prs = b.board, b.prs
    phases = board.get("phases", {}) if board else {}
    live = [p for p in phases.values() if not p["excluded"]]
    done = sum(1 for p in live if p["done"])
    waits = sorted({k for p in live if not p["done"] for k in p["waits"]})
    pushed = board.get("pushedRev") if board else None

    if b.status in ("done", "withdrawn"):
        b.chip, b.next = b.status, ""
    elif b.status == "superseded":
        b.chip, b.next = f"superseded → {b.superseded_by or '?'}", ""
    elif board and board.get("outOfArea"):
        b.chip = "moved out of area"
        b.next = "move #" + ", #".join(str(x["id"]) for x in board["outOfArea"]) + " back"
    elif any(pr["needsAnswers"] for pr in prs) or b.open_questions:
        b.chip, b.next = "needs answers", f"/ado-flow:brief review {b.id}"
    elif prs:
        b.chip, b.next = "brief PR open", "merge PR #" + ", #".join(str(pr["number"]) for pr in prs)
    elif b.revision == 0:
        b.chip, b.next = "no plan yet", f"/ado-flow:brief plan {b.id}"
    elif pushed is None and b.imported:
        b.chip, b.next = "imported — refresh", f"/ado-flow:brief refresh {b.id}"
    elif pushed is None:
        b.chip, b.next = "not pushed", f"/ado-flow:push-plan {b.id}"
    elif pushed < b.revision:
        b.chip, b.next = f"behind r{pushed} → r{b.revision}", f"/ado-flow:push-plan {b.id}"
    elif live and done == len(live):
        b.chip, b.next = "ready to close", f"/ado-flow:wrapup {board['epic']['id']}" if board.get("epic") else f"/ado-flow:brief close {b.id}"
    elif waits:
        b.chip, b.next = "waiting on " + ", ".join(k.rsplit("/", 1)[-1] for k in waits), f"/ado-flow:brief deps {b.id}"
    elif done:
        b.chip, b.next = f"in progress {done}/{len(live)}", f"/ado-flow:pickup {b.id}"
    else:
        b.chip, b.next = "on board", f"/ado-flow:pickup {b.id}"


# --- entry points -------------------------------------------------------------------------


def read_project_briefs(slug: str, force: bool = False) -> dict[str, Any]:
    """All briefs of a project with board and PR facets.

    Stale-while-revalidate: within TTL_SECONDS the cached result is returned; past it,
    the stale result is returned at once and a background refresh is started, so a page
    load never waits on git or ADO. Only the very first read (no cache) and `force`
    block. Each result carries `fetchedAt` so the UI can say how old it is.
    """
    p = brief_project(slug)
    if p is None:
        return {"enabled": False, "briefs": []}
    hit = _cache.get(slug)
    if hit and not force:
        if time.monotonic() - hit[0] >= TTL_SECONDS:
            _refresh_async(p)
        return hit[1]
    return _refresh(p)


def _refresh(p: BriefProject) -> dict[str, Any]:
    with _locks.setdefault(p.slug, threading.Lock()):
        result = _build(p)
        _cache[p.slug] = (time.monotonic(), result)
        return result


def _refresh_async(p: BriefProject) -> None:
    lock = _locks.setdefault(p.slug, threading.Lock())
    if lock.locked():
        return            # a refresh is already running
    threading.Thread(target=_refresh, args=(p,), daemon=True).start()


def _build(p: BriefProject) -> dict[str, Any]:
    errors: dict[str, str] = {}
    try:
        cfg, sha = _sync_mirror(p)
    except Exception as e:   # no mirror means no briefs; say why
        return {"enabled": True, "repo": p.repo, "briefs": [], "errors": {"repo": str(e)}}
    briefs = _read_briefs(p, cfg)
    try:
        board = read_board(cfg)
    except Exception as e:
        board, errors["board"] = {}, str(e)
    try:
        prs = read_brief_prs(p.repo)
    except Exception as e:
        prs, errors["prs"] = {}, str(e)
    for b in briefs:
        b.board = board.get(b.id, {})
        b.prs = prs.get(b.id, [])
        derive(b)
    rows = [asdict(b) for b in briefs]
    for r in rows:   # JSON keys must be strings
        r["board"]["phases"] = {str(k): v for k, v in (r["board"].get("phases") or {}).items()}
    return {
        "enabled": True, "repo": p.repo, "base": cfg.get("git", {}).get("baseBranch"),
        "sha": sha, "prefix": cfg.get("planId", {}).get("prefix"),
        "schemaVersion": cfg.get("schemaVersion"), "fetchedAt": time.time(),
        "briefs": rows, "errors": errors,
    }


def read_brief_file(slug: str, brief_id: str, name: str) -> dict[str, Any]:
    """One file of one brief, from the mirror as last synced."""
    p = brief_project(slug)
    if p is None:
        raise FileNotFoundError("project doesn't read briefs from a repo")
    data = read_project_briefs(slug)
    row = next((b for b in data["briefs"] if b["id"] == brief_id.upper()), None)
    if row is None or name not in row["files"]:
        raise FileNotFoundError(f"{brief_id}/{name}")
    cfg = json.loads((p.mirror / ".claude" / "ado.json").read_text(encoding="utf-8"))
    path = p.mirror / (cfg.get("briefs", {}).get("path") or "docs/briefs") / row["folder"] / name
    return {"id": row["id"], "name": name, "content": path.read_text(encoding="utf-8", errors="replace")}
