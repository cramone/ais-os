# Plans — magiq-media

A plan sequences an agreed review's findings and tracks execution. **A plan cannot exist without an
origin** — a review or a feature request. The convention is in [`../CLAUDE.md`](../CLAUDE.md)
§ Review → Plan; `plans/<workstream>/` mirrors [`../reviews/<workstream>/`](../reviews/README.md) and the
folder name is the link.

> ⚠ **This index was created on 2026-09-16 and is not known to be complete.** See the same warning in
> [`../reviews/README.md`](../reviews/README.md): this working copy had no `plans/` tree. The repo spec
> cites six plan ids — MM-004, MM-026, MM-040, MM-041, MM-042, MM-043 — and **none exists; none should have
> been cited in a spec file at all** (Chase, 2026-09-16). None is an authority, a dependency or a supersede
> target anywhere in this cycle. The 43 citations are a defect in the spec, tracked as finding **SI-5**, and
> MM-045 strips them and restates every rule that leaned on one. The same defect in the `DEC-`/`AD-`/`X-`
> families is **SI-6**, resolved 2026-09-16: `DEC-n` was the decision log of a prior aggregate-design
> review and all fourteen cited decisions are recovered and re-adjudicated in MM-044 § Recovered decisions;
> `AD-n` and `X-n.n` are finding ids and are stripped outright.

---

## Live

| Id | Workstream | Plan | Consumes | Status |
|---|---|---|---|---|
| MM-045 | `spec-coherence` | [Spec Coherence — Remediation Plan](./spec-coherence/spec-coherence-review-2026-09-16.md) | MM-044 | Active — Phase 0 closed, Phase 1 next |

### MM-045 — active, **Phase 0 closed 2026-09-16; start at Phase 1**

**Phase 0 is done.** All nine decision items answered; no spec file edited. Outputs:
[Appendix A — decisions](./spec-coherence/mm-045-appendix-a-phase-0-decisions.md) ·
[Appendix B — citation register](./spec-coherence/mm-045-appendix-b-citation-register.md).

Three things changed that a reader of the rest of this file needs:

- **The citation count is 228, not 43 or 121.** The 43 figure below counts `MM-` lines only; 121 counts lines
  across five families; **228** is occurrences across all eighteen families that fail MM-044's standing test
  (*an id is legitimate in a spec file only if it is defined inside `docs/`*). 120 are load-bearing.
- **Loop A's enumerated regex is retired in favour of that test.** Enumerating families is what let thirteen
  of them through.
- **Phase 1 item 1 carries a logged scope exception.** `.github/workflows/docs-guard.yml` does not exist and
  must be authored — the one artifact MM-045 produces outside `docs/`.

Written 2026-09-16 against [MM-044](../reviews/spec-coherence/spec-coherence-review-2026-09-16.md), which
is now `done` / `outcome: plan`. **Hand-over complete:** plan written, review closed, both READMEs updated,
dependency status resolved.

**Dependency gate, run at authoring:** `depends-on` empty, `blocked-by-external` empty, no cycles → clear →
`active`. Re-run at every session start and every phase boundary.

**Eleven phases, ordered outermost-authority first**, because a spec is a graph of quotations and fixing a
write model before the vocabulary it uses guarantees rework. Phase 0 is decisions only — nine of them each
land in six or seven documents, so no file is edited until they are taken. Phases 1–3 fix what everything
else quotes (vocabulary and the four missing `shared/` authorities; the inventory; the published language).
Phase 4 is one mechanical sweep. Phases 5–8 are the write models in dependency order: Metadata and
disposition, then Catalog, then Asset and Processing, then the three Catalog-driven contexts. Phase 9 is
every derived surface, deliberately last. Phase 10 reconciles the ADRs. Phase 11 is the re-baseline.

**Three nested convergence loops, each bounded.** Loop A is a ripple sweep closing every item. Loop B is the
phase-exit gate, three re-opens maximum — a fourth means the phase's scope is wrong, which is a finding
about the plan. Loop C re-runs MM-044 from its prompt in a fresh session and diffs; three iterations
maximum, and failing to converge is itself the deliverable.

**Scope is documents only** — `docs/spec/` and `docs/adrs/`. No code, no authorization. Acceptance checks
are verifiable by reading the spec.

**No dependencies, no supersede, no external blockers.** `consumes: [MM-044]` and nothing else.

---

## Archived

None in this working copy. Archived plans are expected at `_archive/plans/<id>-<workstream>/`.

---

## Conventions, in short

- **Plan status** — `active` | `blocked` | `parked` | `superseded` | `done`. `blocked` is **derived** from
  unmet dependencies, never set by hand. Front-matter is authoritative.
- **Dependency gating runs three times**: at plan authoring, at every session start on the plan, and at
  every phase boundary. Partial blocking is the common case — mark the blocked phases, do not block the
  whole plan.
- **A dangling `depends-on` id is a data error**, not a blocked state. Stop and ask.
- **A finding discovered during execution never becomes a checklist item in the plan that found it.** It
  goes to the drift register or to a new review.
- **A plan is not `done`** without Chase's explicit agreement and at least one recorded branch.
- **Archive both sides in the same session**, review and plan, into `_archive/` — then delete the emptied
  workstream folders. The live trees hold live work only.
