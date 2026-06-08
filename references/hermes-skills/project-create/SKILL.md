---
name: project-create
description: Capture a new project brief from natural language and scaffold the project folder directly in AIS-OS. Use when Chase says "new project", "start a project", "create project", or describes a new initiative.
triggers:
  - "new project"
  - "start a project"
  - "create project"
  - "new initiative"
---

## Purpose
Capture a new project from natural language and scaffold the full project folder directly in `/workspace/ais-os/projects/[slug]/`.

## Procedure

1. Extract from the user message:

| Field | How to extract | Default |
|---|---|---|
| slug | Lowercase, hyphenated project name | required |
| displayName | Human-readable name | required |
| description | What it does and why it exists | required |
| stack | Technologies, frameworks, cloud services | null |
| modules | Bounded contexts or modules | [] |
| adoBoard | Azure DevOps board name | null |
| integrations | Other systems it connects to | null |
| priority | High / Medium / Low | "Medium" |

If project name is ambiguous, ask: "What should I call this project?"
For all other missing fields — leave null/empty, do not ask.

2. Check `/workspace/ais-os/projects/[slug]/` exists. If found:
   "Project [slug] already exists. Use update [slug] to add information."
   Do not overwrite.

3. Create the project folder and files at `/workspace/ais-os/projects/[slug]/`:

**CLAUDE.md** — project operating manual:
```
# [displayName]

## Project Overview
[description]

**Current status:** Draft

## Stack
[stack or "TBD"]

## Modules
[modules — one per line with dash prefix, or "TBD"]

## Integrations
[integrations or "None yet"]

## ADO Board
[adoBoard or "Not yet assigned"]

## Priority
[priority]

## File Map

| File | Purpose |
|------|---------|
| brief.md | Project summary and constraints |
| notes.md | Open question resolutions and session notes |
| risks.md | Risk register |
| decisions/log.md | Architecture and design decisions (append-only) |
| adrs/ | Formal ADRs for architectural decisions |
| spec/ | Spec files |

## Decisions

All architecture and design decisions go in decisions/log.md.
Formal ADRs go in adrs/.

---

## Memory System

This folder contains MEMORY.md — your external memory for this project.

At the start of every session: Read MEMORY.md before responding. Use what you find — do not announce it.

Memory is user-triggered only. Only add entries when Chase explicitly asks using phrases like
"remember this", "make a note", "log this", "save this". Write immediately and confirm.

All memories are persistent until Chase explicitly asks to remove or change them.

Flag contradictions — never silently overwrite.
```

**brief.md**:
```
# [displayName]
_Captured: [ISO timestamp]_

## Description
[description]

## Stack
[stack or "TBD"]

## Modules
[modules — one per line with dash prefix]

## Integrations
[integrations or "None yet"]

## ADO Board
[adoBoard or "Not yet assigned"]

## Priority
[priority]
```

**MEMORY.md**:
```
# Memory — [slug]
_Last updated: [YYYY-MM-DD]_

## Memory
<!-- Persistent — only remove or change if Chase asks. -->

- **Q2 priorities**: [infer from context or "TBD"]
```

**notes.md** — empty file with header: `# Notes — [displayName]`

**risks.md** — empty file with header: `# Risks — [displayName]`

**decisions/log.md** — empty file with header: `# Decision Log — [displayName]`

4. Confirm:
```
✅ Project "[displayName]" created.
Slug: [slug]
Location: /workspace/ais-os/projects/[slug]/
```

## Notes
- slug must be lowercase, hyphenated, no spaces or special characters.
- Create `decisions/` subdirectory for the log.md file.
- Never call ADO API.
