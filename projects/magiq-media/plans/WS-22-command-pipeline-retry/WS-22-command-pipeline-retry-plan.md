---
id: MM-014
type: plan
project: magiq-media
workstream: WS-22-command-pipeline-retry
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, concurrency, middleware]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-22 (no gap file; row-tracked); no separate review document.
---

# WS-22 — Command-pipeline retry on `EventConcurrencyException`

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Pairs with:** MM-007 (WS-13 — `AggregateAlreadyExistsException` MUST NOT be retried)

Spec: command dispatcher retries up to 3× with backoff on optimistic-concurrency conflict. Today nothing retries; conflict surfaces unhandled.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-22 (plan MM-014). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-22-command-pipeline-retry\WS-22-command-pipeline-retry-plan.md`.
>
> Add `CommandRetryMiddleware` to default command-dispatcher chain. Retry 3× on `EventConcurrencyException` with exponential backoff (base 25ms, cap 200ms + jitter). Do NOT retry `AggregateAlreadyExistsException` (WS-13 / MM-007 contract) or `DomainException`.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/shared/consistency-model.md` + `event-store-and-messaging.md` on retry contract
- [ ] Locate `ICommandDispatcher` + `ICommandMiddleware` chain
- [ ] Confirm no retry middleware exists today

## Phase 1 — `CommandRetryMiddleware`
- [ ] Retry 3× on `EventConcurrencyException` (base 25ms, cap 200ms + jitter)
- [ ] Do NOT retry `AggregateAlreadyExistsException` (WS-13 / MM-007 contract)
- [ ] Do NOT retry `DomainException`
- [ ] After 3 failed attempts: rethrow last `EventConcurrencyException`

## Phase 2 — Registration + ordering
- [ ] Register in default chain before command handler, after validation/authorization
- [ ] Options: `CommandRetryOptions.MaxAttempts`, `.BaseDelay`, `.MaxDelay`

## Phase 3 — Instrumentation
- [ ] Retry-attempt counter with `command_type`, `attempt` dimensions
- [ ] Exhausted-retries counter

## Phase 4 — Tests
- [ ] Unit: single conflict → retry succeeds on attempt 2
- [ ] Unit: 3 consecutive conflicts → rethrows after attempt 3
- [ ] Unit: `AggregateAlreadyExistsException` → no retry
- [ ] Unit: `DomainException` → no retry

## Phase 5 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 6 — Close
- [ ] platform-capabilities/INDEX.md: WS-22 → § Shipped

## Session log
- 2026-10-08: plan drafted
