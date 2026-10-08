---
id: MM-030
type: plan
project: magiq-media
workstream: WS-54a-capability-field-registry
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, capability-fields, classification]
consumes: []
blocked-by-external: [MM-022]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-54 (no gap file; row-tracked); no separate review document.
---

# WS-54a — `ICapabilityFieldRegistry` SDK

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** MM-022 (WS-28a — versioned embedded resources use alias path)
**Unblocks:** MM-044 (WS-54b — magiq-media schemes + route + metric)

Governance groups (classification markings) resolve against this registry; a route surfaces configured scheme per-tenant.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Confirm MM-022 (WS-28a) shipped. Paste:

> Picking up WS-54a (plan MM-030). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-54a-capability-field-registry\WS-54a-capability-field-registry-plan.md`.
>
> Depends on WS-28a (MM-022) shipped. Deliver `ICapabilityFieldRegistry.GetGroups(capability, scheme, version)` returning `IReadOnlyList<CapabilityFieldGroup>`. `CapabilityFieldGroup { Key, Fields[], Scheme, Version, Markings[], Order }`. Loader from embedded resources; startup validation for no duplicate `(scheme, version)`; alias path uses WS-28a mechanism.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/catalog/` § Capability field groups
- [ ] Confirm MM-022 shipped (versioned embedded resources rely on alias path)
- [ ] Enumerate existing capability-group handling

## Phase 1 — `ICapabilityFieldRegistry`
- [ ] Interface: `IReadOnlyList<CapabilityFieldGroup> GetGroups(CapabilityKey capability, ClassificationScheme scheme, Version schemeVersion)`
- [ ] `CapabilityFieldGroup`: `{ Key, Fields[], Scheme, Version, Markings[], Order }`
- [ ] DI: `AddCapabilityFieldRegistry(cfg => cfg.AddScheme(...))`

## Phase 2 — Embedded-resource loader
- [ ] Scheme definitions from embedded JSON / YAML resources
- [ ] Version-pinned per spec `<scheme>@<version>`
- [ ] Startup validation: no duplicate `(scheme, version)`

## Phase 3 — `CapabilityFieldGroupScheme`
- [ ] `ClassificationScheme` enum / string key (platform-neutral)
- [ ] `ClassificationSchemeVersion` wraps `(Scheme, Version)`

## Phase 4 — Query path
- [ ] `GetGroups` returns ordered list; `Order` member
- [ ] Null registry for `(capability, scheme)` → empty; caller decides refusal

## Phase 5 — Tests
- [ ] Unit: registry from embedded resources returns expected groups
- [ ] Unit: unknown `(scheme, version)` → empty
- [ ] Unit: duplicate registration → startup throws

## Phase 6 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 7 — Close
- [ ] spec-divergence/INDEX.md: WS-54 split — `WS-54a shipped`, `WS-54b open`
- [ ] INTEGRATION-BACKLOG: MM-044 (WS-54b) `Dep status: shipped (WS-54a + WS-28a); Integration status: ready`

## Session log
- 2026-10-08: plan drafted (blocked on MM-022 ship)
