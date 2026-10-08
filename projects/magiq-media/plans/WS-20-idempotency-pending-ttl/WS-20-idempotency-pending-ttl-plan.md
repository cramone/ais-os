---
id: MM-012
type: plan
project: magiq-media
workstream: WS-20-idempotency-pending-ttl
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, idempotency, http]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F072-idempotency-pending-ttl.md and INDEX.md#WS-20; no separate review document.
---

# WS-20 — Idempotency `Pending` TTL separate from completion window

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** `draft-ietf-httpapi-idempotency-key-header-07` conformance (pairs with MM-011)

Delivers F072. Current middleware uses one TTL for both Pending + Completed states; a crashed Api Lambda leaves `409 IdempotentRequestInProgress` permanent.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-20 (plan MM-012). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-20-idempotency-pending-ttl\WS-20-idempotency-pending-ttl-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F072-idempotency-pending-ttl.md`.
>
> Two-phase record: `State = Pending | Completed`. Pending TTL (default 20 min, > Api Lambda 15-min timeout). Completion TTL (default 24h). `409 IdempotentRequestInProgress` returned only when Pending within TTL.
>
> Read `aspnetcore-platform/CLAUDE.md`. PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F072 § Required-shape
- [ ] Confirm current middleware uses single TTL for both states
- [ ] Verify Api Lambda max timeout; align Pending TTL above it

## Phase 1 — Two-phase record
- [ ] Store schema: `State = Pending | Completed`
- [ ] Pending write carries `PendingExpiresAt` (now + `PendingTtl`, default 20 min)
- [ ] Completed write carries `CompletedExpiresAt` (now + `CompletionTtl`, default 24h)
- [ ] Lookup: if `State = Pending` and `PendingExpiresAt < now` → treat absent

## Phase 2 — `409 IdempotentRequestInProgress`
- [ ] Returned only when `State = Pending` and `PendingExpiresAt > now`
- [ ] After Pending expiry, second request admitted

## Phase 3 — Options + defaults
- [ ] `IdempotencyOptions.PendingTtl` (default 20 min)
- [ ] `IdempotencyOptions.CompletionTtl` (default 24h)
- [ ] XML doc: Pending TTL must exceed max expected handler latency

## Phase 4 — Tests
- [ ] Unit: Pending within TTL → 409
- [ ] Unit: Pending past TTL → admitted
- [ ] Unit: Completed → replay unchanged
- [ ] Unit: handler-crash scenario simulated by not-writing-Completed

## Phase 5 — Package + ship
- [ ] Bump version; push internal NuGet
- [ ] PR to `aspnetcore-platform/main`

## Phase 6 — Close
- [ ] F072: shipped
- [ ] platform-capabilities/INDEX.md: WS-20 → § Shipped

## Session log
- 2026-10-08: plan drafted
