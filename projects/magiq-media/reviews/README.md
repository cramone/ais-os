# Reviews — magiq-media

_Reorganised 2026-08-24 to mirror `plans/`, one subfolder per workstream. Nothing was rewritten; only
locations changed, plus the references that pointed at the old paths._

**A review is where work starts.** Findings get argued here; sequencing, PR shaping and execution
tracking happen in the matching `plans/` folder. The folder name is shared between the two trees, so a
review and the plan that consumes it stay traceable — including after both are archived. See
`CLAUDE.md § Review → Plan` for the convention in full.

| This folder | Its plans |
|---|---|
| `reviews/architecture-review-remediation/` | `plans/architecture-review-remediation/` |
| `reviews/spec-drift-review/` | `plans/spec-drift-review/` |
| `reviews/spec-structure/` | *(no plan yet — most of it lands in `plans/spec-drift-review/`)* |
| `reviews/design/` | `plans/design/` |
| `reviews/Archive/` | `plans/Archive/` |

---

## `architecture-review-remediation/` — the 2026-07-19 architecture pass

Eleven reviews, read together and consumed as one body of work by
`plans/architecture-review-remediation/architecture-review-remediation-pr-plan.md`. Finding IDs and
severities are theirs; the plan only sequences them.

Per module: `assetmanagement` · `catalog-collection` · `catalog-folder` · `catalog-mediaitem` ·
`catalog-mediaprofile` · `changerequests` · `metadata-recordtype` · `processing-processingjob` ·
`registration-registration`.

Cross-cutting: `cross-module-integration-review.md` (the seams between modules) and
`cross-module-impact-sweep-2026-07-19.md` (what each finding breaks elsewhere).

> The plans referred to these as living in `D:\source\github\magiq-media\docs\reviews\`. That folder
> exists in the repo and is **empty** — the reviews never moved there. Corrected 2026-08-24.

## `spec-drift-review/` — the spec, interrogated

| Review | What it asks |
|---|---|
| `spec-ddd-coverage-review-2026-08-24.md` | Are the 14 DDD dimensions covered across 68 spec files? Spec only, no code read — every finding is "the spec does not say", not "the code does not do". Consumed by `plans/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md` — same filename, per the convention. |

## `spec-structure/` — where each dimension should live

| Review | What it asks |
|---|---|
| `spec-structure-recommendation-2026-08-25.md` | Given the repo as it stands, what structure guarantees the 16 DDD/spec dimensions each have **one** owning file? Verdict: 12 are already well covered — every gap is a dimension that spans aggregates, so it has either been duplicated into every overview (glossary ×8, bounded contexts ×3, aggregate inventory ×3 disagreeing) or has no home at all (sagas, eventual-consistency policy, cascade rules, contradiction register). Recommends +7 files, one merge, one split, and required-section checks in CI. Most of the work already sits in the DDD plan's Phases 2/4a/5; four items are new. |

> The drift review itself — `plans/spec-drift-review/spec-repo-drift-review.md` — is both a review and
> its own working checklist, so it lives on the plans side where the ✓ column is worked. It is the one
> document that does not follow the review-then-plan split, because splitting it would separate the
> findings from the checkboxes that track them.

## `design/` — feature design review

| Review | Produced |
|---|---|
| `mediaitem-edit-lifecycle-as-is-vs-recommended.html` | `plans/design/mediaitem-edit-session-design.html` |

## `Archive/` — reviews whose work is finished

| Review | Plan it produced |
|---|---|
| `api-rest-review.md` | `plans/Archive/api-consistency-remediation-plan.md` |
| `architecture-spec-review.md` | `plans/Archive/s13-uniqueness-atomicity-remediation-plan.md` + its implementation runbook (finding S13) |
| `handler-status-code-review.md` | Folded into the API-consistency plan (status-code stage) |

> S13's subject — name-reservation atomicity and name-release paths — is live again as **X-9.6** in the
> drift review. Read the S13 review before re-deriving that history.
