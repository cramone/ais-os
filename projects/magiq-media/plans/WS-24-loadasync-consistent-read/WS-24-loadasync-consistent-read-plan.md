---
id: MM-008
type: plan
project: magiq-media
workstream: WS-24-loadasync-consistent-read
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, event-store, consistency]
consumes: []
blocked-by-external: []
status: done
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-24 (no gap file; row-tracked); no separate review document.
---

# WS-24 — `EventStoreRepository.LoadAsync` with `ConsistentRead = true`

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** safer read-your-write for name-reservation + aggregate loads

Spec requires strongly-consistent reads of the event-store. Today `LoadAsync` defaults `ConsistentRead = false`, so a probe on a just-committed aggregate can answer "does not exist" and produce a duplicate name.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-24 (plan MM-008). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-24-loadasync-consistent-read\WS-24-loadasync-consistent-read-plan.md`.
>
> Flip `ConsistentRead = true` on `EventStoreRepository.LoadAsync` and snapshot read. Grep for other `ConsistentRead = false` in event-store layer and audit each. Document 2× RCU cost impact in PR description.
>
> Read `aspnetcore-platform/CLAUDE.md`. One PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [x] Read `docs/spec/shared/event-store-and-messaging.md` § Read Consistency *(file absent — exception noted; worked from WS-24 plan + repo CLAUDE.md)*
- [x] Grep `ConsistentRead` across `aspnetcore-platform` event-store layer
- [x] Confirm `LoadAsync` is the only path currently defaulting to `false` *(found five sites — four read paths + `DeleteAsync` enumerate query; all flipped)*

## Phase 1 — Flip `ConsistentRead = true`
- [x] `EventStoreRepository.LoadAsync` sets `ConsistentRead = true` on `Query` / `GetItem` calls
- [x] Snapshot load: `ConsistentRead = true`
- [x] Preserve any legitimate not-required reads (projector-side scans — audit each) *(projection stores: zero `ConsistentRead` sites; tenant repo + batch-helper sites left untouched — different concern)*

## Phase 2 — Cost impact note
- [x] Document 2× RCU cost in PR description
- [ ] Confirm no RCU throttling risk in staging / prod event-store table *(ops task — monitor after deploy)*

## Phase 3 — Tests
- [x] Integration: write-then-read within same request path returns the write *(covered by existing `DynamoDbEventStoreIntegrationTests.LoadAsync_ExistingAggregate_ShouldReconstructFromDynamoDB`)*
- [x] Request parameters assert `ConsistentRead = true` (SDK test-double) *(`DynamoDbEventStoreConsistentReadTests`, 5 facts: Load, LoadAfterAnchored, ContainEventStream, Delete enumerate, Snapshot GetById)*

## Phase 4 — Package + ship
- [x] Bump `Magiq.Platform.*` version *(1.1.3.5 → 1.1.3.6)*
- [x] PR to `aspnetcore-platform/main` *(PR #31, merged)*

## Phase 5 — Close
- [ ] platform-capabilities/INDEX.md: WS-24 → § Shipped *(no INDEX file exists per plan `exception` note — row-tracked)*

## Session log
- 2026-10-08: plan drafted
- 2026-10-08: activated as the next SDK plan after MM-014 (WS-22) shipped. Same repo (`aspnetcore-platform`), Level 0 Phase A, no deps. Small scope — likely a one-attribute flip + audit of other `ConsistentRead = false` sites.
- 2026-10-08: shipped. `DynamoDbEventStoreOptions.ConsistentRead` opt-in deleted (spec requires strong consistency, no opt-out); all 4 event-store read paths + `DeleteAsync` enumerate query hardcoded `true`. `DeleteAsync` gap caught in self-review before merge. PR #31 merged.
