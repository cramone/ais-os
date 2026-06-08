---
name: project-remove
description: Flag something to be removed from an existing project scope, modules, or spec. Use when Chase says "remove from [project]", "drop [thing] from [project]", "scratch [thing] for [project]", "out of scope for [project]". Never deletes anything — only flags for review.
triggers:
  - "remove from [project]"
  - "drop [thing] from [project]"
  - "scratch [thing] for [project]"
  - "out of scope for [project]"
  - "cut [thing] from [project]"
  - "no longer need [thing] in [project]"
---

## Purpose
Flag removals as pending — never delete anything directly.
Writes to `/workspace/ais-os/projects/[slug]/removals.json` for review and confirmation before any file is touched.
This is intentionally conservative: wrong removals are expensive.

## Procedure

1. Identify the project slug from the message. If ambiguous, ask: "Which project?"

2. Check `/workspace/ais-os/projects/[slug]/` exists. If not:
   "No project [slug] found."

3. Extract:
   - target: what to remove (module name, feature, integration, field value, etc.)
   - reason: why it is being removed (verbatim if given, null if not)
   - scope: which file/area it affects (manifest, brief, spec, ideas, risks — infer if possible)

4. Append entry to `/workspace/ais-os/projects/[slug]/removals.json`.
   If file doesn't exist, create it as a JSON array `[]` first, then append:

```json
{
  "id": "[uuid]",
  "capturedAt": "[ISO timestamp]",
  "target": "[what to remove]",
  "reason": "[reason or null]",
  "scope": "[affected area]",
  "status": "pending"
}
```

5. Confirm:
```
Removal flagged for "[slug]": [target]
Review removals.json and apply manually when ready.
```

## Notes
- NEVER delete or modify any existing file. Only write to removals.json.
- status is always "pending" — review and apply manually with confirmation.
- If the request sounds like it could affect real data, confirm first.
