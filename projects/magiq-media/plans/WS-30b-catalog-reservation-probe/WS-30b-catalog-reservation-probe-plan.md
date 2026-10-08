---
id: MM-040
type: plan
project: magiq-media
workstream: WS-30b-catalog-reservation-probe
repo: magiq-media
tags: [magiq-media, catalog, name-reservation, probe]
consumes: []
blocked-by-external: [MM-021]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-30.
---

# WS-30b — `CatalogReservationProbe` + per-scope registration

**Target repo:** `magiq-media`
**Depends on:** MM-021 (WS-30a SDK)
**User policy gate:** no magiq-media code change until all external deps ship.

Spec: Catalog owns five reservation scopes (`media-collection`, `parent:{parentFolderId}`, `media-collection:{collectionId}`, `media-item:{folderId}`, `media-profile`). Each needs an `IReservationOwnerProbe` so stuck reservations can self-repair.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-30b (plan MM-040). SDK (MM-021) ships `IReservationOwnerProbe` hook.
>
> Implement `CatalogReservationProbe : IReservationOwnerProbe` with `GetOwnerIdAsync(scope, name, ct)` reading the right read model per scope. Register one probe instance per scope key via `AddReservationProbe<CatalogReservationProbe>(scope)`.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-021 shipped
- [ ] List Catalog reservation scopes per spec
- [ ] Identify read model for each scope (collection by name, folder by parent+name, media-item by folder+name, media-profile by name)

## Phase 1 — Probe implementation
- [ ] `CatalogReservationProbe.GetOwnerIdAsync(scope, name, ct)` dispatches per scope
- [ ] Each scope: query corresponding read model, return `AggregateId?`
- [ ] `media-collection`: `media-collections` by name
- [ ] `parent:{parentFolderId}`: `media-folders` by parent+name
- [ ] `media-collection:{collectionId}`: `media-folders` scoped to collection by name
- [ ] `media-item:{folderId}`: `media-items` scoped to folder by name
- [ ] `media-profile`: `media-profiles` by name

## Phase 2 — Registration
- [ ] Catalog host DI: `AddReservationProbe<CatalogReservationProbe>(scope)` × 5
- [ ] One instance can handle all scopes if dispatch is internal — pick per SDK convention

## Phase 3 — Tests
- [ ] Unit per scope: probe returns correct aggregate id
- [ ] Unit: probe returns null when read model row absent
- [ ] Integration: stuck reservation → same aggregate's retry succeeds via probe

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] name-reservation/INDEX.md: WS-30 → § Shipped
- [ ] INTEGRATION-BACKLOG: WS-30b → § Shipped
- [ ] Remove `CatalogReservationProbe not registered` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-021 + user policy)
