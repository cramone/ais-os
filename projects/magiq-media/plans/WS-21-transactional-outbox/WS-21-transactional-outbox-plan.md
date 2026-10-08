---
id: MM-023
type: plan
project: magiq-media
workstream: WS-21-transactional-outbox
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, outbox, dynamodb, messaging]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-21 (no gap file; row-tracked); no separate review document.
---

# WS-21 — Transactional outbox SDK

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-028 (WS-25a PromoteAsync), MM-029 (WS-18 F008 claim-check), MM-069 (WS-35 membership indexes)

Spec: events publish via transactional outbox written in same transaction as event-store append. Today events publish inline from command handler after `SaveAsync`; failed SNS loses a committed event.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-21 (plan MM-023). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-21-transactional-outbox\WS-21-transactional-outbox-plan.md`. Reference `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\shared\event-store-and-messaging.md` § Transactional Outbox.
>
> Deliver `IEventStoreTransaction` wrapping `TransactWriteItems`. `IOutboxStore.EnqueueAsync` takes transaction handle. `DynamoDbEventStore.SaveAsync` executes event rows + outbox entries + aggregate-local index puts as one atomic `TransactWriteItems`. Replace `InMemoryOutboxStore` with `DynamoDbOutboxStore`. Outbox relay (Lambda, DynamoDB Streams or scheduled scan) publishes to SNS; on success deletes; dead-letters after N attempts.
>
> Largest SDK workstream — plan on multiple sessions. PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read event-store-and-messaging.md § Transactional Outbox + § Storage Boundaries
- [ ] Locate `IOutboxStore.EnqueueAsync`, `DynamoDbEventStore.SaveAsync`, `InMemoryOutboxStore`
- [ ] Confirm `TransactWriteItems` capacity (25 items) sufficient for single-aggregate commits

## Phase 1 — Transaction handle API
- [ ] `IEventStoreTransaction` abstraction wrapping `List<TransactWriteItem>`
- [ ] `IOutboxStore.EnqueueAsync(outboxEntry, IEventStoreTransaction txn, ct)` appends put to txn
- [ ] `IEventStoreTransaction.CommitAsync(ct)` executes `TransactWriteItems`

## Phase 2 — `DynamoDbEventStore.SaveAsync` as `TransactWriteItems`
- [ ] Single-aggregate save: all event rows + outbox entries + aggregate-local index puts in one `TransactWriteItems`
- [ ] Multi-aggregate save already uses `TransactWriteItems`; extend to accept outbox puts
- [ ] Preserve `attribute_not_exists(SK)` optimistic-concurrency condition on each event row

## Phase 3 — DynamoDB outbox store
- [ ] Replace `InMemoryOutboxStore` with `DynamoDbOutboxStore`
- [ ] Table shape: `outbox-pending` + `outbox-dead`
- [ ] GSI for relay pickup

## Phase 4 — Outbox relay worker
- [ ] Lambda consumer (DynamoDB Streams or scheduled scan)
- [ ] Publishes to SNS; on success deletes outbox row; on failure increments `AttemptCount`
- [ ] Dead-letter after N attempts → `outbox-dead` (WS-18 bounds to 10 with `OutboxEntryParked`)

## Phase 5 — Tests
- [ ] Unit: `SaveAsync` + outbox-enqueue in one txn — atomic on failure
- [ ] Integration: LocalStack DynamoDB `TransactWriteItems` round-trip
- [ ] Chaos: SNS publish failure → outbox retains → relay re-publishes

## Phase 6 — Instrumentation
- [ ] Publish-failure counter (unmasked today — unknown loss rate)
- [ ] Outbox-depth gauge

## Phase 7 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`
- [ ] Migration note: consumers of `IOutboxStore.EnqueueAsync` must pass txn handle

## Phase 8 — Close
- [ ] platform-capabilities/INDEX.md: WS-21 → § Shipped
- [ ] Unblocks MM-028 (WS-25a), MM-029 (WS-18), MM-069 (WS-35) — update INTEGRATION-BACKLOG

## Session log
- 2026-10-08: plan drafted
