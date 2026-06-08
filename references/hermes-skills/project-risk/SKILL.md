---
name: project-risk
description: Capture a risk, concern, or potential issue for an existing project. Use when Chase says "risk for [project]", "concern about [project]", "worried about [project]", "potential problem with [project]", "flag a risk for [project]".
triggers:
  - "risk for [project]"
  - "concern about [project]"
  - "worried about [project]"
  - "potential problem with [project]"
  - "flag a risk for [project]"
  - "watch out for [project]"
---

## Purpose
Append a risk entry directly to `/workspace/ais-os/projects/[slug]/risks.md`.

## Procedure

1. Identify the project slug. If ambiguous, ask: "Which project?"

2. Check `/workspace/ais-os/projects/[slug]/` exists. If not:
   "No project [slug] found."

3. Extract:
   - title: short label (infer, 5 words max)
   - description: the risk verbatim
   - impact: High / Medium / Low (infer from language, default Medium)
   - likelihood: High / Medium / Low (infer from language, default Medium)
   - mitigation: any mitigation mentioned (null if not given)

4. Append to `/workspace/ais-os/projects/[slug]/risks.md`:

```
## [title]
_Captured: [ISO timestamp]_
Impact: [impact] | Likelihood: [likelihood]

**Risk:** [description]

**Mitigation:** [mitigation or "TBD"]

---
```

5. Confirm:
```
Risk captured for "[slug]": [title] ([impact] impact)
```

## Notes
- Do not ask for missing fields — infer or leave as TBD.
- Multiple risks in one message = multiple entries.
- If `risks.md` doesn't exist, create it with `# Risks — [slug]` header first.
