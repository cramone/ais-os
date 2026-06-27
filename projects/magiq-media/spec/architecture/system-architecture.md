# System Architecture — Media Management

_Last updated: 2026-04-26_

---

## Overview

Media Management is a set of C# microservices built around DDD, CQRS, and event sourcing. The system separates write-side (command handling, event persistence) from read-side (projections, query models) and uses AWS-native infrastructure for async processing and storage.

```
┌────────────────────────────────────────────────────────────────────┐
│                        API Gateway / ALB                           │
└────────┬───────────────────────────────────┬───────────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  Ingest API     │                 │  Query API      │
│  (Lambda/ECS)   │                 │  (Lambda/ECS)   │
│  ASP.NET        │                 │  ASP.NET        │
│  FastEndpoints  │                 │  FastEndpoints  │
└────────┬────────┘                 └────────┬────────┘
         │  Commands                         │  Queries
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  Command Bus    │                 │  Read Models    │
│  (MediatR)      │                 │  DynamoDB       │
└────────┬────────┘                 │  OpenSearch     │
         │                          └─────────────────┘
         ▼                                   ▲
┌─────────────────┐                          │
│  Event Store    │                 ┌─────────────────┐
│  DynamoDB       │────────────────▶│  Projectors     │
│  (append-only)  │  Domain Events  │  (Lambda)       │
└────────┬────────┘                 └─────────────────┘
         │
         │  Inline domain event dispatch in Command Handler:
         │    (a) projector handlers (local read-model writes)
         │    (b) *IntegrationEventPublisher handlers per module
         │          → build media.* envelopes, publish to
         │            SNS: media-integration-events (see below)
         │
         │  + Outbound publish to SNS: media-domain-events
         ▼
┌─────────────────┐
│  SNS Topic      │
│  media-domain-  │
│  events         │
└────────┬────────┘
         │
         ├──▶ media-projector SQS → Projectors.ReadModel Lambda (DynamoDB read models)
         ├──▶ media-projector-search SQS → Projectors.Search Lambda (OpenSearch)
         ├──▶ media-processing SQS → Processing Worker Lambda (host not yet deployed)
         └──▶ media-signing SQS → SecuredSigning Adapter Lambda (host not yet deployed)

┌───────────────────────┐
│  SNS Topic            │   populated by per-module
│  media-integration-   │   *DomainEventMapper classes
│  events               │   (inline with Command Handler) — ADR-005
└────────┬──────────────┘
         │
         ├──▶ media-cross-module-events SQS (MM-owned intra-BC fan-in)
         │      └─▶ EventConsumers Lambda
         ├──▶ media-sagas SQS → SagaOrchestrator Lambda
         ├──▶ media-document-signing SQS → SagaOrchestrator.DocumentSigning Lambda
         ├──▶ media-bulk-folder-imports SQS → BulkFolderImportWorker Lambda
         ├──▶ media-bulk-media-imports SQS → BulkMediaImportWorker Lambda
         ├──▶ Notifications-owned SQS
         ├──▶ Search/Discovery-owned SQS
         ├──▶ Billing-owned SQS
         └──▶ Compliance-owned SQS
```

---

## Services

### 1. Ingest API
**Runtime:** AWS Lambda (containerised ASP.NET, FastEndpoints)
**Responsibility:** Accepts upload requests, validates auth, issues pre-signed S3 URLs, dispatches all write commands via MediatR.

- Receives upload request metadata POST (not the binary — client uploads directly to S3 via pre-signed URL)
- Dispatches `UploadAsset` command → `AssetCommandHandler`; returns `AssetId` + pre-signed URL to client
- Receives S3 event notification (via SQS) when upload completes → dispatches `ConfirmAssetUpload` command
- Dispatches commands for all other write operations: `CreateMediaItem`, `AssignMediaItemToFolder`, `CreateCollection`, `CreateFolder`, `InitiateRegistration`, etc.
- `mediaItemId` is optional on `POST /media-assets/upload-url` — omit for standalone (drag-and-drop) uploads

### 2. Query API
**Runtime:** AWS Lambda (containerised ASP.NET, FastEndpoints)
**Responsibility:** Serves all read traffic. No writes.

- Queries DynamoDB read models for media-item detail, media-folder hierarchies, media-collection detail, asset detail, media-registration detail, RecordType and MediaProfile configuration
- Queries OpenSearch for full-text / faceted search on `media-items` and `media-registrations` indexes
- Returns DTOs only — no domain objects cross the boundary

### 3. Command Handler (Write Side)
**Runtime:** Lambda (invoked by Ingest API and SQS triggers)
**Responsibility:** Handles all commands, loads aggregates from the event store, applies domain logic, persists new events.

- Uses MediatR for command dispatch
- Event store: DynamoDB `media-events` (partition key = `TENANT#{TenantId}#{AggregateId}`, sort key = `AggregateVersion`)
- Optimistic concurrency enforced via DynamoDB conditional writes (`attribute_not_exists(AggregateVersion)`)
- After persisting events, publishes to SNS for downstream fan-out

### 4. Projectors

Projectors are split across two Lambda hosts with independent queues, DLQs, and scaling:

#### 4a. Projectors.ReadModel
**Host:** `src/hosts/Projectors.ReadModel`
**Runtime:** Lambda triggered by SQS (`media-projector` queue, subscribed to `media-domain-events`)
**Responsibility:** Consume domain events and maintain DynamoDB read models. All projectors are registered in `ProjectorRegistrations.cs`.

Projectors are further split into two groups: **read-model projectors** (query-facing) and **write-side reference index projectors** (used by command handlers for constraint enforcement and capability resolution).

**Read-model projectors:**

| Projector | Target Table | Notes |
|---|---|---|
| `AssetDetailProjector` | `media-asset` | |
| `AssetSummaryProjector` | `media-assets` | |
| `CollectionDetailProjector` | `media-collection` | |
| `CollectionSummaryProjector` | `media-collections` | |
| `FolderDetailProjector` | `media-folder` | |
| `FolderSummaryProjector` | `media-folders` | |
| `MediaItemDetailProjector` | `media-item` | |
| `MediaItemSummaryProjector` | `media-items` | |
| `MediaItemVersionProjector` | `media-item-versions` | |
| `MediaProfileDetailProjector` | `media-profile` | |
| `MediaProfileVersionProjector` | `media-profile-versions` | |
| `ChangeRequestDetailProjector` | `media-change-request` | |
| `ChangeRequestSummaryProjector` | `media-change-requests` | |
| `ChangeRequestCommentProjector` | `media-change-request-comments` | |
| `SigningSessionDetailProjector` | `media-signing-session` | |
| `SigningSessionSummaryProjector` | `media-signing-sessions` | 🔴 Deferred — `DocumentSigning` module not yet complete |
| `RecordTypeDetailProjector` | `media-record-type` | |
| `RecordTypeSummaryProjector` | `media-record-types` | |
| `RecordTypeVersionProjector` | `media-record-type-versions` | |
| `RegistrationDetailProjector` | `media-registration` | |
| `RegistrationSummaryProjector` | `media-registrations` | |
| `BulkFolderImportJobSummaryProjector` | `media-bulk-folder-import-jobs` | |
| `BulkFolderImportJobDetailProjector` | `media-bulk-folder-import-job-detail` | |
| `BulkMediaImportJobSummaryProjector` | `media-bulk-media-import-jobs` | |
| `BulkMediaImportJobDetailProjector` | `media-bulk-media-import-job-detail` | |

**Write-side reference index projectors** (used by command handlers — not query-facing):

| Projector | Target Table | Purpose |
|---|---|---|
| `FolderRegistrationIndexProjector` | `media-catalog-folder-registration-index` | ActiveRegistrationCount per folder subtree; consumed by `IFolderDomainService.HasActiveRegistrationsInSubtreeAsync` |
| `FolderChildIndexProjector` | `media-catalog-folder-folders-index` | Direct child folder IDs per parent (folder or collection root); guards nesting depth |
| `FolderMediaItemsIndexProjector` | `media-catalog-folder-items-index` | MediaItem IDs per folder; consumed by move/archive guards |
| `MediaProfileIndexProjector` | `media-catalog-profile-index` | Compiled MediaProfile capabilities; consumed by command handlers via `IMediaProfileIndex` |
| `MediaItemProfileIndexProjector` | `media-catalog-item-profile-index` | MediaItem IDs pinned to each profile; consumed by `MediaProfilePublished` conformance fan-out |
| `AssetToMediaItemIndexProjector` | `media-catalog-asset-item-index` | AssetId → MediaItemId; resolves the owning MediaItem from `AssetProcessingCompleted` (carries only AssetId) |
| `RecordTypeVersionDetailIndexProjector` | `media-catalog-record-type-index` | Published RecordType version tracking; queried by `MediaProfileDomainService` at publish time |
| `AssetRefProjector` | `media-catalog-asset-ref` | Asset state reference (Status, ContentType); maintained by `AssetStateReferenceProjector` |
| `VersionAssetRefProjector` | `media-catalog-version-asset-ref` | `MediaItemVersion → Asset` mapping; consumed by Catalog handlers resolving which asset backs a version |

> `CollectionNameIndexProjector`, `FolderChildCountIndexProjector`, `FolderNameScopeIndexProjector`, and `MediaItemTitleScopeIndexProjector` are superseded — name uniqueness is enforced via `INameReservationService` / `media-name-reservations`. Their backing tables (`collection-index`, `folder-name-index`, `media-item-title-scope-index`) are not provisioned.

#### 4b. Projectors.Search
**Host:** `src/hosts/Projectors.Search`
**Runtime:** Lambda triggered by SQS (`media-projector-search` queue, subscribed to `media-domain-events`)
**Responsibility:** Consume domain events and maintain OpenSearch indexes (`media-items`, `media-registrations`). Separate from `Projectors.ReadModel` so OpenSearch and DynamoDB projection pipelines scale, replay, and fail independently.

| Projector | Target Index | Notes |
|---|---|---|
| `MediaItemSearchProjector` | `media-items` | Full-text and faceted search on media items |
| `RegistrationSearchProjector` | `media-registrations` | Registration search and facet filtering |

Index aliases (`media-items-v1` → alias `media-items`) allow zero-downtime reindexing on schema changes. The `Projectors.Search` Lambda holds the index schema and manages alias swap on startup if a migration is pending.

### 5. Processing Worker
**Runtime:** Lambda (`Processing.Lambda`) triggered by SQS
**Responsibility:** Executes the two-stage asset pipeline — validation then full processing — publishing integration events; AssetManagement subscribes and applies all `Asset` aggregate transitions independently. No cross-BC command dispatch.

**Two-stage pipeline:**

**Stage 1 — `AssetValidationWorker`:** Triggered by `AssetUploadConfirmedIntegrationEvent` (from `media-processing` SQS queue, subscribed to `media-integration-events` SNS). Guarantees the object is in S3 at this point. Performs format check, size limit enforcement, and virus scan.
- Resolves `ProcessingJobId` via `AssetProcessingJobIndex` (AssetId → JobId).
- Dispatches `RecordProcessingJobScanResultCommand(outcome, ...)` — a Processing-owned command — which raises `ProcessingJobScanResultRecorded` → `ProcessingJobScanResultIntegrationEvent` published to SNS.
- AssetManagement `ProcessingJobScanResultEventHandler` subscribes and dispatches `RecordValidationResultCommand` to its own `Asset` aggregate, resolving `HasProcessingCapability` via `IMediaItemCapabilityService`.
- AssetManagement then publishes `AssetValidationPassedIntegrationEvent` (carrying `HasProcessingCapability`) or the appropriate failure event.

**Stage 2 — `AssetProcessingWorker`:** Triggered after `AssetIngestionSaga` dispatches `StartProcessingJobCommand` (on receiving `AssetValidationPassedIntegrationEvent` with `HasProcessingCapability = true`).
- `MediaItemId` null (standalone) or `HasProcessingCapability = true`: full pipeline runs
  - Image: Sharp/ImageMagick via Lambda layer
  - Video: MediaConvert job dispatch (async, completion via EventBridge → SQS)
  - Metadata: ExifTool via Lambda layer
- On success: dispatches `CompleteProcessingJobCommand` → `ProcessingJobSucceeded` → `ProcessingJobCompletedIntegrationEvent` → AM applies `CompleteAssetProcessingCommand`
- On failure: dispatches `FailProcessingJobCommand` → `ProcessingJobFailed` → `ProcessingJobFailedIntegrationEvent` → AM applies `FailAssetProcessingCommand`

**Does NOT** dispatch commands to AssetManagement directly — all cross-BC communication is via integration events on `media-integration-events` SNS.

### 6. SecuredSigning Adapter
**Runtime:** Lambda
**Responsibility:** Mediates all SecuredSigning API calls and webhook ingestion.

- Triggered by `SigningSessionInitiated` event on SQS
- Calls SecuredSigning eSign API to create an envelope, dispatches `RecordEnvelopeCreated` on success
- Receives SecuredSigning webhooks at `POST /integrations/secured-signing/webhook` (HMAC validated)
- On `envelope-completed`: downloads signed document, uploads to S3, dispatches `RecordSigningCompleted` + `RecordSignedAsset`
- **Does NOT** write to DynamoDB or publish to SQS directly

### 7. Integration Event Publishing (distributed, per-module)

**Runtime:** In-process with Command Handler (no separate Lambda)
**Responsibility:** Translate internal domain events into published-language `media.*` integration events and publish them to `media-integration-events`. See ADR-005.

**Pattern:** Each module in `src/modules/` owns one or more `*DomainEventMapper` classes in its `WriteModel/IntegrationEvents/Publishing/Mappers/` media-folder. They implement `IDomainEventMapper<TDomainEvent>` and are invoked inline by the Command Handler's domain event dispatch pipeline after the source event is successfully appended to the event store. See ADR-005 for the full pattern.

| Module | Mapper class | Source media-folder |
|---|---|---|
| AssetManagement | `AssetDomainEventMapper` | `modules/AssetManagement/AssetManagement.WriteModel/IntegrationEvents/Publishing/Mappers` |
| Processing | `ProcessingDomainEventMapper` | `modules/Processing/Processing.WriteModel/IntegrationEvents/Publishing/Mappers` |
| Catalog | `MediaItemDomainEventMapper`, `CollectionDomainEventMapper`, `FolderDomainEventMapper`, `MediaProfileDomainEventMapper` | `modules/Catalog/Catalog.WriteModel/IntegrationEvents/Publishing/Mappers` |
| ChangeRequests | `ChangeRequestDomainEventMapper` | `modules/ChangeRequests/ChangeRequests.WriteModel/IntegrationEvents/Publishing/Mappers` |
| Metadata | `RecordTypeDomainEventMapper` | `modules/Metadata/Metadata.WriteModel/IntegrationEvents/Publishing/Mappers` |
| Registration | `RegistrationDomainEventMapper` | `modules/Registration/Registrations.WriteModel/IntegrationEvents/Publishing/Mappers` |

**Responsibilities (each mapper):**
- Implement `IDomainEventMapper<TDomainEvent>` for every domain event that maps to an integration event.
- Build the corresponding `media.*` message record (an `IntegrationEvent`-derived `record` in the module's `.Events` contracts project).
- Apply catalog-declared filters inline (e.g. `AssetDomainEventMapper` suppresses `media.asset.processing-completed` when the owning MediaItem's MediaProfile lacks the `Processing` capability, resolved from the `media-items` read model).
- Publish via `IMessageBus.PublishAsync(...)`. The `IMessageBus` implementation (AWS.Messaging wrapper) resolves the target SNS topic from the registered mapper mapping and stamps SNS message attributes (`TenantId`, `EventType`, `AggregateId`, `AggregateVersion`, `CorrelationId`, `OwnerId`).

**Do NOT:**
- Write to DynamoDB or any read model (projections are separate handlers).
- Dispatch commands.
- Consume from any queue (outbound translators only).

**Idempotency:** `EventId` is stamped deterministically from `(AggregateId, AggregateVersion, eventType)` so that handler re-dispatch produces the same integration-event ID and downstream consumers can de-dupe.

**Catalog alignment:** A unit test per module asserts that every `IntegrationEvent`-derived type registered in DI is present in the Integration Event Catalog (and vice versa), to catch drift.

### 8. Integration Event Consumers Lambda
**Runtime:** Lambda triggered by SQS (`media-cross-module-events`)
**Responsibility:** Intra-BC consumption of `media.*` integration events — lets modules react to *other modules'* integration events without coupling to their internal domain events.

- Subscribes to `media-integration-events` via the `media-cross-module-events` SQS queue.
- Dispatches follow-up commands or writes module-local reference indexes; does not publish integration events.

**Active consumers** (registered in `ConsumerRegistrations.cs`):

| Consumer class | Subscribes to | Action |
|---|---|---|
| `MediaItemCreatedEventHandler` | `MediaItemCreatedIntegrationEvent` | Materialises `MediaItemCapabilityIndex` in AssetManagement |
| `MediaItemArchivedEventHandler` | `MediaItemArchivedIntegrationEvent` | Marks media-item archived in `MediaItemCapabilityIndex` |
| `ProcessingJobStartedEventHandler` | `ProcessingJobStartedIntegrationEvent` | Dispatches `StartAssetProcessing` → raises `AssetProcessingStarted` on Asset aggregate |
| `ProcessingJobCompletedEventHandler` | `ProcessingJobCompletedIntegrationEvent` | Dispatches `CompleteAssetProcessing` → raises `AssetProcessingCompleted`, stamps renditions + metadata |
| `ProcessingJobFailedEventHandler` | `ProcessingJobFailedIntegrationEvent` | Dispatches `FailAssetProcessing` → raises `AssetProcessingFailed` |
| `CollectionArchivedEventHandler` | `CollectionArchivedIntegrationEvent` | Fan-out archive to all media-folders and media-items in the media-collection |
| `RegistrationInitiatedEventHandler` | `RegistrationInitiatedIntegrationEvent` | Updates media-item media-registration count index in Catalog |
| `RecordTypePublishedEventHandler` | `RecordTypePublishedIntegrationEvent` | Tracks published RecordType version in Catalog reference index |
| `RecordTypeDeprecatedEventHandler` | `RecordTypeDeprecatedIntegrationEvent` | Marks RecordType deprecated in Catalog reference index |
| `MediaItemSubmittedForReviewEventHandler` | `MediaItemSubmittedForReviewIntegrationEvent` | Dispatches `CreateChangeRequest` in ChangeRequests module |
| `ChangeRequestCreatedEventHandler` | `ChangeRequestCreatedIntegrationEvent` | Materialises `ChangeRequestReference` in Catalog with `Status = Open`; queried by `ApproveMediaItemHandler` when `ReviewPolicy = RequiredForPublish` |
| `ChangeRequestApprovedEventHandler` | `ChangeRequestApprovedIntegrationEvent` | Updates `ChangeRequestReference` status → `Approved` |
| `ChangeRequestRejectedEventHandler` | `ChangeRequestRejectedIntegrationEvent` | Updates `ChangeRequestReference` status → `Rejected` |
| `ChangeRequestAbandonedEventHandler` | `ChangeRequestAbandonedIntegrationEvent` | Updates `ChangeRequestReference` status → `Abandoned` |
| `MediaItemRegistrationContextCreatedEventHandler` | `MediaItemCreatedIntegrationEvent` | Materialises `MediaItemRegistrationContext` in Registration module |
| `MediaItemRegistrationContextApprovedEventHandler` | `MediaItemApprovedIntegrationEvent` | Updates media-registration context on media-item approval |
| `MediaItemRegistrationContextArchivedEventHandler` | `MediaItemArchivedIntegrationEvent` | Marks media-registration context archived on media-item archive |

> **Note:** `MediaItemCreatedIntegrationEvent` and `MediaItemArchivedIntegrationEvent` each fan out to two independent consumers (AssetManagement + Registration). AWS.Messaging dispatches both handlers per message. `ChangeRequestCreatedIntegrationEvent` fans out to two consumers (Catalog index writer + `ChangeRequestCreatedSagaHandler` in ChangeRequests).

### 9. SagaOrchestrator Lambda
**Runtime:** Lambda triggered by SQS (`media-sagas`)
**Responsibility:** Manages long-running cross-aggregate workflows by consuming integration events from `media-integration-events`. Persists saga state to the `media-sagas` DynamoDB table.

**Why integration events, not domain events:** Integration events are versioned, stable contracts — the saga is isolated from internal domain event shape changes. The `MediaItemReviewSaga` spans the ChangeRequests and Catalog bounded contexts; subscribing to their domain events directly would couple the orchestrator to internal BC implementations and violate context isolation.

Two active media-sagas:

**`AssetIngestionSaga`** — coordinates the asset upload → validate → process → activate pipeline.

| Handler | Subscribes to | Action |
|---|---|---|
| `ProcessingJobCreatedSagaHandler` | `ProcessingJobCreatedIntegrationEvent` | Records job correlation on saga state |
| `AssetValidationPassedSagaHandler` | `AssetValidationPassedIntegrationEvent` | Advances saga; dispatches `BypassProcessingJobCommand` (no `Processing` capability) or `StartProcessingJobCommand` (capable) |
| `AssetProcessingCompletedSagaHandler` | `AssetProcessingCompletedIntegrationEvent` | Marks saga `Completed` |
| `AssetProcessingFailedSagaHandler` | `AssetProcessingFailedIntegrationEvent` | Marks saga `Failed` |

**`MediaItemReviewSaga`** — coordinates the review lifecycle initiated when a MediaItem is submitted for review.

| Handler | Subscribes to | Action |
|---|---|---|
| `ChangeRequestCreatedSagaHandler` | `ChangeRequestCreatedIntegrationEvent` | Creates saga state; starts review timeout |
| `MediaChangeRequestApprovedSagaHandler` | `ChangeRequestApprovedIntegrationEvent` | Marks saga `Completed` |
| `MediaChangeRequestRejectedSagaHandler` | `ChangeRequestRejectedIntegrationEvent` | Marks saga `Completed` (rejected) |
| `MediaChangeRequestAbandonedSagaHandler` | `ChangeRequestAbandonedIntegrationEvent` | Marks saga `Abandoned` |

**`SagaTimeoutScanner` Lambda** (separate host) — queries the `media-sagas` DynamoDB table via
the `SagaTypeByTimeout` GSI for active saga entries past `TimeoutAt` and dispatches the appropriate
compensation command for each. Runs on a 5-minute EventBridge schedule.

**Host:** `Media.SagaTimeoutScanner.Lambda`
**Runtime:** Lambda (containerised), triggered by EventBridge Scheduler
**Schedule:** Every 5 minutes (`rate(5 minutes)`)
**Memory:** 256 MB | **Timeout:** 5 minutes
**Safety buffer:** Scanner aborts a query page loop if Lambda remaining time < 15 s; un-processed
items are handled on the next invocation.

#### Saga Timeout Durations

| Saga | State scanned | Timeout | Rationale | Clock starts | Reset on transition? | Compensation command |
|------|---------------|---------|-----------|--------------|----------------------|----------------------|
| `AssetIngestionSaga` | `AwaitingValidation` | **30 minutes** | ClamAV virus scan + format check on large files (up to 2 GB) should complete in < 5 min under normal load; 30 min provides a 6× safety margin for Lambda cold starts, S3 latency, and queue backlog during burst ingestion. | `ProcessingJobCreated` event received | No — single shared clock | `FailAssetProcessingCommand(ValidationTimeout)` directly on Asset aggregate + `FailProcessingJobCommand` to clean up the job |
| `AssetIngestionSaga` | `ProcessingDispatched` | **Same 30-minute clock** (no reset on transition) | The 30-minute window is shared across the entire pipeline (validation + processing combined). Image/audio processing typically finishes in seconds; video MediaConvert jobs for SD content < 10 min. The shared clock caps the worst-case end-to-end wait a caller experiences. Video jobs > 30 min are handled by MediaConvert async callbacks and should complete well within budget for typical file sizes. | `ProcessingJobCreated` event received | N/A | `FailProcessingJobCommand(ProcessingTimeout)` → propagates to `FailAssetProcessingCommand` via integration event consumer |
| `MediaItemReviewSaga` | `AwaitingReview` | **14 days** | Review cycles for media assets typically close within 1–3 business days; 14 days provides headroom for reviewer holidays or approval queues. After 14 days, the saga marks itself `Abandoned` and the ChangeRequests domain raises `ChangeRequestAbandoned`, which triggers `RejectMediaItem(reason: "ReviewTimeout")` on the Catalog aggregate. The owner may resubmit to start a new review cycle. | MCR created (`ChangeRequestCreatedSagaHandler`) | No — review clock does not reset on reviewer reassignment or comment activity | `FailMediaItemReviewCommand(ReviewTimeout)` via `SagaTimeoutScanner` (future implementation) |

**Key design decision:** `AssetIngestionSaga.TimeoutAt` is set once when the saga is created (on `ProcessingJobCreated`)
and never reset when the saga transitions from `AwaitingValidation` to `ProcessingDispatched`. The
30-minute window therefore covers the *entire* pipeline — validation + processing combined. A saga
that validates in 2 minutes still has only ~28 minutes left for processing.

**Warning window:** The scanner publishes a `SagasApproachingTimeout` CloudWatch metric for sagas
whose `TimeoutAt` is within 6 minutes of expiry (20 % of the 30-minute budget). A CloudWatch alarm
fires when this count ≥ 1, giving operators advance warning before compensation runs.

**`MediaItemReviewSaga`** timeout scanning is not yet implemented; the 14-day timeout defined above will be enforced once the `SagaTimeoutScanner` is extended to cover `MediaItemReviewSaga`. Until then, stale review sagas must be manually identified and resolved.

### 10. BulkFolderImportWorker Lambda
**Host:** `Workers.BulkFolderImport`
**Runtime:** Lambda triggered by SQS (`media-bulk-folder-imports` queue, subscribed to `media-integration-events`)
**Responsibility:** Processes async large-volume folder import jobs. Consumes `BulkFolderImportJobCreatedMessage`, parses input (line-delimited paths, CSV, or JSON), splits into chunks of 200, dispatches `BulkCreateFoldersByPathCommand` per chunk, records per-item results to `media-bulk-import-job-items`, advances job state.

**Processing flow:**
1. Load input (from S3 if `InputStorageKey` present, else inline from job aggregate)
2. Parse input per `InputFormat` (line-delimited, CSV, JSON)
3. Split into chunks of 200 (per `MaxFoldersPerRequest`)
4. For each chunk:
   - Dispatch `BulkCreateFoldersByPathCommand` (existing handler — no changes needed)
   - Collect `succeeded`/`failed` results from partial success envelope
   - Dispatch `RecordBulkFolderImportJobBatchResultCommand`
   - Write per-item results to `media-bulk-import-job-items` via `BatchWriteItem`
5. After all chunks: dispatch `CompleteBulkFolderImportJobCommand` (or `FailBulkFolderImportJobCommand` on fatal error)

**Visibility timeout:** 900 seconds (15 min — chunk processing + DynamoDB writes)
**Max receive count:** 3
**Batch size:** 1 (one job per invocation — job internally chunks to 200)

### 11. BulkMediaImportWorker Lambda
**Host:** `Workers.BulkMediaImport`
**Runtime:** Lambda triggered by SQS (`media-bulk-media-imports` queue, subscribed to `media-integration-events`)
**Responsibility:** Processes async large-volume media item imports. Coordinates multi-phase pipeline: upload → validation → cataloging → processing. Consumes `BulkMediaImportJobCreatedMessage`, issues pre-signed S3 upload URLs, waits for client confirmations, subscribes to validation/processing events, catalogs MediaItems in batches of 50, records per-item results, advances job state through phases.

**Multi-phase state machine:**

**Phase 1 — Issue Upload URLs:**
1. Load manifest (from S3 if `InputStorageKey` present)
2. Parse manifest per `InputFormat` (JSON or CSV)
3. Generate `AssetId` per item (UUID v7)
4. Dispatch `UploadAssetCommand` per item → returns pre-signed S3 URL
5. Write upload URLs to `media-bulk-import-upload-urls` (temp table, TTL 24h)
6. Dispatch `StartBulkMediaImportJobUploadsCommand`

Client uploads assets, then calls `POST /v1/catalog/import-jobs/{jobId}/confirm-uploads`.

**Phase 2 — Validation:**
1. Wait for all upload confirmations (tracked via `UploadedCount`)
2. Dispatch `StartBulkMediaImportJobValidationCommand`
3. Subscribe to `AssetValidationPassedIntegrationEvent` and `AssetValidationFailedIntegrationEvent`
4. Accumulate results, dispatch `RecordBulkMediaImportJobValidationResultsCommand` per batch
5. After all validations: dispatch `StartBulkMediaImportJobCatalogingCommand`

**Phase 3 — Cataloging:**
1. Split validated assets into chunks of 50 (per `MaxMediaItemsPerRequest`)
2. For each chunk:
   - Dispatch `BulkCreateMediaItemsCommand` (new command — see MediaItem write model)
   - Collect results
   - Dispatch `RecordBulkMediaImportJobCatalogingResultsCommand`
3. After all chunks: dispatch `StartBulkMediaImportJobProcessingCommand`

**Phase 4 — Processing:**
1. Subscribe to `ProcessingJobCompletedIntegrationEvent` and `ProcessingJobFailedIntegrationEvent`
2. Accumulate results per asset
3. Dispatch `RecordBulkMediaImportJobProcessingResultsCommand` per batch
4. After all processing complete: dispatch `CompleteBulkMediaImportJobCommand`

**Visibility timeout:** 1800 seconds (30 min — multi-phase processing)
**Max receive count:** 3
**Batch size:** 1

### 12. StorageTierTransitionScanner Lambda
**Host:** `Media.StorageTierTransitionScanner.Lambda`
**Runtime:** Lambda (containerised), triggered by EventBridge Scheduler
**Schedule:** Daily at 00:30 UTC (`cron(30 0 * * ? *)`)
**Memory:** 256 MB | **Timeout:** 15 minutes
**Responsibility:** Keeps `Asset.StorageTier` in the domain in sync with the actual S3 storage class, which transitions silently via the `media-source` bucket lifecycle policy.

**Why it exists:** S3 lifecycle transitions do not publish events. The `Asset` aggregate tracks `StorageTier` as the last-confirmed class, but transitions happen autonomously in S3. Without this scanner, `StorageTier` would permanently read `Standard` for all assets regardless of their actual class.

**Query strategy:** DynamoDB parallel Scan on `media-assets` (the asset summary table) with `TotalSegments = 10`. Uses a `FilterExpression` to identify assets whose recorded `StorageTier` is behind the tier implied by their `CreatedAt` date. `media-assets` is used in preference to `media-asset-detail` because the summary record is smaller (no renditions, metadata), reducing consumed read capacity on the scan.

**Scan thresholds:**

| Condition                                                                     | Target tier      |
| ----------------------------------------------------------------------------- | ---------------- |
| `StorageTier = Standard` AND `CreatedAt < now − 90d`                          | `StandardIA`     |
| `StorageTier IN [Standard, StandardIA, Glacier]` AND `CreatedAt < now − 365d` | `GlacierInstant` |
| `StorageTier != DeepArchive` AND `CreatedAt < now − 730d`                     | `DeepArchive`    |

`Glacier` is included in the 365d check as the legacy alias for `GlacierInstant` — assets that recorded a tier transition before the enum was renamed should not be re-transitioned unnecessarily. The 730d check targets any non-DeepArchive asset (covers all states the legacy `Glacier` value can represent).

**Status filter:** Skips assets with `Status IN [Pending, MultipartAborted, ContainsVirus]` — these have no durable S3 object in `media-source`. All other statuses (Active, Archived, Validating, ValidationFailed, Processing, ProcessingFailed, Deleted) retain their S3 object until a lifecycle deletion rule removes it.

**Dispatch:** For each stale asset, dispatches `RecordStorageTierTransitionCommand(TenantId, AssetId, targetTier, now)` via the internal command dispatcher. The command is idempotent — the aggregate emits no event if `StorageTier` already equals `NewTier`.

**Pagination:** Uses DynamoDB `ExclusiveStartKey` continuation. If the 15-minute Lambda timeout is approached before the scan completes, the remaining work is deferred to the next daily run — a one-day lag is acceptable. For very large tables (> ~50M assets), consider increasing `TotalSegments` or moving to a fan-out pattern (one Lambda per segment, coordinated by Step Functions).

**IAM:** Read access to `media-assets` DynamoDB table; dispatch access to the internal command bus (in-process, no additional IAM required beyond DynamoDB).

---

## Infrastructure

### DynamoDB Tables

**Event store:**

| Table | Partition Key | Sort Key | Purpose |
|---|---|---|---|
| `media-events` | `TENANT#{TenantId}#{AggregateId}` | `AggregateVersion` | Event store — all aggregates (append-only). `TenantId` also stored as plain attribute. |
| `media-sagas` | `TENANT#{TenantId}` | `SAGA#{SagaType}#{SagaId}` | Saga state persistence for `SagaOrchestrator` Lambda. Composite key — corrected 2026-06-17; this row previously omitted the SK, but CDK (`event-store.construct.ts`) has always provisioned PK+SK. |

**Query-facing read models:**

| Table | Partition Key | Sort Key | Purpose |
|---|---|---|---|
| `media-collections` | `TENANT#{TenantId}#COLLECTIONS` | `SUMMARY#{CollectionId}` | Collection summary list — category-partitioned (one shared partition per tenant per entity type; entity id lives in SK). |
| `media-collection` | `TENANT#{TenantId}#COLLECTION` | bare `{CollectionId}` | Full media-collection detail + root media-folder refs. Category-partitioned. |
| `media-folders` | `TENANT#{TenantId}#FOLDERS` | bare `{FolderId}` | Folder summary list. Category-partitioned (no custom schema class — default schema uses bare discriminator as SK). |
| `media-folder` | `TENANT#{TenantId}#FOLDER` | bare `{FolderId}` | Folder detail + child media-folder refs. Category-partitioned. |
| `media-folder-children` | `TENANT#{TenantId}#CHILDREN` | `SUMMARY#{FolderId}` | Active immediate child-folder summaries per parent folder (`FolderChildSummarySchema`). Category-partitioned. |
| `media-items` | `TENANT#{TenantId}#ITEMS` | bare `{MediaItemId}` | MediaItem summary — all GSIs on this table. Category-partitioned. |
| `media-item` | `TENANT#{TenantId}#ITEM` | bare `{MediaItemId}` | Full media-item detail, metadata, role assignments. Category-partitioned. |
| `media-item-versions` (Summary) | `TENANT#{TenantId}#ITEM_VERSIONS` | `SUMMARY#{discriminator}` | Version summary list (`MediaItemVersionSummarySchema`). Shares table + partition with the Detail row below; `SUMMARY#` vs `DETAIL#` SK prefix prevents collision — confirmed, no bug. |
| `media-item-versions` (Detail) | `TENANT#{TenantId}#ITEM_VERSIONS` | `DETAIL#{discriminator}` | Full snapshot per approved version (`MediaItemVersionDetailSchema`). Same partition as Summary row above. |
| `media-assets` | `TENANT#{TenantId}#ASSETS` | `SUMMARY#{AssetId}` | Asset summary list per media-item. Category-partitioned (`AssetSummarySchema`, category `ASSETS`). Includes `StorageTier` and `CreatedAt` attributes (required by `StorageTierTransitionScanner`). |
| `media-asset` | `TENANT#{TenantId}#ASSET#{AssetId}` | constant `DETAIL` | Full asset detail, renditions, metadata. Registered via default schema with category `ASSET` and `AssetId` as groupKey — an inversion of the usual Detail pattern (compare `media-collection`/`media-folder`, which put the category alone in PK and the bare entity id in SK): here the literal `"DETAIL"` is the SK discriminator and `AssetId` is folded into the PK via groupKey. Functionally correct (PK still unique per asset), same inversion convention as `media-catalog-asset-item-index`/`media-catalog-asset-ref` below — just non-obvious. |
| `media-registrations` | `TENANT#{TenantId}#REGISTRATIONS` | `SUMMARY#{RegistrationId}` | Registration summary list per media-item. Category-partitioned (`RegistrationSummarySchema`, category `REGISTRATIONS`). |
| `media-registration` | `TENANT#{TenantId}#REGISTRATION#{RegistrationId}` | constant `DETAIL` | Full media-registration detail including media-items and amendments. Same inverted Detail convention as `media-asset` above — literal `"DETAIL"` is the SK, `RegistrationId` is folded into the PK via groupKey (category `REGISTRATION`). |
| `media-record-types` (Summary) | `TENANT#{TenantId}#RECORD_TYPES` | `SUMMARY#{RecordTypeId}` | RecordType summary list, category-partitioned (`RecordTypeSummarySchema`, schemaIdentifier `RECORD_TYPES`). Powers `ListRecordTypesQuery` via `RecordTypeByNameIndex` GSI. |
| `media-record-types` (Version Detail — anomaly) | `TENANT#{TenantId}#RECORD_TYPES#{Version:D10}` | `VERSION#{RecordTypeId}` | `RecordTypeVersionDetailReadModel`/`RecordTypeVersionDetailSchema` is also registered against this table (not against `media-record-type-versions`, its sibling Summary model's table). Does not collide with the Summary rows above — its PK always carries a version-number groupKey suffix, so it lands in its own partition per version, distinct from the bare `TENANT#{TenantId}#RECORD_TYPES` Summary partition. But it scatters one partition per published version across what's otherwise a one-partition-per-tenant Summary table, and matches neither established precedent in this codebase: not co-located with its own Summary sibling on `media-record-type-versions` (the `media-item-versions` pattern), nor split into its own dedicated table (the `media-profile-version` fix). Git history (commit `eba2790`, 2026-05-07) shows this was a deliberate choice when `RecordTypeVersionDetailReadModel` was introduced to fix `GetRecordTypeVersionQuery` returning the wrong shape — the developer explicitly closed out a pre-existing "review RecordTypeVersion summary and detail" backlog note in the same commit. However, the only spec doc describing this design (`spec/contexts/Metadata/aggregates/RecordType/recordtype.read-model.md`) is itself stale — it still references a `RecordTypeVersionSnapshotReadModel` type removed in that same commit, and was never updated for the later `media-record-type-versions` table split. **Needs a decision from Chase/Karen: leave as-is (with the doc and this anomaly note as the record of intent), move `RecordTypeVersionDetailReadModel` onto `media-record-type-versions` (mirrors `media-item-versions`), or give it a dedicated `media-record-type-version` table (mirrors the `media-profile-version` fix). Not changed here — app-code/table-targeting change is out of this audit's scope.** |
| `media-record-type` | `TENANT#{TenantId}#RECORD_TYPE#{RecordTypeId}` | constant `DETAIL` | Full RecordType detail including draft state. Registered via default schema, category `RECORD_TYPE`. Same inverted Detail convention as `media-asset`/`media-registration` — literal `"DETAIL"` is the SK, `RecordTypeId` is folded into the PK via groupKey. |
| `media-record-type-versions` | `TENANT#{TenantId}#RECORD_TYPE_VERSIONS#{RecordTypeId}` | bare `{Version:D10}` | RecordType version summary list, registered via default schema (category `RECORD_TYPE_VERSIONS`, no custom schema class — bare discriminator as SK). Powers `ListRecordTypeVersionsQuery` via `RecordTypeVersionsByRecordTypeIndex` GSI. Does **not** host the Version Detail rows — see anomaly note on `media-record-types` above. |
| `media-profile` | `TENANT#{TenantId}#PROFILE` | bare `{MediaProfileId}` | Full MediaProfile detail including draft state. Category-partitioned. Also hosts the `MediaProfileByNameIndex` GSI (intentional — see GSI notes below). |
| `media-profiles` | `TENANT#{TenantId}#PROFILES` | bare `{MediaProfileId}` | MediaProfile summary list. Category-partitioned. |
| `media-profile-versions` (Summary) | `TENANT#{TenantId}#PROFILE_VERSIONS` | bare `{discriminator}` | Version summary list (`MediaProfileVersionSummarySchema`). Own dedicated table — mirrors the `media-profile`/`media-profiles` Detail/Summary split. |
| `media-profile-version` (Detail) | `TENANT#{TenantId}#PROFILE_VERSION` | bare `{discriminator}` | Full asset/capability snapshot per published version (`MediaProfileVersionDetailSchema`). Own dedicated table, separate from Summary's `media-profile-versions`. **Fixed 2026-06-16:** previously both Summary and Detail were registered against the same table (`media-profile-versions`) with mismatched category strings (`PROFILE_VERSIONS` vs `PROFILE_VERSION`), splitting them into two orphaned partitions on one table. Corrected by adding a new CDK table `media-profile-version` and repointing the Detail registration in `Catalog.ReadModel.Infrastructure/ServiceCollectionExtensions.cs` at it — now each schema owns its own table, consistent with every other Detail/Summary pair in Catalog except the shared-table `media-item-versions` pattern. |
| `media-change-requests` | `TENANT#{TenantId}#CHANGE_REQUESTS` | `SUMMARY#{ChangeRequestId}` | Change request summary list, category-partitioned (`ChangeRequestSummarySchema`, category `CHANGE_REQUESTS`). Hosts the `ChangeRequestByMediaItemIndex`/`ChangeRequestByOwnerIndex` GSIs (see GSI notes below). |
| `media-change-request` | `TENANT#{TenantId}#CHANGE_REQUEST#{ChangeRequestId}` | constant `DETAIL` | Full change request detail including reviewer decisions. Registered via default schema (category `CHANGE_REQUEST`) with `ChangeRequestId` as groupKey — same inverted Detail convention as `media-asset`/`media-registration`/`media-record-type` above: literal `"DETAIL"` is the SK, the entity id is folded into the PK via groupKey. |
| `media-change-request-comments` | `TENANT#{TenantId}#CHANGE_REQUEST#{ChangeRequestId}` (groupKey form) | `COMMENT#{CommentId}` | Threaded comments per change request (`ChangeRequestCommentSchema`, category `CHANGE_REQUEST`). Same groupKey/discriminator shape as the Detail table above but a distinct table. Note: `ChangeRequestCommentReadModel`'s own XML doc comment is stale — it claims PK `TENANT#{TenantId}#PROJECTION#ReviewCommentReadModel` / SK `{ChangeRequestId}#{CommentId}`, neither of which matches this verified shape; app-code comment issue only, not touched. |
| `media-processing-jobs` | `TENANT#{TenantId}#PROCESSING_JOBS` | `SUMMARY#{JobId}` | ProcessingJob summary list (`ProcessingJobSummarySchema`, category `PROCESSING_JOBS`). Category-partitioned, matches the established Summary pattern across every other module. Hosts the `AssetByProcessingJobIndex` GSI (see GSI notes below). |
| `media-processing-job` | `TENANT#{TenantId}#PROCESSING_JOB#{JobId}` | constant `DETAIL` | Full processing job detail — renditions, extracted metadata, failure reason. Registered via default schema with category `PROCESSING_JOB` and `JobId` as groupKey — same inverted Detail convention as `media-asset`/`media-registration`/`media-record-type`/`media-change-request`: literal `"DETAIL"` is the SK, `JobId` is folded into the PK via groupKey. Note: this read model's own XML doc comment is stale — it claims PK `TENANT#{TenantId}` / SK `JOB#{JobId}`, which matches neither the verified `ProcessingJobDetailReadModel.CreateProjectionKey` behavior nor the `DefaultProjectionSchema` base it relies on; app-code comment issue only, not touched. |
| `media-signing-session` | `TENANT#{TenantId}#{SigningSessionId}` | — | Full signing session detail. |
| `media-signing-sessions` | `TENANT#{TenantId}#{SigningSessionId}` | — | Signing session summary list. ⚠️ `SigningSessionSummaryProjector` not implemented. |
| `media-bulk-folder-import-jobs` | `JobId` | — | Folder import job summary with progress tracking. GSI1: TenantId+CreatedAt, GSI2: CollectionId+CreatedAt. |
| `media-bulk-folder-import-job-detail` | `JobId` | — | Full folder import job detail including input payload or S3 key reference. |
| `media-bulk-media-import-jobs` | `JobId` | — | Media import job summary with multi-phase progress tracking. GSI1: TenantId+CreatedAt, GSI2: CollectionId+CreatedAt. |
| `media-bulk-media-import-job-detail` | `JobId` | — | Full media import job detail including manifest reference and upload URL table pointer. |
| `media-bulk-import-job-items` | `TENANT#{TenantId}#JOB#{JobId}` | `ITEM#{Index}` | Per-item results for all bulk import jobs (shared). Supports both folder and media imports with `JobType` discriminator. |
| `media-bulk-import-upload-urls` | `TENANT#{TenantId}#JOB#{JobId}` | `ITEM#{Index}` | Temporary pre-signed upload URLs for media imports. TTL 24h. |

> All query-facing read model tables store `TenantId` as a plain attribute in addition to the `TENANT#` PK prefix (for observability / scan convenience).

**Write-side reference indexes** (command handler constraint enforcement — not query-facing):

| Table | Partition Key | Sort Key | Purpose |
|---|---|---|---|
| `media-catalog-folder-registration-index` | `TENANT#{TenantId}#MEDIA_ITEM` | bare `{MediaItemId}` | ActiveRegistrationCount per media item (folder-subtree queries assembled at the service layer — see code comment on `FolderRegistrationIndex`). |
| `media-catalog-folder-folders-index` | `TENANT#{TenantId}#FOLDER` | bare `{ParentId}` (FolderId or CollectionId) | Direct child folder IDs per parent (folder or collection root). |
| `media-catalog-folder-items-index` | `TENANT#{TenantId}#MEDIA_ITEM` | bare `{FolderId}` | MediaItem IDs per folder. |
| `media-catalog-profile-index` | `TENANT#{TenantId}#MEDIA_PROFILE` | bare `{MediaProfileId}` | Compiled MediaProfile capability snapshot. |
| `media-catalog-item-profile-index` | `TENANT#{TenantId}#MEDIA_PROFILE` | bare `{MediaProfileId}` | MediaItem IDs pinned to each MediaProfile. |
| `media-catalog-asset-item-index` | `TENANT#{TenantId}#ASSET#{AssetId}` | constant `ASSET` | AssetId → MediaItemId lookup. Note: `ProjectionKey` is constructed with the literal `"ASSET"` as the SK discriminator and `AssetId` as the PK groupKey — an inversion of the usual discriminator/groupKey usage, but correct (PK is still unique per asset). |
| `media-catalog-record-type-index` | version rows: `TENANT#{TenantId}#RECORD_TYPE#{RecordTypeId}`; deprecation sentinel: `TENANT#{TenantId}#RECORD_TYPE#DEPRECATED` | version rows: bare `{Version:D10}`; sentinel: bare `{RecordTypeId}` | Published RecordType version tracking. ⚠️ Two distinct partition strategies share one table: per-RecordType partitions hold one row per published version (SK = zero-padded version), while a single tenant-wide `DEPRECATED` partition holds one sentinel row per deprecated RecordType (SK = RecordTypeId). Intentional per code comments, but worth calling out explicitly since it's not derivable from the table name alone. |
| `media-catalog-asset-ref` | `TENANT#{TenantId}#ASSET#{AssetId}` | constant `STATE` | Asset state reference (Status, ContentType). Same discriminator/groupKey inversion pattern as `media-catalog-asset-item-index` above. |
| `media-catalog-version-asset-ref` | `TENANT#{TenantId}#VERSION` | bare `{MediaItemId}#{VersionNumber}` | `MediaItemVersion → Asset` mapping. |
| `media-asset-item-capability-ref` | `TENANT#{TenantId}#MEDIA_ITEM#{MediaItemId}` | constant `CAPABILITY` | MediaItem capability reference snapshot for AssetManagement command handlers (`MediaItemCapabilityReference`). |
| `media-asset-profile-default-ref` | `TENANT#{TenantId}#PROFILE_DEFAULT#{AssetId}` | constant `PROFILE_DEFAULT` | Default MediaProfile reference per asset (`AssetProfileDefaultReference`). Registration category and instance discriminator are both the literal string `"PROFILE_DEFAULT"` — same string used for two different purposes, just a naming coincidence, not a bug. |
| `media-processing-asset-index` | `TENANT#{TenantId}#ASSET` | bare `{AssetId}` | Current ProcessingJob state per asset (`AssetProcessingJobIndex`) — AssetId → active job status/timestamps; guards duplicate job submission and feeds `AssetJobIndexProjector`. Registered via default schema (category `ASSET`, no groupKey, `AssetId` as discriminator) — note this is *not* the same inverted convention seen elsewhere (no groupKey is used here at all; every asset's row lands in the single tenant-wide `ASSET` partition, distinguished only by SK). Verified against `AssetProcessingJobIndex.CreateProjectionKey`/`AssetJobIndexProjector`. |
| `media-registration-item-ref` | `TENANT#{TenantId}#MEDIA_ITEM#{MediaItemId}` | constant `STATE` | MediaItem reference for Registration command handlers (`MediaItemReference`). |
| `media-name-reservations` | — | — | Two-tier name uniqueness — transactionally written alongside aggregate creation events. Not yet re-verified. |
| `media-folder-locks` | — | — | Distributed per-collection lock for concurrent folder creation (TTL 1 min, `ExpiresAt` attribute). Not yet re-verified. |

> CDK's `write-indexes.construct.ts` doc-comments above each table declaration (e.g. `catalogFolderRegistrationIndex`, `catalogFolderFoldersIndex`, `catalogAssetRef`) currently describe PK shapes that don't match the verified patterns above (e.g. claim `TENANT#{TenantId}#{FolderId}` where the real category is `MEDIA_ITEM` or `FOLDER`, not the literal field name). These are comments only — the actual `partitionKey`/`sortKey` attribute names and types (`PK`/`SK`, both String) are correct and need no CDK change — but the comments are stale and worth a follow-up cleanup pass in `cdk-magiq-media`.

> `collection-index`, `folder-name-index`, and `media-item-title-scope-index` are superseded — name uniqueness is enforced via `media-name-reservations`.

**GSIs:**

- `media-items` (corrected 2026-06-17 — matches CDK `read-models.construct.ts`; `FolderItemsIndex`/`UnassignedIndex`/`OwnerStatusIndex`/`ProfileIndex` did not exist in CDK and have been removed):
  - `MediaItemByFolderIndex` (`GSI1PK`/`GSI1SK`) — sparse; assigned media-items only (populated when `FolderId` is set). `GSI1PK` = `TENANT#{TenantId}#FOLDER#{FolderId}#ITEMS`, `GSI1SK` = `{Title}#{MediaItemId}`. Powers `ListMediaItemsQuery`, alphabetical by title.
  - **`MediaItemUnassignedByOwnerIndex` removed 2026-06-17:** previously documented here as a second confirmed GSI (`GSI2PK`/`GSI2SK`, powering `ListUnassignedMediaItemsQuery`). CDK did provision it, but no corresponding application code (`MediaItemUnassignedByOwnerIndexSchema`, `ListUnassignedMediaItemsQuery`/handler) exists in `magiq-media`'s `develop` branch — the only implementation was found in a stale, prunable agent worktree (`claude/cranky-gould-ce427c`) that was never merged. Dropped from CDK as orphaned infra; `media-items` now has exactly one GSI. Re-add here if/when `ListUnassignedMediaItems` ships for real.
- `media-collections`:
  - `CollectionByNameIndex` (`GSI1PK`/`GSI1SK`) — collection lookup by normalized name.
  - `PublicCollectionByNameIndex` (`GSI2PK`/`GSI2SK`) — sparse; `Visibility=Public` collections only. Powers public media-collection discovery. The previously documented `VisibilityIndex` (Visibility + CreatedAt) does not exist in code or CDK — removed as stale/fictional.
- `media-assets`: `AssetByMediaItemIndex` (`AssetByMediaItemIndexSchema`) — `GSI1PK` only, sparse, no sort key. `GSI1PK` = `TENANT#{TenantId}#ITEM#{MediaItemId}#ASSETS`. Powers `ListAssetsByMediaItemQuery`; status filtering done in-memory, not via GSI.
- `media-registrations`:
  - `RegistrationByMediaItemIndex` (`RegistrationByMediaItemIndexSchema`) — `GSI1PK`/`GSI1SK`. `GSI1PK` = `TENANT#{TenantId}#ITEM#{MediaItemId}#REGISTRATIONS`, `GSI1SK` = `{InitiatedAt:O}#{RegistrationId}` (reverse-chrono). Powers `ListRegistrationsByMediaItemQuery`.
  - `RegistrationByOwnerIndex` (`RegistrationByOwnerIndexSchema`) — `GSI2PK`/`GSI2SK`. `GSI2PK` = `TENANT#{TenantId}#OWNER#{OwnerId}#REGISTRATIONS`, `GSI2SK` = `{InitiatedAt:O}#{RegistrationId}`. Powers `ListRegistrationsByOwnerQuery`.
  - The previously documented `StatusIndex` (Status + SubmittedAt) does not exist in code or CDK — removed as stale/fictional.
- `media-record-types`: `RecordTypeByNameIndex` (`RecordTypeByNameIndexSchema`) — `GSI1PK`/`GSI1SK`. `GSI1PK` = `TENANT#{TenantId}#RECORD_TYPES`, `GSI1SK` = `{Name.ToLowerInvariant()}#{RecordTypeId}` (alphabetical by name). Powers `ListRecordTypesQuery`. The previously documented `OwnerIndex` (OwnerId + CreatedAt, including a literal `"owner_system"` value) does not exist in code or CDK — removed as stale/fictional.
- `media-record-type-versions`: `RecordTypeVersionsByRecordTypeIndex` (`RecordTypeVersionByVersionIndexSchema` — class name doesn't match its own `IndexName` string, cosmetic only) — `GSI1PK`/`GSI1SK`. `GSI1PK` = `TENANT#{TenantId}#RECORD_TYPE#{RecordTypeId}#VERSIONS`, `GSI1SK` = `VERSION#{Version:D10}`. Powers `ListRecordTypeVersionsQuery`. Matches CDK's `RecordTypeVersionsByRecordTypeIndex` GSI exactly.
- `media-change-requests`:
  - `ChangeRequestByMediaItemIndex` (`ChangeRequestByMediaItemIndexSchema`) — `GSI1PK` only, sparse, no sort key. `GSI1PK` = `TENANT#{TenantId}#ITEM#{MediaItemId}#CHANGE_REQUESTS`. Powers `ListChangeRequestsByMediaItemQuery`.
  - `ChangeRequestByOwnerIndex` (`ChangeRequestByOwnerIndexSchema`) — `GSI2PK` only, sparse, no sort key. `GSI2PK` = `TENANT#{TenantId}#OWNER#{OwnerId}#CHANGE_REQUESTS`. Powers `ListChangeRequestsByOwnerQuery`. Both GSIs matched against CDK's `media-change-requests` GSI declarations exactly (`ChangeRequestByMediaItemIndex`/`ChangeRequestByOwnerIndex`, GSI1PK/GSI2PK only, no sort keys on either side) — zero discrepancies.
- `media-processing-jobs`: `AssetByProcessingJobIndex` (`AssetByProcessingJobIndexSchema`) — `GSI1PK`/`GSI1SK`, not sparse. `GSI1PK` = `TENANT#{TenantId}#ASSET#{AssetId}#JOBS`, `GSI1SK` = `{UpdatedAt:O}` (ISO timestamp only — unlike Registration's GSIs, the sort key carries no trailing `#{JobId}` disambiguator, so two jobs for the same asset updated at the exact same instant would collide on SK; flagging as a latent edge case, not fixed since it's app-code key-shape behavior, not a CDK/spec error). Powers `ListProcessingJobsForAssetIdQuery`. Matches CDK's `AssetByProcessingJobIndex` GSI on `media-processing-jobs` exactly (GSI1PK/GSI1SK, both String).

**PK construction — projectors:** Projectors construct all read model PKs as `$"TENANT#{tenantId.Value}#{entityId}"`, sourcing `tenantId` from the SQS message attribute envelope via `SqsExecutionContext`.

**PK construction — Query API:** All `GetItem` and `Query` calls construct PKs using `ctx.TenantId` from `IExecutionContext`. The `TENANT#` prefix is an enforcement boundary — a caller cannot access another tenant's rows even with a known entity ID.

### SNS Topics

| Topic                       | Purpose                                                                                                                 | Subscribers                                    |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `media-domain-events`       | Internal fan-out of domain events (internal shapes).                                                                    | Media Management-owned SQS queues only.        |
| `media-integration-events`  | Boundary fan-out of curated `media.*` integration events (published language). Populated inline by per-module `*IntegrationEventPublisher` classes (ADR-005). | MM-owned `media-cross-module-events` SQS (intra-BC fan-in) and external BC-owned SQS queues (one per BC). |

### SQS Queues

| Queue                        | Purpose                                                                     | Source Topic                 | DLQ? | Lambda host |
| ---------------------------- | --------------------------------------------------------------------------- | ---------------------------- | ---- | ----------- |
| `media-projector`            | DynamoDB read model projections                                             | `media-domain-events`        | Yes  | `Projectors.ReadModel` |
| `media-projector-search`     | OpenSearch index projections — separate queue for independent scaling, replay, and failure isolation from DynamoDB projections | `media-domain-events` | Yes | `Projectors.Search` |
| `media-processing`           | Processing Worker trigger (`AssetUploadConfirmedIntegrationEvent`)          | `media-integration-events`   | Yes  | ⚠️ Host not yet deployed |
| `media-signing`              | SecuredSigning Adapter trigger                                              | `media-domain-events`        | Yes  | ⚠️ Host not yet deployed |
| `media-cross-module-events`  | Integration Event Consumers Lambda trigger — intra-BC fan-in (ADR-005). Renamed from `media-notifications`. | `media-integration-events` | Yes | `EventConsumers` |
| `media-sagas`                | SagaOrchestrator trigger — subscribes to integration events, not domain events. Integration events are stable versioned contracts; the `MediaItemReviewSaga` also spans the ChangeRequests context, so domain event coupling would violate BC isolation. | `media-integration-events` | Yes | `SagaOrchestrator` |
| `media-document-signing`     | DocumentSigning saga trigger — separate from `media-sagas` for isolated deployment and DLQ visibility. | `media-integration-events` | Yes | `SagaOrchestrator.DocumentSigning` |
| `media-bulk-folder-imports`  | BulkFolderImportWorker trigger — processes async folder imports