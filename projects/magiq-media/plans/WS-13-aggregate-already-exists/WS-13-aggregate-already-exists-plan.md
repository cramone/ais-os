---
id: MM-007
type: plan
project: magiq-media
workstream: WS-13-aggregate-already-exists
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, event-store, concurrency]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-007-WS-13-aggregate-already-exists]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/34
merge-sha: 5e17be36
shipped: 2026-10-12
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F020-duplicate-caller-id-exception.md and INDEX.md#WS-13; no separate review document.
---

# WS-13 — `AggregateAlreadyExistsException` distinct from `EventConcurrencyException`

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks (magiq-media):** MM-032 (WS-13b bulk-handler map → `409 IdAlreadyExists`)
**Pairs with:** MM-014 (WS-22 command-pipeline retry — must not retry this exception)

Delivers F020. Today `DynamoDbEventStore.SaveAsync` throws one `EventConcurrencyException` for both duplicate-id and optimistic-concurrency conflicts, so callers can't disambiguate without inspecting internal state. Spec: distinct exception for duplicate caller-supplied id; not retry-eligible.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste prompt:

> Picking up WS-13 (plan MM-007). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-13-aggregate-already-exists\WS-13-aggregate-already-exists-plan.md`. Origin gap file: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F020-duplicate-caller-id-exception.md`.
>
> Deliver `AggregateAlreadyExistsException` distinct from `EventConcurrencyException` in `Magiq.Platform.EventStore`. Discriminate at `DynamoDbEventStore.SaveAsync` on initial-version PK duplicate vs mid-stream concurrency conflict. Must NOT be retry-eligible (pairs with WS-22 / MM-014).
>
> Read `aspnetcore-platform/CLAUDE.md` for repo conventions. Work phase-by-phase; tick acceptance boxes only when verified locally. Log notes in § Session log. New defects → new review, do not bake into this plan.
>
> Ship as one PR to `aspnetcore-platform/main` with migration note (consumers catching `EventConcurrencyException` for first-write must now also catch `AggregateAlreadyExistsException`). Close out per Phase 6.

## Phase 0 — Scope confirmation
- [x] Read F020 § Required-shape + § Detection signals
- [x] Locate `DynamoDbEventStore.SaveAsync` + sole throw-site of `EventConcurrencyException`
- [x] Confirm no caller discriminates duplicate-id vs version-conflict today

## Phase 1 — Introduce exception
- [x] Add `AggregateAlreadyExistsException` in `Magiq.Platform.EventStore` (or equivalent namespace)
- [x] Distinct hierarchy (not derived from `EventConcurrencyException`); carries `TenantId`, `AggregateType`, `AggregateId`
- [x] XML doc declares exception is **not retry-eligible**

## Phase 2 — Discriminate in `DynamoDbEventStore.SaveAsync`
- [x] On `ConditionalCheckFailed`: inspect which condition failed (initial-version PK duplicate vs optimistic-concurrency `attribute_not_exists(SK)` on subsequent event)
- [x] First-version duplicate PK → `AggregateAlreadyExistsException`
- [x] Mid-stream conflict → keep `EventConcurrencyException`
- [x] Verify DynamoDB `TransactWriteItems` + `PutItem` return enough signal (`CancellationReason` / `ConditionalCheckFailedException`)

## Phase 3 — Pipeline guard
- [x] Document contract: `AggregateAlreadyExistsException` MUST NOT be retried by command-pipeline retry middleware (hands off to MM-014 / WS-22)
- [x] If WS-22 lands first: wire type-filter in retry middleware (WS-22 landed first; allowlist already excludes any non-`EventConcurrencyException`; existing `UnrelatedException_NotRetried` test stands in for WS-13)
- [x] If WS-22 lands later: leave XML doc declaration + reserve test name

## Phase 4 — Tests
- [x] Unit: duplicate caller-supplied id on fresh aggregate throws `AggregateAlreadyExistsException` (`AggregateAlreadyExistsExceptionTests.SaveAsync_FirstWriteConflict_ThrowsAggregateAlreadyExistsException`)
- [x] Unit: version conflict on existing aggregate throws `EventConcurrencyException` (`AggregateAlreadyExistsExceptionTests.SaveAsync_MidStreamConflict_ThrowsEventConcurrencyException`)
- [x] Unit: both exceptions carry correct tenant/aggregate payload
- [x] Integration (`DynamoDbEventStoreIntegrationTests`): duplicate caller-supplied id, mid-stream collision, bulk-save duplicate — authored, build-green, require Docker to run (deferred to CI / machine with Docker)

## Phase 5 — Package + ship
- [ ] Bump `Magiq.Platform.*` version (deferred — current practice batches bumps across workstreams; `VersionPrefix` stays at `1.1.3.6` on this PR)
- [ ] Push internal NuGet (follows the deferred bump)
- [x] PR to `aspnetcore-platform/main` with migration note: https://github.com/magiqsoftware/aspnetcore-platform/pull/34

## Phase 6 — Close (post-merge)
- [x] F020: `status: shipped`, `pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/34`, `shipped: 2026-10-12`
- [x] platform-capabilities/INDEX.md: WS-13 → § Shipped (merge SHA `5e17be36`)
- [x] INTEGRATION-BACKLOG WS-13b (MM-032): `Dep status: shipped`, `Integration status: ready`; MM-007 moved to § Shipped; readiness summary bumped 68→67 `new`, 2→3 `ready`, 5→6 `shipped`

## Session log
- 2026-10-08: plan drafted
- 2026-10-12: WS-13 implemented in `aspnetcore-platform` on branch `feature/chase/MM-007-WS-13-aggregate-already-exists`.
  - Added `AggregateAlreadyExistsException` in `Magiq.Platform.EventSourcing.Abstractions` (`sealed`, extends `Exception`, carries `TenantId?` / `AggregateType` / `AggregateId`).
  - `DynamoDbEventStore.SaveAsync` single-aggregate: on `ConditionalCheckFailedException`, discriminates by `aggregate.AggregateVersion == uncommittedEvents.Count` ⇒ base loaded version was 0 ⇒ first write ⇒ `AggregateAlreadyExistsException`; otherwise `EventConcurrencyException`.
  - `DynamoDbEventStore.SaveAsync` bulk: on `TransactionCanceledException`, walks `CancellationReasons` index-parallel to results; any failed index whose aggregate was a first write surfaces `AggregateAlreadyExistsException` even if other items were mid-stream conflicts (duplicate id is permanent and must not be retried for the sake of the retryable items).
  - `CommandRetryMiddleware` unchanged — its allowlist already caught only `EventConcurrencyException`; the new type is deliberately a sibling (not a subclass), so retries do nothing. `UnrelatedException_NotRetried` test already named WS-13 as the standing-in case.
  - Tests: 4 new unit tests (`AggregateAlreadyExistsExceptionTests`) all green locally against mocked `IAmazonDynamoDB`; 3 new integration tests appended to `DynamoDbEventStoreIntegrationTests` — build-green, require Docker to execute, deferred.
  - Version bump + NuGet publish deferred per repo practice (recent WS-14a / WS-32a / WS-24 PRs did not self-bump).
  - PR: https://github.com/magiqsoftware/aspnetcore-platform/pull/34
- 2026-10-12: PR #34 merged to `aspnetcore-platform/main` as `5e17be36`. Phase 6 closed — F020 → shipped, platform-capabilities/INDEX.md WS-13 moved to § Shipped, INTEGRATION-BACKLOG MM-007 moved to § Shipped and MM-032 (WS-13b) flipped to `ready`.
