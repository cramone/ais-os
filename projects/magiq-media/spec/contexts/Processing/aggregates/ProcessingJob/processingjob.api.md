# ProcessingJob — API

_Context: `Processing`_
_Aggregate: `ProcessingJob`_

---

## Overview

The Processing context exposes **no public HTTP endpoints**. All interactions are internal Lambda-to-Lambda command dispatches and SQS-driven event handlers. There is no `Processing.Endpoints` project.

The table below documents the full internal command and event surface for traceability.

---

## Internal Command Surface

All commands are dispatched via `IApplicationBus` — not via HTTP. `TenantId` is always sourced from the SQS message attribute envelope, never from any command body.

| Command | Dispatched By | Trigger | Description |
|---|---|---|---|
| `CreateProcessingJobCommand` | `AssetUploadedEventHandler` | `media.asset.uploaded` integration event | Creates a `ProcessingJob` in `Queued` state for the uploaded asset |
| `StartProcessingJobCommand` | Processing Worker Lambda | After resolving MediaProfile capabilities from `media-items` read model | Transitions job `Queued → Running`; signals pipeline start |
| `CompleteProcessingJobCommand` | Processing Worker Lambda | On successful pipeline execution | Transitions job `Running → Succeeded`; forwards renditions + metadata; dispatches `CompleteAssetProcessingCommand` to AssetManagement |
| `FailProcessingJobCommand` | Processing Worker Lambda (on error); `SagaTimeoutScanner` (on timeout) | Pipeline error or saga timeout | Transitions job `Running → Failed`; dispatches `FailAssetProcessingCommand` to AssetManagement |

---

## Integration Event Consumers

| Integration Event | Topic / Queue | Handler | Action |
|---|---|---|---|
| `media.asset.uploaded` | `media-processing` SQS queue (SNS fan-out from `media-domain-events`) | `AssetUploadedEventHandler` | Dispatches `CreateProcessingJobCommand` |

---

## Integration Events Published

| Integration Event | SNS Topic | Trigger | Consumer |
|---|---|---|---|
| `media.asset.processing-failed` | `media-domain-events` | `ProcessingJobFailed` domain event | Notifications service — alerts the asset owner |

---

## Command → Event → Projection Traceability

| Trigger | Command | Domain Event | Effect in AssetManagement | Read Model Update |
|---|---|---|---|---|
| `AssetUploadedIntegrationEvent` | `CreateProcessingJobCommand` | `ProcessingJobCreated` | — | `ProcessingJobProjector` → `media-processing-jobs` INSERT |
| Processing Worker starts pipeline | `StartProcessingJobCommand` | `ProcessingJobStarted` | — | `ProcessingJobProjector` → `status = Running` |
| Pipeline succeeds | `CompleteProcessingJobCommand` | `ProcessingJobSucceeded` → `CompleteAssetProcessingCommand` → `AssetProcessingCompleted` | `Asset.Status → Active`; renditions + metadata stamped | `AssetProjector` → `media-assets`, `media-asset-detail` |
| Pipeline fails or saga timeout | `FailProcessingJobCommand` | `ProcessingJobFailed` → `FailAssetProcessingCommand` → `AssetProcessingFailed` | `Asset.Status → ProcessingFailed` | `AssetProjector` → `media-assets`, `media-asset-detail` (status = ProcessingFailed) |

---

## Authorization

All commands are dispatched by internal system principals (`actor_type = "System"`). There are no user-facing auth requirements for this context.

The `SagaTimeoutScanner` Lambda uses an IAM role with permission scoped to the Command Handler's SQS input queue — no JWT required.

---

## Related

- [ProcessingJob Write Model](./processingjob.write-model.md)
- [ProcessingJob Read Model](./processingjob.read-model.md)
- [Processing Context Overview](../../context-overview.md)
- [Processing Business Scenarios](../../business-scenarios.md)
- [Asset API](../../../AssetManagement/aggregates/Asset/asset.api.md)
- [Asset Write Model](../../../AssetManagement/aggregates/Asset/asset.write-model.md)
