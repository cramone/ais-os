# Hermes Integration — magiq folder Context

## What Hermes Is
Persistent agent framework. **As of 2026-07-04, the Docker-based install on the Windows PC (`hermes` + `hermes-dashboard` containers, described in "Retired setup" below) is retired.** The active work-profile agent is now **Claudia**, a bare-metal Hermes profile running on the `cortex` server (see [[cortex]]). Job (unchanged): capture notes/ideas/risks/decisions when away from desk, run scheduled cron tasks, bridge messaging platforms.

## Current model — Claudia writes directly into the magiq folder
Claudia's `terminal.cwd` is the magiq folder itself — `/mnt/shared/claudia/magiq/` (= `Z:\claudia\magiq` on Windows). No container mount, no path translation:

| Surface | Path |
|---|---|
| Windows (file tools, Explorer) | `Z:\claudia\magiq\` |
| Cortex / Claudia | `/mnt/shared/claudia/magiq/` |

A Claudia skill writing to `projects/[slug]/` lands directly in this repo — no JSON handoff, no sync step, no Docker mount indirection.

- Project captures → `projects/[slug]/` (`todos.md`, `notes.md`, `risks.md`, etc.)
- Adhoc notes → `context/adhoc-notes.md`

> **Retired (do not rebuild):** the old `~/.hermes/data/` handoff (`ado-pending.json`, `adhoc-notes.md`, `projects/[slug]/*.json`) and the `ado-flush` / `project-scaffold` / `project-sync` / `project-review` skills that drained it. Also retired: the Windows Docker Hermes install itself — see "Retired setup" below.

## Tool split
| Tool | Role |
|---|---|
| **Claudia (bare-metal, cortex)** | Capture (notes/ideas/risks/decisions), morning digest, cron tasks, messaging bridge (Telegram) — writes directly into the magiq folder |
| **Claude Code (magiq folder)** | ADO reads/writes (via `azure-devops` MCP), spec/architecture work, execution |
| **Control Tower** | Local dashboard — ADO sprint (script), GitHub PRs, interrupts, decisions, standup, Claudia chat |

## Claudia's skills (capability-area, in `~/.hermes/profiles/claudia/skills/`)
Reorganized from granular per-action skills into capability umbrellas. Notable ones:

| Skill | What it covers |
|---|---|
| `project-management` | Umbrella: create/update projects, capture decisions/risks/ideas/questions/removals, todo capture, work-planner. Targets `/mnt/shared/claudia/magiq/projects/[slug]/`. |
| `adhoc-capture` | "remember this" → appends `/mnt/shared/claudia/magiq/context/adhoc-notes.md` |
| `morning-digest` | 8am cross-project summary |
| `devops` | DevOps automation (e.g. webhook subscriptions for event-driven runs) |
| `software-development`, `github`, `messaging`, `research`, `media`, … | Domain capability areas |

> `references/hermes-skills/` in this repo holds reference copies of selected skills — used as the install source for fresh Claudia setups (see the setup guide's §15.3b). **Reconciled 2026-07-04** against the live profile: holds `adhoc-capture`, `agenda-generator`, `morning-digest`, `project-management` (the current umbrella, replacing the old granular per-action skills). `github-my-prs` is also kept here but is restore-only — not currently installed on Claudia. `devops/webhook-subscriptions` is deliberately not tracked here (no path deps, no drift risk).

## Hermes MCP connection (Claude Code)
Config in `magiq/.claude/settings.json` — **stale, needs re-verification** now that the Docker Hermes is retired; the below assumed the Docker container:
```json
{ "mcpServers": { "hermes": { "command": "docker", "args": ["exec", "-i", "hermes", "hermes", "mcp", "serve"] } } }
```
If Claude Code still needs the messaging bridge (`messages_send`, `conversations_list`, `events_poll`, `events_wait`, …), this needs to be repointed at Claudia's bare-metal gateway on cortex instead of a local Docker exec. Not yet done — flag as an open item.

## Retired setup (historical — Windows Docker Hermes, pre-2026-07-04)
Docker-based background agent (`hermes` + `hermes-dashboard` containers) ran locally on the Windows PC, mounting the old OneDrive AIS-OS folder into the container:

| Host | Container |
|---|---|
| `C:\Users\chase\.hermes` | `/opt/data` |
| `C:\Users\chase\OneDrive\Magiq\AIS-OS` | `/workspace/ais-os` |

Kept here for historical reference only — do not assume these containers are running or rebuild against `/workspace/ais-os` paths.

## ADO access
ADO is **not** captured through Hermes data files anymore. See `connections.md` → "ADO access paths":
- Tower dashboard → `scripts/devops_summary.py`
- Claude Code → `azure-devops` MCP (`.mcp.json`, gitignored)
- Tower interrupt push → ADO REST (`tower/interrupts/ado_push.py`)

ADO writes originate from the local machine (org IP allowlist). Whether Claudia (running on cortex) can reach ADO is gated by that allowlist — verify before relying on Claudia to create work items directly.

## Control Tower ↔ Claudia
- Per-project captures Claudia writes (`projects/[slug]/todos.md`, `notes.md`) surface in the Tower via the project todos/notes panels.
- The Tower's old Hermes inbox / adhoc / sync views were removed (they read the now-dead `~/.hermes/data` paths).
- Health: the Tower's `/api/health` "claudia" check needs re-verification — it used to check the `hermes` Docker container (`docker ps`), which no longer exists. Should instead check the bare-metal `hermes-gateway-claudia` systemd service on cortex (`systemctl --user status hermes-gateway-claudia`). Open item — see `tower/readers/claudia.py`.

## Constraints
- Model: Haiku for all Claudia/Hermes cron/background runs.
- Outlook/Teams: blocked by org app registration — comms triage stays manual.
- The Claude.ai bash tool runs as `root` in an isolated container — do **not** use it to write files intended for Claudia/Hermes on cortex. Use SSH/`docker exec` via Cowork (which runs in Chase's actual shell session) for cortex; use Claude Code / native file tools for the magiq folder directly.

## Cron schedule
| Job | Schedule | Model |
|---|---|---|
| Morning digest | 8am weekdays | Haiku |
| (others as configured in Hermes) | — | Haiku |
