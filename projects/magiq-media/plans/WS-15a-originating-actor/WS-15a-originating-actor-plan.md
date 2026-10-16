---
id: MM-017
type: plan
project: magiq-media
workstream: WS-15a-originating-actor
repo: mgq-dotnet-platform
tags: [mgq-dotnet-platform, sdk, messaging, actor, context]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-017-WS-15a-originating-actor]
pr: https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/37
merge-sha: b0720738
shipped: 2026-10-12
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F079-originating-actor-and-scanner-context.md and INDEX.md#WS-15; no separate review document.
---

# WS-15a — `OriginatingActorId` on `MessageMetadata` + scanner execution-context factory

**Target repo:** `mgq-dotnet-platform` — `D:\source\github\sprbrk-standard\mgq-dotnet-platform`
**Depends on:** none
**Unblocks:** MM-035 (WS-15b — magiq-media populates originating actor on dispatched commands + scanner context)

Delivers F079. Scanner / saga / cascade work carries originating actor forward so downstream audit entries name the human / system that caused the chain, not the scanner identity.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-dotnet-platform`. Paste:

> Picking up WS-15a (plan MM-017). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-15a-originating-actor\WS-15a-originating-actor-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F079-originating-actor-and-scanner-context.md`.
>
> Add optional `OriginatingActorId` on `MessageMetadata` (SNS/SQS envelope + event-store envelope round-trip). Add nullable `IExecutionContext.OriginatingActorId`. Add `IScannerExecutionContextFactory` that produces per-dispatch context with `Actor = System` + supplied originating actor.
>
> PR to `mgq-dotnet-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F079 § Required-shape
- [ ] Locate `MessageMetadata` + `IExecutionContext`

## Phase 1 — `OriginatingActorId` on `MessageMetadata`
- [ ] Add optional property; serialize/deserialize across SNS/SQS envelopes
- [ ] Preserve across event-store write/read

## Phase 2 — `IExecutionContext.OriginatingActorId`
- [ ] Add nullable slot
- [ ] HTTP context: default = `Actor.Id` (self-originating)
- [ ] SQS context: `MessageMetadataExecutionContextAccessor` reads from message metadata

## Phase 3 — Scanner per-dispatch factory
- [ ] `IScannerExecutionContextFactory.Create(tenantId, originatingActorId)` → `IExecutionContext` with `TenantId` set + `Actor = System` + `OriginatingActorId` as passed
- [ ] Scoped per-dispatch so scanner batching doesn't bleed context

## Phase 4 — Propagation rule
- [ ] Document: `OriginatingActorId` copies unchanged through command/event dispatch
- [ ] Explicit override requires `IOriginatingActorOverride` service (reserved; not used today)

## Phase 5 — Tests
- [ ] Unit: HTTP context defaults `OriginatingActorId = Actor.Id`
- [ ] Unit: SQS context reads from metadata
- [ ] Unit: scanner factory produces `System` + supplied originating-actor
- [ ] Unit: outbox → SNS → SQS round-trip preserves originating actor

## Phase 6 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `mgq-dotnet-platform/main`

## Phase 7 — Close
- [ ] F079: `status: shipped (SDK portion)`
- [ ] platform-capabilities/INDEX.md: WS-15 split — `WS-15a shipped`, `WS-15b open`
- [ ] INTEGRATION-BACKLOG: MM-035 (WS-15b) ready

## Session log
- 2026-10-08: plan drafted.
- 2026-10-12: shipped on branch `feature/chase/MM-017-WS-15a-originating-actor`.
  - `MessageMetadata.OriginatingActorId` added as init-only nullable prop — non-breaking, round-trips SNS→SQS + event-store envelope via existing System.Text.Json path.
  - `IExecutionContext.OriginatingActorId` as default-interface-method returning `Actor.Id` (self-originating). HTTP / Console / Lambda contexts inherit without change. `MessageExecutionContext` overrides as init-only prop; `MessageMetadataExecutionContextAccessor` sets `metadata.OriginatingActorId ?? metadata.ActorId` (first-hop fallback = acting actor is the chain's root).
  - `IScannerExecutionContextFactory.Create(string tenantId, string? originatingActorId = null)` → `IExecutionContext` (new `ScannerExecutionContext`) with `Actor = Actor.System` + supplied tenant + supplied originating actor. Default `ScannerExecutionContextFactory` singleton registered via `AddScannerExecutionContextFactory()`. New instance per call, no sweep bleed.
  - Divergence from plan Phase 2: context slot is `string?` (plan wording), not `IActor?` (gap-file wording). The id alone is enough for audit chaining — full actor rehydration would need a per-tenant actor directory the SDK doesn't own.
  - Scope deliberately excluded: dispatcher-side `IExecutionContext.TenantId = command.TenantId` enforcement (gap-file item), scanner conversion in magiq-media (WS-15b).
  - 8 new unit tests green; full solution build clean.
- 2026-10-12: PR #37 merged to `mgq-dotnet-platform/main` as `b0720738`. F079 → `status: sdk-shipped` with remainder noted. platform-capabilities/INDEX.md WS-15 split: WS-15a shipped row, WS-15b flipped to `ready` under its own row. INTEGRATION-BACKLOG MM-017 moved to § Shipped; MM-035 (WS-15b) flipped `new` → `ready`. Readiness summary bumped 63→62 `new`, 4→5 `ready`, 9→10 `shipped`.
