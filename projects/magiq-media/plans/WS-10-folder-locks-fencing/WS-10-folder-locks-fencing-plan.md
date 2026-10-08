---
id: MM-066
type: plan
project: magiq-media
workstream: WS-10-folder-locks-fencing
repo: magiq-media
tags: [magiq-media, folder-locks, concurrency, fencing]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/folder-locks/INDEX.md#WS-10.
---

# WS-10 — `media-folder-locks` fencing contract

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec: `OwnerToken` on lock, `LeaseDuration > Api Lambda timeout`, acquire via `attribute_not_exists(PK) OR ExpiresAt < :now`, release conditioned on `OwnerToken = :token`, fencing check on every lock-protected write. Current: `503 ExternalServiceUnavailable` on contention; spec: `409 FolderWriteInProgress`.

## Session invocation

> Picking up WS-10 (plan MM-066). Add `OwnerToken` to lock record. Acquire via conditional-put (`attribute_not_exists(PK) OR ExpiresAt < :now`). Release via conditional-delete (`OwnerToken = :token`). Lock-protected writes verify fencing token. Map contention → `409 FolderWriteInProgress`.

## Phase 0 — Scope confirmation
- [ ] Read spec for lock table shape
- [ ] Locate current lock acquire/release/write-protection sites

## Phase 1 — Lock record shape
- [ ] Add `OwnerToken` member
- [ ] `LeaseDuration` > Api Lambda timeout (default 20 min)
- [ ] `ExpiresAt` on each record

## Phase 2 — Acquire
- [ ] `TransactWriteItems` with conditional-put `attribute_not_exists(PK) OR ExpiresAt < :now`
- [ ] Mint `OwnerToken` (UUID v7)
- [ ] Contention → `Result.Failure(FolderWriteInProgress)` → 409

## Phase 3 — Release
- [ ] Conditional delete with `OwnerToken = :token`
- [ ] Idempotent: already-released returns success

## Phase 4 — Fencing on protected writes
- [ ] Every lock-protected write: verify `OwnerToken` on current lock before applying

## Phase 5 — ProblemDetails
- [ ] Remove 503 contention mapping
- [ ] Add `409 FolderWriteInProgress`

## Phase 6 — Tests
- [ ] Unit: acquire + release happy path
- [ ] Unit: contention → 409
- [ ] Unit: expired lock → new acquire succeeds
- [ ] Unit: fencing refuses stale-token write

## Phase 7 — Ship
- [ ] PR to `develop`

## Phase 8 — Close
- [ ] folder-locks/INDEX.md: WS-10 → § Shipped
- [ ] Remove `media-folder-locks acquisition/lease/fencing contract` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
