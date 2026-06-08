---
name: project-question
description: Capture an open question or unresolved point for a project. Use when Chase says "question about [project]", "not sure about [project]", "need to figure out for [project]", "open question for [project]", "still unclear on [project]".
triggers:
  - "question about [project]"
  - "not sure about [project]"
  - "need to figure out for [project]"
  - "open question for [project]"
  - "still unclear on [project]"
  - "unresolved: [project]"
---

## Purpose
Append an open question directly to `/workspace/ais-os/projects/[slug]/questions.md`.
Questions stay open until explicitly resolved.

## Procedure

1. Identify the project slug. If ambiguous, ask: "Which project?"

2. Check `/workspace/ais-os/projects/[slug]/` exists. If not:
   "No project [slug] found."

3. Extract:
   - question: the question verbatim
   - context: any surrounding context given (null if minimal)
   - blocking: true if the question blocks progress, false otherwise (infer from language)

4. Append to `/workspace/ais-os/projects/[slug]/questions.md`:

```
## [short question label — infer 5 words max]
_Captured: [ISO timestamp]_
Blocking: [Yes/No]

**Question:** [question verbatim]

**Context:** [context or "None given"]

**Resolution:** _Open_

---
```

5. Confirm:
```
Question captured for "[slug]"
```
If blocking: append `"⚠ BLOCKING"`

## Notes
- Never try to answer the question — just capture it.
- Blocking questions get flagged visibly in the confirmation.
- If `questions.md` doesn't exist, create it with `# Questions — [slug]` header first.
