---
id: MM-045
type: plan
project: magiq-media
workstream: WS-38b-collection-gsi3-write
repo: magiq-media
tags: [magiq-media, catalog, projection, dynamodb, gsi]
consumes: []
blocked-by-external: [MM-009]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-38.
---

# WS-38b — Populate `GSI3PK` on `MediaCollection` writes + handler read

**Target repo:** `magiq-media`
**Depends on:** MM-009 (WS-38a infra — GSI3 provisioned)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-38b (plan MM-045). CDK (MM-009) provisioned GSI3 on `media-collections`.
>
> `MediaCollection` detail-row writes populate `GSI3PK = TENANT#{TenantId}#PROFILE#{MediaProfileId}#COLLECTIONS` where `DefaultMediaProfileId` present. Wire `MediaProfileDeprecatedEventHandler` to query GSI3 for affected collections. Backfill existing rows (projection replay via `rebuild-index` once MM-068 lands — coordinate).
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-009 shipped (GSI3 active in each env)
- [ ] Locate `MediaCollection` projector write path

## Phase 1 — Populate `GSI3PK`
- [ ] On `MediaCollection` detail-row write: set `GSI3PK` when `DefaultMediaProfileId` present
- [ ] On profile change: update `GSI3PK`
- [ ] On profile clear: delete `GSI3PK` attribute (removes from GSI3)

## Phase 2 — `MediaProfileDeprecatedEventHandler`
- [ ] Query GSI3 for collections carrying the deprecated profile
- [ ] Dispatch commands per collection (profile reset / warning per spec)

## Phase 3 — Backfill
- [ ] Document: full backfill ships via `projections rebuild-index --index media-collections` (coordinate with MM-068 WS-34)

## Phase 4 — Tests
- [ ] Unit: write with profile → `GSI3PK` set
- [ ] Unit: profile change → `GSI3PK` updates
- [ ] Unit: profile cleared → `GSI3PK` attribute removed
- [ ] Integration: `MediaProfileDeprecated` → affected collections found + commands dispatched

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] stored-shapes/INDEX.md: WS-38 → § Shipped
- [ ] INTEGRATION-BACKLOG: WS-38b → § Shipped
- [ ] Remove `CollectionByDefaultProfileIndex` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-009 + user policy)
