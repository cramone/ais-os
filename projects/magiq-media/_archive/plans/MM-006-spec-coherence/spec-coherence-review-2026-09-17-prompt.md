# Execution prompt — MM-006, spec-coherence

Paste into a fresh session. It assumes no prior context.

---

## Where you are

**Project:** `magiq-media` · **Plan:** `MM-006` · **Consumes:** `MM-005`
**Plan:** `Z:\claudia\magiq\projects\magiq-media\plans\spec-coherence\spec-coherence-review-2026-09-17.md`
**Review:** `Z:\claudia\magiq\projects\magiq-media\reviews\spec-coherence\spec-coherence-review-2026-09-17.md`
**Repo:** `D:\source\github\sprbrk-standard\mgq-magiq-media` · **Branch:** `spec/coherence-remediation`, to be cut from `develop`
**Todo id:** `eecf8c43-1452-5bef-9920-42fbe4712d27`

**State at hand-over:** phase 1 closed — all fifteen questions answered 2026-09-18. Phases 0 and 2–10
untouched. 51 findings, all reachable from the plan. **Nothing is blocked**: `depends-on` is empty, there
is no external blocker, and every finding is spec-internal.

**You are editing `docs/spec/`.** MM-005 was a review and was forbidden from touching it. That order is
now reversed — this plan's whole job is to change those files.

## First action, before anything else

```bash
python -c "from tower import cycle; cycle.comment('magiq-media', 'MM-006', 'Picked up MM-006. Found: <state>. Working: <phase and items>.')"
```

Run from `Z:\claudia\magiq` so `tower` imports. The card's status is projected from the plan's front-matter
and **cannot be set from the board** — do not try.

## Second action — run the dependency gate

Required at every session start and every phase boundary, not just the first.

1. Read `depends-on` in the plan's front-matter: `[]`.
2. Read `blocked-by-external`: `[]`.
3. **All clear → `status: active`.** This is the expected result and it should stay that way. If something
   later makes a phase wait on another document, mark the phase, not the plan.

Nothing here waits on `AP-001`. **Do not inherit MM-003's gate** — that plan cannot close without an SDK
release; this one can.

## Read before editing anything

1. **The plan**, in full — especially § The shape of the work and § What must not be lost.
2. **`D:\source\github\sprbrk-standard\mgq-magiq-media\CLAUDE.md` § Spec files state the specified
   system** — the rule every edit is measured against.
3. **`MM-005` § Open Questions** — fifteen answers, each with the effect on the finding list. **This is the
   reasoning behind most of the plan's items.** An item that looks arbitrary usually has its justification
   there.
4. `Z:\claudia\magiq\projects\magiq-media\MEMORY.md`.

Read `MM-005`'s findings as you reach each phase, not upfront — 51 findings will not stay in your head, and
each plan item names the ones it closes. Every finding carries `file:line` evidence with verbatim quotes;
**re-read the surrounding section before editing**, because line numbers move as you work.

## Two answers that are not what a reader would guess

Both were chosen against the options as framed, and a session working from instinct will get them wrong.

- **Q2 — `RetentionScheduleRef`.** Chase picked a third position: the member **is declared** on
  `MediaProfile` (nullable, at most one), and **publishing is never gated on it**. Not "wire the gate", not
  "drop the claims". So: add the property, command, event, snapshot member and read-model field — *and*
  delete the publish requirement from three files. **No refusal code is needed**, which is the part most
  likely to get added by reflex.
- **Q8 — the rendition trigger.** The fix is a **filter-policy change, not new infrastructure**.
  `ProcessingJobStarted` already publishes to `media-integration-events` and `media-processing` already
  subscribes to it. Do not create a queue.

## The four standing rules

In the plan, and repeated here because they are the ones most easily lost mid-session.

1. **The guard is the acceptance check.** `python .github/scripts/docs_guard.py` from the repo root must
   return pass at every phase exit — **eight checks once phase 0 lands**, five before. The baseline is at
   **zero** after MM-003 phase 9 and **must never grow**. If a new hit is a legitimate design statement,
   fix the wording rather than baselining it away.
2. **Never invent design.** If closing an item would mean asserting behaviour no document states and no
   `MM-005` answer covers — **stop and ask.** Phases 7 and 8 are where this bites: they write new
   specification. Phase 8's reviewer-withdrawal item has a sub-decision inside it that is not yet made.
3. **Never reintroduce what was removed.** No citation to anything undefined in `docs/`, no build or
   implementation status, no rationale, no open questions, no dates, no attribution. **Three of this plan's
   corrections delete prose that argues rather than states** — SC-001's worked example, SC-002's summary,
   SC-005's bullet — and the replacement in each case is a *pointer*, not a shorter argument.
4. **A new defect never becomes a checklist item here.** It goes to a new review, or to `MM-002`
   (`reviews/code-defects/`) if it is code. **Log every diversion in § Session log.** One is already
   queued: phase 2 must raise Catalog's sourceless `Processing` gate on MM-002.

**Do not edit `MM-005`.** It is `done` and frozen. Corrections to the plan go in the plan.

## Where to start

**Phase 0 — write the three detectors, before any spec file is edited.**

They do not exist yet. MM-005 found three blind spots in `docs_guard.py`, each from a live instance:
`dates` misses year-month (`README.md:110` carries `2026-08`); `links` cannot see a plain-text `.md`
reference (eleven citations of a deleted `system-spec.md`) or an unclosed `](` (`asset.api.md:768`);
`structure` looks at a file's *end*, so a mid-file truncation passes.

Each new check should **fire on its known instance before the phase that fixes it, and return zero after**
— that is how you know it works. Do not baseline any of them.

**Do not start phase 2 before phase 0 is committed and its workflow has run green on the branch.** This
plan deviates from MM-005's own § Recommended sequencing to put the detectors first, on MM-003's phase 0
precedent: *"stripping without a guard just resets the clock."* Two of the three catch classes this plan
is about to edit.

## Phase order is not advisory

- **Phase 2 rewrites `mediaprofile.write-model.md` § Capabilities exactly once.** Q1, Q2 and SC-032 all
  edit that section. Split them across sessions and the capability count at `:177` will be wrong at least
  once — it is "two gate behaviour, seven gate nothing" today and becomes "three … six" via SC-032 alone,
  because Q2's answer leaves `Retention` gating nothing.
- **Phase 3 is the cheapest high-value block** — thirteen findings, all corrections, one shape: delete the
  restatement, keep the pointer. One person, one pass. It is the obvious place to want to start, and it
  still comes after phase 0.
- **Phase 7 is design, not an edit.** Sizing it as a filter change because the *mechanism* is a filter
  change will underestimate it: the pipeline diagram, scenario P-3, the video branch and four "one type
  only" statements all move with it.

## One item is open on Chase

**Phase 1, second box — confirm Q3's encoding.** He answered that both the `Manage` tier and the owner
admit `force-release`. The plan reads that as `MediaItem.Manage` plus resource predicate
`item.OwnerId == actor.Id`, widened tenant-wide by `MediaItem.Manage.All` — keeping it inside
`api-permissions.md:73`'s existing `.All` rule rather than inventing an OR, and matching the mechanism Q4
adopts.

**It blocks the SC-025 item in phase 6 and nothing else.** Every other phase proceeds. Ask once, early, so
it is settled before phase 6 rather than mid-phase.

## Two things to carry to other workstreams

- **Phase 3 has a box for it:** comment MM-003's card that **phase 10 box 3 names one file and the
  idempotency contract lives in six.** Recommend widening its scope. SC-051's fix should land before that
  box runs — otherwise box 3 passes while two endpoint contracts still say the opposite, and its
  "correct the spec to the delivered behaviour" rule would revert MM-003 phase 5.
- **Phase 2 raises a code defect on MM-002:** with no capability set on any `RecordType` version,
  `Capabilities.Contains("Processing")` is permanently false and every asset takes the bypass. Where
  Catalog's gate reads its input from is a code question.

## Every session

- **Tick boxes in the file as work lands** — a later session resumes from the file, not from chat history.
- **Write `status:` in the same edit that changes what is true.** There is no board update, only this file.
- **Append each branch to `branches`** as it is cut. `spec/coherence-remediation` is not a GitFlow branch;
  that is a deliberate exception for this workstream, as `spec/initial-alignment-work` was for MM-003.
- **Close with a card comment**: what moved, what did not, and the next concrete action. Front-matter
  carries one word; the card carries the narrative, and a workstream picked up three weeks later needs
  both.

## Closing

`status: done` is **Chase's call**, after he agrees the work is complete — not when the last box is ticked.
Then archive both sides together into `_archive/reviews/MM-005-spec-coherence/` and
`_archive/plans/MM-006-spec-coherence/`, and create `_archive/` if it does not exist.
