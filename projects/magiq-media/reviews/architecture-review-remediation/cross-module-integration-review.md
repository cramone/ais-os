# Cross-Module Integration Architecture Review — magiq-media

> **Scope (bounded context):** the whole `magiq-media` bounded context as an event-driven system — the *seams between* the seven modules (`AssetManagement`, `Catalog` [Collection/Folder/MediaItem/MediaProfile], `ChangeRequests`, `Metadata`, `Processing`, `Registration`, `DocumentSigning`). Integration events, cross-module command dispatch, sagas/process managers, write-side reference/ACL models, and the SNS/SQS/DLQ topology. Intra-aggregate internals are out of scope (covered by the per-module reviews).
>
> **Reviewer role:** Principal Domain Architect / DDD, CQRS-ES, EDA-&-Saga, and API architecture.
>
> **Date:** 2026-07-19
>
> **Inputs reviewed (globs):**
> - Spec: `docs/spec/architecture/{system-architecture,bounded-context,service-boundaries,domain-model}.md`, `docs/spec/shared/system-spec.md`, `docs/spec/shared/{api-conventions,error-catalog,security-scenarios,bulk-operations,media-types}.md`, `docs/spec/contexts/*/context-overview.md`, `docs/spec/contexts/*/business-scenarios.md`, per-aggregate `*.write-model.md` event tables.
> - ADRs: `docs/adrs/ADR-002-sqs-event-bus.md`, `ADR-005-integration-event-publisher.md`, `ADR-006`, `ADR-007`, `ADR-008`, `persistence-and-eventing.md`, `asset-storage-and-processing.md`.
> - Code (publish): `src/hosts/Api/Infrastructure/Publishers/**`, each module's `*.Contracts/Events/**`, `*IntegrationEventMapper*`.
> - Code (consume): each module's `IntegrationEvents/Consuming/**`, `*ReferenceProjector`.
> - Code (host wiring): `src/hosts/EventConsumers/{ConsumerRegistrations,IntegrationEventMessageHandler,Function}.cs`, `DEPLOYMENT.md`, `src/hosts/Api/Startup.cs`.
> - Code (sagas): `src/hosts/SagaOrchestrator/**`, `src/hosts/SagaOrchestrator.DocumentSigning/**`, `src/hosts/TimeoutScanner/**`, `src/shared/Media.Shared.Infrastructure/{Sagas,Messaging}/**`.
> - Platform SDK (publish mechanism): `aspnetcore-platform/src/platform/Domain/Magiq.Platform.WriteModel.Application/**`, `Magiq.Platform.Messaging/**`.
> - Deploy topology (read-only): `cdk-magiq-media/lib/**` (SNS topics, SQS queues, subscriptions, filter policies, DLQs, event-source mappings).
>
> **Method:** Re-derived the integration surface from code first-hand: **8 async/API hosts** read (Api, EventConsumers, ProcessingWorker, Projectors.ReadModel, Projectors.Search, SagaOrchestrator, SagaOrchestrator.DocumentSigning, TimeoutScanner); **2 saga definitions** (`AssetIngestionSaga` implemented; `DocumentSigningSaga`/`MediaItemReviewSaga` intended); **6 module consumer-registration surfaces** + the central `ConsumerRegistrations`; **~30 integration-event contracts**; **4 CDK topology/stack files** (`magiq-media-stack.ts`, `sns-topics.construct.ts`, `sqs-queues.construct.ts`, `magiq-media-devops-stack.ts`); the platform integration-event publishing pipeline; and **8 prior per-module reviews** cross-checked. Every seam was verified from *both* sides (publisher contract + consumer registration + CDK subscription/filter).

---

## 1. System Integration Summary

magiq-media is an event-sourced, CQRS bounded context deployed as a fan of AWS Lambda hosts around **two SNS topics** and **five MM-owned SQS queues**:

- **`media-domain-events`** — internal raw domain events; fans out to `media-projector` (DynamoDB read models) and `media-projector-search` (OpenSearch, deferred behind `deploySearch`).
- **`media-integration-events`** — the published "language" (`media.*`) events; fans out to `media-processing` (ProcessingWorker), `media-cross-module-events` (EventConsumers — the intra-BC reference/command fan-in), and `media-sagas` (SagaOrchestrator). External BCs (Notifications, Search, Billing, Compliance) own their own queues off the same topic.

The intended choreography is a classic ingestion pipeline (`upload-confirmed → ProcessingJob → scan-result → validation-passed → StartProcessingJob/Bypass → processing-completed`) coordinated by `AssetIngestionSaga`, plus lifecycle ripples (asset ↔ catalog, record-type → catalog, registration → catalog, media-item review → change-request, collection archive fan-out) and a deferred document-signing slice.

**Production-readiness verdict: NOT production-ready.** The integration surface has a *foundational* defect that renders the entire asynchronous choreography inoperative in production, compounded by a cluster of subscription/filter-policy mismatches that would silently break or DLQ specific flows even if the foundational defect were fixed. The dominant themes are:

1. **The async pipeline does not run in production at all** — worker/consumer/saga/timeout hosts never register the platform `IMessageBus`, so the first command they dispatch throws inside the integration-event publishing middleware (`XM-C1`). This is masked in dev/qa/staging because CDK forces `ASPNETCORE_ENVIRONMENT=Development`, where the API host runs the *entire* pipeline in-process.
2. **The CDK SNS filter policies and the code's consumer bridge are out of sync in both directions** — several events are consumed in code but filtered out at SNS (`recordtype.*`, `asset.archived`, `asset.infection-detected`), and several are allowed through the filter but have no consumer bridge (`validation-passed`, `item.asset-assigned`) → silent loss or perpetual DLQ (`XM-C3`, `XM-C6`, `XM-H2`).
3. **Silent-drop and always-DLQ consumers** — bridged events with no registered handler are ACKed and dropped (`item.submitted-for-review`, `changerequest.created` → `XM-C5`); the Processing saga handler is mis-registered without its repository in EventConsumers → permanent DLQ (`XM-C4`); no consumer inspects a command `Result`, so domain rejections are swallowed (`XM-H1`).
4. **Weak distributed-systems hygiene at the seams** — no transactional outbox (dual-write), saga state saved without optimistic concurrency, reference projectors with inconsistent/absent version-guards, TenantId sourced from the payload body rather than the SNS attribute, and no completion driver for the rendition pipeline.
5. **Deferred slices are wired half-way** — DocumentSigning has hosts, queues (partially), and handlers that `throw NotImplementedException`/return 501, but no aggregate, no events, no registered saga, and no timeout scanner; the MediaItem review saga is likewise unregistered.

---

## 2. Integration Event Catalogue

All integration events inherit `IntegrationEvent`, carry a `long EventVersion` payload field, and are published to **`media-integration-events`**. `[MessageType]` is the routing string stamped as the SNS `EventType` attribute (used by every filter policy). "Publisher (SNS route)" = whether an `AddSNSPublisher<T>` registration exists (API host only). "Bridged→EventConsumers" = whether `ConsumerRegistrations.AddIntegrationEventMessageHandlers` registers an AWS.Messaging handler.

| Event `[MessageType]` | Publisher module | Ver | SNS route registered? | Real consumer(s) | Ordering | Idempotency | Notes |
|---|---|---|---|---|---|---|---|
| `media.asset.upload-initiated` | AssetManagement | v0 | ✅ Api | Catalog `AssetUploadInitiatedEventHandler` (AssetStateRef); Processing (no-op) | tolerant | projector version (unconditional upsert ⚠️) | — |
| `media.asset.upload-confirmed` | AssetManagement | v0 | ✅ Api | ProcessingWorker `AssetUploadConfirmedEventHandler` (creates ProcessingJob) | tolerant | **none** — new JobId per delivery (PJ-H1) | Also delivered to EventConsumers → duplicate job (`XM-C4`) |
| `media.asset.validation-passed` | AssetManagement | v0 | ✅ Api | SagaOrchestrator (`AssetIngestionSaga` trigger) | **saga-critical** | saga status guard | In cross-module filter but **not bridged** → DLQ (`XM-H2`) |
| `media.asset.processing-completed` | AssetManagement | v0 | ✅ Api | Catalog (`AssetProcessingCompleted` + `AutoSubmit`); SagaOrchestrator | tolerant | aggregate/status guard | Fanned to 2 queues; DLQs in EventConsumers (`XM-C4`); `Status` enum mismatch (`XM-M1`) |
| `media.asset.processing-failed` | AssetManagement | v0 | ✅ Api | Catalog (`AssetProcessingFailed`); SagaOrchestrator | tolerant | guard | DLQs in EventConsumers (`XM-C4`) |
| `media.asset.processing-timeout-recovered` | AssetManagement | v0 | ✅ Api | SagaOrchestrator (`Failed→Completed`) | ordering-sensitive | guard | correction event (S6) |
| `media.asset.archived` | AssetManagement | v0 | ✅ Api | Catalog `AssetArchivedEventHandler` | tolerant | version-guarded upsert | **Not in cross-module filter** → never delivered (`XM-C3`) |
| `media.asset.deleted` | AssetManagement | v0 | ✅ Api | Catalog `AssetDeletedEventHandler` | ordering-sensitive | unconditional delete ⚠️ | resurrection risk on reorder (`XM-H4`) |
| `media.asset.infection-detected` | AssetManagement | v0 | ✅ Api | Catalog `AssetInfectionDetectedEventHandler` | tolerant | version-guarded | **Not in cross-module filter** → never delivered (`XM-C3`) |
| `media.asset.attached` | AssetManagement | v0 | ✅ Api | *(none — intentional)* | — | — | notification/Search only |
| `media.item.created` | Catalog | v0 | ✅ Api | AssetMgmt `MediaItemCapabilityRef`; Registration `MediaItemRegistrationContext` | tolerant | projector version | archived-before-created hazard (`XM-H3`) |
| `media.item.approved` | Catalog | v0 | ✅ Api | AssetMgmt `PromoteAssetToVersionArtifact`; Registration | tolerant | per-asset try/skip | drives version-artifact promotion |
| `media.item.archived` | Catalog | v0 | ✅ Api | AssetMgmt `MediaItemCapabilityRef`; Registration | ordering-sensitive | mixed watermark (`XM-H3`) | — |
| `media.item.submitted-for-review` | Catalog (from `MediaItemPublicationRequested`) | v0 | ✅ Api | *(bridged, **no handler registered**)* | — | — | **silent drop** (`XM-C5`) |
| `media.item.version.purged` | Catalog | v0 | ✅ Api | AssetMgmt `ReleaseVersionArtifact` | ordering-sensitive | last-write-wins ref (`XM-H4`) | Catalog version-asset ref never populated (`XM-H6`) |
| `media.item.asset-assigned` | Catalog | v0 | ✅ Api | AssetMgmt handler **DI-registered, not bridged** | tolerant | aggregate guard | S12 flow dead; DLQ (`XM-C6`); absent from spec catalogue |
| `media.item.assigned-to-folder` | Catalog | v0 | ✅ Api | *(none)* | — | — | published-but-unconsumed |
| `media.item.deleted` / `media.item.rejected` | Catalog | v0 | ✅ Api | *(none)* | — | — | published-but-unconsumed |
| `media.collection.archived` | Catalog | v0 | ✅ Api | Catalog `CollectionArchivedEventHandler` (fan-out) | tolerant | fan-out worker | only Collection event consumed intra-BC |
| `media.collection.{created,renamed,tagged,visibility-changed}` | Catalog | v0 | ✅ Api | *(external/Search)* | — | — | intentionally unconsumed intra-BC |
| `media.folder.{created,renamed,moved,archived}` | Catalog | v0 | ✅ Api | *(external/Search)* | — | — | intentionally unconsumed intra-BC |
| `media.profile.published` | Catalog | v0 | ✅ Api | AssetMgmt `AssetProfileDefaultRef`; Catalog `ConformanceFanout` | tolerant | atomic set-add w/ version | lossy summary (MP-FP1) |
| `media.profile.deprecated` | Catalog | v0 | ✅ Api | AssetMgmt `AssetProfileDefaultRef` | tolerant | atomic set-remove | — |
| `media.recordtype.published` | Metadata | v0 | ✅ Api | Catalog `RecordTypePublishedEventHandler` | tolerant | projector | **Not in cross-module filter** → never delivered (`XM-C3`) |
| `media.recordtype.deprecated` | Metadata | v0 | ✅ Api | Catalog `RecordTypeDeprecatedEventHandler` | tolerant | projector | **Not in cross-module filter** (`XM-C3`); version = AggregateVersion (RT-I1) |
| `media.changerequest.created` | ChangeRequests | v0 | ✅ Api | *(bridged, **no handler anywhere**)* | — | — | **silent drop** (`XM-C5`) |
| `media.processingjob.created` | Processing | v0 | ❌ **no route** | SagaOrchestrator (`AssetIngestionSaga` trigger) | **saga-critical** | saga existence guard | **never published** (`XM-C2`) |
| `media.processingjob.scan-result` | Processing | v0 | ❌ **no route** | AssetMgmt `RecordValidationResult` | ingestion-critical | aggregate guard | **never published** (`XM-C2`) |
| `media.processingjob.bypassed` | Processing | v0 | ❌ **no route** | AssetMgmt `ActivateDocumentAsset` | tolerant | aggregate guard | **never published** (`XM-C2`) |
| `media.processingjob.started` | Processing | v0 | ✅ Api | AssetMgmt `StartAssetProcessing` | tolerant | aggregate guard | — |
| `media.processingjob.completed` | Processing | v0 | ✅ Api | AssetMgmt `CompleteAssetProcessing` | tolerant | aggregate guard | metadata fields dropped (F-C5) |
| `media.processingjob.failed` | Processing | v0 | ✅ Api | AssetMgmt `FailAssetProcessing` | tolerant | aggregate guard | — |
| `media.registration.initiated` | Registration | v0 | ✅ Api | Catalog `AddRegistrationRef` | tolerant | remove idempotent | — |
| `media.registration.cancelled` / `.rejected` | Registration | v0 | ✅ Api | Catalog `RemoveRegistrationRef` | tolerant | idempotent | — |
| `media.registration.confirmed` | Registration | v0 | ✅ Api | *(none — spec expects Compliance)* | — | — | published-but-unconsumed |
| `media.registration.submitted` / `.resubmitted` | Registration | v0 | ✅ Api | *(none)* | — | — | published-but-unconsumed |

> **Publisher caveat (`XM-C1`):** the "✅ Api" routes only fire when the event is published *from the API host in Production*. Events whose *only* producer is a worker host (`processingjob.*`, `asset.validation-passed` from the scan hop, the AssetManagement events emitted by consumer-dispatched commands) never publish in production because those hosts have no platform `IMessageBus`. See §8 / `XM-C1`.

---

## 3. Consumer Map

Bridge = `ConsumerRegistrations.AddIntegrationEventMessageHandlers` (`hosts/EventConsumers/ConsumerRegistrations.cs`) unless the "Host" column says otherwise. DLQ = every queue has one (`maxReceiveCount=3`, depth≥1 alarm).

| Consumer host / queue | Subscribed events (SNS filter) | Command / projection dispatched → module | Result-checked? | DLQ | Notes |
|---|---|---|---|---|---|
| **ProcessingWorker** / `media-processing` | `media.asset.upload-confirmed` only | `CreateProcessingJobCommand` + validation → Processing | No | ✅ | new JobId per delivery (no dedup) |
| **SagaOrchestrator** / `media-sagas` | `processingjob.created`, `asset.validation-passed`, `asset.processing-completed`, `asset.processing-failed`, `asset.processing-timeout-recovered` | `AssetIngestionSaga` → `Start`/`Bypass`/`FailProcessingJob` | No (`catch/log`) | ✅ | filter == code ✔; but trigger never published (`XM-C2`) |
| **EventConsumers** / `media-cross-module-events` | (see filter list §6) | AssetMgmt + Catalog + Registration consumers (below) | **No** | ✅ | filter ⇄ bridge mismatches (`XM-C3/C6/H2`) |
| ├ AssetMgmt consumers | `item.created/approved/archived/version.purged/asset-assigned`, `profile.published/deprecated`, `processingjob.bypassed/started/completed/failed/scan-result` | Asset commands + capability/profile-default refs | No | ✅ | TenantId from body (`XM-H8`); `asset-assigned` not bridged (`XM-C6`) |
| ├ Catalog consumers | `asset.archived/deleted/infection-detected/processing-completed/processing-failed/upload-initiated`, `collection.archived`, `registration.initiated/cancelled/rejected`, `recordtype.published/deprecated`, `profile.published` | `AddRegistrationRef`, `UpdateConformance`, `PublishMediaItem`, AssetStateRef, fan-out | No/ACK | ✅ | `archived`/`infection`/`recordtype.*` filtered out (`XM-C3`) |
| ├ Registration consumers | `item.created/approved/archived` | `MediaItemReference` projection | n/a | ✅ | TenantId from body |
| ├ Processing consumers (mis-hosted) | (co-registered via `AddProcessingIntegrationEventConsumers`) | `AssetIngestionSaga`, `AssetUploadConfirmed` | — | ✅ | **DLQ / duplicate** (`XM-C4`) |
| **SagaOrchestrator.DocumentSigning** / `media-signing` | `SigningSessionInitiated` (domain) | `throw NotImplementedException` | — | ✅ | never triggered — domain events not published (`XM-C7`) |
| **Projectors.ReadModel** / `media-projector` | all `media-domain-events` | read-model projections | No (`catch/log`) | ✅ | not a cross-module seam |
| **TimeoutScanner** / EventBridge 5-min | — (scans `media-sagas` table) | `FailProcessingJob` / `FailAssetProcessing` → compensation | idempotent-by-aggregate | n/a (no queue) | only `AssetIngestionSaga`; no DocumentSigning coverage (`XM-G4`) |

**No consumer for:** `media.item.submitted-for-review`, `media.changerequest.created` (bridged, no handler → silent drop, `XM-C5`); `media.asset.attached`, `media.item.assigned-to-folder/deleted/rejected`, `media.registration.confirmed/submitted/resubmitted`, all `collection.*`/`folder.*` except `collection.archived` (published-but-unconsumed intra-BC).

---

## 4. Cross-Module Flow Analysis

### 4.1 Asset ingestion (`AssetIngestionSaga`)

```
Api(prod): ConfirmAssetUpload
   └─ media.asset.upload-confirmed ──▶ [media-processing q]
                                          └─ ProcessingWorker: CreateProcessingJob
                                                └─ ProcessingJobCreated (domain)
                                                     └─(mapper)▶ media.processingjob.created ─▶ [media-sagas q]
                                                                    └─ AssetIngestionSaga: create → AwaitingValidation
                                          └─ AssetValidationWorker: scan
                                                └─ RecordProcessingJobScanResult
                                                     └─(mapper)▶ media.processingjob.scan-result ─▶ [media-cross-module q]
                                                                    └─ AssetMgmt: RecordValidationResult
                                                                         └─▶ media.asset.validation-passed ─▶ [media-sagas q]
                                                                                └─ Saga: → ProcessingDispatched (+StartProcessingJob) | Bypassed (+BypassProcessingJob)
StartProcessingJob ─▶ media.processingjob.started ─▶ AssetMgmt: StartAssetProcessing
(rendition pipeline) ─▶ ProcessingJobSucceeded ─▶ media.processingjob.completed ─▶ AssetMgmt: CompleteAssetProcessing
                                                                                       └─▶ media.asset.processing-completed ─▶ [media-sagas q]
                                                                                              └─ Saga: → Completed (terminal)
```

**Happy path branches:** capable profile → `ProcessingDispatched`; non-capable (document) → `Bypassed` fast-exit via `ActivateDocumentAsset`. **S12 process-on-assign:** a standalone asset assigned to a Processing-capable profile re-enters via `AssetReprocessingRequested → media.asset.upload-confirmed` (not saga-timeout-tracked).

**Issues:** `XM-C1` (nothing after the API's first publish actually runs in prod — ProcessingWorker's `CreateProcessingJob` throws at the publish middleware); `XM-C2` (`processingjob.created/scan-result/bypassed` have no SNS route → saga is never triggered and the scan hop is severed even with `XM-C1` fixed); `XM-H2` (`validation-passed` DLQs in EventConsumers because it is in that queue's filter but unbridged); `XM-H5` (**no completion driver** — `AssetProcessingWorker.ProcessAsync` is registered but never invoked, so capable jobs sit `Running` until the saga forces a timeout `Failed`, PJ-C2); read-your-write race: `AssetValidationPassed.HasProcessingCapability` is computed from the eventually-consistent `MediaItemCapabilityReference` (`XM-H7`).

### 4.2 MediaItem review / approval (`MediaItemReviewSaga`, intended)

```
Catalog: SubmitForReview ─▶ media.item.submitted-for-review ─▶ [media-cross-module q]
                                └─ (bridged, NO HANDLER) → ACK → dropped        ✖ XM-C5
   (intended) → ChangeRequests: CreateChangeRequest ─▶ media.changerequest.created ─▶ (NO HANDLER) → dropped ✖ XM-C5
   (intended) reviewer decisions ─▶ ChangeRequestApproved/Rejected ─▶ MediaItemReviewSaga → Approve/Reject
```

**Issues:** the review choreography is largely **absent** — `ChangeRequests` publishes only `ChangeRequestCreated` (CR-S1); the `Approved/Rejected/Abandoned` integration events, the reviewer commands, and `MediaItemReviewSaga` do not exist in code; `submitted-for-review` and `changerequest.created` are silently dropped (`XM-C5`); the review saga has no 14-day timeout scanner (`XM-G4`). No terminal state reachable ⇒ review threads never form.

### 4.3 Metadata (RecordType) → Catalog

```
Metadata: PublishRecordType ─▶ media.recordtype.published ─▶ [media-cross-module q]
                                   └─ SNS filter allowlist has 'media.profile.published' NOT 'media.recordtype.published' ✖ XM-C3
                                   └─ (never delivered) → Catalog RecordTypeVersion index never updated
```

**Issue:** `XM-C3` — filter/message-type mismatch kills RecordType propagation. (The spec is itself contradictory about whether Catalog consumes these or reads `media-record-types` directly — §9/E — but the code *registers a consumer*, so the missing filter entry is a real defect against code intent.)

### 4.4 Change-request → catalog mutation
Not implemented as an integration flow (comment-only ChangeRequests, CR-S1). Catalog's `ChangeRequestReference` index / review-policy gate described in spec has no feeding consumer.

### 4.5 Folder / Collection lifecycle ripple

```
Catalog: ArchiveCollection ─▶ media.collection.archived ─▶ Catalog CollectionArchivedEventHandler → CollectionArchiveFanOutWorker (BFS)
Catalog: ArchiveFolder     ─▶ media.folder.archived (published, no intra-BC consumer; Search only)
```
Only Collection archive fans in intra-BC; folder/asset lifecycle → AssetManagement capability/archive refs relies on `media.item.archived` (works) but `media.asset.archived`/`infection-detected` are filtered out (`XM-C3`).

### 4.6 Registration → Catalog
`media.registration.initiated/cancelled/rejected → Catalog AddRegistrationRef/RemoveRegistrationRef` (works; best-effort, ACK-on-failure). `confirmed/submitted/resubmitted` published with no consumer.

### 4.7 Document signing (deferred)

```
DocumentSigning: (SigningSessionInitiated domain event — NEVER PUBLISHED; ISigningDomainEvent excluded from DomainEventPublishingMiddleware)
   └─▶ [media-signing q] ─▶ SigningSessionInitiatedHandler → throw NotImplementedException
Webhook (API GW) ─▶ SecuredSigningWebhookHandler → 501
```
Entire slice unwired (`XM-C7`): no aggregate, no integration events, `DocumentSigningSaga` not registered, no 72-h timeout scanner, `ISecuredSigningApiClient` unregistered.

---

## 5. Saga Analysis

### 5.1 `AssetIngestionSaga` (registered ✔, implemented ✔)

```
                 media.processingjob.created
                        │ (create; TimeoutAt = CreatedAt + ValidationBudget[15m])
                        ▼
                ┌──────────────────┐  validation-passed & !capable   ┌──────────┐
                │ AwaitingValidation│ ───────────────────────────────▶│ Bypassed │ (terminal, +BypassProcessingJob)
                └──────────────────┘                                  └──────────┘
                        │ validation-passed & capable
                        │ (+StartProcessingJob; TimeoutAt reset = PassedAt + ProcessingBudget[≤4h])
                        ▼
                ┌────────────────────┐  processing-completed   ┌───────────┐
                │ ProcessingDispatched│ ───────────────────────▶│ Completed │ (terminal)
                └────────────────────┘                          └───────────┘
                        │ processing-failed                          ▲
                        ▼                                            │ processing-timeout-recovered (S6)
                   ┌────────┐ ───────────────────────────────────────┘
                   │ Failed │ (terminal, +FailProcessingJob)   [AwaitingValidation can also → Failed on validation timeout]
                   └────────┘
```

- **Timeouts:** two-phase — `ValidationBudget` 15 min set at creation; reset to per-profile `ProcessingTimeoutMinutes` (else `DefaultProcessingBudget` 4 h) on `AwaitingValidation→ProcessingDispatched`. `TimeoutScanner` scans both `AwaitingValidation` and `ProcessingDispatched` via the `SagaTypeByTimeout` GSI (✔).
- **Compensation:** validation timeout → `FailAssetProcessing(ValidationTimeout)` + `FailProcessingJob`; processing timeout → `FailProcessingJob(ProcessingTimeout)`; `Failed→Completed` reversible via `processing-timeout-recovered`.
- **State guards:** every handler is status-guarded and creation is existence-guarded (good discipline).

**Issues:** `XM-H9` — `DynamoDbSagaRepository.SaveAsync` (`shared/Media.Shared.Infrastructure/Sagas/DynamoDbSagaRepository.cs:53-73`) is a plain `PutItem` with **no optimistic concurrency** (the `Version` attribute is written but never used as a condition); concurrent/duplicate same-`AssetId` deliveries can both pass a status guard and last-write-wins clobber (e.g. a `Completed` write lost, or `Start`/`Fail` double-dispatched). `XM-C4` — the saga handler is *also* mis-registered in EventConsumers without the saga repository → those events perpetually DLQ there. `XM-M4` — `TimeoutScanner` reads `context.RemainingTime` into a snapshot passed once into `ScanAsync` and never re-reads it inside the page loop (`AssetIngestionTimeoutScanner.cs:101,279`), so the "abort when remaining < 15 s" guard is effectively dead → risk of the Lambda being killed mid-compensation.

### 5.2 `MediaItemReviewSaga` — intended, **unregistered/partial**
Spec defines a 14-day review saga (`submitted-for-review → AwaitingReview → Completed/Rejected/Abandoned`). Not in `SagaRegistrations`; the triggering events are dropped (`XM-C5`); no timeout scanner entry (`XM-G4`). Runtime consequence: media items submitted for review never progress and are never auto-rejected on timeout.

### 5.3 `DocumentSigningSaga` — intended, **not implemented**
Not in `SagaRegistrations`. `Function.cs` documents an `AwaitingSigners`/72-h timeout, but the SQS handler throws `NotImplementedException`, the webhook returns 501, there is no aggregate/state persistence, and `TimeoutScanner` only knows `ASSET_INGESTION` (`XM-C7`, `XM-G4`).

---

## 6. Messaging Topology Review (CDK vs code)

**Topics (`sns-topics.construct.ts`):** `media-domain-events`, `media-integration-events`. ✔ matches spec.

**Queues (`sqs-queues.construct.ts`, all standard, `maxReceiveCount=3`, per-queue DLQ + depth≥1 alarm):**

| Queue | Source | Visibility | DLQ retention | Filter (SNS `EventType`) | Consumer |
|---|---|---|---|---|---|
| `media-projector` | domain | 300 s | 14 d | none | Projectors.ReadModel |
| `media-projector-search` | domain | 300 s | 14 d | subscription deferred (`deploySearch`) | Projectors.Search |
| `media-processing` | integration | 1800 s | 14 d | allow `media.asset.upload-confirmed` | ProcessingWorker |
| `media-cross-module-events` | integration | 300 s | **7 d** | 24-value allowlist (below) | EventConsumers |
| `media-sagas` | integration | 300 s | 14 d | 5-value allowlist | SagaOrchestrator |

These numbers match `system-spec.md`. (`docs/spec/architecture/bounded-context.md:712-723` is **stale** — it lists these queues off `media-domain-events` with 30/60 s visibility and different filters; see §9.)

**`media-cross-module-events` filter ⇄ code bridge mismatches** (`sqs-queues.construct.ts:190-224` vs `ConsumerRegistrations.cs:71-119`):

*Consumed in code but **filtered out** at SNS (events never delivered):*
- `media.recordtype.published`, `media.recordtype.deprecated` — bridged (`ConsumerRegistrations.cs:96-97`) & consumed by Catalog, but the allowlist instead contains `media.profile.published`/`media.profile.deprecated` under a `// Metadata (RecordType)` comment (`sqs-queues.construct.ts:211-213`) — the author conflated *profile* and *recordtype*. → **`XM-C3`.**
- `media.asset.archived` — bridged (`:75`) & consumed, **absent** from allowlist. → `XM-C3`.
- `media.asset.infection-detected` — bridged (`:77`) & consumed, **absent** from allowlist. → `XM-C3`.

*In the filter allowlist but **not bridged** in EventConsumers (delivered, then DLQ'd as an unroutable message):*
- `media.asset.validation-passed` (`sqs-queues.construct.ts:199`) — not bridged. → `XM-H2`.
- `media.item.asset-assigned` (`:206`) — handler DI-registered but not bridged. → `XM-C6`.

**`media-sagas` filter** (`:239-247`): `processingjob.created`, `asset.validation-passed`, `asset.processing-completed`, `asset.processing-failed`, `asset.processing-timeout-recovered` — **matches** `SagaRegistrations` (5=5) ✔. (But `processingjob.created` is never published — `XM-C2`.)

**Publisher-vs-topology:** `media.processingjob.created/bypassed/scan-result` have contracts + mappers but no `AddSNSPublisher` in any host → they fan out to **zero** queues (`XM-C2`). `media-processing` visibility 1800 s ✔ (video jobs extend to 4 h). FIFO: none — all standard/at-least-once; consumers must be idempotent (several are not — §8).

**`DEPLOYMENT.md` drift:** `hosts/EventConsumers/DEPLOYMENT.md:52-59` documents a 6-value filter (`MediaItemCreatedMessage`, `FolderArchivedMessage`, `RegistrationInitiatedMessage`, …) that matches *neither* the code bridge nor the CDK allowlist — a third, stale copy of the contract (`XM-M6`).

**Deploy note (`XM-M7`):** `bin/magiq-media.ts:20-29` defaults `ORGANIZATION_ID` to `o-abc123test`; if it reaches a real deploy, the ECR `AllowPull` org-condition denies every Lambda's image pull → cold-start `ECR 403`. Not an integration seam per se but blocks the whole system.

---

## 7. Inter-Module Relationship & Coupling Map

```
                 (domain events → projectors; not shown)

        Processing ──scan-result / job.*──▶ AssetManagement ──asset.*──▶ Catalog
            ▲                                     ▲    │                    │
            │ upload-confirmed                    │    │ profile.published  │ item.created/approved/archived
            │                                     │    ▼                    ▼
        AssetManagement ◀── item.asset-assigned ──┤  (AssetProfileDefaultRef)   Registration
            │  (S12)                              │                         (MediaItemRegistrationContext)
            │                                     │
        Metadata ──recordtype.published──▶ Catalog (RecordTypeVersion ref)
        Catalog ──collection.archived──▶ Catalog (self, fan-out)
        Catalog ──submitted-for-review──▶ ChangeRequests ──changerequest.created──▶ (∅)
        DocumentSigning ──(deferred)──▶ ∅
```

**Reference / ACL models (write-side, one module derived from another's events):**

| Model | Owner | Fed by | Key / watermark | Read by (guard) | Risk |
|---|---|---|---|---|---|
| `MediaItemCapabilityReference` | AssetMgmt | Catalog `item.created/archived` | `ProjectedVersion` — **mixes `EventVersion` (created) and `UtcTicks` (archived)** | `MediaItemCapabilityService` at upload | `XM-H3` (archived-before-created; stale read) |
| `AssetProfileDefaultReference` | AssetMgmt | Catalog `profile.published/deprecated` | atomic set-add/remove w/ `Version` | `AssetProfileDefaultService` | `XM-H4` (shared-key deletable state) |
| `AssetStateReference` | Catalog | AssetMgmt `asset.*` | `EventVersion` (but `upload-initiated` unconditional upsert) | Catalog command handlers | `XM-H4` (overwrite/resurrect) |
| `MediaItemVersionAssetReference` | Catalog | `item.approved/version.purged` | **none (last-write-wins)**, and **no feeding bridge** | `PurgeMediaItemVersion` | `XM-H4`, `XM-H6` |
| `MediaItemReference` | Registration | Catalog `item.created/approved/archived` | `EventVersion` (no compare) | `MediaItemRegistrationContextService` (local) | `XM-H4` |

**Sync cross-BC calls:** none found that cross a bounded context at runtime — `BillingAcl` reads local tenant config (no HTTP), capability/profile/registration lookups all read *local* reference models. This is good ACL discipline; the trade-off is eventual-consistency staleness (`XM-H7`).

**Cycles:** `AssetManagement ⇄ Catalog` and `AssetManagement ⇄ Processing` are bidirectional at the *event* level (asset lifecycle ↔ item lifecycle; asset validation ↔ processing job). These are asynchronous, so they do not deadlock, but they create a tight temporal coupling and the ingestion loop spans AssetMgmt→Processing→AssetMgmt→Saga four times — fragile and hard to observe end-to-end (`XM-DF3`).

---

## 8. Contract & Versioning Review

- **Versioning:** every contract carries `long EventVersion` ✔. All events are effectively **v0** — no consumer branches on version, and payload fields added later (e.g. `StorageKey` on `AssetArchived/Deleted`, documented "null for older events") rely on nullable defaults rather than a version check (`XM-M5`). Acceptable for now but there is no forward-compat test.
- **Producer/consumer field compatibility:** **`XM-M1`** — `AssetProcessingCompletedIntegrationEvent.Status` / `…TimeoutRecovered.Status` carry a `ProcessingStatus` string while `…Failed.Status` carries an `AssetStatus` string (F-P2); a consumer treating `Status` uniformly breaks. **`XM-M2`** — `MediaItemId?` is present on `asset.archived/deleted/infection-detected` but **dropped** from `processing-completed/failed/timeout-recovered` (F-P4), forcing correlation lookups. `ProcessingRenditionDto.FileSizeBytes` vs spec `SizeBytes`; `Width/Height` dropped from the completed contract (F-C5).
- **TenantId propagation:** **`XM-H8`** — virtually every consumer reads `TenantId` from the **payload body** (`e.TenantId`), not the `IMessageHandlingContext.Metadata` SNS attribute (only `CollectionArchivedEventHandler` uses the ambient context). This violates the stated convention (`CLAUDE.md`, ADR-005), and means a privileged consumer-dispatched command's tenant/actor context is reconstructed from untrusted body content rather than the transport attribute. `System`-actor authorization for those commands is not evidenced.
- **Idempotency:** **`XM-H1`** — no consumer inspects the command `Result<T,DomainError>`; a *domain rejection* (a non-exception failure) completes silently → the message is ACKed, indistinguishable from an idempotent no-op, and is **never retried or DLQ'd**. Only thrown infra exceptions trigger redrive (F-C1). Combined with the reference-projector version gaps (`XM-H3/H4`), at-least-once + out-of-order delivery is not safely handled.
- **Domain leakage / PII:** payloads carry `OwnerId` and `StorageKey` (S3 object paths) across the BC boundary — storage keys are an internal concern of AssetManagement/Processing and their appearance in `asset.archived/deleted` is a mild leak of storage layout to external BCs (`XM-M8`). No obvious PII beyond owner ids.

---

## 9. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| `media.item.asset-assigned` (S12) | **absent** from integration catalogue; `AssetAssignedToRole` is domain-only | published + consumed (handler dead, `XM-C6`) | High | add to catalogue; wire the bridge |
| `AssetUnassignedFromRole` / `AssetReplacedInRole` integration events | implied by asset↔item consistency | **not published** (MI-FP2) | High | add events + AssetMgmt consumers |
| RecordType → Catalog | 3-way contradictory (consumes IE / reads table directly / Notifications-only) | code registers Catalog consumers, but filter drops them (`XM-C3`) | High | decide the model; fix filter or remove consumers |
| MediaItem review saga + `changerequest.{approved,rejected,abandoned}` | full review choreography | comment-only; events + saga absent (CR-S1) | High | implement or de-scope in spec |
| DocumentSigning saga/events | defined (72-h timeout, envelope flow) | unwired stubs (`XM-C7`) | Medium (known-deferred) | keep deferred; remove half-wired hosts/queues or gate them |
| `media-cross-module-events` filter policy | "TODO: add explicit filter policy"; 7-day DLQ | filter exists but mismatched (`XM-C3/C6/H2`) | Critical | reconcile filter to bridge |
| Messaging table | `system-spec.md` accurate; `bounded-context.md:712-723` stale (domain-source, 30/60 s) | CDK matches `system-spec` | Low | retire the stale table |
| Publisher naming | `AssetIntegrationEventPublisher` (ADR-005 inline) | `AssetIntegrationEventMapper` (domain-event mapper) | Low | align docs/ADR-005 to the mapper mechanism actually used |
| `RecordTypeDeprecated.RecordTypeVersion` | schema version | event-store `AggregateVersion` (RT-I1) | Medium | source the schema version |
| `MediaProfilePublished` payload | full snapshot (AssetDefinitions/template) | lossy summary (MP-FP1) | High | include the snapshot consumers need |

---

## 10. Bugs

### Critical

- **`XM-C1` — Integration events cannot be published from any worker host (production).** *Files:* `hosts/ProcessingWorker/Function.cs:60-74`, `hosts/EventConsumers/Function.cs:56-65`, `hosts/SagaOrchestrator/Function.cs:44-70`, `hosts/TimeoutScanner/Function.cs:66-83` (no platform `IMessageBus`) vs `hosts/Api/Startup.cs:101,139-156` (only host that registers one); platform `IntegrationEventPublishingMiddleware` resolved lazily at `Magiq.Platform.WriteModel.Application/Events/DomainEventPipelineBuilder.cs:37`, needs `IMessageBus` (ctor). **Description:** worker/consumer/saga/timeout hosts register the write-model (`UseIntegrationEventPublishing()`) but only the *raw* `AddAWSMessageBus` (AWS.Messaging publisher), never the platform `AddMessaging`/`AddInProcessMessageBus` that provides `Magiq.Platform.Messaging.IMessageBus`. **Why it's a problem:** the first command any worker dispatches raises a mapped domain event → the pipeline resolves `IntegrationEventPublishingMiddleware` → `GetRequiredService<IMessageBus>()` throws `InvalidOperationException`. **Impact:** the entire async choreography is inert in prod — `ProcessingWorker.CreateProcessingJob` throws before validation; no `processingjob.*`, no `validation-passed`, no saga progression, no asset state advance. Masked in dev/qa/staging (CDK sets `Development` → API runs everything in-process via `DevInProcessMessageBus`). **Recommendation:** register the platform message bus (`AddMessaging(... AddAwsMessageBus(...AddXIntegrationEventPublishers))`) in every worker host, or provide a shared `AddMediaProductionMessaging()` extension used by all hosts; add a prod smoke test that publishes one event per host.

- **`XM-C2` — `processingjob.created`, `processingjob.scan-result`, `processingjob.bypassed` have no SNS publisher route.** *Files:* `hosts/Api/Infrastructure/Publishers/ProcessingIntegrationEventPublishers.cs:10-12` (registers only Completed/Failed/Started); mappers emit all six at `Processing.WriteModel/IntegrationEvents/Publishing/Mappers/ProcessingDomainEventMapper.cs:21,32,58`. **Why:** `IMessageBus.PublishAsync` for an unregistered type throws `MissingMessageTypeConfiguration`. **Impact:** even with `XM-C1` fixed, the saga trigger (`processingjob.created`), the validation hop (`scan-result`), and the document fast-exit (`bypassed`) are severed. **Recommendation:** register SNS publishers for all six Processing integration events in whichever host publishes them.

- **`XM-C3` — `media-cross-module-events` SNS filter omits events the code consumes.** *Files:* `cdk-magiq-media/lib/constructs/messaging/sqs-queues.construct.ts:190-224` vs `hosts/EventConsumers/ConsumerRegistrations.cs:75,77,96,97`. The allowlist has `media.profile.published/deprecated` mislabeled `// Metadata (RecordType)` and omits `media.recordtype.published`, `media.recordtype.deprecated`, `media.asset.archived`, `media.asset.infection-detected`. **Impact:** RecordType→Catalog propagation, Catalog's asset-archive state, and infection handling never fire (SNS drops the message before the queue). **Recommendation:** add the four missing message-types; generate the filter from the code bridge to prevent drift.

- **`XM-C4` — `asset.processing-completed/failed` always DLQ in EventConsumers (and duplicate saga fan-in).** *Files:* `hosts/EventConsumers/ConsumerRegistrations.cs:59` calls `AddProcessingIntegrationEventConsumers` (registers `AssetProcessingCompletedSagaHandler` etc.) but not `AddProcessingAssetIngestionSaga`; handler ctor needs `AssetIngestionSaga`→`ISagaRepository<AssetIngestionSagaState>` (`Processing.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:41-59,71-72`). **Why:** `IntegrationEventMessageHandler.HandleAsync` (`:43`) calls `GetServices<IIntegrationEventHandler<T>>()`, which constructs the saga handler → unresolved dependency → `InvalidOperationException` → `Failed()` → retried → DLQ every time. Also, `media.asset.upload-confirmed`/`upload-initiated` handlers are co-registered here, duplicating ProcessingJob creation. **Impact:** those two events perpetually DLQ on the cross-module queue and their legitimate Catalog handlers never commit. **Recommendation:** stop registering Processing saga/worker consumers in EventConsumers; register only the reference/command consumers each host actually needs.

- **`XM-C5` — `item.submitted-for-review` and `changerequest.created` are ACKed and silently dropped.** *Files:* `hosts/EventConsumers/ConsumerRegistrations.cs:87,90` (bridged) vs `ChangeRequests.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:23-47` (no `IIntegrationEventHandler` registered; `AddChangeRequestWriteModel` only). `ChangeRequests.WriteModel/IntegrationEvents/Consuming/Handlers/MediaItemPublicationRequestedEventHandler.cs` exists but is never DI-registered; `ChangeRequestCreated` has no handler anywhere. **Why:** the bridge's `GetServices<>` returns empty → `foreach` no-ops → `Success()` → message deleted. **Impact:** review-thread ChangeRequests are never created; the entire media-item review flow dead-ends. **Recommendation:** add `AddChangeRequestIntegrationEventConsumers` and call it from EventConsumers; or, if `changerequest.created` is fire-and-forget for external BCs, remove it from the intra-BC filter and log the design decision.

- **`XM-C6` — S12 `media.item.asset-assigned` consumer is dead (handler registered, no bus bridge).** *Files:* handler registered `AssetManagement.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:107`; **not** bridged in `hosts/EventConsumers/ConsumerRegistrations.cs:71-119`; event is in the SNS filter (`sqs-queues.construct.ts:206`). **Why:** SNS delivers `media.item.asset-assigned` to the queue but AWS.Messaging has no `IMessageHandler` for it → unroutable → DLQ. **Impact:** process-on-assign, lifecycle re-tagging, and standalone-asset attach never run. **Recommendation:** add `bus.AddMessageHandler<IntegrationEventMessageHandler<AssetAssignedToRoleIntegrationEvent>, …>()`.

- **`XM-C7` — DocumentSigning integration surface is non-functional.** *Files:* `hosts/Api/Infrastructure/Middleware/DomainEventPublishingMiddleware.cs:35` (`ISigningDomainEvent` excluded → signing domain events never publish); `hosts/SagaOrchestrator.DocumentSigning/Handlers/SigningSessionInitiatedHandler.cs:40` (`throw NotImplementedException`); `SecuredSigningWebhookHandler.cs:40` (501); no `DocumentSigningSaga` in `SagaRegistrations`; no aggregate/commands in `modules/DocumentSigning`. **Impact:** the entire signing flow is inert. **Recommendation:** keep formally deferred; remove or feature-gate the half-wired host/queue so it does not read as production-ready.

### High

- **`XM-H1` — Consumers never inspect the command `Result`; domain rejections are swallowed.** All consumer handlers `await SendAsync(cmd)` and discard the result (e.g. `AssetManagement.WriteModel/IntegrationEvents/Consuming/Handlers/ProcessingJob*EventHandler.cs`; Catalog `AssetProcessingCompletedAutoSubmitHandler.cs:101`). A domain failure (not an exception) is ACKed → lost, no DLQ (F-C1). **Recommendation:** inspect the `Result`; throw (→ retry/DLQ) on retryable failure, ACK only on genuine idempotent no-op, and emit a metric on domain rejection.
- **`XM-H2` — `media.asset.validation-passed` in the cross-module filter but unbridged → DLQ.** `sqs-queues.construct.ts:199` vs no bridge in `ConsumerRegistrations`. Remove from the cross-module filter (it belongs only to `media-sagas`).
- **`XM-H3` — `MediaItemCapabilityReferenceProjector` mixes watermark domains.** Created path sets `ProjectedVersion = EventVersion` (small int); Archived path sets `ArchivedAt.UtcTicks` (~1e17) — a redelivered Created can appear "newer" than an Archived, and Archived-before-Created leaves an archived item reading not-archived forever, admitting uploads to archived items (F-R1/F-R2). **Recommendation:** one monotonic domain (aggregate version) for both paths.
- **`XM-H4` — Reference projectors are inconsistently version-guarded (last-write-wins / resurrection).** `AssetStateReferenceProjector` uses unconditional `UpsertAsync` for `upload-initiated` (overwrites a later `processing-completed`) and unconditional `DeleteAsync` for `deleted`; `MediaItemVersionAssetReferenceProjector` has no version compare (a duplicate `Approved` after a `Purge` resurrects the row). **Recommendation:** version-guard every reference write; treat delete as a tombstone with a version.
- **`XM-H5` — No completion driver for the rendition pipeline.** `AssetProcessingWorker.ProcessAsync` is registered but never invoked; the sole `validation-passed` consumer (the saga) only dispatches `StartProcessingJob`, so capable jobs sit `Running` until the saga forces a timeout `Failed` (PJ-C2). **Recommendation:** invoke the processing worker after `StartProcessingJob` (in `ProcessingWorker`) and publish `ProcessingJobSucceeded`.
- **`XM-H6` — Catalog `MediaItemVersionAssetReference` is never populated.** No thin `IIntegrationEventHandler<MediaItemApproved/VersionPurged>` feeds `pipeline.DispatchAsync` in the consumer host, so `PurgeMediaItemVersion`'s lookup is always empty. *(Verify against the projection framework's `AddHandlers` dispatch, but no bridge is registered.)* **Recommendation:** register the feeding handlers or confirm the framework auto-dispatches.
- **`XM-H7` — Read-your-write races across the seam.** Upload-time guards read eventually-consistent reference models (`MediaItemCapabilityService`, `AssetProfileDefaultService`); `AssetValidationPassed.HasProcessingCapability` is computed from a projection that may lag Catalog's actual MediaItem state (F-R5). **Recommendation:** accept-and-reconcile, or read the capability from the authoritative aggregate at decision time for the narrow capability check.
- **`XM-H8` — TenantId sourced from payload body, not the SNS attribute.** Systemic across consumers (F-C4). Violates ADR-005/convention and weakens the tenant/actor trust boundary for consumer-dispatched privileged commands. **Recommendation:** read `TenantId`/actor from `IMessageHandlingContext.Metadata`.
- **`XM-H9` — Saga state saved without optimistic concurrency.** `DynamoDbSagaRepository.SaveAsync` plain `PutItem`, `Version` unused as a condition (`shared/Media.Shared.Infrastructure/Sagas/DynamoDbSagaRepository.cs:53-73`). Concurrent/duplicate same-key deliveries clobber. **Recommendation:** conditional `PutItem` on `Version`; retry on `ConditionalCheckFailed`.

### Medium

- **`XM-M1`** — `Status` field mixes `ProcessingStatus` vs `AssetStatus` across completed/failed/timeout-recovered (F-P2).
- **`XM-M2`** — `MediaItemId?` dropped from processing-completed/failed/timeout-recovered; `ProcessingRenditionDto` field-name/`Width/Height` drift (F-P4/F-C5).
- **`XM-M3`** — Document fast-exit publishes `media.asset.processing-completed`, so Billing mis-bills documents as processed (F-P3).
- **`XM-M4`** — `TimeoutScanner` `remainingTime` snapshot never re-read in the page loop → safety-buffer abort is dead (`AssetIngestionTimeoutScanner.cs:101,279`).
- **`XM-M5`** — No version-branching / forward-compat test despite nullable "added later" fields.
- **`XM-M6`** — `EventConsumers/DEPLOYMENT.md:52-59` filter list matches neither code nor CDK.
- **`XM-M7`** — `ORGANIZATION_ID` placeholder → ECR pull 403 blocks all Lambdas if it reaches a real deploy (`bin/magiq-media.ts:20-29`).
- **`XM-M8`** — S3 `StorageKey` (internal storage layout) leaks across the BC boundary in `asset.archived/deleted`.

### Low

- **`XM-L1`** — `RecordTypeDeprecated.RecordTypeVersion` = event-store `AggregateVersion`, not schema version (RT-I1).
- **`XM-L2`** — `*IntegrationEvent` (code) vs `*Message` (spec) naming drift throughout.
- **`XM-L3`** — `registration.confirmed/submitted/resubmitted`, `item.assigned-to-folder/deleted/rejected` published with no consumer (some intentional; `registration.confirmed` diverges from the spec's Compliance consumer).
- **`XM-L4`** — Infection event uses wall-clock timestamp (F-P6).

---

## 11. Design Flaws

- **`XM-DF1` — No transactional outbox (dual-write).** `DomainEventPublishingMiddleware.InvokeAsync` (`hosts/Api/Infrastructure/Middleware/DomainEventPublishingMiddleware.cs:69-82`) commits the event-store write (`next`) then publishes to SNS. Correct ordering, but if the process dies or SNS fails between commit and publish, the events are durably stored yet never published — permanent divergence with no relay. ADR-005 "inline publishers" have the same exposure. **Recommendation:** a DynamoDB-stream/outbox relay that publishes committed events at-least-once.
- **`XM-DF2` — Filter policy / bridge / DEPLOYMENT.md are three hand-maintained copies of one contract.** The `XM-C3/C6/H2/M6` mismatches are the direct symptom. **Recommendation:** generate the SNS filter allowlist from the `[MessageType]` attributes of the bridged handlers at synth time.
- **`XM-DF3` — Overloaded cross-BC ingestion loop / bidirectional coupling.** The ingestion path bounces AssetMgmt→Processing→AssetMgmt→Saga with the saga driven off integration events that AssetMgmt itself produces from Processing's events; a single business action crosses the AssetMgmt↔Processing boundary four times. Temporal coupling is high and end-to-end tracing is hard (no correlation id threaded — §12). **Recommendation:** consider collapsing the scan/validation hop or making the saga the single owner of the ingestion state machine.
- **`XM-DF4` — Same event fanned to two consumer hosts with overlapping handlers.** `asset.processing-completed/failed` and `upload-confirmed` reach both `media-cross-module-events` and `media-sagas`/`media-processing`, and EventConsumers co-registers saga/worker handlers (`XM-C4`). Ownership of each event→host mapping is not enforced. **Recommendation:** one authoritative host per (event, responsibility).

---

## 12. Design Gaps

- **`XM-G1` — No outbox** (see `XM-DF1`).
- **`XM-G2` — Idempotency is inconsistent.** ProcessingJob creation mints a new `JobId` per delivery (no dedup); reference projectors lack version guards; consumers can't distinguish no-op from failure (`XM-H1`).
- **`XM-G3` — No cross-flow correlation/observability.** SNS attributes carry `CorrelationId` (per `DEPLOYMENT.md`) but no host threads it into logs/metrics; there is no per-flow or per-saga success metric, only DLQ-depth and saga-approaching-timeout alarms. A stuck ingestion is invisible until the DLQ fills.
- **`XM-G4` — Missing timeout scanners.** Only `ASSET_INGESTION` is scanned; the spec's 14-day MediaItem review timeout and 72-h DocumentSigning timeout have no scanner (`TimeoutScanner/Scanner/` has one class).
- **`XM-G5` — No compensation for the review/signing sagas** (they don't exist), and the AssetIngestion compensation double-dispatches `FailProcessingJob` on validation timeout (harmless-if-idempotent, but noisy).
- **`XM-G6` — Missing events for asset unassign/replace** (`XM`/MI-FP2) leave AssetManagement unaware of role changes.

---

## 13. Missing Integration Capabilities

- SNS publisher registrations for `processingjob.created/scan-result/bypassed` (`XM-C2`).
- AWS.Messaging bridges for `item.asset-assigned` (`XM-C6`) and consumer registrations for `item.submitted-for-review` / `changerequest.created` (`XM-C5`).
- SNS filter entries for `recordtype.published/deprecated`, `asset.archived`, `asset.infection-detected` (`XM-C3`).
- Platform `IMessageBus` in every worker host (`XM-C1`).
- Integration events + consumers for `AssetUnassignedFromRole` / `AssetReplacedInRole`.
- `MediaItemReviewSaga` (+ its trigger consumers, closing handlers, 14-day scanner) and the full ChangeRequests review event set (`approved/rejected/abandoned`).
- `DocumentSigningSaga` + aggregate + integration events + 72-h scanner + `ISecuredSigningApiClient` registration.
- A transactional outbox / event relay.
- Per-flow correlation-id propagation and per-flow/per-saga success metrics.

---

## 14. Cross-Validation Results

| Check | Result |
|---|---|
| Every integration event has ≥1 real consumer **or** is documented fire-and-forget | **FAIL** — `submitted-for-review`, `changerequest.created` bridged with no handler (`XM-C5`); `item.assigned-to-folder/deleted/rejected`, `registration.confirmed/submitted/resubmitted` published, unconsumed, undocumented (`XM-L3`) |
| Every consumer's subscribed event is actually published by some module | **FAIL** — saga consumes `processingjob.created` which has no SNS route (`XM-C2`) |
| Every saga trigger event is actually published; every step's event can arrive | **FAIL** — `AssetIngestionSaga` trigger never published (`XM-C2`); nothing publishes from workers (`XM-C1`) |
| Every cross-module command is reachable and authorized (System-actor where privileged) | **PARTIAL** — reachable only in dev; actor/System context not evidenced; TenantId from body (`XM-H8`) |
| Every multi-module flow reaches a terminal state on success and failure | **FAIL** — ingestion inert in prod (`XM-C1`); review/signing flows dead-end (`XM-C5/C7`) |
| Every step that can hang has a timeout; every timeout has a scanner entry | **FAIL** — review (14 d) and signing (72 h) have no scanner (`XM-G4`) |
| Every consumer distinguishes idempotent no-op from retryable failure; every queue has a DLQ | **FAIL (logic)** / PASS (DLQs) — `XM-H1`; DLQs exist ✔ |
| Every reference/ACL watermark uses a single consistent version domain, reorder/replay-safe | **FAIL** — `XM-H3/H4` |
| Every spec-defined integration event/flow/saga is implemented; every implemented one is documented | **FAIL** — `XM-C7`, CR-S1, MI-FP2, `XM-C3`, catalogue gaps (§9) |
| No cyclic runtime dependency that can deadlock/livelock | **PASS** — cycles are async (but tightly coupled, `XM-DF3`) |

---

## 15. Recommendations (prioritised)

1. **Correctness — restore the production message bus (`XM-C1`).** Add the platform `IMessageBus` (`AddMessaging(...AddAwsMessageBus(...AddXIntegrationEventPublishers))`) to ProcessingWorker/EventConsumers/SagaOrchestrator/TimeoutScanner via one shared extension; add a prod publish smoke test. *Without this nothing else matters.*
2. **Correctness — register the missing SNS publisher routes (`XM-C2`)** for `processingjob.created/scan-result/bypassed`.
3. **Correctness — reconcile the SNS filter policy with the code bridge (`XM-C3/C6/H2/M6`)**, and generate it from `[MessageType]` attributes to stop future drift (`XM-DF2`).
4. **Correctness — fix the EventConsumers mis-registration (`XM-C4`)** (remove Processing saga/worker consumers) and wire the dropped review/change-request consumers (`XM-C5`).
5. **Data integrity — add version guards to every reference projector and use one watermark domain (`XM-H3/H4`)**; add a transactional outbox/relay (`XM-DF1/G1`).
6. **Data integrity — inspect command `Result` in every consumer (`XM-H1`)** so domain rejections retry/DLQ instead of being swallowed.
7. **Security — source TenantId/actor from the SNS attribute (`XM-H8`)** and assert `System`-actor authorization on consumer-dispatched privileged commands.
8. **Domain modelling — add `AssetUnassignedFromRole`/`AssetReplacedInRole` events**, decide the RecordType→Catalog model, and either implement or de-scope the ChangeRequests review saga and DocumentSigning (§9).
9. **Saga & lifecycle — add optimistic concurrency to the saga repo (`XM-H9`)**, fix the TimeoutScanner remaining-time guard (`XM-M4`), add the missing 14-day/72-h timeout scanners (`XM-G4`), and add a completion driver for the rendition pipeline (`XM-H5`).
10. **Messaging topology & delivery — one authoritative host per (event, responsibility) (`XM-DF4`)**; confirm `media-processing` 1800 s + `ChangeMessageVisibility` for video; verify DLQ retentions (7 d cross-module) match ops runbooks.
11. **Event & contract design — resolve `Status` enum overloading (`XM-M1`)**, restore `MediaItemId` on processing events (`XM-M2`), stop leaking `StorageKey` externally (`XM-M8`), and add a versioning/forward-compat test (`XM-M5`).
12. **Observability — thread `CorrelationId` end-to-end and add per-flow/per-saga success + latency metrics (`XM-G3`).**
13. **Maintainability — retire the stale `bounded-context.md` messaging table and `DEPLOYMENT.md` filter list**; align ADR-005 publisher naming with the mapper mechanism (§9).
14. **Performance/scalability — batchSize is 1 for `media-processing` (correct); revisit projector batch failure semantics** once the pipeline actually runs.

---

## 16. Top 5 Before Production

1. **`XM-C1` — Register the platform `IMessageBus` in every worker host.** The whole async choreography throws on the first worker publish in prod. → Rec. 1.
2. **`XM-C2` — Register SNS publisher routes for `processingjob.created/scan-result/bypassed`.** The saga is never triggered and the validation hop is severed even after `XM-C1`. → Rec. 2.
3. **`XM-C3` — Fix the `media-cross-module-events` filter (`recordtype.*`, `asset.archived`, `asset.infection-detected`; drop the mislabeled/misplaced entries).** SNS silently discards events the code consumes. → Rec. 3.
4. **`XM-C4` + `XM-C5` — Stop the EventConsumers saga mis-registration and wire (or remove) the review/change-request consumers.** `processing-completed/failed` DLQ every time; `submitted-for-review`/`changerequest.created` are silently dropped. → Rec. 4.
5. **`XM-H1` + `XM-H9` + `XM-H3/H4` — Make consumers and sagas safe under at-least-once/out-of-order delivery** (inspect `Result`, add saga optimistic concurrency, version-guard reference projectors) before real traffic hits the standard (unordered, at-least-once) queues. → Recs. 5, 6, 9.
