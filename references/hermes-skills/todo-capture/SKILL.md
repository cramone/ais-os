---
name: todo-capture
description: Capture a todo item for a specific project. Always requires a project. Use when Chase says "add a todo", "new todo", "todo:", "task:", "todo for [project]", or "add a task for [project]".
triggers:
  - "add a todo"
  - "new todo"
  - "todo:"
  - "task:"
  - "todo for [project]"
  - "add a task for [project]"
---

# todo-capture

## Purpose

Persist todo items to the project file system so they survive across sessions.

**Target:** `projects/[slug]/todos.md`

Todos are always project-scoped. General (non-project) todos are not supported.

Each item = a heading (≤10 words) + a message body.

---

## Procedure

### Step 1 — Detect project

Check if a known project slug appears in the message or recent conversation context.

Known slugs: check `/workspace/ais-os/projects/` for folder names.

**If no project detected → ask:**
> "Which project is this todo for?"

Wait for response. Do not proceed until project is confirmed.

If named project not found in `/workspace/ais-os/projects/` → reply:
> "No project [slug] found."
and stop.

---

### Step 2 — Extract heading and body

Parse the message into:
- **heading**: short label, ≤10 words. Infer from the first sentence or intent if not explicit.
- **body**: everything after the heading. Full detail — description, context, constraints, links. Preserve verbatim.

Format examples:

```
todo for magiq-auth: Wire up DynamoDB tenant repo
Create the ITenantRepository interface and Dynamo implementation.
Depends on the DynamoDB client being configured first.
```

```
Add a todo for magiq-media:
Write integration tests for the checkout saga
Cover: happy path, missing media item, expired checkout
```

In both cases, heading = short label, body = everything else.

---

### Step 3 — Append to project file

**Target file:** `projects/[slug]/todos.md`

If the file doesn't exist, create it with:
```
# Todos — {slug}

```

**Entry format:**
```
## [heading]
_Captured: [ISO timestamp]_

[body — verbatim]

---
```

- Heading is plain text after `## ` (no nested markdown)
- Timestamp is UTC ISO format
- Body preserves Chase's wording exactly
- Separator is `---` on its own line
- Do not number entries — just append

---

### Step 4 — Confirm

```
✅ Todo added → [slug]: [heading]
```

One line. No preamble.

---

## Rules

- **Always require a project.** If none given, ask before doing anything.
- One entry per invocation. Do not batch multiple todos silently.
- Do not modify, reorder, or delete existing entries.
- Do not mark items as done — that is a separate operational step Chase takes manually.
- Do not create or link ADO items from todos.
- If the message contains a heading + a body, use both. If only a heading is given, use heading as both and leave body as the heading text.
