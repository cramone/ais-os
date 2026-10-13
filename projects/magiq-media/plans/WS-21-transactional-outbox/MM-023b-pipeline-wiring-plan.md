---
id: MM-023b
type: plan
project: magiq-media
workstream: WS-21b-transactional-outbox-pipeline-wiring
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, outbox, pipeline, middleware]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-023b-WS-21b-outbox-pipeline-wiring]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/43
merge-sha: 8da1d997
shipped: 2026-10-12
created: 2026-10-12
depends-on: MM-023a (SDK primitive)
split-from: WS-21 — parent split 2026-10-12
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-21b (row-tracked); no separate review document.
---

# WS-21b — Transactional outbox pipeline wiring

**Target repo:** `aspnetcore-platform`
**Depends on:** MM-023a (shipped primitive)
**Unblocks:** MM-023d (relay Lambda) only in combination with MM-023c, downstream MM-028/MM-029/MM-069 unblocked once c+d ship

## Scope

Rewire command dispatch so that a command's event-store writes + outbox entries land in **one** `TransactWriteItems`. Currently (post-MM-023a):

- Primitive exists — `txn.CommitAsync` runs the atomic write.
- Handler still calls `repository.SaveAsync` which commits its own txn, then after-the-fact `OutboxPublishingMiddleware` enqueues separately. Not atomic.

Required change:
- New `TransactionalOutboxMiddleware` (built-in or configurable) opens an `IEventStoreTransaction` early in the pipeline, puts it on `ICommandExecutionContext` (or a scoped `IEventStoreTransactionAccessor`).
- `EventStoreRepository.SaveAsync` resolves ambient txn and calls `eventStore.SaveAsync(agg, txn)` — no commit.
- `OutboxPublishingMiddleware` (becomes `TransactionalOutboxDispatchMiddleware`) also appends to the ambient txn.
- Middleware commits after both complete; rollback on exception.
- `ICommandExecutionContext.RecordEvents` moves to **after** commit (events only logically "exist" post-commit).

Open design questions (resolve in Phase 0):
- Where does the ambient txn live? Scoped service vs AsyncLocal vs explicit parameter.
- Compatibility: commands outside a pipeline (sagas calling repo directly, admin tooling) must still work — need either a null-txn fallback or an explicit `IEventStore.SaveAsync(agg)` path.
- Multi-aggregate `SaveAsync(aggregates)` — ambient txn pattern must support batch too.

## Phases
- Phase 0: nail the ambient-txn carrier, confirm callsites tolerant to the ordering change
- Phase 1: `IEventStoreTransactionAccessor` (scoped) + `TransactionalOutboxMiddleware`
- Phase 2: `EventStoreRepository.SaveAsync` → ambient-txn path
- Phase 3: rewrite `OutboxPublishingMiddleware` → ambient-txn append
- Phase 4: `ICommandExecutionContext.RecordEvents` after commit
- Phase 5: tests (atomic failure both-rows / neither; saga outside pipeline still works)
- Phase 6: PR

## Session log
- 2026-10-12: drafted after MM-023 split.
- 2026-10-12: shipped. PR #43 merged as `8da1d997`.
  - **Delivered**: `IEventStoreTransactionAccessor` (scoped) + default internal `EventStoreTransactionAccessor`. `TransactionalOutboxCommandMiddleware` opens txn, publishes on accessor, awaits handler, peeks `ICommandExecutionContext`, maps via `IDomainEventMapper<T>`, builds `LogicalMessage[]` with fresh ids, enqueues via new `IOutbox.EnqueueAsync(msgs, txn)` overload, commits, drains + runs `IDomainEventProcessor.ProcessAsync`. Rollback on any failure (handler/mapping/enqueue/commit): dispose txn, drain context (prevents retried command re-emitting). Nested invoke reuses outer txn. `EventStoreRepository.SaveAsync` single + batch routes through ambient txn when accessor exposes one, else self-commits. `IntegrationEventPublishingMiddleware` ambient-txn-aware (no-op when txn present → no double-publish). `IWriteModelBuilder.UseTransactionalOutbox()` registers accessor + middleware.
  - **Design decisions**: (1) Peek-not-drain pre-commit so local handlers see events post-commit. (2) Rollback = "nothing durable yet" — DynamoDB TransactWriteItems is write-all-or-write-none; dispose + context clear is sufficient. (3) Nested handling preserves atomicity across saga-driven handler composition. (4) `IOutbox.EnqueueAsync(txn)` chosen over `IMessageBus.PublishAsync(txn)` to keep `Messaging.Abstractions` free of event-sourcing types.
  - **11 unit tests pass** (`TransactionalOutboxCommandMiddlewareTests` + `EventStoreRepositoryAmbientTxnTests`): happy path (open → enlist → map → enqueue → commit → drain), handler-throws, commit-throws, no-events, events-but-no-mapper, nested-reuse, publishing-middleware no-op + fallback, repo ambient-txn path, repo self-commit path, repo null-accessor path.
  - **204/204 non-integration suite green**.
  - **Interface break**: `ICommandExecutionContext` gained `PeekPendingEvents()`; `IOutbox` gained `EnqueueAsync(msgs, txn, ct)`. In-repo test fake `InMemoryDomainEventPublisher` updated. Out-of-repo implementers must add both.
  - **Project refs added**: `WriteModel.Application → EventSourcing.Abstractions`; `WriteModel.Application → Messaging.Outbox.Abstractions`.
  - **Trackers updated**: platform-capabilities/INDEX.md WS-21b moved to Shipped, WS-21c flipped `open` → `ready`. INTEGRATION-BACKLOG MM-023b moved to § Shipped, MM-023c flipped `new` → `ready`. Readiness 61 new / 11 ready / 16 shipped.
  - **Deferred to child plans**: MM-023c (table split, now ready), MM-023d (relay Lambda), MM-023e (metrics).
