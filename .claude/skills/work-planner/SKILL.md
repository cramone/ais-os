---
name: work-planner
description: >
  Plan, order, and structure a list of work items into branches, PRs, and optionally Azure DevOps tasks.
  Use this skill whenever the user provides a list of tasks, features, fixes, or work items for a project
  and wants help breaking it down into an ordered, structured delivery plan — even if they don't use the
  words "branch" or "PR". Triggers on phrases like: "here's what I need to do", "help me plan this work",
  "order this work", "split this into PRs", "plan this sprint", "what should I work on first", or when the
  user pastes a bullet list of dev tasks and asks what to do with them.
---

# Work Planner Skill

Transforms an unordered list of work items into a structured, dependency-ordered delivery plan with branch/PR groupings and optional Azure DevOps task creation.

---

## Workflow

### Step 1 — Capture Input

Accept either:
- A raw bullet/numbered list of work items, OR
- A free-form description of work to be done

If context is missing, ask ONE question: "Is there a specific project or bounded context this work belongs to?" — then proceed with what you have.

---

### Step 2 — Analyse and Classify

For each item, silently classify:
- **Type**: feature / bugfix / refactor / infrastructure / docs / chore
- **Layer**: domain / application / API / infrastructure / cross-cutting
- **Dependencies**: does this item need another item completed first?
- **Risk**: low / medium / high (based on scope, blast radius, coupling)

---

### Step 3 — Order the Work

Produce a dependency-ordered list. Rules:
1. Infrastructure and foundational domain changes first
2. Application layer and handlers next
3. API/endpoint layer after handlers
4. Cross-cutting concerns (auth, logging, validation) alongside or after the layers they affect
5. Docs and chores last

Flag circular dependencies or ambiguous ordering — ask the user to resolve before continuing.

---

### Step 4 — Group Into Branches and PRs

Group related ordered items into logical branches. Naming convention:

```
<type>/<short-scope-description>
```

Examples: `feat/asset-registration-api`, `fix/tenant-isolation-on-query`, `refactor/metadata-command-handlers`

**Grouping rules:**
- One PR should be reviewable in a single sitting (aim for cohesion over size)
- Don't mix feature work and refactoring in the same PR unless inseparable
- Each branch should build cleanly on the previous
- Shared infrastructure or domain changes that multiple branches depend on get their own branch first

**Output format per branch:**

```
Branch: feat/example-branch
PR Title: [Type] Short description of what this changes
Base: main (or prior branch if dependent)
Items:
  - item description
  - item description
Rationale: One sentence on why these items are grouped together.
```

---

### Step 5 — Save the Plan

After presenting the plan:

1. Ask: **"What would you like to name this plan?"**
2. Slugify the answer (lowercase, hyphens, no spaces): e.g. `"Auth Cleanup"` → `auth-cleanup`
3. Detect the project from context (e.g. `magiq-auth`, `magiq-media`) — if ambiguous, ask
4. Write the plan to: `projects/<project-name>/plans/<plan-name>.md`

**Plan file format:**

```markdown
# <Plan Name>

Generated: <YYYY-MM-DD>

## Summary

<N> items → <N> branches/PRs
**Flagged:** <any open issues>

---

## Ordered Delivery

| # | Item | Type | Risk |
|---|------|------|------|
...

---

## Branch / PR Breakdown

### Branch N — `<branch-name>`
**PR:** <PR Title>
**Base:** <base branch>

- item
- item

_Rationale._

---

## Open Questions

- [ ] Any unresolved items
```

---

### Step 6 — Azure DevOps (Optional)

After saving the plan, ask:

> "Want me to create these as tasks in Azure DevOps?"

If yes, read `references/azure-devops.md` for the ADO REST API integration details.

Create one **Task** work item per branch/PR group. Use:
- **Title**: PR Title from the plan
- **Description**: bullet list of included items + rationale
- **Area Path / Iteration**: ask the user if not known from context
- **Tags**: branch name

Confirm before creating. Show a summary of what will be created and wait for explicit approval.

---

## Output Structure

Always present the plan in this order:
1. **Summary** — total items, total branches, any flagged issues
2. **Ordered plan** — numbered list of all items in delivery order with type labels
3. **Branch/PR breakdown** — one block per branch as per Step 4 format
4. **Save prompt** — ask for plan name, then write to `projects/<project>/plans/<name>.md`
5. **ADO prompt** — offer to create ADO tasks

---

## Conventions (Chase's project defaults)

When working on magiq-media, magiq-auth, or MAGIQ Documents projects, apply these defaults unless told otherwise:
- Base branch: `main`
- Branch naming: `feat/`, `fix/`, `refactor/`, `chore/`, `infra/`
- Work item type: Task (under the relevant Epic if known)
- Assume DDD/CQRS layering when ordering (domain → application → API → infra)
- TenantId and auth changes are always high-risk — flag and isolate into their own PR

---

## Edge Cases

- **Single item**: still go through the process — output is one branch with framing
- **Already-ordered list**: validate the order, flag any dependency issues, then proceed to grouping
- **Vague items**: do your best to classify, flag ambiguous ones, ask at the end in a single batch
- **Too many items for one session**: split into phases, present Phase 1 first and ask before continuing
