---
name: work-planner
description: Take an unordered list of work items for a project, order them by dependency, assign branches and PRs, and optionally create Azure DevOps work items. Use when Chase says "plan the work", "break this into branches", "organise these tasks", "split this into PRs", or provides a list of items to implement.
triggers:
  - "plan the work"
  - "break this into branches"
  - "organise these tasks"
  - "split this into PRs"
  - "work plan for [project]"
  - "what branches do I need"
---

# work-planner

## Purpose

Transform an unordered list of work items into an ordered execution plan with named branches and PR boundaries. Optionally creates Azure DevOps work items.

Output lands in `/workspace/ais-os/projects/[slug]/plans/`.

---

## Step 1 — Identify the project

Ask only if not obvious: "Which project?"  
Check `/workspace/ais-os/projects/` for valid slugs. Abort if not found.

---

## Step 2 — Read project context

Read these before ordering anything:
- `CLAUDE.md` — stack, modules, priority
- `spec/architecture/bounded-context.md` — dependency graph
- `spec/architecture/domain-model.md` — aggregates, invariants
- `decisions/log.md` — prior decisions that constrain approach

This prevents ordering that violates existing architecture.

---

## Step 3 — Group items by module/bounded context

Each item belongs to exactly one group. If it touches multiple modules, assign it to the module that owns the primary change.

Groups become branches and PRs.

---

## Step 4 — Order items

**Within a group:** dependencies first (models → interfaces → impl → integration → tests).

**Across groups:** respect the bounded context dependency graph. Typical order:
1. Shared/infra (models, base classes, interfaces)
2. Core contexts with no downstream dependents
3. Downstream contexts that consume core
4. API layer / orchestration
5. Integration and cross-cutting concerns

Flag items with no cross-dependencies as **parallelisable**.

---

## Step 5 — Assign branch names and PR scopes

One branch per phase group. Naming: `feat/{slug}-{group-slug}`

For each branch/PR, define:
- Items included
- Likely files touched
- Acceptance criteria for merge

---

## Step 6 — Write the plan

Save to `/workspace/ais-os/projects/[slug]/plans/YYYY-MM-DD-<plan-slug>.md`

```markdown
# Work Plan — [slug]
_Created: [ISO timestamp]_

## Input items (unordered)
- [item 1]
- [item 2]
...

## Ordered execution

### Phase 1: [group name]
**Branch:** `feat/{slug}-{group-slug}`
**PR scope:** [what this PR covers]
**Depends on:** none
**Can parallelise with:** Phase 2, Phase 3

| # | Item | Rationale |
|---|------|-----------|
| 1 | [item] | [why this order] |
| 2 | [item] | [why this order] |

**Likely files:**
- `path/to/file.ext`

**Acceptance criteria:**
- [ ] [criterion]

---

### Phase 2: [group name]
...
```

If phases have no dependency links, add:

```markdown
## Parallel tracks

These phases can run concurrently:
- Phase 2: [name] (`feat/{slug}-...`)
- Phase 3: [name] (`feat/{slug}-...`)
```

---

## Step 7 — Optional Azure DevOps creation

At the end, show the summary and ask:

> "Create these as ADO work items? [Y/n]"

If yes, create one ADO Task per item:
- Priority 2 for early phases, 3 for later phases
- Description includes branch name and phase
- Report ADO IDs or failure reason back

**ADO create payload:**
```json
[
  { "op": "add", "path": "/fields/System.Title",       "value": "[title]" },
  { "op": "add", "path": "/fields/System.Description",  "value": "Branch: feat/...\\nPhase: [phase]\\n\\n[rationale]" },
  { "op": "add", "path": "/fields/System.State",        "value": "New" },
  { "op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": 2 }
]
```

---

## Rules

- Never reorder without explaining rationale.
- Never merge unrelated items into one branch to reduce PR count.
- Ask about ambiguous items — do not guess.
- One plan file per run (dated). Never overwrite existing plans.
- Do not create ADO items unless explicitly confirmed.
