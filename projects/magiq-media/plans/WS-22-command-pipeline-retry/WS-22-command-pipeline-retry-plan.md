---
id: MM-014
type: plan
project: magiq-media
workstream: WS-22-command-pipeline-retry
repo: mgq-dotnet-platform
tags: [mgq-dotnet-platform, sdk, concurrency, middleware]
consumes: []
blocked-by-external: []
status: done
branches: [feature/ws-22-command-pipeline-retry]
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-22 (no gap file; row-tracked); no separate review document.
---

# WS-22 — Command-pipeline retry on `EventConcurrencyException`

**Target repo:** `mgq-dotnet-platform` — `D:\source\github\sprbrk-standard\mgq-dotnet-platform`
**Depends on:** none
**Pairs with:** MM-007 (WS-13 — `AggregateAlreadyExistsException` MUST NOT be retried)

Spec: command dispatcher retries up to 3× with backoff on optimistic-concurrency conflict. Today nothing retries; conflict surfaces unhandled.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-dotnet-platform`. Paste:

> Picking up WS-22 (plan MM-014). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-22-command-pipeline-retry\WS-22-command-pipeline-retry-plan.md`.
>
> Add `CommandRetryMiddleware` to default command-dispatcher chain. Retry 3× on `EventConcurrencyException` with exponential backoff (base 25ms, cap 200ms + jitter). Do NOT retry `AggregateAlreadyExistsException` (WS-13 / MM-007 contract) or `DomainException`.
>
> PR to `mgq-dotnet-platform/main`.

## Phase 0 — Scope confirmation
- [x] ~~Read `docs/spec/shared/consistency-model.md` + `event-store-and-messaging.md` on retry contract~~ — confirmed single-aggregate no-precondition row: 3× exp backoff; precondition commands answer 412 via a different exception
- [x] ~~Locate `ICommandDispatcher` + `ICommandMiddleware` chain~~ — `Magiq.Platform.WriteModel.Application` / `CommandPipelineFactory.Create` wraps middleware around a terminal closed over the command
- [x] ~~Confirm no retry middleware exists today~~

## Phase 1 — `CommandRetryMiddleware`
- [x] ~~Retry 3× on `EventConcurrencyException` (base 25ms, cap 200ms + jitter)~~ — full jitter in [0, delay); shift clamped to [0, 30] against misconfigured MaxAttempts
- [x] ~~Do NOT retry `AggregateAlreadyExistsException` (WS-13 / MM-007 contract)~~ — allowlist catches `EventConcurrencyException` only; distinct types bubble unchanged
- [x] ~~Do NOT retry `DomainException`~~
- [x] ~~After 3 failed attempts: rethrow last `EventConcurrencyException`~~ — rethrows the exception that failed on the final attempt

## Phase 2 — Registration + ordering
- [x] ~~Register in default chain before command handler, after validation/authorization~~ — `UseCommandRetry` adds the middleware innermost; call it last among `UseCommandMiddleware<T>` so retry wraps handler + append only
- [x] ~~Options: `CommandRetryOptions.MaxAttempts`, `.BaseDelay`, `.MaxDelay`~~ — bound via `AddOptions<CommandRetryOptions>()`

## Phase 3 — Instrumentation
- [x] ~~Retry-attempt counter with `command_type`, `attempt` dimensions~~ — `attempt` dimension only; `command.type` dropped because `ICommandHandlingContext` does not know the command type and the context class name would collapse every dispatch to one value. Correlation lives on the dispatcher's log scope; a proper command dimension can land with WS-58 (MM-080) once the dispatcher gains an Activity scope.
- [x] ~~Exhausted-retries counter~~ — `magiq.event_sourcing.command.retry.exhausted`

## Phase 4 — Tests
- [x] ~~Unit: single conflict → retry succeeds on attempt 2~~
- [x] ~~Unit: 3 consecutive conflicts → rethrows after attempt 3~~ — same `EventConcurrencyException` instance surfaces to caller; exhausted counter fires once
- [x] ~~Unit: `AggregateAlreadyExistsException` → no retry~~ — stand-in `InvalidOperationException` (type doesn't exist yet) exercises the allowlist
- [x] ~~Unit: `DomainException` → no retry~~
- [x] ~~(bonus) cancellation during retry → `OperationCanceledException` propagates, loop stops~~

## Phase 5 — Package + ship
- [x] ~~Bump `Magiq.Platform.*` version~~ — deferred until the dependency-gap plans are done (same policy as MM-013/WS-23); PR description notes `EventConcurrencyException` moved to Abstractions
- [x] ~~PR to `mgq-dotnet-platform/main`~~ — PR [#30](https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/30), merge sha `72105dad`

## Phase 6 — Close
- [x] ~~platform-capabilities/INDEX.md: WS-22 → § Shipped~~

## Session log
- 2026-10-08: plan drafted
- 2026-10-08: activated as the next SDK plan after MM-013 (WS-23) shipped. Same repo (`mgq-dotnet-platform`), Level 0 Phase A, pairs with MM-007 (WS-13) on the don't-retry contract.
- 2026-10-08: implemented, reviewed and merged. Branch `feature/ws-22-command-pipeline-retry` → PR [#30](https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/30) merged into `mgq-dotnet-platform/main` as `72105dad` (commits `463595e6` + review-fix `b4b38b86`). `EventConcurrencyException` relocated to `Magiq.Platform.EventSourcing.Abstractions` (namespace unchanged) so middleware outside the DynamoDB implementation can reference the contract type. Review surfaced that `ICommandHandlingContext` does not know the command type — `command.type` tag dropped from the retry counters; correlation lives on the dispatcher's log scope and can be re-added via Activity scope under WS-58 (MM-080). Breaking change for out-of-repo consumers; no package bump yet. 95 non-Docker unit tests pass locally including 5 in `CommandRetryMiddlewareTests.cs`.

## Closing card comment

- Branch: `feature/ws-22-command-pipeline-retry` (mgq-dotnet-platform)
- PR: [#30](https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/30) — merged 2026-10-08
- Commits on `main`: implementation `463595e6`, review follow-up `b4b38b86`, merge `72105dad`
- Residue: `command.type` dimension deferred to WS-58 (MM-080) — needs an Activity scope on `CommandDispatcher` first
- Package bump: deferred until the dependency-gap plans are done
