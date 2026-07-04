---
name: adhoc-capture
description: Capture free-form notes, reminders, or context that Chase wants remembered. Routes to project notes or general adhoc memory depending on context.
triggers:
  - "remember this"
  - "note that"
  - "keep in mind"
  - "don't forget"
  - "make a note"
  - "for later"
  - "save this thought"
  - "adhoc note"
  - "remember for later"
---

## Purpose

Capture free-form notes, reminders, or context that Chase wants remembered across sessions.
Routes to project notes or general adhoc memory depending on context.

## Routing Logic

**Step 1 — Detect project context:**

Check if a known project slug appears in the request or recent conversation:
- `magiq-media` (aliases: "media", "magiq media")
- `magiq-auth` (aliases: "auth", "magiq auth")

**Step 2 — Detect note type** (only if project detected):

| Keywords | Route to `project-management` section |
|---|---|
| "idea", "what if", "thinking about" | § Idea |
| "decided", "going with", "decision" | § Decision |
| "risk", "concern", "worried", "issue" | § Risk |
| "question", "not sure", "need to figure out" | § Question |
| "update", "change", "revise" | § Update |
| anything else | § Idea (default for project notes) |

**Step 3 — Execute:**

- **Project detected** → invoke the matching `project-management` section inline (do not ask user to re-trigger). `project-idea`/`project-decision`/`project-risk`/`project-question`/`project-update` no longer exist as separate skills — they were folded into `project-management`'s labeled sections.
- **No project** → write to general adhoc memory (see below)

---

## General Adhoc Memory Procedure

When no project context detected:

1. Extract note — preserve Chase's wording exactly.
2. Derive short title (≤8 words).
3. Append to `/mnt/shared/claudia/magiq/context/adhoc-notes.md`:

```
## [YYYY-MM-DDTHH:MM:SSZ] — [title]

[Note content verbatim or lightly cleaned]

---
```

4. If file doesn't exist, create with `# Adhoc Notes` header first.
5. Confirm: `Noted — '[title]'. Saved to adhoc notes.`

---

## Notes

- Never ask for confirmation — capture immediately and confirm
- Never call ADO or any external API
- One entry per capture — never batch
- When routing to a project skill, confirm with project slug: `Noted — '[title]' → magiq-media project notes.`
