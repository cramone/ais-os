---
id: MM-007
type: plan
project: magiq-media
workstream: WS-13-aggregate-already-exists
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, event-store, concurrency]
consumes: []
blocked-by-external: []
status: new
branches: []
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
- [ ] Read F020 § Required-shape + § Detection signals
- [ ] Locate `DynamoDbEventStore.SaveAsync` + sole throw-site of `EventConcurrencyException`
- [ ] Confirm no caller discriminates duplicate-id vs version-conflict today

## Phase 1 — Introduce exception
- [ ] Add `AggregateAlreadyExistsException` in `Magiq.Platform.EventStore` (or equivalent namespace)
- [ ] Distinct hierarchy (not derived from `EventConcurrencyException`); carries `TenantId`, `AggregateType`, `AggregateId`
- [ ] XML doc declares exception is **not retry-eligible**

## Phase 2 — Discriminate in `DynamoDbEventStore.SaveAsync`
- [ ] On `ConditionalCheckFailed`: inspect which condition failed (initial-version PK duplicate vs optimistic-concurrency `attribute_not_exists(SK)` on subsequent event)
- [ ] First-version duplicate PK → `AggregateAlreadyExistsException`
- [ ] Mid-stream conflict → keep `EventConcurrencyException`
- [ ] Verify DynamoDB `TransactWriteItems` + `PutItem` return enough signal (`CancellationReason` / `ConditionalCheckFailedException`)

## Phase 3 — Pipeline guard
- [ ] Document contract: `AggregateAlreadyExistsException` MUST NOT be retried by command-pipeline retry middleware (hands off to MM-014 / WS-22)
- [ ] If WS-22 lands first: wire type-filter in retry middleware
- [ ] If WS-22 lands later: leave XML doc declaration + reserve test name

## Phase 4 — Tests
- [ ] Unit: duplicate caller-supplied id on fresh aggregate throws `AggregateAlreadyExistsException`
- [ ] Unit: version conflict on existing aggregate throws `EventConcurrencyException`
- [ ] Unit: both exceptions carry correct tenant/aggregate payload

## Phase 5 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] Push internal NuGet
- [ ] PR to `aspnetcore-platform/main` with migration note

## Phase 6 — Close
- [ ] F020: `status: shipped`, `pr: <link>`, `shipped: <date>`
- [ ] platform-capabilities/INDEX.md: WS-13 → § Shipped
- [ ] INTEGRATION-BACKLOG WS-13b (MM-032): `Dep status: shipped`, `Integration status: ready`

## Session log
- 2026-10-08: plan drafted
