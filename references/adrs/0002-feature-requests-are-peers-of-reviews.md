# 0002. Feature requests are peers of reviews, not a stage before them

**Status:** Accepted
**Date:** 2026-09-07
**Owner:** Chase

## Context

The `review-cycle` skill runs a two-document work cycle: a **review** argues findings, a **plan** sequences them and tracks execution, and a **gate** triages plans against a release decision. Every document carries an id from one per-project space, and `tower/cycle.py` projects all three onto the Control Tower board as read-only cards whose status comes from the file and nowhere else.

The cycle had no way in for work that starts with a *request* rather than a *defect*. Someone asks for a feature; there is nothing broken to raise findings about, no severity to assign, and no `findings-agreed` transition that means anything. The two facts that matter most about such an ask — **who asked, and when** — have no field anywhere in the model. Requests were therefore either logged as interrupts (`tower/data/interrupts.json`, gitignored, disposable, and the wrong home for something durable enough to produce a plan) or not captured at all.

Two structural questions had to be settled before anything could be written.

**Where does a request sit relative to a review?** Either it is *upstream* of one — an intake step that produces a review, which produces a plan — or it is a *peer* of one, consumed by a plan directly.

**How much of the cycle does a second skill restate?** Roughly 60% of `review-cycle/SKILL.md` is machinery shared by every document type: id minting, the `todo-id` derivation, the projection contract, dependency gating, external blockers, archiving, frozen documents, the ADO hand-off. That file was already 494 lines, with a skill description long enough that adding a second document type's triggers to it would measurably degrade matching for both.

## Decision

A **fourth document type, `feature-request`**, in `projects/<slug>/requests/<workstream>/`, consumed directly by a plan.

**It is a peer of a review.** Both are *origin documents*. Either can originate a plan; a plan may consume both, mixed freely in `consumes:`. The invariant *"a plan cannot exist without a review"* becomes *"a plan cannot exist without an **origin**"*, enforced in `cycle.check()` against a new `ORIGIN_TYPES = ("review", "feature-request")`.

**It gets its own skill** — `.claude/skills/feature-request/SKILL.md` — which owns only the delta and **restates nothing**:

- front-matter: `requested-by`, `requested-on`, `request-source`
- status: `new` → `accepted` → `done` | `declined` | `parked` | `superseded`
- body: the requestor's own words quoted first, then the restatement, kept separate; no findings, no severity, no estimate
- three workflows: capture, triage, plan

Everything else is referenced back to `review-cycle` by section, with an explicit precedence rule: **where the two disagree on shared machinery, `review-cycle` wins.** `workstream-query` already establishes this shape — a separate skill that reads the same front-matter and duplicates none of its rules.

**One id space** across all four types. There is no `FR-` space.

`request-source` reuses the `tower/interrupts/store.py` source enum plus `Customer`, so an interrupt that turns out to be a feature ask graduates into a request without a translation table.

An `outcome: review:<id>` escape hatch covers the case where a request genuinely needs investigating before it can be planned: it raises a review through `review-cycle`, and the plan then consumes both.

## Consequences

- **Easier:** requests are durable, versioned, and greppable with the same tooling as everything else; "who asked for this and when" survives the six weeks until the scope question arrives; `declined` costs one status change and one sentence, so the backlog can shrink; the board shows all four types with one projection and no sync.
- **Easier:** the integrity check got **stricter** in passing. The old `_check_plans_have_reviews` accepted any non-empty `consumes:`; `_check_plans_have_origins` verifies at least one named id is actually an origin type, so a plan consuming only other plans or a gate now trips. `cycle.check()` is clean across all 8 projects after the change.
- **Harder / accepted:** two skills now describe one cycle, and the split is only safe because the second restates nothing. Any future shared rule must be written in `review-cycle` and referenced, never copied — a copy will drift, and the drift will be invisible until someone reads both.
- **Harder / accepted:** `requests/` is a third folder in `DOC_FOLDERS`, so every scan touches one more tree. Negligible at this size; worth noting if project trees grow.
- **Watch for:** if requests routinely need a feasibility argument before planning, the `review:<id>` escape hatch becomes the norm rather than the exception — which is the signal that the upstream model was right after all and this decision should be revisited.

## Alternatives considered

**Extend `review-cycle` with the new type.** Cheapest edit. Rejected: the file and its description are already at the size where adding a second vocabulary hurts both triggering and readability, and review statuses (`draft`, `findings-agreed`) plus findings-with-severity are simply the wrong shape for an ask that describes nothing broken.

**A standalone skill duplicating the conventions.** Fastest to write, worst to own. Rejected: two copies of id minting, status mapping and dependency gating drift, and the copy that goes stale is the one someone reads.

**The upstream model — feature request → review → plan, always.** Truer for a large ask that needs a feasibility argument. Rejected: pure ceremony for "add a CSV export button", which is most requests. The `outcome: review:<id>` hatch buys the same rigour opt-in, where it is warranted, instead of taxing every request for the minority that need it.

**Filing requests inside `reviews/<ws>/`.** Avoids touching `DOC_FOLDERS` entirely. Rejected: `reviews/README.md` is built around findings, severity and outcome-of-investigation; one index holding both species reads as neither, and the cost avoided was a single tuple entry.

**A separate `FR-` id space.** Superficially tidier. Rejected: `consumes` and `depends-on` resolve by one regex over one namespace, so a second space would not fail loudly — it would fail *silently*, which is the worst available outcome for a cross-reference.
