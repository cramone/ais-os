---
id: MM-028
type: plan
project: magiq-media
workstream: WS-25a-reservation-promote
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, name-reservation, transaction]
consumes: []
blocked-by-external: [MM-023]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-25 (no gap file; row-tracked); no separate review document.
---

# WS-25a — `PromoteAsync` on `INameReservationService`

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** MM-023 (WS-21 — outbox / transaction handle)
**Unblocks:** MM-042 (WS-25b — magiq-media command middleware calls PromoteAsync)

Promotion rides on same `TransactWriteItems` txn as event-store append. Today pipeline skips promotion; everything stays `PENDING`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Confirm MM-023 (WS-21) shipped. Paste:

> Picking up WS-25a (plan MM-028). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-25a-reservation-promote\WS-25a-reservation-promote-plan.md`.
>
> Depends on WS-21 (MM-023) shipped — needs `IEventStoreTransaction`. Add `INameReservationService.PromoteAsync(tokens, txn, ct)` — each token → `UpdateItem` with `ConditionExpression: State = :pending`. Appends to txn so TransactWriteItems commits atomically with event-store append. `ApplyAsync` returns `ReservationApplyToken { ScopeKey, Name, AggregateId }`. Conditional-check-failed on promote → `ReservationPromotionFailedException`.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/shared/consistency-model.md` § Name reservation two-phase
- [ ] Confirm MM-023 (WS-21) shipped (`IEventStoreTransaction` available)
- [ ] Locate `INameReservationService` + current `ApplyAsync` path

## Phase 1 — `PromoteAsync` on service
- [ ] `Task PromoteAsync(IReadOnlyList<ReservationApplyToken> tokens, IEventStoreTransaction txn, CancellationToken ct)`
- [ ] Each token → `UpdateItem` with `ConditionExpression: State = :pending`, `Set State = :claimed`
- [ ] Appends to `txn.Items` so `TransactWriteItems` commits atomically

## Phase 2 — `ApplyAsync` returns token
- [ ] Returns `ReservationApplyToken { ScopeKey, Name, AggregateId }`
- [ ] Token also carries `State = Pending` at return

## Phase 3 — Promotion failure semantics
- [ ] Conditional-check-failed on promote → `ReservationPromotionFailedException`
- [ ] Txn-wide rollback (all-or-nothing TransactWriteItems)

## Phase 4 — Tests
- [ ] Unit: `ApplyAsync` + `PromoteAsync` in one txn → both commit
- [ ] Unit: event-store append fails → promote rolls back → reservation stays `Pending`
- [ ] Unit: concurrent conflicting promote → `ReservationPromotionFailedException`

## Phase 5 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 6 — Close
- [ ] platform-capabilities/INDEX.md: WS-25 split — `WS-25a shipped`, `WS-25b open`
- [ ] INTEGRATION-BACKLOG: MM-042 (WS-25b) ready

## Session log
- 2026-10-08: plan drafted (blocked on MM-023 ship)
