# Connections

Registry of every system your AIOS can reach. Filled by `/onboard` from Q4-Q7 answers; expanded over time as you wire new tools. `/audit` checks this file for domain coverage and freshness.

| # | Domain | Tool | Mechanism | Auth | Last checked |
|---|---|---|---|---|---|
| 1 | Revenue / Financials | N/A — not in scope for this role | — | — | — |
| 2 | Customer interactions | Microsoft Teams | not yet connected | — | — |
| 3 | Calendar | Outlook Calendar | not yet connected | — | — |
|| 9 | Code hosting | GitHub | `gh` CLI (HTTPS, PAT, `cramone`) | PAT | 2026-06-02 |
| 4 | Communication | Outlook (email) + Microsoft Teams | not yet connected | — | — |
| 5 | Project / task tracking | Azure DevOps | `key+ref` (`AZURE_DEVOPS_PAT` + `references/azure-devops-api.md`) | PAT | 2026-05-03 |
| 6 | Meeting intelligence | Notion | `key+ref` (`NOTION_TOKEN` + `references/notion-api.md`) | Internal integration token | 2026-05-03 |
| 7 | Knowledge / files | Notion + AIS-OS projects/ | `key+ref` (`NOTION_TOKEN` + `references/notion-api.md`) | Internal integration token | 2026-05-03 |
| 8 | Multi-platform messaging | Hermes | `mcp` (Docker stdio — `docker exec -i hermes hermes mcp serve`, configured in `.claude/settings.json`) | None (local Docker container) | 2026-05-28 |

**Mechanism options:** `mcp` (MCP server), `script` (Python/Bash hitting an API, in `scripts/`), `export` (CSV/JSON dump pipeline), `key+ref` (`.env` key + `references/{tool}-api.md` guide), `not yet connected`.

When you wire a new tool, also save `references/{tool}-api.md` capturing endpoints, auth flow, and common queries — researched-once-saved-forever.
