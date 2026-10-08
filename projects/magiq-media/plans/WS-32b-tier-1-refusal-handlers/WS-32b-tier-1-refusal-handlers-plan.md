---
id: MM-039
type: plan
project: magiq-media
workstream: WS-32b-tier-1-refusal-handlers
repo: magiq-media
tags: [magiq-media, name-reservation, handlers, 409]
consumes: []
blocked-by-external: [MM-015]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-32.
---

# WS-32b — Audit Tier-1 refusal sites → `409 …AlreadyExists` at handlers

**Target repo:** `magiq-media`
**Depends on:** MM-015 (WS-32a SDK — `NameAlreadyTakenException`)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-32b (plan MM-039). SDK (MM-015) ships `NameAlreadyTakenException` + registry ConsistentRead.
>
> Grep handler sites catching `InvalidOperationException` from `INameReservationService.IsNameAvailableAsync`. Replace with catching `NameAlreadyTakenException` → `409 …AlreadyExists` ProblemDetails. Confirm platform default mapper handles this; override only when extensions differ.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-015 shipped
- [ ] Grep `IsNameAvailableAsync` call sites across magiq-media handlers
- [ ] Enumerate scopes with Tier-1 refusal paths (collection, folder, media-item, media-profile, record-type)

## Phase 1 — Handler refactor
- [ ] Replace `InvalidOperationException` catch with `NameAlreadyTakenException` catch
- [ ] Return `Result<T, DomainError>` with `AlreadyExists` variant
- [ ] Endpoint mapper → 409 `…AlreadyExists` ProblemDetails

## Phase 2 — Tests
- [ ] Unit per scope: name conflict Tier-1 → 409 with correct `errorCode`
- [ ] Integration: concurrent create of same name → one succeeds, one gets 409

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] name-reservation/INDEX.md: WS-32 → § Shipped
- [ ] INTEGRATION-BACKLOG: WS-32b → § Shipped
- [ ] Remove `Name-reservation retry safety` bullet (Tier 1 portion) from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-015 + user policy)
