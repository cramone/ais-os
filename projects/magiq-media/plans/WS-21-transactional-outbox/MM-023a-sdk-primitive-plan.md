---
id: MM-023a
type: plan
project: magiq-media
workstream: WS-21a-transactional-outbox-sdk-primitive
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, outbox, dynamodb, messaging, transaction]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-023-WS-21-transactional-outbox]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/42
merge-sha: d973466c
shipped: 2026-10-12
created: 2026-10-08
split-from: WS-21 (previously single MM-023 plan)
split-children: [MM-023b (pipeline wiring), MM-023c (outbox table split), MM-023d (relay Lambda — cdk-magiq-media), MM-023e (metrics — dep WS-58)]
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-21a (row-tracked, no gap file); no separate review document.
---

# WS-21a — Transactional outbox SDK primitive

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-023b, MM-023c, MM-023d, MM-023e
**Downstream (post-full WS-21 chain):** MM-028 (WS-25a PromoteAsync), MM-029 (WS-18 F008 claim-check), MM-069 (WS-35 membership indexes) — only released once MM-023b+c+d ship

## Scope

Narrow SDK ship. The full "transactional outbox" delivery was one plan (old MM-023) covering: SDK primitive, pipeline wiring, outbox-table split, relay Lambda, instrumentation. User authorised split 2026-10-12 to keep PR blast radius bounded. This plan ships **primitive only**:

- `IEventStoreTransaction` abstraction + `DynamoDbEventStoreTransaction` concrete
- `IEventStore.BeginTransaction()` + `SaveAsync(agg, txn, ct)` overload
- `IOutboxStore.EnqueueAsync(msgs, txn, ct)` overload
- `CommitAsync` runs one `TransactWriteItems`; translates per-item cancellation reasons to `AggregateAlreadyExistsException` / `EventConcurrencyException`
- In-memory impl keeps feature parity
- Existing `SaveAsync(agg)` / `EnqueueAsync(msgs)` self-committing paths preserved (backward-compat)
- Unit tests covering: atomic failure, no-events no-op, concurrency conflict preserved, caller-dup id preserved, outbox-only path

**Deliberately out of scope** (tracked by child plans):

| Child | Covers |
|---|---|
| MM-023b | `TransactionalOutboxMiddleware` + `EventStoreRepository` rewire so command pipeline opens the txn, handler saves (uncommitted), outbox middleware enqueues, commit happens last. Also `ICommandExecutionContext.RecordEvents` ordering adjustment |
| MM-023c | Outbox-table split (`outbox-pending` + `outbox-dead`), GSI changes, migration guidance |
| MM-023d | Outbox relay Lambda (cdk-magiq-media) — DynamoDB Streams or scheduled scan, SNS publish, 10-attempt bounded retry, `OutboxEntryParked` metric |
| MM-023e | Publish-failure counter + outbox-depth gauge (depends on WS-58 metrics pipeline decision) |

## Session invocation

> Picking up WS-21a (plan MM-023a). SDK primitive only — `IEventStoreTransaction` + `SaveAsync(agg, txn)` + `EnqueueAsync(msgs, txn)`. Pipeline wiring + relay + table split deferred to MM-023b/c/d/e.

## Phase 0 — Scope confirmation (done)
- [x] Read spec § Transactional Outbox
- [x] Locate `IOutboxStore.EnqueueAsync`, `DynamoDbEventStore.SaveAsync`, `InMemoryOutboxStore`
- [x] Confirm current flow: separate PutItem/TransactWriteItem per store; no shared txn

## Phase 1 — Transaction handle (SDK)
- [ ] `IEventStoreTransaction : IAsyncDisposable` in `Magiq.Platform.EventSourcing.Abstractions`
- [ ] `IEventStore.BeginTransaction()` returns `IEventStoreTransaction`
- [ ] `DynamoDbEventStoreTransaction` concrete class (public, in `Magiq.Platform.EventSourcing.DynamoDb`) with per-item context (`EventRowContext` / `OutboxContext` / `GenericContext`) + `AddWriteItem`
- [ ] `InMemoryEventStoreTransaction` collects pending commits as callbacks; executes on CommitAsync

## Phase 2 — EventStore SaveAsync overload
- [ ] `IEventStore.SaveAsync<T>(T aggregate, IEventStoreTransaction txn, CancellationToken ct = default)` default-interface-method (defaults to self-commit for impls that don't override)
- [ ] `DynamoDbEventStore.SaveAsync(agg, txn, ct)` builds the event-row Put, calls `txn.AddEventRowPut(...)` with context carrying base version + event count
- [ ] Backward-compat: existing `SaveAsync(agg, ct)` creates internal txn, calls overload, commits — logic path identical to today's PutItem

## Phase 3 — OutboxStore EnqueueAsync overload
- [ ] `IOutboxStore.EnqueueAsync(IReadOnlyCollection<OutboxLogicalMessage>, IEventStoreTransaction, CancellationToken)` default-interface-method
- [ ] `DynamoDbOutboxStore` override: calls `txn.AddOutboxPut(TransactWriteItem)`
- [ ] `InMemoryOutboxStore` override: registers callback that executes current `EnqueueAsync` on commit

## Phase 4 — Commit semantics
- [ ] `DynamoDbEventStoreTransaction.CommitAsync`: if 1 item → single PutItem (preserves current single-aggregate behaviour); if 2+ → TransactWriteItems
- [ ] On `ConditionalCheckFailedException` (single-item path): translate using the single item's context — same mapping as `DynamoDbEventStore.SaveAsync` today
- [ ] On `TransactionCanceledException` (multi-item path): walk `CancellationReasons`, map per index via item context — AggregateAlreadyExists / EventConcurrency surface correctly
- [ ] Idempotent commit: throws if already committed; disposable without commit is a rollback (no-op on DynamoDB; items simply never written)

## Phase 5 — Tests
- [ ] `IEventStoreTransaction` single-event-row commit = PutItem semantics
- [ ] Two aggregates + outbox msgs = one TransactWriteItems
- [ ] Mid-stream concurrency conflict in multi-item txn → `EventConcurrencyException` with the right offender
- [ ] Caller-dup id in multi-item txn → `AggregateAlreadyExistsException`
- [ ] Outbox-only (no event rows) commit succeeds
- [ ] No uncommitted events (`HasChanges == false`) → txn no-op
- [ ] Double-commit throws
- [ ] In-memory parity

## Phase 6 — Build + regression
- [ ] `dotnet build` solution
- [ ] `dotnet test` — fix any test stub impls of `IEventStore` / `IOutboxStore` that break on default-interface-method mismatch
- [ ] 92 all-WS regression suite green

## Phase 7 — PR
- [ ] PR to `aspnetcore-platform/main`
- [ ] Body explicitly lists MM-023b/c/d/e as deferred follow-ups
- [ ] No version bump — batched per prior policy

## Phase 8 — Close
- [ ] platform-capabilities/INDEX.md: WS-21 row split; WS-21a → shipped row, WS-21b/c/d/e → open rows
- [ ] INTEGRATION-BACKLOG: MM-023 row replaced with MM-023a (shipped) + MM-023b/c/d/e (new rows, deps chained)
- [ ] magiq-media CLAUDE.md "Transactional outbox not deliverable" bullet rewritten to narrower residual (keeps citing child-plan ids)
- [ ] Tower todo: MM-023 entry renamed to MM-023a, child todos created for MM-023b/c/d/e
- [ ] Session log entries

## Session log
- 2026-10-08: parent plan drafted
- 2026-10-12: scope split authorised. Parent MM-023 → MM-023a (this plan). MM-023b/c/d/e drafted as child plans. Child dependency chain documented so follow-ups cannot be lost.
- 2026-10-12: shipped. PR #42 merged as `d973466c`.
  - **Delivered**: `IEventStoreTransaction` (opaque, `IAsyncDisposable`, `CommitAsync`). `DynamoDbEventStoreTransaction` concrete with single-item PutItem fast path + multi-item TransactWriteItems; per-item `ItemContext` (event-row / outbox / generic) maps `ConditionalCheckFailed` → `AggregateAlreadyExistsException` vs `EventConcurrencyException`; `CancellationReasons` walk picks caller-dup over mid-stream in mixed batch. `IEventStore.BeginTransaction()` + `SaveAsync(agg, txn)`. `IOutboxStore.EnqueueAsync(msgs, txn)` on DynamoDb + InMemory. `InMemoryEventStoreTransaction` with callback enlistment. `TrackResource` holds payload-stream disposables through commit.
  - **12 unit tests pass** (`TransactionalOutboxTests`): single-item PutItem fast path, caller-dup → AggregateAlreadyExists, mid-stream → EventConcurrency, multi-item mixed-batch mapping, outbox-only commit, empty commit no-op, double-commit throws, no-events skipped, in-memory parity apply + dispose-rollback, foreign-handle rejection.
  - **218/218 non-integration suite green**. 17 Rotation + S3 failures pre-existing (Docker/AWS), unchanged.
  - **Project refs added**: `Messaging.Outbox.Abstractions → EventSourcing.Abstractions`; `Messaging.Outbox → EventSourcing`; `Messaging.Outbox.DynamoDb → EventSourcing.DynamoDb`; test csproj refs outbox packages.
  - **Interface break**: `IEventStore` gained `BeginTransaction` + `SaveAsync(agg, txn)`; `IOutboxStore` gained `EnqueueAsync(msgs, txn)`. 3 test fakes updated (one NotSupported stub + two decorator stubs delegating to inner).
  - **Trackers updated**: platform-capabilities/INDEX.md WS-21a row moved to Shipped; WS-21b flipped `open` → `ready`. INTEGRATION-BACKLOG MM-023a moved to § Shipped; MM-023b flipped `new` → `ready`. Readiness summary 61 new / 11 ready / 15 shipped.
  - **Deferred to child plans** (visible on five surfaces so cannot be forgotten): MM-023b pipeline wiring, MM-023c outbox table split, MM-023d relay Lambda (cdk-magiq-media), MM-023e metrics (dep WS-58).
