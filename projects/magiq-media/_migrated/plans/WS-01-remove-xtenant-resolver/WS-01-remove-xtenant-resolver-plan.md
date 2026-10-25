---
id: MM-048
type: plan
project: magiq-media
workstream: WS-01-remove-xtenant-resolver
repo: magiq-media
tags: [magiq-media, security, tenant-resolver, pre-staging-gate]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/security/INDEX.md#WS-01; blocked by user policy (all external deps complete first).
---

# WS-01 — Remove `X-Tenant-Id` resolver registration from hosts

**Target repo:** `magiq-media`
**Depends on:** none (external); user policy blocks until all externals ship.
**Pre-staging-gate security.**

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-01 (plan MM-048). Pre-staging security fix. User policy: no magiq-media change until all external deps shipped — confirm via `docs/dependency-gaps/INTEGRATION-BACKLOG.md`.
>
> `Api` + `QueryApi` + any other host registers `X-Tenant-Id` header provider as a resolver fallback behind JWT. Remove the header provider from the resolver chain. Tenantless token → 401 (via MM-016/MM-034 if landed, else the pre-existing refusal path).
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Grep `X-Tenant-Id` across hosts
- [ ] Enumerate every host startup where the resolver chain is built
- [ ] Confirm all external deps + user policy gate

## Phase 1 — Remove registration
- [ ] Delete `X-Tenant-Id` header-provider registration from each host
- [ ] Tenantless token → 401 (ensure path exists)
- [ ] No regression on legitimate flows

## Phase 2 — Tests
- [ ] Integration: `X-Tenant-Id` header set but JWT tenant claim absent → 401 (not bypassed)
- [ ] Integration: valid JWT with tenant → unaffected
- [ ] Integration: no `X-Tenant-Id` header, no tenant claim → 401

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] security/INDEX.md: WS-01 → § Shipped
- [ ] Remove `X-Tenant-Id` bullet from `CLAUDE.md` § Known deferred/partial work

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
