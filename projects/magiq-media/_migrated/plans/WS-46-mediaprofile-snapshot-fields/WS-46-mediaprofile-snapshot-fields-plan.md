---
id: MM-060
type: plan
project: magiq-media
workstream: WS-46-mediaprofile-snapshot-fields
repo: magiq-media
tags: [magiq-media, media-profile, catalog, snapshot]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-46.
---

# WS-46 — `MediaProfileSnapshotField` expand to thirteen members

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec adds `IsSearchable`, `DisplayName`, `Description`, `Group`, `Order`, `LanguageTag`, `AutocompleteToken` (nullable, absent-meanings in `mediaitem.write-model.md`) to the current six members.

## Session invocation

> Picking up WS-46 (plan MM-060). Expand `MediaProfileSnapshotField` to 13 members. All nullable with documented absent-meanings. Backward-compat on load (nullable → absent reads as default).

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/catalog/mediaitem.write-model.md` § MediaProfileSnapshotField
- [ ] Current `MediaProfileSnapshotField` type

## Phase 1 — Add members
- [ ] `IsSearchable: bool?` (absent = false)
- [ ] `DisplayName: string?` (absent = `Name` fallback)
- [ ] `Description: string?`
- [ ] `Group: string?`
- [ ] `Order: int?`
- [ ] `LanguageTag: string?` (BCP 47)
- [ ] `AutocompleteToken: string?`

## Phase 2 — Backward compat
- [ ] Existing snapshots load with new members = null
- [ ] Projection + endpoint emit new members

## Phase 3 — Tests
- [ ] Unit: new field populates
- [ ] Unit: old snapshot loads with nulls
- [ ] Integration: endpoint returns expanded shape

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] spec-divergence/INDEX.md: WS-46 → § Shipped
- [ ] Remove `MediaProfileSnapshotField carries six members` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
