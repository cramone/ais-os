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
import json
import base64
import os
import sys
import datetime
from collections import defaultdict
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


def main():
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
