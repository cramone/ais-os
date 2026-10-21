---
id: MM-102
type: plan
project: magiq-media
workstream: WS-62-asset-missing-integration-events
repo: magiq-media
tags: [magiq-media, asset-management, integration-events, process-wire]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-15
depends-on: -
breaking-change: Process wire
source: alignment-sweep-2026-10-15 cell Asset×integration-events
---

# WS-62 — AssetManagement: 7 missing integration events + Billing filter

**Target repo:** `magiq-media`
**Depends on:** none (SDK outbox + mapping already shipped via MM-023a/b/c/d)

## Problem

Spec [`event-store-and-messaging.md § Integration Events`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/event-store-and-messaging.md#integration-events) specifies 17 `media.asset.*` integration event types. Code (`src/modules/AssetManagement/AssetManagement.Contracts/Events/`) carries only 10 integration event records; `AssetIntegrationEventMapper` publishes 10 (via 12 domain-event→integration-event handlers). Seven integration events are missing from the wire — downstream consumers (Catalog ref index, Processing worker, Notifications, Security audit log, SFN) cannot subscribe.

## Scope

### Missing integration events (7)

| Integration event | Source domain event | Domain event exists? | Mapper handler? | Consumers to notify |
|---|---|---|---|---|
| `media.asset.attach-refused` | `AssetAttachRefused` | **No** | **No** | Catalog (System `UnassignAssetFromRoleCommand`) |
| `media.asset.processing-bypassed` | `AssetProcessingBypassed` | **No** | **No** | Catalog (`Active` + auto-submit), Notifications. **Not** Billing (bypassed is quota-exempt). **Not** SFN (bypass closes synchronously) |
| `media.asset.quarantine-access-issued` | `AssetQuarantineAccessIssued` | **No** | **No** | Security audit log |
| `media.asset.multipart-aborted` | `AssetMultipartUploadAborted` | Yes | **No** | Catalog (`MultipartAborted` state) |
| `media.asset.quarantine-move-retry-requested` | `AssetQuarantineMoveRetryRequested` | **No** | **No** | Processing (`media-processing` SQS — re-executes copy-verify-delete). Raised by `MaintenanceScanner` quarantine-retry pass + on-demand `RequestQuarantineMoveRetry` |
| `media.asset.quarantine-move-confirmed` | `AssetQuarantineMoveConfirmed` | **No** | **No** | No external subscriber. Observability only — AssetManagement's own read-model drops asset from `ContainsVirusAwaitingQuarantineIndex` on apply, not from this event |
| `media.asset.renditions-discarded-on-infection` | `AssetRenditionsDiscardedOnInfection` | **No** | **No** | Processing (deletes named rendition objects from `media-renditions`). Raised alongside `AssetInfectionDetected` when `AttemptNumber ≥ 2` |

### Billing filter — not inline today

Spec: `AssetIntegrationEventMapper` applies inline filter on `media.asset.processing-completed` — Billing receives only when the owning `MediaItem`'s `MediaProfile` has the `Processing` capability. Mapper reads `HasProcessingCapability` on domain event source.

Code: `AssetProcessingCompletedIntegrationEvent` carries no capability flag. Mapper publishes to all subscribers unconditionally. **Billing today receives every processing-completed, including documents** — tenant quota mis-measurement.

Fix path:
- `AssetValidationPassed` already carries `HasProcessingCapability` (visible on `AssetValidationPassedIntegrationEvent`); same flag must propagate onto `AssetProcessingCompleted` + `AssetProcessingTimeoutRecovered` domain events + their integration events.
- `AssetIntegrationEventMapper.Map(AssetProcessingCompleted)` either (a) emits two integration events — one for Billing-filterable, one for others — or (b) emits one with the flag and relies on SNS filter policy. **Spec says inline filter inside mapper**: mapper **yields no Billing event** when `HasProcessingCapability == false`. SDK's `IDomainEventMapper` yielding zero integration events for a given domain event is already a supported outcome.

## Phase 0 — Confirm shape
- [ ] Verify spec: Billing filter is **inline inside mapper**, not SNS attribute filter (confirmed — § Integration Events footnote)
- [ ] Verify `AssetUploadConfirmedIntegrationEvent` + `AssetProcessingCompletedIntegrationEvent` payload carries `HasProcessingCapability` or infer from existing member set
- [ ] Confirm each missing domain event's correct emission site in `Asset.cs`

## Phase 1 — Domain events (6)
- [ ] `AssetAttachRefused` — raised when `AttachAssetToMediaItem` finds asset already attached to another item; carries `AssetId`, `MediaItemId` (requesting), `RequestedBy`, `OccurredAt`
- [ ] `AssetProcessingBypassed` — raised when processing is bypassed (document asset); carries `AssetId`, `OwnerId`, `OccurredAt`
- [ ] `AssetQuarantineAccessIssued` — raised when operator takes signed access to quarantined object via `GET /quarantine/download`; carries `AssetId`, `IssuedTo`, `OccurredAt`
- [ ] `AssetQuarantineMoveRetryRequested` — raised by `RequestQuarantineMoveRetry`; carries `AssetId`, `AttemptNumber`, `OccurredAt`
- [ ] `AssetQuarantineMoveConfirmed` — raised when quarantine copy-verify-delete succeeds; carries `AssetId`, `ConfirmedAt`
- [ ] `AssetRenditionsDiscardedOnInfection` — raised alongside `AssetInfectionDetected` when `AttemptNumber ≥ 2`; carries `AssetId`, `DiscardedRenditionKeys[]`, `OccurredAt`

## Phase 2 — Integration event records (7)
- [ ] `AssetAttachRefusedIntegrationEvent` with `[MessageType("media.asset.attach-refused")]`
- [ ] `AssetProcessingBypassedIntegrationEvent` with `[MessageType("media.asset.processing-bypassed")]`
- [ ] `AssetQuarantineAccessIssuedIntegrationEvent` with `[MessageType("media.asset.quarantine-access-issued")]`
- [ ] `AssetMultipartUploadAbortedIntegrationEvent` with `[MessageType("media.asset.multipart-aborted")]`
- [ ] `AssetQuarantineMoveRetryRequestedIntegrationEvent` with `[MessageType("media.asset.quarantine-move-retry-requested")]`
- [ ] `AssetQuarantineMoveConfirmedIntegrationEvent` with `[MessageType("media.asset.quarantine-move-confirmed")]`
- [ ] `AssetRenditionsDiscardedOnInfectionIntegrationEvent` with `[MessageType("media.asset.renditions-discarded-on-infection")]`

## Phase 3 — Mapper handlers
- [ ] `AssetIntegrationEventMapper` adds `IDomainEventMapper<T>` for each of the 6 new domain events + `AssetMultipartUploadAborted`
- [ ] `Map(AssetMultipartUploadAborted)` yields `AssetMultipartUploadAbortedIntegrationEvent`
- [ ] Each new mapper yields one integration event

## Phase 4 — Billing inline filter
- [ ] `AssetProcessingCompleted` + `AssetProcessingTimeoutRecovered` domain events carry `HasProcessingCapability` bool (additive, nullable for existing streams — upcast on apply from associated `AssetValidationPassed`)
- [ ] `AssetProcessingCompletedIntegrationEvent` + `AssetProcessingTimeoutRecoveredIntegrationEvent` carry the flag (additive)
- [ ] `AssetIntegrationEventMapper.Map(AssetProcessingCompleted)` emits one event when flag true, yields zero when flag false (Billing-filterable behaviour inside mapper per spec footnote)
- [ ] Alternative decision: if SDK supports typed-subscriber filter (SNS `FilterPolicyScope: MessageBody` on an `isBillable` body member), prefer that over mapper-side suppression — but spec text says mapper filter

## Phase 5 — Infra (`cdk-magiq-media`)
- [ ] Downstream SQS filter policies updated to subscribe to new `type` values where consumer wiring exists today (Catalog `media-cross-module-events`, Processing `media-processing`, Notifications)
- [ ] Delivered as separate CDK PR; magiq-media PR gated on it

## Phase 6 — Consumer handlers (intra-BC)
- [ ] Catalog subscribes to `media.asset.attach-refused` → `UnassignAssetFromRoleCommand` as System actor
- [ ] Catalog subscribes to `media.asset.processing-bypassed` → sets asset `Active` in `media-catalog-asset-ref` + auto-submit
- [ ] Catalog subscribes to `media.asset.multipart-aborted` → sets `MultipartAborted` in `media-catalog-asset-ref`
- [ ] Processing subscribes to `media.asset.quarantine-move-retry-requested` → re-executes copy-verify-delete
- [ ] Processing subscribes to `media.asset.renditions-discarded-on-infection` → deletes named objects from `media-renditions`
- [ ] Security audit log subscribes to `media.asset.quarantine-access-issued`
- [ ] No external consumer for `media.asset.quarantine-move-confirmed` — observability only

## Phase 7 — Tests
- [ ] Mapper unit tests for each new mapper handler
- [ ] Integration test: each event flows end-to-end through outbox → SNS → consumer handler
- [ ] Billing filter integration test — document-only MediaItem's processing-completed does **not** reach Billing

## Phase 8 — Ship
- [ ] PR to `develop` + CDK PR landed first
- [ ] magiq-media CLAUDE.md: close Asset-integration-events gap

## Acceptance criteria

- 17 `media.asset.*` integration events published; types match spec
- Mapper applies inline Billing filter on `media.asset.processing-completed`
- All consumer handlers wired per spec

## Breaking-change note

Process wire (narrow): new SNS types extend published vocabulary — existing subscribers (filter-policy allow-lists) unaffected until explicit allowlist edit. Billing filter inline is **Process wire — breaking for Billing**: today Billing receives every processing-completed; after fix, Billing receives only Processing-capability events (correct per spec, but existing quota attribution changes).

## Session log

- 2026-10-15: plan drafted by alignment sweep (Asset×integration-events cell). `status: candidate` pending triage.
