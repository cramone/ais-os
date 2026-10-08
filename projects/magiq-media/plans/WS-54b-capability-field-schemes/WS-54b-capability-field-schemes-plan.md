---
id: MM-044
type: plan
project: magiq-media
workstream: WS-54b-capability-field-schemes
repo: magiq-media
tags: [magiq-media, catalog, capability-fields, classification]
consumes: []
blocked-by-external: [MM-030]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-54.
---

# WS-54b — Register schemes + tenant setting + route + metric

**Target repo:** `magiq-media`
**Depends on:** MM-030 (WS-54a SDK)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-54b (plan MM-044). SDK (MM-030) ships `ICapabilityFieldRegistry`.
>
> Register schemes (AU PSPF, NZ PSR pending Karen; whatever Karen delivers). Bind `Media:Catalog:ClassificationScheme` tenant setting. Expose `GET /v1/capability-field-groups/{capability}?scheme=` route. Emit `Catalog/GovernanceGroupUnresolved` metric when a route references an unresolved scheme.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-030 shipped
- [ ] Confirm Karen delivered scheme content for AU PSPF / NZ PSR

## Phase 1 — Scheme registrations
- [ ] Embed each delivered scheme as versioned resource
- [ ] Register via `AddCapabilityFieldRegistry(cfg => cfg.AddScheme(...))`

## Phase 2 — Tenant setting
- [ ] Bind `Media:Catalog:ClassificationScheme` from tenant settings
- [ ] Fallback: default per-tenant scheme per config

## Phase 3 — Route
- [ ] `GET /v1/capability-field-groups/{capability}?scheme=` FastEndpoint
- [ ] Resolves scheme from tenant setting + query override
- [ ] Returns ordered list of capability field groups

## Phase 4 — Metric
- [ ] `Catalog/GovernanceGroupUnresolved` emitted when route resolves to empty
- [ ] CloudWatch alarm (via `cdk-magiq-media` — coordinate)

## Phase 5 — Tests
- [ ] Unit: route returns groups for registered scheme
- [ ] Unit: unknown scheme → empty + metric emitted
- [ ] Integration: round-trip with tenant-settings override

## Phase 6 — Ship
- [ ] PR to `develop`

## Phase 7 — Close
- [ ] spec-divergence/INDEX.md: WS-54 → § Shipped
- [ ] INTEGRATION-BACKLOG: WS-54b → § Shipped
- [ ] Remove `Capability field groups not built` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-030 + user policy)
