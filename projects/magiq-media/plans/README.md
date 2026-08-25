# Plans — magiq-media

_Reorganised 2026-08-24 from a flat folder into one subfolder per workstream. Nothing was deleted or
rewritten; only locations changed, plus the references that pointed at the old paths._

Each subfolder is a workstream you would pick up as a unit, and each carries its own `Archive/` for the
plans that workstream has finished with. `plans/Archive/` at this level holds completed work with no live
workstream left.

**Status vocabulary:** _Active_ — being worked now · _Parked_ — real but deliberately not being worked ·
_Superseded_ — replaced by another plan, kept for reasoning · _Done_ — closed out.

---

## `spec-drift-review/` — spec ↔ repo drift

The current live workstream.

| Plan | Status | What it is |
|---|---|---|
| `spec-repo-drift-review.md` | **Active** | 58 open findings across spec, ADRs, CDK and platform. The working checklist — tick the ✓ column as items land. |
| `spec-ddd-coverage-review-2026-08-24.md` | **In progress** | Remediation plan for the DDD coverage review of the same name. Six phases from "stop the file truncation" through the saga specs, authorization matrix and MediaItem state matrix. **Phase 1 complete 2026-08-25** — a full-history search recovered 15 of the 17 truncated spec tails (7 only from `Media.wiki`'s history). Dating the sources then split them: 12 link/row tails restored and checked against code, 3 prose tails **quarantined to `docs/spec/_recovered/`** because they predate the 2026-08-24 correction pass, 2 unrecoverable. Phase 3 drops from 3–5 days to ~1 day over 5 files. The check also surfaced **X-11.1 (High)** in the drift review: the spec's traceability tables name projector classes that don't exist, 69 times. D2 resolved; D1, D3–D6 still block Phases 2 and 4. §2 draws the ownership line against the drift review so nothing is worked twice. |
| `Archive/spec-repo-drift-review-completed.md` | Done | The 154 closed findings plus the full session log for every pass. Split out 2026-08-24; the id sets do not overlap. |

Recent: X-9.6 (name-reservation atomicity docs), X-9.7 (`MoveMediaItem` used `SwapAsync` — every
folder-to-folder move 409'd) and X-9.8 (`GuidFactory` byte order — every id in the system unsortable)
all landed 2026-08-24. The X-9.7 and X-9.8 fixes are **written but not yet built or run**, and X-9.8 also
needs a platform package release. See `todos.md` in the project root.

> Historical context for X-9.6 lives in `Archive/s13-uniqueness-atomicity-remediation-plan.md` at the
> plans root — same subject (reservation atomicity, name-release paths), a year-earlier pass.

## `architecture-review-remediation/` — the 2026-07 architecture reviews

Largest workstream, tracked on the ADO **Media** board: 169 work items across 6 Epics.

| Plan | Status | What it is |
|---|---|---|
| `COWORK-EXECUTION-INSTRUCTIONS.md` | Active | **Start here.** How to operate a session — start, continue, end. |
| `IMPLEMENTATION-PLAN.md` | Active | The live tracker and source of truth for state. Status columns in §5, session log in §9. |
| `architecture-review-remediation-pr-plan.md` | Active | The rationale — why each finding groups into which PR, in what order. |
| `architecture-review-ado-workitems.md` | Done | ID index: Epic → Feature → Story → Task, with board URLs and dependency links. |
| `architecture-review-authz-and-outbox-deferred-plan.md` | **Parked** | Authorization (C0–C8) and the transactional outbox (B4/INV-2). Deferred in sequencing only — both remain pre-production gates. |
| `Archive/ado-creation-resume-manifest.md` | Done | Resume notes from the interrupted ADO creation run; superseded by the ID index. |

## `projection-tables/` — projection table rotation and schema versioning

| Plan | Status | What it is |
|---|---|---|
| `schema-versioned-projection-tables-plan.md` | Proposed | Schema-versioned, CDK-owned projection tables. **Supersedes** the rotation plan below. Greenfield — nothing deployed, so no live-data migration. |
| `hot-swappable-projection-rotation-plan.md` | Superseded | Blue-green runtime rotation (`_v{n}`). Kept for the discovery and the rotation-unit decision. |
| `Archive/projection-replay-platform.md` | Done | Platform-side projection replay. |
| `Archive/dynamodb-schema-audit-plan.md` | Done | CDK ↔ spec table audit; DocumentSigning was never covered. |

## `deployment-naming/` — resource naming and environments

| Plan | Status | What it is |
|---|---|---|
| `remove-env-suffix-plan.md` | **Parked** | Drop the `-{env}` suffix from every resource name. Four open decisions at the top of the plan; ADR-first. Renames every non-prod stateful resource — CloudFormation *replaces* them, so dev/qa/staging lose data. |
| `Archive/deploy-handoff-tom.md` | Superseded | The dispatch-only deploy model, replaced by `deploy-runbook.md` in the project root. |

## `design/` — feature design and per-module remediation

| Plan | Status | What it is |
|---|---|---|
| `mediaitem-edit-session-design.html` | Active | MediaItem edit-session design. |
| `Archive/metadata-collision-prevention.md` | Done | Metadata field-name collision prevention. |
| `Archive/content-category-remediation-plan.md` | Done | `MediaContentType` → `MediaCategory` + MIME classification. |
| `Archive/asset-download-endpoints.md` | Done | Presigned S3 GET endpoints for originals and renditions. |

## `Archive/` — completed, no live workstream

`api-consistency-remediation-plan.md` (Stage 5 acceptance was blocked on a spec-tree truncation
incident — worth a look before assuming it is finished) · `request-response-review.md` ·
`Endpoint-ReadModel-Separation.md` · `docs-migration-plan.md` (the spec/ADR move to
`D:\source\github\magiq-media\docs\`; the GitHub Actions wiki-publish step is still unbuilt) ·
`s13-implementation-plan-for-claude-code.md` · `s13-uniqueness-atomicity-remediation-plan.md`.

---

## References repaired in the move

Cross-references *within* a workstream were bare filenames and survived the move unchanged. These
pointed across folders and were repointed:

- `schema-versioned-projection-tables-plan.md` → the rotation plan
- `IMPLEMENTATION-PLAN.md` and `COWORK-EXECUTION-INSTRUCTIONS.md` → their own working directory
- `architecture-review-ado-workitems.md` → the resume manifest, now in its `Archive/`
- `spec-repo-drift-review.md` → `api-consistency-remediation-plan` in `plans\Archive\`
- `todos.md` → `remove-env-suffix-plan.md`
- `CLAUDE.md` file map → this structure
- `architecture-review-remediation-pr-plan.md` → its three "in-flight, do not re-plan" companions, which
  now sit in two different archives (footer note added rather than editing four inline mentions)
- `Archive/s13-implementation-plan-for-claude-code.md` → its companion design doc, now beside it
- `reviews/design/mediaitem-edit-lifecycle-as-is-vs-recommended.html` → the edit-session design doc
- In the app repo: `docs/adrs/persistence-and-eventing.md` → the schema-versioned tables plan;
  `docs/spec/contexts/Registration/.../registration.api.md` and `docs/spec/shared/error-catalog.md` →
  the drift review

Two were **already broken before the move** and are now correct:

- `deploy-runbook.md` (two places) pointed at `plans/deploy-handoff-tom.md`, archived some time ago
- the repo stub `docs/implementation-plans/api-consistency-remediation-plan.md` pointed at a plans-root
  path for a file that had been archived. Its `file:///Z:/…` link is gone rather than repointed — that
  link is drift-review finding X-7.2, unresolvable for anyone but Chase.

**Still stale, needs your hand:** the Cowork project instructions for magiq-media name
`plans\docs-migration-plan.md` as where the docs-migration follow-ups are tracked. That file is at
`plans\Archive\docs-migration-plan.md`. I cannot edit project instructions — update it in the project
settings when convenient.
