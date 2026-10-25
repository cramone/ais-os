---
id: MM-070
type: plan
project: magiq-media
workstream: WS-37-opensearch-external-versioning
repo: magiq-media
tags: [magiq-media, opensearch, projections, search]
consumes: []
blocked-by-external: [MM-068]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/projections/INDEX.md#WS-37.
---

# WS-37 — OpenSearch external versioning + events-based `Projectors.Search` + `reindex` CLI

**Target repo:** `magiq-media`
**Depends on:** MM-068 (WS-34 rebuild-index CLI)
**User policy gate:** no magiq-media change until all external deps ship.
**Unblocks:** MM-071 (WS-52 SearchableMetadataFields)

Spec: `version_type=external`, `version=AggregateVersion` (refusal is success), id `{tenantId}#DETAIL#{aggregateId}`, projector reads source stream events (never read-model), alias flip on mapping change. Add `projections reindex --index <name> --tenant <name>`.

## Session invocation

> Picking up WS-37 (plan MM-070). Depends on MM-068. Flip Search projector to events-based. Set `version_type=external` + `version=AggregateVersion` on indexing. Tenant-prefix id. Add `reindex` CLI verb for `media-items` + `media-registrations`. Alias flip strategy on mapping change.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-068 shipped
- [ ] Current OpenSearch projector reads read-model today — audit all read paths
- [ ] Enumerate OpenSearch indexes: `media-items`, `media-registrations`

## Phase 1 — External versioning
- [ ] Indexing requests set `version_type=external` + `version=AggregateVersion`
- [ ] `_id` = `{tenantId}#DETAIL#{aggregateId}` on `media-items` + `media-registrations`

## Phase 2 — Events-based projector
- [ ] `Projectors.Search` builds document from source stream events (not DynamoDB read model)
- [ ] One handler per aggregate event; emits full document on each

## Phase 3 — `reindex` CLI
- [ ] `projections reindex --index <name> --tenant <name>` verb
- [ ] Writes to a new index name; flips alias on completion

## Phase 4 — Tests
- [ ] Unit: indexing with older version → OpenSearch refuses; projector treats as success
- [ ] Unit: projector builds correct document from events
- [ ] Integration: reindex via alias flip — no search outage

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] projections/INDEX.md: WS-37 → § Shipped
- [ ] Remove `OpenSearch write path` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-068 + user policy)
