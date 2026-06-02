---
name: ado-flush
description: Read pending ADO notes captured by Hermes and create them as work items in Azure DevOps. Use when Chase says "flush pending notes", "create ADO items from Hermes", or "process my pending notes".
---

## What this skill does

Reads `~/.hermes/data/ado-pending.json` via the Hermes MCP connection, presents the full list
for review, then creates confirmed items in Azure DevOps via the existing REST API pattern.
Marks executed items as `status: "created"` in the Hermes data file after confirmation.

## Procedure

1. Read pending items via Hermes MCP. Filter to `status: "pending"`.
2. Group by project, then type (Epic → Feature → Story → Task).
3. Display full list for Chase to review. Ask: "Create all [N] items? Or specify which to skip."
4. On confirmation: for each item, POST to ADO REST API using credentials from `.env`.
   - Use `AZURE_DEVOPS_PAT`, `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT` from `.env`
   - Map project key to ADO project ID (see connections.md)
5. On success: write back to `~/.hermes/data/ado-pending.json` setting `status: "created"` and
   adding `createdAt` timestamp and `adoId` (returned by API).
6. Report: "Created [N] items. [ADO IDs]."

## ADO API — Create Work Item

```python
import urllib.request, base64, json
from pathlib import Path

env = {k.strip(): v.strip() for line in Path('.env').read_text().splitlines()
       if '=' in line and not line.strip().startswith('#')
       for k, v in [line.split('=', 1)]}

PAT = env['AZURE_DEVOPS_PAT']
ORG = env['AZURE_DEVOPS_ORG']
PROJECT = env['AZURE_DEVOPS_PROJECT']  # map project key → ADO project ID

token = base64.b64encode(f':{PAT}'.encode()).decode()
headers = {
    'Authorization': f'Basic {token}',
    'Content-Type': 'application/json-patch+json'
}

work_item_type = 'User Story'  # or Task, Feature, Epic
body = json.dumps([
    {'op': 'add', 'path': '/fields/System.Title', 'value': '{TITLE}'},
    {'op': 'add', 'path': '/fields/System.Description', 'value': '{DESCRIPTION}'},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Common.Priority', 'value': 2},
]).encode()

req = urllib.request.Request(
    f'https://dev.azure.com/{ORG}/{PROJECT}/_apis/wit/workitems/${work_item_type}?api-version=7.1',
    data=body, headers=headers, method='POST'
)
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())
    print(f'Created #{result["id"]} — {result["fields"]["System.Title"]}')
```

## Notes
- Always show full list and wait for confirmation before creating anything.
- Never create items from a different project's notes without explicit confirmation.
- If Hermes MCP is not connected, read `~/.hermes/data/ado-pending.json` directly via file read.

---