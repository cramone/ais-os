# Hermes Integration — AIS-OS Context

## What Hermes Is
Docker-based background agent (`hermes` + `hermes-dashboard` containers) running locally.
Job: capture notes/ideas/risks/decisions when away from desk, run scheduled cron tasks, and bridge messaging platforms.

## Current model — Hermes writes directly into the AIS-OS repo
Hermes mounts the AIS-OS repo into the container and writes captures **straight into it**:

| Host | Container |
|---|---|
| `C:\Users\chase\.hermes` | `/opt/data` |
| `C:\Users\chase\OneDrive\Magiq\AIS-OS` | `/workspace/ais-os` |

So a Hermes skill writing to `/workspace/ais-os/projects/[slug]/` lands directly in `projects/[slug]/` of this repo — no JSON handoff, no sync step.

- Project captures → `projects/[slug]/` (`todos.md`, `notes.md`, `risks.md`, etc.)
- Adhoc notes → `context/adhoc-notes.md`

> **Retired (do not rebuild):** the old `~/.hermes/data/` handoff — `ado-pending.json`, `adhoc-notes.md`, `projects/[slug]/*.json` — and the AIS-OS `ado-flush` / `project-scaffold` / `project-sync` / `project-review` skills that drained it. The data dir is empty; the pipeline is gone because Hermes writes the repo directly.

## Tool split
| Tool | Role |
|---|---|
| **Hermes (Docker)** | Capture (notes/ideas/risks/decisions), morning digest, cron tasks, messaging bridge — writes into the AIS-OS repo |
| **Claude Code (AIS-OS)** | ADO reads/writes (via `azure-devops` MCP), spec/architecture work, execution |
| **Control Tower** | Local dashboard — ADO sprint (script), GitHub PRs, interrupts, decisions, standup, Claudia chat |

## Hermes skills (capability-area, in `~/.hermes/skills/`)
Reorganized from granular per-action skills into capability umbrellas. Notable ones:

| Skill | What it covers |
|---|---|
| `project-management` | Umbrella: create/update projects, capture decisions/risks/ideas/questions/removals, todo capture, work-planner. Targets `/workspace/ais-os/projects/[slug]/`. |
| `adhoc-capture` | "remember this" → appends `/workspace/ais-os/context/adhoc-notes.md` |
| `morning-digest` | 8am cross-project summary |
| `devops` | DevOps automation (e.g. webhook subscriptions for event-driven runs) |
| `software-development`, `github`, `messaging`, `research`, `media`, … | Domain capability areas |

> The AIS-OS `references/hermes-skills/` folder holds reference copies of selected skills; treat `~/.hermes/skills/` as the source of truth and reconcile when they drift.

## Hermes MCP connection (Claude Code)
Config in `AIS-OS/.claude/settings.json`:
```json
{ "mcpServers": { "hermes": { "command": "docker", "args": ["exec", "-i", "hermes", "hermes", "mcp", "serve"] } } }
```
Exposes a messaging bridge (`messages_send`, `conversations_list`, `events_poll`, `events_wait`, …). Available to Claude Code; the Tower does not currently use it (it reads the repo files Hermes writes).

## ADO access
ADO is **not** captured through Hermes data files anymore. See `connections.md` → "ADO access paths":
- Tower dashboard → `scripts/devops_summary.py`
- Claude Code → `azure-devops` MCP (`.mcp.json`, gitignored)
- Tower interrupt push → ADO REST (`tower/interrupts/ado_push.py`)

ADO writes originate from the local machine (org IP allowlist). Whether the Hermes container itself can reach ADO is gated by that allowlist — verify before relying on Hermes to create work items directly.

## Control Tower ↔ Hermes
- Per-project captures Hermes writes (`projects/[slug]/todos.md`, `notes.md`) surface in the Tower via the project todos/notes panels.
- The Tower's old Hermes inbox / adhoc / sync views were removed (they read the now-dead `~/.hermes/data` paths).
- Health: the Tower's `/api/health` reports `claudia` = the `hermes` container being up (`docker ps`).

## Constraints
- Model: Haiku for all Hermes cron/background runs.
- Outlook/Teams: blocked by org app registration — comms triage stays manual.
- The Claude.ai bash tool runs as `root` in an isolated container — do **not** use it to write files for Hermes. Use `docker exec` (via Cowork, which runs in Chase's shell) for Hermes; use Claude Code / Desktop Commander for AIS-OS.

## Cron schedule
| Job | Schedule | Model |
|---|---|---|
| Morning digest | 8am weekdays | Haiku |
| (others as configured in Hermes) | — | Haiku |
