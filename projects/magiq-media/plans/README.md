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

**Backfill completed for every live workstream, 2026-08-31.** MM-001…MM-035 gave every live review
and plan an id and front-matter, so each now appears on the Control Tower board. Statuses were
transcribed from this file and `reviews/README.md`, never inferred from a file body;
`scripts/backfill_magiq_media.py` is kept as the record of what was written and why. `Archive/`
is deliberately still legacy — those documents are finished and cards for them would only pad the
Done column.

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

| Id | Plan | Status | What it is |
|---|---|---|---|
| MM-029 | `authorization-review-2026-08-25.md` | **Blocked** | Consumes MM-028. **X-11.31 and X-11.23 closed 2026-08-26; X-11.30 open at 81 commands, 61 HTTP-reachable.** Status is `blocked`, not `active`: the remaining work *is* X-11.30 and it waits on another team, recorded as a `blocked-by-external` entry with `sent: false`. |

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

| Id | Plan | Status | What it is |
|---|---|---|---|
| MM-026 | `archive-cascade-review-2026-08-25.md` | **Active** | Consumes MM-025. **X-11.16, X-11.18 and X-11.15 closed 2026-08-27; X-11.41 next, X-11.17 narrowed but open, X-11.19 open.** The second review in this workstream is MM-034, still `draft`. |

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

> **Four blocks split out on 2026-09-01, and none of them has a plan yet** — they went back to the review
> side because each was a decision, not work to sequence. § C.6 BulkImportJob → `reviews/bulk-import/`
> (**MM-036** folder, **MM-037** media); § H DocumentSigning plus X-11.12/X-11.13 → `reviews/document-signing/`
> (**MM-038**, parked); the outbox trio X-3.1/X-9.3/X-11.44 → **MM-035**, which already scoped X-11.44.
> § N.2 Platform SDK (five gaps + the prompt) → `reviews/platform-sdk/` (**MM-039**) — it had no id and
> no status, so it was invisible to the board and unplannable.
> **Nothing was closed by the splits.** MM-022's own § Where the open work sits carries the mapping.

| Id | Plan | Status | What it is |
|---|---|---|---|
| MM-022 | `spec-repo-drift-review.md` | **Active** | ▶ **Now review and plan in one — start at its § Execution plan.** Eight waves, one per session, with a wave log to resume from; the front-matter exception is extended to cover it, and there is no separate plan id. **Wave 0 is an hour and not code: send the `magiq-auth` claims hand-off** — it is the critical path for the file's only Critical and it has been sitting written-and-unsent. **Wave 1 is X-4.20** — CI is green against a projection manifest CDK does not read, so until it lands every verification run is evidence about the wrong file. **48 open findings** *(69 → 50 in the 2026-09-01 split to MM-035/036/037/038, then 50 → 48 when **P-2 and P-3** went to MM-018 / ADO **34366** and **34319** — they had been double-tracked for weeks, ticketed there by substance under names that never mention `P-2` or `P-3`, which is why the § 4 ownership boundary never caught it. Nothing was closed by either move.)* across spec, ADRs, CDK and platform. The working checklist — tick the ✓ column as items land. *(Count corrected 2026-08-31: the file said 58, written before the W19–W30 passes appended the X-11.x series.)* **Start at § Spec sweep** — added 2026-08-31, it verifies what is genuinely left to apply to `docs/` against the repo, and orders it. **The spec work is finished.** That day's sweep closed **twenty-six** rows and half-closed four: CI back to `fail 0`, the queue topology, the mapper naming, the `*Message` contract names, the doc residue, **X-4.16** in the CDK repo, and finally **§G Processing (P-5…P-9)**, the last block. **Nothing under `docs/` is now known to be wrong** except §H DocumentSigning (parked by decision) and BI-1's bulk-import tree (a decision about the feature). **Everything else remaining is code** — §I.4 alone holds 43 of the 69. Two of the twenty-six needed no work at all: fixed weeks ago, never ticked — so **re-verify Low rows before planning against them.** <br><br>**X-4.15 closed the same day and immediately paid for itself.** Its new CI check (Messaging Guard) found **X-4.18** — two more handlers registered and never invoked, the third instance of that silent failure — plus **X-4.19**, and it pinned X-1.8's fix to one line in this repo rather than the CDK. Looking for a precedent for it also turned up **X-4.20 (🔴)**: `projection-tables.manifest.json` exists in **both** repos, the two have **diverged on the X-4.10 rotation**, and the CI drift gate checks the copy CDK does not read — so it passes green while CDK would provision `-v1` tables for code expecting `-v2`. **X-4.10 is therefore not fully landed and X-4.11 must not proceed.** |
| MM-024 | `spec-ddd-coverage-review-2026-08-24.md` | **Done** 2026-08-25 | Remediation plan for the DDD coverage review of the same name. **All 31 units (W0–W30) and all six decisions (D1–D6) closed 2026-08-25**; status flipped 2026-09-01 when a completion check found the work finished and only the bookkeeping stale. `check-spec-sections.py` ends at `fail 0 · warn 16 · rename backlog 0`, and **all 16 warnings belong to BI-1** — every other owning unit is at zero. Landed: two CI guards, `docs/spec/README.md` (the question map), `open-questions.md` (the contradiction register), a canonical glossary, the architecture-tier merge into `bounded-contexts.md`, the `system-spec.md` split into five `shared/` files, the saga specs, the **complete 132-command authorization matrix**, the MediaItem state matrix, cross-aggregate invariants and cascade rules, and the consistency model. **The recurring finding is that the plan's own premises were usually wrong** — units repeatedly found the surviving spec text worse than the truncated text, and the checking is what produced the value: the X-11.x series (43 findings, several Critical/High) was raised by this plan and is owned by MM-022 per §4. **What remains is out of scope by that same §4** — the code findings in `spec-repo-drift-review.md`, the two parked workstreams (`asset-custody`, `projection-rebuild`), and **BI-1**, a decision about an unbuilt feature. Two register entries stay open as decisions for Chase, not gaps: **Q-4** ⚖️ (infected object — the destructive path is what ships) and **Q-11** 🔒 (MediaProfile authorization table promises a check the code does not perform). *(Earlier revisions of this row reported Phase-1-only progress and gave X-11.1 as 69 references — superseded: the count is **88**, recounted after the 12 tails were restored.)* |
| — | `Archive/spec-repo-drift-review-completed.md` | Done | The 154 closed findings plus the full session log for every pass. Split out 2026-08-24; the id sets do not overlap. |

Recent: X-9.6 (name-reservation atomicity docs), X-9.7 (`MoveMediaItem` used `SwapAsync` — every
folder-to-folder move 409'd) and X-9.8 (`GuidFactory` byte order — every id in the system unsortable)
all landed 2026-08-24. The X-9.7 and X-9.8 fixes are **written but not yet built or run**, and X-9.8 also
needs a platform package release. See `todos.md` in the project root.

> Historical context for X-9.6 lives in `Archive/s13-uniqueness-atomicity-remediation-plan.md` at the
> plans root — same subject (reservation atomicity, name-release paths), a year-earlier pass.

## `architecture-review-remediation/` — the 2026-07 architecture reviews

Largest workstream, tracked on the ADO **Media** board: 169 work items across 6 Epics.

| Id | Plan | Status | What it is |
|---|---|---|---|
| — | `COWORK-EXECUTION-INSTRUCTIONS.md` | `exception:` | **Start here.** How to operate a session — start, continue, end. Not a plan, so it carries no id. |
| **MM-018** | `IMPLEMENTATION-PLAN.md` | **Active** | **The plan for this workstream.** The live tracker and source of truth for state — status columns in §5, session log in §9. Consumes MM-007…MM-017. All 169 items still To Do. |
| — | `architecture-review-remediation-pr-plan.md` | `exception:` | The rationale — why each finding groups into which PR, in what order. The rationale companion to MM-018; execution state lives there, so this carries no id. |
| — | `architecture-review-ado-workitems.md` | `exception:` | ID index: Epic → Feature → Story → Task, with board URLs and dependency links. Not a plan. |
| MM-019 | `architecture-review-authz-and-outbox-deferred-plan.md` | **Parked** | Authorization (C0–C8) and the transactional outbox (B4/INV-2). Deferred in sequencing only — both remain pre-production gates. |
| — | `Archive/ado-creation-resume-manifest.md` | `exception:` | Resume notes from the interrupted ADO creation run; superseded by the ID index. |

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
| MM-004 | `remove-env-suffix-plan.md` | **Done** (2026-09-01) | Drop the `-{env}` suffix from every resource name. Code complete in both repos, verified at source level by MM-005. The last open item — the ADR, `docs/adrs/deployment-and-resource-naming.md`, change-inventory item 13 — was **written 2026-09-01**, closing DN-1; `docs/adrs/README.md` now links it instead of flagging the gap. DN-4 (stale `.js`/`.d.ts` build output in `cdk-magiq-media`) is cleared too. |
| — | `Archive/deploy-handoff-tom.md` | Superseded | The dispatch-only deploy model, replaced by `deploy-runbook.md` in the project root. |

The consequence the ADR most needs to carry: renaming a stateful resource makes CloudFormation
*replace* it, so dev/qa/staging lose data on cutover. Prod naming is unchanged either way. It carries
it, under § Consequences, along with the one-environment-per-account invariant the whole scheme rests
on — co-locating two tiers in one account would collide every name in the platform.

**Two loose ends, neither blocking `done`.** (a) The ADR and README edit are **written but
uncommitted**, on `feature/change-requests` in the app repo — item 16 wants them on
`deploy/chase/<ticket>-remove-env-suffix` with a cross-linked PR. (b) Verification items 17, 18 (the
`dotnet test` half) and 20 are still unrun: `cdk synth` needs AWS credentials, so `cdk diff` against
dev and **prod — which must show no resource-name diffs** — is outstanding, as is the post-deploy
`/healthz` probe. `npx jest` (6/6) and `tsc --noEmit` are green; the jest suite has no snapshots and
asserts no physical names, so item 5's snapshot regeneration was moot.

## `design/` — feature design and per-module remediation

| Id | Plan | Status | What it is |
|---|---|---|---|
| MM-021 | `mediaitem-edit-session-design.html` | **Active** | MediaItem edit-session design. Consumes MM-020. HTML, so its front-matter is wrapped in an HTML comment. Verified 2026-08-31: 5 of 7 commands built; `AddSessionEditor` / `RemoveSessionEditor` are not, so the collaborative half is unbuilt and only the solo path ships. |
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
