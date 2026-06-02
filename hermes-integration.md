# Hermes Integration — AIS-OS Context

## What Hermes Is
Docker-based background agent (nousresearch/hermes-agent) running locally at `~/.hermes`.
Job: capture notes when away from desk + run scheduled cron tasks.
Does NOT touch ADO directly — org IP allowlist blocks cloud-origin calls.

## Tool Split
| Tool | Role |
|---|---|
| **Hermes (Docker)** | Note capture, morning digest, cron tasks, spec idea capture |
| **Claude Code (AIS-OS)** | ADO reads/writes, spec drafting, architecture, execution |
| **Claude Desktop** | Optional — non-ADO cloud tasks only |

## Key Constraints
- ADO API: local-only. All ADO access stays in Claude Code on local machine.
- Outlook/Teams: blocked by org app registration. Comms triage = manual capture only.
- API-first policy: MCP only where it provides unique capability (Hermes session/memory bridge).
- Model cost: Haiku for all Hermes cron; Sonnet for interactive Claude Code sessions.

## Hermes MCP Connection (Claude Code)
Config in `AIS-OS/.claude/settings.json`:
```json
{ "mcpServers": { "hermes": { "command": "docker", "args": ["exec", "-i", "hermes", "hermes", "mcp", "serve"] } } }
```

## Hermes Skills (`~/.hermes/skills/`)

### Utility skills
| Skill | Trigger phrases | Output |
|---|---|---|
| `ado-note-capture` | "note that", "add a story/task", "add to backlog" | `~/.hermes/data/ado-pending.json` |
| `adhoc-capture` | "remember this", "note that", "keep in mind", "make a note", "for later" | `~/.hermes/data/adhoc-notes.md` |
| `morning-digest` | 8am cron / "morning digest" | Cross-project pending summary |
| `comms-triage` | "flag this", "follow up on", "remind me about" | `~/.hermes/data/flagged-comms.json` |
| `project-status` | "project summary", "what's pending" | Cross-project read from Hermes data |

### Project management skills
| Skill | Trigger phrases | Output |
|---|---|---|
| `project-create` | "new project", "start a project", "create project" | `~/.hermes/data/projects/[slug]/manifest.json` + `brief.md` |
| `project-update` | "update [project]", "change [project]", "revise [project]" | `~/.hermes/data/projects/[slug]/updates.json` |
| `project-idea` | "idea for [project]", "what if [project]", "thinking about [project]" | `~/.hermes/data/projects/[slug]/ideas.md` |
| `project-remove` | "remove from [project]", "drop [thing] from [project]", "scratch [thing]" | `~/.hermes/data/projects/[slug]/removals.json` |
| `project-risk` | "risk for [project]", "concern about [project]", "worried about [project]" | `~/.hermes/data/projects/[slug]/risks.md` |
| `project-decision` | "decided on [project]", "going with [approach] for [project]" | `~/.hermes/data/projects/[slug]/decisions.md` |
| `project-question` | "question about [project]", "not sure about [project]", "need to figure out" | `~/.hermes/data/projects/[slug]/questions.md` |

> `spec-draft-capture` is retired — replaced by the project management skills above.

## AIS-OS Skills (Claude Code)
| Skill | Trigger | What it does |
|---|---|---|
| `ado-flush` | "flush pending notes" | Reads Hermes ado-pending.json → shows list → creates in ADO on confirmation → marks `status: created` |
| `project-scaffold` | "scaffold project [slug]" | Reads Hermes brief + manifest → creates full project folder in `projects/` → registers in EXPANSIONS.md |
| `project-sync` | "sync project [slug]" | Reads all pending Hermes captures for a project → presents grouped → applies on confirmation |
| `project-review` | "review project [slug]" | Read-only status summary — open questions, risks, pending ideas, unsynced Hermes captures |

## Capture → Flush Workflow
1. Hermes captures note → `ado-pending.json` (status: pending)
2. Open Claude Code → `flush pending notes`
3. ado-flush skill shows grouped list → confirm → creates in ADO → marks done

## Key Workflows in Claude Code
| Command | What happens |
|---|---|
| `/devops` | Live ADO sprint status via `devops_summary.py` |
| `flush pending notes` | Triggers ado-flush |
| `/devops all` | Team view grouped by assignee |
| "Read my Hermes morning digest + live ADO view" | Combined start-of-day view |

## Cron Schedule
| Job | Schedule | Model |
|---|---|---|
| Morning digest | 8am weekdays | Haiku |
| Weekly backlog summary | 9am Monday | Haiku |
| Stale item check | 5pm Friday | Haiku |
| Project health check | 9am Wednesday | Haiku |

## Data Files
- `~/.hermes/data/ado-pending.json` — captured ADO items (status: pending → created)
- `~/.hermes/data/adhoc-notes.md` — free-form notes/memory for Claude Code (append-only)
- `~/.hermes/data/flagged-comms.json` — comms follow-ups
- `~/.hermes/USER.md` — Hermes identity/project registry (mirrors AIS-OS context)
- `~/.hermes/data/projects/[slug]/manifest.json` — project metadata (slug, stack, modules, ADO board, priority, status)
- `~/.hermes/data/projects/[slug]/brief.md` — project description captured from natural language
- `~/.hermes/data/projects/[slug]/updates.json` — pending spec/brief updates (status: pending → applied)
- `~/.hermes/data/projects/[slug]/removals.json` — pending removal flags (status: pending → applied/skipped)
- `~/.hermes/data/projects/[slug]/ideas.md` — loose ideas and "what if" captures
- `~/.hermes/data/projects/[slug]/risks.md` — risk captures pending sync to AIS-OS
- `~/.hermes/data/projects/[slug]/decisions.md` — decision captures pending sync to AIS-OS
- `~/.hermes/data/projects/[slug]/questions.md` — open question captures pending sync to AIS-OS

> `~/.hermes/data/spec-ideas/` is retired — project data now lives under `~/.hermes/data/projects/[slug]/`.

## ADO Pending Item Schema
```json
{ "id": "<uuid>", "capturedAt": "<ISO>", "project": "magiq-media", "type": "Story",
  "module": "AssetManagement", "title": "...", "description": "...",
  "acceptanceCriteria": ["..."], "priority": "Medium", "assignee": null, "status": "pending" }
```

## Docker Path Notes

Inside Docker: `~/.hermes` → symlink → `/opt/data` → `C:\Users\chase\.hermes` (Windows volume).  
All skill writes to `~/.hermes/data/` persist correctly via this symlink.  
Claude Code reads from `C:\Users\chase\.hermes\data\` — same location.

## Rollout Status (reference)
Week 1: Docker + Hermes setup, USER.md, ado-note-capture + morning-digest skills, MCP wired
Week 2: ado-flush skill, cron jobs, spec-draft-capture + comms-triage
Week 3: project-status skill, MEMORY.md for magiq-media, connections.md + EXPANSIONS.md updated
Week 4: spec-draft-capture retired → project management skill suite (project-create/update/idea/remove/risk/decision/question), AIS-OS scaffold/sync/review skills added
Week 5: USER.md created, data dirs initialised, ~/.hermes symlinked to /opt/data, adhoc-capture skill added