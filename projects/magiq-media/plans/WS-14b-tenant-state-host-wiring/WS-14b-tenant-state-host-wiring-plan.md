---
id: MM-034
type: plan
project: magiq-media
workstream: WS-14b-tenant-state-host-wiring
repo: magiq-media
tags: [magiq-media, hosts, tenant, auth, problem-details]
consumes: []
blocked-by-external: [MM-016]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-14 F083.
---

# WS-14b — Host wiring for `TenantState != Running` 401 refusal

**Target repo:** `magiq-media`
**Depends on:** MM-016 (WS-14a — SDK resolver refusal reason)
**User policy gate:** no magiq-media code change until all external deps ship.

Wire SDK `TenantResolutionResult.Refused(reason)` through FastEndpoints problem-details mapper so hosts return `401` with distinct `errorCode`s (`TenantDisabled`, `TenantSuspended`, `TenantInvalid`, `TenantPendingProvisioning`).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-14b (plan MM-034). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-14b-tenant-state-host-wiring\WS-14b-tenant-state-host-wiring-plan.md`.
>
> SDK (MM-016) now refuses non-Running tenant with distinct reasons. Wire into `Api` + `QueryApi` ProblemDetails: `401` body per reason. Confirm `media-tenants` table row read path. Add integration tests exercising each non-Running state.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-016 shipped
- [ ] Enumerate FastEndpoints host startup where resolver is registered
- [ ] Confirm `media-tenants` read path intact

## Phase 1 — Problem-details mapper
- [ ] Map each `TenantResolutionResult.Refused(reason)` to `401` with distinct `errorCode`
- [ ] Include tenant-id in logs (not response body)

## Phase 2 — Host registration
- [ ] `Api` + `QueryApi`: register SDK resolver with tenant-state check
- [ ] Remove `X-Tenant-Id` resolver (coordinate with WS-01 / MM-048 — if landing concurrently, same PR)

## Phase 3 — Tests
- [ ] Integration: `Disabled` tenant → 401 `TenantDisabled`
- [ ] Integration: `Suspended` tenant → 401 `TenantSuspended`
- [ ] Integration: `Invalid` tenant → 401 `TenantInvalid`
- [ ] Integration: `Running` tenant → request proceeds

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] F083: shipped (full)
- [ ] INTEGRATION-BACKLOG: WS-14b → § Shipped
- [ ] Remove `Tenant-active enforcement missing` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-016 + user policy)
