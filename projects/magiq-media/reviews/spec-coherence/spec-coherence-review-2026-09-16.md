---
id: MM-044
type: review
project: magiq-media
workstream: spec-coherence
raised-by: []
status: done
outcome: plan
todo-id: -
created: 2026-09-16
exception: Finding ids use per-aggregate prefixes (AS/PJ/CO/FO/MI/MP/CR/RT/RS/RG/DS/R/E/SI) rather than one workstream prefix — the register spans eleven aggregates and was already circulated under these ids on 2026-09-15; renumbering would break citations for no gain.
---

# Spec Coherence — Aggregates and Relationships

_Source under review: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\` (spec + ADRs)_

---

## Executive summary — the seven that matter

1. **`media.item.published` does not exist, and four downstream contracts are built on it.** Four files
   state plainly that a MediaItem going live raises `media.item.approved`; `bounded-contexts.md` subscribes
   Search/Discovery, Billing and Notifications to `media.item.published` in four separate places. One of
   these is the published language — the thing the spec says we are obliged not to break.
2. **`ReviewPolicy` gates nothing, and `AutoSubmitOnComplete` publishes unreviewed records.** The one seeded
   profile intended for governed records (`Governed Media Record`) carries `Review RequiredForPublish` *and*
   `AutoSubmit ✓`. Auto-submit has no reviewer source, so it fires `PublishMediaItemCommand` with an empty
   reviewer list, which publishes immediately. A metadata write can take a governed record `Draft → Published`
   with no human in the loop, in a compliance product.
3. **`CompiledMetadataTemplate.Capabilities` is "the union across contributing RecordType versions", and
   `RecordType` has no capability concept at all.** That compiled union — not the author-declared
   `MediaProfile.Capabilities` — is what `MediaItemCreated` embeds and what the `Processing` gate reads.
4. **Archive is two different operations with opposite guarantees.** Folder archive is synchronous, guarded
   and refuses on an incomplete cascade. Collection archive flips the parent first, has no registration
   guard, no rollback, no DLQ path and no way to re-trigger. The `active-registrations` counter — the gate
   protecting statutory filings — is bypassed entirely by archiving one level up.
5. **The saga that is the system's only watchdog is armed over the leg that loses messages.**
   `AssetIngestionSaga` is created by `ProcessingJobCreated` published across an explicitly non-atomic
   dual write; it has no transition for a *failed* virus scan; and its bypass path writes its terminal state
   before the dispatch that can fail.
6. **Retention is designed against fields that exist in no aggregate.** `RetentionScheduleRef` appears in
   `domain-model.md`, the ADR and the design-decisions file; it appears in no Properties table, no draft, no
   published snapshot and no read model on either `MediaProfile` or `MediaItem`.
7. **The spec routinely cites authorities that are not reachable, in two distinct ways.** Nine `shared/`
   files the index marks live do not exist — `cross-aggregate-invariants.md`, `cascade-rules.md`,
   `error-catalog.md` and `saga-patterns.md` among them — and normative rows across eleven-plus files
   delegate to them. Separately, **121 citations across 28 files point at documents outside the repository
   entirely**: 43 `MM-nnn` plan ids and 78 `DEC-`/`AD-`/`X-` decision and drift ids, none defined anywhere
   in `docs/`, all resolving only on one engineer's machine. The repo's own `CLAUDE.md` forbids the second
   outright — *"Decisions related to changes or reasons do not belong in the spec files"* — and
   `spec/README.md` row 14 names that off-repo project as the wrong place to send a reader. Several of the
   citations are load-bearing on a rule's status, so a reader cannot tell what the rule is, or that they
   cannot tell.

---

## Scope

**Read, in full:** every aggregate spec set (`write-model` · `api` · `read-model` · `scenarios`) for
`Asset`, `ProcessingJob`, `Collection`, `Folder`, `MediaItem`, `MediaProfile`, `ChangeRequest`,
`RecordType`, `Registration`, `DocumentSigningSession`; `retentionschedule.design-decisions.md`;
`mediaprofile.defaults.md`; all seven `context-overview.md` and `business-scenarios.md` files; the three
saga/process-manager files; `architecture/` (`domain-model`, `bounded-contexts`, `system-architecture`,
`branching-and-deployment`); all six `shared/` files that exist; `glossary.md`; `spec/README.md`; and all
eight ADRs.

**Not read, by instruction:** repository source code; any existing review, drift register or audit document
in the tree. Neither informed any finding.

**Excluded, by instruction:** authorization and permission rules. Where a finding sits next to an
authorization rule, only the non-authorization half is reported.

**Severity.** `Critical` — a rule the design states and the design itself breaks, or a defect that destroys
or obscures a record. `High` — a stated guarantee that does not hold, or a lifecycle hole with no recovery.
`Medium` — divergence that will cost a build or an integration. `Low` — naming, counts, dangling references.

**Finding ids.** Per-aggregate prefixes, stable: `AS` Asset · `PJ` ProcessingJob and AssetIngestionSaga ·
`CO` Collection · `FO` Folder · `MI` MediaItem · `MP` MediaProfile · `CR` ChangeRequest · `RT` RecordType ·
`RS` RetentionSchedule · `RG` Registration · `DS` DocumentSigning · `R` relationships · `E` systemic ·
`SI` spec integrity. See the `exception:` line in front-matter.

**Evidence.** Line numbers are approximate (`~`) and were taken on 2026-09-15 against the working tree at
the path above. They locate the statement; they are not a commitment to a revision.

---

## Findings

### Asset (AssetManagement)

| # | Sev | Finding |
|---|---|---|
| AS-1 | Critical | **`Pending` is a trapped state and the exit is specified as non-existent.** `asset.api.md` ~626: *"Nothing in the application enforces the deadline."* Nothing dispatches `FailAssetProcessing(UploadExpired)`; `Pending` is neither archivable (~359) nor deletable (~390). An abandoned upload holds an orphaned S3 key forever. The same is true of `Validating`, `Processing`, `ContainsVirus` and `MultipartAborted` — none has any exit. |
| AS-2 | Critical | **`ConfirmUpload()` is specified as both refusing and serving the multipart path.** `asset.write-model.md` ~231: *"Rejected if `UploadMode = Multipart` — use `CompleteMultipartUpload` instead."* ~378: *"Calls `asset.ConfirmUpload(now)`"* inside `CompleteMultipartUploadHandler`. There is no `CompleteMultipartUpload()` row in the Methods table at all, though the state machine and Commands table both depend on it. |
| AS-3 | High | **`StartProcessing` / `BypassProcessing` guard on `Validating`, which is also the pre-scan status.** A replayed or reordered `ProcessingJobStarted`/`Bypassed` moves an asset that was never scanned to `Processing` or straight to `Active`. Both facts needed to close this (`AssetValidationPassed`, capability) are on the aggregate's own stream and are not checked. |
| AS-4 | High | **`RecordValidationResult` has no idempotency guard on a standard (non-FIFO) queue.** `asset.write-model.md` ~257: *"**No transition** — stays `Validating`."* Every other command self-guards by changing status; this one re-satisfies its own precondition on redelivery and appends a second `AssetValidationPassed`, producing a second saga branch dispatch. |
| AS-5 | High | **Two components race to branch the pipeline.** ~91: *"determined by `AssetIngestionSaga` … with `AssetProcessingWorker` as defensive fallback"* — no correlation key, no dedup; the loser's command returns a domain error against a healthy asset. |
| AS-6 | High | **Reprocessing has no owner and no clock.** The `Active → Validating` edge exists only in the read model (`asset.read-model.md` ~90); there is no `RequestReprocessing` method and no command. `asset-storage-and-processing.md` ~57 says the reprocess run *"is **not** saga-timeout-tracked in this cut"* — and neither `Validating` nor `Processing` is archivable or deletable, so a stalled reprocess is unrecoverable. |
| AS-7 | Medium | **A GET query performs a billable, state-changing S3 restore.** `asset-storage-and-processing.md` ~82 initiates an async `RestoreObject`; `asset.scenarios.md` ~599: *"No event written — read-only query path."* A second caller cannot tell a restore is in flight except by repeating the side effect. |
| AS-8 | Critical | **The invariants table states a rule the same file says is wrong.** ~24: *"Status must be `Active` … `AssignAssetToRole`"*. ~341: *"An earlier revision of this spec required `Status = Active` to attach. That is wrong"*, replaced by an allow-list of five non-terminal statuses. The table was never updated. |
| AS-9 | Critical | **An item-scoped asset can never receive a role.** ~30: *"`MediaItemId` must be null | `AssetAlreadyAttached` | `AttachAssetToMediaItem`"*, but the factory takes `mediaItemId?`, so an asset uploaded *against an item* has it non-null from the creation event. `RoleName` is only carried on `AssetAttachedToMediaItem`. The guard permanently blocks role assignment for exactly the assets uploaded for a role. |
| AS-10 | Critical | **`MediaItemId` is "immutable once set" and there is a command that clears it.** ~42 vs ~301 `DetachAssetFromMediaItemCommand`, and `asset.read-model.md` ~87 *"UPDATE clear `MediaItemId`, `RoleName`"*. |
| AS-11 | Critical | **A cross-context lookup is filed as an aggregate invariant.** ~29: the asset must not be a published profile's `DefaultAssetId`, *"(cross-context guard via `AssetProfileDefaultReference`)"* — evaluable only by reading a Catalog-derived table. `asset.scenarios.md` ~517 places the same rule in the handler. Two sections, two classifications, one rule. |
| AS-12 | High | **`FailAssetProcessing`'s invariant contradicts its own stage matrix.** Invariant ~23: *"Status must be `Validating` or `Processing`"*; stage matrix ~243 admits `Pending | UploadExpired`. |
| AS-13 | Medium | **Write-once metadata vs reprocessing.** ~54: *"`Metadata` … Write-once; stamped by `CompleteAssetProcessing`."* Reprocessing terminates at `CompleteAssetProcessing` a second time. Either the field is not write-once or reprocessing cannot complete. |
| AS-14 | Critical | **Infected-object handling has three mutually exclusive answers, all asserted.** `asset.scenarios.md` ~380 *"**The S3 object is hard-deleted.**"*; ~412 *"no code performs the move … an infected original stays where it was uploaded"*; `context-overview.md` ~39 *"Infected originals are moved to `media-quarantine`"*. `asset.write-model.md` ~259 makes deletion a domain requirement. |
| AS-15 | Critical | **Archive retains renditions and deletes them.** `asset.api.md` ~357 *"S3 objects are retained"* vs `event-store-and-messaging.md` ~451 *"its renditions … must be cleaned up"*. The cleanup contract also depends on a `StorageKey` field that `AssetArchived`/`AssetDeleted` do not carry (~453 vs write-model ~265-266). |
| AS-16 | Critical | **Soft delete vs hard delete.** `asset.write-model.md` ~82 *"Deleted [soft; unassigned only]"* vs `asset.api.md` ~387 *"Hard-deletes an asset permanently."* `asset.scenarios.md` ~535 goes further — *"the asset event stream and all read model records are removed"* — which an event-sourced aggregate cannot do, and which contradicts `AssetDeleted` being appended. |
| AS-17 | Critical | **`AssetId` is caller-generated and server-generated.** `context-overview.md` ~49 *"generated by the caller (UUID v7) for idempotent upload initiation"* vs `asset.api.md` ~76 *"Asset ID is server-generated"*. Server generation removes the stated idempotency property outright. |
| AS-18 | Critical | **Confirmation is and is not idempotent.** `event-store-and-messaging.md` ~475 *"The command is idempotent."* vs `asset.api.md` ~775 *"confirmation is **not** idempotent (AM-7)"*, whose single endpoint 422s when not `Pending`. The same two files also disagree on whether S3 `ObjectCreated` or the client confirms — one of the two paths 422s on every upload. |
| AS-19 | Critical | **Pre-signed PUT terms stated three ways.** `Content-Type` is signed (`asset-storage-and-processing.md` ~29, `asset.write-model.md` ~333) and *"`Content-Type` is NOT signed"* (~398, with a signature that has no content-type parameter). `content-length-range` is present (`asset.api.md` ~96) and unavailable for PUT (~333). |
| AS-20 | Critical | **Standalone quota: charged and not charged.** `asset.write-model.md` ~328 *"**Quota is NOT charged at upload.**"* vs `asset.scenarios.md` ~195 *"`MediaItemId = null` — quota check still applies"*. And the deferral has nowhere to land: ~357 *"True quota accounting … is **not implemented**"*. |
| AS-21 | Medium | Download status guard has three different sets across four places (`asset.api.md` ~538 vs ~560, `asset.scenarios.md` ~591, ADR ~37). `VersionArtifact` — the approved, frozen version — is undownloadable in three of the four. |
| AS-22 | Medium | `captureDigest` is returned by the API (~482) and exists in no read model, no DTO and no projector row. |
| AS-23 | Medium | Tag rules disagree three ways (normalised lowercase ≤64 vs `2–50` with uppercase permitted). Bulk batch limit is 50 (~675) and 100 (~752). Multipart part-URL TTL is 15 min (~187) and 1 h (`asset.scenarios.md` ~335); threshold ≥100 MB (~145) and >50 MB (~269). |
| AS-24 | Medium | `AssetMultipartCompleted` appears in the scenarios (~327) as a raised and published event; it is in no Domain Events table and no projector. |
| AS-25 | Low | Publisher class named three ways (`AssetDomainEventPublisher` / `…Mapper` / `AssetIntegrationEventMapper`); the context overview's published table has 8 rows against the write model's 11. `IsPrimary` and `UploadMode` are surfaced on the API and read model with nothing that sets them. |

### ProcessingJob and AssetIngestionSaga (Processing)

| # | Sev | Finding |
|---|---|---|
| PJ-1 | Critical | **Saga creation trigger, three names.** Domain event `ProcessingJobCreated` (`assetingestionsaga.md` ~18); integration message `media.processingjob.created` (~65); and `system-architecture.md` ~390 creates it on `AssetValidationPassedSagaHandler` with *"saga armed, timeout clock running"*. The third is a live contradiction: the saga's own table needs `Status == AwaitingValidation` to already exist before that event. Anyone building from the architecture diagram loses the entire validation-budget phase. |
| PJ-2 | High | **Terminal state, two names, two destinations.** `Completed` (saga ~52) vs `Complete` (`system-architecture.md` ~399, ~420, ~346). `Status` is *"a plain string — not an enum"* (~44), so this is a silent guard miss, not a compile error. Worse: `system-architecture.md` ~420 reaches `Complete` on `media.asset.processing-failed`, where the saga file reaches `Failed`. |
| PJ-3 | Critical | **No saga transition for a failed or infected scan.** The allowlist is five event types (`system-architecture.md` ~612) and neither `validation-failed` nor `infection-detected` is on it. An infected asset sits in `AwaitingValidation` for 15 minutes and is then failed as `ValidationTimeout` — the wrong terminal cause for every infected upload, applied to an asset that is already terminal. |
| PJ-4 | Critical | **The watchdog is armed over the leg it exists to protect.** `system-architecture.md` ~344: *"Step ① and ② are not atomic. This is the accepted dual-write risk."* The saga's only creation trigger rides that leg. A lost publish leaves the job `Queued` with no saga, no clock and no scanner that will ever see it — exactly the *"asset which stops moving"* the saga was built to notice. |
| PJ-5 | Critical | **Reordering strands the asset.** Saga ~74 treats *"an event for an asset with no saga"* as a handled outcome — nothing throws, nothing redelivers. If `validation-passed` lands before the create, it is consumed and discarded and the saga then waits forever. `system-architecture.md` ~616's claim that sagas *"tolerate out-of-order delivery"* is false: the design tolerates duplicates, not reordering. |
| PJ-6 | Critical | **Bypass writes its terminal state before the dispatch that can fail.** Saga ~83. On a dispatch failure the message redelivers into a guard requiring `AwaitingValidation`, which now fails; ~155 confirms *"no compensation on the Bypassed path"* and ~85 that *"the scanner never acts on it"*. The job stays `Queued` with both watchdogs closed. |
| PJ-7 | High | **The 15-minute validation budget cannot cover the scan it budgets.** Budget is 15 min global (~104); the scan queue's visibility is *"1800s (30 min); video jobs extend to 4 h"* (`system-architecture.md` ~611). Any legitimate >15 min scan is failed while still running, and the late scan-result command then poisons on the `Queued`-only guard. |
| PJ-8 | High | **Scanner pass 3 can never count anything.** The query is `TimeoutAt < now` (~121); pass 3 *"Counts approaching timeouts for metrics"* (~125), which by construction have `TimeoutAt > now`. `WarningWindowFraction` and the `SagasApproachingTimeout` metric are dead. |
| PJ-9 | High | **A missing index row produces a permanently re-scanned saga.** Both compensating dispatches resolve `AssetId → JobId` and *"skip with a warning when no row is found"* (~127-128); the projector *"refuses a missing current row rather than creating one"* (`processingjob.read-model.md` ~108). The saga is rescanned every 5 minutes forever, with no escalation and no DLQ. |
| PJ-10 | High | **Reprocessing is unreachable as specified.** `processingjob.api.md` ~22 promises reprocessing creates a new job; the saga correlates on `AssetId` (~24) and `Bypassed`/`Completed` are absorbing (~56). A second job for the same asset gets no saga, no clock and no compensation. |
| PJ-11 | Critical | **One index row per asset vs many jobs per asset.** `processingjob.write-model.md` ~253: *"keyed (TenantId, AssetId) — one row per asset, not per job"*, against `processingjob.scenarios.md` ~88 (*"A duplicate delivery mints a second JobId"*) and the read model's `ListProcessingJobsForAssetIdQuery` — *"An asset's job history"*. Compensation resolves to the wrong job; the first is orphaned. |
| PJ-12 | Critical | **The write-side index can never leave `Running`.** `processingjob.write-model.md` ~278-279 writes `Status = Running` on both `Succeeded` and `Failed`, with no row for `Bypassed` or `TimeoutRecovered`. `system-architecture.md` ~152 nonetheless claims it *"guards duplicate job submission"*, and the write model concedes *"Written, never read"* (~268). |
| PJ-13 | High | **`Bypassed` is a status no projector can write.** `processingjob.api.md` ~78: *"⚠ none — the event is unprojected"*; the job reads `Queued` permanently (`processingjob.scenarios.md` ~164). The read model declares `Bypassed` a legal value and the enum documents it as terminal. |
| PJ-14 | High | **Timeout recovery destroys the cause it claims to preserve.** ~43 *"A failure that arrives twice keeps the first cause"*; ~163 recovery *"clears `FailureReason` and `FailureCategory`"*. After recovery nothing retains why it failed. |
| PJ-15 | Medium | `Complete` on `Succeeded` is unspecified — absent from both the refused list (~36) and the idempotent list (~32) — and MediaConvert completion is async over a standard queue, so a duplicate completion is expected and will poison to the DLQ. |
| PJ-16 | Medium | Rendition `Width`/`Height` exist on the domain VO (~77) and are dropped by both the contract DTO and the read DTO — silent loss at the only hop that matters. |
| PJ-17 | Medium | Key shapes for `media-processing-job`/`-jobs` differ between `processingjob.read-model.md` and `event-store-and-messaging.md`, which calls itself *"the authoritative table inventory"*. |
| PJ-18 | Critical | **`media.processingjob.bypassed` is absent from the integration-event catalogue** (`event-store-and-messaging.md` ~309-312), as are `…created` and `media.asset.processing-timeout-recovered` — all three on the saga allowlist. `system-architecture.md` ~357 makes the catalogue load-bearing for the SNS filter policy. |
| PJ-19 | Medium | `Bypassed` means two things — *"The profile lacks the `Processing` capability"* (~51) and a standalone upload with no profile at all (`context-overview.md` ~80) — with no field distinguishing them. |

### Collection (Catalog)

| # | Sev | Finding |
|---|---|---|
| CO-1 | Critical | **Archive has no registration guard.** `collection.api.md` ~254 lists the whole error set as `404` / `422 CollectionAlreadyArchived`. Folder archive blocks on `FolderHasActiveRegistrations`. The same subtree archived one level up is never checked — the `active-registrations` counter is bypassed by route selection. `archive-fan-out.md` ~220 states it plainly: *"a collection containing registration-locked content still archives successfully"*. |
| CO-2 | Critical | **Archive is asynchronous with no failure channel.** `collection.scenarios.md` ~120: *"There is no rollback and no user-visible record of a partial cascade."* The handler returns normally on an incomplete run, so no retry and no DLQ; `collection.read-model.md` ~174 records the consequence — an archived collection whose children are still active, *"permanently if the cascade dropped a child"*. There is no API route to re-trigger it (`archive-fan-out.md` ~297). |
| CO-3 | High | **Four commands have no archived guard, and the spec names the sharpest.** `collection.write-model.md` ~107: *"an archived collection can currently be made `Public`"*. `SetVisibility`, `ApplyTags`, `UpdateDescription` and `SetDefaultMediaProfile` are all unguarded. The write is also silently inert — the public index is sparse on `ArchivedAt is null`, so it returns `204` and never appears anywhere. |
| CO-4 | High | **`CollectionStatus` is a declared value object with no property behind it.** ~61 declares `Active | Archived`; the Properties table has no `Status` — state derives from `ArchivedAt.HasValue`. Every other Catalog aggregate has a real `Status`. |
| CO-5 | Medium | **Creation is not one event.** ~112: *"A description or default profile supplied at creation arrives on `CollectionCreated` *and* on its own follow-up event."* Two records of one fact, and `CollectionDescriptionUpdated` carries an `OldDescription?` for a value that never existed. |
| CO-6 | Medium | **`DefaultMediaProfileId` is unreachable.** It is *"Applied to media items created without an explicit profile"* (~31), but `mediaProfileId` is **required** on `POST /v1/items` (`mediaitem.api.md` ~97), and an item created with no folder has no collection to inherit from. Nothing in the MediaItem spec reads it. |
| CO-7 | Medium | **The published profile check is never re-run.** `MediaProfileNotPublished` is enforced at create and set only; a later `Deprecate` leaves a collection pointing at a deprecated default with no signal. |
| CO-8 | Medium | **No cap on the archive subtree.** Folder archive refuses over 500 descendant folders because the cascade runs in-request; collection archive has no equivalent and phase 1 materialises the entire subtree in memory (`archive-fan-out.md` ~77). |
| CO-9 | Medium | `CollectionName` is *"Released on archive"* while the archived collection still exists and is still named — a second collection takes the name and listings show two. Same pattern as Folder and MediaItem. |
| CO-10 | Low | `CollectionArchived` carries `OccurredAt`; `FolderArchived` and `MediaItemArchived` carry `ArchivedAt`. Bulk merges `404 MediaProfileNotFound` and `422 MediaProfileNotPublished` into one per-item code (`collection.api.md` ~163). |
| CO-11 | Low | Id generation policy differs across siblings in one context: Collection caller-supplied-or-server, Folder server-only, MediaItem server, Asset contradictory. |

### Folder (Catalog)

| # | Sev | Finding |
|---|---|---|
| FO-1 | Critical | **"Max 10 levels of nesting" is stated as an invariant and the spec documents how to exceed it.** `folder.write-model.md` ~119-123: *"Moving a 6-deep subtree under a folder at depth 7 succeeds and produces folders at depth 13."* |
| FO-2 | Critical | **Depth counters go stale on every move and are never decremented on archive.** ~276: adjusted *"for the moved folder only"*; `folder.scenarios.md` ~140: *"**Depth counters are never decremented.**"* The counter is the strongly-consistent mechanism the ADR chose specifically so the guard *"needs a count to be authoritative at the instant it is read"* — it is not authoritative for any folder that has been moved or archived. |
| FO-3 | Critical | **Cross-collection move leaves descendants in the wrong collection.** ~116: *"`FolderMoved` is raised for the moved folder only. Descendants are not re-parented or re-emitted, which is why they keep the old `CollectionId`."* The stated rule — *"a folder lives in whatever collection its parent lives in"* — is therefore false immediately after every cross-collection move. Items beneath keep their stale `MediaItem.CollectionId` too. |
| FO-4 | High | **Three of nine "Invariants" are not invariants.** *"The cascade must archive every descendant"*, *"Subtree must not exceed 500 descendant folders"*, and *"No media item in the subtree may have an active registration"* are all pre-conditions on a handler, over projections and counters. The spec index itself draws this distinction (`README.md` row 7 vs 8). |
| FO-5 | Critical | **`ExpectedVersion` is required on every Folder command and exists on none.** `concurrency-and-consistency.md` ~40: *"`Folder` aggregate exposes `Version` and all mutating commands accept `ExpectedVersion`"*. `folder.write-model.md` ~102: *"**No Folder command carries an `ExpectedVersion`.**"* |
| FO-6 | Critical | **The synchronous archive has no queue, no DLQ, no redelivery and no poison concept.** `archive-fan-out.md` ~268: *"If the process dies mid-cascade the work is simply gone"* — with children already archived beneath an un-archived root, and the caller's `504` at API Gateway's 29-second limit killing the fan-out mid-flight. |
| FO-7 | Critical | **Items assigned after creation are invisible to the cascade — including to the registration pre-flight.** `archive-fan-out.md` ~248 (D-1): *"`MediaItemAssignedToFolder` has no index projector"*, so such an item is *"not archived, not counted, and not recorded as a failure, and the run still reports complete"*. A retention-locked item assigned after creation passes the guard. |
| FO-8 | High | **`Close()` has no archived guard and no un-close.** ~84: *"`UpdateDescription` and `Close` do not [refuse when archived]."* `FolderClosed` is what the retention design uses to stamp every contained item's disposal clock — so a disposal clock can be started on an archived folder, irreversibly. |
| FO-9 | High | **`FolderClosed` produces no integration event.** ~330. The retention design (`retentionschedule.design-decisions.md` ~28) requires `FolderClosed` to write the closure date onto each contained item — a cross-aggregate effect with no transport. |
| FO-10 | Medium | **Folder metadata is caller-typed and has a commit step; MediaItem metadata is schema-bound and has none.** `SetFolderMetadataFieldCommand` takes a `FieldType` from the caller; the two share the `MetadataChangeset` VO and nothing else. Two metadata lifecycles behind one type. |
| FO-11 | Medium | A domain invariant mapped to a transport error: *"A folder sits in the same collection as its parent | `400` (validation)"* (~92), against the `Result<T, DomainError>` / 422 convention everywhere else. |
| FO-12 | Medium | `CreateFolderHandler` has no guard that the parent folder or the collection is un-archived. A folder can be created inside an archived collection. |
| FO-13 | High | **A `/v1/folders/**` route creates Collections.** `folder.api.md` ~240: *"That collection is retrieved by name if it exists and created with `Private` visibility if it does not."* It bypasses `defaultMediaProfileId` validation, caller-supplied ids, `onDuplicate` and `CollectionAlreadyExists`, none of which appear in that route's error table. |
| FO-14 | Critical | **Two different scope-key strings for one uniqueness scope.** `concurrency-and-consistency.md` ~212: *"Folder child at media-collection root | `media-collection:{collectionId}`"*. `folder.write-model.md` ~259: *"`ScopeKeys.RootFolder(collectionId)` | `collection:{CollectionId}`"*. The scope key *is* the uniqueness guarantee. |
| FO-15 | High | **`GET /children` promises a `MediaItemStatus` no projector writes.** `FolderChildSummaryProjector` handles only created/assigned/moved/title/archived — nothing projects approval, withdrawal or revision, so every non-archived item reads `Draft` forever. The same field carries two unrelated vocabularies (`Active`/`Archived` for folders, `MediaItemStatus` for items) as a bare `string`. |
| FO-16 | High | **The hierarchy endpoint is unpaginated by design.** `folder.api.md` ~433: *"it is unpaginated — the handler pages … in batches of 1000 and concatenates, then applies `nameContains` in memory"* — against the pagination convention, behind a Lambda payload limit, with the filter applied after the full load. |
| FO-17 | Medium | `archivedDate` is returned by the detail API and exists on neither the detail read model nor any projector write. The archived-children rule is stated both ways in one file (~130 vs ~143). `openedDate` is echoed non-null on `201` and returns null on the next `GET`. |
| FO-18 | Medium | *"This is the complete route surface"* (~43) omits `POST` and `GET /v1/folders/{folderId}/items`, which live in `mediaitem.api.md`. |
| FO-19 | Low | *"No Folder integration event currently has a subscriber"* (~332) against `bounded-contexts.md` ~148, which subscribes Search/Discovery to `media.folder.*`. |

### MediaItem (Catalog)

| # | Sev | Finding |
|---|---|---|
| MI-1 | Critical | **Auto-submit publishes records with no review.** `mediaitem.write-model.md` ~266: auto-submit fires from **three** handlers, *"**A metadata write can take an item `Draft → Published`.**"* Combined with MP-1 (`ReviewPolicy` is never read) and the seeded `Governed Media Record` profile carrying both `Review RequiredForPublish` and `AutoSubmit ✓`, a governed record publishes unreviewed the moment its last required role is filled. |
| MI-2 | Critical | **Folder assignment is guarded by nothing, including by archive.** ~260: *"**No status check, no archive check, no checkout check**"*. An archived item can be moved — and `ArchiveMediaItemHandler` already released the title reservation, so the move calls `MoveAsync` against a row that no longer exists. |
| MI-3 | Critical | **The checkout guard's expression does the opposite of its stated intent.** ~165: the guard reads `profile?.CheckoutPolicy ?? mediaItem.PinnedCheckoutPolicy`, described as *"preferring the live value with the pinned value as a floor"*. It is not a floor: a live profile of `None` overrides a pinned `RequiredForEdit` and disables the lock. `PinnedCheckoutPolicy` is also duplicated inside `MediaProfileSnapshot`, which the guard never reads. |
| MI-4 | High | **Withdraw from `Revising` unpublishes the record.** `mediaitem.api.md` ~417: *"from any other status it returns to `Draft`."* An item in `Revising` has a live published version for readers; withdrawing drops it to `Draft` and that version stops being `Published` — with no equivalent of `DiscardRevision`'s safe return. |
| MI-5 | High | **Withdraw from `Draft` silently releases someone else's lock.** ~426: *"Withdrawing an item already in `Draft` succeeds and **supersedes any open edit session**."* Under `CheckoutPolicy = RequiredForEdit`, whose purpose is serialising edits, any actor can void an exclusive lease through a status route whose error table does not mention checkout. |
| MI-6 | High | **Two routes dispatch multiple commands with no atomicity and no way to tell what landed.** `PATCH /v1/items/{itemId}` ~143: *"dispatches up to two commands in sequence and returns on the first failure. There is no rollback."* `PUT /folder` ~165 *"dispatches assign first and falls through to move"* — using a domain error as control flow. |
| MI-7 | High | **Purging a version orphans its summary row.** `MediaItemVersionSummaryProjector` handles *"`MediaItemApproved` only"* (`mediaitem.read-model.md` ~240); only the detail projector deletes on purge. `GET /versions` reads the summary rows, so a purged version stays listed forever. |
| MI-8 | Medium | **The `RequiredForEdit` gate's three checks fail in different directions and the closer records the wrong outcome.** ~522-561 documents the bypass in full: check out under `cr-01`, abandon it, keep editing, publish — and at approval the closer *"swallows the mismatch … so **the change that actually landed is recorded permanently as `Abandoned`**"*. The fix (Status/Scope/Kind on the reference row) depends on contract members ChangeRequests' `context-overview.md` ~98 marks *"⚠ added 2026-09-14, not yet built"*. |
| MI-9 | Medium | An unassigned item has neither folder nor collection, so it is outside every visibility, uniqueness and archive mechanism the Catalog provides. The glossary calls `Unassigned` *"a creation-time transient state only"*; nothing enforces transience. |
| MI-10 | Critical | **`MediaItemApproved.ReviewSessionId` is non-nullable and the immediate-publish path has no review session.** `mediaitem.api.md` ~741: `POST /publish` raises *"`MediaItemPublicationRequested`, or `MediaItemApproved` on the immediate path"*. The payload (`mediaitem.write-model.md` ~437) declares `ReviewSessionId` without `?`, unlike the `CommentThreadId?` beside it. |
| MI-11 | High | **The `EditSession` value object omits a field it demonstrably stores.** `EditSession` is `{ Id, OpenedBy, Editors, OriginStatus, OpenedAt, LeaseExpiresAt? }` (~107, and the glossary agrees), yet `CheckOut` takes `changeRequestId?`, `EditSessionOpened` carries `ChangeRequestId?`, `ReviewSession` carries `EditSessionChangeRequestId?`, and `domain-model.md` ~63 lists `MediaItem.EditSession.ChangeRequestId?` as a cross-aggregate reference. |
| MI-12 | High | **`ReviewerAssignment.Decision` includes `Withdrawn` and no command produces it.** ~106. Publication completes when *"every non-withdrawn reviewer has approved"* (~291) — a condition with no way to become true, and no reviewer add/remove command anywhere. |
| MI-13 | Medium | **`MediaItemWithdrawn` carries a `Reason` the command discards.** ~488: *"The reason is accepted and discarded — D-9"*, while the event payload (~439) carries `Reason`. |
| MI-14 | Medium | **`RetentionScheduleRef` is the "pin of record" on `MediaItem` and appears in no Properties table.** `domain-model.md` ~72 states it; `mediaitem.write-model.md` Properties, `MediaProfileSnapshot`, and every MediaItem read model have no such member. |
| MI-15 | Medium | `UnassignAssetFromRole(assetId, unassignedAt)` derives the role from the assets list — ambiguous the moment `AllowMultiple` puts one asset in two roles, which nothing prevents. The single-slot guard is *"in the handler, not here"* (~321), so the invariant is unenforceable on any non-HTTP dispatch path. |
| MI-16 | Critical | **There is no `MediaItemPublished` event and no `media.item.published` integration event.** See E-1 — the single most consequential inconsistency in the tree. |
| MI-17 | High | **The publish command name, method name, handler name, event name and integration-event name are five different words for one act.** Route `publish` → `PublishMediaItemCommand` → method `RequestPublication` → handlers `PublishMediaItemHandler` *and* `SubmitMediaItemForReviewHandler` (both listed, ~515-516) → event `MediaItemPublicationRequested` → integration event `MediaItemSubmittedForReviewIntegrationEvent`. The two handlers are never reconciled. |
| MI-18 | Medium | `POST /publish`'s error list omits every change-request refusal the handler is specified to make; the checkout error table lists `ChangeRequestNotOpen` but not `ChangeRequestNotForItem` or `ChangeRequestWrongKind`. |
| MI-19 | Medium | **The projector count is wrong.** `mediaitem.read-model.md` ~187: *"**Six projectors maintain MediaItem read models.**"* Six are listed, and `IsAccessible` is *"written only by `AssetAccessibilitySummaryProjector`"* (~62) — a seventh, writing `media-items`. |
| MI-20 | Medium | Summary carries `IsAccessible`, detail carries `HasAccessibleAssets`, API surfaces both as `isAccessible`; and the read model says the detail row is *"All summary fields except `IsAccessible`"*. |
| MI-21 | Medium | Bulk metadata bypasses the whole `allowsConcurrentEdit` mechanism (no `If-Match`, no per-item version) and collapses `MetadataFieldUnknown`/`Ambiguous`/`NameReserved` into a single `FieldNotFound` code that no write model produces. |
| MI-22 | Low | `GET /versions` includes version `0` as a version, while `PurgeVersion` requires `versionNumber >= 1` and `CurrentVersionNumber` is `0` until first publish. Three meanings for `0`. |

### MediaProfile (Catalog)

| # | Sev | Finding |
|---|---|---|
| MP-1 | Critical | **`ReviewPolicy` gates nothing.** `mediaprofile.write-model.md` ~165: *"`ReviewPolicy` itself gates nothing today (D-7): the publish path never reads it."* `PublishMediaItemCommand` takes `ReviewerIds[]` **from the client**, and an empty list publishes immediately. `RequiredForPublish` is unenforceable by construction, not by omission. |
| MP-2 | Critical | **The capability set that reaches a MediaItem is computed from a concept RecordType does not have.** ~119: `CompiledMetadataTemplate.Capabilities` is *"The union across contributing RecordType versions"*, and ~185: that union *"is what `MediaItemCreated` embeds and what the `Processing` gate reads"*, while *"`MediaProfile.Capabilities` — the set the author declared — reaches `MediaProfilePublishedIntegrationEvent` and stops there."* Metadata's own overview (~330) states: *"**`RecordType` has no capability concept at all.**"* Two consequences: (a) a profile published with capabilities but no record types short-circuits to `CompiledMetadataTemplate.Empty` and reaches items with an empty capability set; (b) `Processing`, `Registration` and the quota exemption all hang off this. |
| MP-3 | Critical | **Seven of nine capabilities gate nothing, including every governance capability.** ~164-170. `Review`, `CheckInOut`, `VersionControl`, `Signing`, `Distribution`, `Governance` — all ❌. The seeded `Governed Media Record` profile's governance is `Review + CheckInOut + Registration`; two of those three are inert. |
| MP-4 | Critical | **`PublishedProfileReadModel` has none of the fields the handlers read from it.** `mediaitem.write-model.md` ~599: `(MediaProfileId, Version, CompiledTemplate, RecordTypeRefs, AssetDefinitions, Capabilities)`. `CheckOutMediaItemHandler` *"Resolves the lease duration and the change-request policy"* from `GetPublishedAsync` (~513) and the guard reads `profile?.CheckoutPolicy` (~165). None of `CheckoutPolicy`, `LeaseDurationMinutes` or `ChangeRequestPolicy` is on that record. |
| MP-5 | High | **`UpdateAssetDefinition` renames the role, and role names are the join key to every existing item.** ~249. Items pin `MediaProfileSnapshot` at creation, but `PublishMediaItemHandler` *"Loads the **aggregate**"* and checks required roles against the **current** published definitions (~511). After a rename, every pinned item's `MediaAssetReference.RoleName` refers to a role the live profile no longer has, and the conformance fan-out manufactures `MissingRequiredAssetRole` gaps whose remediation duplicates an already-assigned asset. |
| MP-6 | High | **A never-published profile can never be discarded, deprecated or deleted.** `DiscardDraft` guards `Status == Published` (~261); `Deprecate` guards `Status == Published` (~263); there is no `DELETE`. An abandoned profile holds its tenant-unique name permanently — and RecordType has `Abandon` for exactly this. |
| MP-7 | High | **`RetentionScheduleRef` does not exist on the aggregate.** The `Retention` publish gate (~167) requires a pin that appears in no Properties table, no `MediaProfileDraft`, no `MediaProfilePublishedSnapshot`, and no read model or DTO. |
| MP-8 | High | **The publish compensation is one-sided and the spec says what it costs.** ~366-369: on a failed save after a rename, the `catch` releases the **new** name only. *"The stored aggregate still carries the old name while holding **no reservation at all**."* |
| MP-9 | High | **The breaking-change guard is best-effort.** `CheckRevisionBreaksAsync` is *"Best-effort, non-transactional break detection"* (~340). *"Removing a capability from a draft is a breaking change"* (~181) is therefore advisory, not enforced. |
| MP-10 | Medium | **`AssetDefinitionDefaultSet` carries no old value**, so replacing a default asset never releases the previous asset's `DefaultAssetId` protection — while `MediaProfileDeprecated` deliberately carries `DefaultAssetIds` to release them. Every other Catalog event carrying a replacement carries `Old`/`New`. |
| MP-11 | Medium | **A retention argument is used to justify metadata-field precedence.** ~143, inside § Metadata field collision resolution: *"**No precedence logic exists and none should be built.** A profile pins exactly one `RetentionSchedule`, so there is never a second disposal rule to reconcile."* Disposal rules have nothing to do with colliding metadata field names. |
| MP-12 | Medium | **Scope key spelled two ways.** `concurrency-and-consistency.md` ~214 gives `"media-profile"`; `mediaprofile.write-model.md` ~333/~346 gives scope `MediaProfile`, against that file's own rule that scope keys are *"lowercase with colon delimiters"*. |
| MP-13 | Medium | `AssetDefinition` in the glossary has no `IsDefault`; the write model and the read DTO do. `ListMediaProfilesQuery` is specified against `media-profile` (detail) while `MediaProfileSummaryProjector` maintains `media-profiles`, which then has no reader. |
| MP-14 | Medium | **Seeding is the only source of profiles and nothing invokes it.** `mediaprofile.defaults.md` ~155: *"There is no `TenantProvisioned` consumer, no seeding Lambda"*. `mediaProfileId` is required on item creation and must be `Published`. A new tenant cannot create a single item until an operator runs a CLI. Deprecating a seeded profile also frees its name, so the next run recreates it under a new id. |
| MP-15 | Medium | A profile pins at most 3 record types and at most one version each, and the one-version rule is well argued (~229) — but the rule that makes it necessary, *"both keys are identical for v1 and v4"*, is exactly the rule that makes a pinned version change re-key nothing. See RT-4. |

### ChangeRequest (ChangeRequests)

| # | Sev | Finding |
|---|---|---|
| CR-1 | Critical | **`Kind` — the discriminator the Catalog gate depends on — is specified three ways.** `changerequest.write-model.md` ~52: *"**`Kind` is a stored property, replicated onto `ChangeRequestReference`.**"* `changerequest.scenarios.md` ~28: *"It is derived at map time … rather than stored"*. `changerequest.read-model.md` ~25: *"the endpoint layer derives `kind` from it"*. Neither read model has a `Kind` field and no projector writes one, while both API responses render `"kind": "governance"`. |
| CR-2 | Critical | **`Kind` is "fixed at creation" and appears on no creation event.** ~50 vs the `ChangeRequestCreated` payload at ~232. An event-sourced property with no field on its own creation event cannot be fixed at creation; ~58 then concedes it is replayed from `ReviewSessionId`. |
| CR-3 | Critical | **`EditComment`/`DeleteComment` have an open-status gate and do not, in one file.** Invariants ~112 and guard order ~142 require `IsOpen` (422); Operations ~204 says *"No Status gate — permitted at any time"* and Design Notes ~347 agrees, as does the API. Two readers build two systems. |
| CR-4 | High | **"A governance record freezes when it closes" is asserted and implemented nowhere.** `changerequest.scenarios.md` ~245 vs ~266 *"No lifecycle gate — permitted even after … `Resolved` or `Abandoned`"* and `changerequest.api.md` ~204. In a regulated-records product, the governance record accepts body edits and deletions after it is terminal. |
| CR-5 | High | **`Create` has no invariants at all.** ~71: *"**None.** Neither handler checks for an existing open request"*. Consequences: `title` is "required" with no domain rule; `ParticipantIds` is uncapped and replayed forever, where `EditSession` caps collaborators at 25 for exactly that reason; nothing checks `MediaItemId ∈ Scope`. |
| CR-6 | High | **`Scope` is a client-supplied list with no invariant.** ~41 *"Today always exactly `[MediaItemId]`"* is a usage description presented as a rule. A caller can open `{ mediaItemId: "mi-01", scope: ["mi-99"] }` — a governance request whose scope excludes its own item. Conversely, for requests created the documented way the `ChangeRequestNotForItem` check can never fail, so the gate's `Scope` half is tautological. |
| CR-7 | High | **Any participant can terminate a live review's comment thread, irreversibly.** `MayClose` includes `IsParticipant` (~80) and both terminal states have *"No reopen, no un-resolve, no un-abandon"* (~74). On a comment thread, participants are the reviewers. |
| CR-8 | High | **A lost close is unrecoverable and unobservable by design.** ~313: *"Any other error is logged as an error and **the message is still acked** — a failed close is not retried and not dead-lettered."* With no reopen and no reconciliation, a dropped `MediaItemApproved` strands an `Open` governance request permanently — the exact leak CR-15 was introduced to fix. |
| CR-9 | High | **Rejected and withdrawn reviews are recorded as `Resolved`.** All three review-ending handlers dispatch `ResolveChangeRequestCommand` (~309), and `Resolved` is defined as *"the change it governs has landed"* (`changerequest.read-model.md` ~201). `Abandoned` exists for the opposite and is never used by the review path. This is the audit trail. |
| CR-9b | High | **Only approval closes a governance request.** ChangeRequests' `context-overview.md` ~137: `media.item.approved` is *"The only path that closes a governance request"*, and the lifecycle table (~174-176) leaves it *"Left open"* on both rejected and withdrawn. Every rejected or withdrawn governed edit strands an open governance request against the item — and under `ChangeRequestPolicy = RequiredForEdit` that stale request stays citable on the next checkout, since the gate only asks whether it is `Open`. |
| CR-10 | High | **The withdrawn close never fires.** ChangeRequests' `context-overview.md` ~139: *"⚠ **Inert — the producer is not built.** `MediaItemDomainEventMapper` has no `MediaItemWithdrawn` case"*, against `changerequest.scenarios.md` ~161, which says both rejected and withdrawn are deliverable. One third of the "a review ends three ways and all three close it" rule is dead. |
| CR-11 | Medium | **Two property tables for one aggregate, disagreeing.** `Participants` vs `ParticipantIds`; `ChangeRequestId` typed as a value object in one and `GUID` in the other, against the platform rule that ids are never raw `Guid`. The same table is also specified twice with different keys — the write-model copy omits the mandatory `TENANT#` prefix and the `AuthorId` its own edit guard needs. |
| CR-12 | Medium | **Deleted comments are both returned and `404`.** `changerequest.api.md` ~326 returns them with `isDeleted: true`; ~362 returns `404` for the single-comment read — the exact contradiction the delete endpoint's own note (~249) rejects. |
| CR-13 | Medium | `CommentId` is *"caller-generated"* (~212) and *"**server-generated**"* (~247). The detail projector's event set (three lifecycle events) cannot maintain the `CommentCount` and `UpdatedAt` fields it declares. |
| CR-14 | Medium | **Catalog mints ids for another context's aggregate.** `PublishMediaItemHandler` *"mints a fresh `ChangeRequestId` on every publish with reviewers"* — and that id is what the submit-time fail-closed gate then looks up in an eventually-consistent index with *"**Staleness bound:** **none**"*. |
| CR-15 | Low | Every comment on a `governance` request — which has no review — is recorded as a `ReviewComment*` event. `ResolvedAt` is also the timestamp for `Abandoned` and is exposed under that name. |

### RecordType (Metadata)

| # | Sev | Finding |
|---|---|---|
| RT-1 | Critical | **The whole uniqueness guarantee rests on machinery the same file says does not exist.** `recordtype.write-model.md` ~1563: *"`IReservationOwnerProbe` does not exist … and neither does promote-or-reclaim"*, ~1568: *"So a stuck identifier is permanent in every scope today."* Name uniqueness, the retained-name rule and the `{alias}.{fieldName}` collision key all sit on a one-phase reservation row with no `State`, no `ExpiresAt` and no reclaim. |
| RT-2 | Critical | **`ReplaceField`'s immutability guard is specified against two different baselines.** ~678 argues the fork is unrepairable because *"`ReplaceField` refuses an immutable baseline"*; the invariants table (~1007) reads the flag from `PublishedSnapshot`. For a name the latest version no longer carries, the guard passes vacuously and a published-immutable field's type changes. |
| RT-3 | Critical | **Which alias qualifies a colliding field is undetermined.** Up to ten aliases may be pinned and `RecordTypePublished.Aliases` pins the whole set; ~184 offers *"`{alias}.{fieldName}` and `{recordTypeId}.{fieldName}`"* as an either/or chosen per field, with nothing selecting *which* alias. The qualified metadata key is not a function of the pinned version. |
| RT-4 | High | **A later alias edit changes a published version's qualified keys.** `SetAliases` is not draft-gated and is unguarded against aliases a published version pins; retention protects the reservation, not the key. v1 and v2 can qualify the same field under different keys, and items created under each are not re-keyable. |
| RT-5 | High | **"Structural mutations operate on the draft only" is false for two members of the version snapshot.** ~19 vs `Aliases` *"Root-level and **not draft-gated**"* (~108) and `Update`'s rename, both of which pin into the immutable published version with no draft preview. |
| RT-6 | High | **`Name` is unique tenant-wide and is not.** ~105 vs ~1627: *"Uniqueness is therefore scoped to non-abandoned record types."* `recordtype.api.md` ~894: *"two rows sharing a name, one of them abandoned, is the expected shape"*. |
| RT-7 | High | **The only recovery for destroyed draft work has no backfill and no rebuild.** `recordtype.api.md` ~308 says a discarded draft is reconstructible from history; `recordtype.read-model.md` ~332: *"This table has no backfill and no rebuild path, and it is the compliance artefact."* `RecordTypeDraftDiscarded` carries only a `Reason`, breaking that file's own rule that an event replacing a value carries the replaced value. |
| RT-8 | High | **Version retirement reaches nobody and the two files disagree that it does.** Metadata's `context-overview.md` ~161 marks `RecordTypeVersionDeprecated` *"⚠ not shipped … nothing can address a single one today"*; `recordtype.write-model.md` ~1686 declares the mapper and consumer with no marker. `DeprecateRecordTypeVersion`, `CannotDeprecateLastVersion` and `supersededBy` all depend on it. |
| RT-9 | High | **Retiring a version does not stop it propagating to new records.** Only `AttachRecordType`, `UpdatePinnedRecordTypeVersion` and `PublishMediaProfile` refuse. MediaItem creation reads the profile's already-compiled template, so new items keep being created under a retired version indefinitely — against the stated intent, *"a bad version should stop propagating"* (~1220). |
| RT-10 | High | **A profile pinning a whole-type-deprecated record type has no forward path.** All three re-pin routes refuse against a deprecated type, every version row is deprecated, and no detach command appears in the Metadata files. |
| RT-11 | High | **The lifecycle guard hangs on one unordered, unreplayable SNS delivery.** Metadata's `context-overview.md` ~394: *"if this event is filtered out in transit, the guards never learn, and a deprecated record type stays attachable forever"* — into an index with no rebuild path. |
| RT-12 | High | **Deprecation is terminal, irreversible and blind.** `recordtype.scenarios.md` ~297: *"**The administrator cannot see what this affects, and Metadata cannot tell them.**"* The item-count half is unanswered. |
| RT-13 | Medium | `Order` is patchable on a route whose precondition *"deliberately does not move the tag"* (`recordtype.api.md` ~178), so a stale-but-accepted `fieldVersion` overwrites a concurrent reorder. `SupersededBy` can never be set after the fact. |
| RT-14 | Medium | Wire status vocabulary (`active`) ≠ domain status vocabulary (`Published`); feeding a returned status back as a filter is a `400`. Read model says five of six field events stamp `fieldVersion`; the write model's own table says four. |
| RT-15 | Low | *"All seven field operations sit directly under `/fields`"* — six are listed. The GSI rationale names fourteen summary attributes; the table defines twelve. `SchemaPayloadTooLarge` is *"a structural backstop, not a live refusal"* in one file and a publish error in two others. |

### RetentionSchedule (Metadata — designed, not built)

Judged as a design, not as a build gap.

| # | Sev | Finding |
|---|---|---|
| RS-1 | Critical | **The clock re-stamps on move, reintroducing one of the three defects the item-level placement was chosen to dissolve.** ~28: *"`FolderClosed` writes the closure date onto each contained item, **re-applied on an audited move**"*, against ~33: *"moving between two closed folders re-dated to whichever file the item currently sat in. Pinning on the item dissolves all three."* |
| RS-2 | Critical | **"Pinned by value, exactly as it pins a `RecordType`" is contradicted two paragraphs later.** ~103 vs ~214 *"The item carries **a pinned reference, not four typed strings**"*, with a model sketch showing only `{BuildingConsentFiles, v2}`. RecordType pins by value precisely because the alternative forces a cross-boundary read at disposal time — and no integration event or reference index for schedule content is specified anywhere. |
| RS-3 | Critical | **The `Superseded` trigger resolves a record's disposal clock from a schema's version row.** ~302: *"**`SupersededAt` on the record type's version row**"*. Every item under that record type becomes due simultaneously regardless of when it was filed — and the source field is written only by an explicit, optional `RecordTypeVersionDeprecated` (which RT-8 says is unshipped). |
| RS-4 | High | **The `Closure` trigger is specified twice with incompatible mechanisms.** ~280 *"`ClosedDate` on the item's **current folder**"* (a live lookup) vs ~28 *"The clock is a fact the record holds, not a replicated lookup."* |
| RS-5 | High | **As gated, no computable disposal rule can be authored.** `Destroy` gated, `Review` refused, `Transfer` refused; only `RetainPermanently` is available, and *"`period` … must be absent when it is"* (~500). A shippable v1 authors "keep forever, no period" — the trigger is inert on every legal schedule. |
| RS-6 | High | **The free-text `authority` defect that killed the field-based design survives the move.** ~123 diagnoses `DA-2019/14 s.3.2` / `DA 2019/14 s3.2` as *"unmatchable"*; ruling 4 keeps them as flat fields, and ~492 concedes the register does not exist — while ~214 claims the reference query now works. |
| RS-7 | Medium | The override's concurrency rule (*"refused rather than silently re-based"*) references a mutation the immutable-published-version lifecycle forbids. The publish gate has no migration text and no backfill for items already carrying `retention_expiry_date`. |
| RS-8 | Medium | **`FolderClosed` has no integration event** (see FO-9), so the mechanism that stamps every item's clock has no transport. |
| RS-9 | Critical | **There is no legal hold, and the platform's one destruction primitive sits outside the disposition model.** `PurgeMediaItemVersion` permanently removes a published version snapshot and releases its assets from `VersionArtifact` — the only irreversible destruction the platform performs — and it is specified purely as an admin operation: guards are `versionNumber >= 1`, not-the-current-version, and a non-empty reason. **Nothing consults a retention schedule, a disposition authority or a hold.** `mediaitem.api.md` ~473 gives the worked example as *"GDPR erasure request 2026-114"*, which is precisely the case where a competing legal hold most often exists. `retentionschedule.design-decisions.md` ~250 states the consequence for the other side: *"`Destroy` cannot name an operation the platform can perform while the destruction primitive sits outside the model."* So the disposition model cannot destroy, and the thing that can destroy answers to nothing. A records platform for government agencies needs *suspend disposal, and refuse destruction while suspended* as a first-class, auditable concept that outranks both retention expiry and an erasure request. Raised here because MM-044 did not reach it independently and the recovered **DEC-3** did. |

### Registration

| # | Sev | Finding |
|---|---|---|
| RG-1 | Critical | **Cancel from a dispatched state strands the authority's answer.** `Cancel` is legal from `Submitted` and `PendingConfirmation` (~276) — i.e. after the adapter lodged the filing — and `Cancelled` is terminal. A later confirmation is permanently unrecordable: `Confirm` requires `PendingConfirmation`, there is no route back, and nothing tells the authority the platform abandoned a live filing. |
| RG-2 | Critical | **The 409/422 contract is false for both of this aggregate's 409s.** ~228: *"after a `409` the identical request can succeed once the caller has done one other thing"*. The two are `ItemAlreadyAttached` (no detach command exists) and `DuplicatePendingAmendment` (clearable only by a `[System]` decision). |
| RG-3 | High | **The amendment route bypasses `ItemAlreadyAttached`.** The uniqueness rule is scoped to `AttachMediaItemToRegistration` only (~204); `RequestAmendment`'s only guard is "no `Pending` amendment for the same item" (~278). A document attached pre-confirmation can be appended a second time on approval. |
| RG-4 | High | **Item eligibility is checked at request time and enforced at approval time.** `ApproveAmendment` has no handler pre-condition row and raises the attach unconditionally (~287). Between `Pending` and `Approved` — an interval controlled by an external authority — the document can be withdrawn, archived or deleted. |
| RG-5 | High | **`Discharge` orphans pending amendments permanently.** `Discharge` requires `Confirmed`; amendment decisions also require `Confirmed`; and *"A discharged registration accepts no further commands at all"* (~81). A `Pending` amendment live at discharge has no exit, ever. |
| RG-6 | High | **The filed record is mutable after dispatch.** `registration.scenarios.md` ~130: documents may be attached from any status except the three terminal ones, *"so step 4 could equally have come after step 5"* — step 5 being the lodgement. `Items` can diverge from what the authority received, with no marker distinguishing pre- from post-dispatch attachments. |
| RG-7 | High | **A confirmed `Reference` has no correction path and the spec says so.** ~76: *"correcting a mistyped `Reference` … is **not** addressed here."* `Confirmed` accepts only additive amendments; `Discharged` accepts nothing. The only remedy is a second Registration, which re-increments the archive counter. |
| RG-8 | High | **A `Pending` amendment has no timeout and no owner-side withdrawal.** Both exits are `[System]`. With `DuplicatePendingAmendment`, an authority that never answers permanently blocks any further amendment for that document. |
| RG-9 | High | **The `Published` guard runs on a replica the spec says is knowingly wrong and cannot be rebuilt.** ~505: *"Rows written before the two handlers land keep `IsPublished = true` for items that were withdrawn or deleted, and nothing converges them"*, with no CLI rebuild verb for Registration. |
| RG-10 | High | **"Must be `Published`" holds only at t=0.** A registration initiated against a published item stays valid, submittable and confirmable after the item is withdrawn, archived or deleted — the handler updates the reference row and no live Registration reacts. |
| RG-11 | Medium | The whole amendment lifecycle — three events, three commands, two routes, a sub-state machine — hangs off an `Amendment` record the shared glossary does not declare, and it has identity while sitting in a value-object table. |
| RG-12 | Medium | Guard order (*"registration exists → owner → item eligibility → aggregate invariants"*, ~250) contradicts both scenario files, which expect `422 RegistrationConfirmed` where the stated order yields `MediaItemNotPublished`. |
| RG-13 | Medium | `RegistrationDischarged` is a blanket refusal documented on only 2 of 12 write routes. No discharge member appears in any response contract, so a client cannot distinguish discharged from confirmed except by the status string. |
| RG-14 | Medium | `RegistrationSubmissionRecorded.RecordedAt` is projected nowhere — the moment a filing left the platform is unreadable. `SubmittedAt` is updated by `Resubmit`, which only moves status, so an item parked in `Resubmitted` reports a submission that has not happened. |
| RG-15 | Medium | Nothing prevents duplicate registrations of the same item, type and authority; *"a single MediaItem may carry several independent registrations of different types"* is asserted and never enforced. Each duplicate publishes its own counter `+1`. |
| RG-16 | Low | One concept, four spellings: `RegistrationOfficerId` / `OfficerId` / `ownerId` / `RequestedBy`; plus `CancelledAt` vs the event's `CanceledAt`, and `RegistrationReference` vs `Reference`. The "four codes" rule has a fifth (`400` on three read routes). |

### DocumentSigningSession and the signing saga (designed, not built)

| # | Sev | Finding |
|---|---|---|
| DS-1 | Critical | **The aggregate's state machine is declared to be the projector's.** The glossary classes `SigningSessionStatus` as *"a **read-model** status, consumed by the projector. Not a saga status"*, while the write model makes it the aggregate's field and gates every transition on it (*"A terminal session accepts no further transition"*, ~97). Three layers claim one enum. |
| DS-2 | Critical | **Signer status has two owners in one document.** ~77 *"`Signer` … The aggregate's tracked signer state"* vs ~82 *"a signer's status is derived by the projector … only `SignerDto` holds it"*. The completion invariant (*"Every signer must be `Completed` before the session completes"*, ~96) needs the first; the second invalidates it. |
| DS-3 | Critical | **No path voids the provider envelope.** Cancel is legal in `Initiated`, where the adapter may already have created the envelope; the session goes terminal, the later `RecordEnvelopeCreated` is refused, no lookup row is written, and the envelope stays signable at the provider with every callback unresolvable. The saga *"never calls SecuredSigning"* (~20). |
| DS-4 | Critical | **Compensation is a mandated two-command sequence with one state field and no resume.** *"Order is not optional. Step 1 must precede step 2."* (~122) with no per-step flag, and guards *"on **saga state**, not on the aggregate"* (~145). After unlink succeeds and release fails, redelivery finds the saga already in `Releasing` and acks without acting — the release never happens, silently. |
| DS-5 | Critical | **Archiving an item deadlocks compensation permanently.** `MediaItem.Archive` has no signing check; `UnlinkSigningSession` guards *"not archived"*. `documentsigningsession.scenarios.md` ~68: *"An item released with the flag still set is permanently un-checkoutable and un-publishable, and no operator route clears it."* |
| DS-6 | Critical | **The mutual-exclusion invariant has an open window by construction.** The flag is set only on `SigningEnvelopeCreated` (~90), the check reads a projector-lagged Catalog read model, and no reservation is designed. Two initiate calls seconds apart both pass. A lost `LinkSigningSession` is never retried (see DS-4), so the flag may never be set at all. |
| DS-7 | High | **Is `Completed` terminal?** The write model shows `Completed → RecordSignedAsset → SignedAssetRecorded`; `documentsigningsession.scenarios.md` ~174 makes timeout a no-op on `Completed`. Under the write model a timeout firing while a fully-signed session awaits its asset transitions to `TimedOut` and compensates — discarding a completed signature. `Voided` is likewise reachable *"from any non-terminal state"*. |
| DS-8 | High | **Completion is racy against the spec's own out-of-order guarantee.** *"webhooks are replayable, and callbacks may arrive out of order"* (~141), yet `RecordSigningCompleted` arriving before the last `SignerCompleted` is rejected `422` with no retry path on a synchronous route. |
| DS-9 | High | **The completion invariant asserts a fact only the provider owns.** The signer list is a snapshot captured at initiation; nothing resyncs it when the provider delegates, adds or removes a signer. The aggregate can refuse a genuinely completed envelope forever. |
| DS-10 | Critical | **The adapter and the saga consume the same queue.** DocumentSigning's `context-overview.md` ~57 and `documentsigningsaga.md` ~156 both put `SigningSessionInitiated` on `media-signing`. SQS consumers on one queue compete; the scenario requires both to receive it. |
| DS-11 | High | **The tenant-lookup exception is weaker than claimed.** The row is written by a projector (asynchronous), the PK is a provider-chosen external string with no `TenantId` in the key, the write has no conditional-put rule, re-recording an envelope is unguarded, and the row has an *"Optional TTL once the session resolves"*. Strong consistency on the read covers none of that, and the webhook `200`-acks an unresolvable id so the provider never re-sends. |
| DS-12 | High | **The happy path force-releases the owner's checkout and then asks them to keep working in it.** `documentsigningsession.scenarios.md` ~58 vs ~60. The release also requires an actor the saga structurally does not have (~75), using a user-scoped `ForceReleaseCheckoutCommand`, and can be refused outright if the owner checked in during the days of signing latency — with no error branch out of `Releasing`. |
| DS-13 | High | **`Compensated` is unreachable and `Releasing` is left by a non-event.** The only exit from `Releasing` is *"release path complete"*; every compensation path terminates in `Completed`, and the exit is the synchronous return of two dispatched commands, contradicting the saga's own event-driven model and `AssetIngestionSaga`, *"the reference for every convention this one must follow"*. |
| DS-14 | High | **The signed `Asset` is created by the adapter, outside AssetManagement's model.** No Asset command, event or ingestion path appears anywhere; `SignedAssetId` is carried as a bare `string` with no back-reference. |
| DS-15 | Medium | Signing outcomes are said to *"surface through Catalog"*, but success, void, cancel and timeout compensate identically — a downstream consumer cannot tell "signed" from "expired unsigned". |
| DS-16 | Medium | `RoutingOrder` is required on the public API and on the event contract, and *"No code reads `RoutingOrder` today"* — so sequential vs parallel signing is undecided while both the completion and timeout models depend on the answer. |
| DS-17 | Medium | Signer identity is an email in a URL path, with no normalisation rule and no defined behaviour for an unknown signer — after which the completion gate never satisfies. |
| DS-18 | Medium | Command payloads carry `InitiatedBy` / `CancelledBy` that no route supplies; either they are body-sourced (forbidden for actor data) or the traceability table is wrong. `signingSessionId` is caller-generated *and* `Idempotency-Key` applies, with no defined outcome for re-posting an existing id. |

### Relationships

| # | Sev | Finding |
|---|---|---|
| R-1 | Critical | **`MediaItem` ↔ `MediaProfile` — the activation chain breaks in the middle.** The stated chain is `MediaItem → MediaProfile → Capabilities → domain modules`, and it fails at two links: the set that crosses is the compiled RecordType union rather than the declared profile set (MP-2), and the snapshot and the live profile disagree about what a role is called (MP-5). The write-side query service returns none of the policy fields its callers read (MP-4), and two pinned copies of `CheckoutPolicy` exist on `MediaItem` with the guard reading neither correctly (MI-3). |
| R-2 | Critical | **`MediaItem` ↔ `Asset` — the role binding has two owners and two mechanisms.** Catalog's `AssignAssetToRoleHandler` dispatches `AttachAssetToMediaItemCommand` while AssetManagement's `AssetAssignedToRoleEventHandler` dispatches `ApplyAssetAssignmentCommand`; nothing reconciles them, so one attachment can be applied twice — and AssetManagement's own overview forbids the first. `AssetUnassignedFromRole` and `AssetReplacedInRole` have no integration event on either side, so every downstream index that learned about an attachment never learns it ended. Asset status is checked at publish and at approval but not at assignment — three bars for one relationship. `VersionArtifact` is released only by `MediaItemVersionPurged`, so an item deleted without purging its versions leaves its assets unreachable and undeletable. |
| R-3 | High | **`MediaItem` ↔ `ProcessingJob` — capability lag silently downgrades a record.** Capability resolution crosses on `MediaItemCreated`'s snapshot into an asynchronously-maintained reference index; if it lags an upload the asset resolves as not-capable and takes the bypass path, which is terminal in the job, terminal in the saga and explicitly uncompensated. Bypass and full success also emit the same asset event, so no consumer can tell "processed" from "never processed". |
| R-4 | Critical | **`MediaItem` ↔ `ChangeRequest` — a governance gate neither side can enforce.** Catalog needs `Status`, `Scope` and `Kind`; ChangeRequests specifies `Kind` three ways and stores it nowhere (CR-1/CR-2), `Scope` has no invariant (CR-6), and the contract members are marked not yet built. Direction is stated as Catalog-drives, yet an unguarded `Abandon` by any participant halts submit and publish. The consumed-event count disagrees with the same file's own flow table, one producer is inert (CR-10), and only the winning outcome closes the governance request (CR-9b). Both directions are eventually-consistent mirrored indexes, one fail-closed on absence, with no staleness bound. |
| R-5 | Critical | **`MediaItem` ↔ `Registration` — the counter is the gate and it drifts both ways.** `Rejected` is −1 and `Cancelled` is −1 and Cancel is legal from `Rejected`, so initiate/reject/cancel nets −1 and releases a sibling's hold. Both repair events (`Discharged`, `Resubmitted`) are unbuilt on both sides, so every `Confirmed` registration holds its counter forever *and* a reject with no compensating resubmit leaves a later confirmation counted at zero. The counter was never seeded; the Catalog-side ref handlers have no idempotency fence; attached document items are invisible to Catalog and get no archive protection; the registered item itself is ungated; and the whole gate is bypassable by archiving the collection instead (CO-1). |
| R-6 | Critical | **`Collection` ↔ `Folder` ↔ `MediaItem` — containment is asserted, not maintained.** Containment is expressed on the child and read through a projected index — the right choice — but the index has a gap on first assignment (FO-7) and `IsComplete` is *"a claim about the traversal, not about the tree"* whose dependency *"is not yet met"*. A cross-collection folder move never updates descendants (FO-3), so both stored `CollectionId` fields beneath the moved node are wrong from the moment it commits. Archive means two different things depending on the level invoked, and the spec's own summary is: *"Neither invocation model is wrong on its own; having both is."* Name reservations are released on archive before the aggregate is saved, on all three. An unassigned item is in neither hierarchy. |
| R-7 | Critical | **`MediaProfile` ↔ `RecordType` — schema authority and validation authority have diverged.** A five-property summary crosses a twenty-one-property schema; ten constraint properties, `IsImmutable`, `IsSearchable`, `AllowsConcurrentEdit`, `DefaultValue`, `Group` and `Order` never arrive. `AllowsConcurrentEdit` fails closed to the wrong behaviour silently. `IsDeprecated` is absent from `MediaProfileSnapshotField`, so `DeprecateField` releases nothing where it is enforced. Pin-never-floats holds for the pin and not for the key (RT-3/RT-4), and deprecation propagates on one unordered SNS delivery into an index with no rebuild path. |
| R-8 | High | **`MediaItem` ↔ `DocumentSigningSession` — the link is the invariant and nothing maintains it.** `ActiveSigningSessionId` is set late, checked against a lagged projection, never retried if lost, unlinkable only while un-archived (unenforced), and cleared by a compensation whose ordering is mandatory and unresumable. Its only legitimate caller is a host that *"is named for a saga and is not one"*, and nothing validates that the session being unlinked is the active one. |
| R-9 | Critical | **`Folder` ↔ `RetentionSchedule` — the disposal clock has no carrier.** `FolderClosed` is the stamp; it has no integration event, no guard against being raised on an archived folder, no un-close, and it re-stamps on move (RS-1). The pin it stamps against exists on no aggregate. This is the least-built and highest-stakes edge in the model for a regulated-records product. |

### Systemic

| # | Sev | Finding |
|---|---|---|
| E-1 | Critical | **`media.item.published` does not exist.** Four files state it plainly (Catalog's `context-overview.md` ~123 *"there is no `media.item.published`"*; `persistence-and-eventing.md` ~197; `event-store-and-messaging.md` ~290; MediaItem's own published-events table). `bounded-contexts.md` subscribes Search/Discovery (~148, ~340) and Billing (~152, ~344) to it. `bounded-contexts.md` is the file that owns the published-language contract. Every consumer built from it receives nothing. |
| E-2 | Critical | **Invariants and pre-conditions are systematically conflated.** The spec index draws the distinction explicitly (row 7 vs row 8) and then Asset, Folder, MediaProfile and Registration all file cross-aggregate, read-model-backed handler checks under § Invariants. Every one of those is a rule that cannot hold and is documented as if it does. |
| E-3 | Critical | **Every cross-aggregate guard in the system reads an eventually-consistent projection with "Staleness bound: none".** Registration's published check, the change-request gate, the capability resolution, the archive registration guard, the RecordType deprecation guard, the signing mutual-exclusion flag. Five of the six also have no rebuild path. The design is consistent; what is missing is anywhere that says what the guards mean when the projection is behind. |
| E-4 | Critical | **Name reservation is a two-write, non-atomic protocol with no reclaim, and the spec knows it.** `concurrency-and-consistency.md` ~252: *"Today the row is indistinguishable from a live one and nothing recovers it."* Four handlers release **before** the save; only two compensate at all, one of them one-sidedly. Every uniqueness invariant on the platform sits on this. |
| E-5 | High | **Cascades and compensations have no persisted state anywhere.** Archive fan-out: no state row, no checkpoint, no cursor. Signing compensation: one status field for a mandatory two-step sequence. `AssetIngestionSaga` is the only process with durable state, and its one watchdog is armed over a lossy leg. |
| E-6 | High | **Idempotency is specified three incompatible ways.** `bulk-operations.md` ~146 *"returns the cached envelope"*; `api-conventions.md` ~71 *"**It rejects the duplicate; it does not replay the original response**"*; `concurrency-and-consistency.md` ~52 agrees with the rejection and notes the key is consumed before execution. Asset confirmation is separately both idempotent and not. |
| E-7 | High | **Commands accept fields they discard, and events carry fields no command supplies.** `WithdrawMediaItemCommand.Reason` (discarded, event carries it); `AssetValidationPassed.JobId` (no aggregate meaning); `Asset.IsPrimary` / `UploadMode` (surfaced, never set); DocumentSigning's `InitiatedBy` / `CancelledBy` (no route supplies them). |
| E-8 | Medium | **Counts do not match their lists, repeatedly.** Catalog's *"Seventeen handler registrations"* against 19; MediaItem's *"Six projectors"* against seven writers; RecordType's *"seven field operations"* against six; `spec/README.md`'s *"twelve aggregates"* against `domain-model.md`'s nine-plus-four; RecordType's fourteen GSI attributes against twelve. Each is trivial; collectively they mean no count in this tree can be trusted without recounting. |
| E-9 | Medium | **Terminal states are terminal for the aggregate and not for the world.** Archived collections accept visibility changes; archived items accept moves and registration-ref removals; archived folders accept closes; discharged registrations orphan pending amendments; `Confirmed` registrations hold a counter forever. In every case the "terminal" claim is made in the status section and broken in the methods table two pages down. |
| E-10 | Medium | **Timestamp and id naming has no convention that holds.** `OccurredAt` vs event-specific names (stated as a rule in Catalog, broken by `CollectionArchived`); `Id` vs `MediaItemId` across read models of one aggregate; `CancelledAt` vs `CanceledAt` on one event; `RegistrationReference` vs `Reference`; `version` vs `newVersion` on adjacent MediaProfile routes, where the wrong one *"binds nothing … and the call is refused `404`"*. |

### Spec integrity

| # | Sev | Finding |
|---|---|---|
| SI-1 | Critical | **Nine `shared/` files the index marks live do not exist.** `docs/spec/shared/` contains exactly six: `api-conventions.md`, `bulk-operations.md`, `concurrency-and-consistency.md`, `event-store-and-messaging.md`, `media-types.md`, `multi-tenancy-and-auth.md`. Missing and cited as authority: `cross-aggregate-invariants.md` (`spec/README.md` row 7b, `domain-model.md`, `mediaitem.write-model.md` ×3, `glossary.md` ×3, `archive-fan-out.md`), `cascade-rules.md` (row 7c, `catalog-domain-invariants.md`), `consistency-model.md` (row 13, four read models, repo `CLAUDE.md`), `error-catalog.md` (row 15, `folder.api.md`, `collection.api.md`, DocumentSigning ×2, repo `CLAUDE.md`), `saga-patterns.md` (row 12, `glossary.md`, repo `CLAUDE.md`, DocumentSigning ×2), `authorization-matrix.md` (row 14b), `magiq-auth-role-claims-requirements.md` (row 14c), `operations.md` (file tree, `archive-fan-out.md`), `security-scenarios.md` (file tree, Catalog `business-scenarios.md`). |
| SI-2 | High | **Three aggregate inventories disagree.** `domain-model.md`: nine coded + four specified = thirteen. `spec/README.md`: *"the twelve aggregates are …"* — a list of twelve including the two bulk-import jobs and omitting `RetentionSchedule`. `spec/README.md` row 3 itself says *"**Two inventories still disagree — 10 vs 12**"*, which matches neither of the other two counts. |
| SI-3 | High | **Files indexed that have no folder.** `bulkfolderimportjob.*` and `bulkmediaimportjob.*` (linked from `domain-model.md`, Catalog `business-scenarios.md`, `bulk-operations.md` and the glossary) and `mediaprofile.design-decisions.md` (linked from `mediaprofile.write-model.md`, `mediaprofile.read-model.md` and `mediaprofile.defaults.md`). |
| SI-4 | Low | **Dangling internal references.** `U-1` (cited in `mediaitem.api.md` and `mediaitem.scenarios.md`), `D-2` (`folder.read-model.md`), `D-11` (`folder.api.md`), and *"see below"* / *"see the GSI note above"* in `changerequest.read-model.md` where no such text follows or precedes. |
| SI-5 | Critical | **The spec carries decision provenance it was explicitly instructed not to carry, pointing at a store no reader can reach.** **43 `MM-nnn` citations across 14 files**, naming six plan ids — `MM-004`, `MM-026`, `MM-040`, `MM-041`, `MM-042`, `MM-043`. **Confirmed 2026-09-16: none exists, and none should have been cited in a spec file in the first place.** Two standing rules forbid it. The repo `CLAUDE.md` § Important: *"Decisions related to changes or reasons do not belong in the spec files. Spec files need to remain pure finalized documents."* And `spec/README.md` row 14 names the Z:\ docs project as the **wrong** place to look for what is contested — *"That is one engineer's machine, which is exactly why this register is in-repo."* A `MM-` id resolves only in that project, so every one of these citations sends a reader — a reader the repo `CLAUDE.md` tells to *"skip those rows"* — to a drive they cannot mount. **The damage is not uniform.** Most citations are provenance and delete cleanly. A minority are load-bearing on a rule's *status or scope*, and deleting those alone leaves the rule undefined: `domain-model.md` ~74 hangs the `MediaItem.RetentionScheduleRef` relationship row on *"Added here 2026-09-14 by MM-043 Phase 0"*; `archive-fan-out.md` ~151 and ~175 make `IsComplete`'s meaning and the persisted cascade report conditional on *"MM-043 Phase 2"* and *"Phase 6"*; `mediaprofile.write-model.md` ~167 gates the `Retention` capability on *"MM-043 Phase 7"*; `collection.write-model.md` ~79 marks collection un-archive *"⏳ Being specified — see below (MM-043 Phase 15)"*, and there is no "below". Remediation is **strip every citation, restate every rule that leaned on one in its own terms** — `⏳` with an owner and a condition where it is genuinely undecided, normative where it is not — and add a CI guard so the pattern cannot return. There is no resolve-the-id branch: the ids are gone and were never legitimate here. |
| SI-6 | Critical | **The same defect, three more id families, 78 more occurrences across 24 files — none defined anywhere in `docs/`.** Every occurrence is a citation pointing out of the tree, to the same unreachable store as SI-5. **Resolved 2026-09-16 (Open Question 14), and the families split.** The **`DEC-`** half is the decision log of the prior aggregate-design review MM-042; all fourteen cited decisions were recovered from their citation sites and re-adjudicated in § Recovered decisions, so those citations delete once each decision is restated in-tree. **`AD-`** and **`X-`** are *finding* ids — MM-042's own register and the global drift register — and a finalised spec has no business carrying a bookkeeping handle for work: they are stripped outright, keeping the correction and the date and dropping the number. Several citations were load-bearing and are named so the restatement is not missed: `domain-model.md` ~74 attributes the disposal-clock re-stamp to *"(DEC-9)"* — the rule overturned at Open Question 4; `mediaprofile.write-model.md` ~165 says `ReviewPolicy` was *"Made authoritative 2026-09-14 (DEC-22)"*, so the MP-1 remediation rests on it; `archive-fan-out.md` ~151/~175 carry *"(DEC-16 / AD-26)"* and *"(DEC-11 / AD-32)"*; `mediaitem.write-model.md` ~410 concludes *"And it explains AD-14"*, whose premise is unreachable. **Eight `DEC-` numbers were taken and never cited and are unrecoverable** — recorded here because it is the measurable cost of the practice, not a gap anything in this plan can close. The standing test: **an id is legitimate in a spec file only if it is defined in a file inside `docs/`.** |

---

## Recovered decisions — the `DEC-` family

**What `DEC-n` refers to.** `retentionschedule.design-decisions.md` ~16 names it exactly: *"DEC-1, DEC-18
of the aggregate-design review **MM-042**; written by **MM-043**"*. `DEC-n` is the decision log of a prior
aggregate-design review, implemented by a plan. `AD-n` are that review's *findings*; `DD-n` is a third
register; `X-n.n` is the global drift register. **MM-042 was a previous pass at the job this review is
doing**, and both it and its plan are gone.

**Why they can be recovered.** In every case the spec states the decision inline and tags it with the
number — *"re-applied on an audited move (DEC-9)"*, *"Made authoritative 2026-09-14 (DEC-22)"*. The
**substance** survives at the citation site; only the **argument** is lost. That is enough to re-adjudicate
each one here, on this review's own evidence, and give it an in-tree home.

**The limit, stated plainly.** Only decisions the spec happened to cite can be recovered. Fourteen distinct
ids appear — 1, 2, 3, 5, 9, 11, 12, 16, 17, 18, 19, 20, 21, 22. The gaps (4, 6, 7, 8, 10, 13, 14, 15) were
taken and never cited, and **they are unrecoverable.** If any of them settled something, that settlement is
gone and the spec never recorded it. Nothing in this workstream can fix that; it is the cost of the
practice SI-5 describes.

**Eleven of the fourteen this review had already re-derived independently**, without reading MM-042 — which
is the useful result, because it means adopting them costs almost nothing and the one conflict is a real
disagreement rather than a lost detail.

| Id | What it decided, from the citation site | MM-044's position | Lands in |
|---|---|---|---|
| **DEC-1** / **DEC-18** | The retention pin of record moves from `MediaProfile` to `MediaItem`, copied from the profile at creation; **and it grants a per-item override after creation**, amending ruling 3's *"No override in v1"* | **Adopt.** Independently reached at Q5. MM-044 adds that neither aggregate declares the field — MI-14, MP-7 — so the decision is currently inexpressible | Phase 5, with the field declarations in Phase 6 |
| **DEC-2** | `CaptureDigest` / `ContentDigest` `{ Algorithm, Value }` and the `VersionManifest`; sequenced early because fixity cannot be reconstructed retrospectively | **Adopt.** Consistent with the glossary's own fixity model. MM-044 adds that the fields exist in no aggregate, DTO or read model (AS-22) | Phase 7 (Asset), manifest half Phase 6 |
| **DEC-3** | Brings `PurgeVersion` **inside** the disposition model as a named, authorised, recorded, refusable act, and **makes legal hold a first-class concept** | **Adopt, and it is the most important of the fourteen.** MM-044 did not reach it — see new finding **RS-9**. A destruction primitive outside the disposition model is a disposal path with no disposal authority, and no legal hold means no way to suspend one | Phase 5 |
| **DEC-5** / **DEC-17** | Declaration — the point content is fixed — is **`MediaItemApproved`**. No separate `Declare` command, because approval already mints the version and carries a human act | **Adopt.** Consistent with MI-1/MI-10 and with Q2. MM-044 adds that the immediate-publish path fires `MediaItemApproved` with a non-nullable `ReviewSessionId` and no session — so declaration currently happens through a malformed event | Phase 6 |
| **DEC-9** | The disposal clock is a stamp written by `FolderClosed`, **re-applied on an audited move** | **Overturn.** See Q4 and RS-1. Re-dating a disposal clock on custodial movement is the classic disposal-avoidance defect, and the design text contradicts itself on this point already (~28 vs ~33). **Stamp once; an audited move records the move, not a new clock** | Phase 5 |
| **DEC-11** / AD-32 | The cascade report must be **readable after the run** — persisted and inspectable per run, rather than computed and discarded | **Adopt.** MM-044 makes it part of the collection-archive remediation (CO-2): a partial disposition that leaves only a warning-level log line is not an auditable disposition | Phase 6 |
| **DEC-12** / **DEC-19** | The disposition-action ladder — `Transfer` and `Review` as first-class actions alongside `Destroy` and `RetainPermanently` | **Adopt in principle, sequence later.** RS-5 is the live problem: with `Destroy` gated and `Transfer`/`Review` refused, the only authorable rule is *"keep forever, no period"* and every trigger is inert. The ladder is what fixes that | Phase 5 |
| **DEC-16** / AD-26 | `IsComplete` is a claim about the **traversal**, not about the tree | **Adopt.** Already stated in `archive-fan-out.md`; MM-044's contribution is FO-7 and R-6 — the dependency that would make it a claim about the tree is unmet, and the first-assignment index gap means a retention-locked item can pass the guard | Phase 6 |
| **DEC-20** / DD-5 | Correction-by-append: changing a recorded fact by an **attributed, reason-bearing act that never overwrites**, with the prior value legible from the aggregate's own surface. Six consumers | **Adopt and extend.** Q10 reaches the same rule and adds a **seventh** consumer: `Registration.Reference` after confirmation (RG-7), which today has no correction path at all | Phase 5 (mechanism), Phase 8 (Registration) |
| **DEC-21** | Also ends *"overridable afterwards"* — the retention override, with DEC-1 | **Adopt**, folded into DEC-1. The design file itself notes neither said what an override *is*; DEC-20 supplies the mechanism | Phase 5 |
| **DEC-22** | `ReviewPolicy` is made **authoritative** — the publish path reads it | **Adopt and strengthen.** Q2 reaches the same conclusion and adds the missing half: auto-submit under `RequiredForPublish` may only submit, never publish (MI-1, MP-1). Without that, making the policy authoritative closes one bypass and leaves the other open | Phase 6 |

**Net effect on this review.** Ten adopted, one adopted-and-extended, one overturned, one (DEC-3) adopted as
new scope. None requires MM-042 to be found. Once each decision is restated in-tree — in the spec where it
is a rule, in an ADR or `<agg>.design-decisions.md` where it is a reason — **every `DEC-` citation can be
deleted without losing anything the spec still needs**, which is what turns SI-6's `DEC-` half from an open
question into work the plan already does.

---

## Open Questions

Questions 1–10 are answered here from records-management and media-management practice, per the standing
instruction to resolve rather than park where practice gives a defensible answer. The reasoning is stated so
the answer can be overturned on its merits rather than re-derived.

1. **Which capability set reaches a `MediaItem` — the declared `MediaProfile.Capabilities`, or the compiled
   RecordType union?**
   **Answered: the declared set.** A capability is a governance aspect of the record class, asserted by
   whoever authors the contract; deriving it from which schema elements a profile happens to cite makes an
   administrative control an accident of composition, and lets a control appear or vanish when a record type
   is attached or detached for unrelated reasons. `metadata-schema-composition.md` already states that
   `Capability` is *"a platform governance aspect and never a general composition mechanism"*; this is that
   rule applied consistently. The compiled union becomes a derived convenience with no authority, or is
   removed. Closes MP-2, R-1, R-7 in part; changes `mediaprofile.write-model.md`, `mediaitem.write-model.md`,
   Metadata's `context-overview.md`, `glossary.md`, `domain-model.md` and two ADRs — which is why it is a
   Phase 0 decision and not an edit.

2. **Does `ReviewPolicy` become authoritative, and what may `AutoSubmitOnComplete` do under it?**
   **Answered: yes, and auto-submit may only submit, never publish.** Declaration — the point after which a
   record's content is fixed — must be a deliberate, attributable act by a responsible officer. A path that
   declares a record because a field was filled in has no such actor. So: the publish path reads
   `ReviewPolicy`; under `RequiredForPublish` an empty reviewer list is refused rather than treated as an
   immediate publish; and auto-submit under that policy may only move the item to `PendingApproval`. The
   spec has already reached this conclusion for itself (`glossary.md` § Declaration, DEC-22) — this finding
   is that nothing implements it and three files still describe the old behaviour.

3. **Collection archive: add the guard, or make it a request the cascade can refuse?**
   **Answered: guard it, and flip the parent after the cascade — i.e. make collection archive behave like
   folder archive.** Two practice rules bear on it. Disposition must never be able to obscure a record under
   a live statutory obligation, which the registration guard exists to enforce and which the collection path
   bypasses. And an aggregation's closed status must be a true statement about its contents; a collection
   that reads archived while an unbounded number of descendants are active is a false statement in the one
   place an auditor looks first. The asymmetry is the defect, and the folder path is the correct side of it.
   The unbounded-subtree problem (CO-8) does not argue for the weaker path — it argues for making the
   cascade chunked and resumable, which is a separate piece of work.

4. **The retention clock: stamp once, or re-stamp on an audited move?**
   **Answered: stamp once.** Re-dating a disposal clock when a record moves between aggregations is the
   classic disposal-avoidance defect — it lets the retention period be extended indefinitely by custodial
   activity that has nothing to do with the record's business meaning. An audited move records the move;
   it does not restart the clock. This overturns the current design text
   (`retentionschedule.design-decisions.md` ~28, *"re-applied on an audited move"*), which contradicts its
   own ruling at ~33 in any case. Closes RS-1; contributes to RS-4 and R-9.

5. **Where does `RetentionScheduleRef` live as a field?**
   **Answered: on `MediaItem` as the pin of record (per DEC-1), with `MediaProfile` carrying the default.**
   That part is already decided; the finding is that neither aggregate declares the field. The decision this
   review adds is that the design is not expressible until both Properties tables carry it — a relationship
   table is not a schema. Closes MI-14 and MP-7.

6. **The nine missing `shared/` files: write them, or repoint the citations?**
   **Answered: write the four that carry normative authority; repoint or delete the rest.** A control that
   exists only by reference is not a control, and a compliance-grade spec cannot carry a promissory link
   where a rule should be. `cross-aggregate-invariants.md`, `cascade-rules.md`, `error-catalog.md` and
   `consistency-model.md` are each cited as *the* authority for a rule that appears nowhere else — those get
   written. `saga-patterns.md`, `operations.md` and `security-scenarios.md` are cited for cross-cutting
   context that exists elsewhere — those citations get repointed. `authorization-matrix.md` and
   `magiq-auth-role-claims-requirements.md` are **out of scope** for this workstream under the authorization
   exclusion and are neither written nor repointed here.

7. **May the ADRs be edited, or must a reversed decision be superseded?**
   **Answered: superseded.** An ADR is a dated record of a decision and its context. Editing one to match
   what the system now does destroys the only account of why the earlier choice was made, which is the thing
   the record exists for. A reversed decision gets a new ADR carrying `supersedes:`; the old one stays, with
   a pointer forward. Additive corrections of fact — a wrong file path, a renamed type — are edits.

8. **`MediaItem` withdraw from `Revising`: what is the correct target status?**
   **Answered: `Published`.** A revision is work in progress against a live published version; abandoning it
   must not unpublish the version readers are already using. Withdraw from `Revising` should either be
   refused with a pointer to `DiscardRevision`, or behave as `DiscardRevision` does. Returning the item to
   `Draft` removes a published record from publication as a side effect of abandoning unrelated draft work,
   and nothing in the spec says that is intended. Closes MI-4.

9. **What is the rule for a terminal state?**
   **Answered: a terminal status refuses every substantive command; the only permitted post-terminal writes
   are metadata about the disposition itself.** Records practice is that a closed or destroyed entity keeps
   its metadata and accepts no change to its substance. Applied here this is one sweep rule that closes the
   E-9 family across five aggregates, rather than five separate arguments.

10. **`Registration.Reference` correction after confirmation.**
    **Answered: by annotation, never overwrite.** The original value stays legible and the correction is
    attributed and reason-bearing. The platform already has this designed as *correction-by-append*; the
    finding is that it was scoped to six consumers and `Reference` is not one of them. Extend it. Closes
    RG-7.

11. **Are there live external subscribers to `media.item.published` today?**
    **Answered (Chase, 2026-09-16): no — there are none.**
    E-1 is therefore a documentation defect with no migration attached: no consumer is receiving nothing
    today, because no consumer exists. The remediation is to correct `bounded-contexts.md` and fold the
    routing keys into one normative table, and no breaking-change notice is owed to Search/Discovery,
    Billing or Notifications. The severity stays `Critical` — the published-language contract states an
    event that does not exist, and the next team to build against it is the injured party — but the fix is
    one phase and one file family rather than a coordinated change across three contexts. Phase 3.

12. **Do the two bulk-import aggregates stay specified?**
    **Answered (Chase, 2026-09-16): no — remove them.**
    `BulkFolderImportJob` and `BulkMediaImportJob` come out of the aggregate inventory, out of
    `glossary.md` (the `Batch`, `Chunk`, `Job` and `Phase` entries), out of `bulk-operations.md`, out of
    `domain-model.md`'s specified-aggregate table and its per-aggregate spec index, out of `spec/README.md`
    (both the file tree and the twelve-aggregate sentence), and out of Catalog's `business-scenarios.md`
    index. This resolves SI-3 outright and simplifies SI-2: the inventory becomes **nine coded aggregates
    plus two specified-and-unbuilt** (`DocumentSigningSession`, `RetentionSchedule`) — eleven, stated once.
    Note the removal is of the *specification*, not of any decision about bulk import as a capability;
    `POST /v1/items/bulk`, `POST /v1/collections/bulk` and the folder bulk routes are inline bulk endpoints
    and are unaffected. Phase 2, with the glossary half in Phase 1.

13. **What is this workstream's relationship to the plan ids the spec cites?**
    **Answered (Chase, 2026-09-16): none of them exists, and none should have been cited in a spec file in
    the first place.** All six — MM-004, MM-026, MM-040, MM-041, MM-042, MM-043 — are dead, and the
    citation itself was the error, not just its target. There is no dependency, no supersede, no deferral
    and nothing to resolve. All 43 occurrences are stripped and every rule that leaned on one is restated
    in its own terms. Raised as **SI-5**, severity `Critical`, because two standing rules already forbade
    it: the repo `CLAUDE.md`'s *"Decisions related to changes or reasons do not belong in the spec files"*,
    and `spec/README.md` row 14, which names the off-repo docs project as the wrong place to send a reader.

14. **Do `DEC-nnn`, `AD-nn` and `X-n.n` go the same way as `MM-nnn`?**
    **Answered 2026-09-16, and the three families split.**

    **`DEC-` — absorbed, not merely stripped.** These are the decision log of **MM-042**, a prior
    aggregate-design review, and this review is doing the same job. Every one the spec cites states its
    substance inline, so all fourteen were recovered, re-adjudicated on MM-044's own evidence, and given
    in-tree homes — see § Recovered decisions. Eleven were independently re-derived here already; ten are
    adopted, one extended, **DEC-9 is overturned** (the disposal clock does not re-stamp on a move), and
    **DEC-3 is adopted as new scope** and raised as RS-9. Once each is restated in-tree the citations delete
    cleanly. **The unrecoverable part is stated rather than hidden:** eight DEC numbers were taken and never
    cited, and whatever they settled is gone.

    **`AD-` and `X-` — stripped.** These are *finding* ids, not decisions: `AD-n` from MM-042's own
    register, `X-n.n` from the global drift register. A finding id is a bookkeeping handle for work, and a
    finalised spec has no business carrying one — the repo `CLAUDE.md` rule applies unchanged. Where a
    citation carries a live claim (*"⚠ Corrected 2026-08-24, drift review X-9.5"*), the correction stays
    and the id goes; the file keeps the date and the statement, which is what a reader needs.

    The test stands for anything found later: **an id is legitimate in a spec file only if it is defined in
    a file inside `docs/`.** SI-6 is narrowed to `AD-`/`X-` accordingly.

---

## Dependencies

**None.** This review has no `depends-on` and no `blocked-by-external`. Confirmed 2026-09-16.

The ids the spec cites are **not** dependencies of this workstream — they are defects in it, tracked as
**SI-5** (`MM-*`, settled) and **SI-6** (`DEC-*`, `AD-*`, `X-*`, pending Open Question 14). None is an
authority, a dependency or a supersede target anywhere in this cycle, and nothing in this workstream waits
on one. Where a citation carried the only account of why a rule is as it is, that account is gone and the
rule is restated from first principles rather than recovered — which is the cost SI-5 and SI-6 are really
measuring.

**External blockers:** none.

> **Open data error on this review's own id.** `Z:\claudia\magiq\projects\magiq-media\reviews\` and `plans\`
> did not exist when this review was written — this file creates the first. **MM-044 and MM-045 were minted
> from the highest id appearing in the repo spec**, which was the only evidence available at the time. That
> basis is now known to be worthless: those citations should never have been in the spec, so they were never
> evidence of anything about the id space. **The true high-water mark is unknown.**
>
> Before any document cross-references MM-044 or MM-045, run the real grep across `reviews/`, `requests/`,
> `plans/` **and `_archive/`** in the live tree. If it returns above MM-043 these two collide and must be
> re-minted; if the tree is genuinely empty they may be renumbered from MM-001, which is a tidier outcome
> and equally valid since no document yet points at them. Either way it is a decision, not a cleanup — a
> duplicate id is a data error and ids are never silently renumbered. **Phase 0, first item.**

---

## Recommended sequencing

The plan refines this. What follows is the order and the convergence machinery, which are the two things
this review is asked to settle.

### Why this order

**Not by severity.** A spec is a dependency graph of quotations: files quote the glossary, aggregate specs
quote `shared/`, derived surfaces quote write models, ADRs record decisions about all of them. Fixing a
Critical finding in a write model before the vocabulary it uses is settled guarantees the fix is re-worked.
The order below is **outermost-authority first**, with one exception at the front.

**The exception is decisions.** Nine findings are not local to any file — the same choice lands in six or
seven documents at once. Editing any one of them first guarantees rework in the other six. So Phase 0 takes
those decisions and writes no spec at all.

### Phases

| Phase | Name | Covers | Why here |
|---|---|---|---|
| **0** | **Decide once** | This review's own id (see § Dependencies); the SI-5/SI-6 citation triage — enumerate all 121 occurrences and classify each **provenance** (delete) or **load-bearing on a rule's status or scope** (delete, then restate); ratify § Recovered decisions and assign each of the fourteen its in-tree home; confirm where answers 1–10 land normatively | Every later phase quotes a Phase 0 answer. **No spec file is edited.** The citation triage is a decision and not an edit because the same restatement lands in six files — and because deleting a load-bearing citation without restating its rule leaves the rule undefined, which is worse than the citation. |
| **1** | Vocabulary and the authority map | `glossary.md`, `spec/README.md`, and executing decision 6 — write the four normative `shared/` files, repoint the rest. SI-1, SI-4, parts of E-3/E-6. The glossary half of the bulk-import removal: the `Batch`, `Chunk`, `Job` and `Phase` entries. **And the CI guard for SI-5/SI-6** — extend `.github/workflows/docs-guard.yml` to fail any spec file containing an id pattern not defined inside `docs/` | Everything downstream cites these. Until the four authorities exist, no aggregate spec can be made correct: its *"see X for the rule"* is a dangling promise. The guard lands here, before the stripping starts, so the remediation cannot reintroduce what it is removing — stripping without a guard just resets the clock. |
| **2** | Inventory and relationship model | `domain-model.md`. SI-2, SI-3, SI-5's citations in this file, MI-14, MP-7, and the relationship table's references to fields that do not exist. Removes `BulkFolderImportJob` and `BulkMediaImportJob` from the inventory, the spec index and `bulk-operations.md`; the inventory becomes **nine coded plus two specified-and-unbuilt**, stated once | Settles what exists before anything describes it. The bulk removal lands here rather than in Phase 9 because the inventory is what four other files quote. |
| **3** | Published language | `bounded-contexts.md`, `event-store-and-messaging.md`, and one normative routing-key table with one owner. E-1, MI-16, PJ-18, R-2's missing events, FO-19, CO-10 | This is the external contract. It is fixed before the internals that feed it, so no later phase re-derives an event name. |
| **4** | The invariant / pre-condition sweep | All eleven write models, mechanically. E-2, and the `Critical` half of AS-8, AS-11, FO-4 | One rule, applied everywhere, before anyone argues about individual invariants. Doing it per-aggregate inside phases 5–8 would mean eleven separate arguments about the same distinction. |
| **5** | Metadata, retention and disposition | `recordtype.*` write model, then `retentionschedule.design-decisions.md`. RT-1..RT-15, RS-1..RS-9, R-7, R-9. Carries the recovered **DEC-1/18/21** (item-level pin plus override), **DEC-9 overturned** (stamp once), **DEC-12/19** (the disposition-action ladder), **DEC-20** (correction-by-append, the mechanism), and **DEC-3 / RS-9** — legal hold as a first-class concept and `PurgeVersion` brought inside the disposition model | Metadata → Catalog is conformist: the profile pins RecordType versions and compiles their fields, so the schema model is settled before the thing that consumes it. RS-9 lands here rather than with `MediaItem` because a hold is a disposition concept that must outrank both retention expiry and an erasure request — putting it on the aggregate that happens to expose the purge route would make it a property of the route. |
| **6** | Catalog write models | `mediaprofile` → `mediaitem` → `folder` → `collection`. MP-*, MI-*, FO-*, CO-*, R-1, R-4, R-6 | In that order: the profile defines the contract the item conforms to; folder and collection are containers the item references. Check MM-026 before starting (see § Dependencies). |
| **7** | AssetManagement and Processing | `asset.write-model.md`, then `processingjob.write-model.md` and `assetingestionsaga.md`. AS-*, PJ-*, R-2, R-3, E-5 | One pipeline, fixed as one. Depends on Phase 6 for the capability decision's landing point. |
| **8** | ChangeRequests, Registration, DocumentSigning | `changerequest.*`, `registration.*`, `documentsigningsession.*` and its saga. CR-*, RG-*, DS-*, R-5, R-8 | All three are driven by Catalog. They cannot be made consistent until Catalog is. |
| **9** | Derived surfaces | Every `api`, `read-model` and `scenarios` file. The remaining Medium/Low findings in each aggregate | Derived documents quote normative ones. Doing them per-aggregate as you go means redoing them when a later phase changes a shared rule — which phases 3, 4 and 5 all do. |
| **10** | ADR reconciliation | All eight ADRs, against what the spec now says. Per decision 7: additive corrections are edits; reversed decisions get a superseding ADR | Last, because an ADR records a decision about the spec, and the spec is not settled until Phase 9 closes. |
| **11** | Re-baseline | Loop C, below | The acceptance test for the whole plan. |

### The loops

Three nested loops. Each has a termination rule, because a convergence loop with no bound is its own defect.

**Loop A — the ripple sweep. Runs inside every checklist item.**

An item is not complete when the edit is made. It is complete when the edit's blast radius has been walked.
On finishing an edit, grep the whole `docs/` tree for every term, type name, event name, routing key, error
code, table name, scope key and file path the edit touched — **plus, on every item without exception, the
standing pattern `\b(MM-[0-9]{3}|DEC-[0-9]+|AD-[0-9]+|X-[0-9]+(\.[0-9]+)?)\b`**, so remediation cannot
reintroduce an off-repo citation while removing them (SI-5, SI-6). Then classify every hit:

- **Consistent** — record the count in the item, move on.
- **The same finding, in another file** — extend the current item to cover it. Permitted: it traces to a
  finding id the plan already consumes.
- **A different defect** — **do not add a checklist item.** It goes to the drift register with an `X-`
  number, or to a new review. This is the skill's rule and it is the one that keeps the plan's scope
  honest; the temptation to absorb it is exactly why the rule exists. Record the diversion in the session
  log and ask which register.
- **A hit that invalidates the phase's approach** — stop. Do not re-plan in place.

**Loop B — the phase-exit gate. Runs at every phase boundary.**

A phase closes only when all four hold:

1. Every checklist item ticked.
2. The phase-level ripple sweep returns zero **inconsistent** hits — that is, re-running Loop A's grep set
   across every term the phase changed finds nothing left disagreeing.
3. A re-read of every file the phase touched against that phase's own acceptance rules. Not the diff — the
   file. A diff cannot show a statement that should have changed and did not.
4. The repo's `docs-guard` CI workflow passes. It already fails a spec file ending mid-construct and a
   context overview that grows a Ubiquitous Language section back; both are failure modes this remediation
   can cause.

Any of 2–4 failing re-opens the phase. **Bound: three re-opens.** A phase that will not close in three is
not a phase with remaining work — it is a phase whose scope is wrong, and that is a finding about the plan,
raised as one.

**Loop C — the re-baseline. Runs once at Phase 11, and is the plan's acceptance test.**

Re-run this review. Same scope, same method, a fresh session started from `MM-044`'s prompt file with no
context from the remediation. Diff the new finding register against this one.

- **Zero findings of `High` or above tracing to MM-044's scope** → the plan may close.
- **Any `High`+ in scope** → the plan re-opens at the phase that owns that area, and Loop C runs again after
  it closes.
- **Any `Critical`/`High` outside MM-044's scope** → a new review, not a re-open. Scope creep inside a
  closing plan is how a remediation never ends.
- **Bound: three iterations.** Failing to converge in three means the spec's structure — not its content —
  is the problem, and that conclusion is itself the deliverable. Say so and stop.

This is the records-management pattern for closing a nonconformance: the corrective action does not close
it, the re-audit that fails to reproduce it does. Applied to a spec, the re-audit is a fresh review from the
same prompt.

### Three standing rules for the whole plan

- **A file touched in three different phases is a signal its ownership is wrong.** Raise it rather than
  editing it a third time — the spec's own index exists precisely to give every question one home, and a
  file that keeps coming back is one the index has mis-assigned.
- **Never repair a citation by weakening it.** Where a rule cites an authority that does not exist, the two
  permitted outcomes are *write the authority* and *state the rule here and delete the citation*. Softening
  the wording so the missing file no longer looks load-bearing is not a third option.
- **Strip off-repo id citations wherever a phase meets one** (SI-5, SI-6), whatever phase that is. A spec
  rule whose status is expressed as *"Phase 7 of MM-043"*, or whose reason is *"(DEC-9)"*, is undefined the
  moment the reader cannot reach the target — and no reader outside this machine ever could. Restate the
  rule in its own terms: `⏳` with an owner and a condition where it is genuinely undecided, normative where
  it is not. Phase 0 sets the disposition for all 121; the phases execute it in the files they are already
  touching. **The governing rule is the repo's own:** *"Decisions related to changes or reasons do not
  belong in the spec files. Spec files need to remain pure finalized documents."* Where a phase finds a
  reason worth keeping, it goes to an ADR or a `<agg>.design-decisions.md` — in-tree, and by name rather
  than by number.

---

## Related

- Plan: **MM-045** — gated on this review reaching `findings-agreed`. All fourteen questions in
  § Open Questions are answered as of 2026-09-16.
- Convention: `projects/magiq-media/CLAUDE.md` § Review → Plan, and § Review → Plan cycle.
