---
name: decision
description: Use when Chase decides something worth remembering and wants it logged — "log this decision", "record that we decided", "add a decision", "/decision", or after any tradeoff call in a session. Appends a structured entry to decisions/log.md and, for architecture-level calls, spins up an ADR in references/adrs/. Enforces the CLAUDE.md decision-logging rules so the "why" never has to be re-derived.
---

## What this skill does

Captures a decision once, in the canonical place, so future-you and the Control Tower both see it.

- **Every decision** → appended to `decisions/log.md` (append-only, chronological, newest at the bottom).
- **Architecture decisions** → additionally get their own ADR in `references/adrs/NNNN-slug.md`, and the log entry links to it.
- Tower's decisions panel parses these entries via `tower/readers/decisions.py`, so the format below is not optional — the `## YYYY-MM-DD — Title` header and `**Project:**` line are what the reader keys on.

This is the *only* sanctioned way to write a decision. Project files reference decisions, they never duplicate them (CLAUDE.md rule).

## When NOT to run this

- Trivial or reversible choices with no reusable "why" — skip the ceremony.
- Automation specs — those come from `/level-up` Phase 2, which writes its own log entries.
- Something already logged — check the tail of `decisions/log.md` first; update the existing block instead of adding a duplicate.

## Steps

1. **Gather the decision.** From the conversation or by asking. You need: a short title, what was decided, the why (constraints + what would change your mind), alternatives considered, owner (default: Chase), and the project tag (match a folder in `projects/` when one applies).

2. **Classify.** Is this an **architecture** decision (system shape, stack, deployment topology, data model, integration boundary)? If yes → ADR path. If no → log-only.

3. **Append to the log.** Read `decisions/log.md`, then append this block *at the end* (chronological — do not prepend):

   ```
   ## YYYY-MM-DD — Short title

   **Project:** project-slug (or blank if cross-cutting)

   **Decision:** what was decided.

   **Why:** the reasoning, constraints, and what would change your mind.

   **Alternatives considered:** what else was on the table.

   **Owner:** who's accountable.
   ```

   Use today's date. Keep it terse. Preserve the `---` separators already in the file (one blank line, `---`, blank line between entries).

4. **Architecture only — write the ADR.** Create `references/adrs/` if it doesn't exist. Number the ADR by scanning existing files (`0001`, `0002`, …; start at `0001`). Filename: `NNNN-kebab-title.md`. Body:

   ```
   # NNNN. Short title

   **Status:** Accepted
   **Date:** YYYY-MM-DD
   **Owner:** Chase

   ## Context
   What forces are at play — the problem, constraints, and pressures.

   ## Decision
   What we decided, stated plainly.

   ## Consequences
   What becomes easier, what becomes harder, what we now have to live with.

   ## Alternatives considered
   Each option and why it lost.
   ```

   Then in the log block from step 3, add a final line: `**ADR:** references/adrs/NNNN-slug.md`.

5. **Confirm.** Show Chase the log entry (and ADR path if created) as written. Don't ask permission to write — write, then show. If he wants edits, edit in place.

## Notes

- The log preamble says "append-only" — honor it. Never rewrite history; correct a wrong decision with a new entry that supersedes it, referencing the old date.
- If the decision touches a security event, it also belongs in `security-incidents/{customer}/{dd-mm-yyyy}/` per CLAUDE.md — flag that, don't auto-file it.
