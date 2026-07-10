---
name: interrupt
description: Use to capture an interrupt — an unplanned request that competes with sprint focus (support escalation, exec ask, finance/product request) — from Claude Code without opening the Tower. Triggers on "capture an interrupt", "log an interrupt", "something just came in", "add to interrupts", "/interrupt". Writes straight into the same tower/data/interrupts.json the Control Tower reads, so it shows up in the dashboard immediately.
---

## What this skill does

Gives the Interrupts feature CLI parity. The Control Tower can create interrupts through its UI; this skill does it from a Claude Code session, writing to the **same store** (`tower/data/interrupts.json`) via the canonical helpers in `tower/interrupts/store.py`. No new data model, no drift — one source of truth.

Capture only. To work the queue (comment, tag, push to ADO, close), use `/triage`.

## Data model (from tower/interrupts/store.py)

- **source:** Support · Finance · Product · Executive · Internal
- **priority:** urgent · normal · low (auto-rule: Executive + due today → urgent)
- **status:** new · in-progress · deferred · done
- Optional: `dueDate` (YYYY-MM-DD), `customer`, `zendeskTicket`

## Steps

1. **Gather.** From the message or by asking: a one-line title, source, and — if known — due date, priority, customer, Zendesk ticket. Don't over-interrogate; title + source is enough to capture.

2. **Apply the urgency rule.** If source is `Executive` and due date is today, set priority `urgent` unless told otherwise.

3. **Write it** using the store helper (run from repo root so `tower` is importable):

   ```bash
   python -c "from tower.interrupts.store import create_interrupt; from pathlib import Path; import json; print(json.dumps(create_interrupt(Path('tower/data/interrupts.json'), title='TITLE', source='Support', priority='normal', due_date=None, customer=None, zendesk_ticket=None)))"
   ```

   Fill the kwargs from step 1. `create_interrupt` sets id, status `new`, empty tags/activity, and timestamps.

4. **Confirm.** Report the created id and title, and note it's now live in the Tower. If Chase gave context worth keeping (root cause, who asked), append it as a comment immediately via `/triage` semantics:

   ```bash
   python -c "from tower.interrupts.store import append_activity; from pathlib import Path; append_activity(Path('tower/data/interrupts.json'), 'THE_ID', 'comment', 'NOTE TEXT', author='Chase')"
   ```

## Notes

- This is local JSON — no server needs to be running. The Tower picks it up on its next poll.
- Do **not** hand-edit `interrupts.json`. Always go through the store helpers so timestamps and the activity log stay consistent.
- Related: [[triage]] to action interrupts, `/decision` if the interrupt resolution produces a call worth logging.
