#!/usr/bin/env python3
"""Catalog an ADO org: projects, Git and TFVC repos, last commit, open PRs, pipelines, LFS, feeds/packages, service connections.

Usage:  python scripts/inventory_ado.py infoxpert          (reads ADO_INFOXPERT_ORG_URL / ADO_INFOXPERT_PAT from .env)
Output: spec/inventory/<source-key>/<YYYY-MM-DD>/
          repos.csv                register-schema rows (id blank, assigned on merge into repo-register.csv)
          packages.csv             every feed and package with its latest version
          service-connections.csv  name, type, URL (no secrets; ADO never returns them)
          build-definitions.csv    pipeline definition per repo
          raw/                     raw API JSON (gitignored)
Read-only. Never writes to the org, and never prints the PAT.
Stdlib only (Python 3.8+).
"""
import base64, csv, datetime as dt, json, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "7.1"
SOURCE_KEYS = {"infoxpert": "infoxpert-ado", "magiqsoftware": "magiq-ado", "magiq": "magiq-vs-ado"}
REGISTER_COLS = ["id", "name", "source", "source_url", "last_commit_date", "last_commit_author", "open_prs",
                 "has_pipelines", "has_lfs", "has_packages", "visibility", "owner", "classification",
                 "disposition", "migration_status", "destination_url", "notes"]


def load_env():
    path = Path(os.environ.get("REPO_HK_ENV_FILE", ROOT / ".env"))
    if not path.exists():
        sys.exit(f"No env file at {path}. Copy .env.example to .env and fill it in.")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Ado:
    def __init__(self, org_url, pat):
        self.org_url = org_url.rstrip("/")
        host = urllib.parse.urlparse(self.org_url).netloc
        org = host.split(".")[0] if host.endswith("visualstudio.com") else self.org_url.split("/")[-1]
        legacy = host.endswith("visualstudio.com")
        self.feeds_url = f"https://{org}.feeds.visualstudio.com" if legacy else f"https://feeds.dev.azure.com/{org}"
        self.vsrm_url = f"https://{org}.vsrm.visualstudio.com" if legacy else f"https://vsrm.dev.azure.com/{org}"
        self._auth = "Basic " + base64.b64encode(f":{pat}".encode()).decode()
        self.raw = {}
        self.authed = False      # set True after the first successful call; any later 401/403 is a permission gap, not a bad PAT
        self.project = ""        # current project, used when recording gaps
        self.gaps = []

    def _gap(self, url, code):
        area = next((a for a in ("git", "build", "release", "serviceendpoint", "packaging", "tfvc") if f"/{a}/" in url or f"_apis/{a}" in url), "other")
        self.gaps.append({"project": self.project or "(org)", "area": area, "http": code, "endpoint": url.split("?")[0]})
        print(f"  ⚠ {code} {self.project or 'org'}: no access to {area} (recorded, continuing)", file=sys.stderr)

    def get(self, url, params=None, ok404=False, base=None):
        params = {**(params or {}), "api-version": API}
        full = f"{base or self.org_url}/{url.lstrip('/')}?{urllib.parse.urlencode(params, safe='$/', quote_via=urllib.parse.quote)}"
        req = urllib.request.Request(full, headers={"Authorization": self._auth, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status == 203 or "json" not in r.headers.get("Content-Type", ""):
                    if not self.authed:
                        sys.exit("Auth failed (ADO returned a sign-in page). Check the PAT, its scopes and expiry.")
                    self._gap(url, 203)
                    return None
                body = json.loads(r.read() or b"{}")
                body["_continuation"] = r.headers.get("x-ms-continuationtoken")
                self.authed = True
                return body
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                if not self.authed:
                    sys.exit(f"{e.code} on first call. Check the PAT, its org and its scopes.")
                self._gap(url, e.code)
                return None
            if ok404 and e.code in (404, 400):
                return None
            self._gap(url, e.code)      # 5xx or unexpected: record it and keep going
            return None
        except urllib.error.URLError as e:
            sys.exit(f"Network error reaching {base or self.org_url}: {e.reason}")

    def paged(self, url, params=None, base=None):
        token, out = None, []
        while True:
            p = {**(params or {}), **({"continuationToken": token} if token else {})}
            body = self.get(url, p, base=base, ok404=True) or {}
            out += body.get("value", [])
            token = body.get("_continuation")
            if not token:
                return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Read-only ADO inventory")
    ap.add_argument("org", choices=list(SOURCE_KEYS))
    ap.add_argument("--only", help="comma-separated project names to include (default: all you can see)")
    ap.add_argument("--skip", help="comma-separated project names to exclude")
    args = ap.parse_args()
    key = args.org.lower()
    source = SOURCE_KEYS[key]
    load_env()
    org_url, pat = os.environ.get(f"ADO_{key.upper()}_ORG_URL"), os.environ.get(f"ADO_{key.upper()}_PAT")
    if not org_url or not pat:
        sys.exit(f"Set ADO_{key.upper()}_ORG_URL and ADO_{key.upper()}_PAT in .env")

    ado = Ado(org_url, pat)
    out = ROOT / "spec" / "inventory" / source / dt.date.today().isoformat()
    (out / "raw").mkdir(parents=True, exist_ok=True)
    repos, builds, svc, pkgs = [], [], [], []

    projects = ado.paged("_apis/projects", {"$top": 500, "stateFilter": "wellFormed"})
    visible = len(projects)
    norm = lambda s: {x.strip().lower() for x in s.split(",") if x.strip()} if s else set()
    only, skip = norm(args.only), norm(args.skip)
    projects = [p for p in projects if (not only or p["name"].lower() in only) and p["name"].lower() not in skip]
    print(f"{visible} projects visible to this PAT in {ado.org_url}; scanning {len(projects)}")
    raw = {"projects": projects, "repos": {}}

    for p in projects:
        pname, pq = p["name"], urllib.parse.quote(p["name"])
        ado.project = pname
        print(f"→ {pname}")
        vis = "public" if p.get("visibility") == "public" else "private"

        # Pipelines (build definitions), indexed by repo id
        defs = ado.paged(f"{pq}/_apis/build/definitions", {"includeLatestBuilds": "true", "includeAllProperties": "true", "queryOrder": "lastModifiedDescending"})
        by_repo = {}
        for d in defs:
            rid = (d.get("repository") or {}).get("id")
            lb = (d.get("latestBuild") or {})
            builds.append({"project": pname, "definition": d["name"], "id": d["id"],
                           "repo_type": (d.get("repository") or {}).get("type"), "repo_name": (d.get("repository") or {}).get("name"),
                           "queue_status": d.get("queueStatus"), "last_build": (lb.get("finishTime") or "")[:10],
                           "last_result": lb.get("result", "")})
            if rid:
                by_repo.setdefault(rid, []).append(d)
        releases = ado.get(f"{pq}/_apis/release/definitions", base=ado.vsrm_url, ok404=True)
        rel_count = len((releases or {}).get("value", []))
        build_gap = any(g["project"] == pname and g["area"] in ("build", "release") for g in ado.gaps)  # unknown ≠ false

        # Service connections
        for e in ado.paged(f"{pq}/_apis/serviceendpoint/endpoints"):
            svc.append({"project": pname, "name": e.get("name"), "type": e.get("type"), "url": e.get("url"),
                        "is_shared": e.get("isShared"), "created_by": (e.get("createdBy") or {}).get("uniqueName", "")})

        # Git repos
        for r in (ado.get(f"{pq}/_apis/git/repositories") or {}).get("value", []):
            rid, branch = r["id"], (r.get("defaultBranch") or "").replace("refs/heads/", "")
            notes = [f"project={pname}"]
            if r.get("isDisabled"):
                notes.append("DISABLED")
            last_date = last_author = ""
            if branch and r.get("size", 0) > 0:
                c = (ado.get(f"{pq}/_apis/git/repositories/{rid}/commits",
                             {"searchCriteria.$top": 1, "searchCriteria.itemVersion.version": branch}, ok404=True) or {}).get("value", [])
                if c:
                    last_date, last_author = c[0]["committer"]["date"][:10], c[0]["author"]["name"]
                ga = ado.get(f"{pq}/_apis/git/repositories/{rid}/items",
                             {"path": "/.gitattributes", "includeContent": "true", "versionDescriptor.version": branch}, ok404=True)
                has_lfs = "true" if ga and "filter=lfs" in (ga.get("content") or "") else "false"
            else:
                has_lfs = "false"
                notes.append("EMPTY")
            prs = ado.paged(f"{pq}/_apis/git/repositories/{rid}/pullrequests", {"searchCriteria.status": "active", "$top": 1000})
            pdefs = by_repo.get(rid, [])
            if pdefs:
                notes.append(f"{len(pdefs)} build def(s)")
            if rel_count:
                notes.append(f"project has {rel_count} release def(s)")
            if r.get("size"):
                notes.append(f"{round(r['size'] / 1048576, 1)}MB")
            repos.append({"id": "", "name": r["name"], "source": source, "source_url": r.get("webUrl", ""),
                          "last_commit_date": last_date, "last_commit_author": last_author, "open_prs": len(prs),
                          "has_pipelines": "true" if pdefs else ("unknown" if build_gap else "false"),
                          "has_lfs": has_lfs, "has_packages": "unknown",
                          "visibility": vis, "owner": "", "classification": "unknown", "disposition": "tbd",
                          "migration_status": "not-started", "destination_url": "", "notes": "; ".join(notes)})
            raw["repos"][r["name"]] = r

        # TFVC. Projects can contain TFVC alongside Git; GitHub's importer can't migrate TFVC directly
        root = ado.get(f"{pq}/_apis/tfvc/items", {"scopePath": f"$/{pname}", "recursionLevel": "OneLevel"}, ok404=True)
        if root and len(root.get("value", [])) > 1:
            cs = (ado.get(f"{pq}/_apis/tfvc/changesets", {"searchCriteria.itemPath": f"$/{pname}", "$top": 1}, ok404=True) or {}).get("value", [])
            repos.append({"id": "", "name": f"$/{pname}", "source": source, "source_url": f"{ado.org_url}/{pq}/_versionControl",
                          "last_commit_date": cs[0]["createdDate"][:10] if cs else "",
                          "last_commit_author": (cs[0].get("author") or {}).get("displayName", "") if cs else "",
                          "open_prs": 0, "has_pipelines": "true" if (defs or rel_count) else ("unknown" if build_gap else "false"), "has_lfs": "false",
                          "has_packages": "unknown", "visibility": vis, "owner": "", "classification": "unknown",
                          "disposition": "tbd", "migration_status": "not-started", "destination_url": "",
                          "notes": f"project={pname}; TFVC: needs git-tfs/git-tfvc conversion before migration"
                                   + (f"; {len(defs)} build def(s) in project" if defs else "")
                                   + (f"; {rel_count} release def(s) in project" if rel_count else "")})

    # Feeds and packages (org-scoped plus project-scoped)
    ado.project = ""
    feeds = ado.paged("_apis/packaging/feeds", base=ado.feeds_url)
    for p in projects:
        ado.project = p["name"]
        feeds += ado.paged(f"{urllib.parse.quote(p['name'])}/_apis/packaging/feeds", base=ado.feeds_url) or []
    seen = set()
    for f in feeds:
        if f["id"] in seen:
            continue
        seen.add(f["id"])
        scope = (f.get("project") or {}).get("name", "")
        fpath = f"{urllib.parse.quote(scope) + '/' if scope else ''}_apis/packaging/feeds/{f['id']}/packages"
        for pk in ado.paged(fpath, {"$top": 1000}, base=ado.feeds_url):
            latest = next((v for v in pk.get("versions", []) if v.get("isLatest")), (pk.get("versions") or [{}])[0])
            pkgs.append({"feed": f["name"], "feed_scope": scope or "org", "package": pk["name"],
                         "protocol": pk.get("protocolType"), "latest_version": latest.get("version", ""),
                         "published": (latest.get("publishDate") or "")[:10]})

    def write(name, rows, cols=None):
        cols = cols or (list(rows[0].keys()) if rows else ["empty"])
        with open(out / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)

    write("repos.csv", repos, REGISTER_COLS)
    write("build-definitions.csv", builds)
    write("service-connections.csv", svc)
    write("packages.csv", pkgs)
    write("access-gaps.csv", ado.gaps, ["project", "area", "http", "endpoint"])
    raw["scan"] = {"visible_projects": visible, "scanned": [p["name"] for p in projects],
                   "only": sorted(only), "skip": sorted(skip)}
    (out / "raw" / "inventory.json").write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")

    gap_projects = sorted({g["project"] for g in ado.gaps})
    print(f"\n✓ {len(repos)} repos · {len(builds)} build defs · {len(svc)} service connections · "
          f"{len(feeds)} feeds / {len(pkgs)} packages\n  → {out.relative_to(ROOT)}")
    if ado.gaps:
        print(f"  ⚠ {len(ado.gaps)} access gaps across {len(gap_projects)} project(s), see access-gaps.csv")
    print("  ℹ Projects this PAT can't see aren't listed by ADO at all. Ask an org admin for the full project count.")


if __name__ == "__main__":
    main()
