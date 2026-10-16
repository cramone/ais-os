---
id: MM-146
type: plan
project: magiq-media
workstream: WS-106-processingjob-integration-events
repo: magiq-media
tags: [magiq-media, processing, processingjob, integration-events, mapper, sns, timeout-recovered]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Process wire — additive
source: alignment-sweep-2026-10-15 cell ProcessingJob × integration-events
---

# WS-106 — ProcessingJob integration events: distinct `timeout-recovered` type

**Target repo:** `magiq-media`
**Depends on:** —

## Problem

Spec names 7 ProcessingJob integration event types; code publishes 6 distinct types. `media.processingjob.timeout-recovered` is unbuilt — `ProcessingJobTimeoutRecovered` domain event maps to `ProcessingJobCompletedIntegrationEvent` (completion reuse) rather than a distinct type. The reuse is intentional for the intra-BC hop ("Internal Processing -> AssetManagement hop reuses the completion contract — the distinct external correction is published at the Asset level") but the catalog names a separate `media.processingjob.timeout-recovered` type that must be emitted alongside.

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
| `media.processingjob.created` | `ProcessingJobCreatedIntegrationEvent` | ✓ |
| `media.processingjob.scan-result` | `ProcessingJobScanResultIntegrationEvent` | ✓ |
| `media.processingjob.started` | `ProcessingJobStartedIntegrationEvent` | ✓ |
| `media.processingjob.completed` | `ProcessingJobCompletedIntegrationEvent` | ✓ |
| `media.processingjob.failed` | `ProcessingJobFailedIntegrationEvent` | ✓ |
| `media.processingjob.bypassed` | `ProcessingJobBypassedIntegrationEvent` | ✓ |
| `media.processingjob.timeout-recovered` | — | **missing** |

## What the spec requires

- `ProcessingJobTimeoutRecoveredIntegrationEvent { TenantId, JobId, AssetId, RecoveredAt, Renditions[], Metadata?, AggregateVersion }` under `Processing.Contracts/Events/`.
- `ProcessingDomainEventMapper.Map(ProcessingJobTimeoutRecovered)` yields a `ProcessingJobTimeoutRecoveredIntegrationEvent` in addition to (or in place of) the `ProcessingJobCompletedIntegrationEvent` reuse — audit `RecoverAssetProcessingTimeoutCommand` handler to decide whether the completion reuse continues as a bridge or is retired.
- CDK filter-policy entry in `cdk-magiq-media` admits `media.processingjob.timeout-recovered` to AssetManagement's `media-processing-events` consumer queue.

## Wire-visibility

- Process wire — additive (new type). If reuse-emission is retired in the same PR, that's a Process wire — breaking shift for any current subscriber filtering on `completed`. Audit before deciding.

## Scope boundary

- Contract record + mapper edit + CDK filter policy.
- No domain-event change (`ProcessingJobTimeoutRecovered` exists).
- `RecoverAssetProcessingTimeoutCommand` handler consumer wiring — audit under this plan; migrate if needed.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-106 (plan MM-146). Audit `ProcessingDomainEventMapper.Map(ProcessingJobTimeoutRecovered)` + `AssetProcessingTimeoutRecoveredSagaHandler` before deciding whether to retire the `completed`-reuse emission.

## Phase 0 — Audit

- [ ] Trace `RecoverAssetProcessingTimeoutCommand` handler — current source: `ProcessingJobCompletedIntegrationEvent` or distinct?
- [ ] Decide: dual-emit (completion + timeout-recovered) for one release, then retire; or hard-cut.

## Phase 1 — Contract record

- [ ] `ProcessingJobTimeoutRecoveredIntegrationEvent` under `Processing.Contracts/Events/`

## Phase 2 — Mapper

- [ ] `ProcessingDomainEventMapper.Map(ProcessingJobTimeoutRecovered)` yields `ProcessingJobTimeoutRecoveredIntegrationEvent` + (optional transition) `ProcessingJobCompletedIntegrationEvent`

## Phase 3 — CDK filter policy

- [ ] `cdk-magiq-media` admits `media.processingjob.timeout-recovered` to AssetManagement's `media-processing-events` consumer queue; `FilterPolicyScope: MessageBody` on `type`

## Phase 4 — Consumer migration

- [ ] `AssetProcessingTimeoutRecoveredSagaHandler` consumes the new type (if migration path chosen)
- [ ] Dual-handler window for one release if retiring reuse

## Phase 5 — Tests

- [ ] Integration: `ProcessingJobTimeoutRecovered` → SNS → body carries `type = media.processingjob.timeout-recovered`
- [ ] Integration: AssetManagement consumer routes correctly

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
