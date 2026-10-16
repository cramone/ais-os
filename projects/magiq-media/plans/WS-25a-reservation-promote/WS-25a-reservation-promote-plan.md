---
id: MM-028
type: plan
project: magiq-media
workstream: WS-25a-reservation-promote
repo: mgq-dotnet-platform
tags: [mgq-dotnet-platform, sdk, name-reservation, transaction]
consumes: []
blocked-by-external: [MM-023]
status: shipped
branches: [feature/chase/MM-028-WS-25a-reservation-promote]
pr: https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/46
merge-sha: e2d1ca06
shipped: 2026-10-12
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-25 (no gap file; row-tracked); no separate review document.
---

# WS-25a — `PromoteAsync` on `INameReservationService`

**Target repo:** `mgq-dotnet-platform` — `D:\source\github\sprbrk-standard\mgq-dotnet-platform`
**Depends on:** MM-023 (WS-21 — outbox / transaction handle)
**Unblocks:** MM-042 (WS-25b — magiq-media command middleware calls PromoteAsync)

Promotion rides on same `TransactWriteItems` txn as event-store append. Today pipeline skips promotion; everything stays `PENDING`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-dotnet-platform`. Confirm MM-023 (WS-21) shipped. Paste:

> Picking up WS-25a (plan MM-028). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-25a-reservation-promote\WS-25a-reservation-promote-plan.md`.
>
> Depends on WS-21 (MM-023) shipped — needs `IEventStoreTransaction`. Add `INameReservationService.PromoteAsync(tokens, txn, ct)` — each token → `UpdateItem` with `ConditionExpression: State = :pending`. Appends to txn so TransactWriteItems commits atomically with event-store append. `ApplyAsync` returns `ReservationApplyToken { ScopeKey, Name, AggregateId }`. Conditional-check-failed on promote → `ReservationPromotionFailedException`.
>
> PR to `mgq-dotnet-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/shared/consistency-model.md` § Name reservation two-phase
- [ ] Confirm MM-023 (WS-21) shipped (`IEventStoreTransaction` available)
- [ ] Locate `INameReservationService` + current `ApplyAsync` path

## Phase 1 — `PromoteAsync` on service
- [ ] `Task PromoteAsync(IReadOnlyList<ReservationApplyToken> tokens, IEventStoreTransaction txn, CancellationToken ct)`
- [ ] Each token → `UpdateItem` with `ConditionExpression: State = :pending`, `Set State = :claimed`
- [ ] Appends to `txn.Items` so `TransactWriteItems` commits atomically

## Phase 2 — `ApplyAsync` returns token
- [ ] Returns `ReservationApplyToken { ScopeKey, Name, AggregateId }`
- [ ] Token also carries `State = Pending` at return

## Phase 3 — Promotion failure semantics
- [ ] Conditional-check-failed on promote → `ReservationPromotionFailedException`
- [ ] Txn-wide rollback (all-or-nothing TransactWriteItems)

## Phase 4 — Tests
- [ ] Unit: `ApplyAsync` + `PromoteAsync` in one txn → both commit
- [ ] Unit: event-store append fails → promote rolls back → reservation stays `Pending`
- [ ] Unit: concurrent conflicting promote → `ReservationPromotionFailedException`

## Phase 5 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `mgq-dotnet-platform/main`

## Phase 6 — Close
- [ ] platform-capabilities/INDEX.md: WS-25 split — `WS-25a shipped`, `WS-25b open`
- [ ] INTEGRATION-BACKLOG: MM-042 (WS-25b) ready

## Session log
- 2026-10-08: plan drafted (blocked on MM-023 ship)
- 2026-10-12: shipped on branch `feature/chase/MM-028-WS-25a-reservation-promote`.
  - New types in `Magiq.Platform.UniquenessRegistry.Abstractions`: `ReservationState` (Pending/Claimed), `ReservationApplyToken(TenantId, ScopeKey, Name, AggregateId)`, `ReservationPromotionFailedException(Token)`.
  - `INameReservationService.ApplyAsync` return type → `Task<IReadOnlyList<ReservationApplyToken>>`. Reserve / BulkReserve / BulkReserveAcrossScopes emit one token per newly staked row written `State = PENDING`; swap / move / release emit none (nothing to promote). Same-owner idempotent retries emit no tokens — the existing row's state is left untouched.
  - New `INameReservationService.PromoteAsync(IReadOnlyList<ReservationApplyToken>, IEventStoreTransaction, CancellationToken)` enlists one conditional `UpdateItem` per token on the shared transaction. DynamoDb path writes `SET #state = :claimed` with `ConditionExpression: #state = :pending`; the update rides the same `TransactWriteItems` as the event-store append so promote succeeds iff the event-store commit does. Condition failure surfaces as `ReservationPromotionFailedException`; rollback leaves the row in Pending for later reaper cleanup. In-memory path enlists an equivalent flip callback on `InMemoryEventStoreTransaction`.
  - `DynamoDbEventStoreTransaction` gained `AddConditionalWriteItem(TransactWriteItem, string description, Func<Exception, Exception> translateConditionalFailure)` + `CustomConditionContext` record so collaborators outside `Magiq.Platform.EventSourcing.DynamoDb` can wire their own exception translator without inverting the dependency. Single-item commit path now handles `Update` items alongside `Put` (so a promote-only commit works).
  - 6 new unit tests under `tests/Magiq.AspNetCore.Tests/UniquenessRegistry/ReservationPromoteTests.cs` cover: committed-promote-flips-row (second promote on same tokens fails — row is Claimed), dispose-without-commit-stays-pending, concurrent-promote-second-commit-fails, bulk-reserve-emits-one-token-per-entry, release-emits-no-tokens, empty-token-list-promote-is-no-op. 25 UniquenessRegistry tests + 174 non-Docker regression tests pass. Pre-existing failures (`Magiq.Platform.Tenants.Abstractions → AspNetCore` arch violation, Docker-dependent integration fixtures) unchanged by this PR.
  - `tests/Magiq.AspNetCore.Tests.csproj` gained `Magiq.Platform.UniquenessRegistry.Stores.InMemory` ref. `InMemoryNameReservationStore` promoted internal → public to match the DynamoDb store (now instantiable by tests without DI). Version prefix bumped 1.1.3.6 → 1.1.3.7 in `build/Magiq.AspNetCore.Commons.props` (merge may have reset).
- 2026-10-12: PR #46 merged to `mgq-dotnet-platform/main` as `e2d1ca06`. Tower MM-028 (WS-25a) flipped `new` → `done`; MM-042 (WS-25b) tagged `ready` — the SDK primitive is now in place for the magiq-media middleware wiring. The plan's referenced docs — `docs/dependency-gaps/platform-capabilities/INDEX.md` and `INTEGRATION-BACKLOG` — were not located in the current snapshot, so closure was recorded in Tower only.
