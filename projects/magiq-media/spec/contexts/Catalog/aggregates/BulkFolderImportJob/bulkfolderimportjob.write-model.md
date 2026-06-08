# BulkFolderImportJob — Write Model

_Context: `Catalog`_
_Aggregate: `BulkFolderImportJob`_
_Stream prefix: `bulk-folder-import-job_`_

---

## Purpose

Tracks lifecycle of async large-volume folder imports. Accepts line-delimited paths, CSV, or JSON input formats. Splits input into chunks of 200 folders (per `MaxFoldersPerRequest`), processes via queue, aggregates results. Provides progress tracking and per-item failure detail for imports that exceed inline HTTP timeout limits (>1000 folders or >30sec processing time).

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| Job cannot be cancelled after completion | `JobAlreadyCompleted` | `CancelBulkFolderImportJobCommand` |
| Batch results cannot be recorded for non-processing job | `JobNotProcessing` | `RecordBulkFolderImportJobBatchResultCommand` |
| Job must be in Processing state to complete | `JobNotProcessing` | `CompleteBulkFolderImportJobCommand` |
| Total items must be > 0 | `InvalidOperation` | `CreateBulkFolderImportJobCommand` |

---

## Properties

| Property | Type | Notes |
|---|---|---|
| `JobId` | `BulkFolderImportJobId` | UUID v7-based. Caller-generated. |
| `TenantId` | `TenantId` | Set from creation event (first field). Immutable. |
| `CollectionId` | `CollectionId` | Target collection. Immutable. |
| `InputFormat` | `BulkImportInputFormat` | `LineDelimited | CSV | JSON` |
| `InputStorageKey` | `string?` | S3 key if input >10KB; null if inline |
| `Status` | `BulkFolderImportJobStatus` | `Queued | Processing | Completed | Failed | Cancelled` |
| `TotalItems` | `int` | Estimated item count from input parsing |
| `ProcessedCount` | `int` | Incremented per batch |
| `SucceededCount` | `int` | Cumulative successful creations |
| `FailedCount` | `int` | Cumulative failures |
| `CreatedAt` | `DateTimeOffset` | |
| `CompletedAt` | `DateTimeOffset?` | Set when job reaches terminal state |
| `Version` | `int` | Event sequence count |

---

## Methods (Commands)

| Method | Description | Preconditions |
|---|---|---|
| `BulkFolderImportJob.Create(tenantId, jobId, collectionId, inputFormat, inputStorageKey?, totalItems)` | Factory. Raises `BulkFolderImportJobCreated`. | `totalItems > 0` |
| `RecordBatchResult(succeededCount, failedCount)` | Raises `BulkFolderImportJobBatchProcessed`. | Status = Processing |
| `Complete()` | Raises `BulkFolderImportJobCompleted`. | Status = Processing |
| `Fail(reason)` | Raises `BulkFolderImportJobFailed`. | Status = Processing |
| `Cancel()` | Raises `BulkFolderImportJobCancelled`. | Status ∈ {Queued, Processing} |

---

## Domain Events

| Event | Key Payload Fields |
|---|---|
| `BulkFolderImportJobCreated` | `TenantId`†, `JobId`, `CollectionId`, `InputFormat`, `InputStorageKey?`, `TotalItems` |
| `BulkFolderImportJobBatchProcessed` | `JobId`, `ProcessedCount`, `SucceededCount`, `FailedCount` |
| `BulkFolderImportJobCompleted` | `JobId`, `CompletedAt`, `TotalSucceeded`, `TotalFailed` |
| `BulkFolderImportJobFailed` | `JobId`, `FailureReason`, `FailedAt` |
| `BulkFolderImportJobCancelled` | `JobId`, `CancelledAt` |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command | Handler | Result |
|---|---|---|
| `CreateBulkFolderImportJobCommand(JobId, CollectionId, InputFormat, InputStorageKey?, TotalItems)` | `CreateBulkFolderImportJobHandler` | `Result<BulkFolderImportJobId, DomainError>` |
| `RecordBulkFolderImportJobBatchResultCommand(JobId, SucceededCount, FailedCount)` | `RecordBulkFolderImportJobBatchResultHandler` | `Result<Unit, DomainError>` |
| `CompleteBulkFolderImportJobCommand(JobId)` | `CompleteBulkFolderImportJobHandler` | `Result<Unit, DomainError>` |
| `FailBulkFolderImportJobCommand(JobId, Reason)` | `FailBulkFolderImportJobHandler` | `Result<Unit, DomainError>` |
| `CancelBulkFolderImportJobCommand(JobId)` | `CancelBulkFolderImportJobHandler` | `Result<Unit, DomainError>` |

---

## Published Integration Events

Published inline by `BulkFolderImportJobIntegrationEventPublisher` (`Catalog.WriteModel`) immediately after domain event persistence. All events target `media-integration-events` SNS topic.

| Integration Event | Source Domain Event | Notes |
|---|---|---|
| `BulkFolderImportJobCreatedMessage` | `BulkFolderImportJobCreated` | Consumed by `BulkFolderImportWorker` Lambda via `media-bulk-folder-imports` SQS queue |
| `BulkFolderImportJobCompletedMessage` | `BulkFolderImportJobCompleted` | Optional — consumed by Notifications for user alerts |
| `BulkFolderImportJobFailedMessage` | `BulkFolderImportJobFailed` | Optional — consumed by Notifications |

---

## Consumed Integration Events

None. This write model does not subscribe to external events. All inputs arrive via direct API calls or intra-context command dispatch from `BulkFolderImportWorker`.

---

## Worker Processing Flow

`BulkFolderImportWorker` Lambda triggered by `BulkFolderImportJobCreatedMessage` from `media-bulk-folder-imports` SQS queue:

1. Load input (from S3 if `InputStorageKey` present, else inline from job aggregate)
2. Parse input per `InputFormat` (line-delimited, CSV, JSON)
3. Split into chunks of 200 (per `MaxFoldersPerRequest`)
4. For each chunk:
   - Dispatch `BulkCreateFoldersByPathCommand` (existing handler)
   - Collect `succeeded`/`failed` results
   - Dispatch `RecordBulkFolderImportJobBatchResultCommand`
   - Write per-item results to `media-bulk-import-job-items` table
5. After all chunks:
   - Dispatch `CompleteBulkFolderImportJobCommand` (or `FailBulkFolderImportJobCommand` on fatal error)

---

## Input Storage Strategy

| Input Size | Storage | Access Pattern |
|---|---|---|
| ≤10KB | Inline in `BulkFolderImportJob` aggregate event payload | Direct from event |
| >10KB | S3 `media-bulk-import-inputs` bucket | Worker streams from S3 key |

**S3 Key Pattern:** `{tenantId}/folder-imports/{jobId}.{ext}`

---

## Related

- [BulkFolderImportJob Read Model](./bulkfolderimportjob.read-model.md)
- [BulkFolderImportJob API](./bulkfolderimportjob.api.md)
- [Folder Write Model](../Folder/folder.write-model.md)
- [Bulk Operations](../../../../shared/bulk-operations.md)
