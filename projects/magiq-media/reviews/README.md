# Reviews — magiq-media

**Work goes through a review before it gets a plan.** The review argues the findings; the plan sequences
them and tracks execution. The convention is in [`../CLAUDE.md`](../CLAUDE.md) § Review → Plan and
§ Review → Plan cycle; the machinery is the `review-cycle` skill.

One subfolder per workstream. `reviews/<workstream>/` pairs with `plans/<workstream>/` — **the folder name
is the link**, and it is what survives archiving.

---

## Live

| Id | Workstream | Review | Status | Outcome | Plan |
|---|---|---|---|---|---|
| MM-001 | `spec-baseline` | [Spec Baseline — contradictions, gaps and the missing domain-model record](./spec-baseline/spec-baseline-review-2026-09-16.md) | **Active** — findings agreed 2026-09-16 | pending | awaiting authoring |
| MM-002 | `code-defects` | [Code defects — five clusters carried out of the retired todo file](./code-defects/code-defects-review-2026-09-16.md) | Draft | pending | — |

**MM-001 and MM-002 are the same subject from opposite sides.** MM-001 fixes a spec that never stated a
rule; MM-002 fixes code that does not enforce one. Writing the rule does not guard the command, and guarding
the command does not write the rule — neither review closes the other. Authorization is where they touch
most: MM-001 Q1 settles the permission model, and MM-002's CD-1 consumes it rather than inventing one.

### MM-002 — what it covers

Five code-defect clusters carried out of `todos.md` when that file was retired on 2026-09-16: authorization
not enforced anywhere but the five MediaProfile governance setters (Critical — an unprivileged member can
disable the guards tenant-wide); archive cascade discarding per-child failures; no outbox, a deliberate
ADR-005 divergence from the platform's own rule; seven write-side reference indexes that replay cannot
rebuild, each backing a guard; and `Asset` custody, parked behind a detach path that nothing dispatches.

**Everything here is unverified.** Findings were captured 2026-08-24 to 2026-09-01 and one item in the
source was already fixed by 2026-09-08. Re-verification is question 1 and the first sequencing step. The
~40 `X-` ids the source cited belonged to a drift register that no longer exists; each cluster is restated
in its own terms instead.

### MM-001 — what it covers

A full read of `docs/` — 103 files across `spec/` and `adrs/`. **74 findings** in six groups: authorization is
largely unspecified; the domain model contradicts itself on aggregates and relationships; cross-file
contradictions; ~30 behaviour gaps; no ADR records the domain model at all; and residue the automated sweeps
could not reach.

Raised immediately after two sweeps on 2026-09-16 removed 430 off-repo citations and all build/implementation
status from the spec tree. Those sweeps are why the findings are visible — the correction notes and caveats
that were masking them are gone.

**All ten questions answered (2026-09-16).** Worked in tiers by blast radius — scope calls first, because
three of them changed the finding list; the ADR shape last, because it depended on how many rulings turned
out to be decisions rather than corrections.

| # | Question | Answer |
|---|---|---|
| 1 | Authorization — intent or enforcement? | **Intent, in three places, not a matrix.** `Resource.Verb[.All]` vocabulary once in `shared/api-permissions.md`; endpoint → scope mapping per route *and per query* in each `<agg>.api.md`; resource predicates stay as aggregate invariants. **Scopes never replace resource checks** — `.All` widens range, it does not remove the predicate |
| 2 | Bulk-import aggregates | **Removed** — six files go; inventory 13 → 11 |
| 3 | Cross-region DR | **Out of scope** — single-region, stated explicitly |
| 4 | Date stamps | **Removed** — no date in a spec file, for any reason; CI-enforceable |
| 5 | `owner_system` | **Sentinel removed** — `OwnerId` is provenance; system authority is `actor_type` |
| 6 | `IdentityAcl` | **Type removed, ACL relationship kept**; `HttpExecutionContext` named as translator |
| 7 | Infected upload | **Quarantine**, not destroy — and the move gets specified properly |
| 8 | Folder write gating | **Not owner-gated** — follows Q5 |
| 9 | Idempotency | **Conform to IETF draft-07** — cached replay, `409` for concurrency only, fingerprint + `422` |
| 10 | ADR shape | **One foundational ADR structured by context, plus four standalone decision ADRs** |

Four of the ten were genuine decisions rather than corrections, which is why they earn their own ADRs. The
rulings raised seven new findings (SB-68…SB-74) and closed two. **Awaiting `findings-agreed`.**

---

## Archived

None. This board was reset on 2026-09-16 and the `MM-` sequence restarted at `MM-001`.

---

## Conventions, in short

- **Ids** — `MM-<nnn>`, monotonic, never reused, never renumbered. One id space covers reviews, feature
  requests, plans and gates. Cross-references are ids, never paths.
- **Review status** — `draft` → `findings-agreed` → `done` | `parked` | `superseded`. Front-matter is
  authoritative; the Control Tower board is a projection of it and cannot be edited.
- **`findings-agreed` is Chase's call**, not an inference. Until he makes it, no plan.
- **Severity** — `Critical | High | Medium | Low`. 🔴/🟠 belong to `type: gate` documents only.
- **A review must reach a terminal `outcome`.** `pending` is not a resting state.
- **Index everything from creation, including `draft`.** A review that exists and is not indexed here is
  invisible to the next session, which is the exact failure this convention prevents.
