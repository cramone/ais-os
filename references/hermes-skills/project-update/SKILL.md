---
name: project-update
description: Capture an update or change to an existing project spec or brief. Use when Chase says "update [project]", "change [project]", "revise [project]", "actually for [project]", or provides new information that modifies existing scope, stack, modules, or constraints.
triggers:
  - "update [project]"
  - "change [project]"
  - "revise [project]"
  - "actually for [project]"
  - "correction for [project]"
  - "amend [project]"
---

## Purpose
Apply updates directly to the relevant project files in `/workspace/ais-os/projects/[slug]/`.
Simple field changes (priority, status, ADO board) go straight into `CLAUDE.md` and `brief.md`.
Complex changes (scope, modules, stack, description) are appended to `notes.md` for review before touching spec files.

## Procedure

1. Identify the project slug from the message. If ambiguous, ask: "Which project?"

2. Check `/workspace/ais-os/projects/[slug]/` exists. If not:
   "No project [slug] found. Create it first with new project [name]."

3. Extract from the message:
   - field: what is changing (description, stack, modules, integrations, adoBoard, priority, status, or general)
   - change: the new information or correction, verbatim

4. Route by field type:

   **Simple fields** (priority, adoBoard, status):
   - Update the value directly in `brief.md` and `CLAUDE.md`.
   - Confirm: `✅ [field] updated for "[slug]": [new value]`

   **Complex changes** (description, stack, modules, integrations, or general):
   - Append to `/workspace/ais-os/projects/[slug]/notes.md`:

```
## Update — [field]
_Captured: [ISO timestamp]_

[change — verbatim]

---
```
   - Confirm: `Update noted for "[slug]" ([field]). Review notes.md to apply to spec files.`

## Notes
- One entry per message — if multiple changes, handle each separately.
- Never modify spec files directly — those go through notes.md for review.
- If `notes.md` doesn't exist, create it with `# Notes — [slug]` header first.
