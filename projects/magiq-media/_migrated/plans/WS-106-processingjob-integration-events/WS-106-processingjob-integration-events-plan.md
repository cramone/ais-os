---
id: MM-146
type: plan
project: magiq-media
workstream: WS-106-processingjob-integration-events
repo: magiq-media
tags: [magiq-media, processing, processingjob, integration-events, mapper, sns, timeout-recovered, encode-result, mediaconvert, eventbridge]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Process wire — additive
source: alignment-sweep-2026-10-15 cell ProcessingJob × integration-events
---

# WS-106 — ProcessingJob integration events: distinct `timeout-recovered` type + `encode-result` consumer

**Target repo:** `magiq-media`
**Depends on:** —

## Problem

Spec names 8 ProcessingJob integration event types; code handles 6 distinct publication types + 1 missing publication (timeout-recovered) + 1 missing consumer (encode-result, EventBridge-forwarded by MediaConvert — not published by magiq-media).

**Gap 1 — `media.processingjob.timeout-recovered` unbuilt (publication-side).** `ProcessingJobTimeoutRecovered` domain event maps to `ProcessingJobCompletedIntegrationEvent` (completion reuse) rather than a distinct type. The reuse is intentional for the intra-BC hop ("Internal Processing -> AssetManagement hop reuses the completion contract — the distinct external correction is published at the Asset level") but the catalog names a separate `media.processingjob.timeout-recovered` type that must be emitted alongside.

**Gap 2 — `media.processingjob.encode-result` unbuilt (consumption-side).** Surfaced in Arnica review re-diff. Not published by magiq-media — MediaConvert state changes are forwarded by EventBridge to `media-processing` SQS queue, framed as `media.processingjob.encode-result`. The spec names `MediaConvertJobCompletedHandler` on `media-processing` as the consumer: on `COMPLETE` dispatch `CompleteProcessingJobCommand`; on `ERROR` dispatch `FailProcessingJobCommand(ProcessingError)`; JobId resolved from the callback's `ClientRequestToken` (which `AssetProcessingWorker` stamps with `ProcessingJobId` when submitting the MediaConvert job for video). Duplicate delivery acked — aggregate's completion guards refuse a second complete. Zero `MediaConvert`/`encode-result` files exist in `src/modules/Processing/`.

Current mapper:

```csharp
public IEnumerable<IIntegrationEvent> Map(ProcessingJobTimeoutRecovered e)
{
    yield return new ProcessingJobCompletedIntegrationEvent(...);
}
```

Spec:

| type | domain event | consumer |
|---|---|---|
| `media.processingjob.timeout-recovered` | `ProcessingJobTimeoutRecovered` | AssetManagement (intra-BC — `RecoverAssetProcessingTimeoutCommand`) |

## Code state

| spec type | code | status |
|---|---|---|
| `media.processingjob.created` | `ProcessingJobCreatedIntegrationEvent` | ✓ publication |
| `media.processingjob.scan-result` | `ProcessingJobScanResultIntegrationEvent` | ✓ publication |
| `media.processingjob.started` | `ProcessingJobStartedIntegrationEvent` | ✓ publication |
| `media.processingjob.completed` | `ProcessingJobCompletedIntegrationEvent` | ✓ publication |
| `media.processingjob.failed` | `ProcessingJobFailedIntegrationEvent` | ✓ publication |
| `media.processingjob.bypassed` | `ProcessingJobBypassedIntegrationEvent` | ✓ publication |
| `media.processingjob.timeout-recovered` | — reuses `completed` contract today | **missing publication** |
| `media.processingjob.encode-result` | — | **missing consumption** — EventBridge-forwarded, needs `MediaConvertJobCompletedHandler` on `media-processing` SQS |

## What the spec requires

**Gap 1 — timeout-recovered publication:**

- `ProcessingJobTimeoutRecoveredIntegrationEvent { TenantId, JobId, AssetId, RecoveredAt, Renditions[], Metadata?, AggregateVersion }` under `Processing.Contracts/Events/`.
- `ProcessingDomainEventMapper.Map(ProcessingJobTimeoutRecovered)` yields a `ProcessingJobTimeoutRecoveredIntegrationEvent` in addition to (or in place of) the `ProcessingJobCompletedIntegrationEvent` reuse — audit `RecoverAssetProcessingTimeoutCommand` handler to decide whether the completion reuse continues as a bridge or is retired.
- CDK filter-policy entry in `cdk-magiq-media` admits `media.processingjob.timeout-recovered` to AssetManagement's `media-processing-events` consumer queue.

**Gap 2 — encode-result consumer:**

- `MediaConvertJobCompletedHandler` under `Processing.WriteModel/IntegrationEvents/Consuming/Handlers/` consumes `media.processingjob.encode-result` from `media-processing` SQS. On `COMPLETE`: dispatches `CompleteProcessingJobCommand` with the renditions + metadata MediaConvert produced. On `ERROR`: dispatches `FailProcessingJobCommand(ProcessingError)` with MediaConvert's error message. JobId resolved from callback's `ClientRequestToken`. Duplicate delivery acked (aggregate's completion guards refuse second complete).
- `ProcessingJobEncodeResultIntegrationEvent` contract record under `Processing.Contracts/Events/` for the consumed shape (MediaConvert JSON forwarded by EventBridge).
- `AssetProcessingWorker` must stamp `ClientRequestToken = ProcessingJobId` when submitting MediaConvert jobs for video (verify at Phase 0 — may already be in code).
- CDK EventBridge rule in `cdk-magiq-media`: MediaConvert `COMPLETE` + `ERROR` state changes → forwarded to `media-processing` SQS as `media.processingjob.encode-result` on body-scope.
- `media-processing` SQS filter policy (`cdk-magiq-media`) admits `media.processingjob.encode-result` to the `type` allowlist (per `event-store-and-messaging.md § 416`).

## Wire-visibility

- Process wire — additive on timeout-recovered publication. If reuse-emission is retired in the same PR, that's a Process wire — breaking shift for any current subscriber filtering on `completed`. Audit before deciding.
- Process wire — additive on encode-result consumer. Not currently emitted anywhere; adding the handler + EventBridge rule turns on the MediaConvert → ProcessingJob completion path that is dark today. Video encodes submitted to MediaConvert never report back — they'd time out and recover via `ProcessingJobTimeoutRecovered` only (which is the forgiveness path, not the success path).

## Scope boundary

**Gap 1:** Contract record + mapper edit + CDK filter policy. No domain-event change (`ProcessingJobTimeoutRecovered` exists). `RecoverAssetProcessingTimeoutCommand` handler consumer wiring — audit under this plan; migrate if needed.

**Gap 2:** Contract record + consumer handler + EventBridge rule + SQS filter-policy admission. No domain event (encode-result is an infra callback, not an aggregate event). The two existing commands (`CompleteProcessingJobCommand`, `FailProcessingJobCommand`) are dispatched from the handler — no new commands.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-106 (plan MM-146). Audit `ProcessingDomainEventMapper.Map(ProcessingJobTimeoutRecovered)` + `AssetProcessingTimeoutRecoveredSagaHandler` before deciding whether to retire the `completed`-reuse emission.

## Phase 0 — Audit

- [ ] Trace `RecoverAssetProcessingTimeoutCommand` handler — current source: `ProcessingJobCompletedIntegrationEvent` or distinct?
- [ ] Decide: dual-emit (completion + timeout-recovered) for one release, then retire; or hard-cut.
- [ ] Confirm no `MediaConvertJobCompletedHandler` / encode-result consumer exists in `src/modules/Processing/` (sanity — zero hits at re-diff time 2026-10-18)
- [ ] Audit `AssetProcessingWorker` MediaConvert-submit path: does it stamp `ClientRequestToken = ProcessingJobId`? If not, add under Phase 2b

## Phase 1 — Timeout-recovered contract + mapper

- [ ] `ProcessingJobTimeoutRecoveredIntegrationEvent` under `Processing.Contracts/Events/`
- [ ] `ProcessingDomainEventMapper.Map(ProcessingJobTimeoutRecovered)` yields `ProcessingJobTimeoutRecoveredIntegrationEvent` + (optional transition) `ProcessingJobCompletedIntegrationEvent`

## Phase 2 — Encode-result contract + consumer handler

- [ ] `ProcessingJobEncodeResultIntegrationEvent` contract record under `Processing.Contracts/Events/` matching the MediaConvert state-change shape (JobId, State ∈ {COMPLETE,ERROR}, Renditions[]?, Metadata?, ErrorMessage?)
- [ ] `MediaConvertJobCompletedHandler` under `Processing.WriteModel/IntegrationEvents/Consuming/Handlers/`
  - [ ] Consumes `media.processingjob.encode-result` from `media-processing` SQS
  - [ ] Resolves `ProcessingJobId` from `ClientRequestToken`
  - [ ] On `COMPLETE`: dispatches `CompleteProcessingJobCommand` with renditions + metadata
  - [ ] On `ERROR`: dispatches `FailProcessingJobCommand(ProcessingError)` with MediaConvert error message
  - [ ] Reads tenant from `executionContext.TenantId` (not from the forwarded event body — tenant resolution comes from the `ProcessingJob`'s own tenant on JobId lookup)
  - [ ] Duplicate delivery acked (aggregate's completion guards refuse second complete)

## Phase 2b — AssetProcessingWorker MediaConvert-submit audit

- [ ] Confirm MediaConvert submit site stamps `ClientRequestToken = ProcessingJobId` (per processingjob.write-model.md). If missing, add it under this plan — the consumer handler can't resolve JobId without it.

## Phase 3 — CDK coordination

- [ ] **Precondition:** every existing subscription on `media-integration-events` migrated to `FilterPolicyScope: MessageBody` (per `docs/breaking-changes.md § Cross-cutting ordering constraint`). Cross-cutting prerequisite for `.timeout-recovered` publication; does not apply to `.encode-result` which rides EventBridge → SQS directly
- [ ] `cdk-magiq-media` SNS filter-policy: AssetManagement `media-processing-events` consumer queue admits `media.processingjob.timeout-recovered` on body-scope
- [ ] `cdk-magiq-media` EventBridge rule: MediaConvert `COMPLETE` + `ERROR` state changes framed as `media.processingjob.encode-result`, forwarded to `media-processing` SQS
- [ ] `cdk-magiq-media` `media-processing` SQS filter-policy allowlist includes `media.processingjob.encode-result` (per `event-store-and-messaging.md § SQS queue allowlists`)

## Phase 4 — Consumer migration (timeout-recovered)

- [ ] `AssetProcessingTimeoutRecoveredSagaHandler` consumes the new type (if migration path chosen)
- [ ] Dual-handler window for one release if retiring reuse

## Phase 5 — Tests

- [ ] Integration: `ProcessingJobTimeoutRecovered` → SNS → body carries `type = media.processingjob.timeout-recovered`
- [ ] Integration: AssetManagement consumer routes `timeout-recovered` correctly
- [ ] Integration: MediaConvert COMPLETE → EventBridge → `media-processing` → `MediaConvertJobCompletedHandler` → `CompleteProcessingJobCommand` → ProcessingJob transitions to Completed with renditions + metadata
- [ ] Integration: MediaConvert ERROR → `FailProcessingJobCommand(ProcessingError)` → ProcessingJob transitions to Failed with MediaConvert error message
- [ ] Integration: duplicate MediaConvert callback → second dispatch idempotent (aggregate guards refuse)
- [ ] Unit: `ClientRequestToken` parsing resolves `ProcessingJobId` correctly

## Phase 6 — Communicate change

- [ ] Breaking-changes.md entry — Process wire additive (+ breaking shift if reuse retired)

## Phase 7 — Ship

- [ ] PR to `develop` (magiq-media) + `spec/initial-alignment` (cdk-magiq-media)

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-146 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-106 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell ProcessingJob × integration-events; 1 missing type `timeout-recovered`; current code reuses `completed` contract for the intra-BC hop)
- 2026-10-18: re-diffed under Arnica review fix for finding #8 (catalog Phase 1 regression). Added `media.processingjob.encode-result` → 2nd missing type on **consumption** side (EventBridge-forwarded from MediaConvert, not emitted by magiq-media). Zero `MediaConvert`/`encode-result` files in `src/modules/Processing/` at re-diff time. Scope: 1 contract + 1 mapper (timeout-recovered) + **1 contract + 1 consumer handler + 1 EventBridge rule + 1 SQS allowlist entry** (encode-result). Phase 2 new (encode-result handler). Phase 2b new (AssetProcessingWorker ClientRequestToken audit). Phase 3 CDK gains EventBridge rule + SQS allowlist entry. Phase 5 Tests expanded with 4 MediaConvert integration tests. Without this, video encodes submitted to MediaConvert never report back; they'd fall through to the timeout-recovered forgiveness path only. Title + Problem + What-spec-requires + Scope boundary + tags all updated.
