#!/usr/bin/env python3
"""
Queries Azure DevOps for work items assigned to you and prints a grouped summary.
Usage: python scripts/devops_summary.py [--all] [--sprint] [--json]
  --all     Show all active items (default: assigned to me only)
  --sprint  Show current sprint items only
  --json    Output structured JSON instead of human-readable text
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import base64
import os
import sys
import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
env = {}
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

PAT = env.get("AZURE_DEVOPS_PAT") or os.environ.get("AZURE_DEVOPS_PAT")
ORG = env.get("AZURE_DEVOPS_ORG") or os.environ.get("AZURE_DEVOPS_ORG")
PROJECT = env.get("AZURE_DEVOPS_PROJECT") or os.environ.get("AZURE_DEVOPS_PROJECT")

if not all([PAT, ORG, PROJECT]):
    print("Missing AZURE_DEVOPS_PAT, AZURE_DEVOPS_ORG, or AZURE_DEVOPS_PROJECT in .env")
    sys.exit(1)

TOKEN = base64.b64encode(f":{PAT}".encode()).decode()
HEADERS = {"Authorization": f"Basic {TOKEN}", "Content-Type": "application/json"}
BASE_URL = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis"

ARGS = sys.argv[1:]
SHOW_ALL = "--all" in ARGS
SPRINT_ONLY = "--sprint" in ARGS
JSON_OUT = "--json" in ARGS
CROSS_PROJECT = "--cross-project" in ARGS
PR_THREADS = "--pr-threads" in ARGS
WITH_COMMENTS = "--comments" in ARGS

# Only fetch comments for items touched within this window, capped, to bound API cost
_COMMENT_WINDOW_DAYS = 21
_COMMENT_MAX_ITEMS = 60


def api_get(path):
    req = urllib.request.Request(f"https://dev.azure.com/{ORG}/{PROJECT}/_apis{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def api_post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"https://dev.azure.com/{ORG}/{PROJECT}/_apis{path}",
        data=data,
        headers=HEADERS
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# --- Org-level variants (no project scope) — for cross-project queries ---

def org_api_get(path):
    req = urllib.request.Request(f"https://dev.azure.com/{ORG}/_apis{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def org_api_post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"https://dev.azure.com/{ORG}/_apis{path}", data=data, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def org_get_work_items(ids, fields):
    if not ids:
        return []
    results = []
    field_list = ",".join(fields)
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        id_str = ",".join(str(x) for x in chunk)
        data = org_api_get(f"/wit/workitems?ids={id_str}&fields={field_list}&api-version=7.1")
        results.extend(data.get("value", []))
    return results


import re
import html as _html

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s):
    """Collapse ADO rich-text comment HTML to plain text."""
    s = _TAG_RE.sub(" ", s)
    s = _html.unescape(s)
    return " ".join(s.split()).strip()


def authenticated_user_id():
    """My ADO identity id — used to tell my own comments from others'."""
    try:
        data = org_api_get("/connectionData?api-version=7.1")
        return data.get("authenticatedUser", {}).get("id", "")
    except Exception:
        return ""


def get_item_comments(project, item_id, my_id):
    """Fetch comments for one work item; return (total, last_comment_dict|None, awaiting_me).
    awaiting_me = newest comment exists and was NOT authored by me."""
    url = (f"https://dev.azure.com/{ORG}/{urllib.parse.quote(project)}"
           f"/_apis/wit/workItems/{item_id}/comments?api-version=7.1-preview.4")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
    except Exception:
        return 0, None, False
    comments = data.get("comments", [])
    if not comments:
        return 0, None, False
    comments.sort(key=lambda c: c.get("createdDate", ""))
    last = comments[-1]
    author = last.get("createdBy", {}) or {}
    is_mine = author.get("id", "") == my_id
    text = _strip_html(last.get("text", "") or "")
    if len(text) > 140:
        text = text[:137] + "..."
    last_comment = {
        "author": author.get("displayName", ""),
        "date": last.get("createdDate", ""),
        "text": text,
        "is_mine": is_mine,
    }
    return data.get("totalCount", len(comments)), last_comment, (not is_mine)


def wiql(query):
    return api_post("/wit/wiql?api-version=7.1", {"query": query})


def get_work_items(ids, fields):
    if not ids:
        return []
    chunk_size = 200
    results = []
    field_list = ",".join(fields)
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i:i + chunk_size]
        id_str = ",".join(str(x) for x in chunk)
        data = api_get(f"/wit/workitems?ids={id_str}&fields={field_list}&api-version=7.1")
        results.extend(data.get("value", []))
    return results


def build_query():
    conditions = ["[System.TeamProject] = @project", "[System.State] NOT IN ('Done', 'Closed', 'Removed')"]
    if not SHOW_ALL:
        conditions.append("[System.AssignedTo] = @me")
    if SPRINT_ONLY:
        conditions.append("[System.IterationPath] = @currentIteration")
    where = " AND ".join(conditions)
    return f"SELECT [System.Id] FROM workitems WHERE {where} ORDER BY [System.ChangedDate] DESC"


def display_name(assigned):
    if isinstance(assigned, dict):
        return assigned.get("displayName", "Unassigned")
    return "Unassigned" if not assigned else str(assigned)


def main_json():
    """Output structured JSON for tower consumption."""
    result = wiql(build_query())
    item_ids = [i["id"] for i in result.get("workItems", [])]

    if not item_ids:
        print(json.dumps({"items": [], "total": 0, "fetched_at": datetime.datetime.now().isoformat()}))
        return

    fields = [
        "System.Id",
        "System.Title",
        "System.WorkItemType",
        "System.State",
        "System.AssignedTo",
        "System.IterationPath",
        "System.AreaPath",
        "Microsoft.VSTS.Common.Priority",
        "System.Tags",
    ]

    raw_items = get_work_items(item_ids, fields)
    output = []
    for item in raw_items:
        f = item["fields"]
        item_id = f["System.Id"]
        iteration = f.get("System.IterationPath", "")
        sprint = iteration.split("\\")[-1] if "\\" in iteration else iteration
        area = f.get("System.AreaPath", "")
        module = area.split("\\")[-1] if "\\" in area else area
        output.append({
            "id": item_id,
            "title": f.get("System.Title", ""),
            "type": f.get("System.WorkItemType", ""),
            "state": f.get("System.State", ""),
            "assignee": display_name(f.get("System.AssignedTo")),
            "priority": f.get("Microsoft.VSTS.Common.Priority"),
            "sprint": sprint,
            "module": module,
            "project": area,
            "tags": f.get("System.Tags", "") or "",
            "url": f"https://dev.azure.com/{ORG}/{PROJECT}/_workitems/edit/{item_id}",
            "daysInState": None,
        })

    print(json.dumps({
        "items": output,
        "total": len(output),
        "fetched_at": datetime.datetime.now().isoformat(),
    }))


def main_cross_project():
    """Org-wide: my open items across ALL projects, grouped by project. JSON only."""
    query = (
        "SELECT [System.Id] FROM workitems "
        "WHERE [System.AssignedTo] = @me "
        "AND [System.State] NOT IN ('Done', 'Closed', 'Removed', 'Resolved') "
        "ORDER BY [System.ChangedDate] DESC"
    )
    result = org_api_post("/wit/wiql?api-version=7.1", {"query": query})
    item_ids = [i["id"] for i in result.get("workItems", [])]

    if not item_ids:
        print(json.dumps({"projects": [], "total": 0, "fetched_at": datetime.datetime.now().isoformat()}))
        return

    fields = [
        "System.Id", "System.Title", "System.WorkItemType", "System.State",
        "System.TeamProject", "System.AreaPath", "System.IterationPath",
        "Microsoft.VSTS.Common.Priority", "System.Tags", "System.ChangedDate",
    ]
    raw_items = org_get_work_items(item_ids, fields)

    projects: dict[str, dict] = {}
    for item in raw_items:
        f = item["fields"]
        proj = f.get("System.TeamProject", "Unknown")
        area = f.get("System.AreaPath", "")
        module = area.split("\\")[-1] if "\\" in area else area
        iteration = f.get("System.IterationPath", "")
        sprint = iteration.split("\\")[-1] if "\\" in iteration else iteration
        state = f.get("System.State", "")
        item_id = f["System.Id"]

        p = projects.setdefault(proj, {"name": proj, "total": 0, "code_review": 0, "states": {}, "items": []})
        p["total"] += 1
        p["states"][state] = p["states"].get(state, 0) + 1
        if state == "Code Review":
            p["code_review"] += 1
        item = {
            "id": item_id,
            "title": f.get("System.Title", ""),
            "type": f.get("System.WorkItemType", ""),
            "state": state,
            "priority": f.get("Microsoft.VSTS.Common.Priority"),
            "module": module,
            "sprint": sprint,
            "tags": f.get("System.Tags", "") or "",
            "url": f"https://dev.azure.com/{ORG}/_workitems/edit/{item_id}",
            "comment_count": 0,
            "last_comment": None,
            "awaiting_me": False,
            "_project": proj,
            "_changed": f.get("System.ChangedDate", ""),
        }
        p["items"].append(item)

    if WITH_COMMENTS:
        _enrich_comments(projects)

    # Strip internal fields and roll up per-project awaiting_me count
    ordered = sorted(projects.values(), key=lambda x: x["total"], reverse=True)
    for p in ordered:
        p["awaiting_me"] = sum(1 for it in p["items"] if it.get("awaiting_me"))
        for it in p["items"]:
            it.pop("_project", None)
            it.pop("_changed", None)

    print(json.dumps({
        "projects": ordered,
        "total": sum(p["total"] for p in ordered),
        "project_count": len(ordered),
        "awaiting_me": sum(p["awaiting_me"] for p in ordered),
        "comments_enriched": WITH_COMMENTS,
        "fetched_at": datetime.datetime.now().isoformat(),
    }))


def _enrich_comments(projects):
    """Fetch work-item comments for recently-changed items (bounded) and attach in place."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=_COMMENT_WINDOW_DAYS))
    candidates = []
    for p in projects.values():
        for it in p["items"]:
            changed = it.get("_changed", "")
            try:
                cd = datetime.datetime.fromisoformat(changed.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue
            if cd >= cutoff:
                candidates.append(it)
    candidates.sort(key=lambda it: it.get("_changed", ""), reverse=True)
    candidates = candidates[:_COMMENT_MAX_ITEMS]
    if not candidates:
        return
    my_id = authenticated_user_id()

    def work(it):
        total, last, awaiting = get_item_comments(it["_project"], it["id"], my_id)
        it["comment_count"] = total
        it["last_comment"] = last
        it["awaiting_me"] = awaiting

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(work, candidates))


def _org_pr_search(criteria):
    url = (f"https://dev.azure.com/{ORG}/_apis/git/pullrequests"
           f"?{criteria}&searchCriteria.status=active&$top=200&api-version=7.1")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()).get("value", [])


def _pr_active_threads(project, repo_id, pr_id, my_id):
    """Return (unresolved_count, last_unresolved_dict|None) for a PR.
    Unresolved = thread.status == 'active' with at least one non-system comment."""
    url = (f"https://dev.azure.com/{ORG}/{urllib.parse.quote(project)}"
           f"/_apis/git/repositories/{repo_id}/pullRequests/{pr_id}/threads?api-version=7.1")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as r:
            threads = json.loads(r.read()).get("value", [])
    except Exception:
        return 0, None
    open_threads = []
    for t in threads:
        if t.get("status") != "active":
            continue
        comments = [c for c in t.get("comments", []) if c.get("commentType") != "system"]
        if not comments:
            continue
        last = comments[-1]
        author = last.get("author", {}) or {}
        open_threads.append({
            "author": author.get("displayName", ""),
            "text": _strip_html(last.get("content", "") or "")[:140],
            "date": last.get("publishedDate", "") or last.get("lastUpdatedDate", ""),
            "mine": author.get("id", "") == my_id,
        })
    last_unres = max(open_threads, key=lambda x: x["date"]) if open_threads else None
    return len(open_threads), last_unres


def main_pr_threads():
    """My active ADO Repos PRs across projects + unresolved comment-thread counts.
    Requires PAT with Code (read) scope; degrades gracefully on 401."""
    my_id = authenticated_user_id()
    prs_raw = {}
    try:
        for crit, role in [(f"searchCriteria.creatorId={my_id}", "author"),
                           (f"searchCriteria.reviewerId={my_id}", "reviewer")]:
            for pr in _org_pr_search(crit):
                pid = pr["pullRequestId"]
                if pid not in prs_raw:
                    prs_raw[pid] = (pr, role)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(json.dumps({
                "prs": [], "total": 0, "total_unresolved": 0,
                "error": "auth", "scope_hint": "AZURE_DEVOPS_PAT needs 'Code (read)' scope to read pull requests.",
                "fetched_at": datetime.datetime.now().isoformat(),
            }))
            return
        raise
    except Exception as e:
        print(json.dumps({"prs": [], "total": 0, "total_unresolved": 0, "error": str(e),
                          "fetched_at": datetime.datetime.now().isoformat()}))
        return

    items = []
    for pid, (pr, role) in prs_raw.items():
        repo = pr.get("repository", {}) or {}
        project = (repo.get("project", {}) or {}).get("name", "")
        items.append({
            "id": pid,
            "title": pr.get("title", ""),
            "repo": repo.get("name", ""),
            "project": project,
            "role": role,
            "isDraft": pr.get("isDraft", False),
            "url": f"https://dev.azure.com/{ORG}/{urllib.parse.quote(project)}/_git/{urllib.parse.quote(repo.get('name',''))}/pullrequest/{pid}",
            "_repo_id": repo.get("id", ""),
            "_project": project,
        })

    def work(it):
        n, last = _pr_active_threads(it["_project"], it["_repo_id"], it["id"], my_id)
        it["unresolved"] = n
        it["last_unresolved"] = last

    if items:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(work, items))

    for it in items:
        it.pop("_repo_id", None)
        it.pop("_project", None)
    items.sort(key=lambda x: x.get("unresolved", 0), reverse=True)
    print(json.dumps({
        "prs": items,
        "total": len(items),
        "total_unresolved": sum(it.get("unresolved", 0) for it in items),
        "fetched_at": datetime.datetime.now().isoformat(),
    }))


def main():
    if PR_THREADS:
        main_pr_threads()
        return
    if CROSS_PROJECT:
        main_cross_project()
        return
    if JSON_OUT:
        main_json()
        return

    print(f"Querying {ORG}/{PROJECT}{'  [sprint only]' if SPRINT_ONLY else ''}{'  [all users]' if SHOW_ALL else '  [assigned to me]'}...\n")

    result = wiql(build_query())
    item_ids = [i["id"] for i in result.get("workItems", [])]

    if not item_ids:
        print("No active work items found.")
        return

    fields = [
        "System.Id",
        "System.Title",
        "System.WorkItemType",
        "System.State",
        "System.AssignedTo",
        "System.IterationPath",
        "Microsoft.VSTS.Common.Priority",
        "System.Tags",
    ]

    items = get_work_items(item_ids, fields)

    # Group by type then state
    by_type = defaultdict(lambda: defaultdict(list))
    for item in items:
        f = item["fields"]
        wit = f.get("System.WorkItemType", "Unknown")
        state = f.get("System.State", "Unknown")
        by_type[wit][state].append(f)

    total = len(items)
    label = "all users" if SHOW_ALL else "you"
    print(f"{'─' * 60}")
    print(f"  ACTIVE WORK ITEMS — {label.upper()}  ({total} total)")
    print(f"{'─' * 60}")

    type_order = ["Epic", "Feature", "User Story", "Product Backlog Item", "Bug", "Task"]
    all_types = type_order + sorted(t for t in by_type if t not in type_order)

    for wit in all_types:
        if wit not in by_type:
            continue
        states = by_type[wit]
        type_total = sum(len(v) for v in states.values())
        print(f"\n▸ {wit} ({type_total})")

        state_order = ["Active", "In Progress", "Code Review", "In Review", "New", "To Do", "Blocked"]
        all_states = state_order + sorted(s for s in states if s not in state_order)

        for state in all_states:
            if state not in states:
                continue
            state_items = states[state]
            print(f"  [{state}] ({len(state_items)})")
            for f in state_items[:10]:
                priority = f.get("Microsoft.VSTS.Common.Priority", "")
                p_str = f" P{priority}" if priority else ""
                assigned = display_name(f.get("System.AssignedTo"))
                assigned_str = f" → {assigned}" if SHOW_ALL else ""
                title = f.get("System.Title", "")
                if len(title) > 70:
                    title = title[:67] + "..."
                print(f"    #{f['System.Id']}{p_str}{assigned_str}  {title}")
            if len(state_items) > 10:
                print(f"    ... and {len(state_items) - 10} more")

    print(f"\n{'─' * 60}")

    # Code review items highlighted
    cr_items = [
        f for wit_states in by_type.values()
        for state, items_list in wit_states.items()
        if state == "Code Review"
        for f in items_list
    ]
    if cr_items:
        print(f"\n⚠  CODE REVIEW NEEDED ({len(cr_items)})")
        for f in cr_items:
            print(f"  #{f['System.Id']}  {f.get('System.Title', '')}")

    print()


if __name__ == "__main__":
    main()
