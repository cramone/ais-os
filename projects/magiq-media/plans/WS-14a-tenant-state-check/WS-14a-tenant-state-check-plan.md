---
id: MM-016
type: plan
project: magiq-media
workstream: WS-14a-tenant-state-check
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, tenant-resolver, auth]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F083-tenant-active-check.md and INDEX.md#WS-14; no separate review document.
---

# WS-14a — `TenantState != Running` → `401` in resolver

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-034 (WS-14b — host 401 wiring)

Delivers F083. Today `IdentifierResolutionStrategy` doesn't check tenant state; `Disabled`/`Invalid`/`Suspended` tenants continue serving requests.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-14a (plan MM-016). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-14a-tenant-state-check\WS-14a-tenant-state-check-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F083-tenant-active-check.md`.
>
> After `TenantId` resolution, load `TenantState` from registry; non-`Running` → `TenantResolutionResult.Refused(reason)` with distinct reason codes (`TenantDisabled`, `TenantSuspended`, `TenantInvalid`, `TenantPendingProvisioning`). Short state-cache (30s) + `Invalidate` hook. Reason → `401` by host middleware (WS-14b).
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F083 § Required-shape
- [ ] Locate `IdentifierResolutionStrategy` + tenant-state source
- [ ] Enumerate `TenantState` enum members

## Phase 1 — State check in resolver
- [ ] After tenant-id resolution: load `TenantState`
- [ ] Non-`Running` → `TenantResolutionResult.Refused(reason)` with distinct reasons
- [ ] Reason mapped to `401` by host middleware (WS-14b wires the ProblemDetails body)

## Phase 2 — Resolver caching
- [ ] Short cache TTL (default 30s) on tenant-state read
- [ ] `ITenantStateCache.Invalidate(tenantId)` hook for admin flows

## Phase 3 — Logging + metrics
- [ ] Log refusal at Information with `tenant_id`, `state`, `reason`
- [ ] Metric: `tenant_refused_count` with `state` dimension

## Phase 4 — Tests
- [ ] Unit: `Running` → pass through
- [ ] Unit: each non-`Running` state → refused with correct reason
- [ ] Unit: cache hit doesn't re-fetch
- [ ] Unit: `Invalidate` forces next read to fetch

## Phase 5 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 6 — Close
- [ ] F083: `status: shipped (SDK portion)`
- [ ] platform-capabilities/INDEX.md: WS-14 split — `WS-14a shipped`, `WS-14b open`
- [ ] INTEGRATION-BACKLOG: MM-034 (WS-14b) ready

## Session log
- 2026-10-08: plan drafted
