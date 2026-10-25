---
id: MM-105
type: plan
project: magiq-media
workstream: WS-65-asset-write-model-residuals
repo: magiq-media
tags: [magiq-media, asset-management, write-model, event-schema, enum-ordinals]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
depends-on: -
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell Asset×write-model
---

# WS-65 — AssetManagement: legal-hold events + AssetStatus/FailureCategory ordinals pinned

**Target repo:** `magiq-media`
**Depends on:** none

## Problem

Spec [`asset.write-model.md § Domain Events`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/contexts/AssetManagement/aggregates/Asset/asset.write-model.md) names 29 Asset domain events. Code emits 19 — most of the delta is already in scope of other sweep plans:

| Missing in code | Covered by |
|---|---|
| `AssetProcessingBypassed`, `AssetQuarantineAccessIssued`, `AssetQuarantineMoveRetryRequested`, `AssetQuarantineMoveConfirmed`, `AssetRenditionsDiscardedOnInfection` | MM-102 WS-62 (integration events — the domain events land as part of that work) |
| `AssetTagsAdded`, `AssetTagsRemoved`, `AssetPersonalDataErased` | MM-103 WS-63 (missing HTTP routes — the commands dispatch to these events) |

Two residual gaps remain for this cell:

1. **`AssetHolderLegalHoldPlaced` + `AssetHolderLegalHoldLifted` not emitted.** Spec says Asset reflects its MediaItem holder's hold state via these two events. `Asset.cs` has no `LegalHold` handling at all — no apply, no state field, nothing. Downstream fencing (e.g. `AssetArchive` + `DeleteAsset` under hold) relies on the asset-side flag being up to date.

2. **`AssetStatus` + `FailureCategory` enum ordinals not pinned.** Spec: stored shape states enum ordinals explicitly. Code declares both enums with implicit source-order values. Reordering, inserting or removing a member silently rewrites every historical stream — the kind of change CLAUDE.md § Spec files state the specified system calls out.

MM-052 (WS-41) already covers `ProcessingJobStatus` + `FailureCategory` ordinal pinning for the Processing module. **`FailureCategory` is Asset-owned** (`src/modules/AssetManagement/AssetManagement.Domain/ValueObjects/FailureCategory.cs`) — the MM-052 scope mentions it under ProcessingJob but the type lives here. Treat MM-052 as the owner for `FailureCategory`; this plan takes `AssetStatus` only.

## Scope

### Legal-hold reflection on Asset

- Two new domain events: `AssetHolderLegalHoldPlaced(TenantId, AssetId, MediaItemId, HoldId, PlacedBy, OccurredAt)` + `AssetHolderLegalHoldLifted(TenantId, AssetId, MediaItemId, HoldId, LiftedBy, OccurredAt)`
- `Asset.ApplyLegalHoldPlaced` / `ApplyLegalHoldLifted` adjust `Asset.ActiveHoldIds` (new `IReadOnlyCollection<HoldId>` state field)
- `MediaItemLegalHoldPlacedIntegrationEventHandler` (intra-BC subscriber) dispatches the command on the owning asset(s) — asset list resolved through `media-asset-item-capability-ref` or equivalent reverse index
- Status guards on `ArchiveAsset`, `DeleteAsset`, `ErasePersonalData` consult `ActiveHoldIds.Any()` as part of the refusal set (feeds `ErasureRefusedUnderLegalHold`)

### Enum ordinals

- `AssetStatus` members get explicit numeric values. Preserve the current source-order ordinals so existing streams load unchanged — this is a code-only annotation change.
  - `Pending = 0`, `Validating = 1`, `ValidationFailed = 2`, `ContainsVirus = 3`, `Processing = 4`, `ProcessingFailed = 5`, `Active = 6`, `Archived = 7`, `Deleted = 8`, `MultipartAborted = 9`, `VersionArtifact = 10`
- Add XML-doc note that the integer value is a persisted contract and must not change
- Add roundtrip unit test asserting each name maps to the expected ordinal (catches an accidental reordering in review)

**Do not** pin `FailureCategory` here — MM-052 scope. The two plans share a file; whichever lands first adds the test harness, the second adds the complement.

## Phase 0 — Confirm
- [ ] MM-102 confirmed to carry the five quarantine/bypass-family domain events
- [ ] MM-103 confirmed to carry `AssetTagsAdded`, `AssetTagsRemoved`, `AssetPersonalDataErased`
- [ ] MM-052 confirmed to carry `FailureCategory` ordinal pinning

## Phase 1 — AssetStatus ordinals
- [ ] Explicit numeric assignments on `AssetStatus.cs` matching current source order
- [ ] Roundtrip unit test (name → ordinal map)

## Phase 2 — Legal-hold events + state
- [ ] `AssetHolderLegalHoldPlaced` + `AssetHolderLegalHoldLifted` domain events with `[DomainEvent]` attribute
- [ ] `Asset.ActiveHoldIds` state field + apply methods
- [ ] `Asset.PlaceHolderLegalHold` + `LiftHolderLegalHold` methods (System-only — dispatched by subscriber)
- [ ] Guards: `ArchiveAsset`, `DeleteAsset`, `ErasePersonalData` refuse under non-empty `ActiveHoldIds` with `ErasureRefusedUnderLegalHold` where applicable

## Phase 3 — Intra-BC subscriber
- [ ] `MediaItemLegalHoldPlacedEventHandler` + `MediaItemLegalHoldLiftedEventHandler` subscribe to `media.item.*` legal-hold integration events via `media-cross-module-events`
- [ ] Handlers resolve the asset set bound to the media item (via existing `media-asset-item-capability-ref` or new reverse lookup) and dispatch the Asset-side commands as System

## Phase 4 — Tests
- [ ] Unit: hold placed on item → both assets' streams carry `AssetHolderLegalHoldPlaced`
- [ ] Unit: `DeleteAsset` under hold → `ErasureRefusedUnderLegalHold`
- [ ] Unit: `AssetStatus` enum ordinal map
- [ ] Integration: hold → delete refused → lift → delete succeeds

## Phase 5 — Ship
- [ ] magiq-media CLAUDE.md: close Asset write-model bullet

## Acceptance criteria

- Both legal-hold domain events emitted on item-hold boundary
- `Asset.ActiveHoldIds` state field drives the three refusal paths
- `AssetStatus` ordinals explicit; test enforces them

## Breaking-change note

Internal only. Legal-hold events are not in the published `media.asset.*` integration-event vocabulary (spec does not list them under § Integration Events — hold reflection is intra-BC state). Ordinal pinning preserves current values.

## Session log

- 2026-10-15: plan drafted by alignment sweep (Asset×write-model cell). `status: candidate` pending triage.
