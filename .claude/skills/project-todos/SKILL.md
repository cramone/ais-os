---
name: project-todos
description: Use to capture and work per-project todos from Claude Code without opening the Tower — add a task to a project, list a project's todos, comment, retag, change status, or delete. Triggers on "todo for [project]", "add a task to [project]", "[project] todos", "mark [todo] done for [project]", "/project-todos". Writes the same tower/data/todos/{slug}.json store the Control Tower's per-project Todos tab reads.
---

## What this skill does

Gives the Control Tower's **per-project Todos** feature CLI parity. The Tower creates and edits todos through its UI; this skill does the same from a Claude Code session, writing to the **same store** — `tower/data/todos/{slug}.json` — via the canonical helpers in `tower/interrupts/store.py`. One source of truth, no drift.

Todos share the exact item schema as Interrupts (see [[interrupt]] / [[triage]]) — same fields, same helpers — only the file differs: one JSON file per project slug under `tower/data/todos/`.

## Data model (from tower/interrupts/store.py)

- **priority:** urgent · normal · low
- **status:** new · in-progress · deferred · done
- **tags:** free-form (Tower shows them as chips)
- Optional: `dueDate` (YYYY-MM-DD). `source`/`customer`/`zendeskTicket` exist in the schema but are unused for todos.
- Each item carries an `activity` log (comments + events).

> Legacy `projects/{slug}/todos.md` is migrated into the JSON store once on first read, then ignored. Never write todos to `todos.md`.

## Steps

Run everything from repo root so `tower` is importable. The store path comes from `config.todos_file(slug)`, so you never hard-code it.

1. **Identify the project slug.** From the message; if ambiguous, ask "Which project?" A file is created on first write — you don't need the project to pre-exist a todos file.

2. **Capture a todo:**

   ```bash
   python -c "from tower.interrupts.store import create_item; from tower import config; import json; print(json.dumps(create_item(config.todos_file('SLUG'), title='TITLE', priority='normal', due_date=None)))"
   ```

   `create_item` sets id, status `new`, empty tags/activity, and timestamps. If Chase gave extra context, add it as a comment immediately (see step 4).

3. **List a project's todos:**

   ```bash
   python -c "from tower.interrupts.store import load_interrupts; from tower import config; import json; print(json.dumps(load_interrupts(config.todos_file('SLUG')), indent=2))"
   ```

   Present grouped: **Overdue** (dueDate < today, not done) · **Due today** · **Open** (new / in-progress) · **Deferred**. One line each: priority dot, title, tags, due chip, short id. Skip `done` unless asked.

4. **Act on Chase's choice** (substitute the id; all mutations go through helpers):

   - **Comment:**
     ```bash
     python -c "from tower.interrupts.store import append_activity; from tower import config; append_activity(config.todos_file('SLUG'), 'ID', 'comment', 'TEXT', author='Chase')"
     ```
   - **Status** (new · in-progress · deferred · done):
     ```bash
     python -c "from tower.interrupts.store import update_interrupt; from tower import config; update_interrupt(config.todos_file('SLUG'), 'ID', status='done')"
     ```
   - **Tag** — read current tags, add/remove, write back, then log an event:
     ```bash
     python -c "from tower.interrupts.store import update_interrupt; from tower import config; update_interrupt(config.todos_file('SLUG'), 'ID', tags=['blocked'])"
     python -c "from tower.interrupts.store import append_activity; from tower import config; append_activity(config.todos_file('SLUG'), 'ID', 'event', \"Tag 'blocked' added\")"
     ```
   - **Delete:**
     ```bash
     python -c "from tower.interrupts.store import delete_interrupt; from tower import config; delete_interrupt(config.todos_file('SLUG'), 'ID')"
     ```

5. **Confirm** each action and re-show the affected item's new state.

## Notes

- This is local JSON — no server needs to be running. The Tower picks it up on its next poll.
- Do **not** hand-edit the JSON. Always go through the store helpers so `updatedAt` and the activity log stay consistent.
- Mirrors the Hermes `project-management` skill's `§ Todo` section (`references/hermes-skills/project-management/SKILL.md`) — same schema, same store — so todo ops are identical across CLI, Desktop, and Hermes.
- Related: [[interrupt]] / [[triage]] (same schema, sprint-interrupt store), `/decision` when a todo resolution yields a call worth logging.
