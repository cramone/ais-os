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
| MM-003 | `spec-baseline` | [Spec Baseline — Remediation Plan](./spec-baseline/spec-baseline-review-2026-09-16.md) | **Done** 2026-09-18 — awaiting archive | [MM-001](../reviews/spec-baseline/spec-baseline-review-2026-09-16.md) | none (was `AP-001`; removed 2026-09-18) |

### MM-003 — shape and state

**Closed `done` on 2026-09-18. Ten phases on `spec/initial-alignment-work`, all closed.** Documents only.
The guard runs seven checks and passes, with an **empty baseline** — the arc was 209 → 192 → 187 → 7 → 0,
and it only ever shrank.

> **Closed is not integrated.** At close, `spec/initial-alignment-work` was **78 commits ahead of
> `origin/develop` and 3 behind**, with **4 unpushed**. MM-006 is stacked behind the same branch and never
> reached develop either. **Archive is held until that is settled** — archiving a workstream whose commits
> are unpushed hides where the work actually is.

Phase 0 was first rather than last on purpose. The previous remediation attempt made the same call in the
same words — *"stripping without a guard just resets the clock"* — recorded the guard as done, and never
wrote it; `.github/scripts/__pycache__` was all that survived. Nine phases of editing with no detector
running is how the citations got in.

**Phase 10 was lifted out on 2026-09-18 and is now [ADO #35118](https://dev.azure.com/MAGIQSoftware/Media/_workitems/edit/35118).**
It was the SDK release gate, and it was the one phase that contradicted this plan's documents-only scope.
Two things happened the same day: the repo `CLAUDE.md` inverted the spec-versus-code rule — the spec is
authoritative, a gap is a **code** defect — and `AP-001` was **removed** from `aspnetcore-platform` rather
than shipped. That left two code-and-release boxes with no dependency to track them, so they moved to the
board.

**What has not changed is the gap.** `Magiq.AspNetCore.Idempotency` still does replay rejection while the
spec states IETF draft-07 conformance. SB-20, SB-72, SB-73, SB-74 and SB-76 are closed **as
specification** and open **as behaviour** until #35118 ships. The record of that lives permanently in the
repo `CLAUDE.md` § Known deferred/partial work, which § *When the spec and the code disagree* cites as its
worked example — **it is not a marker to delete when the SDK catches up.**

**Largest phase by far was 4b** — every write command *and every query* across ten aggregates got a scope
and, where the resource is owner- or membership-scoped, a resource predicate. **A row with a scope and no
predicate on an owner-scoped resource is wrong**; that was the rule most likely to be lost in the volume.

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
