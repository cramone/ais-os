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
| `AssetDetailProjector` | `media-asset-detail` | |
| `AssetSummaryProjector` | `media-assets` | |
| `CollectionDetailProjector` | `media-collection-detail` | |
| `CollectionSummaryProjector` | `media-collections` | |
| `FolderDetailProjector` | `media-folder-detail` | |
| `FolderSummaryProjector` | `media-folders` | |
| `MediaItemDetailProjector` | `media-item-detail` | |
| `MediaItemSummaryProjector` | `media-items` | |
| `MediaItemVersionProjector` | `media-item-versions` | |
| `MediaProfileDetailProjector` | `media-profiles` | |
| `MediaProfileVersionProjector` | `media-profile-versions` | |
| `ChangeRequestDetailProjector` | `media-change-request-detail` | |
| `ChangeRequestSummaryProjector` | `media-change-requests` | |
| `ChangeRequestCommentProjector` | `media-change-request-comments` | |
| `SigningSessionDetailProjector` | `media-signing-session-detail` | |
| `SigningSessionSummaryProjector` | `media-signing-sessions` | 🔴 Deferred — `DocumentSigning` module not yet complete |
| `RecordTypeDetailProjector` | `media-record-type-detail` | |
| `RecordTypeSummaryProjector` | `media-record-types` | |
| `RecordTypeVersionProjector` | `media-record-type-versions` | |
| `RegistrationDetailProjector` | `media-registration-detail` | |
| `RegistrationSummaryProjector` | `media-registrations` | |
| `BulkFolderImportJobSummaryProjector` | `media-bulk-folder-import-jobs` | |
| `BulkFolderImportJobDetailProjector` | `media-bulk-folder-import-job-detail` | |
| `BulkMediaImportJobSummaryProjector` | `media-bulk-media-import-jobs` | |
| `BulkMediaImportJobDetailProjector` | `media-bulk-media-import-job-detail` | |

**Write-side reference index projectors** (used by command handlers — not query-facing):

| Projector | Target Table | Purpose |
|---|---|---|
| `FolderChildIndexProjector` | `folder-child-index` | Direct child media-folder membership; set size = child count |
| `FolderMediaItemsIndexProjector` | `folder-media-index` | MediaItem membership per media-folder |
| `MediaProfileIndexProjector` | `media-profile-index` | MediaProfile capability data for Processing Worker |
| `RecordTypeVersionDetailIndexProjector` | `catalog-record-type-versions` | Published RecordType version tracking for Catalog |
| ~~`RegistrationCountIndexProjector`~~ | ~~`folder-registration-index`~~ | ⚠️ NOT IMPLEMENTED |
| ~~`FolderActiveItemCountIndexProjector`~~ | ~~`folder-active-item-count-index`~~ | ⚠️ NOT IMPLEMENTED |

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
| `media-sagas` | `TENANT#{TenantId}#{SagaId}` | — | Saga state persistence for `SagaOrchestrator` Lambda. |

**Query-facing read models:**

| Table | Partition Key | Sort Key | Purpose |
|---|---|---|---|
| `media-collections` | `TENANT#{TenantId}#{CollectionId}` | — | Collection summary list. |
| `media-collection-detail` | `TENANT#{TenantId}#{CollectionId}` | — | Full media-collection detail + root media-folder refs. |
| `media-folders` | `TENANT#{TenantId}#{FolderId}` | — | Folder summary list. |
| `media-folder-detail` | `TENANT#{TenantId}#{FolderId}` | — | Folder detail + child media-folder refs. |
| `media-items` | `TENANT#{TenantId}#{MediaItemId}` | — | MediaItem summary — all GSIs on this table. |
| `media-item-detail` | `TENANT#{TenantId}#{MediaItemId}` | — | Full media-item detail, metadata, role assignments. |
| `media-item-versions` | `TENANT#{TenantId}#{MediaItemId}:{VersionNumber}` | — | Full snapshot per approved version. |
| `media-assets` | `TENANT#{TenantId}#{AssetId}` | — | Asset summary list per media-item. Includes `StorageTier` and `CreatedAt` attributes (required by `StorageTierTransitionScanner`). |
| `media-asset-detail` | `TENANT#{TenantId}#{AssetId}` | — | Full asset detail, renditions, metadata. |
| `media-registrations` | `TENANT#{TenantId}#{RegistrationId}` | — | Registration summary list per media-item. |
| `media-registration-detail` | `TENANT#{TenantId}#{RegistrationId}` | — | Full media-registration detail including media-items and amendments. |
| `media-record-types` | `TENANT#{TenantId}#{RecordTypeId}` | — | RecordType summary list per owner (includes `"owner_system"`). |
| `media-record-type-detail` | `TENANT#{TenantId}#{RecordTypeId}` | — | Full RecordType detail including draft state. |
| `media-record-type-versions` | `TENANT#{TenantId}#{RecordTypeId}` | `Version` | Full field snapshot per published version — schema validation and replay. |
| `media-profiles` | `TENANT#{TenantId}#{MediaProfileId}` | — | Full MediaProfile detail including draft state. |
| `media-profile-versions` | `TENANT#{TenantId}#{MediaProfileId}:{Version}` | — | Full asset/capability snapshot per published version. |
| `media-change-requests` | `TENANT#{TenantId}#{ChangeRequestId}` | — | Change request summary list per media-item. |
| `media-change-request-detail` | `TENANT#{TenantId}#{ChangeRequestId}` | — | Full change request detail including reviewer decisions. |
| `media-change-request-comments` | `TENANT#{TenantId}#{ChangeRequestId}` | `CommentId` | Threaded comments per change request. |
| `media-signing-session-detail` | `TENANT#{TenantId}#{SigningSessionId}` | — | Full signing session detail. |
| `media-signing-sessions` | `TENANT#{TenantId}#{SigningSessionId}` | — | Signing session summary list. ⚠️ `SigningSessionSummaryProjector` not implemented. |
| `media-bulk-folder-import-jobs` | `JobId` | — | Folder import job summary with progress tracking. GSI1: TenantId+CreatedAt, GSI2: CollectionId+CreatedAt. |
| `media-bulk-folder-import-job-detail` | `JobId` | — | Full folder import job detail including input payload or S3 key reference. |
| `media-bulk-media-import-jobs` | `JobId` | — | Media import job summary with multi-phase progress tracking. GSI1: TenantId+CreatedAt, GSI2: CollectionId+CreatedAt. |
| `media-bulk-media-import-job-detail` | `JobId` | — | Full media import job detail including manifest reference and upload URL table pointer. |
| `media-bulk-import-job-items` | `TENANT#{TenantId}#JOB#{JobId}` | `ITEM#{Index}` | Per-item results for all bulk import jobs (shared). Supports both folder and media imports with `JobType` discriminator. |
| `media-bulk-import-upload-urls` | `TENANT#{TenantId}#JOB#{JobId}` | `ITEM#{Index}` | Temporary pre-signed upload URLs for media imports. TTL 24h. |

> All query-facing read model tables store `TenantId` as a plain attribute in addition to the `TENANT#` PK prefix (for observability / scan convenience).

**Write-side reference indexes** (command handler constraint enforcement — not query-facing):

| Table | Purpose |
|---|---|
| `folder-child-index` | Direct child media-folder membership per media-folder |
| `folder-media-index` | MediaItem membership per media-folder |
| `media-profile-index` | MediaProfile capability data (Processing Worker reads) |
| `catalog-record-type-versions` | Published RecordType version index (Catalog cross-module reference) |
| `media-name-reservations` | Two-tier name uniqueness — transactionally written alongside aggregate creation events |
| ~~`folder-status-index`~~ | ⚠️ NOT IMPLEMENTED — archive cascade blocked |
| ~~`folder-registration-index`~~ | ⚠️ NOT IMPLEMENTED |
| ~~`folder-active-item-count-index`~~ | ⚠️ NOT IMPLEMENTED |

> `collection-index`, `folder-name-index`, and `media-item-title-scope-index` are superseded — name uniqueness is enforced via `media-name-reservations`.

**GSIs:**

- `media-items`:
  - `FolderItemsIndex` (FolderId + MediaItemId) — sparse; assigned media-items only. Powers `GET /media-items?folderId=`.
  - `UnassignedIndex` (OwnerId + CreatedAt) — sparse; null-FolderId media-items only. Write-once: inserted on `MediaItemCreated` (unassigned), removed permanently on `MediaItemAssignedToFolder`. Powers `GET /media-items?assigned=false`.
  - `OwnerStatusIndex` (OwnerId + Status + CreatedAt) — all media-items.
  - `ProfileIndex` (MediaProfileId + Status)
- `media-collections`: `VisibilityIndex` (Visibility + CreatedAt) — public media-collection discovery
- `media-registrations`: `StatusIndex` (Status + SubmittedAt)
- `media-record-types`: `OwnerIndex` (OwnerId + CreatedAt) — includes `"owner_system"` for platform-level types

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
| `media-processing`           | Processing Worker trigger                                                   | `media-domain-events`        | Yes  | ⚠️ Host not yet deployed |
| `media-signing`              | SecuredSigning Adapter trigger                                              | `media-domain-events`        | Yes  | ⚠️ Host not yet deployed |
| `media-cross-module-events`  | Integration Event Consumers Lambda trigger — intra-BC fan-in (ADR-005). Renamed from `media-notifications`. | `media-integration-events` | Yes | `EventConsumers` |
| `media-sagas`                | SagaOrchestrator trigger — subscribes to integration events, not domain events. Integration events are stable versioned contracts; the `MediaItemReviewSaga` also spans the ChangeRequests context, so domain event coupling would violate BC isolation. | `media-integration-events` | Yes | `SagaOrchestrator` |
| `media-document-signing`     | DocumentSigning saga trigger — separate from `media-sagas` for isolated deployment and DLQ visibility. | `media-integration-events` | Yes | `SagaOrchestrator.DocumentSigning` |
| `media-bulk-folder-imports`  | BulkFolderImportWorker trigger — processes async folder imports. Filter policy: `message_type = ["media.bulkfolderimportjob.created"]`. | `media-integration-events` | Yes | `BulkFolderImportWorker` |
| `media-bulk-media-imports`   | BulkMediaImportWorker trigger — processes async media imports with multi-phase pipeline. Filter policy: `message_type = ["media.bulkmediaimportjob.created"]`. | `media-integration-events` | Yes | `BulkMediaImportWorker` |

External bounded contexts (Notifications, Search/Discovery, Billing, Compliance) own their own SQS queues subscribed to `media-integration-events` — these are **not** Media Management-owned resources.

All MM-owned queues are standard (not FIFO). DLQ max 3 retries; CloudWatch alarms on DLQ depth.

**SNS message attributes on every published event:**

| Attribute | Type | Source |
|---|---|---|
| `TenantId` | String | `eventRecord.TenantId` — stamped by `EventPublisher` |
| `AggregateId` | String | Aggregate stream identifier |
| `AggregateVersion` | Number | Event sequence position |
| `EventType` | String | Discriminator for filter policies |
| `CorrelationId` | String | Propagated from originating request |

Consumers extract `TenantId` from message attributes and construct an `SqsExecutionContext` per message. `TenantId` is never parsed from the event payload body.

### OpenSearch

**Index: `media-items`** — primary search surface
```json
{
  "tenantId": "keyword",
  "mediaItemId": "keyword",
  "collectionId": "keyword",
  "folderId": "keyword",
  "ownerId": "keyword",
  "title": "text (analyzed)",
  "status": "keyword",
  "isAccessible": "boolean",
  "mediaProfileId": "keyword",
  "tags": "keyword[]",
  "metadata": "object — only fields where FieldDefinition.IsSearchable = true; mapping per FieldType: Text → text (analyzed), Number → double, Date → date, Boolean → boolean, Url → keyword, Enum/MultiEnum → keyword[]",
  "createdAt": "date",
  "publishedAt": "date"
}
```

**Index: `media-registrations`** — media-registration search / facet filtering
```json
{
  "tenantId": "keyword",
  "registrationId": "keyword",
  "mediaItemId": "keyword",
  "ownerId": "keyword",
  "registrationType": "keyword",
  "registrationAuthority": "keyword",
  "status": "keyword",
  "submittedAt": "date",
  "confirmedAt": "date"
}
```

Index aliases (`media-items-v1` → alias `media-items`) allow zero-downtime reindexing on schema changes.

### S3

Three separate buckets with independent lifecycle and IAM policies. Keys never include `OwnerId` — ownership is mutable and cannot be embedded in a storage key that must remain stable. `TenantId` is the prefix; `AssetId` provides uniqueness within a tenant.

| Bucket | Key Pattern | Written By | Notes |
|---|---|---|---|
| `media-source` | `{tenantId}/{shard}/{assetId}/original.{ext}` | Ingest API (pre-signed PUT) | MediaProfile has `Processing` capability, or unattached asset |
| `media-renditions` | `{tenantId}/{shard}/{assetId}/{renditionType}.{ext}` | Processing Worker | Generated renditions (image variants, video transcodes) |
| `media-documents` | `{tenantId}/{shard}/{assetId}/document.{ext}` | Ingest API (pre-signed PUT) | MediaProfile lacks `Processing` capability (media-registration documents, signed PDFs) |
| `media-bulk-import-inputs` | `{tenantId}/folder-imports/{jobId}.{ext}` or `{tenantId}/media-imports/{jobId}.{ext}` | Ingest API | Large import manifests (>10KB). TTL 7 days. |

**Shard prefix:** `{shard}` = last 4 hex chars of the UUID v7 `AssetId` (`assetId.ToString("N")[^4..]`) — 65,536 distinct prefixes sourced from random bits at positions 112–127. No hashing required; the shard is reconstructible from the `AssetId` alone.

**Key construction:** The `StorageKeyGenerator` in the Ingest API constructs all keys. The client receives a pre-signed URL and cannot influence the key path (see ADR-004). Bucket selection (`media-source` vs. `media-documents`) is determined by resolving `HasProcessingCapability` from the `media-profile-index` reference model at upload initiation time.

**Lifecycle rules:**
- `media-source`: time-based, applies to **all objects** (no tag filter). Transitions from object creation date:
  - 0–90 days → S3 Standard
  - 90–365 days → S3 Standard-IA
  - 365 days – 2 years → S3 Glacier Instant Retrieval
  - 2+ years → S3 Glacier Deep Archive
- `media-renditions`: no lifecycle rule — retained alongside their originals.
- `media-documents`: no lifecycle transition — media-registration documents are retained indefinitely.

**StorageTier sync:** The `Asset` aggregate tracks `StorageTier` as the last-confirmed S3 storage class. Since S3 lifecycle transitions happen silently, the `StorageTierTransitionScanner` (scheduled Lambda) periodically computes the expected tier from `Asset.CreatedAt` and dispatches `RecordStorageTierTransitionCommand` for any asset whose recorded tier is stale.

**IAM policy boundaries:**
- Ingest API role: `s3:PutObject` on `media-source` and `media-documents`, scoped to keys prefixed with the actor's `TenantId`. Pre-signed URL conditions enforce `content-type` and exact `content-length` (see ADR-004).
- Processing Worker role: `s3:GetObject` on `media-source`; `s3:PutObject` on `media-renditions`. `s3:PutObjectTagging` on `media-source` is **no longer required** (tag-based lifecycle removed).
- Query API role: `s3:GetObject` on all three buckets, scoped to the request `TenantId`.
- No service role holds `s3:DeleteObject` on any bucket — deletion is managed via S3 lifecycle rules only.

**Bucket policy:** Each bucket enforces `aws:SecureTransport` (HTTPS only) and blocks all public access at the account level.

---

## Cross-Cutting Concerns

> Full cross-cutting spec is in `spec/shared/system-spec.md`. This section documents the architectural enforcement points.

### TenantId Isolation

`TenantId` is the primary tenant boundary and flows through the entire stack:

| Layer | Source | Enforcement |
|---|---|---|
| HTTP | JWT `tenant_id` claim | `HttpExecutionContext` resolves via `IHttpContextAccessor`; validated at API Gateway |
| SQS | SNS message attribute `TenantId` | `SqsExecutionContext` constructed per-message; never parsed from event payload body |
| DynamoDB | `TENANT#{TenantId}#` PK prefix | Hard partition isolation — a valid key for tenant A cannot address tenant B's rows |
| S3 | `{tenantId}/` key prefix | IAM condition on all pre-signed URLs and service role policies |
| Event store | `aggregate.TenantId` field | `IEventStore.SaveAsync` reads from the aggregate directly — not from `IExecutionContext` |
| SNS attributes | `TenantId` stamped by `EventPublisher` | Consumers read from message attributes to construct `SqsExecutionContext` |

`OwnerId` is **not** `TenantId`. `OwnerId` identifies an actor within a tenant; `TenantId` identifies the tenant boundary. `OwnerId` is never used as a storage key prefix.

### IExecutionContext

```csharp
interface IExecutionContext {
    string   TenantId       // JWT tenant_id claim — drives PK prefix and storage keys
    IActor   Actor          // Resolved actor (User | System | Guest)
    string?  CausationId
    string?  CorrelationId
}
```

| Host | Implementation | Scope |
|---|---|---|
| `Api` (FastEndpoints, write) | `HttpExecutionContext` — from validated JWT claims via `IHttpContextAccessor` | Scoped per HTTP request |
| `QueryApi` (FastEndpoints, read) | `HttpExecutionContext` — from validated JWT claims via `IHttpContextAccessor` | Scoped per HTTP request |
| SQS Lambda entry-points (`Projectors.ReadModel`, `Projectors.Search`, `EventConsumers`, `SagaOrchestrator`, `SagaOrchestrator.DocumentSigning`) | `SqsExecutionContext` — constructed per-message from SNS message attributes | Scoped per SQS message |

### Aggregate Convention

Every aggregate implements `ITenantScoped`:
- `TenantId` is the **first field** on every aggregate creation event
- Set once in the creation event's `Apply()` handler — immutable thereafter
- `TenantId` is the **first parameter** on every aggregate factory method

All aggregate IDs are UUID v7 strongly-typed value objects (e.g. `MediaItemId`, `AssetId`, `FolderId`).

### Command Result Contract

All commands return `Result<T, DomainError>` — no domain exceptions escape handlers. The HTTP layer maps `DomainError` variants to RFC 9457 `ProblemDetails` responses. Lambda SQS handlers treat non-transient `DomainError` results as acknowledged (no requeue); infrastructure failures surface as uncaught exceptions and trigger SQS retry / DLQ.

### Optimistic Concurrency

All aggregates use event store–level optimistic concurrency enforced by DynamoDB conditional writes:

```
ConditionExpression: attribute_not_exists(AggregateVersion)
```

`ConditionalCheckFailedException` → `DomainError.ConcurrencyConflict` → command handler retries up to **3×** with exponential backoff.

### Name Uniqueness — Two-Tier Enforcement

Name uniqueness (media-collection names, media-folder child names, MediaItem titles within media-folder scope, MediaProfile names, RecordType names) is enforced by:

1. **Tier 1 (read-model check):** `INameReservationService` queries `media-name-reservations` before the aggregate is loaded. Rejects the command cheaply in the common case.
2. **Tier 2 (atomic reservation):** `IEventStore.SaveAsync` wraps the event append in a `DynamoDB.TransactWriteItems` call that atomically appends the event **and** writes a reservation to `media-name-reservations`. If either condition fails, the entire transaction is rejected — exactly one concurrent writer succeeds.

On **rename**, the transaction additionally deletes the old reservation atomically (3-item `TransactWriteItems`).

---

## Security

> Full authentication and authorisation spec is in `spec/shared/system-spec.md §Authentication & Authorization`.

### JWT Validation

All non-public endpoints require a JWT bearer token validated at the API Gateway level. Required claims: `sub`, `name`, `roles`, `actor_type`, `tenant_id`, `exp`, `jti`. Expired tokens are rejected unconditionally.

### Token Replay Detection

Every presented JWT is checked against the `media-used-jtis` DynamoDB table (`PK: jti`, `TTL: exp`) on every authenticated request:

1. `GetItem(PK = jti)` — if exists → reject `401`
2. Conditional `PutItem({jti, exp})` with `attribute_not_exists(PK)` — if `ConditionalCheckFailedException` → reject `401`

Full enforcement for all actor types that present a JWT. Table is platform-managed (not an MM-owned infrastructure resource).

### Command-Level Authorization

| Command | Permitted Actor | Rule |
|---|---|---|
| `CreateRecordType` / `PublishRecordType` (system-owned) | System | `ActorType == "System"` |
| `ForceReleaseCheckout` | System | `ActorType == "System"` — no User or Guest may invoke |
| `AssignReviewer`, `RemoveReviewer` | User (owner) | `Actor.Id == ChangeRequest.OwnerId` |
| `ApproveMediaItem`, `RejectMediaItem` (via CR) | User (reviewer) | `Actor.Id ∈ ChangeRequest.Reviewers[].ReviewerId` |
| All write commands on `MediaItem`, `Asset`, `Registration`, `ChangeRequest` | User (owner) | `Actor.Id == aggregate.OwnerId` |
| `ArchiveCollection`, `RenameCollection`, `SetCollectionVisibility` | User (owner) | `Actor.Id == Collection.OwnerId` |

**Guest** actors (no JWT) have read-only access to public endpoints only, rate-limited by source IP.

### HTTP-Level Idempotency

Mutating endpoints accept an `IdempotencyKey` request header. The `Magiq.AspNetCore.Idempotency` platform middleware caches the first response; replays within the TTL window return the cached response without re-executing the command. The key is **not** propagated through SNS/SQS — message-level idempotency is handled by event store conditional writes, projector `ProjectedVersion` guards, and saga status checks.

---

## Observability

| Signal | Tool | Notes |
|---|---|---|
| Structured logs | Serilog | `TenantId`, `CorrelationId`, `CausationId` enriched on every log event (per HTTP request or SQS message scope) |
| Distributed tracing | AWS X-Ray | Enabled on all Lambda invocations; `TenantId` annotated as a first-class dimension |
| Error handling | `Result<T, DomainError>` | Domain errors never escape handlers as exceptions; surfaces as structured RFC 9457 error responses |
| DLQ monitoring | CloudWatch Alarms | Alarm on DLQ depth (`> 0`) for all MM-owned queues; max 3 retries before DLQ |
| Saga timeout monitoring | CloudWatch Events | `SagaTimeoutScanner` Lambda on 5-minute schedule; CloudWatch metric on expired saga dispatch count |
| Storage tier sync | CloudWatch Events | `StorageTierTransitionScanner` Lambda on daily schedule; CloudWatch metric on transition dispatch count and scan errors |
| Integration event drift | Unit test per module | Asserts every `IntegrationEvent`-derived type registered in DI is present in the Integration Event Catalog and vice versa — catches mapper/catalog drift at build time |

---

## Module Structure

Each bounded context in `src/modules/` follows a consistent layer structure:

```
src/modules/
├── AssetManagement/
│   ├── AssetManagement.Domain/                    # Aggregates, domain events, value objects
│   ├── AssetManagement.WriteModel/                # Command handlers, write-side projectors,
│   │   └── IntegrationEvents/Publishing/Mappers/  #   integration event mappers (*DomainEventMapper)
│   ├── AssetManagement.ReadModel/                 # Query handlers, read model types
│   └── AssetManagement.Events/                    # Integration event contracts (shared with consumers)
├── Catalog/
├── ChangeRequests/
├── DocumentSigning/
├── Metadata/
├── Processing/
└── Registration/

src/hosts/
├── Api/                                           # FastEndpoints write API — all command endpoints
├── QueryApi/                                      # FastEndpoints read API — all query endpoints
├── Projectors.ReadModel/                          # SQS worker — DynamoDB read model projections
├── Projectors.Search/                             # SQS worker — OpenSearch index projections
├── EventConsumers/                                # SQS worker — integration event consumers (ADR-005)
├── SagaOrchestrator/                              # SQS worker — AssetIngestionSaga + MediaItemReviewSaga
├── SagaOrchestrator.DocumentSigning/              # SQS worker — DocumentSigningSaga (deferred)
└── TimeoutScanner/                                # EventBridge (5 min) — saga timeout compensation
