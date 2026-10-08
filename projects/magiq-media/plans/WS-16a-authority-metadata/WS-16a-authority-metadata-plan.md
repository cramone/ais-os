---
id: MM-018
type: plan
project: magiq-media
workstream: WS-16a-authority-metadata
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, messaging, authority, audit]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F094-authority-on-message-metadata.md and INDEX.md#WS-16; no separate review document.
---

# WS-16a — `Authority` on `MessageMetadata` + event-store envelope + SNS propagation

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-036 (WS-16b — magiq-media populates `Authority` on retention/legal-hold/court-order flows)

Delivers F094. Enables cross-service audit traceability for authority-driven events (retention schedule, legal hold, archival decision, court order).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-16a (plan MM-018). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-16a-authority-metadata\WS-16a-authority-metadata-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F094-authority-on-message-metadata.md`.
>
> `Authority = { Kind, Reference, Narrative? }`. Optional on `MessageMetadata`, event-store envelope, `IExecutionContext`. Propagated unchanged through command dispatch → event raise → outbox → SNS. Consuming handler's raised event inherits `Authority` from source event's metadata (document rule).
>
> PR to `aspnetcore-platform/main`.

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
- [ ] PR to `aspnetcore-platform/main`

## Phase 7 — Close
- [ ] F094: `status: shipped (SDK portion)`
- [ ] platform-capabilities/INDEX.md: WS-16 split — `WS-16a shipped`, `WS-16b open`
- [ ] INTEGRATION-BACKLOG: MM-036 (WS-16b) ready

## Session log
- 2026-10-08: plan drafted
