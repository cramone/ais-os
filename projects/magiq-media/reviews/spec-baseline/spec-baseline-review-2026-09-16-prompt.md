# Pick-up prompt — MM-001, spec-baseline

Paste into a fresh session. It assumes no prior context.

---

## Where you are

**Project:** `magiq-media` · slug `magiq-media`
**Project folder:** `Z:\claudia\magiq\projects\magiq-media`
**Code + spec repo:** `D:\source\github\sprbrk-standard\mgq-magiq-media`

**Document:** `MM-001`, a review
**Path:** `Z:\claudia\magiq\projects\magiq-media\reviews\spec-baseline\spec-baseline-review-2026-09-16.md`
**Todo id:** `8f9d3a14-4198-5e7e-a02c-e8ed12d23a12`

## First action, before anything else

Record what you are picking up and the state you found it in:

```bash
python -c "from tower import cycle; cycle.comment('magiq-media', 'MM-001', 'Picked up MM-001. Found: <state>. Working: <what>.')"
```

Run it from the repo root (`Z:\claudia\magiq`) so `tower` imports. The card's status is projected from the
document's front-matter and **cannot be set from the board** — do not try.

## Read first

1. `D:\source\github\sprbrk-standard\mgq-magiq-media\CLAUDE.md` § **Spec files state the specified system** —
   the rule that governs every edit this review leads to.
2. The review itself, in full.
3. `Z:\claudia\magiq\projects\magiq-media\MEMORY.md`.
4. Only then, the spec files a finding names.

## Background you need

Two sweeps landed on 2026-09-16, immediately before this review was written:

- **Citations removed** — 430 off-repo ids across 63 files. `breaking-changes.md` was deleted.
- **Build status removed** — implementation and deployment state across 76 files.

Both were careful never to invent design. This review exists **because** those sweeps removed the correction
notes and caveats that were papering over real contradictions and silences. Do not treat the findings as
regressions caused by the sweeps; they are pre-existing defects that are now visible.

The `MM-` sequence restarted at `MM-001` on 2026-09-16 — `reviews/` and `plans/` were cleared. If you find a
reference to an `MM-` id above `MM-001`, it is stale and names nothing.

## Out of scope

- **Application code, CDK and tests.** This review is about documents. Do not read code to settle a finding —
  if a question needs code, say so and stop.
- **Fixing anything during the review.** A review argues; a plan sequences; execution happens after both.
- **Code defects.** `MM-002` (`reviews/code-defects/`) holds the code-side work carried out of the retired
  `todos.md`. It overlaps this review on authorization and the boundary matters: **MM-001 fixes a spec that
  never stated a rule; MM-002 fixes code that does not enforce one.** Neither closes the other.

## Working the findings

- Finding ids are `SB-<n>`, already minted. **Stable — never renumber.** New findings continue the sequence.
- Severity is `Critical | High | Medium | Low`. Never 🔴/🟠 — those belong to gate documents only.
- **Evidence before conclusion.** Cite `file:line`. Quote what the file says rather than paraphrasing it.
- If you find something outside this review's scope, **it does not become an `SB-` finding.** Surface it and
  ask where it belongs.
- Where two documents disagree, the review states both and rules on neither. Keep that discipline: a ruling is
  Chase's, and it goes in § Open Questions as **Answered**, not silently into a finding.

## The gate

**Do not write the plan until both are true:**

1. Every question in `## Open Questions` reads `**Answered:** …` — zero `**Open**` markers.
2. Chase has moved the review to `status: findings-agreed`. That is his call, never an inference, however few
   questions remain.

**Question 1 is already Answered** (Chase, 2026-09-16) and its ruling is binding on a third of the plan. In
short: authorization is **intent**, specified in three places, and **not as a matrix**.

- A Graph-style scope vocabulary, `Resource.Verb[.All]`, declared once in a new `shared/api-permissions.md`.
  Three verbs — `Read`, `ReadWrite`, `Manage` (governance and destructive). `.All` means any resource in the
  tenant; omitted means the caller's own.
- The endpoint → scope mapping, per route **and per query**, in the existing `## Authorization` section of each
  `<agg>.api.md`. There is no central mapping table, and you do not create one.
- Resource predicates — owner match, reviewer roster, edit-session participation — stay as aggregate invariants
  in `<agg>.write-model.md`.

**The rule you must not break while working this:** a scope is checked at the edge and says what the *token*
may attempt; a resource predicate is checked in the handler or aggregate and says whether *this* resource is in
range for *this* caller. **`.All` widens a scope's range; it never removes the predicate.** Writing
`Asset.ReadWrite.All` and deleting `asset.OwnerId == actor.Id` is the exact collapse that turned the old matrix
into an enforcement audit. If a row in your output has a scope and no predicate on an owner-scoped resource,
that row is wrong.

`shared/authorization-matrix.md` is retired as a source of truth — but only in phase 4c, after the per-endpoint
mapping covers every route it names. Do not delete it early.

**All ten questions are Answered as of 2026-09-16 — zero `**Open**` markers remain.** Read § Open Questions
in full before touching anything: four of the ten are decisions with rejected alternatives recorded, and the
reasoning is the thing that stops them being re-litigated. Do not reopen one without saying so explicitly.

**The only thing still gating the plan is Chase moving the review to `findings-agreed`.** That is his call and
never an inference — not from the question count, and not from how complete the review looks.

Two questions an earlier draft carried — signer routing, and what identifies a signing session's owner — have
been **removed from § Open Questions on purpose**. They are findings (SB-35/SB-31 and SB-12), designed in
phase 6. Do not put them back: neither can be answered without doing the remediation the gate blocks, so
listing them makes the review un-closable by construction.

## Writing the plan

When the gate opens, write
`Z:\claudia\magiq\projects\magiq-media\plans\spec-baseline\spec-baseline-review-2026-09-16.md` —
the plan takes the review's filename.

Front-matter:

```yaml
---
id: MM-<next>          # mint by grep across reviews/ plans/ requests/ _archive/, +1
type: plan
project: magiq-media
workstream: spec-baseline
consumes: [MM-001]
depends-on: []
blocked-by-external: []
status: active
todo-id: <cycle.todo_id_for('magiq-media', '<new-id>')>
branches: []
ado: -
created: <session date>
---
```

Then phases. **A phase is a `## Phase <N> — <name>` heading**, an intro line, then `- [ ]` items each small
enough to finish in one session. Every item names the `SB-` finding it closes and its acceptance check. The
heading shape is not cosmetic — `ado-create-from-plan` parses it.

**Acceptance checks must be verifiable by reading the documents**, because this plan changes documents only.
"`grep -c 'owner_system' docs/spec` returns 1" is an acceptance check; "the code enforces it" is not.

Leave `ado: -`. Pushing to the board is a separate explicit step via `ado-create-from-plan`, run only once the
plan is `active`. This workstream is **not currently board-tracked**, so omit the `## ADO mapping` block
entirely rather than filling it with placeholders.

Close the plan with a `## Closing out` section: the plan moves to `done` only after Chase agrees the work is
complete, the closing comment records every branch it landed on, and the review/plan pair is then archived to
`_archive/reviews/MM-001-spec-baseline/` and `_archive/plans/<plan-id>-spec-baseline/`.

## Standing rules for any edit this leads to

The repo `CLAUDE.md` rule is absolute. No remediation may reintroduce:

- a citation to anything not defined inside `docs/` — no review, finding, plan or workstream ids
- build or implementation status — whether code exists, is wired, deployed, registered or deferred
- rationale, rejected options, recommendations, open questions, ✓ tracking
- notes addressed to a reader or an AI agent; who decided, and when

Rationale goes to `docs/adrs/`. Build status goes to the `Media` ADO board. Open questions stay on the plan
side. **When a spec is wrong, fix the statement and delete the wrong one — the diff is the history.**

And the constraint that matters most: **never invent design.** If closing a finding would mean asserting
behaviour no document states and no ruling covers, stop and ask. A spec that is silent is a known gap; a spec
that is confidently wrong is the thing this whole workstream exists to undo.

## Every session

Tick the checklist in the file as work lands. Update front-matter `status` in the same edit that changes what
is true — there is no board update, only the file. Append each branch to `branches`. Close with a card comment
saying what moved, what did not, and the next concrete action.
