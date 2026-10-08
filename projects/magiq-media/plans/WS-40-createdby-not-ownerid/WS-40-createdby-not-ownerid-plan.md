---
id: MM-050
type: plan
project: magiq-media
workstream: WS-40-createdby-not-ownerid
repo: magiq-media
tags: [magiq-media, catalog, read-model, projection]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/stored-shapes/INDEX.md#WS-40.
---

# WS-40 — Collection + Folder read-model `CreatedBy` (not `OwnerId`)

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec: `media-collections`, `media-collection`, `media-folders`, `media-folder` project `CreatedBy`, not `OwnerId`. No deployed data to migrate (greenfield).

## Session invocation

> Picking up WS-40 (plan MM-050). Grep read-model projectors + endpoints emitting `OwnerId` on Collection + Folder shapes. Rename to `CreatedBy`. Update DTOs + endpoints + any search doc. No migration (no deployed data under old shape).

## Phase 0 — Scope confirmation
- [ ] Grep `OwnerId` across Collection + Folder read-model code
- [ ] Confirm no deployed data under old shape

## Phase 1 — Rename
- [ ] Projectors emit `CreatedBy`
- [ ] DTOs expose `CreatedBy`
- [ ] Endpoints emit `CreatedBy`

## Phase 2 — Tests
- [ ] Unit: projector writes `CreatedBy`
- [ ] Integration: endpoint returns `CreatedBy`

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] stored-shapes/INDEX.md: WS-40 → § Shipped
- [ ] Remove `CreatedBy` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
