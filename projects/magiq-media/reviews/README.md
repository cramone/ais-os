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
| MM-001 | `spec-baseline` | [Spec Baseline — contradictions, gaps and the missing domain-model record](./spec-baseline/spec-baseline-review-2026-09-16.md) | Draft | pending | — |

### MM-001 — what it covers

A full read of `docs/` — 103 files across `spec/` and `adrs/`. 70 findings in six groups: authorization is
largely unspecified; the domain model contradicts itself on aggregates and relationships; eleven cross-file
contradictions; ~30 behaviour gaps; no ADR records the domain model at all; and residue the automated sweeps
could not reach.

Raised immediately after two sweeps on 2026-09-16 removed 430 off-repo citations and all build/implementation
status from the spec tree. Those sweeps are why the findings are visible — the correction notes and caveats
that were masking them are gone.

**Ten questions — one Answered, nine `Open`,** tiered by blast radius: three scope calls that change the
finding list, two domain-model rulings, three contradictions, and the ADR shape last. Question 1, the pivotal
one, is settled: authorization is
specified as **intent, in three places, and not as a matrix**. A Graph-style `Resource.Verb[.All]` vocabulary
lives once in `shared/api-permissions.md`; the endpoint → scope mapping lives per route *and per query* in each
`<agg>.api.md`; resource predicates stay as aggregate invariants. **Scopes never replace resource checks** —
`.All` widens a scope's range, it does not remove the predicate. `shared/authorization-matrix.md` is retired as
a source of truth, its privileged-command analysis moving to the domain-model ADR. That ruling reshapes
SB-1…SB-5, raises SB-68/SB-69, and closes SB-70.

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
