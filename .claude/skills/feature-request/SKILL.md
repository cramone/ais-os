---
name: feature-request
description: Use to capture a feature request as a cycle document and run it to a plan — record who asked and when, triage it to accepted or declined, then write the plan the same way a review does. Triggers on "capture a feature request", "log a feature request for [project]", "[person] asked for [feature]", "raise an FR", "new feature request", "triage the feature requests", "write the plan for [request]", "/feature-request". Writes to projects/{slug}/requests/, projects/{slug}/plans/, and the tower/data/todos/{slug}.json todo store.
---

## What this skill does

Runs the **feature-request → plan** cycle. A feature request argues *this should exist*; a plan sequences it and tracks execution.

It is the same cycle [[review-cycle]] runs, with one document type swapped at the front. **A feature request is a peer of a review, not a stage before it** — both are *origin documents*, both are consumed by a plan, both live in the same id space. What differs is the argument they make and the fields that support it.

| | review | feature request |
|---|---|---|
| Argues | this is broken | this should exist |
| Evidence | findings with severity and `file:line` | a requestor, a date, and a stated need |
| Gate to plan | `findings-agreed` | `accepted` |
| Lives in | `reviews/<ws>/` | `requests/<ws>/` |

**Everything downstream is identical and is not restated here.** Read [[review-cycle]] for: § Document ids, § Todo store, § The card is the session log, § Dependency gating, § External blockers, § Cross-project work, § Findings discovered during execution, § Frozen documents, § Archiving, § Legacy files, § ADO. Those sections govern feature requests unchanged. **Where this file and `review-cycle` disagree on shared machinery, `review-cycle` wins** — this one is a delta, not a copy.

## Adoption

Same marker, same rule as [[review-cycle]]:

```markdown
## Review → Plan cycle
prefix: MM
we-operate: true
```

No marker, or `we-operate: false` → out of scope. **Do not raise a feature request against a repo we do not operate.** That is someone else's backlog; it is a `blocked-by-external` entry on our plan with a hand-off doc ([[review-cycle]] § Cross-project work).

## Ids

**One id space, shared with reviews, plans and gates.** `<PREFIX>-<nnn>`, monotonic per project. Mint by grep across all three folders, `Archive/` included:

```bash
grep -rhoE '^id: [A-Z]+-[0-9]{3}' projects/<slug>/reviews projects/<slug>/requests projects/<slug>/plans | sort | tail -1
```

Never a separate `FR-1` counter. `consumes:` and `depends-on:` resolve by one regex over one namespace — a second space would silently fail to resolve.

## Naming

- workstream slug — kebab-case from the request, e.g. `bulk-export`
- request — `projects/<project>/requests/<workstream>/<workstream>-request-<YYYY-MM-DD>.md`
- prompt — `projects/<project>/requests/<workstream>/<request-filename>-prompt.md`
- plan — `projects/<project>/plans/<workstream>/<primary-request-filename>.md`
- archive — `requests/<ws>/Archive/`, capital A

**Never write a bare `request.md`.** A workstream accumulates requests; a fixed filename overwrites.

**A workstream slug is shared across trees.** If `bulk-export` exists as a review workstream and a request arrives about the same area, that is one workstream with two origins — `requests/bulk-export/` beside `reviews/bulk-export/`, and the plan `consumes` both ids. Do not invent `bulk-export-fr`.

**Dates come from the session environment, never from memory or inference.**

## Front-matter

Every field mandatory; use `-` or `[]` for empty.

```yaml
---
id: <PREFIX>-<nnn>
type: feature-request
project: <slug>                  # project that OWNS the code the feature lands in
workstream: <slug>
requested-by: <name or team>
requested-on: YYYY-MM-DD
request-source: Support | Product | Executive | Internal | Finance | Customer
raised-by: [<id>, ...]           # origin documents; [] if requested directly
status: new | accepted | declined | parked | superseded | done
outcome: pending | plan | declined | parked | review:<id> | folded-into:<id>
todo-id: <uuid>
created: YYYY-MM-DD
---
```

Notes on the four fields a review does not have:

- **`requested-by`** — a person or a team, never "the customer". The point of the field is knowing who to go back to when the scope question arrives six weeks later. Unknown requestor → ask before writing the file; if genuinely untraceable, `-` plus a line in `## Request` saying where it came from.
- **`requested-on`** — when the *ask* was made, which is not `created`. A request captured a fortnight late has two different dates and both matter: `requested-on` is how long they have been waiting, `created` is how long we have known.
- **`request-source`** — the `interrupts/store.py` source enum plus `Customer`. Deliberately shared so [[triage]] and this skill speak one language and an interrupt can graduate into a request without a translation table.
- **`status`** — a different vocabulary from a review's, because there are no findings to agree. See below.

`exception: <one-line reason>` silences every check on the file, same as anywhere else in the cycle.

## Status vocabulary

`new` → `accepted` → `done` | `declined` | `parked` | `superseded`

| Front-matter | Todo status | Todo tag | README word | Means |
|---|---|---|---|---|
| `new` | `new` | — | New | Captured, not yet triaged |
| `accepted` | `in-progress` | — | Accepted | We are doing it; the plan gate is open |
| `declined` | `done` | `declined` | Declined | We are not doing it. Reason mandatory |
| `parked` | `deferred` | `parked` | Parked | Real, deliberately not now. Reason mandatory |
| `superseded` | `done` | `superseded` | Superseded | Overtaken; kept for the reasoning |
| `done` | `done` | — | Done | Terminal, with an outcome |

**`accepted` is a call Chase makes, not one you infer.** A request with a clear need and no open questions is *ready to accept*, not accepted. Say so and wait. Until Chase accepts it, the plan gate stays shut.

**`declined` is a first-class outcome and must be easy to reach.** A backlog that can only grow is not a backlog. Declining costs one status change and one sentence, and the document stays — the reasoning is the point. **Never delete a declined request.**

## Body

Required sections, in order:

- `## Request` — the ask **in the requestor's own words first**, quoted, then your restatement. Two lines, kept separate. The gap between what someone asked for and what you understood is where the wrong feature gets built, and it is only visible if both are on the page.
- `## Context` — why now. Who is blocked, what they do instead today, what happens if we never build it. This is the section that makes `declined` defensible.
- `## Scope` — in and out, explicitly. Out-of-scope is the more useful half.
- `## Open Questions` — numbered, each `**Open**` or `**Answered:** <answer>`.
- `## Dependencies` — other documents needed, by id, plus any external blocker; `none` if none.
- `## Recommended sequencing` — rough; the plan refines it.

**No `## Findings`, no severity.** There is nothing broken to rate. A request that turns out to be describing a defect is a review — see § Outcome `review:<id>`.

**No effort estimate in the request.** Sizing is a plan concern; an estimate written before the scope is settled becomes the number everyone remembers.

## Workflow 1 — capture a request

Trigger: someone asked for something and it should outlive the conversation.

1. **Resolve target.** Project slug and workstream slug. Ambiguous project → ask, do not guess. Read the adoption marker. **No marker, or `we-operate: false` → stop** and propose an external hand-off.
2. **Get requestor and date.** `requested-by` and `requested-on` are the reason this skill exists. Ask if not stated; do not fill them with a guess. Everything else can be thin on a first capture.
3. **Check for a duplicate.** Grep `requests/` for the same area before minting an id. A second request for a thing already captured gets `raised-by` pointing at the first and `outcome: folded-into:<id>`, not a new workstream.
4. **Mint the id** from the project's prefix, across all three folders.
5. **Create folders.** `requests/<workstream>/`, plus `requests/README.md` if the project has none (§ README).
6. **Do not create the todo.** The board projects it on the next read with id `cycle.todo_id_for(<slug>, <doc-id>)` — put that value in `todo-id` and it will match.
7. **Write the request** with front-matter (`status: new`, `outcome: pending`) and the sections above.
8. **Write the prompt file** — `<request-filename>-prompt.md` beside it (§ The prompt file). Skip only when the request is trivially small and will be planned in this same session; say so if you skip it.
9. **Index it.** A row in `requests/README.md` carrying id, requestor, date and status `New`.
10. **Report** id, paths written, todo id, requestor and date.

**Capture is cheap and must stay cheap.** A request captured thin is worth more than one not captured. Steps 2 and 4 are the only ones that cannot be deferred; if Chase is mid-flow, write the file with a thin `## Context` and say what is missing.

## Workflow 2 — triage

Trigger: "triage the feature requests", or a `new` request coming up in conversation.

For each request at `status: new`, put one of these to Chase with a recommendation — never decide it yourself:

| Call | Sets | Also |
|---|---|---|
| accept | `status: accepted` | Plan gate opens. Zero `**Open**` markers required first |
| decline | `status: declined`, `outcome: declined` | **Reason mandatory** in the body |
| park | `status: parked`, `outcome: parked` | **Reason mandatory**, and what would unpark it |
| needs investigation | `status: accepted`, `outcome: review:<id>` | Raise a review via [[review-cycle]]; the plan then consumes both |
| duplicate | `status: superseded`, `outcome: folded-into:<id>` | Add this id to that document's `consumes` |

Then, every time: write the status into front-matter in the same edit, and comment the card with what settled it ([[review-cycle]] § The card is the session log).

**Never leave a request at `outcome: pending` once we have stopped working it.** That is the state a backlog rots in.

## Workflow 3 — the request produces a plan

Preconditions, all three, checked and reported before anything is written:

- request `status: accepted`
- zero `**Open**` markers in `## Open Questions`
- Chase has said to write the plan

Then follow [[review-cycle]] § Workflow 2a exactly, with `consumes` naming the request id. Specifically:

1. **Mint the plan id.** Resolve dependencies ([[review-cycle]] § Dependency gating) and write `plans/<workstream>/<primary-request-filename>.md`, `consumes` listing every origin id it takes — requests and reviews alike, mixed freely.
2. **Close the request.** `status: done`, `outcome: plan`. Comment its card with the plan id.
3. **Do not create the plan todo.** The projection makes it. Comment it with the hand-over.
4. **Index it** in `plans/README.md`; update the row in `requests/README.md`.
5. The plan carries a `## Closing out` section, same terms as any other plan.

**Hand-over is complete only when steps 1–4 have all happened.** Report it explicitly before execution begins.

**One extra step for requests, and it is not optional: tell the requestor.** A feature request has a person on the other end. When a request reaches `accepted`, `declined` or `plan`, name in your report who needs telling and draft the message if Chase wants one — but **never send it**. External communication in Chase's voice is shown as a draft first, always (`CLAUDE.md § Voice`).

## The prompt file

Pasted into a fresh Claude session with zero context from this one. It must stand alone.

Same contract as [[review-cycle]] § The prompt file, with these differences:

- Say the document is a **feature request, not a review**: there are no findings to raise and nothing to rate for severity. The job is to sharpen scope and answer the open questions.
- Carry `requested-by` and `requested-on` verbatim, and name the requestor as the person to go back to on a scope question.
- The gate is: **do not write the plan until every open question is answered AND Chase has moved the request to `accepted`.**
- Instruct that a defect found while scoping does **not** get folded into the request — it goes to a review or the drift register ([[review-cycle]] § Findings discovered during execution).
- The `## Writing the plan` section is identical to the review version, including the `## Phase <N> — <name>` heading shape [[ado-create-from-plan]] parses, and `ado: -` left for a separate explicit step.

## README

`projects/<slug>/requests/README.md`, mirroring `reviews/README.md` — created on the first request in a project.

```markdown
# Feature requests — <project>

**A feature request is where work starts when nothing is broken.** It argues that
something should exist. Scope is settled here; sequencing and execution happen in the
matching `plans/` folder, under the same workstream name. Peer of a review, not a
stage before one — see the `feature-request` skill.

**Status** — _New_ · _Accepted_ · _Declined_ · _Parked_ · _Superseded_ · _Done_.
**Outcome** — _plan_ · _declined_ · _parked_ · _review_ · _folded-into_. _pending_ is a
state to leave, not to rest in.

| Id | Workstream | Request | Requested by | Requested | Status | Outcome | Its plan |
|---|---|---|---|---|---|---|---|
```

Archived rows move to an archive section at the bottom, keeping id and name. Never deleted.

**Index everything from creation, including `new`.** A request that exists but is not in the README is invisible to the next session.

## Boundary with interrupts

They overlap and the seam matters.

- **[[interrupt]]** — an unplanned thing competing with sprint focus. Local JSON, gitignored, disposable. Right for "Zendesk 4412 is on fire".
- **feature request** — a durable, versioned document that can produce a plan. Right for "Sarah wants bulk export".

An interrupt that turns out to be a feature ask **graduates**: capture it here, comment the interrupt with the new document id, close the interrupt. `request-source` uses the interrupt source enum precisely so this costs nothing. **Do not run the same ask in both systems** — one of the two copies will go stale, and it will be the one someone reads.

A feature request never demotes to an interrupt. Once it is a document with an id, it stays one.

## Invariants

Additional to [[review-cycle]] § Invariants, which apply unchanged:

- A feature request has `requested-by` and `requested-on`. Unknown requestor is `-` plus an explanation in the body, never a guess.
- Requests share one id space with reviews, plans and gates. There is no `FR-` space.
- A plan's origin is a review **or** a feature request. `consumes` naming neither is a data error, and `cycle.check()` reports it.
- A request cannot produce a plan before `accepted` with zero `**Open**` questions.
- `accepted` and `declined` are Chase's calls, never inferred.
- A declined or superseded request is kept, never deleted — the reasoning is the artifact.
- Severity and 🔴/🟠 never appear in a request. Severity belongs to review findings; gate status belongs to gates.
- One workstream slug across `requests/`, `reviews/` and `plans/`.
- The requestor is told when a request reaches a terminal state — drafted, never sent unprompted.

## Related

- [[review-cycle]] — the peer skill and the owner of all shared machinery
- [[workstream-query]] — the read side; never duplicate its queries here
- [[project-todos]] — the todo store API
- [[interrupt]] / [[triage]] — the ephemeral queue this graduates from
- [[ado-create-from-plan]] — pushing the resulting plan to the board
- [[decision]] — log the call when a decline or a park is architectural
