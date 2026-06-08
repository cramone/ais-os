---
name: morning-digest
description: Generate a morning digest of pending ADO notes, project ideas, blocking questions, and reminders. Runs on schedule at 8am weekdays.
triggers:
  - "morning digest"
  - "daily digest"
  - scheduled
---

## Purpose
Cross-project start-of-day summary. Orients Chase without requiring him to open anything.

## Procedure

1. Read `~/.hermes/data/ado-pending.json`.
   Group by project, then type. Count per project.
   Flag any project with no new notes in 5+ days.
   Flag any High priority items.

2. For each project under `/workspace/ais-os/projects/`:
   - Read `ideas.md` — list entries added in last 7 days
   - Read `questions.md` — list any open blocking questions (Blocking: Yes, Resolution: Open)
   - Read `risks.md` — list High impact risks added in last 7 days

3. Read `~/.hermes/data/reminders.json` if it exists — list active reminders.

4. Format:

---
**Morning Digest — [Date]**

**Pending ADO Items**
magiq-media (N): Stories (n), Tasks (n) [⚠ n High priority]
magiq-auth (N): Stories (n)

**Recent Ideas**
- [title] ([project]) — [date]

**Blocking Questions**
- [project]: [question label]

**Recent Risks**
- [title] ([project]) — [impact] impact

**Reminders**
- [item]

*Open Claude Code in AIS-OS and run `/devops` or "flush pending notes" to act on ADO items.*
---

5. Deliver via Telegram (default) or CLI.

## Notes
- Skip any section that has no entries — don't show empty sections
- If no pending items at all, say: "Nothing pending. Clean slate."
