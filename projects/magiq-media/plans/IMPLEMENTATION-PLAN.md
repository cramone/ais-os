# magiq-media — Architecture-Review Remediation: Implementation Working Plan

_Cross-session operating plan + live tracker. Working directory: `Z:\claudia\magiq\projects\magiq-media\plans`._
_Board: ADO **Media** project. Owner/assignee: Chase Ramone (chase.ramone@magiqsoftware.com)._
_Created 2026-07-20. Companion docs in this folder: `architecture-review-remediation-pr-plan.md` (rationale), `architecture-review-ado-workitems.md` (ID index), `architecture-review-authz-and-outbox-deferred-plan.md` (deferred)._

---

## 0. How this file is used across sessions

This is the **source of truth for execution**. Any session (me/Claude) picks up here:

1. Working directory = this `plans` folder. Read this file first (especially the **Status** column and the **Session log**).
2. `Story/Bug = one PR` (confirmed). Epics and Features are *not* PRs — they group work.
3. **You create the branches** (names are in this file), cut from `develop` in the named repo. I then do the code + spec work directly on that branch and finalize with a PR.
4. I **assign and update** the ADO work items as I go (protocol in §4). I update the **Status** column here in the same session.

Repos (all on GitHub; work items on ADO):
- **app** → `D:\source\github\magiq-media` (application code + `docs\spec\` + `docs\adrs\` — source of truth for spec/ADRs). Read its `CLAUDE.md` before any code/spec work.
- **cdk** → `D:\source\github\cdk-magiq-media` (CDK/TypeScript deploy infra).
- **platform** → `D:\source\github\aspnetcore-platform` (Magiq.Platform / Magiq.AspNetCore SDK).

---

## 1. Roles & handshake per PR

1. I pick the next ready Story (deps met — see §5 order) and tell you the **exact branch name + repo**.
2. **You create the branch** from `develop` in that repo (or say "go" and I'll note it's ready).
3. I assign the Story to you in ADO and move it to **In Progress**; I do the code **and** the spec/ADR changes on that branch, committing as I go (spec co-locates with code — repo convention).
4. I verify (build + tests green per the Acceptance cell), then open a PR into `develop` titled `AB#<id> <KEY> — <title>`, body citing the finding IDs it closes, and link the PR to the work item.
5. I move the Story to **Code Review** and comment the PR URL; QA/release/merge is your team's flow. I update the **Status** here.

---

## 2. Branch naming

`feature/chase/<workItemId>-<slug>` — cut from `develop`, in the repo noted per item. The `<workItemId>` is load-bearing: it's what links the GitHub PR back to the Media board via `AB#<id>` (Azure Boards GitHub app must be installed — confirm once).

Cross-repo Stories (A2, A4a, A4d) = **two branches / two PRs**, one per repo, keyed on the Task IDs; both PRs cite the same Story's `AB#`.

---

## 3. Execution order (waves)

Only two hard gates: **A1 (34301)** unblocks everything async; **A5 (34397)** is the deploy-re-enable gate. Otherwise reorder to capacity.

- **Wave 1 (unblock):** INV spikes → **A1** → the ★ trivials (D-PJ1 34319, D-RT1 34304, D-RG1 34340, D-COL2 34324, D-AM1 34300) — independent of A1.
- **Wave 2 (backbone live):** A2 → A3 → A4a–A4e → **A5 gate** · B1, B2 · G1.
- **Wave 3 (safety):** B1b · B3 (after INV-1).
- **Wave 4 (module depth):** the D-* clusters; run the archive-coordination group together (**D-COL1 + D-FOL2 + D-MI1**); do **D-MP3** early (feeds B3).
- **Wave 5 (hygiene + features):** E1–E5 · F1–F5.

---

## 4. ADO update protocol

**Assignee:** Chase Ramone (`chase.ramone@magiqsoftware.com`) — set on the Story/Bug and its Task(s) when work starts.

**Story/Bug & Task states** (real workflow on this board):
`New` → `In Progress` (I start) → `Code Review` (PR open) → `Ready for QA` → `QA Testing` → `Ready for Release` → `Done`.
- I drive **New → In Progress → Code Review** and stop there (leave QA/release/Done to your flow, unless you tell me to close).
- **Feature** completed state = `Closed`; **Epic** completed state = `Done`. When all Stories under a Feature are Done, set the Feature `Closed`; when all Features under an Epic are Closed/Done, set the Epic `Done`. (If unsure of a type's allowed states, read them from the work-item type before setting.)

**On each transition:** set state via `wit_update_work_item` (`op:"Replace"`, path `/fields/System.State`); set `System.AssignedTo` (`op:"Replace"`) — note the board uses `Replace` with a value to set and `Replace` with `""` to clear (Remove op is rejected). Add a comment with the PR URL at Code Review. Link PR↔work item via `AB#<id>` in the PR + `wit_link_work_item_to_pull_request` where available.

---

## 5. Master tables

Legend: **Status** ∈ To Do / In Progress / Code Review / Done. ★ = trivial-but-critical (pull forward). Branch repo in brackets. "Work" = key touch points; "Accept" = done-when.

### Epic A — Async integration backbone (34275)

| Key | WI | Branch (repo) | Deps | Status | Work (touch points) | Accept |
|---|---|---|---|---|---|---|
| A1 ★ROOT | 34301 | `feature/chase/34301-production-messaging-registration` (app, +platform if SDK) | — | To Do | `AddMediaProductionMessaging()` ext registering platform `IMessageBus` + all module SNS publishers; call from ProcessingWorker/EventConsumers/SagaOrchestrator/TimeoutScanner; add 3 missing Processing publishers; move started/completed/failed to correct host | Per-host publish smoke test: no `InvalidOperationException` |
| A2 | 34358 | see §6 (cdk + app) | A1 | To Do | integration env on SNS-backed bus; parameterise `ORGANIZATION_ID` (`bin/magiq-media.ts`) | no placeholder org id in any real deploy; hosts publish over SNS |
| A3 | 34366 | `feature/chase/34366-eventconsumers-rewire-idempotent-create` (app) | A1 | To Do | stop saga/worker consumers in `EventConsumers`; keep saga in `SagaOrchestrator`; `GetByAssetIdAsync`; idempotent create keyed on `AssetId`; check create Result before scan | 1 upload-confirmed → exactly 1 job; redelivery → no-op |
| A4a | 34372 | see §6 (cdk + app) | A1 | To Do | add `media.recordtype.published/deprecated` to cross-module filter; register `RecordTypeVersionDetailIndexProjector` | recordtype events reach the projector |
| A4b | 34380 | `feature/chase/34380-asset-archived-infection-filter` (cdk) | A1 | To Do | add `media.asset.archived` + `media.asset.infection-detected` to cross-module filter | both events routed; no DLQ |
| A4c | 34384 | `feature/chase/34384-bind-asset-assigned-handler` (app) | A1 | To Do | `AddMessageHandler<AssetAssignedToRole,…>()` binding | handler consumes; no DLQ |
| A4e | 34388 | `feature/chase/34388-drop-validation-passed-filter` (cdk) | A1 | To Do | remove `media.asset.validation-passed` from cross-module filter | event only on media-sagas |
| A4d | 34392 | see §6 (app + cdk) | INV-4 | To Do | interim gate: feature-flag review publish OFF or logged no-op + alarm | review publishes not silently dropped |
| A4f (opt) | 34395 | `feature/chase/34395-filter-gen-from-attributes` (cdk) | INV-3 | To Do | generate filter allowlist from `[MessageType]` at synth | generated == hand-maintained; drift-proof |
| A5 GATE | 34397 | `feature/chase/34397-e2e-ingestion-verification` (app) | A1,A2,A3,A4a-e | To Do | integration tests in A2 env: upload→…→complete + 2 timeout paths | green; no DLQ growth; **gates deploy re-enable** |

### Epic B — Distributed-systems safety (34276)

| Key | WI | Branch (repo) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| B1 | 34306 | `feature/chase/34306-consumer-contract-result-tenant` (app, Media.Shared) | A1 | To Do | shared consumer base: inspect dispatch `Result` (ACK vs throw→DLQ+metric); build `SqsExecutionContext` from SNS attr; tenant/actor from attr; reload-before-retry; apply to AssetManagement + Processing | swallowed results gone; tenant from attribute |
| B1b | 34308 | `feature/chase/34308-consumer-contract-rollout` (app) | B1 | To Do | apply B1 base to MediaItem/MediaProfile/ChangeRequests/Collection/Registration consumers | archive fan-out failures propagate |
| B2 | 34302 | `feature/chase/34302-saga-occ-timeout-scanner` (app, Media.Shared.Infrastructure/Sagas) | A1 | To Do | `DynamoDbSagaRepository.SaveAsync` conditional write on `Version` (retry on ConditionalCheckFailed); re-read remaining time in TimeoutScanner loop | concurrent saves safe; safety-buffer abort works |
| B3 | 34305 | `feature/chase/34305-reference-projector-watermarks` (app) | INV-1, INV-5 | To Do | monotonic watermark per ref model; reorder-safe tombstones; skip-if-stale; confirm-time re-check. Covers Capability/AssetState/VersionAsset/AssetProfileDefault + Registration MediaItemReference projectors | duplicate/reordered delivery safe |

### Epic G — Observability (34280)

| Key | WI | Branch (repo) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| G1 | 34309 | `feature/chase/34309-observability-correlation-metrics` (app, +cdk alarms) | B1 | To Do | CorrelationId logging scope per host; per-flow/per-saga success+latency metrics; alarms: saga-approaching-timeout, review-thread-not-created, counter-drift | correlation traceable end-to-end; alarms live |

### Epic E — Contract, validation & spec hygiene (34278)

| Key | WI | Branch (repo) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| E1 | 34299 | `feature/chase/34299-validators-fluentvalidation` (app) | — | To Do | FluentValidation on every module's commands/requests | malformed input → 400/422 not 500 |
| E2 | 34343 | `feature/chase/34343-error-contract-rfc9457` (app) | — | To Do | RFC 9457 `errorCode`; catalog-coded DomainErrors; 409-vs-422; missing per-module codes | coded errors; correct statuses |
| E3 | 34350 | `feature/chase/34350-spec-wiki-reconciliation` (app `docs\spec`) | — | To Do | `*IntegrationEvent` vs `*Message` naming; stale write-model tables; `bounded-context.md` + `DEPLOYMENT.md` drift | docs match code; wiki-publish-ready |
| E4 | 34356 | `feature/chase/34356-dead-code-dto-cleanup` (app) | — | To Do | remove dead code/DTOs; CR-F4 implicit→explicit mappers | no dead code; explicit mappers |
| E5 | 34364 | `feature/chase/34364-contract-design-nits` (app, +cdk) | — | To Do | split Status enum; MediaItemId on processing events; StorageKey leak; version-branch test; routing-string discipline; distinct reprocessing `[MessageType]`; doc fast-exit vs completion | each nit closed + test |

### Epic F — Deferred choreography features (34279) — product-gated by INV-4

| Key | WI | Branch (repo) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| F1 | 34370 | `feature/chase/34370-mediaitem-review-saga` (app) | INV-4 | To Do | review saga + review event set + submitted-for-review consumer + reviewer cmds + 14-day timeout + terminal states | review flow runs end-to-end |
| F2 | 34376 | `feature/chase/34376-documentsigning-saga` (app) | INV-4 | To Do | signing saga+aggregate+events+72h timeout+`ISecuredSigningApiClient`, OR formally remove half-wired host | built or cleanly removed |
| F3 | 34381 | `feature/chase/34381-reprocessing-timeout-compensation` (app) | INV-4 | To Do | reprocessing timeout/compensation (saga terminal-per-asset problem) | stalled reprocess recovers |
| F4 | 34385 | `feature/chase/34385-checkout-lifecycle` (app) | INV-4 | To Do | implement or formally defer checkout; review timeout so PendingApproval can't hang | decided + no hang |
| F5 | 34389 | `feature/chase/34389-registration-submission-timeout` (app) | INV-4 | To Do | submission timeout/compensation + ExpiresAt/retention driving | timeouts fire; retention enforced |

### Epic D — Module correctness bugs (34277)

**AssetManagement (Feature 34290)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-AM1 ★ | 34300 | `feature/chase/34300-s3-delete-guard-virus-quarantine` | — | To Do | `asset.Delete()` before S3 delete; quarantine-not-hard-delete on virus; settle soft/hard delete | guard-before-delete; no data loss |
| D-AM2 | 34307 | `feature/chase/34307-am-read-model-completeness` | — | To Do | infection projection; version-artifact/reprocess gaps; hide soft-deleted in GET/list; populate FileSizeBytes | read models complete |
| D-AM3 | 34310 | `feature/chase/34310-role-assignment-delete-lock` | — | To Do | item-scoped uploads get a role; restore delete-lock invariant (pairs D-MI2) | locked assets protected |
| D-AM4 | 34311 | `feature/chase/34311-multipart-idempotency-compensation` | — | To Do | idempotent complete/abort; orphaned-multipart compensation; part-URL TTL | redelivery safe; no orphans |
| D-AM5 | 34314 | `feature/chase/34314-upload-ceiling-quota-accounting` | — | To Do | upload size ceiling; per-owner quota (no DI-singleton mutation); assign-time charge | quota correct + thread-safe |
| D-AM6 | 34318 | `feature/chase/34318-am-mapping-rendition-enum-determinism` | — | To Do | metadata mapping; rendition retrievability; poison-enum TryParse; deterministic recordedAt | all four closed |

**Processing (Feature 34291)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-PJ1 ★ | 34319 | `feature/chase/34319-pj-projector-correctness` | — | To Do | failed→Failed (not Succeeded); terminal not indexed Running; project Bypassed; event×status test matrix | projector matrix green |
| D-PJ2 | 34321 | `feature/chase/34321-pj-completion-driver` | A1 | To Do | wire `AssetProcessingWorker.ProcessAsync`; single owner of Start/Bypass | capable jobs progress |
| D-PJ4 | 34320 | `feature/chase/34320-pj-scan-failure-idempotent-complete` | — | To Do | scan-failure terminal transition; idempotent Complete/Fail; Outcome as enum/VO | redelivery no-op; terminal correct |
| D-PJ5 | 34322 | `feature/chase/34322-pj-real-scan-rendition-pipeline` | INV-4 | To Do | real scan + rendition behind feature gate; remove hardcoded "Passed"/NotImplemented | pipeline runs (gated) |

**Collection (Feature 34292)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-COL1 | 34323 | `feature/chase/34323-col-archive-readmodel-reversible` | B1 | To Do | archive → read-model-only reversible fan-out; bounded/checkpointed; propagate failures; `UnarchiveCollection` (coordinate D-FOL2+D-MI1+s13) | archive reversible + bounded |
| D-COL2 ★ | 34324 | `feature/chase/34324-col-summary-projector-timestamps` | — | To Do | stop summary projector overwriting CreatedAt/UpdatedAt on DefaultProfileSet | timestamps preserved |
| D-COL3 | 34325 | `feature/chase/34325-col-archived-state-guards` | — | To Do | archived guards on 4 mutators; suppress mutation events when archived | archived collections immutable |
| D-COL4 | 34326 | `feature/chase/34326-col-atomic-update-command` | — | To Do | single atomic `UpdateCollection` command for PATCH | PATCH atomic |
| D-COL5 | 34327 | `feature/chase/34327-col-default-profile-guards-gsi` | — | To Do | default-profile published+owner guards; createdAt sort GSI | guards + sort work |

**Folder (Feature 34293)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-FOL1 | 34399 | `feature/chase/34399-fol-move-safety` | — | To Do | cycle guard; cross-collection immutability; subtree-height + depth-counter recompute | moves safe |
| D-FOL2 | 34401 | `feature/chase/34401-fol-archive-cascade-rebuild` | s13 saga | To Do | archive cascade on s13 saga; guard root; single bounded resumable leaf-first pass | no re-dispatch storm; resumable |
| D-FOL3 | 34403 | `feature/chase/34403-fol-mediaitems-index-counter` | — | To Do | index handles AssignedToFolder/Deleted; registration counter authoritative + strong-consistency gate (pairs D-MI1) | index + counter correct |
| D-FOL4 | 34406 | `feature/chase/34406-fol-archived-guards-parent-existence` | — | To Do | archived guards; bulk parent-existence; registration-gate vs ADR-006 | guards + ADR-006 reconciled |
| D-FOL5 | 34410 | `feature/chase/34410-fol-creation-lock-expectedversion` | — | To Do | creation-lock rework/TTL/documented 503; thread `ExpectedVersion` | lock robust; OCC threaded |

**MediaItem (Feature 34294)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-MI1 | 34416 | `feature/chase/34416-mi-active-items-counter-archived-guard` | — | To Do | maintain ADR-006 active-items counter; archived-folder admission guard (enables D-FOL3/4 gate) | counter maintained |
| D-MI2 | 34421 | `feature/chase/34421-mi-emit-unassign-replace-events` | — | To Do | emit `AssetUnassignedFromRole`/`AssetReplacedInRole` (pairs D-AM3) | binding two-sided |
| D-MI3 | 34426 | `feature/chase/34426-mi-metadata-merge-conformance` | — | To Do | full-replace truly replaces; conformance partial-resolution + gap-set compare (pairs D-MP2) | replace + gap-set correct |
| D-MI4 | 34431 | `feature/chase/34431-mi-summary-version-projector-fixes` | — | To Do | CollectionId on assign/move; tag-replace; draft version #; v0-sentinel filter; purged-version handler | projectors correct |
| D-MI5 | 34433 | `feature/chase/34433-mi-registration-consumer-withdraw` | B1 | To Do | consumer result-handling; withdraw guard; suppress spurious submitted-for-review | consumer robust |
| D-MI6 | 34435 | `feature/chase/34435-mi-empty-reviewer-guard-conformance-fanout` | — | To Do | empty-reviewer auto-submit guard; bounded/checkpointed conformance fanout | guard + bounded fanout |

**MediaProfile (Feature 34295)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-MP1 | 34437 | `feature/chase/34437-mp-compiled-template-roundtrip` | — | To Do | converter+snapshot round-trip for BareName/SuppressedFieldNames; project/surface compiled fields | round-trip lossless |
| D-MP2 | 34439 | `feature/chase/34439-mp-conformance-model` | — | To Do | remove publish-block (ADR-010 flag-never-block); bounded/checkpointed fan-out | ADR-010 honoured |
| D-MP3 | 34441 | `feature/chase/34441-mp-published-snapshot-completeness` | — | To Do | include AssetDefinitions/CompiledTemplate/per-role MaxFileSizeBytes in published snapshot (feeds B3 — do early) | snapshot complete |
| D-MP4 | 34443 | `feature/chase/34443-mp-summary-dimension-seeding` | — | To Do | summary count drift; dimension-constraints projection; resumable/idempotent seeding | counts + seeding correct |

**RecordType (Feature 34296)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-RT1 ★ | 34304 | `feature/chase/34304-rt-data-corruption-trio` | — | To Do | DraftDiscarded ≠ IsDeprecated; FieldDeprecated only target field; last-field-removal safe; tests | trio fixed + tested |
| D-RT2 | 34329 | `feature/chase/34329-rt-schema-version-name-release` | — | To Do | real schema version on deprecate; release name; coded errors incl RecordTypeNotPublished 409 | correct version + errors |
| D-RT3 | 34330 | `feature/chase/34330-rt-readmodel-table-aliases` | — | To Do | fix GetById/projector table mis-wire; alias projector+read-model; verify names vs cdk | GetById works; aliases readable |
| D-RT4 | 34332 | `feature/chase/34332-rt-owner-scoping-summary-fields` | — | To Do | OwnerId on summary + owner index; fix HasDraft/PublishedVersion (authz enforcement = deferred C6) | summary fields correct |
| D-RT5 | 34335 | `feature/chase/34335-rt-capability-order-validators` | — | To Do | capability Order de-conflict; force client-field defaults; field validators | order + validators |

**Registration (Feature 34297)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-RG1 ★ | 34340 | `feature/chase/34340-rg-inverted-eligibility-guard` | — | To Do | flip guard to `!HasProcessingCapability` | valid docs accepted; processed media rejected |
| D-RG2 | 34345 | `feature/chase/34345-rg-search-indexer` | — | To Do | build search indexing projector; align index/fields; owner-scope | `/registrations/search` returns |
| D-RG3 | 34352 | `feature/chase/34352-rg-status-reconciliation-notes-projector` | B3 | To Do | reconcile status name across 4 sources; owner-notes capture; reorder-safe ref projector | status consistent |

**ChangeRequests (Feature 34298)**

| Key | WI | Branch (app) | Deps | Status | Work | Accept |
|---|---|---|---|---|---|---|
| D-CR0 | 34357 | `feature/chase/34357-cr-spec-reconciliation` (app `docs\spec`) | — | To Do | reconcile context-overview/read-model/error-catalog to current model (do first) | specs consistent |
| D-CR1 | 34363 | `feature/chase/34363-cr-snapshot-participants-comment-bodies` | — | To Do | snapshot retains `_participantIds`+`ReviewSessionId`; comment bodies → read model | post-snapshot AddComment works |
| D-CR2 | 34369 | `feature/chase/34369-cr-comment-validation-coded-errors` | — | To Do | body validation + 4000 cap + control-char strip; coded 403/404; scrub deleted | validation + coded errors |
| D-CR3 | 34374 | `feature/chase/34374-cr-participant-roster-projection` | — | To Do | participant roster projection (read-authz enforcement = deferred C8) | roster projected |

---

## 6. Cross-repo Stories (two branches / two PRs each)

| Story | Task WI | Branch | Repo |
|---|---|---|---|
| A2 (34358) | 34359 | `feature/chase/34359-sns-test-env-orgid-fix` | cdk-magiq-media |
| A2 (34358) | 34362 | `feature/chase/34362-integration-env-messaging-config` | magiq-media |
| A4a (34372) | 34375 | `feature/chase/34375-recordtype-events-filter` | cdk-magiq-media |
| A4a (34372) | 34378 | `feature/chase/34378-register-recordtype-projector` | magiq-media |
| A4d (34392) | 34393 | `feature/chase/34393-review-path-interim-gate` | magiq-media |
| A4d (34392) | 34394 | `feature/chase/34394-review-path-alarm-noop` | cdk-magiq-media |

---

## 7. Spikes (no branch — investigation; I record findings in the work item + this file)

| Key | WI | Nature | Feeds |
|---|---|---|---|
| INV-1 | 34336 | read the 4 reference projectors; produce watermark design | B3 (34305) |
| INV-3 | 34341 | feasibility: generate filter from `[MessageType]` | A4f (34395) |
| INV-4 | 34346 | **product decision**: build vs defer review saga + signing | A4d, F1–F5 |
| INV-5 | 34351 | confirm platform store conditional-write semantics (platform repo — may produce a test branch `feature/chase/34351-store-conditional-write-test`) | B3 |

---

## 8. Branch list to create (grouped by repo)

Create from `develop`. Spikes need no branch (except optional INV-5 test).

**magiq-media (app) — 46 branches:**
```
feature/chase/34301-production-messaging-registration
feature/chase/34362-integration-env-messaging-config
feature/chase/34366-eventconsumers-rewire-idempotent-create
feature/chase/34378-register-recordtype-projector
feature/chase/34384-bind-asset-assigned-handler
feature/chase/34393-review-path-interim-gate
feature/chase/34397-e2e-ingestion-verification
feature/chase/34306-consumer-contract-result-tenant
feature/chase/34308-consumer-contract-rollout
feature/chase/34302-saga-occ-timeout-scanner
feature/chase/34305-reference-projector-watermarks
feature/chase/34309-observability-correlation-metrics
feature/chase/34299-validators-fluentvalidation
feature/chase/34343-error-contract-rfc9457
feature/chase/34350-spec-wiki-reconciliation
feature/chase/34356-dead-code-dto-cleanup
feature/chase/34364-contract-design-nits
feature/chase/34370-mediaitem-review-saga
feature/chase/34376-documentsigning-saga
feature/chase/34381-reprocessing-timeout-compensation
feature/chase/34385-checkout-lifecycle
feature/chase/34389-registration-submission-timeout
feature/chase/34300-s3-delete-guard-virus-quarantine
feature/chase/34307-am-read-model-completeness
feature/chase/34310-role-assignment-delete-lock
feature/chase/34311-multipart-idempotency-compensation
feature/chase/34314-upload-ceiling-quota-accounting
feature/chase/34318-am-mapping-rendition-enum-determinism
feature/chase/34319-pj-projector-correctness
feature/chase/34321-pj-completion-driver
feature/chase/34320-pj-scan-failure-idempotent-complete
feature/chase/34322-pj-real-scan-rendition-pipeline
feature/chase/34323-col-archive-readmodel-reversible
feature/chase/34324-col-summary-projector-timestamps
feature/chase/34325-col-archived-state-guards
feature/chase/34326-col-atomic-update-command
feature/chase/34327-col-default-profile-guards-gsi
feature/chase/34399-fol-move-safety
feature/chase/34401-fol-archive-cascade-rebuild
feature/chase/34403-fol-mediaitems-index-counter
feature/chase/34406-fol-archived-guards-parent-existence
feature/chase/34410-fol-creation-lock-expectedversion
feature/chase/34416-mi-active-items-counter-archived-guard
feature/chase/34421-mi-emit-unassign-replace-events
feature/chase/34426-mi-metadata-merge-conformance
feature/chase/34431-mi-summary-version-projector-fixes
feature/chase/34433-mi-registration-consumer-withdraw
feature/chase/34435-mi-empty-reviewer-guard-conformance-fanout
feature/chase/34437-mp-compiled-template-roundtrip
feature/chase/34439-mp-conformance-model
feature/chase/34441-mp-published-snapshot-completeness
feature/chase/34443-mp-summary-dimension-seeding
feature/chase/34304-rt-data-corruption-trio
feature/chase/34329-rt-schema-version-name-release
feature/chase/34330-rt-readmodel-table-aliases
feature/chase/34332-rt-owner-scoping-summary-fields
feature/chase/34335-rt-capability-order-validators
feature/chase/34340-rg-inverted-eligibility-guard
feature/chase/34345-rg-search-indexer
feature/chase/34352-rg-status-reconciliation-notes-projector
feature/chase/34357-cr-spec-reconciliation
feature/chase/34363-cr-snapshot-participants-comment-bodies
feature/chase/34369-cr-comment-validation-coded-errors
feature/chase/34374-cr-participant-roster-projection
```

**cdk-magiq-media (cdk) — 5 branches:**
```
feature/chase/34359-sns-test-env-orgid-fix
feature/chase/34375-recordtype-events-filter
feature/chase/34380-asset-archived-infection-filter
feature/chase/34388-drop-validation-passed-filter
feature/chase/34394-review-path-alarm-noop
feature/chase/34395-filter-gen-from-attributes
```

**aspnetcore-platform (platform) — as needed:**
```
(A1 may need a companion branch here if AddMediaProductionMessaging lands in the SDK)
feature/chase/34351-store-conditional-write-test   (optional, INV-5)
```

> Tip: you don't need to create all at once — create per wave (§3) as we get to them. For Wave 1 you need: `34301-...` (app) and the ★ trivials `34319`, `34304`, `34340`, `34324`, `34300` (app).

---

## 9. Session log

_Append one line per session: date · what advanced · state changes._

- 2026-07-20 — Plan created. All 169 work items + links exist on Media board (see `architecture-review-ado-workitems.md`). Nothing started; all Stories New/To Do.
