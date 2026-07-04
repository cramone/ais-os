---
name: project-management
description: |
  Class-level umbrella for all AIS-OS project lifecycle operations: create, update,
  capture decisions, risks, ideas, questions, and removal flags. Use when Chase gives
  any project-related instruction containing a project slug. Each labeled section
  maps to a formerly separate skill.
triggers:
  - "new project"
  - "start a project"
  - "create project"
  - "new initiative"
  - "decided on [project]"
  - "going with [approach] for [project]"
  - "decision for [project]"
  - "we have chosen [X] for [project]"
  - "confirmed for [project]"
  - "settled on [project]"
  - "idea for [project]"
  - "what if [project]"
  - "thinking about [project]"
  - "could we add to [project]"
  - "question about [project]"
  - "not sure about [project]"
  - "need to figure out for [project]"
  - "open question for [project]"
  - "still unclear on [project]"
  - "unresolved: [project]"
  - "remove from [project]"
  - "drop [thing] from [project]"
  - "scratch [thing] for [project]"
  - "out of scope for [project]"
  - "cut [thing] from [project]"
  - "no longer need [thing] in [project]"
  - "risk for [project]"
  - "concern about [project]"
  - "worried about [project]"
  - "potential problem with [project]"
  - "flag a risk for [project]"
  - "watch out for [project]"
  - "update [project]"
  - "change [project]"
  - "revise [project]"
  - "actually for [project]"
  - "correction for [project]"
  - "amend [project]"
---

# Project Management

A single skill for every AIS-OS project lifecycle action. All operations target
`/mnt/shared/claudia/magiq/projects/[slug]/`.

## Shared routing — apply every time

1. Identify the project slug from the message. If ambiguous, ask "Which project?"
2. Check `/mnt/shared/claudia/magiq/projects/[slug]/` exists.
   - If not: "No project [slug] found. Create it first with a new project [name]."
   - Exception: see § Create below.
3. Extract the listed fields from the message. Do not prompt for missing fields unless noted.
4. Confirm with the exact phrase shown in the section.

## § Todo Capture
Retired sibling `todo-capture` is archived here. Capture a todo item with a heading and message body. General todos go to AIS-OS context; project-specific todos go to the project folder.

## § Work Planner
Retired sibling `work-planner` is archived here. Take an unordered list of work items for a project, order them by dependency, assign branches and PRs, and optionally create Azure DevOps work items.

## § Create

**Trigger phrases:** "new project", "start a project", "create project", "new initiative"

### Extracted fields

| Field | Default |
|---|---|
| `slug` | Lowercase, hyphenated — required |
| `displayName` | required |
| `description` | required |
| `stack` | null |
| `modules` | [] |
| `adoBoard` | null |
| `integrations` | null |
| `priority` | "Medium" |

If the project name is ambiguous, ask "What should I call this project?"
For all other missing fields, leave null/empty — do not ask.

### Post-existence check

If `/mnt/shared/claudia/magiq/projects/[slug]/` already exists, stop:
"Project [slug] already exists. Use update [slug] to add information."

### Files to scaffold

**CLAUDE.md**
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
```

**brief.md**
```
# [displayName]
_Captured: [ISO timestamp]_

## Description
[description]

## Stack
[stack or "TBD"]

## Modules
[modules or "TBD"]

## Integrations
[integrations or "None yet"]

## ADO Board
[adoBoard or "Not yet assigned"]

## Priority
[priority]
```

**MEMORY.md**
```
# Memory — [slug]
_Last updated: [YYYY-MM-DD]_

## Memory
<!-- Persistent — only remove or change if Chase asks. -->

- **Q2 priorities**: [infer from context or "TBD"]
```

**notes.md** — empty with `# Notes — [displayName]`
**risks.md** — empty with `# Risks — [displayName]`
**decisions/log.md** — empty with `# Decision Log — [displayName]`
Also create `decisions/` and `adrs/` and `spec/` directories.

### Confirmation
```
✅ Project "[displayName]" created.
Slug: [slug]
Location: /mnt/shared/claudia/magiq/projects/[slug]/
```

### Notes
- `slug` must be lowercase, hyphenated.
- Never call ADO API.

## § Decision

**Trigger phrases:** "decided on [project]", "going with [approach] for [project]", "decision for [project]", "we have chosen [X] for [project]", "confirmed for [project]", "settled on [project]"

### Extracted fields
- `title` — 5-8 words, inferred
- `decision` — verbatim
- `rationale` — verbatim or null
- `alternatives` — verbatim or null
- `adrCandidate` — true if architecture/technology/pattern/infrastructure; else false

### Append to `decisions/log.md`
```
## [title]
_Captured: [ISO timestamp]_
ADR candidate: [Yes/No]

**Decision:** [decision]

**Rationale:** [rationale or "Not captured"]

**Alternatives considered:** [alternatives or "Not captured"]

---
```

### Confirmation
```
Decision captured for "[slug]": [title]
```
If `adrCandidate`: append `"Flagged as ADR candidate — formalise in adrs/ when ready."`

### Notes
- Do not ask for missing fields.
- Create `decisions/log.md` first if missing.

## § Idea

**Trigger phrases:** "idea for [project]", "what if [project]", "thinking about [project]", "could we add to [project]", "for [project], what about"

### Extracted fields
- `title` — 5 words max, inferred
- `idea` — verbatim
- `module` — inferred or null

### Append to `ideas.md`
```
## [title]
_Captured: [ISO timestamp]_
Module: [module or "unassigned"]

[idea — verbatim]

---
```

### Confirmation
```
Idea captured for "[slug]": [title]
```

### Notes
- Low friction. Never create ADO items from ideas.
- Multiple ideas in one message = multiple entries.
- Create `ideas.md` first if missing.

## § Question

**Trigger phrases:** "question about [project]", "not sure about [project]", "need to figure out for [project]", "open question for [project]", "still unclear on [project]", "unresolved: [project]"

### Extracted fields
- `question` — verbatim
- `context` — or null
- `blocking` — inferred (true/false), default false

### Append to `questions.md`
```
## [short question label — infer 5 words max]
_Captured: [ISO timestamp]_
Blocking: [Yes/No]

**Question:** [question verbatim]

**Context:** [context or "None given"]

**Resolution:** _Open_

---
```

### Confirmation
```
Question captured for "[slug]"
```
If blocking: append `"⚠ BLOCKING"`

### Notes
- Never answer it.
- Create `questions.md` first if missing.

## § Remove

**Trigger phrases:** "remove from [project]", "drop [thing] from [project]", "scratch [thing] for [project]", "out of scope for [project]", "cut [thing] from [project]", "no longer need [thing] in [project]"

### Extracted fields
- `target` — what to remove
- `reason` — verbatim or null
- `scope` — affected file/area (infer if possible)

### Append to `removals.json`
Create the file as a JSON array `[]` first if missing. Append:
```json
{
  "id": "[uuid]",
  "capturedAt": "[ISO timestamp]",
  "target": "[what to remove]",
  "reason": "[reason or null]",
  "scope": "[affected area]",
  "status": "pending"
}
```

### Confirmation
```
Removal flagged for "[slug]": [target]
Review removals.json and apply manually when ready.
```

### Notes
- NEVER delete or modify any existing file. Only write to `removals.json`.
- `status` is always "pending".
- Confirm first if the request could affect real data.

## § Risk

**Trigger phrases:** "risk for [project]", "concern about [project]", "worried about [project]", "potential problem with [project]", "flag a risk for [project]", "watch out for [project]"

### Extracted fields
- `title` — 5 words max, inferred
- `description` — verbatim
- `impact` — High/Medium/Low, default Medium
- `likelihood` — High/Medium/Low, default Medium
- `mitigation` — or null

### Append to `risks.md`
```
## [title]
_Captured: [ISO timestamp]_
Impact: [impact] | Likelihood: [likelihood]

**Risk:** [description]

**Mitigation:** [mitigation or "TBD"]

---
```

### Confirmation
```
Risk captured for "[slug]": [title] ([impact] impact)
```

### Notes
- Create `risks.md` first if missing.

## § Update

**Trigger phrases:** "update [project]", "change [project]", "revise [project]", "actually for [project]", "correction for [project]", "amend [project]"

### Extracted fields
- `field` — one of: description, stack, modules, integrations, adoBoard, priority, status, general
- `change` — the new information, verbatim

### Routing

**Simple fields** (priority, adoBoard, status):
- Update value directly in `brief.md` and `CLAUDE.md`.
- Confirm: `✅ [field] updated for "[slug]": [new value]`

**Complex change** (description, stack, modules, integrations, or general):
- Append to `notes.md`:
```
## Update — [field]
_Captured: [ISO timestamp]_

[change — verbatim]

---
```
- Confirm: `Update noted for "[slug]" ([field]). Review notes.md to apply to spec files.`

### Notes
- One entry per message — if multiple changes, handle each separately.
- Never modify spec files directly.
- Create `notes.md` first if missing.
