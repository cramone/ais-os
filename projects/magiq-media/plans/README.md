# Plans — magiq-media

**A plan sequences findings and tracks execution; the review that argues them comes first.** The convention
is in [`../CLAUDE.md`](../CLAUDE.md) § Review → Plan and § Review → Plan cycle; the machinery is the
`review-cycle` skill.

One subfolder per workstream. `plans/<workstream>/` pairs with `reviews/<workstream>/` — **the folder name
is the link**, and it is what survives archiving. The plan file takes the primary review's filename.

---

## Live

| Id | Workstream | Plan | Status | Consumes | Depends on |
|---|---|---|---|---|---|
| MM-003 | `spec-baseline` | [Spec Baseline — Remediation Plan](./spec-baseline/spec-baseline-review-2026-09-16.md) | Active | [MM-001](../reviews/spec-baseline/spec-baseline-review-2026-09-16.md) | `AP-001` (unmet — one item only) |

### MM-003 — shape and state

**Eleven phases** on `spec/initial-alignment-work`. Phases 0–9 are documents only; **phase 10 is a release
gate**. **Phase 1 is closed** (all ten of MM-001's questions answered) and **phase 0 is written and awaiting
commit** — the five detectors, their baseline and the CI workflow.

Phase 0 is first rather than last on purpose. The previous remediation attempt made the same call in the
same words — *"stripping without a guard just resets the clock"* — recorded the guard as done, and never
wrote it; `.github/scripts/__pycache__` was all that survived. Nine phases of editing with no detector
running is how the citations got in.

**The SDK dependency is isolated in phase 10, and it is what stops this plan closing.** Phase 5 writes the
conformant idempotency contract without waiting — the spec states what the system is *specified* to be and
is silent on whether the code has caught up, so writing it early is correct by construction rather than
premature. Phase 10 is the release step that makes it true: `AP-001` shipped, packages published,
`MagiqPlatformVersion` bumped, and the delivered behaviour checked against the text.

**Consequence for anyone working this:** phases 0–9 can all finish while the middleware still does replay
rejection. At that point the plan is *substantially* complete and **not** complete — SB-20, SB-72, SB-73,
SB-74 and SB-76 will read as closed in the spec while being open in fact. **Do not set `status: done`
while any phase 10 box is open**; comment the card instead, saying documentation is complete and naming
what it waits on. The card's status is projected from front-matter and nothing else, so that line is the
only mechanism.

`depends-on` resolves **unmet** — AP-001 is a review that has produced no plan — but status is `active`
under the partial-blocking rule. **Repoint `depends-on` at AP-001's plan id when that plan exists.**

**Largest phase by far is 4b** — every write command *and every query* across ten aggregates gets a scope
and, where the resource is owner- or membership-scoped, a resource predicate. **A row with a scope and no
predicate on an owner-scoped resource is wrong**; that is the rule most likely to be lost in the volume.

---

## Archived

| Id | Workstream | Plan | Closed | Consumed |
|---|---|---|---|---|
| MM-006 | `spec-coherence` | [`_archive/plans/MM-006-spec-coherence/`](../_archive/plans/MM-006-spec-coherence/spec-coherence-review-2026-09-17.md) | 2026-09-18 | [MM-005](../_archive/reviews/MM-005-spec-coherence/spec-coherence-review-2026-09-17.md) |

**MM-006 grew from eleven phases to thirteen, and the two it grew are the interesting ones.** Phase 11 took
in three batches the standing rules would have sent elsewhere — five contradictions an independent
verification found unprompted, six catalogued codes with no raise site, and MM-005's eleven
*could-not-settle* questions, answered by design rather than by reading code. Phase 12 caught two of the
plan's *own* changes removing a field from a shape held in the event store and writing it as a clean
deletion.

**The verification pass is the part worth reusing.** Run independently against the fourteen shared-layer
findings, it returned eleven confirmed and three partial — and every partial was the same failure: the
statement corrected where the finding pointed and left standing where it did not. It also found two defects
in the remediation's own edits. **A remediation plan checking its own work finds what it was looking for.**

Sixteen commits, on `spec/coherence-remediation` and then directly on `spec/initial-alignment-work` after
the merge. **It never reached `develop` and was never meant to** — it is stacked behind MM-003.

---

## Conventions, in short

- **Ids** — `MM-<nnn>`, monotonic, never reused, never renumbered. One id space covers reviews, feature
  requests, plans and gates. Cross-references are ids, never paths.
- **Plan status** — `active` | `blocked` | `parked` | `superseded` | `done`. Front-matter is authoritative;
  the Control Tower board is a projection of it and cannot be edited.
- **`blocked` is derived** from unmet dependencies, never set by hand. Partial blocking marks the phase,
  not the plan.
- **A phase is `## Phase <N> — <name>`.** The heading shape is parsed by `ado-create-from-plan`; do not
  reformat it.
- **A new defect never becomes a checklist item** in the plan that found it. It goes to a new review, or to
  the code-defects workstream if it is code. Log the diversion in the plan's § Session log.
- **`done` is Chase's call**, after the work is agreed complete — not when the last box is ticked.
