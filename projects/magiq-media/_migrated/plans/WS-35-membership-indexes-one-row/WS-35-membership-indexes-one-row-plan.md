---
id: MM-069
type: plan
project: magiq-media
workstream: WS-35-membership-indexes-one-row
repo: magiq-media
tags: [magiq-media, catalog, read-model, migration, dynamodb]
consumes: []
blocked-by-external: [MM-023, MM-068]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/projections/INDEX.md#WS-35.
---

# WS-35 — Membership indexes as one-row-per-edge

**Target repo:** `magiq-media`
**Depends on:** MM-023 (WS-21 outbox txn), MM-068 (WS-34 rebuild-index CLI)
**User policy gate:** no magiq-media change until all external deps ship.

Spec: `media-catalog-folder-folders-index` (`FOLDER_FOLDERS#{ParentId}`/`{FolderId}`), `media-catalog-folder-items-index`, `media-catalog-filing-folder-items-index`, `media-catalog-item-profile-index` as one row per edge each carrying `SourceVersion`. Current list-per-container shape fails at ~10 000 members and has no per-member fence.

## Session invocation

> Picking up WS-35 (plan MM-069). Depends on MM-023 (txn) + MM-068 (rebuild-index CLI). Reshape four membership indexes to one-row-per-edge. Each row carries `SourceVersion` for per-member fence. Migration via `rebuild-index` per index per tenant then cutover.

## Phase 0 — Scope confirmation
- [ ] Read spec for each of four indexes
- [ ] Confirm MM-023 + MM-068 shipped
- [ ] Current list-per-container shape audit

## Phase 1 — Projector rewrite
- [ ] `media-catalog-folder-folders-index`: one row per parent-child edge
- [ ] `media-catalog-folder-items-index`: one row per folder-item edge
- [ ] `media-catalog-filing-folder-items-index`: one row per filing edge
- [ ] `media-catalog-item-profile-index`: one row per item-profile edge
- [ ] Each carries `SourceVersion`

## Phase 2 — Migration per tenant
- [ ] `projections rebuild-index --index <name> --tenant <tenant>` per index per tenant
- [ ] Cutover (traffic flip or dual-write period per deploy practice)

## Phase 3 — Transactional writes
- [ ] Membership index puts in same `TransactWriteItems` as event-store append (uses MM-023 txn contract)

## Phase 4 — Tests
- [ ] Unit: projector writes correct edge shape
- [ ] Unit: fence refuses stale `SourceVersion`
- [ ] Integration: 10k+ member container reads cleanly

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] projections/INDEX.md: WS-35 → § Shipped
- [ ] Remove `Write-side membership indexes are list-per-container` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-023 + MM-068 + user policy)
