---
id: MM-071
type: plan
project: magiq-media
workstream: WS-52-searchable-metadata-fields
repo: magiq-media
tags: [magiq-media, catalog, media-item, search, opensearch]
consumes: []
blocked-by-external: [MM-070]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-52.
---

# WS-52 — `SearchableMetadataFields` on MediaItem detail row + `SearchableMetadata` on `media-items` document

**Target repo:** `magiq-media`
**Depends on:** MM-070 (WS-37 OpenSearch events-based projector)
**User policy gate:** no magiq-media change until all external deps ship.

Spec: `SearchableMetadataFields` on MediaItem detail (from snapshot's `IsSearchable`); derived `SearchableMetadata { Key, Value, Text }` list on `media-items` doc; matched by `?q=`.

## Session invocation

> Picking up WS-52 (plan MM-071). Depends on MM-070. Project `SearchableMetadataFields` from `MediaProfileSnapshot` fields where `IsSearchable == true`. Projectors.Search derives `SearchableMetadata` list on `media-items` doc. `?q=` matches `.Text` field across list.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-070 shipped
- [ ] Confirm MM-060 (MediaProfileSnapshotField expansion) shipped (`IsSearchable` member available)

## Phase 1 — Detail-row projection
- [ ] Project `SearchableMetadataFields` from `MediaProfileSnapshot` fields where `IsSearchable == true`
- [ ] Stored on MediaItem detail row

## Phase 2 — Search document
- [ ] `Projectors.Search` builds `SearchableMetadata` as list of `{ Key, Value, Text }`
- [ ] `Text` = flattened text; indexable
- [ ] `?q=` query matches `Text` across list

## Phase 3 — Reindex path
- [ ] `projections reindex --index media-items --tenant <t>` rebuilds post-ship
- [ ] Alias flip

## Phase 4 — Tests
- [ ] Unit: projector derives from snapshot
- [ ] Unit: `?q=` matches on configured searchable fields
- [ ] Integration: media item with multiple searchable fields searchable by any

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] spec-divergence/INDEX.md: WS-52 → § Shipped
- [ ] Remove `Searchable metadata not indexed` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-070 + user policy)
