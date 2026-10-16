---
id: MM-018
type: plan
project: magiq-media
workstream: WS-16a-authority-metadata
repo: mgq-dotnet-platform
tags: [mgq-dotnet-platform, sdk, messaging, authority, audit]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-018-WS-16a-authority-metadata]
pr: https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/50
merge-sha: fd6fc381
shipped: 2026-10-13
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F094-authority-on-message-metadata.md and INDEX.md#WS-16; no separate review document.
---

# WS-16a — `Authority` on `MessageMetadata` + event-store envelope + SNS propagation

**Target repo:** `mgq-dotnet-platform` — `D:\source\github\sprbrk-standard\mgq-dotnet-platform`
**Depends on:** none
**Unblocks:** MM-036 (WS-16b — magiq-media populates `Authority` on retention/legal-hold/court-order flows)

Delivers F094. Enables cross-service audit traceability for authority-driven events (retention schedule, legal hold, archival decision, court order).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-dotnet-platform`. Paste:

> Picking up WS-16a (plan MM-018). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-16a-authority-metadata\WS-16a-authority-metadata-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F094-authority-on-message-metadata.md`.
>
> `Authority = { Kind, Reference, Narrative? }`. Optional on `MessageMetadata`, event-store envelope, `IExecutionContext`. Propagated unchanged through command dispatch → event raise → outbox → SNS. Consuming handler's raised event inherits `Authority` from source event's metadata (document rule).
>
> PR to `mgq-dotnet-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F094 § Required-shape + § Detection signals
- [ ] Locate `MessageMetadata`, `EventStreamItem` envelope, SNS publisher

## Phase 1 — `Authority` member
- [ ] Define `Authority` type: `{ Kind, Reference, Narrative? }`
- [ ] Optional `Authority` property on `MessageMetadata`
- [ ] Optional `Authority` property on event-store envelope (`EventStreamItem.Authority`)

## Phase 2 — `IExecutionContext.Authority`
- [ ] Nullable `Authority` slot
- [ ] Propagated unchanged through command dispatch → event raise → outbox → SNS

## Phase 3 — Propagation rules
- [ ] Document: handler consuming event with `Authority` → every raised event inherits same `Authority`
- [ ] Explicit override requires dedicated API — not implicit on command inputs
- [ ] HTTP commands may carry inbound `Authority` header (reserved; opt-in per route)

## Phase 4 — Serialization
- [ ] Event-store envelope: `authority` JSON member
- [ ] SNS message body: `authority` under `metadata`
- [ ] Backward-compat: absent member reads as null

## Phase 5 — Tests
- [ ] Unit: command context with `Authority` → raised event's envelope carries same
- [ ] Unit: SNS round-trip preserves `Authority`
- [ ] Unit: consuming handler's raised event inherits from source
- [ ] Unit: command context without `Authority` → envelope `authority` absent

## Phase 6 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `mgq-dotnet-platform/main`

## Phase 7 — Close
- [ ] F094: `status: shipped (SDK portion)`
- [ ] platform-capabilities/INDEX.md: WS-16 split — `WS-16a shipped`, `WS-16b open`
- [ ] INTEGRATION-BACKLOG: MM-036 (WS-16b) ready

## Session log
- 2026-10-08: plan drafted
- 2026-10-13: shipped — PR #50 merged as `fd6fc381`.
  - `Authority { Kind, Reference, Narrative? }` + `AuthorityKind` enum (`RetentionSchedule` / `LegalHold` / `ArchivalDecision` / `CourtOrder` / `Other`) live in `Magiq.Platform.Core/Audit/`. `AuthorityKind` attribute-pinned to `JsonStringEnumConverter<AuthorityKind>` so member-name serialization survives host `JOptions` that lack a string converter (outbox + AWSMessaging). `Magiq.Platform.Messaging.Abstractions` gained a `Core` project ref.
  - `MessageMetadata.Authority` (init-only, nullable) carried by `OutboxLogicalMessageFactory`, `MessageHandler.MapOutgoingMessageMetadataAsync`, `DefaultMessageMetadata`, `AspNetCoreMessageMetadata`. Round-trips SNS→SQS via STJ; absent member reads as null (backwards-compat). Same change filled the `OriginatingActorId` + `TaskToken` drop in `OutboxLogicalMessageFactory` that F079/WS-05 had left behind — drive-by, bundled.
  - `EventStreamItem.Authority` (nullable) added as a slot on each per-event envelope. **Stamping on save deferred** — plan Phase 2 scopes propagation through command dispatch → event raise → outbox → SNS, not event-store envelope stamping. A follow-up would inject `IExecutionContextAccessor` into `DynamoDbEventStore` / `EventStreamItemSerializer` and stamp `IExecutionContext.Authority` onto each item at `SaveAsync` time; the gap doc's "event-store append path stamps Authority" requirement is still open.
  - `IExecutionContext.Authority` as a default-interface-method returning `null` (ordinary user actions have no external citation). `MessageExecutionContext` and `ScannerExecutionContext` override as init-only. `MessageMetadataExecutionContextAccessor` sets it from `metadata.Authority` — no fallback (unlike `OriginatingActorId`, which falls back to `ActorId` on first-hop). `IScannerExecutionContextFactory.Create` gains an optional `Authority` parameter.
  - Didn't touch command middleware — a command can set `Authority` by writing it onto `IExecutionContext` via the host-specific accessor (or by having the scanner factory bind it); explicit per-command override API not yet in scope.
  - No `Magiq.Platform.*` version bump (per batched-at-end-of-stream convention).
  - Tests: 12 new xUnit cases, all green (`dotnet test --filter "AuthorityTests|OriginatingActorIdTests"` → 20/20 pass, 411 ms). Full solution builds clean.
  - Close: F094 unblocks WS-16b (MM-036) in `magiq-media`. `docs/dependency-gaps/platform-capabilities/INDEX.md` + `INTEGRATION-BACKLOG` do not exist on the local snapshot; closure recorded in Tower + this session log only.
