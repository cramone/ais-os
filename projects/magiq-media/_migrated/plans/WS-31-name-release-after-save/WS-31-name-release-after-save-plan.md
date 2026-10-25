---
id: MM-063
type: plan
project: magiq-media
workstream: WS-31-name-release-after-save
repo: magiq-media
tags: [magiq-media, name-reservation, handlers, catalog]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/name-reservation/INDEX.md#WS-31.
---

# WS-31 — Name releases after save + rename/move reserve-new/release-old

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Current: `CompleteCollectionArchive`, `ArchiveFolderNode`, `ArchiveMediaItem`, `DeprecateMediaProfile`, `AbandonMediaProfile` release name BEFORE `SaveAsync`. Rename/move handlers use `SwapAsync`/`MoveAsync` before append. Only `CreateMediaProfileHandler` + `PublishMediaProfileHandler` compensate failed save. Spec: release AFTER save; reserve-new/release-old for rename/move.

## Session invocation

> Picking up WS-31 (plan MM-063). Reorder release/reserve ops relative to `SaveAsync`. Reserve-new BEFORE save; append event; on success release-old; on save failure release-new.

## Phase 0 — Scope confirmation
- [ ] Enumerate handlers listed above
- [ ] Grep release/swap call sites relative to SaveAsync

## Phase 1 — Archive/deprecate handlers release-after-save
- [ ] `CompleteCollectionArchive`, `ArchiveFolderNode`, `ArchiveMediaItem`, `DeprecateMediaProfile`, `AbandonMediaProfile`
- [ ] Pattern: `SaveAsync` → on success release name; on failure leave name reserved (retry safe)

## Phase 2 — Rename/move reserve-new/release-old
- [ ] Rename: reserve-new → `SaveAsync` → on success release-old; on failure release-new (compensation)
- [ ] Move: analogous

## Phase 3 — Tests
- [ ] Unit per handler: save success → correct release outcome
- [ ] Unit: save failure → correct compensation outcome
- [ ] Integration: concurrent rename contention tests

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] name-reservation/INDEX.md: WS-31 → § Shipped
- [ ] Remove `Name releases happen before the save` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
