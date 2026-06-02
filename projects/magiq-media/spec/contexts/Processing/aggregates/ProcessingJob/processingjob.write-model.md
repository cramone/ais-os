# ProcessingJob — Write Model

_Context: `Processing`_
_Aggregate: `ProcessingJob`_
_Stream prefix: `processing_job_`_

---

## Purpose

Tracks the lifecycle of a single asset processing pipeline execution — from job creation through virus scan, rendition generation, metadata extraction, and terminal outcome. One `ProcessingJob` is created per uploaded asset.

The `ProcessingJob` does **not** own the final asset state. It drives the process and publishes integration events; AssetManagement subscribes and applies the outcomes to the `Asset` aggregate. The two contexts communicate exclusively via integration events on `media-integration-events` — no cross-BC command dispatch.

---

## Invariants

| Rule | Error | Method |
|---|---|---|
| Status must be `Queued` | `InvalidOperation` | `RecordScanResult()`, `Start()` |
| Status must be `Running` | `InvalidOperation` | `Complete()`, `Fail()` |
| `StorageKey` is immutable after `ProcessingJobCreated` | Structural invariant | — |

---

## Properties

| Property | Type | Notes |
|---|---|---|
| `ProcessingJobId` | `ProcessingJobId` | UUID v7. Generated on factory. |
| `TenantId` | `TenantId` | Set from `ProcessingJobCreated` (first field). Immutable. |
| `AssetId` | `AssetId` | The asset being processed. |
| `StorageKey` | `string` | S3 key of the original file. Immutable after creation. |
| `ContentType` | `string` | `MediaContentType` enum value as string. |
| `Status` | `ProcessingJobStatus` | `Queued → Running → Succeeded \| Failed` |
| `Renditions` | `IReadOnlyList<RenditionResult>` | Empty until `ProcessingJobSucceeded`. Empty list on fast-exit path. |
| `Metadata` | `ExtractedMetadata?` | Null until `ProcessingJobSucceeded`. Null on fast-exit path. |
| `FailureReason` | `string?` | Set on `ProcessingJobFailed`. |
| `CompletedAt` | `DateTimeOffset?` | Set on `ProcessingJobSucceeded` or `ProcessingJobFailed`. |
| `CreatedAt` | `DateTimeOffset` | |

---

## Status Lifecycle

```
Queued  → (Start)              → Running
Running → (Complete)           → Succeeded  [terminal]
Running → (Fail)               → Failed     [terminal]
```

**Lifecycle notes:**

- `Queued` → created on `AssetUploadConfirmedIntegrationEvent` receipt (`AssetUploadConfirmedEventHandler`); the `AssetValidationWorker` picks up the job, runs the virus scan, and records the result — status stays `Queued` during scan.
- `Running` → `AssetIngestionSaga` dispatches `StartProcessingJobCommand` after receiving `AssetValidationPassedIntegrationEvent` with `HasProcessingCapability = true`.
- `Succeeded` → Processing Worker calls `CompleteProcessingJobCommand` after pipeline completes. Publishes `ProcessingJobCompletedIntegrationEvent`; AssetManagement subscribes and applies `CompleteAssetProcessingCommand`.
- `Failed` → Processing Worker calls `FailProcessingJobCommand` on error, or `SagaTimeoutScanner` dispatches it on timeout. Publishes `ProcessingJobFailedIntegrationEvent`; AssetManagement subscribes and applies `FailAssetProcessingCommand`.

---

## Value Objects

| Value Object | Description |
|---|---|
| `ProcessingJobId` | UUID v7 string, generated on factory |
| `ProcessingJobStatus` | `Queued \| Running \| Succeeded \| Failed` |
| `RenditionResult` | `{ RenditionType, StorageKey, ContentType, SizeBytes }` — one per generated rendition |
| `ExtractedMetadata` | `{ Width?, Height?, DurationSeconds?, Format?, ExifData }` — technical characteristics extracted from the original file |

**`ExtractedMetadata` fields:**

| Field | Applies To |
|---|---|
| `Format?` | All |
| `Width?`, `Height?` | Image, Video |
| `DurationSeconds?` | Video, Audio |
| `ExifData` | Image (never null; empty dict for non-image) |

---

## Methods (Commands)

| Method | Description | Preconditions |
|---|---|---|
| `ProcessingJob.Create(tenantId, assetId, storageKey, contentType, createdAt)` | Factory. Raises `ProcessingJobCreated`. | — |
| `RecordScanResult(outcome, failureReason, recordedAt)` | Records virus scan / format validation outcome. Raises `ProcessingJobScanResultRecorded`. Status remains `Queued` — scan result is an informational event; the saga drives the next transition. | `Status = Queued` |
| `Start()` | Marks pipeline execution start. Raises `ProcessingJobStarted`. | `Status = Queued` |
| `Complete(renditions, metadata, completedAt)` | Records successful outcome. Raises `ProcessingJobSucceeded`. | `Status = Running` |
| `Fail(reason)` | Records failure. Raises `ProcessingJobFailed`. | `Status = Running` |

---

## Domain Events

| Event | Key Payload Fields | Status Transition |
|---|---|---|
| `ProcessingJobCreated` | `TenantId`†, `JobId`, `AssetId`, `StorageKey`, `ContentType`, `OccurredAt` | → Queued |
| `ProcessingJobScanResultRecorded` | `TenantId`, `JobId`, `AssetId`, `Outcome` (`Passed`/`Failed`/`VirusDetected`), `FailureReason?`, `RecordedAt` | Queued → Queued (no status change) |
| `ProcessingJobStarted` | `TenantId`, `JobId`, `StartedAt` | Queued → Running |
| `ProcessingJobSucceeded` | `TenantId`, `JobId`, `AssetId`, `Renditions[]`, `Metadata?`, `CompletedAt` | Running → Succeeded |
| `ProcessingJobFailed` | `TenantId`, `JobId`, `AssetId`, `Reason`, `FailedAt` | Running → Failed |

† `TenantId` is the **first field** on the creation event per multi-tenancy convention. See [System Spec — Multi-Tenancy](../../../../shared/system-spec.md#multi-tenancy-strategy).

---

## Commands

| Command | Handler | Dispatched By | Result |
|---|---|---|---|
| `CreateProcessingJobCommand(TenantId, AssetId, StorageKey, ContentType)` | `CreateProcessingJobCommandHandler` | `AssetUploadConfirmedEventHandler` (on `AssetUploadConfirmedIntegrationEvent`) | `Result<Unit, DomainError>` |
| `RecordProcessingJobScanResultCommand(TenantId, JobId, Outcome, FailureReason?, RecordedAt)` | `RecordProcessingJobScanResultCommandHandler` | `AssetValidationWorker` after virus scan completes | `Result<Unit, DomainError>` |
| `StartProcessingJobCommand(TenantId, JobId)` | `StartProcessingJobCommandHandler` | `AssetIngestionSaga` on `AssetValidationPassedIntegrationEvent` (when `HasProcessingCapability = true`) | `Result<Unit, DomainError>` |
| `BypassProcessingJobCommand(TenantId, JobId)` | `BypassProcessingJobCommandHandler` | `AssetIngestionSaga` on `AssetValidationPassedIntegrationEvent` (when `HasProcessingCapability = false`) | `Result<Unit, DomainError>` |
| `CompleteProcessingJobCommand(TenantId, JobId, Renditions[], Metadata?)` | `CompleteProcessingJobCommandHandler` | Processing Worker Lambda on pipeline success | `Result<Unit, DomainError>` |
| `FailProcessingJobCommand(TenantId, JobId, Reason)` | `FailProcessingJobCommandHandler` | Processing Worker Lambda on error; `SagaTimeoutScanner` on timeout | `Result<Unit, DomainError>` |


---

## Command Handlers

All handlers:

1. Resolve `TenantId` from the command (Processing context is Lambda-only — no HTTP context; `TenantId` comes from the SQS message attribute on the originating event envelope)
2. Load aggregate via `IProcessingJobRepository`
3. Call single aggregate method
4. Persist via `IProcessingJobRepository.SaveAsync`
5. Return `Result<Unit, DomainError>` — no domain exceptions escape

**`CreateProcessingJobCommandHandler` additional responsibilities:**

- Before creating, calls `IProcessingJobRepository.GetByAssetIdAsync(tenantId, command.AssetId)`. If a job already exists for the `AssetId`, returns `Result.Success(Unit.Value)` — idempotent no-op. This handles duplicate SQS delivery of `AssetUploadedIntegrationEvent` without creating duplicate jobs.
- Creates a new `ProcessingJob` via factory only when no existing job is found.
- Does **not** call `Start()` — the job sits in `Queued` until the Processing Worker picks it up from SQS and explicitly starts it.

**`RecordProcessingJobScanResultCommandHandler` responsibilities:**

- Loads `ProcessingJob` by `JobId`.
- Calls `job.RecordScanResult(command.Outcome, command.FailureReason, command.RecordedAt)`.
- Persists. The resulting `ProcessingJobScanResultRecorded` domain event is mapped to `ProcessingJobScanResultIntegrationEvent` (via `ProcessingDomainEventMapper`) and published to `media-integration-events` SNS.
- AssetManagement subscribes and dispatches `RecordValidationResultCommand` on its own `Asset` aggregate.

**`CompleteProcessingJobCommandHandler` additional responsibilities:**

- After persisting `ProcessingJobSucceeded`, `ProcessingJobCompletedIntegrationEvent` is published. AssetManagement subscribes and dispatches `CompleteAssetProcessingCommand`.
- `Renditions` and `Metadata` are forwarded verbatim from the Processing Worker's pipeline output.

**`FailProcessingJobCommandHandler` additional responsibilities:**

- After persisting `ProcessingJobFailed`, `ProcessingJobFailedIntegrationEvent` is published. AssetManagement subscribes and dispatches `FailAssetProcessingCommand`.

**Write model service interfaces required:**

```csharp
interface IProcessingJobRepository {
    Task<ProcessingJob?> GetByIdAsync(TenantId tenantId, ProcessingJobId id, CancellationToken ct);
    Task<ProcessingJob?> GetByAssetIdAsync(TenantId tenantId, AssetId assetId, CancellationToken ct);
    Task SaveAsync(ProcessingJob job, CancellationToken ct);
}
```

---

## Published Integration Events

Published inline by Processing domain event handlers (`Processing.WriteModel`) immediately after each state transition is persisted. All events target the `media-integration-events` SNS topic.

Note: `AssetProcessingCompletedIntegrationEvent` and `AssetProcessingFailedIntegrationEvent` are distinct events published by **AssetManagement** (triggered by `AssetProcessingCompleted` / `AssetProcessingFailed`) after AssetManagement consumes and processes the events below. Processing publishes its own job-level events; AssetManagement translates them into asset-level state transitions and publishes the asset-scoped integration events.

| Integration Event | Source Domain Event | Consumers |
|---|---|---|
| `ProcessingJobScanResultIntegrationEvent` (`media.processingjob.scan-result`) | `ProcessingJobScanResultRecorded` | AssetManagement `ProcessingJobScanResultEventHandler` — dispatches `RecordValidationResultCommand`; AssetManagement then publishes `AssetValidationPassedIntegrationEvent` (or failure variant) |
| `ProcessingJobStartedIntegrationEvent` | `ProcessingJobStarted` | AssetManagement `ProcessingJobStartedEventHandler` — dispatches `StartAssetProcessingCommand` to transition asset `Validating → Processing` |
| `ProcessingJobCompletedIntegrationEvent` | `ProcessingJobSucceeded` | AssetManagement `ProcessingJobCompletedEventHandler` — dispatches `CompleteAssetProcessingCommand` with renditions and metadata; Billing (capability-filtered) |
| `ProcessingJobFailedIntegrationEvent` | `ProcessingJobFailed` | AssetManagement `ProcessingJobFailedEventHandler` — dispatches `FailAssetProcessingCommand`; Notifications (owner alert); SagaOrchestrator (saga completion) |

---

## Consumed Integration Events

Consumed via the `media-cross-module-events` SQS queue.

**From AssetManagement — consumer: `AssetUploadConsumer`**

Creates a `ProcessingJob` aggregate for each uploaded asset so the Processing Worker has a job record to claim before starting the pipeline.

| Integration Event                      | Source          | Command Dispatched                                                                                                                     |
| -------------------------------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `AssetUploadConfirmedIntegrationEvent` | AssetManagement | `CreateProcessingJobCommand(TenantId, AssetId, StorageKey, ContentType)` — idempotent; no-op if a job already exists for the `AssetId` |

The `AssetUploadConfirmedIntegrationEvent` is consumed from the `media-processing` SQS queue (subscribed to `media-integration-events` SNS with `EventType = media.asset.upload-confirmed` filter). `AssetValidationWorker` is triggered by this same event — it resolves the `ProcessingJobId` via `AssetProcessingJobIndex`, runs the virus scan, and dispatches `RecordProcessingJobScanResultCommand`.

---

## AssetIngestionSaga Relationship

The `AssetIngestionSaga` is a separate construct (in `media-sagas` DynamoDB) managed by the `SagaOrchestrator` Lambda. It is **not** part of the `ProcessingJob` aggregate. The saga:

- Is created on `AssetValidationPassedIntegrationEvent` (not on `ProcessingJobCreated`) — triggered after AssetManagement records the scan result and publishes the event
- Reads `HasProcessingCapability` from the event payload to select the processing branch
- Holds a `TimeoutAt` per content type (Video = 4h; others = shorter)
- Dispatches `FailProcessingJobCommand` on timeout via `SagaTimeoutScanner`
- Transitions to `Complete` on `ProcessingJobSucceeded` or `ProcessingJobFailed`

See [System Spec — Saga Coordination](../../../../shared/system-spec.md#saga-coordination-patterns).

---

## Write-Side Reference Models

### `AssetProcessingJobIndex`

A write-side reference model (implements `IReferenceModel`) that allows the Processing Worker to resolve the `ProcessingJobId` for a given asset without a cross-aggregate query.

**Why it exists:** The `AssetValidationWorker` is triggered by `AssetUploadConfirmedIntegrationEvent` (consumed from the `media-processing` SQS queue). At that point the worker knows the `AssetId` but not the `JobId` — the `ProcessingJob` was created separately by `AssetUploadConfirmedEventHandler` in response to the same event. The index provides a keyed lookup so the worker can resolve the `ProcessingJobId` and dispatch `RecordProcessingJobScanResultCommand` with the correct `JobId`.

**Shape:**

| Field | Type | Notes |
|---|---|---|
| `TenantId` | `TenantId` | Partition key component |
| `AssetId` | `ProcessingAssetId` | Sort key component — the lookup key |
| `JobId` | `ProcessingJobId` | The correlated `ProcessingJob` identifier |
| `StartedAt` | `DateTimeOffset?` | Null until `ProcessingJobStarted` projected |
| `Status` | `ProcessingJobStatus` | Mirrors current job statu