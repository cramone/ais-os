#!/usr/bin/env python3
"""Build dashboard.html from the project's CSV/markdown state.

Usage:  python scripts/build_dashboard.py            # writes ./dashboard.html
Inputs: spec/repo-register.csv, spec/tasks.csv, spec/package-dependencies.csv,
        latest spec/inventory/<source>/<date>/*.csv, risks.md, decisions/log.md
Output: dashboard.html (single self-contained file, no network needed)
"""
import csv, json, re, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive_lib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec"
NOTE_SOURCES = ["infoxpert-ado", "magiq-vs-ado", "magiq-ado", "github"]


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if any((v or "").strip() for v in r.values())] if rows and "empty" not in rows[0] else []


def latest_dirs():
    out = {}
    inv = SPEC / "inventory"
    if not inv.exists():
        return out
    for s in sorted(p for p in inv.iterdir() if p.is_dir()):
        dates = sorted(d for d in s.iterdir() if d.is_dir())
        if dates:
            out[s.name] = dates[-1]
    return out


def parse_risks():
    p = ROOT / "risks.md"
    out = []
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| R-"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split(" | ")]
        if len(c) >= 5:
            out.append(dict(id=c[0], risk=c[1], impact=c[2], mitigation=c[3], status=c[4]))
    return out


def parse_decisions():
    p = ROOT / "decisions" / "log.md"
    out = []
    if not p.exists():
        return out
    cur = None
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"## (D-\d+) — (.*?)(?: \((\d{4}-\d{2}-\d{2})\))?$", line)
        if m:
            cur = dict(id=m.group(1), title=m.group(2), date=m.group(3) or "", body="")
            out.append(cur)
        elif cur is not None:
            cur["body"] += line + "\n"
    for d in out:
        d["body"] = d["body"].strip()
    return out


def collect():
    """Gather all project state into one dict (used by the static build and the live server)."""
    register = read_csv(SPEC / "repo-register.csv")
    reg_urls = {r["source_url"].lower() for r in register}
    inv_dirs = latest_dirs()

    staged, builds, svc, pkgs, mycommits, gaps = [], [], [], [], [], []
    inv_meta = {}
    for src, d in inv_dirs.items():
        inv_meta[src] = d.name
        for r in read_csv(d / "register-staged.csv"):
            if r["source_url"].lower() not in reg_urls:
                r["_inv"] = src
                staged.append(r)
        for r in read_csv(d / "build-definitions.csv"):
            r["_src"] = src; builds.append(r)
        for r in read_csv(d / "service-connections.csv"):
            r["_src"] = src; svc.append(r)
        for r in read_csv(d / "packages.csv"):
            r["_src"] = src; pkgs.append(r)
        for r in read_csv(d / "my-commits.csv"):
            r["_src"] = src; mycommits.append(r)
        gaps += read_csv(d / "access-gaps.csv")

    # collapse packages into per-feed summaries (keep full list small)
    feeds = {}
    for p in pkgs:
        f = feeds.setdefault((p["_src"], p["feed"]), dict(source=p["_src"], feed=p["feed"], scope=p.get("feed_scope", ""),
                                                           count=0, latest="", y2026=0))
        f["count"] += 1
        pub = p.get("published", "")
        f["latest"] = max(f["latest"], pub)
        if pub.startswith("2026"):
            f["y2026"] += 1

    raw = (SPEC / "repo-register.csv").read_bytes()
    data = dict(
        built=datetime.date.today().isoformat(),
        eol="\r\n" if b"\r\n" in raw else "\n",
        bom=raw.startswith(b"\xef\xbb\xbf"),
        register=register,
        staged=staged,
        tasks=read_csv(SPEC / "tasks.csv"),
        pkgdeps=read_csv(SPEC / "package-dependencies.csv"),
        builds=builds,
        svc=svc,
        feeds=list(feeds.values()),
        mycommits=[m for m in mycommits if m.get("in_register") == "no"],
        gaps=gaps,
        risks=parse_risks(),
        decisions=parse_decisions(),
        inventory=inv_meta,
        archives=sorted(str(p.relative_to(ROOT / "archive")).replace("\\", "/")
                        for p in (ROOT / "archive").glob("*/*") if p.is_dir()) if (ROOT / "archive").exists() else [],
        notes={src: ((SPEC / "notes" / f"{src}.md").read_text(encoding="utf-8").replace("\r\n", "\n")
                     if (SPEC / "notes" / f"{src}.md").exists() else "")
               for src in NOTE_SOURCES},
        arch=archive_lib.scan(register),
        archiveRoot=str(ROOT / "archive"),
        phase=1,  # current migration phase (1-5); bump when a phase closes
    )
    return data


def rev():
    """Cheap fingerprint of every input file (mtime+size). Changes whenever any source file changes."""
    parts = []
    files = [SPEC / "repo-register.csv", SPEC / "tasks.csv", SPEC / "package-dependencies.csv",
             ROOT / "risks.md", ROOT / "decisions" / "log.md"]
    inv = SPEC / "inventory"
    if inv.exists():
        files += [p for p in inv.rglob("*.csv")]
    if (SPEC / "notes").exists():
        files += list((SPEC / "notes").glob("*.md"))
    for f in sorted(files):
        try:
            st = f.stat()
            parts.append(f"{f.name}:{st.st_mtime_ns}:{st.st_size}")
        except OSError:
            parts.append(f"{f.name}:missing")
    parts.append(archive_lib.fingerprint(None))
    return str(abs(hash("|".join(parts))))


def render_html(data):
    tpl = (ROOT / "scripts" / "dashboard_template.html").read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return tpl.replace("/*__DATA__*/null", blob)


def main():
    data = collect()
    (ROOT / "dashboard.html").write_text(render_html(data), encoding="utf-8")
    print(f"dashboard.html written: {len(data['register'])} register rows, {len(data['staged'])} unmerged staged, "
          f"{len(data['tasks'])} tasks, {len(data['risks'])} risks, {len(data['decisions'])} decisions")


if __name__ == "__main__":
    sys.exit(main())
