"""Archive-folder helpers shared by build_dashboard.py and serve_dashboard.py.

Layout (see archive/README.md):  archive/<source>/<project>/<repo>/ARCHIVE.md  (+ the zip / mirror the user copies in)
Folder names are always derived from the register row, never from client input.
"""
import hashlib, json, re, shutil, os
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "archive"
README = ARCHIVE / "README.md"
META = ".rhk-archive.json"
S_START, S_END = "<!-- rhk:status:start -->", "<!-- rhk:status:end -->"
I_START, I_END = "<!-- rhk:index:start -->", "<!-- rhk:index:end -->"
ELIGIBLE = {"archive-in-place", "decommission"}
SKIP_FILES = {"ARCHIVE.md", META}


def safe(name):
    n = re.sub(r"^\$/", "", name or "")
    n = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", n)
    n = re.sub(r"\s+", "-", n.strip()).strip(". -")
    return n or "repo"


def project_of(row):
    m = re.search(r"project=([^;]+)", row.get("notes", "") or "")
    return (m.group(1).strip() if m else row.get("name", ""))


def legacy_folder_for(row, rows):
    """Folder name used by the previous flat layout archive/<source>/<repo>/ (kept only for migration)."""
    base = safe(row["name"])
    dup = [r for r in rows if r["source"] == row["source"] and safe(r["name"]).lower() == base.lower()]
    return f"{base}--{safe(project_of(row))}" if len(dup) > 1 else base


def folder_for(row, rows):
    """Repo folder name inside its project folder: <repo> (or <repo>--<id> if the same source+project has two with one name)."""
    base = safe(row["name"])
    dup = [r for r in rows if r["source"] == row["source"] and safe(project_of(r)).lower() == safe(project_of(row)).lower()
           and safe(r["name"]).lower() == base.lower()]
    return f"{base}--{row['id']}" if len(dup) > 1 else base


def path_for(row, rows):
    """archive/<source>/<project>/<repo>/"""
    return ARCHIVE / safe(row["source"]) / safe(project_of(row)) / folder_for(row, rows)


def migrate_layout(rows):
    """One-off, idempotent: move archive/<source>/<repo>/ -> archive/<source>/<project>/<repo>/. Returns list of (old, new)."""
    moves = []
    for r in rows:
        old = ARCHIVE / safe(r["source"]) / legacy_folder_for(r, rows)
        new = path_for(r, rows)
        if old == new or not old.is_dir() or new.exists():
            continue
        if not ((old / "ARCHIVE.md").exists() or (old / META).exists()):
            continue                      # a project folder (new layout), not an old repo folder
        tmp = old.with_name(old.name + ".__rhk_mv")
        os.rename(old, tmp)               # temp name first: old folder may share its name with the new project folder
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp), str(new))
        moves.append((str(old.relative_to(ROOT)).replace("\\", "/"), str(new.relative_to(ROOT)).replace("\\", "/")))
    return moves


def _meta(p):
    try:
        return json.loads((p / META).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _files(p):
    meta = _meta(p).get("files", {})
    out = []
    for f in sorted(p.iterdir(), key=lambda x: x.name.lower()):
        if f.name in SKIP_FILES or f.name.startswith("."):
            continue
        if f.is_file():
            st = f.stat()
            m = meta.get(f.name, {})
            sha = m.get("sha256") if m.get("size") == st.st_size else None
            out.append({"name": f.name, "size": st.st_size, "sha256": sha or ""})
        else:
            out.append({"name": f.name + "/", "size": sum(x.stat().st_size for x in f.rglob("*") if x.is_file()), "sha256": ""})
    return out


def scan(rows):
    """{register id: {rel, abs, exists, has_md, files[]}} for every register row."""
    res = {}
    for r in rows:
        p = path_for(r, rows)
        e = p.is_dir()
        res[r["id"]] = {"rel": str(p.relative_to(ROOT)).replace("\\", "/"), "abs": str(p), "exists": e,
                        "has_md": (p / "ARCHIVE.md").exists() if e else False, "files": _files(p) if e else []}
    return res


def fingerprint(rows):
    """Cheap change token for archive dirs (names, sizes, mtimes)."""
    parts = []
    if ARCHIVE.exists():
        for p in sorted(ARCHIVE.glob("*/*/*")):
            try:
                parts.append(f"{p.name}:{p.stat().st_mtime_ns}")
                for c in p.iterdir():
                    parts.append(f"{c.name}:{c.stat().st_size}:{c.stat().st_mtime_ns}")
            except OSError:
                pass
    return "|".join(parts)


def _backup_label(v):
    return {"yes": "yes — 2 locations confirmed", "no": "no — not done", "not-required": "not required (empty/obsolete)"}.get(v or "", "not recorded")


def status_block(row, files):
    conf = (f"{row.get('confirmed_by') or 'Chase Ramone'}, {row['confirmed_date']}" if row.get("confirmed_date") else "not confirmed")
    ft = "\n".join(f"| `{f['name']}` | {f['size']:,} bytes | {f['sha256'] or '_not recorded (use Rescan in the dashboard)_'} |" for f in files) \
        or "| _no files yet — copy the archive zip into this folder_ | | |"
    return "\n".join([
        S_START,
        "_Managed by the dashboard. Anything between these markers is overwritten; write your notes elsewhere in this file._",
        "",
        "| | |", "|---|---|",
        f"| Register id | {row['id']} |",
        f"| Source repo | {row.get('source_url', '')} |",
        f"| Disposition | {row.get('disposition', '')} |",
        f"| Migration status | {row.get('migration_status', '')} |",
        f"| 2-location backup | {_backup_label(row.get('backup_2loc'))} |",
        f"| Decision confirmed | {conf} |",
        f"| Last synced | {date.today().isoformat()} |",
        "",
        "| File | Size | SHA-256 |", "|---|---|---|", ft,
        S_END])


def new_md(row, files):
    return f"""# {row['name']} — {row['source']}

{status_block(row, files)}

## Archive record

| | |
|---|---|
| Archive method | Zip snapshot of `<branch>` _(change if you use a full mirror, see archive/README.md)_ |
| Archive file | `<repo>-<branch>.zip` |
| Archived on | |
| HEAD commit | |
| Pipelines | |
| Package feed | |

## Checks still to do

- [ ] Archive zip downloaded and copied into this folder
- [ ] HEAD commit SHA and date recorded above
- [ ] SHA-256 recorded (use **Rescan files** in the dashboard)
- [ ] Second copy made (S3 or other) and **2-location backup** set to `yes` in the dashboard
- [ ] Written confirmation recorded (Confirmed by / date in the dashboard)
- [ ] Source archived or deleted at source

## Decision trail

- {date.today().isoformat()}: Archive folder created from the dashboard (disposition: {row.get('disposition', '')}).
"""


def sync_md(row, rows, trail=None, insert_if_missing=False):
    """Refresh the managed block in ARCHIVE.md (if the folder exists) and optionally append decision-trail bullets."""
    p = path_for(row, rows)
    md = p / "ARCHIVE.md"
    if not md.exists():
        return False
    txt = md.read_text(encoding="utf-8")
    blk = status_block(row, _files(p))
    if S_START in txt and S_END in txt:
        txt = re.sub(re.escape(S_START) + r".*?" + re.escape(S_END), lambda m: blk, txt, flags=re.S)
    elif insert_if_missing:
        lines = txt.split("\n")
        i = next((n for n, l in enumerate(lines) if l.startswith("# ")), -1)
        lines[i + 1:i + 1] = ["", blk]
        txt = "\n".join(lines)
    else:
        return False
    if trail:
        stamp = date.today().isoformat()
        add = "\n".join(f"- {stamp}: {t}" for t in trail) + "\n"
        if "## Decision trail" in txt:
            txt = txt.rstrip("\n") + "\n" + add
        else:
            txt = txt.rstrip("\n") + "\n\n## Decision trail\n\n" + add
    md.write_text(txt, encoding="utf-8")
    return True


def create(row, rows):
    p = path_for(row, rows)
    if p.exists():
        raise FileExistsError(f"{p.relative_to(ROOT)} already exists. Archives are never overwritten.")
    p.mkdir(parents=True)
    (p / "ARCHIVE.md").write_text(new_md(row, []), encoding="utf-8")
    (p / META).write_text(json.dumps({"id": row["id"], "source": row["source"], "name": row["name"],
                                      "created": datetime.now().isoformat(timespec="seconds"), "files": {}}, indent=2), encoding="utf-8")
    return p


def rescan(row, rows):
    """Hash every file (streaming) and refresh ARCHIVE.md."""
    p = path_for(row, rows)
    if not p.is_dir():
        raise FileNotFoundError("Archive folder does not exist")
    meta = _meta(p) or {"id": row["id"], "files": {}}
    meta["files"] = {}
    for f in sorted(p.iterdir()):
        if f.is_file() and f.name not in SKIP_FILES and not f.name.startswith("."):
            h = hashlib.sha256()
            with open(f, "rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            meta["files"][f.name] = {"size": f.stat().st_size, "sha256": h.hexdigest().upper(), "hashed": date.today().isoformat()}
    (p / META).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    sync_md(row, rows, insert_if_missing=True)
    return _files(p)


def remove(row, rows, confirm=None):
    """Delete the folder. Empty scaffold -> rmdir. Folder holding files -> move to archive/.trash (recoverable) after typed confirm."""
    p = path_for(row, rows)
    if not p.is_dir():
        raise FileNotFoundError("Archive folder does not exist")
    held = [f for f in _files(p)]
    if held and confirm != p.name:
        return {"needs_confirm": True, "folder": p.name, "files": held}
    if held:
        dest = ARCHIVE / ".trash" / safe(row["source"]) / safe(project_of(row)) / f"{p.name}-{datetime.now():%Y%m%d-%H%M%S}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dest))
        _tidy(p.parent)
        return {"ok": True, "trashed": str(dest.relative_to(ROOT)).replace("\\", "/")}
    shutil.rmtree(p)
    _tidy(p.parent)
    return {"ok": True, "trashed": None}


def _tidy(project_dir):
    """Remove the project folder if the repo folder was its last child."""
    try:
        if project_dir.parent.parent == ARCHIVE and not any(project_dir.iterdir()):
            project_dir.rmdir()
    except OSError:
        pass


def write_index(rows):
    """Regenerate the managed archive index inside archive/README.md."""
    if not README.exists():
        return
    st = scan(rows)
    lines = ["| Source | Project | Repo | Reg. id | Disposition | 2-loc backup | Folder | Files |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s = st[r["id"]]
        if not s["exists"]:
            continue
        files = ", ".join(f"`{f['name']}`" for f in s["files"]) or "_none yet_"
        lines.append(f"| {r['source']} | {project_of(r)} | {r['name']} | {r['id']} | {r.get('disposition', '')} | {r.get('backup_2loc') or '—'} | `{s['rel']}` | {files} |")
    if len(lines) == 2:
        lines.append("| _no archive folders yet_ | | | | | | | |")
    block = I_START + "\n" + "\n".join(lines) + "\n" + I_END
    txt = README.read_text(encoding="utf-8")
    if I_START in txt and I_END in txt:
        txt = re.sub(re.escape(I_START) + r".*?" + re.escape(I_END), lambda m: block, txt, flags=re.S)
    else:
        txt = txt.rstrip("\n") + "\n\n## Archived repos (managed by the dashboard)\n\nRegenerated automatically when an archive folder is created, deleted or rescanned. Don't edit between the markers.\n\n" + block + "\n"
    README.write_text(txt, encoding="utf-8")
