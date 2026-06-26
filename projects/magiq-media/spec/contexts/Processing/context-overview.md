# Processing — Context Overview

_Context: `Processing`_

---

## Purpose

The Processing context owns the asset ingestion pipeline — from upload confirmation through virus scan, rendition generation, and metadata extraction. It owns a first-class `ProcessingJob` aggregate that provides durability, idempotency, and observable job lifecycle across Lambda invocations. The Processing Worker Lambda reads `AssetUploadConfirmedIntegrationEvent` from the `media-processing` SQS queue, runs the virus scan, and publishes `ProcessingJobScanResultIntegrationEvent`. AssetManagement subscribes and applies the result to the `Asset` aggregate. Processing and AssetManagement communicate exclusively via integration events on `media-integration-events` SNS — no cross-BC command dispatch occurs.

---

## Responsibilities

- Validate uploaded files (format, size, content type)
- Run virus scan on all media-assets regardless of capability
- Generate renditions for media-assets whose owning MediaProfile has the `Processing` capability
- Extract technical metadata (EXIF, codec, dimensions, frame rate, archive manifest) for processed media-assets
- Fast-exit for document media-assets (MediaProfile lacks `Processing` capability) — virus scan only
- Maintain `ProcessingJob` aggregate lifecycle (Queued → Running → Succeeded | Failed)
- Publish processing outcome integration events; AssetManagement subscribes and applies outcomes to the `Asset` aggregate
- Participate in `AssetIngestionSaga` timeout compensation via `SagaTimeoutScanner`

---

## Services

| Service | Runtime | Trigger | Responsibility |
|---|---|---|---|
| `Processing Worker` | Lambda | SQS `media-processing` queue (`AssetUploadConfirmedIntegrationEvent`) | Receives `AssetUploadConfirmedIntegrationEvent`; creates `ProcessingJob`; runs virus scan via `AssetValidationWorker`; dispatches `RecordProcessingJobScanResultCommand`; publishes `ProcessingJobScanResultIntegrationEvent`. For capable assets: runs rendition/metadata pipeline after `StartProcessingJobCommand` is dispatched by SagaOrchestrator. Stateless executor — saga routing owned by SagaOrchestrator. |
| `SagaTimeoutScanner` | Lambda | CloudWatch schedule (every 5 minutes) | Scans `media-sagas` for timed-out processing jobs; dispatches `FailProcessingJobCommand` |

---

## Aggregate Ownership

This context owns the **`ProcessingJob`** aggregate. All write-side Asset state lives in `Asset` (AssetManagement context). Processing outcomes are communicated as integration events published to `media-integration-events` SNS. AssetManagement subscribes via `media-cross-module-events` and dispatches its own commands:

| Processing Integration Event | AssetManagement Handler | AssetManagement Command | Asset Transition |
|---|---|---|---|
| `ProcessingJobScanResultIntegrationEvent` | `ProcessingJobScanResultEventHandler` | `RecordValidationResultCommand` | Emits `AssetValidationPassed` (or failure) |
| `ProcessingJobStartedIntegrationEvent` | `ProcessingJobStartedEventHandler` | `StartAssetProcessingCommand` | `Validating → Processing` |
| `ProcessingJobCompletedIntegrationEvent` | `ProcessingJobCompletedEventHandler` | `CompleteAssetProcessingCommand` | `Processing → Active` |
| `ProcessingJobFailedIntegrationEvent` | `ProcessingJobFailedEventHandler` | `FailAssetProcessingCommand` | `Processing → ProcessingFailed` |

---

## Pipeline Logic

```
[ProcessingWorker Lambda — media-processing SQS]
AssetUploadConfirmedIntegrationEvent
    │
    ├─ AssetValidationWorker
    │       ├─ Resolve ProcessingJobId via AssetProcessingJobIndex (AssetId → JobId)
    │       ├─ Run virus scan
    │       └─ Dispatch RecordProcessingJobScanResultCommand
    │               └─ ProcessingJob.RecordScanResult() → ProcessingJobScanResultRecorded
    │                       └─ Publish ProcessingJobScanResultIntegrationEvent (SNS)
    │                                                       ▲
    │                          [ProcessingWorker terminates here]
    │
    │   [EventConsumers Lambda — media-cross-module-events SQS]
    │   [AssetManagement subscribes — ProcessingJobScanResultEventHandler]
    │       └─ RecordValidationResultCommand → Asset.RecordValidationResult()
    │               ├─ Resolves HasProcessingCapability via IMediaItemCapabilityService
    │               └─ Emits AssetValidationPassed (HasProcessingCapability, ...) → SNS
    │
    │   [SagaOrchestrator Lambda — media-sagas SQS]
    │   [AssetIngestionSaga handles AssetValidationPassedIntegrationEvent]
    │       │
    │       ├─ HasProcessingCapability = false → BypassProcessingJobCommand
    │       │       └─ ProcessingJobBypassed → ProcessingJobBypassedIntegrationEvent → AM: Validating → Active
    │       │
    │       └─ HasProcessingCapability = true → StartProcessingJobCommand
    │               └─ ProcessingJobStarted → ProcessingJobStartedIntegrationEvent → AM: Validating → Processing
    │
    │   [ProcessingWorker Lambda — StartProcessingJobCommand triggers rendition pipeline]
    │       ├─ Image → Sharp / ImageMagick (Lambda layer) → renditions + EXIF
    │       ├─ Video → MediaConvert job (async; completion via EventBridge → SQS)
    │       ├─ Audio → rendition generation (Lambda layer)
    │       ├─ Document / Archive → no renditions; metadata only
    │       └─ Dispatch CompleteProcessingJobCommand (or FailProcessingJobCommand on error)
    │               └─ ProcessingJobSucceeded/Failed → integration event → AM: Processing → Active/Failed
```

---

## Rendition and Metadata Tools

| Content Type | Rendition Tool | Metadata Tool |
|---|---|---|
| Image | Sharp / ImageMagick (Lambda layer) | ExifTool (Lambda layer) |
| Video | AWS MediaConvert (async) | ExifTool |
| Audio | Lambda layer | ExifTool |
| Document | None | ExifTool |
| Archive | None | File inspection (CompressionFormat, FileCount, etc.) |

---

## S3 Paths

| Asset Type | Bucket | Key Pattern |
|---|---|---|
| Media originals (Processing capability present, or standalone) | `media-source` | `{tenantId}/{shard}/{assetId}/original.{ext}` |
| Renditions | `media-renditions` | `{tenantId}/{shard}/{assetId}/{renditionType}.{ext}` |
| Document media-assets (Processing capability absent) | `media-documents` | `{tenantId}/{shard}/{assetId}/document.{ext}` |

`{shard}` = last 4 hex chars of UUID v7 `AssetId` (no dashes) — 65,536 distinct prefixes, no hashing needed.

---

## AssetIngestionSaga

The `AssetIngestionSaga` is created when `AssetValidationPassedIntegrationEvent` is received and guards against stuck processing jobs:

- Created with `TimeoutAt = StartedAt + N hours` (timeout varies by content type: Video = 4h, others shorter)
- Receives `ProcessingJobSucceeded` or `ProcessingJobFailed` → transitions to `Complete`
- If neither arrives before `TimeoutAt`: `SagaTimeoutScanner` dispatches `FailProcessingJobCommand({reason: "ProcessingTimeout"})` — idempotent; no-op if job already transitioned

Saga state is persisted in `media-sagas` (DynamoDB). The `SagaOrchestrator` Lambda manages lifecycle.

---

## Integration Events

### Published

Published inline by the `ProcessingJob` domain event handlers in `Processing.WriteModel` immediately after each state transition is persisted. All events target the `media-integration-events` SNS topic.

| C# Record Type | Trigger Domain Event | Consumers |
|---|---|---|
| `ProcessingJobScanResultIntegrationEvent` | `ProcessingJobScanResultRecorded` | AssetManagement (`ProcessingJobScanResultEventHandler` → `RecordValidationResultCommand`) |
| `ProcessingJobStartedIntegrationEvent` | `ProcessingJobStarted` | AssetManagement (`ProcessingJobStartedEventHandler`) |
| `ProcessingJobCompletedIntegrationEvent` | `ProcessingJobSucceeded` | AssetManagement (`ProcessingJobCompletedEventHandler`), Billing (capability-filtered) |
| `ProcessingJobFailedIntegrationEvent` | `ProcessingJobFailed` | AssetManagement (`ProcessingJobFailedEventHandler`), Notifications |

### Consumed

#### ProcessingWorker Lambda (`media-processing` SQS — filtered: `AssetUploadConfirmedIntegrationEvent` only)

| Integration Event | Source | Handler | Action |
|---|---|---|---|
| `AssetUploadConfirmedIntegrationEvent` | AssetManagement | `AssetUploadConfirmedEventHandler` | Creates `ProcessingJob`; `AssetValidationWorker` runs virus scan; `RecordProcessingJobScanResultCommand` dispatched |

#### SagaOrchestrator Lambda (`media-sagas` SQS)

The following events drive `AssetIngestionSaga` coordination and are consumed by the **SagaOrchestrator** — not by the ProcessingWorker:

| Integration Event | Source | Handler | Action |
|---|---|---|---|
| `ProcessingJobCreatedIntegrationEvent` | Processing (self) | `ProcessingJobCreatedSagaHandler` | Initialises `AssetIngestionSaga` in `AwaitingValidation` state |
| `AssetValidationPassedIntegrationEvent` | AssetManagement | `AssetValidationPassedSagaHandler` | Advances `AssetIngestionSaga`; dispatches `StartProcessingJobCommand` or `BypassProcessingJobCommand` based on `HasProcessingCapability` |
| `AssetProcessingCompletedIntegrationEvent` | AssetManagement | `AssetProcessingCompletedSagaHandler` | Closes `AssetIngestionSaga` on success |
| `AssetProcessingFailedIntegrationEvent` | AssetManagement | `AssetProcessingFailedSagaHandler` | Closes `AssetIngestionSaga` on failure |

## Integration Event Contracts

### Published

#### `ProcessingJobScanResultIntegrationEvent`

```csharp
[MessageType("media.processingjob.scan-result")]
record ProcessingJobScanResultIntegrationEvent(
    string TenantId,
    string JobId,
    string AssetId,
    string Outcome,        // "Passed" | "Failed" | "VirusDetected"
    string? FailureReason,
    DateTimeOffset RecordedAt,
    long EventVersion
);
```

#### `ProcessingJobStartedIntegrationEvent`

```csharp
record ProcessingJobStartedIntegrationEvent(
    string TenantId,
    string JobId,
    string AssetId,
    DateTimeOffset StartedAt
);
```

#### `ProcessingJobCompletedIntegrationEvent`

```csharp
record ProcessingJobCompletedIntegrationEvent(
    string TenantId,
    string JobId,
    string AssetId,
    IReadOnlyList<ProcessingRenditionDto> Renditions,
    ProcessingMetadataDto? Metadata,    // null for document media-assets (no Processing capability)
    DateTimeOffset CompletedAt
);

record ProcessingRenditionDto(
    string RenditionType,
    string StorageKey,
    string ContentType,
    long SizeBytes
);

record ProcessingMetadataDto(
    int? Width,
    int? Height,
    decimal? DurationSeconds,
    string? Format,
    IReadOnlyDictionary<string, string> ExifData
);
```

> `AssetManagement.ProcessingEventConsumer` maps `Renditions` to `Rendition` value objects and `Metadata` to `AssetMetadata` before dispatching `CompleteAssetProcessingCommand`. `Renditions` is empty for document media-assets.

#### `ProcessingJobFailedIntegrationEvent`

```csharp
record ProcessingJobFailedIntegrationEvent(
    string TenantId,
    string JobId,
    string AssetId,
    string FailureCategory,    // e.g. "ProcessingError" | "Timeout" | "ValidationFailure"
    string Reason,
    DateTimeOffset FailedAt
);
```

> `AssetManagement.ProcessingEventConsumer` maps `FailureCategory` via `Enum.Parse<FailureCategory>` before dispatching `FailAssetProcessingCommand`.

---

## External Dependencies

| Dependency | Type | Direction |
|---|---|---|
| `AssetProcessingJobIndex` read model | DynamoDB (Processing) | Inbound — resolve ProcessingJobId from AssetId for `AssetValidationWorker` |
| `media-source`, `media-documents` S3 buckets | S3 | Inbound — read uploaded files |
| `media-renditions` S3 bucket | S3 | Outbound — write generated renditions |
| `media-integration-events` SNS | AWS SNS | Outbound — publish `ProcessingJobScanResultIntegrationEvent`, `ProcessingJobStartedIntegrationEvent`, `ProcessingJobCompletedIntegrationEvent`, `ProcessingJobFailedIntegrationEvent` |
| AWS MediaConvert | External AWS service | Outbound — async video encoding |

---

## Ubiquitous Language

| Term | Meaning |
|---|---|
| Processing Worker | The Lambda that drives the ProcessingJob aggregate — runs the virus scan (`AssetValidationWorker`) and, for capable media-assets, the rendition/metadata pipeline (`AssetProcessingWorker`) |
| ProcessingJob | Aggregate tracking a single asset's processing lifecycle (Queued → Running → Succeeded \| Failed) |
| Rendition | A processed derivative of the original file (thumbnail, compressed, transcoded) |
| Document asset | An asset whose owning MediaProfile lacks the `Processing` capability — virus scan only, no renditions; `AssetIngestionSaga` routes to bypass path |
| Fast-exit / Bypass | `AssetIngestionSaga` path for document media-assets: dispatches `BypassProcessingJobCommand` → `ProcessingJobBypassedIntegrationEvent` → AM activates asset directly |
| SagaTimeoutScanner | Lambda on CloudWatch schedule; finds timed-out saga instances and dispatches FailProcessingJobCommand |
| AssetIngestionSaga | Saga that guards the `Validating → Processing → Active/Failed` transition window; created on `AssetValidationPassedIntegrationEvent` |
| Shard | Last 4 hex chars of AssetId UUID v7 — used as S3 key prefix for partition distribution |

---

## Related

- [Processing Business Scenarios](./business-scenarios.md)
- [ProcessingJob Write Model](./aggregates/ProcessingJob/processingjob.write-model.md)
- [ProcessingJob Read Model](./aggregates/ProcessingJob/processingjob.read-model.md)
- [Asset Write Model](../AssetManagement/aggregates/Asset/asset.write-model.md)
- [Asset Read Model](../AssetManagement/aggregates/Asset/asset.read-model.md)
- [AssetManagement Context Overview](../AssetManagement/context-overview.md)
