#!/usr/bin/env python3
"""Find every repo (Git across all branches, plus TFVC) where you have commits, and flag the ones not yet in repo-register.csv.

Usage:  python scripts/find_my_commits.py magiqsoftware
        python scripts/find_my_commits.py infoxpert --match "chase,chaser"
Output: spec/inventory/<source>/<date>/my-commits.csv
Read-only. Uses the same .env and token as inventory_ado.py.
"""
import argparse, csv, datetime as dt, sys, urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inventory_ado as inv  # reuses load_env and the Ado client (gap handling, paging)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("org", choices=list(inv.SOURCE_KEYS))
    ap.add_argument("--match", default="chase.ramone,chase ramone,chaser",
                    help="comma-separated, case-insensitive substrings matched against author name or email")
    a = ap.parse_args()
    key, source = a.org.lower(), inv.SOURCE_KEYS[a.org.lower()]
    needles = [m.strip().lower() for m in a.match.split(",") if m.strip()]
    mine = lambda name, email: any(n in f"{name} {email}".lower() for n in needles)

    inv.load_env()
    import os
    ado = inv.Ado(os.environ[f"ADO_{key.upper()}_ORG_URL"], os.environ[f"ADO_{key.upper()}_PAT"])
    reg = inv.ROOT / "spec" / "repo-register.csv"
    registered = {r["source_url"] for r in csv.DictReader(open(reg, encoding="utf-8"))} if reg.exists() else set()

    rows = []
    for p in ado.paged("_apis/projects", {"$top": 500}):
        pname, pq = p["name"], urllib.parse.quote(p["name"])
        ado.project = pname
        print(f"→ {pname}")
        for r in (ado.get(f"{pq}/_apis/git/repositories") or {}).get("value", []):
            if r.get("isDisabled") or not r.get("size"):
                continue
            rid, count, last, branches = r["id"], 0, "", []
            seen = set()
            for ref in ado.paged(f"{pq}/_apis/git/repositories/{rid}/refs", {"filter": "heads/"}):
                br = ref["name"].replace("refs/heads/", "")
                commits = ado.paged(f"{pq}/_apis/git/repositories/{rid}/commits",
                                    {"searchCriteria.itemVersion.version": br, "searchCriteria.$top": 5000})
                hits = [c for c in commits if mine(c["author"].get("name", ""), c["author"].get("email", ""))]
                if hits:
                    branches.append(br)
                    for c in hits:
                        if c["commitId"] not in seen:
                            seen.add(c["commitId"])
                            count += 1
                            last = max(last, c["author"]["date"][:10])
            if count:
                rows.append({"project": pname, "repo": r["name"], "vc": "git", "my_commits": count, "my_last_commit": last,
                             "branches": ";".join(branches[:10]) + (" …" if len(branches) > 10 else ""),
                             "in_register": "yes" if r.get("webUrl") in registered else "no", "source_url": r.get("webUrl", "")})
        cs = ado.paged(f"{pq}/_apis/tfvc/changesets", {"searchCriteria.itemPath": f"$/{pname}", "$top": 5000})
        hits = [c for c in cs if mine((c.get("author") or {}).get("displayName", ""), (c.get("author") or {}).get("uniqueName", ""))]
        if hits:
            url = f"{ado.org_url}/{pq}/_versionControl"
            rows.append({"project": pname, "repo": f"$/{pname}", "vc": "tfvc", "my_commits": len(hits),
                         "my_last_commit": max(c["createdDate"][:10] for c in hits), "branches": "",
                         "in_register": "yes" if url in registered else "no", "source_url": url})

    out = inv.ROOT / "spec" / "inventory" / source / dt.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    cols = ["project", "repo", "vc", "my_commits", "my_last_commit", "branches", "in_register", "source_url"]
    with open(out / "my-commits.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["in_register"], r["project"], r["repo"])))
    new = [r for r in rows if r["in_register"] == "no"]
    print(f"\n✓ {len(rows)} repos with your commits · {len(new)} not in register → {(out / 'my-commits.csv').relative_to(inv.ROOT)}")
    if ado.gaps:
        print(f"  ⚠ {len(ado.gaps)} access gaps (not saved separately; rerun inventory_ado.py for detail)")


if __name__ == "__main__":
    main()
