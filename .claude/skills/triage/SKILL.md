---
name: triage
description: Use to work the interrupt queue from Claude Code — review open interrupts, comment, tag, change status, or push one to Azure DevOps as a Task. Triggers on "triage interrupts", "work my interrupts", "what's in my interrupt queue", "push this interrupt to ADO", "close that interrupt", "/triage". Reads and writes the same tower/data/interrupts.json the Control Tower uses.
---

## What this skill does

The action half of the Interrupts feature (capture is `/interrupt`). Lists the queue, then lets Chase act on any item — comment, retag, restatus, escalate to ADO — using the canonical helpers in `tower/interrupts/store.py`. Every change flows through the same store the Tower reads, so the dashboard stays in sync.

## Steps

1. **Load the queue.** Run from repo root:

   ```bash
   python -c "from tower.interrupts.store import load_interrupts; from pathlib import Path; import json; print(json.dumps(load_interrupts(Path('tower/data/interrupts.json')), indent=2))"
   ```

2. **Present it triaged.** Group by urgency, newest signal first: **Overdue** (dueDate < today, status ≠ done) · **Due today** · **Open** (new / in-progress) · **Deferred**. One line each: priority dot, title, source, tags, due chip, short id. Skip `done` unless asked.

3. **Act on Chase's choice.** All mutations go through store helpers (run from repo root, substitute the id):

   - **Comment:**
     ```bash
     python -c "from tower.interrupts.store import append_activity; from pathlib import Path; append_activity(Path('tower/data/interrupts.json'), 'ID', 'comment', 'TEXT', author='Chase')"
     ```
   - **Tag** (built-ins: blocked · waiting-for-feedback · requested-review · needs-more-info · complete; custom allowed). Read current tags, add/remove, then:
     ```bash
     python -c "from tower.interrupts.store import update_interrupt; from pathlib import Path; update_interrupt(Path('tower/data/interrupts.json'), 'ID', tags=['blocked','waiting-for-feedback'])"
     ```
     Also append an event so the activity feed records it:
     ```bash
     python -c "from tower.interrupts.store import append_activity; from pathlib import Path; append_activity(Path('tower/data/interrupts.json'), 'ID', 'event', \"Tag 'blocked' added\")"
     ```
   - **Status** (new · in-progress · deferred · done):
     ```bash
     python -c "from tower.interrupts.store import update_interrupt; from pathlib import Path; update_interrupt(Path('tower/data/interrupts.json'), 'ID', status='done')"
     ```

4. **Push to ADO** (when Chase says escalate/promote to a work item). Use the **azure-devops MCP** (Claude Code already has it — cleaner than the Tower's REST helper, no PAT juggling):
   - Create a Task via `wit_create_work_item`: title `[Interrupt] {title}`, description `Source: {source}. Captured: {capturedAt}.` followed by the joined comment activity.
   - Take the returned work-item id and write it back so the Tower shows "View in ADO" instead of "Push":
     ```bash
     python -c "from tower.interrupts.store import update_interrupt; from pathlib import Path; update_interrupt(Path('tower/data/interrupts.json'), 'ID', adoItemId=12345)"
     ```
   - Append an event: `Pushed to ADO as #12345`.

5. **Confirm** each action taken and re-show the affected item's new state.

## Notes

- Never hand-edit `interrupts.json` — the store helpers keep `updatedAt` and the activity log honest.
- Email drafts stay a Tower feature (needs the browser + template/tone UI) — don't reimplement here.
- Related: [[interrupt]] to capture, `/decision` when a resolution yields a call worth logging, `/standup-rollup` which already folds open interrupts into the blockers column.
