---
id: MM-015
type: plan
project: magiq-media
workstream: WS-32a-registry-consistent-read
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, name-reservation, consistency]
consumes: []
blocked-by-external: []
status: shipped
branches: [WS-32a-registry-consistent-read]
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/name-reservation/INDEX.md#WS-32 (no gap file; row-tracked); no separate review document.
---

# WS-32a — Name registry `ConsistentRead` + Tier-1 refusal shape

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-039 (WS-32b — magiq-media handler Tier-1 refusal sites → 409 shape)

Two SDK changes: (1) `NameRegistry.GetItem` sets `ConsistentRead = true`; (2) Tier-1 refusal surfaces `NameAlreadyTakenException` (not `InvalidOperationException`) with payload for `409 …AlreadyExists` mapping.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-32a (plan MM-015). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-32a-registry-consistent-read\WS-32a-registry-consistent-read-plan.md`.
>
> Flip `ConsistentRead = true` on `NameRegistry.GetItem` + any availability-check Query. Replace `InvalidOperationException` on Tier-1 refusal with `NameAlreadyTakenException` carrying `ScopeKey`, `Name`, `OwnerAggregateId?`. Document mapping: consumers map → `409 …AlreadyExists`.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [x] Read `docs/spec/shared/consistency-model.md` § Name reservation Tier-1
- [x] Locate `NameRegistry.GetItem` + availability-check path
- [x] Enumerate current Tier-1 refusal exception sites

## Phase 1 — `ConsistentRead = true` on registry read
- [x] `NameRegistry.GetItem` + any availability-check `Query` → `ConsistentRead = true`
- [x] Document 2× RCU cost on registry table

## Phase 2 — Tier-1 refusal error shape
- [x] Define `NameAlreadyTakenException` (or `Result<T, NameAlreadyTaken>`)
- [x] Carries `ScopeKey`, `Name`, `OwnerAggregateId` (null when no probe)
- [x] Not derived from `InvalidOperationException`

## Phase 3 — Mapping guidance
- [x] XML doc: consumers map to `409 …AlreadyExists` ProblemDetails
- [x] Platform problem-details mapper (if present) wires default mapping

## Phase 4 — Tests
- [x] Unit: registry read parameters assert `ConsistentRead = true`
- [x] Unit: Tier-1 refusal throws `NameAlreadyTakenException`
- [x] Unit: exception carries scope + name
- [x] Unit: default mapper → `409`

## Phase 5 — Package + ship
- [x] Bump `Magiq.Platform.*` version
- [x] PR to `aspnetcore-platform/main`

## Phase 6 — Close
- [x] name-reservation/INDEX.md: WS-32 split — `WS-32a shipped`, `WS-32b open`
- [x] INTEGRATION-BACKLOG: MM-039 (WS-32b) ready

## Session log
- 2026-10-08: plan drafted
- 2026-10-08: activated after WS-24 (MM-008) shipped. Same repo (`aspnetcore-platform`), no deps, direct thematic sibling (ConsistentRead on registry read + exception shape).
- 2026-10-09: shipped — [PR #32](https://github.com/magiqsoftware/aspnetcore-platform/pull/32), merge `63328bf9`. Reality note: current refusal already threw a dedicated `NameReservationConflictException` (not `InvalidOperationException` as the plan assumed). Renamed to plan-agreed `NameAlreadyTakenException`, added nullable `OwnerAggregateId` payload, flipped `ConsistentRead = true` on `GetOwnerIdAsync`, `IsNameAvailableAsync`, `HasItemsInScopeAsync`, and both `BatchGetItem` helpers. No separate platform problem-details mapper to wire (none exists); XML/README guidance covers consumer mapping. 10 new unit tests. Unblocks WS-32b (MM-039).
