---
id: MM-064
type: plan
project: magiq-media
workstream: WS-29-mediaprofile-origin-member
repo: magiq-media
tags: [magiq-media, media-profile, event, migration]
consumes: []
blocked-by-external: [MM-041]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/event-schema/INDEX.md#WS-29.
---

# WS-29 — `MediaProfileCreated` carries `ProfileOrigin` from first written form

**Target repo:** `magiq-media`
**Depends on:** MM-041 (WS-28b — upcasters framework)
**User policy gate:** no magiq-media change until all external deps ship.

Spec assumes no deployed stream predates the member. If any env carries it without, replay reads enum zero-ordinal silently. Recovery options:
- (a) One-shot `RecordMediaProfileOrigin` dispatch per affected profile
- (b) Grow a `MediaProfileOriginRecorded` event + `v1→v2` upcaster

Pick based on affected count.

## Session invocation

> Picking up WS-29 (plan MM-064). Depends on MM-041. Audit each env for `MediaProfileCreated@1` records missing `ProfileOrigin`. If common, write `v1→v2` upcaster assuming default. If rare, dispatch `RecordMediaProfileOrigin` per affected profile.

## Phase 0 — Audit affected
- [ ] Confirm MM-041 shipped
- [ ] Count affected `MediaProfileCreated` records per env
- [ ] Pick path (a) or (b)

## Phase 1a — If dispatch path
- [ ] `RecordMediaProfileOrigin` command + handler
- [ ] One-shot script dispatches per affected profile

## Phase 1b — If upcaster path
- [ ] `MediaProfileOriginRecorded@1` new event
- [ ] `MediaProfileCreated` `v1 → v2` upcaster inserts default `ProfileOrigin`
- [ ] Projection replay

## Phase 2 — Tests
- [ ] Unit: new `MediaProfileCreated@2` writes with origin
- [ ] Unit per path: recovery runs idempotently

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] event-schema/INDEX.md: WS-29 → § Shipped
- [ ] Remove `MediaProfileCreated carries ProfileOrigin` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-041 + user policy)
