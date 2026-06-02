---
name: devops
description: Use when Chase asks about Azure DevOps tasks, work items, sprint status, code review queue, or anything related to his current workload in DevOps. Triggers on "devops", "/devops", "my tasks", "what's in code review", "sprint status", "task summary", "what am I working on", or any request to view, update, or query Azure DevOps work items.
---

## What this skill does

Queries Azure DevOps via `scripts/devops_summary.py` and interprets the results. Surfaces task
status, code review queue, sprint items, and workload summary in a clean format. Can also answer
targeted questions by running filtered queries directly against the REST API.

Credentials and org config live in `.env` at the project root. Script handles auth, pagination,
and grouping.

---

## Modes

### 1. `/devops` — full summary (default)

Run when Chase says `/devops`, "what's my DevOps status", "task summary", or similar with no
specific filter.

```bash
python scripts/devops_summary.py
```

Interpret and present the output as:

```
## DevOps — {date}

**{total} active items assigned to you**

### By Type
- Epic ({n})    — {state breakdown}
- Feature ({n}) — {state breakdown}
- Task ({n})    — {state breakdown}
- Bug ({n})     — {state breakdown}

### ⚠ Code Review ({n})
#{id} — {title}
...

### Needs Attention
{blocked items, or anything flagged as high priority not yet active}
```

Keep it scannable. Summarise counts; call out code review and blocked items explicitly.
Don't repeat every item.

---

### 2. `/devops sprint` — current sprint only

Run when Chase asks "sprint status", "what's in this sprint", "current sprint".

```bash
python scripts/devops_summary.py --sprint
```

Same output format, scoped to sprint items only.

---

### 3. `/devops review` — code review queue only

Run when Chase asks "what's in code review", "review queue", "what needs review".

```bash
python scripts/devops_summary.py
```

Filter output to Code Review state only. Present as a clean numbered list:

```
## Code Review Queue ({n} items)

1. #{id} — {title}
2. #{id} — {title}
...
```

If queue is empty: "Code review queue is clear."

---

### 4. `/devops all` — team view

Run when Chase asks "team tasks", "what's the team working on", "full board".

```bash
python scripts/devops_summary.py --all
```

Group by assignee then by state. After output, offer: "Want me to turn this into a standup
summary?"

---

### 5. `/devops #<id>` — single item detail

Run when Chase references a specific work item ID (e.g. "show me #342", "what's task 456").

```python
import urllib.request, base64, json, re
from pathlib import Path

env = {}
for line in Path('.env').read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

PAT, ORG, PROJECT = env['AZURE_DEVOPS_PAT'], env['AZURE_DEVOPS_ORG'], env['AZURE_DEVOPS_PROJECT']
token = base64.b64encode(f':{PAT}'.encode()).decode()
headers = {'Authorization': f'Basic {token}'}

item_id = {ITEM_ID}
req = urllib.request.Request(
    f'https://dev.azure.com/{ORG}/{PROJECT}/_apis/wit/workitems/{item_id}?api-version=7.1&$expand=relations',
    headers=headers
)
with urllib.request.urlopen(req) as r:
    item = json.loads(r.read())
    f = item['fields']
    print(f'#{item_id} — {f["System.Title"]}')
    print(f'Type:      {f["System.WorkItemType"]}')
    print(f'State:     {f["System.State"]}')
    print(f'Assigned:  {f.get("System.AssignedTo", {}).get("displayName", "Unassigned")}')
    print(f'Priority:  {f.get("Microsoft.VSTS.Common.Priority", "-")}')
    print(f'Iteration: {f.get("System.IterationPath", "-")}')
    desc = f.get('System.Description', '')
    if desc:
        print(f'Desc:      {re.sub("<[^>]+>", "", desc)[:300]}')
```

Present cleanly. Offer to update state or add a comment if relevant.

---

### 6. `/devops update #<id> <state>` — update item state

Run when Chase says "move #123 to Active", "mark #456 done", "set #789 to Code Review".

Valid states: `New`, `Active`, `In Progress`, `Code Review`, `Done`, `Closed`

```python
import urllib.request, base64, json
from pathlib import Path

env = {}
for line in Path('.env').read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

PAT, ORG, PROJECT = env['AZURE_DEVOPS_PAT'], env['AZURE_DEVOPS_ORG'], env['AZURE_DEVOPS_PROJECT']
token = base64.b64encode(f':{PAT}'.encode()).decode()
headers = {'Authorization': f'Basic {token}', 'Content-Type': 'application/json-patch+json'}

item_id = {ITEM_ID}
new_state = '{STATE}'

body = json.dumps([{'op': 'replace', 'path': '/fields/System.State', 'value': new_state}]).encode()
req = urllib.request.Request(
    f'https://dev.azure.com/{ORG}/{PROJECT}/_apis/wit/workitems/{item_id}?api-version=7.1',
    data=body, headers=headers, method='PATCH'
)
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())
    print(f'Updated #{item_id} → {result["fields"]["System.State"]}')
```

Confirm the update to Chase after it runs.

---

## Behavioural rules

- **Always run the script — never guess task state from memory.** DevOps data changes constantly.
- **Code review queue gets called out explicitly** in every full summary — it's Chase's biggest
  recurring overhead.
- **Interpret, don't just dump.** Summarise counts, highlight what needs action, flag anything
  unusual (e.g. large code review backlog).
- **Suggest logging decisions** if Chase makes a notable call during a DevOps discussion (e.g.
  deferring a feature, changing priority).
- **After `/devops all`**, offer standup-ready summary: "Want me to turn this into a standup
  summary?"

---

## Credentials

Loaded from `.env` at project root — never hardcode.

```
AZURE_DEVOPS_PAT=...
AZURE_DEVOPS_ORG=MAGIQSoftware
AZURE_DEVOPS_PROJECT=Media
```

---

## Error handling

- **403 Forbidden:** PAT may be expired. Prompt Chase to regenerate at Azure DevOps →
  User Settings → Personal Access Tokens.
- **"Host not in allowlist":** Running outside Chase's network. Must run from his machine —
  org IP allowlist blocks external hosts.
- **Connection error:** Check VPN or network. Script requires access to `dev.azure.com`.
