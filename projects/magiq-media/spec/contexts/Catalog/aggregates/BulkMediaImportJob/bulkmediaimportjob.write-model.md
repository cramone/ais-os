# BulkMediaImportJob — Write Model

_Context: `Catalog`_
_Aggregate: `BulkMediaImportJob`_
_Stream prefix: `bulk-media-import-job_`_

---

## Purpose

Tracks lifecycle of async large-volume media item imports. Coordinates multi-phase pipeline: asset upload → virus scan → cataloging → processing. Provides progress tracking across processing pipeline stages. Distinct from `BulkFolderImportJob` due to binary upload coordination, asset processing integration, and lower batch limits (50 vs 200).

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| Job cannot be cancelled after completion | `JobAlreadyCompleted` | `CancelBulkMediaImportJobCommand` |
| Phase transitions must follow valid sequence | `InvalidStateTransition` | Phase advancement commands |
| Total items must be > 0 | `InvalidOperation` | `CreateBulkMediaImportJobCommand` |
| Cannot record validation results before uploads complete | `JobNotInUploadingState` | `RecordBulkMediaImportJobValidationResultsCommand` |

---

## Properties

| Property | Type | Notes |
|---|---|---|
| `JobId` | `BulkMediaImportJobId` | UUID v7-based. Caller-generated. |
| `TenantId` | `TenantId` | Set from creation event (first field). Immutable. |
| `CollectionId` | `CollectionId` | Target collection. Immutable. |
| `InputFormat` | `BulkImportInputFormat` | `JSON | CSV` (line-delimited not supported — media needs structured metadata) |
| `InputStorageKey` | `string?` | S3 key if input >10KB |
| `Status` | `BulkMediaImportJobStatus` | See state machine below |
| `TotalItems` | `int` | Item count from manifest |
| `UploadedCount` | `int` | Assets uploaded + confirmed |
| `ValidatedCount` | `int` | Assets passed virus scan |
| `CatalogedCount` | `int` | MediaItems created |
| `ProcessedCount` | `int` | Assets completed processing pipeline |
| `FailedCount` | `int` | Cumulative failures across all phases |
| `CreatedAt` | `DateTimeOffset` | |
| `CompletedAt` | `DateTimeOffset?` | |
| `Version` | `int` | Event sequence count |

---

## State Machine

```
Queued → AwaitingUploads → Validating → Cataloging → Processing → Completed
                                                                  ↘ Failed
                                                                  ↘ Cancelled
```

**Phase descriptions:**

| Status | Description |
|---|---|
| `Queued` | Job created, worker not yet started |
| `AwaitingUploads` | Pre-signed URLs issued, waiting for client uploads + confirmations |
| `Validating` | Assets uploaded, virus scans in progress |
| `Cataloging` | Validation passed, creating MediaItem aggregates in batches |
| `Processing` | MediaItems cataloged, asset processing pipeline running (renditions, metadata extraction) |
| `Completed` | All phases complete |
| `Failed` | Fatal error in any phase |
| `Cancelled` | User-requested cancellation |

---

## Methods (Commands)

| Method | Description | Preconditions |
|---|---|---|
| `BulkMediaImportJob.Create(tenantId, jobId, collectionId, inputFormat, inputStorageKey?, totalItems)` | Factory. Raises `BulkMediaImportJobCreated`. | `totalItems > 0` |
| `StartUploads()` | Raises `BulkMediaImportJobUploadsStarted`. Status = Queued |
| `RecordUploadConfirmations(count)` | Raises `BulkMediaImportJobUploadConfirmationsRecorded`. | Status = AwaitingUploads |
| `StartValidation()` | Raises `BulkMediaImportJobValidationStarted`. | Status = AwaitingUploads, all uploads confirmed |
| `RecordValidationResults(passedCount, failedCount)` | Raises `BulkMediaImportJobValidationResultsRecorded`. | Status = Validating |
| `StartCataloging()` | Raises `BulkMediaImportJobCatalogingStarted`. | Status = Validating, all scans complete |
| `RecordCatalogingResults(succeededCount, failedCount)` | Raises `BulkMediaImportJobCatalogingResultsRecorded`. | Status = Cataloging |
| `StartProcessing()` | Raises `BulkMediaImportJobProcessingStarted`. | Status = Cataloging, all items cataloged |
| `RecordProcessingResults(succeededCount, failedCount)` | Raises `BulkMediaImportJobProcessingResultsRecorded`. | Status = Processing |
| `Complete()` | Raises `BulkMediaImportJobCompleted`. | Status = Processing |
| `Fail(reason)` | Raises `BulkMediaImportJobFailed`. | Status ≠ terminal |
| `Cancel()` | Raises `BulkMediaImportJobCancelled`. | Status ∈ {Queued, AwaitingUploads, Validating, Cataloging} |

---

## Domain Events

| Event | Key Payload Fields |
|---|---|
| `BulkMediaImportJobCreated` | `TenantId`†, `JobId`, `CollectionId`, `InputFormat`, `InputStorageKey?`, `TotalItems` |
| `BulkMediaImportJobUploadsStarted` | `JobId`, `StartedAt` |
| `BulkMediaImportJobUploadConfirmationsRecorded` | `JobId`, `UploadedCount` |
| `BulkMediaImportJobValidationStarted` | `JobId`, `StartedAt` |
| `BulkMediaImportJobValidationResultsRecorded` | `JobId`, `ValidatedCount`, `FailedCount` |
| `BulkMediaImportJobCatalogingStarted` | `JobId`, `StartedAt` |
| `BulkMediaImportJobCatalogingResultsRecorded` | `JobId`, `CatalogedCount`, `FailedCount` |
| `BulkMediaImportJobProcessingStarted` | `JobId`, `StartedAt` |
| `BulkMediaImportJobProcessingResultsRecorded` | `JobId`, `ProcessedCount`, `FailedCount` |
| `BulkMediaImportJobCompleted` | `JobId`, `CompletedAt`, `TotalSucceeded`, `TotalFailed` |
| `BulkMediaImportJobFailed` | `JobId`, `FailureReason`, `FailedAt` |
| `BulkMediaImportJobCancelled` | `JobId`, `CancelledAt` |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command | Handler | Result |
|---|---|---|
| `CreateBulkMediaImportJobCommand(...)` | `CreateBulkMediaImportJobHandler` | `Result<BulkMediaImportJobId, DomainError>` |
| `StartBulkMediaImportJobUploadsCommand(JobId)` | `StartBulkMediaImportJobUploadsHandler` | `Result<Unit, DomainError>` |
| `RecordBulkMediaImportJobUploadConfirmationsCommand(JobId, Count)` | Handler | `Result<Unit, DomainError>` |
| `StartBulkMediaImportJobValidationCommand(JobId)` | Handler | `Result<Unit, DomainError>` |
| `RecordBulkMediaImportJobValidationResultsCommand(JobId, PassedCount, FailedCount)` | Handler | `Result<Unit, DomainError>` |
| `StartBulkMediaImportJobCatalogingCommand(JobId)` | Handler | `Result<Unit, DomainError>` |
| `RecordBulkMediaImportJobCatalogingResultsCommand(JobId, SucceededCount, FailedCount)` | Handler | `Result<Unit, DomainError>` |
| `StartBulkMediaImportJobProcessingCommand(JobId)` | Handler | `Result<Unit, DomainError>` |
| `RecordBulkMediaImportJobProcessingResultsCommand(JobId, SucceededCount, FailedCount)` | Handler | `Result<Unit, DomainError>` |
| `CompleteBulkMediaImportJobCommand(JobId)` | Handler | `Result<Unit, DomainError>` |
| `FailBulkMediaImportJobCommand(JobId, Reason)` | Handler | `Result<Unit, DomainError>` |
| `CancelBulkMediaImportJobCommand(JobId)` | Handler | `Result<Unit, DomainError>` |

---

## Published Integration Events

Published inline by `BulkMediaImportJobIntegrationEventPublisher` (`Catalog.WriteModel`). All events target `media-integration-events` SNS topic.

| Integration Event | Source Domain Event | Notes |
|---|---|---|
| `BulkMediaImportJobCreatedMessage` | `BulkMediaImportJobCreated` | Consumed by `BulkMediaImportWorker` Lambda via `media-bulk-media-imports` SQS queue |
| `BulkMediaImportJobCompletedMessage` | `BulkMediaImportJobCompleted` | Optional — consumed by Notifications |
| `BulkMediaImportJobFailedMessage` | `BulkMediaImportJobFailed` | Optional — consumed by Notifications |

---

## Worker Processing Flow

`BulkMediaImportWorker` Lambda triggered by `BulkMediaImportJobCreatedMessage` from `media-bulk-media-imports` SQS queue:

### Phase 1: Issue Upload URLs
1. Load manifest (from S3 if `InputStorageKey` present)
2. Parse manifest per `InputFormat` (JSON or CSV)
3. Generate `AssetId` per item (UUID v7)
4. Dispatch `UploadAssetCommand` per item → returns pre-signed S3 URL
5. Write upload URLs to response table (`media-bulk-import-upload-urls`)
6. Dispatch `StartBulkMediaImportJobUploadsCommand`

Client uploads assets using pre-signed URLs, then calls:
```
POST /v1/catalog/import-jobs/{jobId}/confirm-uploads
```

### Phase 2: Validation
1. Wait for all upload confirmations (tracked via `UploadedCount`)
2. Dispatch `StartBulkMediaImportJobValidationCommand`
3. Subscribe to `AssetValidationPassedIntegrationEvent` and `AssetValidationFailedIntegrationEvent` (fan-in from asset processing pipeline)
4. Accumulate results, dispatch `RecordBulkMediaImportJobValidationResultsCommand` per batch
5. After all validations: dispatch `StartBulkMediaImportJobCatalogingCommand`

### Phase 3: Cataloging
1. Split validated assets into chunks of 50 (per `MaxMediaItemsPerRequest`)
2. For each chunk:
   - Dispatch `BulkCreateMediaItemsCommand` (new command — see MediaItem write model additions)
   - Collect results
   - Dispatch `RecordBulkMediaImportJobCatalogingResultsCommand`
3. After all chunks: dispatch `StartBulkMediaImportJobProcessingCommand`

### Phase 4: Processing
1. Subscribe to `ProcessingJobCompletedIntegrationEvent` and `ProcessingJobFailedIntegrationEvent`
2. Accumulate results per asset
3. Dispatch `RecordBulkMediaImportJobProcessingResultsCommand` per batch
4. After all processing complete: dispatch `CompleteBulkMediaImportJobCommand`

---

## Input Storage Strategy

Same as `BulkFolderImportJob`:

| Input Size | Storage | Access Pattern |
|---|---|---|
| ≤10KB | Inline in aggregate event | Direct from event |
| >10KB | S3 `media-bulk-import-inputs` bucket | Worker streams from S3 |

**S3 Key Pattern:** `{tenantId}/media-imports/{jobId}.{ext}`

---

## Related

- [BulkMediaImportJob Read Model](./bulkmediaimportjob.read-model.md)
- [BulkMediaImportJob API](./bulkmediaimportjob.api.md)
- [MediaItem Write Model](../MediaItem/mediaitem.write-model.md)
- [Asset Write Model](../../../AssetManagement/aggregates/Asset/asset.write-model.md)
- [Bulk Operations](../../../../shared/bulk-operations.md)
