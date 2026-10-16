---
id: MM-012
type: plan
project: magiq-media
workstream: WS-20-idempotency-pending-ttl
repo: mgq-dotnet-platform
tags: [mgq-dotnet-platform, sdk, idempotency, http]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-011-MM-012-WS-19-20-idempotency-rewrite]
pr: https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/35
merge-sha: 68706c06
shipped: 2026-10-12
shipped-jointly-with: MM-011 (WS-19-idempotency-replay-headers)
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F072-idempotency-pending-ttl.md and INDEX.md#WS-20; no separate review document.
---

# WS-20 — Idempotency `Pending` TTL separate from completion window

**Target repo:** `mgq-dotnet-platform` — `D:\source\github\sprbrk-standard\mgq-dotnet-platform`
**Depends on:** none
**Unblocks:** `draft-ietf-httpapi-idempotency-key-header-07` conformance (pairs with MM-011)

Delivers F072. Current middleware uses one TTL for both Pending + Completed states; a crashed Api Lambda leaves `409 IdempotentRequestInProgress` permanent.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-dotnet-platform`. Paste:

> Picking up WS-20 (plan MM-012). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-20-idempotency-pending-ttl\WS-20-idempotency-pending-ttl-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F072-idempotency-pending-ttl.md`.
>
> Two-phase record: `State = Pending | Completed`. Pending TTL (default 20 min, > Api Lambda 15-min timeout). Completion TTL (default 24h). `409 IdempotentRequestInProgress` returned only when Pending within TTL.
>
> Read `mgq-dotnet-platform/CLAUDE.md`. PR to `mgq-dotnet-platform/main`.

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
- [ ] PR to `mgq-dotnet-platform/main`

## Phase 6 — Close
- [ ] F072: shipped
- [ ] platform-capabilities/INDEX.md: WS-20 → § Shipped

## Session log
- 2026-10-08: plan drafted.
- 2026-10-12: shipped jointly with WS-19 under one middleware rewrite PR — the two gaps are one capability. See WS-19 plan session log for the full implementation record. Branch `feature/chase/MM-011-MM-012-WS-19-20-idempotency-rewrite`; PR #35; merge SHA `68706c06`. Phase 1–5 acceptance covered by the WS-19 shipment (two-phase record, Pending TTL distinct from Window, `IdempotencyOptions.PendingHorizon` default 20min > 15min Lambda, 409 IdempotentRequestInProgress only when Pending within horizon, Completed replay unchanged, handler-crash scenario via Pending TTL expiry). Host-side invariant `PendingHorizon > ApiLambdaTimeout + PipelineRetryBudget` is host-owned since the SDK can't see the Lambda ceiling — plugin enforces `PendingHorizon < Window` and documents the stronger invariant in XML doc.
