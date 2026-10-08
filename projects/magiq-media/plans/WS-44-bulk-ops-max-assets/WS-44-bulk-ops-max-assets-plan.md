---
id: MM-054
type: plan
project: magiq-media
workstream: WS-44-bulk-ops-max-assets
repo: magiq-media
tags: [magiq-media, catalog, config, bulk]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-44.
---

# WS-44 — `BulkOperationsOptions.MaxAssetsPerRequest` on Catalog's class

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Catalog's `BulkOperationsOptions` class has no `MaxAssetsPerRequest` member → bind to root-level `BulkOperations` section takes compiled defaults silently.

## Session invocation

> Picking up WS-44 (plan MM-054). Add `MaxAssetsPerRequest` property to Catalog's `BulkOperationsOptions`. Bind from `Media:Catalog:BulkOperations` section. Document default. Validation: positive int.

## Phase 0 — Scope confirmation
- [ ] Locate `BulkOperationsOptions` class in Catalog
- [ ] Confirm current binding section + compiled default

## Phase 1 — Add property
- [ ] `public int MaxAssetsPerRequest { get; set; } = <default-per-spec>`
- [ ] Options validator: positive int

## Phase 2 — Consumer wiring
- [ ] `BulkCreateMediaItemsHandler` reads `.MaxAssetsPerRequest`
- [ ] Request exceeding → 400 with `errorCode: BulkRequestTooLarge`

## Phase 3 — Tests
- [ ] Unit: config bound correctly
- [ ] Unit: oversized request → 400
- [ ] Unit: zero / negative config → startup validation fails

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] spec-divergence/INDEX.md: WS-44 → § Shipped
- [ ] Remove `BulkOperationsOptions` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
