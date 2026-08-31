# Plans — magiq-media

_Reorganised 2026-08-24 from a flat folder into one subfolder per workstream. Nothing was deleted or
rewritten; only locations changed, plus the references that pointed at the old paths._

Each subfolder is a workstream you would pick up as a unit, and each carries its own `Archive/` for the
plans that workstream has finished with. `plans/Archive/` at this level holds completed work with no live
workstream left.

**Status vocabulary** — the full set, matching the `review-cycle` skill's front-matter. Nothing outside
this list: _Draft_ — a review exists, not yet agreed · _Active_ — being worked now · _Active (blocked)_ —
waiting on a dependency, which is derived, never set by hand · _Parked_ — real but deliberately not being
worked · _Superseded_ — replaced by another plan, kept for reasoning · _Done_ — closed out.

**Document ids — backfill started 2026-08-31.** `projection-tables/` (MM-001, MM-002),
`deployment-naming/` (MM-004) and `prod-readiness/` (MM-006, the gate) carry `id:` and front-matter.
Every other plan here is still legacy: no id, status **UNKNOWN** per the `review-cycle` skill's
§ Legacy files — do not treat any of them as met, unmet, active or done, and do not name one in a
`depends-on`. Continue one workstream at a time. Do not bulk-rewrite.

**Every plan is now either paired with a review or marked `exception:`.** A sweep on 2026-08-31 found
seven plans with no review — all archived, all predating the convention — and four documents living
in `plans/` that are not plans at all (an operating brief, an ADO id index, a resume manifest, a
hand-off doc). None were back-filled with a review: three of the seven never shipped, so a
retrospective review would be inventing the argument the cycle exists to make. Each carries a
one-line `exception:` saying why instead.

`cycle.check('magiq-media')` enforces this from here — a new plan whose workstream has no review is
flagged, and the only way to silence it is an `exception:` line someone has to write and stand
behind. `cycle.known_exceptions('magiq-media')` lists all seventeen.

---

## `authorization/` — the missing authorization layer, opened 2026-08-26

**Both 🔴 prod-readiness blockers live here.** Paired with `reviews/authorization/`.

| Plan | Status | What it is |
|---|---|---|
| `authorization-review-2026-08-25.md` | **Active** | Named for the review it consumes, per the folder convention. **X-11.31 and X-11.23 closed 2026-08-26; X-11.30 open at 81 commands, 61 HTTP-reachable.** |

The step that reshaped the workstream: **`magiq-auth` issues no `roles` claim and no `actor_type`
claim** — verified against its source, not its docs. So a role check admits nobody, `ActorType` is
always `"User"` over HTTP, and the System half of `AssetOwnership.CheckOwner` and `ForceReleaseCheckout`
is dead in practice. The X-11.31 guard is written against roles anyway (Chase's call) so it starts
working the moment the identity provider emits the claim. **X-11.30 is now blocked on another team**,
which makes `docs/spec/shared/magiq-auth-role-claims-requirements.md` — the hand-off, written and
unsent — the critical path rather than an errand.

**The X-11.31 change has never been compiled.** No .NET SDK in the session. Build and test before PR.

## `archive-cascade/` — the archive fan-out, opened 2026-08-27

Paired with `reviews/archive-cascade/`. Two 🟠 gate blockers closed, two still open.

| Plan | Status | What it is |
|---|---|---|
| `archive-cascade-review-2026-08-25.md` | **Active** | Named for the review it consumes. **X-11.16 and X-11.18 closed 2026-08-27; X-11.41, X-11.17, X-11.15, X-11.19 open.** |

The decision the workstream turned on — the review's open question 1 — was answered **continue and
suppress ancestors**, not abort: the cascade archives everything it can, records every refusal, and
declines to archive the refusing child's folder and every folder above it. That keeps the un-archived
remainder a connected subtree containing the root, which is what closes X-11.18, and it makes an archived
folder a truthful claim about its own subtree for the first time. The review framed continuing as
requiring the traversal index to stop pruning; that is only true if you continue *upward*.

**Both workers now have tests** — they had none, which is the most likely reason all six findings went
unnoticed. Steps 2–5 extend those fixtures rather than starting cold.

**The step-1 change has never been compiled.** No .NET SDK in the session — the same gap as X-11.31. Run
`dotnet test tests/modules/Catalog/` before treating either finding as closed; the plan lists the likely
compile risks in order.

## `spec-drift-review/` — spec ↔ repo drift

The current live workstream.

| Plan | Status | What it is |
|---|---|---|
| `spec-repo-drift-review.md` | **Active** | 58 open findings across spec, ADRs, CDK and platform. The working checklist — tick the ✓ column as items land. |
| `spec-ddd-coverage-review-2026-08-24.md` | **Active** | Remediation plan for the DDD coverage review of the same name. Six phases from "stop the file truncation" through the saga specs, authorization matrix and MediaItem state matrix. **Phase 1 complete 2026-08-25** — a full-history search recovered 15 of the 17 truncated spec tails (7 only from `Media.wiki`'s history). Dating the sources then split them: 12 link/row tails restored and checked against code, 3 prose tails **quarantined to `docs/spec/_recovered/`** because they predate the 2026-08-24 correction pass, 2 unrecoverable. Phase 3 drops from 3–5 days to ~1 day over 5 files. The check also surfaced **X-11.1 (High)** in the drift review: the spec's traceability tables name projector classes that don't exist, 69 times. D2 resolved; D1, D3–D6 still block Phases 2 and 4. §2 draws the ownership line against the drift review so nothing is worked twice. |
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

**Under the cycle since 2026-08-31.** Paired with `reviews/projection-tables/` (MM-003).

| Id | Plan | Status | What it is |
|---|---|---|---|
| MM-002 | `schema-versioned-projection-tables-plan.md` | **Parked** | Schema-versioned, CDK-owned projection tables. **Phase A shipped** — verified at source level by MM-003 against all three repos. Parked on **Phase B only** (version-aware projectors), deferred by the decision in `docs/adrs/persistence-and-eventing.md` until the first breaking read-model change needs a zero read/write window. |
| MM-001 | `Archive/hot-swappable-projection-rotation-plan.md` | Superseded | Blue-green **runtime** rotation (`_v{n}`). Never built as written — the runtime counter meant CDK could not own the tables, which forced a broad `table/media-*` control-plane grant. Kept for the discovery and the rotation-unit decision, both of which MM-002 § 3.1 carries forward. Archived 2026-08-31. |
| — | `Archive/projection-replay-platform.md` | Done | Platform-side projection replay. |
| — | `Archive/dynamodb-schema-audit-plan.md` | Done | CDK ↔ spec table audit; DocumentSigning was never covered. |

**Read MM-003 before touching this.** Two things it found that the plan does not say: Phase B's
deferral has a **trigger nobody monitors** — no check fires when a `schemaVersion` bumps (PT-2) — and
the implementation **straddles a merge boundary**, with `develop` (2026-07-29) holding the platform
and manifest work and `feature/change-requests` (2026-08-27, pushed, unmerged) holding the later
refinements (PT-4). Nothing here has been compiled or run.

## `deployment-naming/` — resource naming and environments

**Under the cycle since 2026-08-31.** Paired with `reviews/deployment-naming/` (MM-005).

| Id | Plan | Status | What it is |
|---|---|---|---|
| MM-004 | `remove-env-suffix-plan.md` | **Active** | Drop the `-{env}` suffix from every resource name. **Code complete in both repos**, verified at source level by MM-005; three of the four opening decisions were taken and implemented. **One item outstanding — the ADR** (`docs/adrs/deployment-and-resource-naming.md`, change-inventory item 13), which was meant to land *before* the code and never did. `docs/adrs/README.md:20` flags the gap itself. That is finding DN-1 and the only thing between this plan and `done`. |
| — | `Archive/deploy-handoff-tom.md` | Superseded | The dispatch-only deploy model, replaced by `deploy-runbook.md` in the project root. |

The consequence the ADR most needs to carry: renaming a stateful resource makes CloudFormation
*replace* it, so dev/qa/staging lose data on cutover. Prod naming is unchanged either way.

## `design/` — feature design and per-module remediation

| Plan | Status | What it is |
|---|---|---|
| `mediaitem-edit-session-design.html` | Active | MediaItem edit-session design. |
| `Archive/metadata-collision-prevention.md` | Done | Metadata field-name collision prevention. |
| `Archive/content-category-remediation-plan.md` | Done | `MediaContentType` → `MediaCategory` + MIME classification. |
| `Archive/asset-download-endpoints.md` | Done | Presigned S3 GET endpoints for originals and renditions. |

## `Archive/` — completed, no live workstream

Paired with `reviews/Archive/`: `api-consistency-remediation-plan.md` ← `api-rest-review.md` (Stage 5
acceptance was blocked on a spec-tree truncation incident — worth a look before assuming it is
finished; `handler-status-code-review.md` folded into its status-code stage) ·
`s13-uniqueness-atomicity-remediation-plan.md` and its runbook
`s13-implementation-plan-for-claude-code.md` ← `architecture-spec-review.md`.

Unpaired, and marked `exception:` 2026-08-31 rather than back-filled:
`Endpoint-ReadModel-Separation.md` (archived at 0 of 76 items ticked) · `docs-migration-plan.md` (the
spec/ADR move to `D:\source\github\magiq-media\docs\` did happen 2026-07-07, but the GitHub
Actions wiki-publish step it specifies is still unbuilt).

> **Moved 2026-08-31:** `request-response-review.md` → `reviews/Archive/`. It is a review — 866 lines
> titled "Request/Response Model Review" — and was the only one sitting in the plans tree without the
> working-checklist justification that keeps `spec-drift-review/spec-repo-drift-review.md` there.

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

---

## `prod-readiness/` — MM-006, the gate, created 2026-08-25

**`prod-readiness-gate.md` is a gate, not a backlog.** It triages the **42 open code findings** from the
spec-drift review into what must close before `PROD_ENABLED` (or `STAGING_ENABLED`) is set to `true`, and
what can be scheduled normally. `spec-repo-drift-review.md` remains the source of truth for *what each
finding is*; this file only answers **which of them block a release**.

**The fact it turns on:** nothing is in production — both flags are unset and only `dev`/`qa` deploy. So no
finding is exploitable today; the risk is that they go live silently when the flags are flipped. Two 🔴
security blockers and six 🟠 data-loss/compliance blockers.

**Updated 2026-08-26: X-11.31 is closed** — the escalation path that made the rest of the authorization
gaps compound is shut, so **X-11.30 is the only 🔴 left**, at 81 commands rather than 86. It is now
blocked on `magiq-auth` issuing role claims; see the `authorization/` workstream above. The six 🟠 rows
are untouched and are the next thing to pick up if the identity provider work is slow.
