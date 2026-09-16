# Reviews — magiq-media

**Work goes through a review before it gets a plan.** The review argues the findings; the plan sequences
them and tracks execution. The convention is in [`../CLAUDE.md`](../CLAUDE.md) § Review → Plan and
§ Review → Plan cycle; the machinery is the `review-cycle` skill.

One subfolder per workstream. `reviews/<workstream>/` pairs with `plans/<workstream>/` — **the folder name
is the link**, and it is what survives archiving.

> ⚠ **This index was created on 2026-09-16 and is not known to be complete.**
> This working copy had no `reviews/` or `plans/` tree when MM-044 was written. The repo spec cites six
> plan ids — MM-004, MM-026, MM-040, MM-041, MM-042, MM-043 — and **none of them exists; none should have
> been cited in a spec file at all** (Chase, 2026-09-16). Those 43 citations are a defect in the spec,
> tracked as finding **SI-5**, not evidence about this tree.
>
> **Consequence for id minting:** MM-044 and MM-045 were minted from the highest id appearing in the repo
> spec, which is now known to have been no evidence at all. **The true high-water mark is unknown.** Before
> any document cross-references them, run the real grep across `reviews/`, `requests/`, `plans/` **and
> `_archive/`**. Above MM-043 → they collide and must be re-minted. Genuinely empty → they may be
> renumbered from MM-001, which is tidier and equally valid while nothing points at them. Chase's call
> either way; ids are never silently renumbered. **MM-045 Phase 0, first item.**

---

## Live

| Id | Workstream | Review | Status | Outcome | Plan |
|---|---|---|---|---|---|
| MM-044 | `spec-coherence` | [Spec Coherence — Aggregates and Relationships](./spec-coherence/spec-coherence-review-2026-09-16.md) | Done | plan | [MM-045](../plans/spec-coherence/spec-coherence-review-2026-09-16.md) — Active |

**Findings agreed and the review closed 2026-09-16.** MM-045 is written and active; hand-over complete.
This file is now frozen — no edits, no status changes, no re-scoping. Only two additive cases may touch it:
a `folded-into` review being added to a closed plan's `consumes:`, and a `supersedes:` pointer on a gate.

### MM-044 — what it found, and what settled it

A design review of the spec documents (`docs/spec/` + `docs/adrs/`), aggregate by aggregate and then
relationship by relationship: design flaws, inconsistencies, contradictions and invalid invariants. Code
was not read; authorization was excluded. ~190 findings across eleven aggregates, nine relationship edges,
ten systemic patterns and four spec-integrity findings.

Its § Recommended sequencing carries the eleven-phase order and the three convergence loops — that section
is what MM-045 transcribes rather than re-derives.

**All fourteen open questions are answered as of 2026-09-16.** Ten were settled in the review itself from
records-management and media-management practice, with the reasoning stated so each can be overturned on
its merits. Four were Chase's and are now closed:

1. **Q11** — no live subscribers to `media.item.published`. E-1 is a documentation fix; no migration, no
   notice owed downstream.
2. **Q12** — `BulkFolderImportJob` and `BulkMediaImportJob` are **removed** from the spec. The inventory
   becomes nine coded aggregates plus two specified-and-unbuilt. The inline bulk *endpoints* are unaffected.
3. **Q13** — **no `MM-nnn` id exists, and none should have been cited in a spec file in the first place.**
   All 43 citations across 14 files are stripped and every rule that leaned on one is restated in its own
   terms. Raised as **SI-5** at `Critical`: the repo `CLAUDE.md` already forbids decisions and reasons in
   spec files, and `spec/README.md` row 14 already names the off-repo project as the wrong place to send a
   reader.

4. **Q14** — the same defect in three more id families (**SI-6**, 78 occurrences across 24 files). Resolved
   by splitting them. **`DEC-n` is the decision log of MM-042**, a prior aggregate-design review — the same
   job this one is doing. All fourteen cited decisions were recovered from their citation sites, where the
   spec states each one inline, and re-adjudicated in **§ Recovered decisions**: ten adopted, one extended,
   **DEC-9 overturned** (the disposal clock does not re-stamp on a move), **DEC-3 adopted as new scope** —
   legal hold, raised as **RS-9**. Eleven of the fourteen this review had already re-derived independently.
   **`AD-n` and `X-n.n` are finding ids and are stripped outright.** Eight `DEC-` numbers were taken and
   never cited; they are unrecoverable, and the review says so rather than papering over it.

**Chase agreed the findings 2026-09-16.** The review moved `draft` → `findings-agreed` → `done` /
`outcome: plan` in that session, and MM-045 was authored against it.

---

## Archived

None in this working copy. See the warning above — archived magiq-media reviews are expected at
`_archive/reviews/<id>-<workstream>/` and that tree is not present here either.

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
