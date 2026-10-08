---
id: MM-021
type: plan
project: magiq-media
workstream: WS-30a-reservation-probe-hook
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, name-reservation]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/name-reservation/INDEX.md#WS-30 (no gap file; row-tracked); no separate review document.
---

# WS-30a — SDK hook consulting per-scope `IReservationOwnerProbe`

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-040 (WS-30b — magiq-media `CatalogReservationProbe` registration)

Today name-reservation refuses any held row; a reservation stuck under its own aggregate becomes permanently un-takeable. Spec: SDK consults per-scope `IReservationOwnerProbe`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-30a (plan MM-021). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-30a-reservation-probe-hook\WS-30a-reservation-probe-hook-plan.md`.
>
> Define `IReservationOwnerProbe` with `GetOwnerIdAsync(scope, name, ct) → AggregateId?`. Register per `ScopeKey` via `IReservationOwnerProbeRegistry`. On Tier-1 refusal in `ApplyAsync`: consult probe → if returns command's own aggregate id, treat as available; otherwise refuse.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/shared/consistency-model.md` § Name reservation
- [ ] Locate `INameReservationService.ApplyAsync` + reservation registry
- [ ] Confirm no probe hook exists today

## Phase 1 — Probe interface
- [ ] `IReservationOwnerProbe.GetOwnerIdAsync(ScopeKey scope, string name, CancellationToken ct)` → `Task<AggregateId?>`
- [ ] Keyed per `ScopeKey` via `IReservationOwnerProbeRegistry`
- [ ] DI: `AddReservationProbe<TProbe>(scope)`

## Phase 2 — `ApplyAsync` consultation
- [ ] On Tier-1 refusal: look up probe for `ScopeKey`
- [ ] No probe → refuse as today (`NameAlreadyTaken` → `409 …AlreadyExists`)
- [ ] Probe returns null → refuse
- [ ] Probe returns matching command's own aggregate id → available (same-aggregate retry safety)
- [ ] Probe returns different aggregate id → refuse

## Phase 3 — `GetOwnerIdAsync` on service surface
- [ ] Public `INameReservationService.GetOwnerIdAsync(scope, name, ct)` returns probe's answer for handler-side checks

## Phase 4 — Tests
- [ ] Unit: probe-less scope refuses held name
- [ ] Unit: probe returns matching aggregate id → succeeds
- [ ] Unit: probe returns different aggregate id → refuses
- [ ] Unit: probe returns null → refuses

## Phase 5 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 6 — Close
- [ ] name-reservation/INDEX.md: WS-30 split — `WS-30a shipped`, `WS-30b open`
- [ ] INTEGRATION-BACKLOG: MM-040 (WS-30b) ready

## Session log
- 2026-10-08: plan drafted
