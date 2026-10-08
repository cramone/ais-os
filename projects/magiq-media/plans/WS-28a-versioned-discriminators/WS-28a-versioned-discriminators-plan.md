---
id: MM-022
type: plan
project: magiq-media
workstream: WS-28a-versioned-discriminators
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, event-schema, upcaster, alias]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/event-schema/INDEX.md#WS-28 (no gap file; row-tracked); no separate review document.
---

# WS-28a — Versioned discriminators + `IEventUpcaster<T>` + alias in `IDomainEventRegistry`

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-030 (WS-54a CapabilityFieldRegistry), MM-041 (WS-28b magiq-media `[DomainEvent]` + upcasters), MM-064 (WS-29), MM-065 (WS-53)

Key driver: `registrationsubmissionrecorded@1` cannot load today — alias mechanism is required before Registration streams carrying it can be read.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-28a (plan MM-022). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-28a-versioned-discriminators\WS-28a-versioned-discriminators-plan.md`.
>
> Add `Version` + `Aliases` to `[DomainEvent]`. Discriminator format `<type>@<version>`. Introduce `IEventUpcaster<TEventIn, TEventOut>` with chain-of-responsibility. `IDomainEventRegistry.Resolve(discriminator)` tries exact match then aliases. Startup fail-hard on ambiguous alias / duplicate `(type, version)`.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/shared/event-store-and-messaging.md` § Event schema + aliases
- [ ] Locate `[DomainEvent]` attribute, `IDomainEventRegistry`, `AddDomainEventsFromAssembly`
- [ ] Enumerate current `IDomainEvent` discovery

## Phase 1 — `Version` + `Aliases` on `[DomainEvent]`
- [ ] Add `Version` (default `1`) + `Aliases` (string[])
- [ ] Discriminator format: `<type>@<version>`
- [ ] Alias format: raw string
- [ ] Backward-compat: `[DomainEvent]` without `Version` → `1`

## Phase 2 — `IEventUpcaster<TEvent>`
- [ ] `IEventUpcaster<TEventIn, TEventOut>` with `UpcastAsync(TEventIn, UpcastContext, ct)`
- [ ] Chain-of-responsibility `UpcasterChain` applies in dependency order (`v1 → v2 → v3`)
- [ ] `AddDomainEventUpcastersFromAssembly` discovery

## Phase 3 — `IDomainEventRegistry` alias resolution
- [ ] `Resolve(discriminator)` tries exact match first
- [ ] On miss: scan aliases, match aliased discriminator → canonical type + required upcasters
- [ ] Ambiguous alias → fail hard at startup

## Phase 4 — Deserialize path
- [ ] Event-store read: discriminator → canonical type → intermediate record → upcaster chain → final event
- [ ] SNS/SQS consume: same path

## Phase 5 — Startup validation
- [ ] Every registered event has `[DomainEvent]` with version
- [ ] No duplicate `(type, version)`
- [ ] No duplicate alias across types
- [ ] Fail startup with diagnostic

## Phase 6 — Tests
- [ ] Unit: current-version event (no upcaster) → succeeds
- [ ] Unit: prior-version event → runs upcaster chain
- [ ] Unit: aliased discriminator → canonical type + required upcasters
- [ ] Unit: ambiguous alias at startup → fails
- [ ] Unit: SNS → SQS → consumer path preserves version + applies upcasters

## Phase 7 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 8 — Close
- [ ] event-schema/INDEX.md: WS-28 split — `WS-28a shipped`, `WS-28b open`
- [ ] INTEGRATION-BACKLOG: MM-041 (WS-28b), MM-064 (WS-29), MM-065 (WS-53), MM-044 (WS-54b) now `Dep status: shipped`

## Session log
- 2026-10-08: plan drafted
