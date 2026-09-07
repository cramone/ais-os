---
name: workstream-query
description: Use to read the state of reviews, feature requests and plans across every project without changing anything — what's unblocked and ready to work, what's blocked and why, what's stuck waiting on a decision or an unsent hand-off, which requests are untriaged, what a given document blocks, and the dependency graph. Triggers on "what's unblocked", "what can I work on", "what's blocked", "why is [workstream] blocked", "what's stuck", "what's untriaged", "what does [id] block", "show the workstream graph", "/workstream-query". Read-only companion to review-cycle and feature-request — it never writes files or todos.
---

## What this skill does

Answers "what is the state of the work" by grepping the front-matter that [[review-cycle]] and [[feature-request]] write. **Read-only. It never writes a file, never touches the todo store, never changes a status.** If a query surfaces something that needs changing, report it and hand off to the skill that owns it — [[review-cycle]] for reviews, plans and gates, [[feature-request]] for requests.

**Every query sweeps all adopting projects, not the current one.** That global sweep is what stops cross-project work from orphaning — a review raised by one project and landing in another surfaces from both ends.

## Scope

Adopting projects are those whose `CLAUDE.md` carries a `## Review → Plan cycle` section:

```markdown
## Review → Plan cycle
prefix: MM
we-operate: true
```

```bash
grep -l "^## Review → Plan cycle" projects/*/CLAUDE.md
```

Projects without it are out of scope — do not scan them, and say which ones you skipped if it matters to the answer.

## What you are reading

Front-matter on four document types under `projects/<slug>/reviews/`, `projects/<slug>/requests/` and `projects/<slug>/plans/`:

| type | Lives in | Key fields |
|---|---|---|
| `review` | `reviews/` | `status`, `outcome`, `raised-by`, `workstream`, `todo-id` |
| `feature-request` | `requests/` | `status`, `outcome`, `requested-by`, `requested-on`, `request-source`, `raised-by` |
| `plan` | `plans/` | `status`, `consumes`, `depends-on`, `blocked-by-external`, `branches`, `ado` |
| `gate` | `plans/` | `status`, `consumes`, `supersedes` |

**`review` and `feature-request` are peers**, not stages — either can originate a plan, and a plan may consume both. Treat them alike in every query except where a field only one of them has is being asked about.

Statuses: reviews are `draft` → `findings-agreed` → `done` | `parked` | `superseded`. Feature requests are `new` → `accepted` → `done` | `declined` | `parked` | `superseded`. Plans are `active` | `blocked` | `parked` | `superseded` | `done`. Gates are `active` | `superseded` | `done`.

**Cross-references are ids, never paths, and one id space covers all four types.** Resolve one by grepping across all three folders:

```bash
grep -rl "^id: MM-014" projects/*/reviews projects/*/requests projects/*/plans
```

**Ids are for references; names are for reading.** Always resolve an id to its title in the output — `MM-014 — archive cascade`, never a bare id.

## Queries

### "what's unblocked" / "what can I work on"

Plans with `status: active`, grouped by project.

For each: id, title, workstream, and **the next unticked `- [ ]` item** in the plan body — skipping any phase the plan marks as blocked. That next item is the whole point of the answer; a plan without one is finished in practice and should be flagged for close-out.

Sort by todo priority (`urgent` → `normal` → `low`), then by project.

### "what's blocked and why"

Plans with `status: blocked`. For each, name the specific cause, not just the state:

- **internal** — a `depends-on` id that is unmet, with that document's current status
- **external, sent** — a `blocked-by-external` entry with `sent: true`; we are waiting on someone
- **external, unsent** — `sent: false`; **we own this**, and it is the critical path, not an errand

Call out partial blocks: if the plan marks only some phases blocked, say which phases can still proceed.

### "what's stuck"

Things that are neither moving nor visibly blocked:

- reviews or requests at `outcome: pending` whose todo has no recent activity
- any `blocked-by-external` with `sent: false` — the ask exists and nobody has sent it
- plans at `status: active` whose todo is still `new`
- reviews at `status: draft` older than the current sprint
- reviews at `findings-agreed` with zero `**Open**` questions and no plan — ready to plan, waiting on nobody
- requests at `status: accepted` with zero `**Open**` questions and no plan — same, on the request side
- requests at `status: new` — untriaged. **Sort these by `requested-on`, not by id**, and give the age in days: an untriaged request is the one kind of stuck where someone outside this workspace is waiting and does not know it

### "what's untriaged" / "what's in the request queue"

Feature requests at `status: new`, across every adopting project.

Per item: id, title, project, `requested-by`, `requested-on` and its age in days, `request-source`. Sort oldest ask first. Name the count of anything older than 30 days as its own line — that is the number worth acting on.

This is read-only. Triaging them is [[feature-request]] § Workflow 2.

### "what does <id> block"

The reverse edge. Everything whose `depends-on` contains that id, plus anything whose `raised-by` or `consumes` names it. Answers "if I finish this, what unlocks".

```bash
grep -rn "MM-014" projects/*/reviews projects/*/requests projects/*/plans --include=*.md
```

### "show the graph"

`raised-by` / `depends-on` / `consumes` edges as an id list with titles. Group by project; mark cross-project edges explicitly. Flag any cycle you find — A depends on B and B on A, directly or transitively — but **do not attempt to break it**; that is a [[review-cycle]] decision.

### "status of <workstream>"

Everything in that workstream folder across all three trees: reviews and feature requests with status and outcome, plans with status and dependency state, the gate that consumes them if any, and the matching todos. A workstream may have origins in both `reviews/` and `requests/` — list both. Include `Archive/` contents, marked as archived.

## Data problems — report, never fix

These are read-only findings. Surface them plainly and stop:

| What you see | What it means |
|---|---|
| `depends-on` id that resolves to nothing | Dangling reference — a data error, **not** a blocked state |
| A file with no front-matter | Legacy, predates the cycle. **UNKNOWN** status — never infer one |
| Two files with the same `id` | Minting collision |
| A path in `consumes` or `depends-on` | Should be an id |
| Front-matter status disagreeing with the todo store | The file is authoritative; report the mismatch |
| A review or request at `outcome: pending` that nobody is working | Needs a terminal outcome |
| A plan whose `consumes` names no review and no feature request | No origin — the plan exists for work nobody argued for |
| A request with `requested-by: -` and no explanation in the body | The one field the request exists to carry, missing |
| A file carrying `exception:` | Deliberate convention break — report it, never flag it as wrong |

Roughly twenty legacy files carry no front-matter at all. Say so when it limits an answer — an honest "these six workstreams are unreadable to me" beats a confident partial list.

## Output shape

- Lead with the direct answer. No preamble.
- One line per item: id, title, project, the fact that was asked for.
- Group by project only when more than one project appears.
- State coverage when it is incomplete: which projects were skipped, how many files were unreadable.
- Never pad a thin result. Three unblocked plans is a three-line answer.

## Related

- [[review-cycle]] — the write side for reviews, plans and gates; anything that changes state goes there
- [[feature-request]] — the write side for feature requests
- [[project-todos]] — todo state, for when the question is about todos rather than documents
- [[triage]] — the interrupt queue, a different store with the same item schema
