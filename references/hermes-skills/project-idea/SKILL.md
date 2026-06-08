---
name: project-idea
description: Capture a loose idea, enhancement, or what-if thought for an existing project. Use when Chase says "idea for [project]", "what if [project]", "thinking about [project]", "could we add to [project]". Low friction — no structure required.
triggers:
  - "idea for [project]"
  - "what if [project]"
  - "thinking about [project]"
  - "could we add to [project]"
  - "for [project], what about"
---

## Purpose
Capture unstructured ideas without interrupting flow. Appends directly to `/workspace/ais-os/projects/[slug]/ideas.md`.
Ideas are reviewed and triaged in context — not automatically turned into tasks.

## Procedure

1. Identify the project slug from the message. If ambiguous, ask: "Which project?"

2. Check `/workspace/ais-os/projects/[slug]/` exists. If not:
   "No project [slug] found. Create it first with new project [name]."

3. Extract:
   - title: short label for the idea (infer from message, 5 words max)
   - idea: the full description verbatim
   - module: which module it relates to (infer if possible, null if not)

4. Append to `/workspace/ais-os/projects/[slug]/ideas.md`:

```
## [title]
_Captured: [ISO timestamp]_
Module: [module or "unassigned"]

[idea — verbatim]

---
```

5. Confirm:
```
Idea captured for "[slug]": [title]
```

## Notes
- Keep it fast. Low-friction capture, not structured intake.
- Never create ADO items from ideas.
- Multiple ideas in one message = multiple entries.
- If `ideas.md` doesn't exist, create it with `# Ideas — [slug]` header first.
