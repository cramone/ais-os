# Connections

Registry of every system your AIOS can reach. Filled by `/onboard` from Q4-Q7 answers; expanded over time as you wire new tools. `/audit` checks this file for domain coverage and freshness.

| # | Domain | Tool | Mechanism | Auth | Last checked |
|---|---|---|---|---|---|
| 1 | Revenue / Financials | N/A — not in scope for this role | — | — | — |
| 2 | Customer interactions | Microsoft Teams | not yet connected | — | — |
| 3 | Calendar | Outlook Calendar | not yet connected | — | — |
|| 9 | Code hosting | GitHub | `gh` CLI (HTTPS, PAT, `cramone`) | PAT | 2026-06-02 |
| 4 | Communication | Outlook (email) + Microsoft Teams | not yet connected | — | — |
| 5 | Project / task tracking | Azure DevOps | `mcp` (`azure-devops` in `.mcp.json`, gitignored) for interactive Claude Code + `key+ref` (`scripts/devops_summary.py` + `.env`) for the Tower | PAT | 2026-06-26 |
| 6 | Meeting intelligence | Notion | `key+ref` (`NOTION_TOKEN` + `references/notion-api.md`) | Internal integration token | 2026-05-03 |
| 7 | Knowledge / files | Notion + AIS-OS projects/ | `key+ref` (`NOTION_TOKEN` + `references/notion-api.md`) | Internal integration token | 2026-05-03 |
| 8 | Multi-platform messaging + capture | Hermes | `mcp` (Docker stdio — `docker exec -i hermes hermes mcp serve`, in `.claude/settings.json`) + direct write into the AIS-OS repo (mounted at `/workspace/ais-os`) | None (local Docker container) | 2026-06-26 |

**Mechanism options:** `mcp` (MCP server), `script` (Python/Bash hitting an API, in `scripts/`), `export` (CSV/JSON dump pipeline), `key+ref` (`.env` key + `references/{tool}-api.md` guide), `not yet connected`.

When you wire a new tool, also save `references/{tool}-api.md` capturing endpoints, auth flow, and common queries — researched-once-saved-forever.

## ADO access paths (deliberate split)

| Surface | Mechanism | Why |
|---|---|---|
| Control Tower (dashboard) | `scripts/devops_summary.py` → JSON, 300s cache | Headless web server; no MCP in-process |
| Claude Code (interactive) | `azure-devops` MCP (`wit_*` / `work_*` tools) | Rich read/write, item creation, queries |
| Tower interrupt → ADO | ADO REST (`tower/interrupts/ado_push.py`) from local machine | One-click push of a captured interrupt |

All ADO writes originate from the local machine (org IP allowlist). The PAT lives only in `.env` and the gitignored `.mcp.json` — never in a tracked file.
