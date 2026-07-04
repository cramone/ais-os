---
name: morning-digest
description: Generate a morning digest of project ideas, blocking questions, and risks. Runs on schedule at 8am weekdays.
triggers:
  - "morning digest"
  - "daily digest"
  - scheduled
---

## Purpose
Cross-project start-of-day summary. Orients Chase without requiring him to open anything.

## Procedure

1. For each project under `/mnt/shared/claudia/magiq/projects/`:
   - Read `ideas.md` — list entries added in last 7 days
   - Read `questions.md` — list any open blocking questions (Blocking: Yes, Resolution: Open)
   - Read `risks.md` — list High impact risks added in last 7 days

2. Format:

---
**Morning Digest — [Date]**

**Recent Ideas**
- [title] ([project]) — [date]

**Blocking Questions**
- [project]: [question label]

**Recent Risks**
- [title] ([project]) — [impact] impact

---

3. Deliver via Telegram (default) or CLI.

## Notes
- Skip any section that has no entries — don't show empty sections
- If no pending items at all, say: "Nothing pending. Clean slate."
