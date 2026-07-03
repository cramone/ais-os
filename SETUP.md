# AIS-OS Setup

Setting up on a new machine or as a new operator? You edit **three files**. Everything else (internal paths) self-locates — moving the folder needs zero changes.

The fastest path is to let the AIOS walk you through it:

1. **`/onboard`** — establishes identity: who you are, what you sell, priorities, voice. Writes `aios.config.md` + `context/`.
2. **`/configure`** — establishes the runtime: API keys, tokens, MCP servers. Writes `.env` + `.mcp.json`. Prompts you for every required variable.

If you'd rather do it by hand, here's the full manifest.

---

## The three files

| File | Tracked? | Holds | How |
|---|---|---|---|
| `aios.config.md` | yes (per-operator) | Operator identity, focus, priorities, connections | Edit directly, or `/onboard` |
| `.env` | **no** (gitignored) | Secrets + external paths | Copy `.env.example` → `.env`, or `/configure` |
| `.mcp.json` | **no** (gitignored) | MCP server wiring | Copy `.mcp.json.example` → `.mcp.json`, or `/configure` |

`.env` and `.mcp.json` are gitignored on purpose — they hold secrets. Never commit them.

---

## `.env` variables

Copy `.env.example` → `.env` and fill:

**Required (for the features you use):**
- `AZURE_DEVOPS_ORG` — your ADO org (`dev.azure.com/<org>`)
- `AZURE_DEVOPS_PROJECT` — your ADO project
- `AZURE_DEVOPS_PAT` — ADO Personal Access Token
- `ANTHROPIC_API_KEY` — required for brief / email draft generation

**Optional:**
- `TOWER_TOKEN` — Control Tower `/api` auth. Blank = open (localhost dev).
- `NOTION_TOKEN` — only if Notion is wired
- `MCP_ADO_SERVER` — path to azure-devops MCP server entry (only if using `${VAR}` form of `.mcp.json`)
- `TOWER_PORT` — default `8765`
- `HERMES` — Hermes home, default `~/.hermes`
- `HERMES_DATA` — Hermes projects data dir, default `/opt/data/.hermes/data/projects`
- `AIOS_ROOT` — leave unset; scripts self-locate

## `.mcp.json`

Copy `.mcp.json.example` → `.mcp.json`. Two ways to fill it:

- **Literal (simplest):** put the real MCP server path + ADO values straight in. It's gitignored/machine-local, so this is safe. Works with no shell setup.
- **`${VAR}` expansion:** keep the `${...}` placeholders. Claude Code expands them from your **shell environment** (not `.env`) at launch — so you must export `MCP_ADO_SERVER`, `AZURE_DEVOPS_*` in your shell/profile first.

`/configure` defaults to the literal form.

## `aios.config.md`

Operator identity. Edit the table + focus/priorities/connections sections. `/onboard` fills this from your intake answers.

---

## After editing

- Restart Claude Code to load MCP servers from `.mcp.json`.
- `git status` must show **neither** `.env` nor `.mcp.json`. If it does, stop — they should be gitignored.
- Start the Control Tower: `tower/launch.bat` (Windows) or `python tower/start.py`.

## Environment note (writing config files via an agent)

If an agent writes these files for you, it must use native file tools (Desktop Commander), **not** the bash tool. The bash tool runs as `root` in an isolated container; files it writes to `/mnt/c/...` land unreadable to the operator and to Docker containers. See `CLAUDE.md` → Environment constraints.
