---
name: note-capture
description: Use when Chase says "remember this", "note that", "keep in mind", "don't forget", "make a note", "for later", "save this thought", "adhoc note", or "remember for later". Captures free-form notes to context/adhoc-notes.md — same file Hermes adhoc-capture uses.
---

## Purpose

Capture free-form notes, reminders, or context Chase wants remembered.
Writes to `context/adhoc-notes.md` — shared with Hermes adhoc-capture skill.

## Routing Logic

**Step 1 — Detect project context:**

Check if a known project slug appears in the request or recent conversation:
- `magiq-media` (aliases: "media", "magiq media")
- `magiq-auth` (aliases: "auth", "magiq auth")

**Step 2 — If project detected, detect note type:**

| Keywords | Note type |
|---|---|
| "idea", "what if", "thinking about" | project idea |
| "decided", "going with", "decision" | → use `/decision` skill instead |
| "risk", "concern", "worried", "issue" | project risk |
| "question", "not sure", "need to figure out" | project question |
| anything else | project note (general) |

**Step 3 — Execute:**

- **Project detected** → write to `projects/{slug}/notes.md` (create if missing, with `# Notes` header)
- **No project** → write to general adhoc notes (see below)

---

## General Adhoc Notes Procedure

When no project context detected:

1. Extract note — preserve Chase's wording exactly.
2. Derive short title (≤8 words).
3. If `context/adhoc-notes.md` doesn't exist, create with `# Adhoc Notes` header first.
4. Append to `context/adhoc-notes.md`:

```
## [YYYY-MM-DDTHH:MM:SSZ] — [title]

[Note content verbatim or lightly cleaned]

---
```

5. Confirm: `Noted — '[title]'. Saved to adhoc notes.`

---

## Project Notes Procedure

1. Extract note — preserve Chase's wording exactly.
2. Derive short title (≤8 words).
3. If `projects/{slug}/notes.md` doesn't exist, create with `# Notes` header first.
4. Append entry in same format as adhoc notes above.
5. Confirm: `Noted — '[title]' → {slug} project notes.`

---

## Rules

- Never ask for confirmation — capture immediately and confirm after
- Never call ADO or any external API
- One entry per capture — never batch
- Use ISO 8601 timestamp for the heading (UTC)
- For decisions → redirect to `/decision` skill, don't capture here
