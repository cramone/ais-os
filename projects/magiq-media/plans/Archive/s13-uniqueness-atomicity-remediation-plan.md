# S13 — Uniqueness Registry Atomicity & Name-Release Remediation Plan

_magiq-media · Plan for architecture-spec-review finding **S13** ("Reservation + counter non-atomicity; confirm all name-freeing paths release")._
_Author: architecture pass (AI-assisted), for Chase Ramone · Drafted 2026-07-18._
_Status: **DRAFT for review** — nothing implemented yet. Scope confirmed: **full fix including platform**._

> **Companion to** `reviews/architecture-spec-review.md` §S13. This plan supersedes S13's original framing — the investigation (against `D:\source\github\magiq-media`, `D:\source\github\aspnetcore-platform`, `D:\source\github\cdk-magiq-media`) found the review inherited a stale premise from the `catalog-domain-invariants.md` ADR. The corrected problem statement is below.

---

## 1. Executive summary

S13 as written points at "reservation + counter non-atomicity, backstopped by idempotent replay + a negative-counter alarm." Investigation shows three corrections:

1. **The dangerous seam is reservation to event-store, not reservation to counter.** Every name-scoped handler mutates the reservation table *first*, then appends the aggregate event *last*, as two writes to two different tables with no shared transaction. A failure between them orphans a reservation (create), splits reservation/aggregate name state (rename), or frees a name while the aggregate is still live (archive).
2. **The ADR describes a mechanism that was never built.** The `child-folders` / `active-items` counters that `catalog-domain-invariants.md` says gate folder archive do not exist in code (`CounterKeys` defines only `depth` and `active-registrations`). Folder archive is a **cascade** blocked only on active registrations.
3. **Neither stated backstop exists.** `DecrementCounterAsync` is floored (`ConditionExpression "#count >= :amount"`), so a counter **cannot go negative** — the "alarm on negative counters" watches an impossible state, and no such alarm exists in CDK anyway. Idempotent replay is claimed but not implemented: the Tier-1 check is not owner-aware, so a retry returns `AlreadyExists` instead of resuming.

The good news: **name-freeing paths themselves are well covered** (rename to `SwapAsync`, move to `MoveAsync`, archive/deprecate to `ReleaseAsync`, hard-delete gated on `Status==Archived`). The gap is atomicity and self-healing, not missing releases — with two exceptions (inconsistent create-failure compensation; cascade swallows descendant failures).

The fix is a **platform-level transactional write** that appends the aggregate event and the reservation/counter mutations in one `TransactWriteItems`, plus Tier-1 hardening that closes the live holes without waiting on the platform change, plus doc/ops reconciliation.

---

## 2. Evidence (as-built)

### 2.1 Handler pattern — reservation first, event last

All Catalog/Metadata name handlers follow: `IsNameAvailable` (Tier 1) then mutate aggregate then `nameReservation.{Reserve|Swap|Move|Release}` then `repository.SaveAsync` (event append). The reservation write and the event append are **separate DynamoDB writes to separate tables** (`media-name-reservations` vs `media-events`).

| Command | Reservation op | Event append | Compensates on Save failure? |
|---|---|---|---|
| `CreateCollectionHandler` | `ReserveAsync` | `repository.SaveAsync` | **No** |
| `CreateFolderHandler` | `ReserveAsync` + `IncrementCounter(depth)` | `repository.SaveAsync` | **No** |
| `CreateRecordTypeHandler` | `ReserveAsync` | `repository.SaveAsync` | **No** |
| `CreateMediaProfileHandler` | `ReserveAsync` | `repository.SaveAsync` | **Yes** (`ReleaseAsync` in catch) |
| `PublishMediaProfileHandler` (name change) | `SwapAsync` | `repository.SaveAsync` | **Yes** |
| `RenameCollectionHandler` / `RenameFolderHandler` / `UpdateMediaItemTitleHandler` / `RenameRecordTypeHandler` | `SwapAsync` | `repository.SaveAsync` | No |
| `MoveFolderHandler` / `MoveMediaItemHandler` | `MoveAsync` + depth counter loop | `repository.SaveAsync` | No |
| `ArchiveCollectionHandler` / `ArchiveFolderHandler` / `ArchiveMediaItemHandler` | `ReleaseAsync` | `repository.SaveAsync` | No |
| `DeprecateMediaProfileHandler` / `DeprecateRecordTypeHandler` | `ReleaseAsync` | `repository.SaveAsync` | No |
| `DeleteMediaItemHandler` / `PurgeMediaItemVersionHandler` | — (none) | `repository.SaveAsync` | N/A — gated on `Status==Archived`, reservation already released |

Failure modes between the two writes:
- **Create:** Save fails, orphaned reservation, name permanently blocked (no aggregate to archive-release it). Retry blocked by non-owner-aware Tier-1 check.
- **Rename (Swap):** Save fails, aggregate keeps old name, table says new name; old name now free for others; retry blocked.
- **Archive (Release):** Save fails, name freed while aggregate still Active, concurrent create can duplicate the name.

### 2.2 Platform primitives already in place

- `INameReservationService.ApplyAsync(NameReservationIntent)` — intent-based; `SwapAsync`, `MoveAsync`, `ReserveManyAcrossScopes`, `DeleteScopeAsync` already commit via `TransactWriteItems` in `DynamoDbNameReservationStore`. Single `Reserve`=conditional `PutItem`, single `Release`=`DeleteItem`.
- `IUniquenessCounterService` — counter rows live in the **same table and same partition** as reservations: `PK=TENANT#{tenantId}#SCOPE#{scope}`, `SK=COUNTER#{counter}` (reservations use `SK=NAME#{name}`). `Decrement` floored at 0.
- `DynamoDbEventStore.SaveAsync` — **already builds `List<TransactWriteItem>`** (one conditional `Put` per aggregate, `attribute_not_exists(SortKey)`) and calls `TransactWriteItemsAsync`. Max 25 items/txn, single-tenant enforced.

This is the key enabler: the event append is *already a transaction*; we only need to let it carry a few extra items.

### 2.3 Counters that actually exist

`CounterKeys` = `{ depth, active-registrations }`. `child-folders` / `active-items` are **not defined or used anywhere**. `ArchiveFolderHandler` blocks only on `FolderArchiveFanOutWorker.HasActiveRegistrationsAsync` (reads `active-registrations`), then cascades archival of descendants leaf-first. `MoveFolderHandler` adjusts `depth` via a **loop of single `Increment`/`Decrement` calls** (non-atomic, N calls).

### 2.4 No backstop

CDK (`cdk-magiq-media`) defines only DLQ-depth alarms (`sqs-queues.construct.ts`) and saga-approaching-timeout alarms (`magiq-media-stack.ts`). No counter alarm, no reconciliation job.

### 2.5 Spec/doc drift to correct

- `docs/adrs/catalog-domain-invariants.md` Hierarchy Invariants — describes `child-folders`/`active-items` counters and a `CounterIsZero` archive guard that don't exist; counter key layout (`PK=<tenantId>`) is wrong (real: `PK=TENANT#{tenantId}#SCOPE#{scope}`); "negative counter alarm" backstop is a phantom.
- `docs/spec/shared/system-spec.md` — Tier 2 (~L283–301) implies event+reservation commit in one `TransactWriteItems`; L351 correctly says they are two separate writes. Self-contradiction; L351 matches code today (and L283 becomes true once Tier 2 lands).

---

## 3. Requirements

**R1 — Atomic write.** Aggregate event append + name reservation mutation (+ any counter mutation in the same command) must commit atomically or not at all.
**R2 — Self-healing retries.** A client retry of a create/rename after a partial failure must converge, not dead-end on `AlreadyExists`.
**R3 — No silent divergence.** Any residual reservation/counter drift must be detectable (observability), since under-count is silent and negatives are impossible.
**R4 — Complete release coverage.** Every name-freeing transition releases; confirmed — keep it that way and add the two missing cases (create-failure compensation; cascade partial-failure).
**R5 — Docs match code.** ADR + system-spec reflect the shipped design (cascade+registration-block; real counter set/layout; atomic write once R1 lands).

---

## 4. Tier 1 — handler + cascade hardening (no platform change)

Ship first; closes the live holes immediately and remains correct even after Tier 2.

**T1.1 — Compensating release on Save failure** for `CreateCollectionHandler`, `CreateFolderHandler`, `CreateRecordTypeHandler`. Wrap `repository.SaveAsync` in try/catch; on failure, `ReleaseAsync` the just-made reservation (and, for folder, decrement the `depth` counter it set) before rethrowing. Mirror the existing `CreateMediaProfileHandler` pattern. _(R1 partial, R4.)_

**T1.2 — Owner-aware Tier-1 check.** In create/rename handlers, when `IsNameAvailableAsync` returns false, call `GetOwnerIdAsync`; if the holder is *this* aggregate's ID, treat as already-reserved and continue to the event append instead of returning `AlreadyExists`. Makes retries idempotent/resumable — the mitigation the ADR claims. _(R2.)_

**T1.3 — Harden `FolderArchiveFanOutWorker`.** Today it logs a warning and continues on a failed descendant archive, then the root is archived anyway, active name-holding child under an archived parent. Change to: collect failures and **fail the root archive** if any descendant archive failed (surface a retryable error), OR convert the cascade to a resumable saga. Recommend fail-fast now, saga later if cascade sizes grow. _(R4.)_

Tier-1 files (app repo, `src/modules/Catalog/...` + `src/modules/Metadata/...`): the six create/rename handlers above + `FolderArchiveFanOutWorker.cs`. Mechanical; no new abstractions.

---

## 5. Tier 2 — platform transactional write (the real `ITransactionalUniquenessRegistry`)

Goal: one `TransactWriteItems` carrying the aggregate event `Put` (with its `attribute_not_exists` concurrency guard) **plus** the reservation `Put`/`Delete` and any counter `Update`. All same account/region; name ops add 1–2 items to a transaction that normally holds 1, far under the 25-item limit.

### 5.1 Design fork — how the event store carries extra items

**Option T-A (recommended) — event store accepts enlisted conditional writes via a platform-neutral abstraction.**
- New abstraction (in `Magiq.Platform.EventSourcing.Abstractions`): `IConditionalWrite` — a store-neutral description of a put/delete/update-with-condition (no AWS types).
- `IEventStore` gains an overload: `SaveAsync<TAggregate>(TAggregate aggregate, IReadOnlyCollection<IConditionalWrite> sideEffects, CancellationToken)`.
- `DynamoDbEventStore` translates `IConditionalWrite` to `TransactWriteItem` and appends to its existing `transactItems` list before the single `TransactWriteItemsAsync` call.
- `Magiq.Platform.UniquenessRegistry.Abstractions` gains `ITransactionalUniquenessRegistry` that turns intents (`ReserveNameIntent`, `SwapNameReservationIntent`, counter deltas, …) into `IConditionalWrite`s. Handlers pass those to the repo/event-store overload.
- **Pros:** event store stays the single commit authority; minimal new surface; no AWS types in abstractions; reuses existing intent records. **Cons:** one new neutral abstraction (`IConditionalWrite`) + a DynamoDb translator.

**Option T-B — shared DynamoDb transaction builder.** Both event store and registry contribute `TransactWriteItem`s to a coordinator that commits. Most flexible; more plumbing; risks coupling `EventSourcing.DynamoDb` to `UniquenessRegistry.DynamoDb`.

**Option T-C — compensation-only (no true atomicity).** Skip the cross-table transaction; rely on Tier-1 owner-aware idempotency + the reconciliation job (Section 6). Lowest risk/effort; does **not** satisfy R1 (windows remain, just detected + healed). Fallback if the platform change is deferred.

**Recommendation: T-A.** It satisfies R1 with the smallest clean footprint and keeps platform layering intact.

### 5.2 Plumbing (T-A)

Handler to app repository `SaveAsync(aggregate, sideEffects)` to platform `EventStoreRepository.SaveAsync(aggregate, sideEffects)` to `IEventStore` overload to `DynamoDbEventStore` translate + single-transaction commit.

Touchpoints:
- `Magiq.Platform.EventSourcing.Abstractions`: add `IConditionalWrite` + `IEventStore.SaveAsync(aggregate, sideEffects, ct)` overload.
- `Magiq.Platform.EventSourcing.DynamoDb`: translate + append to `transactItems`.
- `Magiq.Platform.EventSourcing` (`EventStoreRepository`): pass-through overload; snapshot logic unchanged.
- `Magiq.Platform.UniquenessRegistry(.Abstractions/.Stores.DynamoDb)`: `ITransactionalUniquenessRegistry` producing `IConditionalWrite`s from intents.
- App repositories (`IFolderRepository`, `ICollectionRepository`, `IMediaItemRepository`, `IMediaProfileRepository`, `IRecordTypeRepository` + impls): `SaveAsync(aggregate, sideEffects)` overload.
- Catalog/Metadata handlers: replace the separate `ReserveAsync/SwapAsync/MoveAsync/ReleaseAsync` + `SaveAsync` pair with one enlisted `SaveAsync(aggregate, sideEffects)`. Counter mutations that belong to the same command (`depth`, `active-registrations`) fold in as counter side-effects. After this, Tier-1's T1.1 compensation becomes unnecessary (kept harmless) and T1.2 owner-aware check becomes belt-and-suspenders.

### 5.3 Package/release note

magiq-media consumes the platform via **NuGet PackageReferences**, not project references. The new/changed `Magiq.Platform.EventSourcing.*` and `Magiq.Platform.UniquenessRegistry.*` packages must be built, version-bumped in `Directory.Packages.props`, and restored before the app compiles against the new overloads. (Same release gotcha called out in S1/S6.)

---

## 6. CDK + observability (R3)

- **Delete the phantom backstop from the design** (there is no negative-counter alarm and negatives are impossible).
- **Add a reconciliation job** (scheduled Lambda, like `TimeoutScanner`): per tenant/scope, diff `NAME#` reservations and `COUNTER#` values against aggregate/read-model state; emit a CloudWatch metric + alarm on orphaned reservations or under-counts. This is the only backstop that catches the *real* failure (silent under-count / orphaned reservation). Only needed as a safety net once Tier 2 lands; **required** if T-C is chosen instead.
- CDK: new scheduled Lambda + rule; metric filter/alarm. No table changes (reservations+counters already co-located).

---

## 7. Docs (R5)

- Rewrite `docs/adrs/catalog-domain-invariants.md` Hierarchy Invariants: shipped design is cascade archival + active-registrations block; `child-folders`/`active-items` counters do not exist; real counter set = `depth` + `active-registrations`; real key layout `PK=TENANT#{tenantId}#SCOPE#{scope}`, `SK=COUNTER#{counter}`; decrement floored (negatives impossible); replace "negative-counter alarm" with the reconciliation job; record that atomicity is delivered by `ITransactionalUniquenessRegistry` (Tier 2), not deferred.
- Fix `docs/spec/shared/system-spec.md`: reconcile Tier 2 (~L283–301) with L351 — pre-Tier-2 they are two writes; post-Tier-2 they commit in one `TransactWriteItems`. State the current reality and the target.
- These land in the same PR as the code they describe (docs/ co-location rule).

---

## 8. Sequencing

1. **Tier 1** (T1.1–T1.3) — app-only, no platform bump. Ship first.
2. **Docs** — correct ADR + system-spec to as-built (can land with Tier 1).
3. **Tier 2** — platform packages then version bump then app rewire. Larger PR; gated on platform build.
4. **CDK reconciliation job** — after Tier 2 (or with T-C if platform is deferred).

## 9. Verification (cannot run in this session — no compiler)

- `dotnet build` `aspnetcore-platform` (EventSourcing.*, UniquenessRegistry.*) + unit tests.
- Version-bump packages; restore in magiq-media; `dotnet build` Api + EventConsumers hosts.
- Run `Catalog.WriteModel.Tests`, `Catalog.IntegrationTests`, `Metadata.*` — add tests for: create Save-failure to no orphaned reservation; retry-after-partial-failure converges; archive cascade partial failure fails root; enlisted transaction rolls back reservation on event-concurrency conflict.
- `cdk synth` / `diff` for the reconciliation Lambda.

## 10. Open decisions for Chase

- **D1 — Tier-2 API:** confirm **T-A** (neutral `IConditionalWrite` + event-store overload) vs T-B (shared txn builder) vs T-C (compensation-only, defer platform).
- **D2 — Cascade:** fail-fast now (recommended) vs go straight to a resumable archive saga.
- **D3 — Reconciliation job:** build now as the safety net, or defer until after Tier 2 proves out.

---

## 11. Decisions confirmed (2026-07-18, Chase)

- **D1 = T-A** (best-practice call): store-neutral `IConditionalWrite` + `IEventStore.SaveAsync` overload; DynamoDb event store translates and appends to its existing transact list. Event store remains the single commit authority; abstractions stay AWS-free; no cross-adapter coupling.
- **D2 = Resumable archive saga now** (supersedes the fail-fast option in T1.3). Folder archive cascade becomes a durable, resumable saga rather than an in-handler fan-out that swallows failures.
- **D3 = Build the reconciliation Lambda now**, in parallel with the rest — active detector for orphaned reservations / under-counts before the atomic path lands.

### Revised sequencing given the above
1. **PR1 — platform foundation (aspnetcore-platform):** `IConditionalWrite` + `IEventStore.SaveAsync(aggregate, sideEffects)` overload + DynamoDb translator; `ITransactionalUniquenessRegistry` producing `IConditionalWrite`s. Version-bump packages.
2. **PR2 — app rewire (magiq-media):** repository `SaveAsync(aggregate, sideEffects)` overloads; Catalog/Metadata handlers switch to the enlisted single-transaction write (event + reservation + counter). This makes the Tier-1 T1.1 compensating-release throwaway; keep only T1.2 owner-aware check as defense-in-depth.
3. **PR3 — archive saga (magiq-media + CDK):** resumable `FolderArchiveSaga` replacing the in-handler fan-out; register in `SagaRegistrations`; CDK queue + orchestrator wiring.
4. **PR4 — reconciliation job (magiq-media + CDK):** scheduled Lambda diffing `NAME#`/`COUNTER#` vs aggregate state; CloudWatch metric + alarm.
5. **Docs (with each PR):** correct `catalog-domain-invariants.md` + `system-spec.md` as the code lands.

> **Blocker noted 2026-07-18:** all three repos have large uncommitted working trees (magiq-media 1621 files + stale `.git/index.lock`; aspnetcore-platform 1366; cdk 41). S13 must land on clean dedicated branches cut from a committed base — not on top of the current in-flight S5/S6/JTI work. Clear the lock and commit/stash first, or author S13 as apply-on-clean patches.
