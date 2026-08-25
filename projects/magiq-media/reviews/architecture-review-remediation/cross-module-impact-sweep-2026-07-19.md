# magiq-media — Fresh Cross-Module Impact Sweep (code-first, all modules)

**Date:** 2026-07-19
**Reviewer role:** Principal Domain Architect (independent second opinion)
**Method:** A/B/C seam triangulation — every `media.*` event verified from the producer contract (A), the consumer bridge (B), and the SNS/SQS transport + filter policy (C), from code and spec first-hand. The existing reviews in `docs/reviews/` were held unseen until §7.
**Repos read:** app `D:\source\github\magiq-media`; deploy `D:\source\github\cdk-magiq-media`; platform `D:\source\github\aspnetcore-platform`; spec/ADRs `magiq-media\docs\`.
**Scope:** cross-module seams only — integration events, cross-boundary command dispatch, shared write-side reference/counter models, sagas, and the SNS/SQS/DLQ topology. Intra-aggregate internals, projector field bugs, validators and DTO shape are out of scope except where they change what another module receives.

> **Independence note.** This sweep was derived without reading the prior reviews. It converges almost entirely with the existing `cross-module-integration-review.md` — which is strong corroboration, not inheritance. §7 reconciles the two; the small set of genuine deltas is called out there.

---

## 1. System integration summary

### 1.1 Derived topology

Two SNS topics, five SQS queues (all standard, non-FIFO, `rawMessageDelivery:false`), each queue with a DLQ (`maxReceiveCount:3`) and a depth alarm. Filter policies key on the SNS **message attribute `EventType`**, which carries the producer's `[MessageType]` string.

```
                          ┌────────────────────────────┐
   Api (write host) ──────► media-domain-events (SNS)   │
   [only host with a           │  (internal shapes)     │
    platform IMessageBus]      ├──► media-projector ─────────► Projectors.ReadModel   [NO filter: firehose]
                               └──► media-projector-search ──► Projectors.Search      [deploySearch=false ⇒ orphan]
   Api (write host) ──────► media-integration-events (SNS)
                               │  (published language, EventType-filtered)
                               ├──► media-processing            ──► ProcessingWorker   [EventType = upload-confirmed]
                               ├──► media-cross-module-events   ──► EventConsumers      [24-value allowlist]
                               └──► media-sagas                 ──► SagaOrchestrator    [5-value allowlist]

   TimeoutScanner  ◄── EventBridge rate(5 min)   (scans AssetIngestion sagas only)
   SagaOrchestrator.DocumentSigning ── NO queue, NO event-source mapping (deferred)
```

Producing/consuming hosts: **Api** is the only host that raises domain→integration events on the write path *and* the only host that registers a platform `IMessageBus` / SNS publishers (and only in its production branch). **ProcessingWorker**, **EventConsumers**, **SagaOrchestrator** consume via the AWS.Messaging consumer integration but do **not** register the platform publisher — yet they run command handlers that raise integration events. This asymmetry is the root of most Critical findings.

### 1.2 Production-readiness verdict

**NOT production-ready.** The asynchronous choreography does not function end-to-end in any environment:

- In **dev/qa** (the only currently-deployed environments) the Api host uses an **in-process** message bus, so integration events never reach SNS and the worker Lambdas are never triggered.
- In **prod/staging** (deploy disabled) the Api host *would* publish to SNS, but the three async hosts that raise the ingestion/validation/processing integration events register **no** publisher, so those events cannot be published from where they originate.

The result: everything downstream of the Api write host — the entire upload → scan → validate → process → complete chain, and the `AssetIngestionSaga` that drives it — is inert. On top of that, several seams are additionally severed at the SNS filter (RecordType→Catalog, asset.archived→Catalog) or at the consumer bridge (asset-assigned, submitted-for-review), and the multi-tenancy convention (tenant from SNS attribute, never body) is violated systemically.

### 1.3 Counts

| Failure class | Count | of which Critical / High |
|---|---|---|
| 1 — Missing subscription | 7 | 0 / 5 |
| 2 — Event not emitted | 4 | 1 / 3 |
| 3 — Mishandled event | 7 | 1 / 3 |
| 4 — Bad event design → wrong action | 3 | 0 / 0 |
| 5 — Invalid cross-module flow | 5 | 2 / 2 |
| **Total** | **26** | **4 Critical / 13 High / 7 Med / 2 Low** |

Critical: **S-08** (async hosts can't publish), **S-12** (processing-completed/failed DLQ-loop), **S-22** (AssetIngestionSaga dead end-to-end), **S-23-C** (review→change-request severed at two points — high-critical, counted High below but Critical-in-effect).

---

## 2. Integration event catalogue

Legend — **A** route registered in the host where the triggering handler runs? · **B** a consumer handler bridged (registered on the bus, not just DI)? · **C** does the `media-integration-events` filter policy pass this `EventType` to that consumer's queue? · Status ∈ ok / missing-sub / not-emitted / mishandled / bad-design / invalid-flow.

### AssetManagement (producer)
| `[MessageType]` | Producing host | A | B | C | Real consumer(s) | Idempotency | Status |
|---|---|---|---|---|---|---|---|
| `media.asset.upload-initiated` | Api | ✓ | ✓ | ✓ | Catalog `AssetStateReference` | version-guarded | ok (tenant-from-body) |
| `media.asset.upload-confirmed` | Api | ✓ | ✓ | ✓ (in **two** filters) | ProcessingWorker **and** EventConsumers Processing handler | **none — new JobId/run** | **bad-design/invalid-flow** (S-13) |
| `media.asset.archived` | Api | ✓ | ✓ | **✗ not in filter** | Catalog `AssetArchivedEventHandler` (bridged) | version-guarded | **missing-sub** (S-02) |
| `media.asset.deleted` | Api | ✓ | ✓ | ✓ | Catalog `AssetStateReference` delete | idempotent | ok |
| `media.asset.attached` | Api | ✓ | — | ✗ | none in MM (outbound only) | — | informational |
| `media.asset.infection-detected` | **EventConsumers** | **✗** | ✓ | **✗ not in filter** | Catalog `AssetInfectionDetectedEventHandler` | version-guarded | **not-emitted + missing-sub** (S-03) |
| `media.asset.validation-passed` | **EventConsumers** | **✗** | ✓ | ✓ (sagas); also stray in cross-module filter → DLQ | `AssetIngestionSaga` | saga status-gate | **not-emitted** (+ S-06 stray) |
| `media.asset.processing-completed` | **EventConsumers** | **✗** | ✓ (but DLQ-loops) | ✓ | Catalog proj + auto-submit; saga | proj version-guarded | **not-emitted + mishandled** (S-12) |
| `media.asset.processing-failed` | **EventConsumers** | **✗** | ✓ (DLQ-loops) | ✓ | Catalog proj; saga | version-guarded | **not-emitted + mishandled** (S-12) |
| `media.asset.processing-timeout-recovered` | **EventConsumers** | **✗** | ✓ | ✓ (sagas) | `AssetIngestionSaga` | saga status-gate | **not-emitted** |

### Processing (producer)
| `[MessageType]` | Producing host | A | B | C | Real consumer(s) | Status |
|---|---|---|---|---|---|---|
| `media.processingjob.created` | ProcessingWorker | **✗ (no publisher in ANY host)** | ✓ | ✓ (sagas) | `AssetIngestionSaga` **start trigger** | **not-emitted** (S-09) |
| `media.processingjob.scan-result` | ProcessingWorker | **✗ (no publisher in ANY host)** | ✓ | ✓ | AM `RecordValidationResultCommand` | **not-emitted** (S-09) |
| `media.processingjob.bypassed` | SagaOrchestrator/Worker | **✗ (no publisher in ANY host)** | ✓ | ✓ | AM `ActivateDocumentAssetCommand` | **not-emitted** (S-09) |
| `media.processingjob.started` | SagaOrchestrator | **✗ (registered only in Api — wrong host)** | ✓ | ✓ | AM `StartAssetProcessingCommand` | **not-emitted** (S-10) |
| `media.processingjob.completed` | ProcessingWorker | **✗ (only in Api)** | ✓ | ✓ | AM `CompleteAssetProcessingCommand` | **not-emitted** (S-10) |
| `media.processingjob.failed` | ProcessingWorker | **✗ (only in Api)** | ✓ | ✓ | AM `FailAssetProcessingCommand` | **not-emitted** (S-10) |

### Catalog (producer — all raised in Api)
| `[MessageType]` | A | B | C | Real consumer(s) | Status |
|---|---|---|---|---|---|
| `media.collection.archived` | ✓ | ✓ | ✓ | Catalog fan-out worker (tenant from `IExecutionContext` ✓) | ok, but **non-idempotent + hard-archives descendants** (S-26) |
| `media.item.created` | ✓ | ✓ | ✓ | AM capability ref + Registration ref | ok |
| `media.item.approved` | ✓ | ✓ | ✓ | AM `PromoteAssetToVersionArtifact` (per-asset, swallows) + Reg | **mishandled** (S-15/S-16) |
| `media.item.archived` | ✓ | ✓ | ✓ | AM + Reg refs | ok |
| `media.item.submitted-for-review` | ✓ | **✗ (handler never DI-registered)** | ✓ | ChangeRequests — none live | **missing-sub / invalid-flow** (S-05) |
| `media.item.version.purged` | ✓ | ✓ | ✓ (dot-form matches) | AM `ReleaseVersionArtifact` (per-asset, swallows) | **mishandled** (S-16); naming (S-21) |
| `media.item.asset-assigned` | ✓ | **✗ (DI-registered, not bound to bus)** | ✓ | AM `ApplyAssetAssignmentCommand` — dead | **missing-sub** → DLQ (S-04) |
| `media.profile.published` | ✓ | ✓ | ✓ | AM fan-out + Catalog conformance fan-out (swallows, unbounded) | ok / mishandled (S-15) |
| `media.profile.deprecated` | ✓ | ✓ | ✓ | AM fan-out | ok |
| `media.collection.{created,renamed,tagged,visibility-changed}`, `media.folder.*`, `media.item.{assigned-to-folder,deleted,rejected}` | ✓ | via projectors | ✗ (not in cross-module filter) | Search/Discovery + read-model projectors (domain-event path) | informational |

### Metadata / ChangeRequests / Registration (producers — all raised in Api)
| `[MessageType]` | A | B | C | Real consumer(s) | Status |
|---|---|---|---|---|---|
| `media.recordtype.published` | ✓ | ✓ (bridged in EC) | **✗ not in filter** | Catalog `RecordTypePublishedEventHandler` (+ projector not registered in-host) | **missing-sub** (S-01) + in-host gap (S-17) |
| `media.recordtype.deprecated` | ✓ | ✓ | **✗ not in filter** | Catalog `RecordTypeDeprecatedEventHandler` | **missing-sub** (S-01) |
| `media.changerequest.created` | ✓ | — | ✓ (in filter, no handler) | external Notifications only | dangling / no-op (S-07) |
| `media.registration.initiated` | ✓ | ✓ | ✓ | Catalog `AddRegistrationRefCommand` (Result-checked ✓) | ok |
| `media.registration.cancelled` | ✓ | ✓ | ✓ | Catalog `RemoveRegistrationRefCommand` (checked ✓) | ok |
| `media.registration.rejected` | ✓ | ✓ | ✓ | Catalog `RemoveRegistrationRefCommand` (checked ✓) | ok |
| `media.registration.{confirmed,submitted,resubmitted}` | ✓ | — | ✗ (not in filter) | external Compliance / unimplemented submission saga | informational / deferred |

**Ordering sensitivity (applies broadly):** all queues are standard (not FIFO); per-aggregate order is guaranteed only at the event store by `AggregateVersion`. Reference projectors that guard on `ProjectedVersion`/`EventVersion` tolerate reorder; the `AssetIngestionSaga` tolerates it via status gates; the non-idempotent handlers (upload-confirmed, per-asset promote/release) do not.

---

## 3. Consumer map

| Host / queue | Subscribed `EventType`s (via filter) | Command/projection → target module | Result-checked? | DLQ? | Notes |
|---|---|---|---|---|---|
| **ProcessingWorker** / `media-processing` | `media.asset.upload-confirmed` | `CreateProcessingJobCommand` + `ValidateAsync` → Processing | **No** | Yes | Non-idempotent (`ProcessingJobId.New()` each run); also handled by EventConsumers → **duplicate jobs** (S-13). Cannot publish `ProcessingJobCreated/ScanResult` (S-08/S-09). |
| **EventConsumers** / `media-cross-module-events` | 24-value allowlist (see §2) | many cross-module commands + reference projectors | **Mostly No** (Registration handlers Yes) | Yes (7-day) | Hosts the saga handlers for `processing-completed/failed` **without** the saga repo → DLQ-loop (S-12). Cannot publish the async Asset events it raises (S-08). Tenant from body (S-14). |
| **SagaOrchestrator** / `media-sagas` | `processingjob.created`, `asset.validation-passed`, `asset.processing-completed`, `asset.processing-failed`, `asset.processing-timeout-recovered` | `AssetIngestionSaga` → dispatches Start/Bypass/Fail `ProcessingJobCommand` (Processing) and `FailAssetProcessing` (AssetMgmt) | saga-internal | Yes | Saga is correctly coded but its triggers are never published (S-22); it dispatches into AssetMgmt cross-BC. Cannot publish `ProcessingJobStarted/Bypassed/Failed` (S-08/S-10). |
| **Projectors.ReadModel** / `media-projector` | **none (firehose — all domain events)** | DynamoDB read models | n/a | Yes | Unfiltered by design; confirm it is meant to see every domain-event type. |
| **Projectors.Search** / `media-projector-search` | none; **subscription only when `deploySearch=true`** | OpenSearch | n/a | Yes | Orphan queue in every current environment (no producer subscription, no Lambda). |
| **TimeoutScanner** | EventBridge rate(5 min) | `FailAssetProcessing` on timeout → AssetMgmt | n/a | n/a | Scans **only** `SagaType=ASSET_INGESTION`; no coverage for any other saga. |
| **SagaOrchestrator.DocumentSigning** | — | — | — | — | No queue / no ESM; handlers stubbed (`NotImplementedException` / HTTP 501). |

---

## 4. Cross-module flow analysis

Each flow is traced end-to-end; the ✗ marks the first hop that breaks and the wrong end state a real request reaches.

### (a) Asset ingestion — **broken at the first async hop**
```
Api: InitiateUpload → AssetUploadInitiated ─► SNS ok
Api: ConfirmUpload  → AssetUploadConfirmed  ─► SNS ok  ─► media-processing ─► ProcessingWorker
ProcessingWorker: CreateProcessingJob → ProcessingJobCreated ──✗── cannot publish (no IMessageBus in host; no publisher route)
                                                                    └─► AssetIngestionSaga START never fires
```
Wrong end state: asset sits in `Validating` forever; no ProcessingJob event ever reaches the saga; no timeout fires (the saga was never created). Root: S-08 + S-09 + S-22. Aggravation: the same `upload-confirmed` is also delivered to EventConsumers, which mints a **second** ProcessingJob (S-13).

### (b) Asset ⇄ Catalog lifecycle — **partially broken**
```
Catalog: MediaItemCreated/Approved/Archived ─► SNS ok ─► filter ok ─► AM capability refs + Reg refs   ✓
Catalog: MediaItemApproved ─► AM PromoteAssetToVersionArtifact (per-asset) ──✗ Result swallowed / exception swallowed per asset
Catalog: media.item.asset-assigned ─► SNS ok ─► filter ok ──✗ handler DI-only, not bridged ─► DLQ (S12 tag+reprocess never runs)
Asset:   media.asset.archived ─► SNS ok ──✗ EventType not in filter ─► Catalog AssetStateReference never updated
```
Wrong end state: approved assets silently not promoted on a transient fault; S12 process-on-assign never executes; Catalog's asset-state reference goes stale on archive. Root: S-04, S-02, S-15/S-16.

### (c) RecordType publish/deprecate → Catalog — **broken at the filter**
```
Metadata(Api): RecordTypePublished/Deprecated ─► media-integration-events ──✗ EventType absent from media-cross-module-events filter
                                                                                └─► never reaches EventConsumers
(even if delivered: RecordTypeVersionDetailIndexProjector is not registered in EventConsumers host — second break)
```
Wrong end state: MediaProfile's `RecordTypeVersionReference` never learns of new/deprecated record-type versions. Root: S-01 + S-17.

### (d) Registration → Catalog — **works**
```
Registration(Api): RegistrationInitiated ─► SNS ok ─► filter ok ─► Catalog AddRegistrationRef (Result-checked, logs) ✓
Terminal Cancelled/Rejected ─► RemoveRegistrationRef ✓   (active-registrations counter maintained)
```
Healthiest seam in the system. (Reverse direction — MediaItemCreated/Approved/Archived → Registration `IsPublished` — also live.)

### (e) Media-item review → change-request — **entirely broken**
```
Catalog(Api): MediaItemPublicationRequested → media.item.submitted-for-review ─► SNS ok ─► filter ok
   ──✗ ChangeRequests IIntegrationEventHandler never DI-registered ─► GetServices<> empty ─► message ACKed, no action
   ──✗ MediaItemReviewSaga does not exist (no class/state/handlers/registration)
```
Wrong end state: a publish that requires review is silently accepted with no ChangeRequest ever created; reviewer approve/reject has nothing to link to. Root: S-05 + S-23.

### (f) Collection archive fan-out — **runs, but destructive and non-idempotent**
```
Catalog(Api): CollectionArchived ─► SNS ok ─► filter ok ─► Catalog fan-out worker (tenant ✓)
   ──! worker HARD-archives every descendant Folder + MediaItem aggregate (spec says read-model-only / reversible)
   ──! re-delivery re-runs the full BFS archive (non-idempotent)
```
Wrong end state: an archive that the spec intends as a reversible accessibility flag instead irreversibly mutates every descendant aggregate; a redelivery repeats it. Root: S-26.

### (g) Media-profile publish → conformance — **runs, with swallowed failures**
```
Catalog(Api): MediaProfilePublished ─► SNS ok ─► filter ok ─► Catalog conformance fan-out
   ──! unbounded, uncheckpointed enumeration of pinned items; SaveAsync loop does not inspect Result
```
Wrong end state: on a large profile or a transient fault, conformance is partially updated and the message ACKs as success. Root: S-15 (+ scale). Functionally the seam delivers.

### (h) Document signing — **not implemented**
```
Catalog(Api): SigningSessionInitiated ─► (intended media-signing queue) ──✗ no queue, no saga, no ESM
SagaOrchestrator.DocumentSigning handlers: throw NotImplementedException / return 501
```
Wrong end state: a stuck signing session is unrecoverable (no saga, no 72-h timeout, no compensation). Root: S-24 (deferred).

---

## 5. Findings

IDs are stable (`S-nn`). Severity carries a risk type: data-integrity / reliability / security / destructive.

### Class 1 — Missing subscription

**S-01 · RecordType→Catalog events are dropped by the SNS filter · High (data-integrity)**
A: `media.recordtype.published/deprecated` are mapped and published from the Api host (`RecordTypeDomainEventMapper.cs:17,23`; `MetadataIntegrationEventPublishers.cs:10-11`). B: Catalog bridges both in EventConsumers (`ConsumerRegistrations.cs:96-97` / DI `Catalog.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:146`). C: **neither `EventType` is in the `media-cross-module-events` allowlist** (`sqs-queues.construct.ts:192-224` — the list carries `media.profile.published/deprecated`, mislabeled `// Metadata (RecordType)`, but no `media.recordtype.*`). Failure: SNS silently drops the events; MediaProfile's record-type version reference is never maintained. Fix: add `media.recordtype.published` and `media.recordtype.deprecated` to the filter policy (and see S-17).

**S-02 · asset.archived is dropped by the SNS filter · High (data-integrity)**
A: published from Api (`AssetIntegrationEventMapper.cs:45`; `AssetManagementIntegrationEventPublishers.cs:10`). B: Catalog `AssetArchivedEventHandler` bridged in EC (`ConsumerRegistrations.cs:75`). C: `media.asset.archived` is **not** in the filter allowlist. Failure: Catalog `AssetStateReference` never reflects an archived asset. Fix: add to filter.

**S-03 · asset.infection-detected is both unpublishable and filtered out · High (data-integrity/reliability)**
A: raised by an AssetManagement consumer running in **EventConsumers**, which registers no publisher (S-08). B: Catalog `AssetInfectionDetectedEventHandler` bridged in EC (`ConsumerRegistrations.cs:77`). C: `media.asset.infection-detected` not in filter. Double break. Fix: resolve S-08, then add to filter.

**S-04 · S12 `media.item.asset-assigned` handler is registered in DI but never bound to the bus · High (reliability)**
A: published from Api (`MediaItemDomainEventMapper.cs:31`). B: `AssetAssignedToRoleEventHandler` is DI-registered (`AssetManagement.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:107`) but there is **no** `bus.AddMessageHandler<…AssetAssignedToRole…>` in `AddIntegrationEventMessageHandlers` (`ConsumerRegistrations.cs:67-130`). C: the `EventType` **is** in the filter, so SNS delivers it → AWS.Messaging finds no handler → unroutable → DLQ. Failure: `ApplyAssetAssignmentCommand` (S3 tier-policy tag + process-on-assign, added 2026-07-17) never runs. Fix: add the bus handler binding.

**S-05 · ChangeRequests `submitted-for-review` consumer is never registered · High (data-integrity)**
A: published from Api (`MediaItemDomainEventMapper.cs:102`). B: bridged on the bus (`ConsumerRegistrations.cs:87`) but `AddChangeRequestWriteModel` registers only command handlers + repo (`ChangeRequests.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:23-47`) — no `IIntegrationEventHandler`. `GetServices<>` returns empty → the bridge returns `Success()` → message ACKed, no action. `MediaItemPublicationRequestedEventHandler` is dead code. C: filter passes. Failure: review-gated publishes create no ChangeRequest. Fix: register the handler (and reconcile with S-23).

**S-06 · `asset.validation-passed` is a stray value in the cross-module filter · Medium (reliability)**
It belongs only to `media-sagas`, but it is also present in the `media-cross-module-events` allowlist while no EC handler consumes it → delivered to EventConsumers and DLQ'd as unroutable. Fix: remove from the cross-module filter.

**S-07 · `media.changerequest.created` is a dangling subscription · Low (reliability)**
In the cross-module filter with no in-MM consumer (intended consumer is external Notifications). Harmless no-op today, but it means the queue receives traffic it can't act on. Fix: leave for the external consumer or drop from the intra-BC filter.

### Class 2 — Event not emitted

**S-08 · Integration-event publishing is unwired in every async host · Critical (reliability, data-integrity)**
`ProcessingWorker`, `EventConsumers`, and `SagaOrchestrator` build only the AWS.Messaging consumer bus (`*/Function.cs`) and never register the platform `IMessageBus` (registered only by `AddMessaging()`/`AddInProcessMessageBus()` in `Api/Startup.cs`). Yet all three call `AddProcessingWriteModel()` → `UseIntegrationEventPublishing()` → `IntegrationEventPublishingMiddleware`, whose ctor hard-depends on `IMessageBus`. Any command dispatched in those hosts that raises a domain event therefore cannot publish. Concretely this kills `ProcessingJobCreated/ScanResult/Started/Completed/Failed/Bypassed` and the async Asset events `validation-passed/processing-completed/processing-failed/processing-timeout-recovered/infection-detected`. Evidence corroborated independently by the producer sweep (no `AddSNSPublisher` in worker hosts) and the saga sweep (no `IMessageBus` in worker hosts). Fix: register the platform message bus + module SNS publishers in every host that raises integration events (or move publication to a shared relay). **Ship with S-09/S-10.**

**S-09 · Three Processing events have no publisher registration in ANY host · High (reliability)**
`AddProcessingIntegrationEventPublishers` (`ProcessingIntegrationEventPublishers.cs:10-12`) registers only Completed/Failed/Started. `media.processingjob.created` (`ProcessingDomainEventMapper.cs:32`), `media.processingjob.scan-result` (`:58`), and `media.processingjob.bypassed` (`:21`) are mapped and actively consumed but never registered as SNS publishers anywhere — so even after S-08, they still won't publish. `processingjob.created` is the **saga start trigger**. Fix: add the three publisher registrations.

**S-10 · Processing started/completed/failed are registered only in the Api host · High (reliability)**
These are registered in `ProcessingIntegrationEventPublishers` but raised in `ProcessingWorker`/`SagaOrchestrator`. The registration is in the wrong host. Folds into the S-08 fix.

**S-11 · No live environment publishes cross-host over SNS · High (reliability/config)**
dev/qa run the Api host with `AddInProcessMessageBus()` (`ASPNETCORE_ENVIRONMENT=Development`), so integration events never leave the Api Lambda; prod/staging (which would use SNS) are deploy-disabled. Consequence: the async pipeline has never run end-to-end. Fix: enable an SNS-backed bus in a non-prod environment for integration testing, or add an in-cluster equivalent, before declaring the choreography functional.

### Class 3 — Mishandled event

**S-12 · `processing-completed`/`processing-failed` DLQ-loop in EventConsumers, taking the Catalog projections with them · Critical (reliability, data-integrity)**
`ConsumerRegistrations.cs:59` calls `AddProcessingIntegrationEventConsumers()`, which registers `AssetProcessingCompletedSagaHandler`/`AssetProcessingFailedSagaHandler` whose ctors require `AssetIngestionSaga` — but EventConsumers never calls `AddProcessingAssetIngestionSaga()`/`AddSagaTable()` (only `SagaOrchestrator/Function.cs` does). The bus routes these events (`ConsumerRegistrations.cs:78-79`); `IntegrationEventMessageHandler.cs:43` resolves `GetServices<IIntegrationEventHandler<…>>()`, which throws activating the saga handler → caught → `Failed()` → retry → DLQ. The legitimately co-registered Catalog handlers (`AssetProcessingCompletedEventHandler` projection, `AssetProcessingCompletedAutoSubmitHandler`, `AssetProcessingFailedEventHandler`) never run: the asset-state index is never updated on completion/failure and auto-submit never fires. Fix: do not invoke the saga-only `AddProcessingIntegrationEventConsumers()` in the EventConsumers host; keep saga handlers in `SagaOrchestrator` only.

**S-13 · `AssetUploadConfirmed` is consumed by two hosts and is non-idempotent · High (data-integrity)**
Delivered to `media-processing` (ProcessingWorker) **and** `media-cross-module-events` (EventConsumers, via `AddProcessingIntegrationEventConsumers`). The handler mints a fresh `ProcessingJobId.New()` per delivery (`AssetUploadConfirmedEventHandler.cs:33-38`) → two distinct ProcessingJobs, two virus scans, two `ProcessingJobCreated` events → two saga instances. Fix: single-host consumption + idempotent create keyed on `AssetId` (`GetByAssetIdAsync` short-circuit).

**S-14 · TenantId sourced from the event payload body, systemically · High (security)**
CLAUDE.md mandates tenant from the SNS message attribute / `IExecutionContext` — never the body. Nearly every consumer reads `e.TenantId` (e.g. `ProcessingJobCompletedEventHandler.cs:22`, `RegistrationInitiatedEventHandler.cs:28`, reference projectors keyed on `e.TenantId`). Only `CollectionArchivedEventHandler.cs:27` uses `executionContext.TenantId`. Per the multi-tenancy rule this is at least High. Practical cross-tenant risk is bounded today because the publisher stamps the body from a trusted context, but it removes the defense-in-depth the convention exists to provide and is fragile against any future re-publish/relay. Fix: build `SqsExecutionContext` from the message attribute and source tenant from it in every handler.

**S-15 · Command `Result<T,DomainError>` swallowed across AssetManagement/Catalog handlers · Medium (reliability)**
`ProcessingJobStarted/Completed/Failed/Bypassed/ScanResult` handlers and `AssetProcessingCompletedAutoSubmitHandler` return the dispatch `Task` without inspecting the result (e.g. `ProcessingJobCompletedEventHandler.cs:20`). A domain-rejected command produces a completed Task → message ACKs → the state transition is lost, indistinguishable from an idempotent no-op. Contrast the correct `RegistrationInitiatedEventHandler.cs:33-38`. Fix: inspect `result.IsSuccess`; on domain failure, log + decide ACK vs DLQ deliberately.

**S-16 · Per-item catch-and-swallow deletes transient faults · Medium (reliability)**
`MediaItemApprovedEventHandler.cs:36-51` and `MediaItemVersionPurgedEventHandler.cs:37-53` loop over assets with an inner try/catch that swallows all exceptions "to not fail the whole message." A transient DynamoDB throttle on one asset is logged and skipped; the message ACKs; the asset is never promoted/released and never redelivered. Fix: distinguish transient (rethrow → redeliver) from permanent, or track per-asset progress for safe redelivery.

**S-17 · RecordType reference projector not registered in the consuming host · Medium (data-integrity)**
Even if S-01's filter is fixed, `RecordTypePublished/DeprecatedEventHandler` dispatch to `IProjectionPipeline`, but `RecordTypeVersionDetailIndexProjector` is registered only in `AddCatalogWriteModelProjectors` (domain-event projector host), not in `AddCatalogIntegrationEventConsumers` (EventConsumers). So the integration-event dispatch has no in-host projector. Fix: register the projector in the EventConsumers composition.

**S-18 · Saga state store has no optimistic concurrency · High (data-integrity/reliability)**
`DynamoDbSagaRepository.SaveAsync` (`shared/Media.Shared.Infrastructure/Sagas/DynamoDbSagaRepository.cs:53-74`) is an unconditional `PutItem`; a `Version` attribute is written but never used in a condition expression. `LoadAsync` is `ConsistentRead=true` but load/save are separate with no version guard, so two concurrent deliveries (e.g. a duplicate `processing-completed` racing a real `processing-timeout-recovered`) can both read the same state and the second write clobbers the first. Status gates narrow but cannot close the window. Fix: conditional write on `Version` (or `attribute_not_exists`) with retry.

### Class 4 — Bad event design → wrong downstream action

**S-19 · `AssetUploadConfirmed` `[MessageType]` reused for initial confirm and S12 reprocessing · Medium (data-integrity)**
Both `AssetUploadConfirmed` and `AssetReprocessingRequested` map to `media.asset.upload-confirmed` (`AssetIntegrationEventMapper.cs:164,30`). A single filter matches both; consumers cannot distinguish origin from the routing key. Combined with S-13's dual-host delivery, reprocessing also re-triggers duplicate job creation. Fix: distinct `[MessageType]` for reprocessing, or an origin discriminator the consumer honours.

**S-20 · Document fast-exit publishes `processing-completed` · Medium (data-integrity)**
`ProcessingJobCompleted` is emitted for both real success and the bypass/timeout-recovery paths (`ProcessingDomainEventMapper.cs:82,104`); documents that skip rendition still surface as "processing completed," which downstream Billing/metering can mis-count. Fix: separate the bypass/fast-exit signal from genuine rendition completion.

**S-21 · `media.item.version.purged` routing string breaks the naming convention · Low (reliability)**
Uses a 4-segment dot form where every sibling uses a hyphen in a 3-segment name (`media.item.submitted-for-review`, `media.item.asset-assigned`). It works only because the filter value matches the literal string; any "normalisation" would silently break the seam. Fix: standardise to `media.item.version-purged` and update the filter in the same change.

### Class 5 — Invalid cross-module flow

**S-22 · AssetIngestionSaga is dead end-to-end in production · Critical (reliability)**
The saga itself is correctly implemented and registered (`SagaOrchestrator/SagaRegistrations.cs:33-37`), with idempotent creation, status-gated transitions, and a two-phase timeout. But its start trigger `media.processingjob.created` is never published (S-09), and every step trigger it consumes originates in a host that cannot publish (S-08). So the saga never starts and never advances; the timeout scanner has nothing to scan. Fix: S-08 + S-09 together; then integration-test the full chain per S-11.

**S-23 · Media-item review → change-request choreography is entirely absent · High (data-integrity) — Critical-in-effect**
Two independent breaks: (1) the `submitted-for-review` consumer is unregistered (S-05); (2) `MediaItemReviewSaga` does not exist as a class, state, handler, or registration anywhere in `src/` (the CLAUDE.md note "partial, missing closing handlers" understates it — nothing is implemented). A review-gated publish is silently accepted with no ChangeRequest and no review lifecycle. Fix: implement/register the review saga and the consumer as a pair, or explicitly gate the review-required publish path off until then.

**S-24 · DocumentSigning has no saga, timeout, or compensation · Medium (reliability) — deferred**
The `SagaOrchestrator.DocumentSigning` host is a stub (`SigningSessionInitiatedHandler.cs:40` throws; `SecuredSigningWebhookHandler.cs:40` returns 501); no queue/ESM; TimeoutScanner covers only `ASSET_INGESTION`. A stuck signing session is unrecoverable. Consistent with the documented deferral — flagged so it is feature-gated, not silently shipped.

**S-25 · Dual-write with silently-swallowed publish failures · High (reliability)**
Publication is a direct SNS publish after the event-store append (no outbox is wired, though the platform ships one). `MessageBus.PublishAsync` (`platform Messaging/…/MessageBus.cs:36-76`) wraps the publish in try/catch and only logs on failure, so a failed SNS publish does not fail the command — the event is durably stored but never published, with no retry or rollback. Fix: at minimum fail the command (or enqueue) on publish failure; strategically, wire the platform outbox relay (note: even the platform outbox enqueues in a separate write from the event append, so it narrows rather than eliminates the window unless a single `TransactWriteItems` spans events + outbox).

**S-26 · Collection archive fan-out hard-archives descendants irreversibly and non-idempotently · High (destructive)**
The fan-out worker propagates archival by mutating every descendant Folder/MediaItem aggregate rather than flipping a read-model accessibility flag (spec intends reversible, read-model-only), and re-delivery re-runs the full BFS with no checkpoint. An accidental or duplicated archive is destructive and not cleanly reversible. Fix: make the propagation a read-model projection (reversible) and checkpoint/idempotent per page.

---

## 6. Sequenced recommendations

Landing order; **paired** items must ship in the same change or the seam stays broken.

1. **Unblock publishing (must ship together): S-08 + S-09 + S-10.** Register the platform `IMessageBus` and *all* module SNS publishers (including `processingjob.created/scan-result/bypassed`) in every host that raises integration events. Nothing downstream of Api works until this lands. Prerequisite for S-22.
2. **Stand up a real transport test environment: S-11.** Enable an SNS-backed bus in dev/qa (or a dedicated integration environment) so the chain can be exercised before prod is re-enabled. Without this, 1 and 3 cannot be verified.
3. **Fix the EventConsumers mis-wiring: S-12 + S-13** (same root — `AddProcessingIntegrationEventConsumers` in the wrong host). Remove saga handlers from EventConsumers; make ProcessingJob creation single-host and idempotent.
4. **Close the filter/bridge gaps (each pairs a code binding with a CDK filter edit):**
   - S-01 (+ S-17): add `recordtype.published/deprecated` to the filter **and** register the projector in-host.
   - S-02, S-03: add `asset.archived`, `asset.infection-detected` to the filter (S-03 also needs 1).
   - S-04: bind the `asset-assigned` handler to the bus.
   - S-05 (+ S-23): register the ChangeRequests consumer **and** land the review saga, or gate the review path.
   - S-06: remove the stray `asset.validation-passed` from the cross-module filter.
5. **Correctness/reliability hardening: S-14** (tenant from attribute), **S-15/S-16** (Result + transient handling), **S-18** (saga optimistic concurrency), **S-25** (publish-failure handling / outbox).
6. **Design cleanups: S-19, S-20, S-21** (routing-string discipline), **S-26** (make archive fan-out reversible + idempotent).
7. **Deferred, feature-gate explicitly: S-24** (DocumentSigning), plus the unimplemented registration-submission saga path.

Prerequisite chain: **1 → 2 → 3 → 4**; 5/6 can proceed in parallel once 1 lands. Do not re-enable prod/staging deploys until 1–4 are verified in a live SNS environment.

---

## 7. Appendix — diff against the existing reviews

Read only after the above was formed. Sources: `docs/reviews/cross-module-integration-review.md` (primary) and ten per-module/mechanical reviews.

### 7a. Convergence (this sweep independently reproduced their headline seam findings)
The existing `cross-module-integration-review.md` is thorough and my independent A/B/C sweep lands on the same core conclusions — strong mutual corroboration. Direct correspondences:

| This sweep | Existing review |
|---|---|
| S-08 async hosts can't publish | XM-C1 |
| S-09 three processing events unregistered | XM-C2 |
| S-01/S-02/S-03 filter omissions | XM-C3 |
| S-12 processing-completed/failed DLQ-loop + S-13 dup jobs | XM-C4 (+ PJ-H1) |
| S-05 submitted-for-review / changerequest.created dropped | XM-C5 |
| S-04 asset-assigned dead handler | XM-C6 |
| S-24 DocumentSigning non-functional | XM-C7 |
| S-06 validation-passed stray filter value | XM-H2 |
| S-15 swallowed Result | XM-H1 |
| S-14 tenant-from-body | XM-H8 |
| S-18 saga no optimistic concurrency | XM-H9 |
| S-25 dual-write / no outbox | XM-DF1 / XM-G1 |
| S-22 saga dead in prod | implied by XM-C1 + XM-C2 (they classify the saga "implemented but inert") |
| S-23 review saga absent | consistent with ChangeRequests CR-S1/S2 + MediaItem MI-Life2 |
| S-26 collection archive hard-mutates descendants | COL-C2 / COL-FC1 |

### 7b. Findings this sweep adds or sharpens (their comparative thin spots)
- **S-17 (RecordType projector not registered in the consuming host)** — the existing review caught the SNS filter omission (XM-C3) but frames RecordType→Catalog as fixed by the filter edit alone. This sweep finds a **second, independent** break: even delivered, `RecordTypeVersionDetailIndexProjector` isn't registered in EventConsumers, so the filter fix alone would not restore the seam. Recommend verifying against `AddCatalogIntegrationEventConsumers`.
- **S-10 (started/completed/failed registered in the wrong host)** — a distinct registration-locus defect separate from XM-C1's "no bus" and XM-C2's "no route"; worth calling out because it survives a naive "add a bus to the worker" fix if the publisher list isn't also present there.
- **Transport hygiene not emphasised in the primary review:** the two **unfiltered firehose** subscriptions on `media-domain-events` (`media-projector`, `media-projector-search`) and the **orphan `media-projector-search` queue** in every non-search environment (`deploySearch=false`). Low severity, but they belong in the topology picture.
- **Verified-clean non-findings (recorded to prevent future false "fixes"):** (i) the `media-sagas` filter value `media.processingjob.created` **does** match the producer `[MessageType]` (`ProcessingJobCreatedIntegrationEvent.cs:16`) — it is *not* a naming mismatch; the defect is that the event is never *published* (S-09), not mis-routed. (ii) `media.item.version.purged`'s dot-form matches its filter value literally, so it works today despite the convention break (S-21).

### 7c. Their findings this sweep did NOT independently reproduce (and why)
- **Intra-module aggregate / authz / read-model findings** — e.g. XM-adjacent per-module items like missing ownership authorization (A-C2, COL-C1, MI-C1, MP-C1, RG-C1, RT-H1), projector copy-paste bugs (PJ-C1 "failed job reported Succeeded", RT-P1/P2), `DeleteAsset` S3-before-guard (A-C1). These are **out of this sweep's cross-module scope**; I neither confirm nor deny them here. They look serious and should not be discounted because they are absent from this report.
- **XM-H3/H4/H5/H6/H7 reference-projector watermark/ordering bugs** — partially in scope (shared write-side reference models). This sweep's consumer pass observed several reference projectors (`AssetStateReferenceProjector`, `MediaItemCapabilityReferenceProjector`, `MediaItemRegistrationIndexProjector`) as version/`ProjectedVersion`-guarded, whereas XM-H4 claims `AssetStateReferenceProjector` is an unconditional upsert and the capability projector mixes watermark domains (XM-H3). **This is a genuine contradiction** — see 7d. I did not read these projectors line-by-line in this pass, so I mark my "looks guarded" read **provisional** and defer to a targeted re-check.
- **XM-M4 (TimeoutScanner `remainingTime` snapshot), XM-M7 (`ORGANIZATION_ID` placeholder → ECR 403), XM-M3/S-20 mis-billing detail** — plausible and consistent with what I saw, but I did not independently verify each to `file:line` in this pass; treat as theirs, unconfirmed by me.

### 7d. Contradiction to resolve
**Reference-projector idempotency.** Existing XM-H3/H4 assert the AssetManagement capability projector mixes version domains (archived-before-created wedges the item as not-archived) and that `AssetStateReferenceProjector`/`MediaItemVersionAssetReferenceProjector` are unconditional/last-write-wins. This sweep's consumer pass read several of those projectors as version-guarded. Both cannot be fully true. Because a resurrection/last-write-wins bug on a write-side capability reference is high-impact (it gates uploads to archived items), this specific contradiction should be closed by a line-by-line read of `MediaItemCapabilityReferenceProjector`, `AssetStateReferenceProjector`, and `MediaItemVersionAssetReferenceProjector` before either claim is trusted. My read is the provisional one here.

---

*Prepared as an independent second-opinion sweep. All `file:line` references are to the state of the repos on 2026-07-19. Where a claim could not be confirmed from all three sides it is marked provisional above.*
