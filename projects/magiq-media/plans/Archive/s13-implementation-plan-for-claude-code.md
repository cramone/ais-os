# S13 Implementation Plan (for a Claude Code session)

_magiq-media - Executable implementation runbook for architecture-spec-review finding S13._
_Prepared 2026-07-18 for Chase Ramone. Execute this in a local Claude Code session with build/test access._
_Companion design doc: plans/s13-uniqueness-atomicity-remediation-plan.md (read it first for the "why")._

---

## 0. How to use this document

You are implementing S13 across three repos:
- D:\source\github\aspnetcore-platform - the Magiq.Platform / Magiq.AspNetCore SDK (has its own CLAUDE.md)
- D:\source\github\magiq-media - the application (has its own CLAUDE.md)
- D:\source\github\cdk-magiq-media - CDK/TypeScript deploy infra

Read each repo's CLAUDE.md before editing it. Follow its conventions exactly (they override defaults). Key ones that bite here: NuGet versions are centrally managed in Directory.Packages.props (never pin in a .csproj); nullable reference types on (no unjustified !); commands return Result<T, DomainError> (no domain exceptions escape handlers); strongly-typed Id<T> (never raw Guid); FastEndpoints only; abstractions-before-implementations (an *.Abstractions project holds interfaces, no infra types).

Work PR by PR, in order - each is independently buildable and reviewable. Build and test after every PR. Do not batch all four into one branch.

This plan is decision-locked (Chase, 2026-07-18): Tier-2 API = T-A (neutral IConditionalWrite + event-store overload); folder archive = resumable saga; reconciliation Lambda = build now.

---

## 1. Corrected problem (one paragraph)

Every name-scoped handler in Catalog/Metadata writes the name reservation (and any counter) to media-name-reservations first, then appends the aggregate event to media-events last, as two separate DynamoDB writes with no shared transaction. A failure between them orphans a reservation (create), splits reservation vs aggregate name state (rename), or frees a name while the aggregate is still live (archive). The DynamoDbEventStore already commits via TransactWriteItems; the fix is to let that single transaction also carry the reservation/counter writes. Separately: the catalog-domain-invariants.md ADR describes child-folders/active-items counters and a negative-counter alarm that do not exist (real counters are only depth and active-registrations; decrement is floored so negatives are impossible; there is no counter alarm), and the folder-archive cascade currently swallows per-descendant failures. All of that is corrected here.

---

## 2. Pre-flight (do once, before PR1)

1. Clear the stale lock. D:\source\github\magiq-media\.git\index.lock is present and will block git writes. Confirm no git process is running, then delete it.
2. Commit or stash in-flight work. All three repos have large uncommitted trees (magiq-media ~1600 files, aspnetcore-platform ~1300, cdk ~40) containing S5/S6/JTI work. Get each repo to a clean, committed base before cutting S13 branches so S13 lands isolated and reviewable. Confirm with Chase what to commit vs stash.
3. Branch names (GitFlow, cut from develop):
   - platform: feature/chase/s13-transactional-uniqueness
   - app: feature/chase/s13-uniqueness-atomicity
   - cdk: feature/chase/s13-reconciliation-and-archive-saga
4. Baseline build each repo green before changing anything, so later failures are attributable.

---

## 3. PR1 - Platform foundation (aspnetcore-platform)

Goal: the event-store append can atomically carry extra conditional writes (reservation puts/deletes, counter updates), and the uniqueness registry can produce those writes from intents. No AWS SDK types leak into any *.Abstractions project.

### 3.1 New abstraction: IConditionalWrite

Create in src/platform/Domain/Magiq.Platform.EventSourcing.Abstractions/Transactions/ (new folder):
- IConditionalWrite - marker/base for a store-neutral conditional write.
- Concrete neutral records (no AWS types):
  - ConditionalPut(string TableId, IReadOnlyDictionary<string, WriteValue> Item, string? ConditionExpression) - reserve a name (condition attribute_not_exists(PK) equivalent, expressed neutrally).
  - ConditionalDelete(string TableId, IReadOnlyDictionary<string, WriteValue> Key, string? ConditionExpression) - release.
  - CounterUpdate(string TableId, IReadOnlyDictionary<string, WriteValue> Key, string CounterAttribute, long Delta, string? ConditionExpression) - increment/decrement (ADD), incl. the floored-decrement condition.
- WriteValue - a tiny neutral value union (string / number / bool) so abstractions do not reference AttributeValue. Keep it minimal - only S and N as used by reservation/counter rows.
- TableId is a logical id the DynamoDb layer resolves to a physical table name via the existing ITableResolver (the uniqueness table already registers DynamoDbNameReservationTableSchema.TableId). Do not put physical table names in the abstraction.

Design note: keep this abstraction deliberately tiny and reservation/counter-shaped. It is not a general query language - just enough to express reserve/release/swap/move/counter += n as transact items. This keeps the translator trivial and the 25-item transaction budget obvious.

### 3.2 Event-store overload

IEventStore (Magiq.Platform.EventSourcing.Abstractions/IEventStore.cs) - add:

    Task SaveAsync<TAggregate>(
        TAggregate aggregate,
        IReadOnlyCollection<IConditionalWrite> sideEffects,
        CancellationToken cancellationToken = default)
        where TAggregate : IEventSourced;

DynamoDbEventStore (Magiq.Platform.EventSourcing.DynamoDb/DynamoDbEventStore.cs):
- Refactor the existing single-aggregate append so it builds its List<TransactWriteItem> (aggregate Put with ConditionExpression = attribute_not_exists(SortKey)), then appends the translated sideEffects before the one TransactWriteItemsAsync call.
- Add a private TransactWriteItem Translate(IConditionalWrite) mapping the neutral records to Put/Delete/Update using ITableResolver for TableId and building AttributeValues from WriteValue.
- Enforce the transaction budget: assert 1 + sideEffects.Count <= 25 (name ops add 1-2); throw a clear InvalidOperationException if exceeded.
- Preserve existing behavior: TransactionCanceledException -> EventConcurrencyException (now also covers a reservation-condition failure, which is correct - a concurrent name claim should surface as a conflict; verify the handler maps it appropriately in PR2).
- The no-side-effects overload keeps calling the existing path unchanged.

### 3.3 Repository pass-through

IRepository<TAggregate, TId> (Magiq.Platform.WriteModel) - add:

    Task SaveAsync(TAggregate aggregate,
        IReadOnlyCollection<IConditionalWrite> sideEffects,
        CancellationToken cancellationToken = default);

EventStoreRepository.SaveAsync(aggregate, sideEffects, ct) - mirror the existing SaveAsync(aggregate) exactly (early-out on !HasChanges(), DomainException.PersistenceFailure wrap, executionContext.RecordEvents + ClearUncommittedEvents, snapshot policy), but call the new eventStore.SaveAsync(aggregate, sideEffects, ct). Factor a private helper if cleaner rather than duplicating snapshot logic.

### 3.4 ITransactionalUniquenessRegistry

Magiq.Platform.UniquenessRegistry.Abstractions - add ITransactionalUniquenessRegistry that converts existing intent records into IConditionalWrites (does not execute them):

    public interface ITransactionalUniquenessRegistry
    {
        IReadOnlyCollection<IConditionalWrite> Build(params NameReservationIntent[] intents);
        IConditionalWrite Reserve(string tenantId, ScopeKey scope, string name, OwnerId owner);
        IConditionalWrite Release(string tenantId, ScopeKey scope, string name);
        IReadOnlyCollection<IConditionalWrite> Swap(string tenantId, ScopeKey scope, string oldName, string newName, OwnerId owner);
        IReadOnlyCollection<IConditionalWrite> Move(string tenantId, ScopeKey oldScope, ScopeKey newScope, string name, OwnerId owner);
        IConditionalWrite CounterDelta(string tenantId, ScopeKey scope, string counter, long delta); // floored decrement condition when delta<0
    }

Implement in Magiq.Platform.UniquenessRegistry.Stores.DynamoDb (it knows the layout: PK=TENANT#{tenantId}#SCOPE#{scope}, SK=NAME#{normalizedName} | COUNTER#{counter}; normalize names exactly as NormalizedName/NameReservation factories do - reuse them). Reuse DynamoDbNameReservationTableSchema constants. Register in the existing DI extensions.

Keep the old INameReservationService.ApplyAsync path intact - bulk/standalone flows (BulkCreateFolders, seeding) still use it. Only the single-aggregate name handlers move to the transactional path in PR2.

### 3.5 In-memory parity

Update Magiq.Platform.UniquenessRegistry.Stores.InMemory and any in-memory IEventStore used by tests so SaveAsync(aggregate, sideEffects) applies side-effects against the in-memory reservation/counter store atomically (single lock section). Tests depend on this parity.

### 3.6 Tests (PR1)

- Event store: SaveAsync(aggregate, sideEffects) commits event + reservation together; a failing reservation condition rolls back the event (no stream written); >25 items throws.
- Registry: Reserve/Release/Swap/Move/CounterDelta produce correctly-keyed writes; decrement carries the >= amount floor condition.

### 3.7 Package/versioning + build

- Bump versions for changed packages (Magiq.Platform.EventSourcing.Abstractions/.DynamoDb, Magiq.Platform.WriteModel, Magiq.Platform.UniquenessRegistry.Abstractions/.Stores.*) per this repo's scheme; central-managed.
- dotnet build the solution + dotnet test affected projects. Pack the nupkgs (use Copy-PackagesLocal.ps1 / Clean-Packages.ps1 to publish to the local feed magiq-media restores from).

---

## 4. PR2 - App rewire (magiq-media)

Goal: every single-aggregate name handler commits event + reservation (+ same-command counter) in one enlisted transaction. Depends on PR1 packages being restorable.

### 4.1 Bump the platform dependency

Update Directory.Packages.props to the PR1 versions; dotnet restore. Confirm the app sees IConditionalWrite, ITransactionalUniquenessRegistry, and the new SaveAsync overload.

### 4.2 Module repository overloads

Add to each module repo interface + impl a pass-through SaveAsync(aggregate, IReadOnlyCollection<IConditionalWrite> sideEffects, ct) that delegates to the wrapped IRepository<T,TId>.SaveAsync(aggregate, sideEffects, ct):
- IFolderRepository/FolderRepository, ICollectionRepository, IMediaItemRepository, IMediaProfileRepository (Catalog), IRecordTypeRepository (Metadata).

### 4.3 Rewire the handlers

For each handler below: remove the standalone nameReservationService.{Reserve|Swap|Move|Release}Async call and any same-command counter call; build the equivalent IConditionalWrite[] via ITransactionalUniquenessRegistry; pass them to repository.SaveAsync(aggregate, sideEffects, ct). Keep the Tier-1 IsNameAvailableAsync pre-check (fast fail + friendly error) but rely on the transaction's reservation condition as the authoritative guard - a conflict from the enlisted write maps to the existing EntityAlreadyExists domain error (verify the CommandHandler base / MediatR pipeline translates EventConcurrencyException; add mapping if not).

Handlers (Catalog unless noted):
- Create: CreateCollectionHandler, CreateFolderHandler (+ depth counter delta as a side-effect), CreateMediaProfileHandler, CreateRecordTypeHandler (Metadata). Remove the now-unnecessary compensating ReleaseAsync in CreateMediaProfileHandler.
- Rename/title: RenameCollectionHandler, RenameFolderHandler, UpdateMediaItemTitleHandler, RenameRecordTypeHandler (Metadata) -> Swap side-effects.
- Move: MoveFolderHandler (+ depth delta; replace the increment/decrement loop with a single CounterDelta), MoveMediaItemHandler -> Move side-effects.
- Archive/deprecate: ArchiveCollectionHandler, ArchiveMediaItemHandler, DeprecateMediaProfileHandler, DeprecateRecordTypeHandler -> Release side-effect. (ArchiveFolderHandler changes land in PR3 with the saga.)
- Publish (name change): PublishMediaProfileHandler -> Swap; remove its compensating release.

Leave unchanged: DeleteMediaItemHandler/PurgeMediaItemVersionHandler (gated on Status==Archived, reservation already released), and the bulk handlers (BulkCreate*) which keep the existing ApplyAsync/lock path unless Chase wants them converted (out of scope for S13).

### 4.4 Owner-aware retry (defense-in-depth)

Even with atomicity, keep create/rename idempotent on client retry: when Tier-1 IsNameAvailableAsync returns false, call GetOwnerIdAsync; if the holder is this aggregate's id, treat as already-reserved and proceed (skip re-adding the reserve side-effect; still append any pending event). A retried, partially-applied command then converges instead of returning AlreadyExists.

### 4.5 Tests (PR2)

Per aggregate (Catalog.WriteModel.Tests + Catalog.IntegrationTests, Metadata.*):
- Create then simulate event-append conflict -> no orphaned reservation.
- Concurrent create of same name -> exactly one wins; loser gets EntityAlreadyExists.
- Rename retry after simulated partial failure converges (owner-aware path).
- Move updates depth by a single delta and moves the reservation atomically.
- dotnet build Api + EventConsumers hosts; run the module test projects.

---

## 5. PR3 - Resumable folder-archive saga (magiq-media + cdk)

Goal: replace the in-handler fan-out (which swallows per-descendant failures and archives the root anyway) with a durable, resumable saga so a partial cascade cannot leave an active, name-holding child under an archived parent.

### 5.1 Model on the existing ingestion saga

Read AssetIngestionSaga + SagaRegistrations + the SagaOrchestrator host + TimeoutScanner first, and mirror their structure (platform saga abstractions per app CLAUDE.md: ISaga/ISagaDefinition, ISagaStateStore, ISagaMessageRouter, timeout handling). Do not invent a new saga shape.

### 5.2 Design

- New FolderArchiveSaga with durable state: root FolderId, tenant, discovered subtree levels (or a cursor), per-node archive status, and a timeout.
- Trigger: ArchiveFolderHandler validates (folder exists; block on active registrations in subtree - keep HasActiveRegistrationsAsync), then starts the saga instead of calling FolderArchiveFanOutWorker inline.
- Saga steps: BFS-discover descendants -> archive media items -> archive descendant folders leaf-first -> archive root. Each step dispatches the existing ArchiveMediaItemCommand/ArchiveFolderCommand (leaf-node archive), which already release reservations via PR2's enlisted path. On a step failure: retry with backoff; on exhaustion, park the saga in a Faulted state and emit an alarm-worthy failure event - never advance to root archive. Archiving an already-archived node is a no-op (idempotent).
- Retire FolderArchiveFanOutWorker's fire-and-forget Task.WhenAll + warning-swallow. If you keep the BFS helpers, move them into the saga; delete the swallow-and-continue dispatch.

### 5.3 CDK + registration

- Register FolderArchiveSaga in SagaRegistrations.
- CDK (cdk-magiq-media): add the SQS queue + DLQ (reuse sqs-queues.construct.ts pattern with its DLQ-depth alarm) and wire the SagaOrchestrator subscription filter for the saga's message types. Ensure TimeoutScanner covers the new saga's timeouts.

### 5.4 Tests (PR3)

- Cascade success archives whole subtree + releases all reservations.
- Injected mid-cascade failure: saga faults, root stays active, no orphaned/leaked reservations, retry resumes to completion.
- Active registration in subtree blocks the archive at validation.

---

## 6. PR4 - Reconciliation job (magiq-media + cdk)

Goal: an active detector for the real failure modes (orphaned NAME# reservations, under-counted COUNTER# values). Required now (Chase's call), and the sole backstop if any non-atomic path remains.

### 6.1 Model on TimeoutScanner

New CloudWatch-scheduled host (mirror TimeoutScanner's Lambda + schedule wiring). Per tenant/scope it:
- Scans media-name-reservations NAME# rows and confirms each has a live aggregate (via read model / event-store existence) owning that name in that scope; flags orphans.
- Recomputes depth/active-registrations counters from source (read models) and flags drift (esp. under-count).
- Emits CloudWatch metrics (OrphanedReservations, CounterDrift) and logs actionable detail. Do not auto-mutate in v1 - alarm + report; add guarded auto-heal later if desired.

### 6.2 CDK

- New scheduled Lambda + EventBridge rule (reuse existing scheduled-Lambda pattern).
- CloudWatch Alarm on the drift metrics (replaces the phantom negative-counter alarm the ADR references - negatives are impossible; this watches orphans/under-count instead).

### 6.3 Tests (PR4)

- Seed an orphaned reservation and a drifted counter in an integration fixture; assert the scanner emits the metrics.

---

## 7. Docs (land with the PR that makes them true)

### 7.1 docs/adrs/catalog-domain-invariants.md (Hierarchy Invariants section)

Rewrite to as-built + as-fixed:
- Remove the child-folders/active-items counter table and the CounterIsZero archive-guard code block - never implemented.
- State the real counter set: depth (folder nesting cap) and active-registrations (folder-archive block), keyed PK=TENANT#{tenantId}#SCOPE#{scope}, SK=COUNTER#{counter} (same table/partition as NAME# reservations). Decrement is floored (#count >= :amount), so a counter cannot go negative.
- Describe folder archive as a resumable saga (cascade leaf-first, blocked on active registrations), not an in-handler fan-out.
- Replace "backstopped by a CloudWatch alarm on negative counter values" with the reconciliation job (orphaned-reservation / counter-drift alarms).
- Record that reservation + event + counter now commit atomically via ITransactionalUniquenessRegistry (T-A) - remove the "deferred / not yet built" language.

### 7.2 docs/spec/shared/system-spec.md (Name Uniqueness)

- Reconcile the self-contradiction: pre-fix text ~L283-301 (implying event + reservation are one TransactWriteItems) vs ~L351 (two separate writes). After PR2 the single-transaction statement is true - update L351's "not atomic" note to describe the enlisted transaction, and make the Tier-2 section describe the IConditionalWrite enlistment.
- Correct the counter key layout if referenced.

Spec/ADRs live under D:\source\github\magiq-media\docs\ and publish to the ADO wiki via CI - edit there, in the same PR as the code, and do not hand-edit the Media.wiki repo.

---

## 8. Cross-cutting gotchas

- NUL bytes / BOM: several Catalog/Metadata spec + a few source files carry stray NUL padding (read as "binary" to grep). If you touch one, strip the NUL bytes (they also break the wiki publish). Do not introduce new ones.
- Central package versions: any new package reference goes in Directory.Packages.props; never a Version= in a .csproj.
- No Guid: use the strongly-typed Id<T>/UUID v7 value objects; OwnerId wraps the aggregate id string - match existing usage (handlers pass aggregate.Id.ToString()).
- Result<T, DomainError>: no exceptions for control flow; conflicts surface as domain errors at the handler boundary.
- Snapshots: the enlisted SaveAsync must preserve snapshot-on-policy behavior (best-effort/after-commit today - keep it that way).
- Do not convert bulk handlers unless asked - they use locks + ApplyAsync and are out of S13 scope.

---

## 9. Definition of done

- [ ] PR1 platform builds + tests green; nupkgs packed to local feed.
- [ ] PR2 app builds (Api + EventConsumers) + Catalog/Metadata tests green; new atomicity/idempotency tests pass.
- [ ] PR3 archive saga registered; partial-failure test proves no root archive on descendant failure; CDK synth/diff clean.
- [ ] PR4 reconciliation Lambda + alarm; drift-detection test passes; CDK synth/diff clean.
- [ ] Docs (ADR + system-spec) updated in the same PRs and consistent with code.
- [ ] Each PR is a clean branch off develop, no unrelated S5/S6/JTI churn, index.lock cleared.

---

## 10. Suggested order of operations for the session

1. Pre-flight (Section 2) - clear lock, clean base, branches, baseline builds.
2. PR1 (platform) -> build/test/pack.
3. PR2 (app) -> bump dep, rewire, build/test. Ship value here - atomicity is live.
4. PR3 (saga) -> build/test + CDK.
5. PR4 (reconciliation) -> build/test + CDK.
6. Docs verified against final code; open PRs.
