---
name: project-decision
description: Capture an architectural or design decision made for a project. Use when Chase says "decided on [project]", "going with [approach] for [project]", "decision for [project]", "we have chosen [X] for [project]".
triggers:
  - "decided on [project]"
  - "going with [approach] for [project]"
  - "decision for [project]"
  - "we have chosen [X] for [project]"
  - "confirmed for [project]"
  - "settled on [project]"
---

## Purpose
Append a decision entry directly to `/workspace/ais-os/projects/[slug]/decisions/log.md`.
Architectural decisions can be promoted to formal ADRs in `adrs/` when warranted.

## Procedure

1. Identify the project slug. If ambiguous, ask: "Which project?"

2. Check `/workspace/ais-os/projects/[slug]/` exists. If not:
   "No project [slug] found."

3. Extract:
   - title: short decision label (infer, 5-8 words max)
   - decision: what was decided, verbatim
   - rationale: why (verbatim if given, null if not)
   - alternatives: any alternatives mentioned (null if not given)
   - adrCandidate: true if architectural in nature, false otherwise

4. Append to `/workspace/ais-os/projects/[slug]/decisions/log.md`:

```
## [title]
_Captured: [ISO timestamp]_
ADR candidate: [Yes/No]

**Decision:** [decision]

**Rationale:** [rationale or "Not captured"]

**Alternatives considered:** [alternatives or "Not captured"]

---
```

5. Confirm:
```
Decision captured for "[slug]": [title]
```
If adrCandidate: append `"Flagged as ADR candidate — formalise in adrs/ when ready."`

## Notes
- Do not ask for missing fields. Capture what is given.
- adrCandidate = true when the decision involves architecture, technology choices, patterns, or infrastructure.
- If `decisions/log.md` doesn't exist, create it with `# Decision Log — [slug]` header first.
