---
id: MM-049
type: plan
project: magiq-media
workstream: WS-26-version-mismatch-412
repo: magiq-media
tags: [magiq-media, http, concurrency, wire-contract]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-26.
---

# WS-26 — `VersionMismatch` → `412 Precondition Failed`

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

RFC 9110 § 13.1.1: failed `If-Match` is 412, not 409. Also `If-Match` on an uncovered route → `400 InvalidIfMatch`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-26 (plan MM-049). Wire-status change: `VersionMismatch` → 412 (RFC 9110). Also 400 `InvalidIfMatch` for `If-Match` on uncovered routes.
>
> Coordinate with client SDKs switching on 409 — breaking change if any client depends on current behaviour.

## Phase 0 — Scope confirmation
- [ ] Confirm all external deps shipped + user policy gate
- [ ] Grep `VersionMismatch` → 409 mapping sites
- [ ] Enumerate `If-Match` routes
- [ ] Check client SDK usage of 409 on write endpoints

## Phase 1 — Mapping fix
- [ ] `ProblemDetailsMapper`: `VersionMismatch` → 412 `Precondition Failed`
- [ ] `If-Match` on uncovered route → `400 InvalidIfMatch`

## Phase 2 — Communicate change
- [ ] Document breaking change in PR description + release notes
- [ ] Coordinate with magiq-media-ui (UI client)

## Phase 3 — Tests
- [ ] Integration: stale `If-Match` → 412
- [ ] Integration: `If-Match` on route not supporting it → 400 `InvalidIfMatch`
- [ ] Integration: matching `If-Match` → request proceeds

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] platform-capabilities/INDEX.md: WS-26 → § Shipped
- [ ] Remove `VersionMismatch answers 409` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
