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
  - "todo for [project]"
  - "add a task to [project]"
  - "[project] needs to"
  - "capture a todo for [project]"
  - "remind me to [x] for [project]"
  - "mark [todo] done for [project]"
  - "promote note to todo for [project]"
  - "turn [note] into a todo for [project]"
  - "make [note] a todo for [project]"
  - "convert [note] to a task for [project]"
  - "promote [note] for [project]"
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

## § Todo

Project-level todos are the **same feature** as the Control Tower's per-project
Todos tab. They are **not** markdown — each project's todos live as a JSON array of
items in `/mnt/shared/claudia/magiq/tower/data/todos/[slug].json`, one file per
project, using the shared interrupt/todo item schema. The Tower reads this file
directly, so a captured todo shows in the dashboard on its next poll.

> The legacy `projects/[slug]/todos.md` is migrated into this JSON once on first
> read, then left in place as a dead backup. **Never** write todos to `todos.md` —
> always write the JSON store.

**Trigger phrases:** "todo for [project]", "add a task to [project]", "[project] needs to", "capture a todo for [project]", "remind me to [x] for [project]", "mark [todo] done for [project]"

### Extracted fields
- `title` — one line, verbatim or lightly cleaned — required
- `priority` — `urgent` · `normal` · `low`, default `normal`
- `dueDate` — `YYYY-MM-DD` or null
- `note` — any extra context → becomes the first activity comment, or null

### Capture — append to `tower/data/todos/[slug].json`
Create the file as a JSON array `[]` first if missing. Append an item that matches
the schema **exactly** (the Tower and CLI ignore malformed items):
```json
{
  "id": "[uuid]",
  "title": "[title]",
  "source": "",
  "dueDate": [dueDate or null],
  "priority": "[priority]",
  "status": "new",
  "tags": [],
  "adoItemId": null,
  "zendeskTicket": null,
  "customer": null,
  "capturedAt": "[ISO timestamp]",
  "updatedAt": "[ISO timestamp]",
  "activity": [
    { "type": "comment", "text": "[note]", "author": "Chase", "timestamp": "[ISO timestamp]" }
  ]
}
```
If no `note`, use `"activity": []`.

### Status change / comment on an existing todo
Find the item by `id` (or by matching `title`) in the array, then:
- **Status:** set `status` to one of `new` · `in-progress` · `deferred` · `done` and refresh `updatedAt`.
- **Comment:** append `{ "type": "comment", "text": "…", "author": "Chase", "timestamp": "[ISO]" }` to its `activity`, refresh `updatedAt`.
- **Tag:** edit its `tags` array, refresh `updatedAt`.

### Confirmation
```
✅ Todo captured for "[slug]": [title]
```
(or `Todo updated for "[slug]": [title] → [new status]`)

### Notes
- One file per slug at `tower/data/todos/[slug].json` — NOT `projects/[slug]/todos.md`.
- `id` must be a real UUID; timestamps are ISO 8601 UTC.
- Only append or edit the targeted item — never touch other items in the array.
- Priority/status vocab matches the Interrupts feature — same schema, different store.

## § Promote (note → todo)

Turn an existing project **note** (a block in `projects/[slug]/notes.md`) into a
**todo** item in `tower/data/todos/[slug].json`, then **remove the note**. This is
the same promote the Control Tower does via the ➡️✅ button on a note — identical
result whichever surface triggers it.

**Trigger phrases:** "promote note to todo for [project]", "turn [note] into a todo for [project]", "make [note] a todo for [project]", "convert [note] to a task for [project]", "promote [note] for [project]"

### Identify the note
- Match the note by its heading (title) in `notes.md`. If the phrasing is ambiguous
  or multiple notes match, list the candidate note titles and ask which one.

### Steps (order matters — write the todo first)
1. Read the target note block from `notes.md`. Capture:
   - `title` = the note heading (the `## …` line, minus `## `)
   - `body` = everything under the heading **except** the `_Captured:` line and the
     trailing `---` separator
2. **Append the todo** to `tower/data/todos/[slug].json` (create the file as `[]`
   first if missing) using the § Todo schema **exactly**, with:
   - `title` = the note title
   - `tags` = `["from-note"]`
   - `activity` = `[ { "type": "comment", "text": "[body]", "author": "Chase", "timestamp": "[ISO]" } ]`
     (or `[]` if the note body is empty)
   - everything else as § Todo defaults (`status: "new"`, `priority: "normal"`, real UUID `id`, ISO timestamps)
3. **Only after** the todo is written, remove the note block from `notes.md` (delete
   the whole `## …` block including its `_Captured:` line and trailing `---`). Never
   remove the note before the todo exists — a failure must leave the note intact.

### Confirmation
```
✅ Promoted note → todo for "[slug]": [title] (note removed)
```

### Notes
- Never touch other note blocks or other todo items — only the one being promoted.
- One note per request. If asked to promote several, handle each separately.
- The Tower reads both stores directly, so the moved item shows in the Todos tab and
  disappears from the Notes panel on the next poll.

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
- If no title is provided, generate a brief title (5 words max) inferred from the content of the note.
- Append to `notes.md`:
```
## [title — provided or inferred from note content, 5 words max]
_Captured: [ISO timestamp]_

[change — verbatim]

---
```
- Confirm: `Update noted for "[slug]" ([field]). Review notes.md to apply to spec files.`

### Notes
- One entry per message — if multiple changes, handle each separately.
- Always write the `_Captured: [ISO timestamp]` line directly under the heading — the
  Control Tower parses it and shows the capture date on the note in the project Notes panel.
- Never modify spec files directly.
- Create `notes.md` first if missing.
