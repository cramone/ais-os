---
id: MM-017
type: plan
project: magiq-media
workstream: WS-15a-originating-actor
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, messaging, actor, context]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F079-originating-actor-and-scanner-context.md and INDEX.md#WS-15; no separate review document.
---

# WS-15a — `OriginatingActorId` on `MessageMetadata` + scanner execution-context factory

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-035 (WS-15b — magiq-media populates originating actor on dispatched commands + scanner context)

Delivers F079. Scanner / saga / cascade work carries originating actor forward so downstream audit entries name the human / system that caused the chain, not the scanner identity.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-15a (plan MM-017). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-15a-originating-actor\WS-15a-originating-actor-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F079-originating-actor-and-scanner-context.md`.
>
> Add optional `OriginatingActorId` on `MessageMetadata` (SNS/SQS envelope + event-store envelope round-trip). Add nullable `IExecutionContext.OriginatingActorId`. Add `IScannerExecutionContextFactory` that produces per-dispatch context with `Actor = System` + supplied originating actor.
>
> PR to `aspnetcore-platform/main`.

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
- [ ] PR to `aspnetcore-platform/main`

## Phase 7 — Close
- [ ] F079: `status: shipped (SDK portion)`
- [ ] platform-capabilities/INDEX.md: WS-15 split — `WS-15a shipped`, `WS-15b open`
- [ ] INTEGRATION-BACKLOG: MM-035 (WS-15b) ready

## Session log
- 2026-10-08: plan drafted
