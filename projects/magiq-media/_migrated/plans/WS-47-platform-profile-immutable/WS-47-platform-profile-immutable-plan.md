---
id: MM-055
type: plan
project: magiq-media
workstream: WS-47-platform-profile-immutable
repo: magiq-media
tags: [magiq-media, catalog, media-profile, auth]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-47.
---

# WS-47 — `PlatformProfileImmutable` (403) refusal in MediaProfile handlers

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec: MediaProfile with `Origin = Platform` refuses tenant writes with `403 PlatformProfileImmutable`.

## Session invocation

> Picking up WS-47 (plan MM-055). Add refusal: handlers that mutate MediaProfile check `Origin`; if `Platform`, return `403 PlatformProfileImmutable`.

## Phase 0 — Scope confirmation
- [ ] Grep MediaProfile mutation handlers
- [ ] Confirm `ProfileOrigin` member accessible (post MM-041 WS-29 for ProfileOrigin ensure dependency)
- [ ] Verify error catalog has `PlatformProfileImmutable`

## Phase 1 — Handler refusal
- [ ] Every MediaProfile mutation command: check `Profile.Origin == Platform` → `Result.Failure(new PlatformProfileImmutable(...))`
- [ ] ProblemDetails: `403 PlatformProfileImmutable`

## Phase 2 — Tests
- [ ] Unit: tenant mutation of Platform profile → 403
- [ ] Unit: tenant mutation of Tenant profile → unaffected

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] spec-divergence/INDEX.md: WS-47 → § Shipped
- [ ] Remove `PlatformProfileImmutable` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
