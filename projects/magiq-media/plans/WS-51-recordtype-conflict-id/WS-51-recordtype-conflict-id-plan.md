---
id: MM-057
type: plan
project: magiq-media
workstream: WS-51-recordtype-conflict-id
repo: magiq-media
tags: [magiq-media, metadata, record-type, error-extensions]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-51.
---

# WS-51 — `conflictingRecordTypeId` on `RecordTypeNameConflict` + `RecordTypeAliasNotUnique`

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec: name conflicts carry the reservation's `ownerId` on every `RecordTypeNameConflict` / `RecordTypeAliasNotUnique`. Metadata handlers never set it.

## Session invocation

> Picking up WS-51 (plan MM-057). Metadata name-conflict refusals must populate `conflictingRecordTypeId` extension from reservation's `OwnerId` (consult SDK's `IReservationOwnerProbe` once MM-021/MM-040 land; else from registry probe).

## Phase 0 — Scope confirmation
- [ ] Grep `RecordTypeNameConflict` / `RecordTypeAliasNotUnique` raise sites
- [ ] Confirm MM-021 + MM-040 shipped (`CatalogReservationProbe`) — or equivalent for Metadata

## Phase 1 — Populate extension
- [ ] On conflict: call `GetOwnerIdAsync(scope, name)` to resolve
- [ ] Add `conflictingRecordTypeId` to ProblemDetails extension

## Phase 2 — Tests
- [ ] Unit: name conflict → extension populated with owner id
- [ ] Unit: alias conflict → extension populated

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] spec-divergence/INDEX.md: WS-51 → § Shipped
- [ ] Remove `Name conflicts don't carry conflictingRecordTypeId` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
