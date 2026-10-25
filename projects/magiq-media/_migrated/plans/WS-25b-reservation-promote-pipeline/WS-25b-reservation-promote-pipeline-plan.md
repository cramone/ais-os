---
id: MM-042
type: plan
project: magiq-media
workstream: WS-25b-reservation-promote-pipeline
repo: magiq-media
tags: [magiq-media, middleware, name-reservation, pipeline]
consumes: []
blocked-by-external: [MM-028]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-25.
---

# WS-25b — Command middleware calls `PromoteAsync` after `SaveAsync`

**Target repo:** `magiq-media`
**Depends on:** MM-028 (WS-25a SDK)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-25b (plan MM-042). SDK (MM-028) ships `INameReservationService.PromoteAsync` on txn handle.
>
> Add `ReservationPromotionMiddleware` to the command dispatcher chain, after event-store save. Collects `ReservationApplyToken`s from the active command's context + calls `PromoteAsync(tokens, txn, ct)` within the same `TransactWriteItems` as `SaveAsync`.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-028 shipped
- [ ] Enumerate handlers that call `IsNameAvailableAsync` + `ApplyAsync`

## Phase 1 — Context carries tokens
- [ ] Extend command-execution context (or an `IReservationContext`) carrying `List<ReservationApplyToken>`
- [ ] `ApplyAsync` wrapper stores token in context

## Phase 2 — Middleware
- [ ] `ReservationPromotionMiddleware` wraps `SaveAsync`:
  - Build `IEventStoreTransaction txn`
  - Append event rows
  - Append `PromoteAsync(tokens, txn)` to same txn
  - `txn.CommitAsync()`

## Phase 3 — Tests
- [ ] Unit: successful save promotes all reservations to CLAIMED
- [ ] Unit: event-store conflict rolls back promotion (reservation stays PENDING)
- [ ] Integration: observable state after create = reservation CLAIMED

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] platform-capabilities/INDEX.md: WS-25 → § Shipped
- [ ] INTEGRATION-BACKLOG: WS-25b → § Shipped
- [ ] Remove `Reservation promotion (step 6a) not wired` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-028 + user policy)
