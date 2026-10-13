---
id: MM-023c
type: plan
project: magiq-media
workstream: WS-21c-outbox-table-split
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, outbox, dynamodb, schema]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-023c-WS-21c-outbox-table-split]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/44
merge-sha: 084dd6a8
shipped: 2026-10-12
created: 2026-10-12
depends-on: MM-023b (pipeline wiring)
split-from: WS-21 — parent split 2026-10-12
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-21c (row-tracked); no separate review document.
---

# WS-21c — Outbox table split (`outbox-pending` + `outbox-dead`)

**Target repo:** `aspnetcore-platform` (+ `cdk-magiq-media` for CDK side)

## Scope — corrected 2026-10-12

**Scope pivot.** Original plan read as "split into two tables (`outbox-pending` + `outbox-dead`)". Spec (`event-store-and-messaging.md` § Transactional Outbox lines 300-304) actually specifies **one table with a `Parked = true` flag**: "marked `Parked = true` with `ParkedAt`, `ParkReason` and `AttemptCount`, and skipped by the relay on subsequent passes." Correcting to spec — split-tables was my miss during the 2026-10-12 WS-21 split.

Required change:
- Outbox row gains `Parked` (bool), `ParkedAt` (unix ms), `ParkReason` (string) attributes
- Max attempts bounded to 10 (currently 3)
- Relay flips `Parked = true` on retry exhaustion (atomic update, drops row from `GSI_NextAttempt` as it already does today by removing `NextAttemptAt`)
- Dequeue defensively filters `Parked != true`
- `OutboxEntryParked` counter emitted when parking (Meter `Magiq.Platform.Messaging.Outbox`)
- Operator redrive: `UnparkAsync(messageIds)` on `IOutboxStore` — resets Parked flag, clears ParkedAt/ParkReason, sets fresh `NextAttemptAt`, resets AttemptCount

Phases
- Phase 0: scope pivot documented
- Phase 1: schema constants (`Parked`, `ParkedAt`, `ParkReason`), raise `MaxRetryCount` default to 10
- Phase 2: `OutboxLogicalMessage` gains `IsParked` + `ParkedAt` + `ParkReason`; `MarkedAsFailed` carries park state when attempts exhausted
- Phase 3: `DynamoDbOutboxStore.EnqueueFailedMessagesAsync` writes park attributes on exhaustion
- Phase 4: `DynamoDbOutboxStore.DequeueNextBatchAsync` filters `Parked != true` defensively (GSI absence already enough but defence-in-depth)
- Phase 5: `IOutboxStore.UnparkAsync` + DynamoDb + in-memory impls
- Phase 6: `OutboxMetrics` class + `OutboxEntryParked` counter wired at park site
- Phase 7: Tests + PR

## Session log
- 2026-10-12: drafted after MM-023 split.
- 2026-10-12: scope correction — spec is "Parked flag on single table", not "two tables". Phases rewritten to match spec. Implementation starting now.
- 2026-10-12: shipped. PR #44 merged as `084dd6a8`.
  - **Delivered**: `Parked`/`ParkedAt`/`ParkReason` schema attrs; `OutboxOptions.MaxRetryCount` default 3→10; `OutboxLogicalMessage.MarkAsParked`; processor exhaustion → park + metric; DynamoDb `EnqueueFailedMessagesAsync` atomic park write; defensive dequeue filter; `IOutboxStore.UnparkAsync` (DynamoDb + InMemory); `OutboxMetrics` + Meter `Magiq.Platform.Messaging.Outbox` + counter `outbox.entry_parked`.
  - **7 unit tests + 211/211 non-integration regression green**.
  - **Interface break**: `IOutboxStore.UnparkAsync`. Default change: `MaxRetryCount` 3→10.
  - **Trackers updated**: platform-capabilities/INDEX.md WS-21c moved to Shipped, WS-21d flipped `open` → `ready`. INTEGRATION-BACKLOG MM-023c moved to § Shipped, MM-023d flipped `new` → `ready`. Readiness 61 new / 11 ready / 17 shipped.
  - **Deferred to child plans**: MM-023d (relay Lambda, cdk-magiq-media — now ready), MM-023e (metrics export pipeline — blocked by WS-58).
