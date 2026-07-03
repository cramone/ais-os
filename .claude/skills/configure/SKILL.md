---
name: configure
description: Use to set up or update the AIS-OS runtime environment — the .env secrets, .mcp.json MCP servers, and aios.config.md operator identity. Triggers on "configure env", "set up my environment", "fill in .env", "wire up secrets", "configure AIS-OS", "set my API keys", "onboard day 2", "/configure", or on a fresh clone after /onboard. Idempotent — re-run any time to add or rotate variables.
---

## What this skill does

Interactive config walk. Prompts the operator for every runtime variable AIS-OS needs, then writes the three per-machine files:

1. `.env` — secrets + external paths (gitignored)
2. `.mcp.json` — MCP server wiring (gitignored)
3. `aios.config.md` — operator identity (tracked, but per-operator)

This is the **Day-2** counterpart to `/onboard`. `/onboard` establishes *who you are* (identity, voice, priorities). `/configure` establishes *how the machine runs* (keys, tokens, paths). Internal repo paths self-locate — this skill never asks for them.

## Source of truth

`.env.example` and `.mcp.json.example` are the variable manifest. **Read them first** — they list every variable, which are required, and their defaults. Do not hardcode a variable list in this skill; derive it from those files so the walk stays in sync as they change.

## Critical rules

1. **Write with native file tools only** (Write/Edit — Desktop Commander runs as the operator). NEVER write `.env`, `.mcp.json`, or `aios.config.md` via the bash tool — bash runs as `root` in an isolated container and the files land unreadable to Docker/the operator (see CLAUDE.md → Environment constraints).
2. **Never commit `.env` or `.mcp.json`.** Both are gitignored. If either is somehow tracked, stop and warn.
3. **Never echo a full secret back.** When confirming an existing value, show only a masked preview (`sk-ant-…7Yg`, last 3-4 chars). When the operator provides a new one, confirm receipt without reprinting it.
4. **Idempotent.** If a file exists, read it, show what's set (masked), and only prompt for missing/blank vars — unless the operator says "rotate" or "redo".
5. **Skippable optionals.** Required vars block; optional vars can be left blank. Mark each clearly.
6. **No secret rotation advice unless asked** — but if a secret was ever pasted into a tracked file or git history, flag it.

## Execution

### Step 1 — Read the manifest and current state

Read, in parallel:
- `.env.example` and `.env` (if exists)
- `.mcp.json.example` and `.mcp.json` (if exists)
- `aios.config.md` (if exists)

Build the variable list from the `.example` files. Classify each variable:
- **Required** — app breaks without it. From `.env.example`: `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`, `AZURE_DEVOPS_PAT` (if ADO used), `ANTHROPIC_API_KEY` (if brief/email drafting used). From `.mcp.json.example`: `MCP_ADO_SERVER` (if the azure-devops MCP is wanted).
- **Optional** — `TOWER_TOKEN`, `NOTION_TOKEN`, `TOWER_PORT`, `HERMES`, `HERMES_DATA`, `AIOS_ROOT`.

Report current state up front: *"`.env` exists — 5 of 8 vars set. Missing: MCP_ADO_SERVER, NOTION_TOKEN, TOWER_TOKEN."* Then walk only the gaps.

### Step 2 — Walk the variables (grouped)

Ask in small grouped batches, not one giant form. Suggested groups:

**A. Azure DevOps** (required if you track work in ADO)
- `AZURE_DEVOPS_ORG` — org name (e.g. from `dev.azure.com/<org>`)
- `AZURE_DEVOPS_PROJECT` — project name
- `AZURE_DEVOPS_PAT` — Personal Access Token. *Prompt: "Paste your ADO PAT. It'll be written to .env (gitignored) — never committed."*
- `MCP_ADO_SERVER` — absolute path to the azure-devops MCP server entry (e.g. `…/azure-devops-mcp-server/build/index.js`). Ask only if they want the ADO MCP in Claude Code.

**B. Anthropic** (required for brief / email drafting)
- `ANTHROPIC_API_KEY`

**C. Optional services**
- `NOTION_TOKEN` — only if Notion is wired
- `TOWER_TOKEN` — Control Tower API auth. Offer to generate a random one (openssl/uuid) if they want auth; blank = open localhost.

**D. Optional paths** (defaults shown — most operators skip)
- `HERMES` (default `~/.hermes`), `HERMES_DATA`, `TOWER_PORT` (default 8765), `AIOS_ROOT` (leave blank — self-locates)

For each: show the default/current (masked if secret), accept new value or "skip"/"keep".

### Step 3 — Write the files

Once the walk is done, write in one batch:

1. **`.env`** — from `.env.example` structure, filled with provided values. Preserve comments and grouping. Leave skipped optionals as empty `KEY=` (or commented, matching the example).
2. **`.mcp.json`** — if the operator gave `MCP_ADO_SERVER` and wants env-var expansion, write the `${VAR}` form from `.mcp.json.example` AND remind them Claude Code expands `${VAR}` from **shell environment, not .env** — so those vars must be exported in their shell/profile. If they prefer zero shell setup, offer the **literal** form instead: write the real path + values directly into `.mcp.json` (safe — it's gitignored, machine-local). Default to the literal form; it "just works" without shell exports.
3. **`aios.config.md`** — if it still contains a prior operator's details, confirm before overwriting. If `/onboard` was run, pull operator/priorities from `aios-intake.md` / `context/` to fill it. Otherwise prompt for: name, role, employer, product, current focus, priorities, connections.

### Step 4 — Verify and close

1. Confirm gitignore still covers `.env` and `.mcp.json`: they must NOT appear in `git status`. If they do, stop and warn loudly.
2. Print a masked summary — one line per var, value masked, status ✅ set / ⬜ skipped.
3. Closing screen (three lines max):

```
✓ Environment configured. .env + .mcp.json written (gitignored), aios.config.md set.
Restart Claude Code to load the MCP servers.
Test: start the Control Tower (tower/launch.bat) or ask me — "what's on my ADO board?"
```

## When NOT to run

- Just changing identity/priorities → edit `aios.config.md` directly, no walk needed.
- Adding a brand-new MCP server type not in `.mcp.json.example` → edit `.mcp.json` directly, then update `.mcp.json.example` so the manifest stays complete.

## Verification (for the implementer)

- Fresh clone, no `.env`: run `/configure`, provide ADO + Anthropic values, confirm `.env` written with correct keys and `.mcp.json` populated.
- Idempotency: re-run with `.env` present — only missing vars prompted, existing shown masked, no overwrite of set values.
- Secret hygiene: confirm no full secret is echoed in the transcript and `git status` shows neither `.env` nor `.mcp.json`.
