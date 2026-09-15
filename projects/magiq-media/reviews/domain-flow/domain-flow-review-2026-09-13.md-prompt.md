# Domain flow review — paste-ready session prompt

You are picking up a review in the `magiq-media` project. This prompt assumes you have **no context from
any previous session**. Everything you need is below or at the paths it names.

---

## Where you are

| | |
|---|---|
| Project slug | `magiq-media` |
| Project folder | `Z:\claudia\magiq\projects\magiq-media` |
| Review | **MM-040** — `Z:\claudia\magiq\projects\magiq-media\reviews\domain-flow\domain-flow-review-2026-09-13.md` |
| Review todo id | `3d6eb9fb-9fbf-5c65-97b7-6a7050802830` |
| Plan | **MM-041** — `Z:\claudia\magiq\projects\magiq-media\plans\domain-flow\domain-flow-review-2026-09-13.md` |
| Plan todo id | `5fc762ca-dc8a-58ed-94bb-f7f99f670129` |
| Code / spec repo | `D:\source\github\sprbrk-standard\mgq-magiq-media` |
| Workstream slug | `domain-flow` |
| Finding id prefix | `DF-` |

## First action, before anything else

Write a card comment recording what you are picking up and the state you found it in:

```bash
python -c "from tower import cycle; cycle.comment('magiq-media', 'MM-041', '<what you are starting, and the state you found it in>')"
```

Run it from the AIS-OS repo root (`Z:\claudia\magiq`). The card's status is **projected from the file's
front-matter and cannot be set from the board** — a `PATCH` against a cycle card returns 409. Do not try.
The only way a status changes is you writing it into front-matter.

## What to read first

1. **MM-040 in full.** It is the argument; everything below depends on having read it. Eighteen findings,
   `DF-1 … DF-18`, derived from reading `docs/spec/` as a whole and tracing each lifecycle end to end.
2. **MM-041 in full.** The plan is already written. It owns **DF-1 … DF-4 only**, and Phase 0 is four
   decisions that gate everything else.
3. `D:\source\github\sprbrk-standard\mgq-magiq-media\CLAUDE.md` — stack, conventions, module and host
   layout. Read it before touching spec or code.
4. The spec files MM-040 cites per finding, under `mgq-magiq-media\docs\spec\`. That repo is the **only**
   copy of the spec and ADRs; nothing is published or mirrored, so a spec change reaches readers only
   through a PR there.

## Scope

**In scope:** `DF-1`, `DF-2`, `DF-3`, `DF-4` — and only those. They are the four findings MM-040 raised
that no other workstream already owns.

**Out of scope, with owners that already exist:**

| Findings | Owner |
|---|---|
| DF-7 | MM-025 / MM-026 `archive-cascade` — X-11.17 open |
| DF-5, DF-6 | MM-032 `projection-rebuild`, parked |
| DF-11, DF-16 | MM-030 / MM-035 `event-reliability` |
| DF-12 | MM-038 `document-signing`, parked |
| DF-8, DF-9, DF-14, DF-15 | **No owner.** One problem, four faces — the pinned-vocabulary seam. MM-040 argues they will not converge if fixed separately. Candidate for the next workstream; do not start it here |
| DF-10, DF-13, DF-17, DF-18 | The drift review, MM-022 |

**Authorization and authentication are out of scope by instruction.** Nothing in this workstream is a
guard, claim or role finding.

## How to work findings

- **Evidence before conclusion.** State what the file says, then what follows from it.
- **Cite `file:line`** for every claim. Where two spec files disagree, cite both.
- **Do not fix code during a review.** A review argues; the plan sequences. If you are executing MM-041,
  you are past that line — but the rule still holds for anything you notice outside DF-1…DF-4.
- **Severity is `High` / `Medium` / `Low`.** Never 🔴/🟠/🟡 — those belong to `type: gate` documents only,
  where they mean "blocks the release flag flip" rather than "is bad". A High finding is not automatically
  a gate blocker; `plans/prod-readiness/prod-readiness-gate.md` makes that call, and a review must not
  pre-empt it.

## Anything you find outside scope

It does **not** go into MM-040's findings and it does **not** become a new checklist item in MM-041.
Surface it and ask where it belongs — the global drift register (an `X-` number in MM-022) or a new review
in the right workstream. If a new finding invalidates MM-041's approach, **stop**; do not re-plan in
place. Chase decides whether the review reopens or a new one starts. Record any such diversion in the
plan's session log.

The one edit you may make to the checklist without asking: closing, splitting or correcting an item that
already traces to a finding MM-041 consumes. A split keeps the original finding id on both halves.

## The gate on the plan

MM-040 is at `status: done`, `outcome: plan`, with zero `**Open**` questions, and MM-041 is `active`. The
hand-over is complete: plan written, review closed, both READMEs updated, dependency status resolved
(`depends-on: []`, `blocked-by-external: []`). **Execution may begin.**

If you are instead reopening the review, the gate re-applies in full: no plan work until every open
question is answered **and Chase has moved the review to `findings-agreed`**. That transition is Chase's
to make and is never inferred, however few questions remain.

## Working the plan

MM-041 is already written — **do not re-author it.** Its shape, for reference and for any phase you add:

- A phase is a `## Phase <N> — <name>` heading, an intro line, then a checklist of `- [ ]` items each
  small enough to finish in one session.
- Every item names the finding id it closes and its acceptance check.
- A phase blocked by a dependency says so in the body.

The heading shape is load-bearing, not cosmetic: `ado-create-from-plan` reads `## Phase <N> — <name>` to
find Features, and keys its branch table on the same `<N> — <name>`.

**Start at Phase 0.** It is four decisions — D1 (`active-registrations` semantics, and X-11.40 in the same
call), D2 (is the `RequiredForEdit` gate a real invariant), D3 and D4 (retention). Nothing in Phases 1–4
starts without them. Following MM-031's precedent: these need a decision, not more research.

**Tick checkboxes in the file as work lands**, so the next session resumes from the file rather than from
chat history.

## ADO

`ado:` in MM-041's front-matter is `-` and stays `-`. Pushing a plan to the board is a separate, explicit
step run through `ado-create-from-plan` once the plan is `active` — never during a review, and most plans
never go to the board at all. The field is a slot for that step to fill, not something to populate by
hand. **Do not create ADO items as part of this cycle.**

This workstream is **not** board-tracked today, so MM-041 carries no `## ADO mapping` block. Leave it
that way rather than filling one with placeholders.

## End-of-session protocol

Non-negotiable, every session, including one that achieves nothing:

1. Update the checklist in MM-041.
2. Update front-matter `status:` in the same edit as whatever made it true. There is no separate board
   update — the file is the only writer.
3. Append any branch you cut to `branches:` in the front-matter.
4. **Write the closing card comment** — what moved, what did not, and **the next concrete action**:

   ```bash
   python -c "from tower import cycle; cycle.comment('magiq-media', 'MM-041', '<what moved, what did not, next concrete action>')"
   ```

   Lead with the outcome, not the activity. Name finding and document ids so entries are greppable. Two or
   three sentences. The timestamp and author are recorded for you — do not write the date. Do not log
   individual file edits or commands run; the card is a log of decisions and outcomes, not a transcript.

MM-041 is `done` only when Chase agrees the work is implemented and complete, and only with at least one
recorded branch. Its `## Definition of done` lists the six conditions.
