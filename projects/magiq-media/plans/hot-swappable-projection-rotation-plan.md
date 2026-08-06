# Hot-Swappable Projection Table Rotation (Blue-Green) — Implementation Plan

**Status:** Ready to implement · **Author:** Chase (via Claude analysis session, 2026-07-24)
**Scope:** `aspnetcore-platform` (platform SDK) + `magiq-media` (app + CLI)
**Goal:** Rebuild a read-model (projection) DynamoDB table into a new versioned table and cut live reads/writes over to it **without redeploying the application** — with atomic cutover and instant rollback.

> This plan is self-contained. A fresh session with access to the two repos can execute it without re-doing the discovery. All current-state facts below were verified against the code on 2026-07-24; re-confirm file paths before editing (the platform Replay subsystem was scaffolded but never integration-tested, so treat its current contents as a starting skeleton, not working code).

---

## Decision addendum — rotation unit (2026-07-24)

**Open decision §8.1 is resolved: rotation is keyed by `TableId` — the platform's stable logical table identity — not by read-model type name and not by physical table name.**

Rationale, verified against the code:
- The physical table name is *derived* from a `TableId` (`ITableResolver.GetTableName(tableId)` applies prefix/segment/suffix) and is exactly what a rotation *changes*, so it cannot be the stable key.
- Read models already share physical tables today: `Catalog` registers `MediaItemVersionSummaryReadModel` **and** `MediaItemVersionDetailReadModel` under `media-item-versions`, and `RecordTypeSummaryReadModel` **and** `RecordTypeVersionDetailReadModel` under `media-record-types` (M2). Keying by read-model type name would rebuild one and orphan its co-located siblings.
- `TableId` is stable across physical renames and shared by co-located read models, so rotating a `TableId` rebuilds every read model mapped to it, together. This also preserves the platform's existing multiple-projections-per-table capability (unused by magiq-media today, but supported).

Every component keys by `TableId`: the metadata row identity (P1), the active-table snapshot (P2.1), the replay override (P2.2), the resolver precedence (P2.3), and the orchestrator (P4). PR1's metadata layer is updated accordingly (record field, store key attribute, migration PK → `TableId`).

## Execution model — separate replay tool (2026-07-25)

Rotation is **not** run from the deployed magiq-media services. A **separate replay tool** owns rotation
execution and the lifecycle of the versioned (`_v{n}`) tables. Responsibilities split three ways:

- **Deployed hosts (Api, QueryApi, Projectors.*)** — rotation-*aware* only: the resolver, the active
  snapshot, the replay context, and read/write of the metadata table. They never create or drop tables.
  After a flip they read/write the new active `_v{n}` table, so their DynamoDB data-plane IAM must reach
  it (see M4).
- **cdk-magiq-media** — provisions the initial metadata table as a normal CDK table with a `TableId`,
  granted like the others. `ProjectionsTableMigration` also creates it (folded in), so it exists in
  non-CDK contexts too. The standalone `ReadModelTableMetadataStoreMigration` is retired.
- **Separate replay tool** — resolves `IProjectionRotationOrchestrator` in its own scope, creates and
  drops the `_v{n}` tables, and needs DynamoDB control-plane IAM plus `ITableSchemaBuilder` registered in
  its DI (the platform does not register it — `TableMigrationManager` news it up).


---

## 1. Background & the load-bearing problem

magiq-media resolves every projection table name through a single choke point:

```
DynamoDbProjectionStore<T>  →  IProjectionTableNameResolver.Resolve(schema)
   →  ProjectionTableNameResolver  →  ITableResolver (singleton)  →  IOptions<DynamoDbOptions>
```

`TableResolver` reads `IOptions<DynamoDbOptions>` **once** and memoizes every physical name in a `ConcurrentDictionary`. Physical table names are therefore **frozen for the process lifetime**. The well-known names enter via `AddProjectionSchema<T>("media-collection", …)` plus a global `Platform:DynamoDB:TableSuffix`.

**Consequence:** the only way to point the app at a differently-named table today is a config change + redeploy. There is no runtime pointer.

**The one piece of leverage:** reads *and* writes both go through `ProjectionTableNameResolver.Resolve`. Make that method rotation-aware and both paths move together, in one change.

### What already exists in the platform (skeleton, unwired)

Under `aspnetcore-platform/src/platform/Domain/Magiq.Platform.Projections.Stores.DynamoDb/Replay/`:

- `Metadata/ReadModelTableMetadata.cs` — record `{ ReadModelName, ActiveTableName, Version, ReplayInProgress, LastRotatedAt }`. **Missing a `PendingTableName` field** even though the store reads/writes one.
- `Metadata/Stores/ReadModelTableMetadataStore.cs` — DynamoDB-backed. `BeginReplayAsync` / `CompleteReplayAsync` do a **correct atomic conditional-write flip** (`SET ActiveTableName = PendingTableName … REMOVE PendingTableName` guarded on `ReplayInProgress`). **Three bugs** (see §4).
- `Metadata/Stores/ReadModelTableMetadataStoreMigration.cs` — creates the metadata table with `PK`/`SK` keys that **don't match** the store's `ReadModelName` access pattern. Broken as written.
- `Metadata/IReadModelMetadataTableResolver.cs` + `Metadata/Resolvers/ReadModelMetadataTableResolver.cs` — thin wrapper over the store (`BeginRotation`/`CompleteRotation`/`GetActiveTable`).
- `Replay/DynamoDbProjectionReplayStore.cs` — **entirely `NotImplementedException` + commented pseudocode.** Orphaned: nothing uses `IReplayProjectionStore<TEvent>`.

**Wired and working:** `IProjectionReplayCoordinator` → `ProjectionReplayCoordinator` (`Magiq.Platform.Projections/Replay/`). It streams events via `IEventScanner` and dispatches them through the **normal** `IProjectionPipeline` in batches — i.e. it writes through the same `DynamoDbProjectionStore`/resolver as live projectors. It does **not** touch tables or metadata. Registered in both `AddProjections` overloads (`Magiq.Platform.Projections/ServiceCollectionExtensions.cs`).

**Nothing metadata/rotation-related is registered in any host or the CLI.** The magiq-media CLI `ProjectionsRebuildCommand` does a **destructive in-place** delete-then-replay into the single live table (opposite of blue-green).

### Key physical-reality constraint that simplifies the design

The projection tables are **multi-tenant** — one physical table holds all tenants (PK = `TENANT#{TenantId}#{EntityId}`). `TableNamePerTenant` exists in `DynamoDbOptions` but magiq-media does not use it. Therefore **rotation is per-read-model and GLOBAL across tenants** — you rebuild the whole table for all tenants at once. The `tenantId` parameters threaded through the Replay interfaces are vestigial/aspirational and should be treated as **global** (keyed by read-model name only). This removes the need for any tenant context in the resolver. (Per-tenant physical isolation is only meaningful if `TableNamePerTenant` is adopted — explicitly **out of scope**.)

---

## 2. Target design

### 2.1 Runtime pointer at the choke point

Make `ProjectionTableNameResolver.Resolve(schema)` consult an in-memory **active-table snapshot** keyed by **`TableId`** (the logical table the schema resolves to — see Decision addendum / §8.1):

- Resolve the schema's base `TableId` (existing logic: the per-type name registered under `ProjectionsTableSchema.TableId`, else the base `projections` table). If a metadata row exists for that `TableId` → return its `ActiveTableName`.
- If **no** metadata row exists for that `TableId` → return the existing static `ITableResolver` name (today's behavior). **Tables that are never rotated behave exactly as they do now — zero behavioral change, no bootstrapping required.**

`Resolve` must stay **synchronous** (it is called ~16 times inside `DynamoDbProjectionStore`; making it async ripples widely). Back it with a TTL cache:

- Snapshot = `Dictionary<string /*tableId*/, string /*activeTableName*/>` behind a `volatile` reference, plus a `last-refreshed` timestamp.
- On `Resolve`, read the snapshot synchronously. If older than the TTL (default **10s**), return the current (possibly slightly stale) value **and** kick a fire-and-forget async refresh (`Task.Run`) that reloads the metadata table and swaps the snapshot for the next call.
- **Do not use a background `IHostedService`/timer** — hosts are SQS-triggered Lambdas and are frozen between invocations, so timers are unreliable. Piggybacking refresh on `Resolve` calls is Lambda-safe.

**Flip latency = TTL** (all instances converge within ~10s of `CompleteReplay`). That is the "hot" in hot-swap. Cost: one `Scan`/`BatchGet` of the small metadata table per instance per TTL window — negligible.

### 2.2 Read-vs-write during replay (the one genuinely subtle decision)

During a rebuild, live projectors must keep writing the **active** (v1) table so queries stay fresh, while the replay writes the **pending** (v2) table. Both go through the same resolver. Distinguish them with an **ambient replay override**:

- Add `IReplayContext` (singleton) exposing an `AsyncLocal<string?> PendingTableOverride` (or a small scoped struct).
- The replay coordinator sets the override to the pending table for the duration of `ReplayAsync`.
- `Resolve` precedence becomes: **replay override (if set for the resolved `TableId`) → active-from-snapshot (by `TableId`) → static name.** Keying the override by `TableId` means that during a rotation of table X only writes destined for X are redirected to the pending table; writes to other tables triggered by the same event stream resolve normally.

Because replay runs in a **separate process** (the CLI, or a dedicated one-off task), the `AsyncLocal` override only affects that process. Live hosts never see it → they keep writing v1. This is the cleanest separation and needs no dual-write plumbing in the live projectors.

### 2.3 The tail / cutover sequence (leverages existing idempotency)

Projection writes are idempotent via the `ProjectedVersion` guard (dispatcher skips events where `current.ProjectedVersion >= event.Version`). Use that to close the tail:

1. `Initialize` metadata if absent (`ActiveTableName` = current static name, `Version` = 1).
2. **Create** the pending table `v2` (empty) — physical name `"{activeTableName}_v{Version+1}"` (or `_rebuild_{Version+1}`; pick one convention, see §7). Schema/GSIs cloned from the read model's registered schema.
3. `BeginReplay` → sets `ReplayInProgress = true`, `PendingTableName = v2`, `Version++` (atomic, guarded).
4. **Full replay** of the entire event history into v2 (replay override active → all writes land in v2).
5. **Catch-up loop:** re-run replay for events that arrived during step 4. Idempotent — already-applied events are no-ops; only the tail is applied. Loop until the per-pass delta is ~0.
6. **Verify** v2 vs v1 (item counts per schema, optional checksum over a key range). Abort → drop v2, `ReplayInProgress` stays false after a `BeginReplay` compensation (or add an `AbortReplay` that clears the flag + `PendingTableName`).
7. `CompleteReplay` → atomic flip `ActiveTableName = v2`. Live hosts pick up v2 within the TTL.
8. **Post-flip reconcile pass** (safety): one more idempotent catch-up now that v2 is active, covering any event written to v1 in the final window before the flip.
9. Retain v1 for rollback. Drop it later (separate command, after a soak period).

**Rollback** = flip `ActiveTableName` back to v1. v1 stayed live and current the entire time (live projectors never stopped writing it), so rollback is instant and lossless. This is the core safety property.

### 2.4 Single registration point

Every module's `AddXReadModelProjectors/Queries` calls `UseDynamoDbStore` (`ProjectionsBuilderExtensions.cs`). Registering the metadata store, the pointer snapshot, `IReplayContext`, and the metadata-table migration **inside `UseDynamoDbStore`** automatically covers **Api, QueryApi, Projectors.ReadModel, and Projectors.Search** — every host that reads or writes projections — with no per-host edits. This is the elegant equivalent of the resolver choke point on the DI side.

---

## 3. Work breakdown — `aspnetcore-platform`

All paths under `src/platform/Domain/`.

### P1. Fix & complete the metadata model + store
`Magiq.Platform.Projections.Stores.DynamoDb/Replay/Metadata/`

- **P1.1** `ReadModelTableMetadata.cs`: add `string? PendingTableName`. **Identity is the `TableId`** (rename `ReadModelName` → `TableId` per §8.1 — the row is the rotation state of a logical table, which may back several read models); drop/ignore any tenant dimension (global — see §1).
- **P1.2** `Stores/ReadModelTableMetadataStore.cs`:
  - **Bug A (key schema):** the store keys on attribute `ReadModelName`; the migration (P1.3) must create the table with **partition key `ReadModelName`** (no sort key). Align them. Do **not** silently keep `PK`/`SK`.
  - **Bug B (null contract):** `GetAsync` currently `throw`s `InvalidOperationException` when the item is missing. The resolver relies on "no row → fall back to static name," so `GetAsync` **must return `null`** when absent (matches the interface doc). Fix this.
  - **Bug C (tenantId):** the `tenantId` parameters are unused and misleading. Either remove them from the signatures or document them as ignored (global keying). Prefer removing for clarity, but that ripples to `IReadModelMetadataTableResolver` — acceptable, it's unwired.
  - Read/write `PendingTableName` in `GetAsync` (currently not read).
  - Add `GetAllAsync()` returning every metadata row — needed by the resolver snapshot refresh (one `Scan` of a tiny table).
- **P1.3** `Stores/ReadModelTableMetadataStoreMigration.cs`: create table `read-model-metadata` with PK `ReadModelName` (S), no SK. (Confirm `SchemaBuilder.CreateTableAsync` single-key overload; the projections migration uses the two-key form.)

### P2. Make the resolver rotation-aware (the load-bearing change)
`Magiq.Platform.Projections.Stores.DynamoDb/Schema/ProjectionTableNameResolver.cs`

- **P2.1** Introduce `IActiveProjectionTableSnapshot` (singleton): holds `volatile Dictionary<string,string>` (tableId → activeTableName) + `DateTimeOffset LastRefreshedUtc`; `TryGetActive(readModelName, out name)`; `RefreshAsync()` (calls `store.GetAllAsync()`); a sync `EnsureFresh()` that returns immediately and fire-and-forget refreshes when stale (TTL from options, default 10s). Guard against overlapping refreshes (a single in-flight `Task`).
- **P2.2** Introduce `IReplayContext` (singleton) with `AsyncLocal<string?>` pending override + `IDisposable BeginPending(string tableId, string pendingTable)` (keyed by `TableId`).
- **P2.3** `ProjectionTableNameResolver.Resolve(schema)` new precedence. First compute the schema's **base `TableId`** with the existing logic (`_typeTableNames[schema.ModelType]` → that name as a `TableId`, else `ProjectionsTableSchema.TableId`). Then:
  1. If `IReplayContext` has a pending override for that `TableId` → return the pending physical name.
  2. `EnsureFresh()`; if the snapshot has an active physical name for that `TableId` → return it.
  3. Fall back to existing logic (`ITableResolver.GetTableName(tableId)` — today's behavior).
  Keep the method **synchronous**. The rotation key is the **`TableId`**, computed the same way in the resolver, the snapshot, the replay context, and the orchestrator (§8.1). The old per-read-model `ReadModelMetadataTableResolver` (`typeof(TReadModel).Name`) is the wrong granularity under this decision — re-base it to take a `TableId`, or drop it (it's unwired).
- **P2.4** Add a `ProjectionRotationOptions { TimeSpan SnapshotTtl = 10s; string TableNameSuffixFormat = "_v{0}"; }` bound from config (e.g. `Platform:DynamoDB:Projections:Rotation`).

### P3. Runtime table creation for the pending table
`Magiq.Platform.Projections.Stores.DynamoDb/`

- **P3.1** Factor the single-table creation out of `ProjectionsTableMigration.cs` into a reusable `IProjectionTableProvisioner.CreateTableAsync(physicalName, IProjectionSchema, indexEntries)` so a pending table can be created at runtime with the **same PK/SK/GSIs** as the live one. `ProjectionsTableMigration` should then call the provisioner too (no behavior change at deploy).
- **P3.2** Handle "table already exists" idempotently (crash-recovery: a rotation that died after `BeginReplay` but before create/flip).

### P4. Implement the rotation orchestration
`Magiq.Platform.Projections.Stores.DynamoDb/Replay/`

- **P4.1** Replace the stub `DynamoDbProjectionReplayStore` **or** add a new `IProjectionRotationOrchestrator` (cleaner — the stub implements the orphaned `IReplayProjectionStore<TEvent>`; prefer a new interface). Orchestrator method `RotateAsync(rotationOptions, ct)` implements the §2.3 sequence steps 1–8, delegating the event replay to the existing `IProjectionReplayCoordinator` while `IReplayContext.BeginPending(...)` is active.
- **P4.2** Add `AbortAsync(readModelName)` (drop pending table, clear `ReplayInProgress`/`PendingTableName`) and `RollbackAsync(readModelName)` (re-flip active↔previous; keep the previous name in metadata or derive from `Version`).
- **P4.3** Add `VerifyAsync` hooks (item counts per schema; optional sampled checksum). Make verification a pluggable predicate so the CLI can gate `CompleteReplay` on it.
- **P4.4** Crash recovery: `RotateAsync` must be resumable — if `ReplayInProgress` is already true with a known `PendingTableName`, resume the replay/catch-up rather than erroring.

### P5. Wire registration into `UseDynamoDbStore`
`Magiq.Platform.Projections.Stores.DynamoDb/ProjectionsBuilderExtensions.cs`

- Register (singletons): `IReadModelTableMetadataStore` → `ReadModelTableMetadataStore`, `IActiveProjectionTableSnapshot`, `IReplayContext`, `IProjectionTableProvisioner`, `IProjectionRotationOrchestrator`, `IReadModelMetadataTableResolver<>` (if kept).
- `AddDynamoDbTable(ReadModelTableMetadataStore.TableId)` + `AddDynamoDbTableMigration<ReadModelTableMetadataStoreMigration>()` so **every host provisions the metadata table** at startup (same pattern as `ProjectionsTableMigration`).
- Bind `ProjectionRotationOptions`.
- **Acceptance:** Api / QueryApi / Projectors.ReadModel / Projectors.Search all resolve the new services with no per-host edits.

### P6. Abstractions
`Magiq.Platform.Projections.Abstractions/Replay/` — add `IProjectionRotationOrchestrator`, `RotationOptions`, `IReplayContext`, verification delegate. Keep `Domain` free of AWS (interfaces here, DynamoDB impls in `…Stores.DynamoDb`).

---

## 4. Bug checklist (must-fix before anything works)

1. Metadata migration key schema (`PK`/`SK`) ≠ store access pattern (now `TableId`, per §8.1). — P1.2/P1.3
2. `GetAsync` throws instead of returning `null` on missing row — breaks the fall-back-to-static path. — P1.2
3. `ReadModelTableMetadata` record lacks `PendingTableName`. — P1.1
4. `tenantId` params ignored (global keying) — remove/document; do not leave them looking per-tenant. — P1.2
5. `DynamoDbProjectionReplayStore` is 100% `NotImplementedException` — replace with real orchestrator. — P4
6. None of the metadata/rotation services registered anywhere — register via `UseDynamoDbStore`. — P5

---

## 5. Work breakdown — `magiq-media`

### M1. CLI: add rotation commands
`src/tools/Cli/Commands/Projections/`

- Keep `ProjectionsRebuildCommand` (in-place delete+replay) as-is — it remains useful for fixing a buggy projector on a small table.
- Add `ProjectionsRotateCommand` (`projections rotate --read-model <name>|all [--verify counts|checksum|none] [--dry-run] [--confirm]`):
  1. resolve `IProjectionRotationOrchestrator` in the CLI's tenant/service scope (mirror how `ProjectionsRebuildCommand` builds its scope and resolves `IProjectionReplayCoordinator`);
  2. call `RotateAsync` with progress reporting (reuse the existing `IProgress<ReplayProgress>` console reporter);
  3. gate flip on verification.
- Add `ProjectionsRollbackCommand` (`projections rollback --read-model <name>`) → `RollbackAsync`.
- Add `ProjectionsDropOldCommand` (`projections drop-old --read-model <name> [--keep 1]`) → delete retired `_vN` tables after soak.
- **Global rebuild note:** rotation is global (all tenants). `RotateAsync` should drive `IProjectionReplayCoordinator` with `ReplayOptions.TenantId = null` (scan all tenants) unless a `--tenant` filter is explicitly given for a targeted partial rebuild.

### M2. Read-model identity mapping — ✅ RESOLVED (rotate by `TableId`)
Audit complete (2026-07-24). Rotation keys on the **`TableId`** — the `tableName` string passed to `AddProjectionSchema<T>("<tableName>")` — not the read-model type. Shared physical tables already exist and must rebuild as a unit:
- `media-item-versions` ← `MediaItemVersionSummaryReadModel` **and** `MediaItemVersionDetailReadModel`
- `media-record-types` ← `RecordTypeSummaryReadModel` **and** `RecordTypeVersionDetailReadModel`
Every magiq-media projection registers an explicit `tableName`, so each read model's `TableId` is unambiguous and co-located read models share one `TableId`. The CLI selects a **table**: resolve `--read-model <name>` to its `TableId` (or accept `--table <tableId>` directly); `RotateAsync` rebuilds all read models mapped to that `TableId` together. No further per-module change beyond this mapping.

### M3. No host edits expected
Because registration rides on `UseDynamoDbStore` (P5), `hosts/Api/Startup.cs`, `hosts/QueryApi/Startup.cs`, `hosts/Projectors.ReadModel/ServiceCollectionExtensions.cs`, and `hosts/Projectors.Search/ServiceCollectionExtensions.cs` should need **no changes**. Verify after wiring: each host boots, provisions `read-model-metadata`, and resolves live tables identically to today (no metadata rows yet → static names).

### M4. CDK — `cdk-magiq-media`
- **Metadata table:** provision it in `lib/constructs/dynamodb/platform-tables.construct.ts` and add it to
  `PlatformTables.all` — PK `TableId` (S), no SK, on-demand, CMK, PITR, matching the other platform tables.
  `platform.all` already flows into the `grantReadWriteData(allTables)` / `grantReadData(readOnlyTables)`
  loops, so data-plane grants come for free.
- **Deployed-host IAM:** after a flip, live hosts read/write the `_v{n}` table, which their exact-ARN grants
  don't cover. Widen their DynamoDB data-plane grants to the projection-table namespace (wildcard
  `table/media-*` + `/index/*`) so the cutover works without a redeploy. **(Open decision — scope tradeoff.)**
- **Separate replay-tool IAM:** control-plane (`CreateTable`, `DeleteTable`, `DescribeTable`,
  `UpdateContinuousBackups`, `TagResource`/`UntagResource`) + data-plane + `Scan` on `table/media-*`, plus
  `kms:CreateGrant`/`GenerateDataKey`/`Decrypt` on the CMK. Role placement depends on where the tool runs.
  **(Open decision.)**
- **Deletion protection off for `_v{n}`** — the replay tool must create them unprotected, else abort/drop
  can't `DeleteTable`. Controlled by the tool's `TableMigrationOptions`.

---

## 6. Testing strategy

- **Platform unit tests** (`aspnetcore-platform` test projects):
  - Resolver precedence: replay override > active snapshot > static fallback; no-row → static.
  - Snapshot TTL staleness + single-flight refresh; concurrency safety.
  - Store: atomic `BeginReplay`/`CompleteReplay` conditional writes (happy path + guard rejection); `GetAsync` returns null on missing; `GetAllAsync`.
  - Orchestrator: full rotate happy path against **DynamoDB Local**; crash-recovery resume; abort; rollback; verification gate blocks flip on mismatch.
- **magiq-media integration tests** (`tests/integration`, `Media.IntegrationTests.Shared` fixtures, DynamoDB Local):
  - Seed events → rotate Catalog `MediaItem` read model → assert live queries return identical results before and after flip, and that a write landing during replay is present post-flip (tail closure).
  - Rollback restores v1 exactly.
- **Manual/staging runbook rehearsal** on `dev` before documenting for `qa`.

**Status (2026-07-26):** platform unit tests (resolver precedence, snapshot TTL/single-flight, store guards, orchestrator abort/rollback/verify/resume/drop-old) and platform **integration** tests against DynamoDB Local — `ReadModelTableMetadataStoreIntegrationTests` (store atomicity + conditional-check guards) and `ProjectionRotationOrchestratorIntegrationTests` (full rotate → flip → snapshot, rollback, verification-fail → abort+drop) — implemented and passing. magiq-media end-to-end integration test (§12.8) implemented — `CollectionRotationE2ETests` (Catalog.IntegrationTests, dedicated `RotationE2E` collection): seeds collections via the live API, rotates `media-collections` using the operator tool's own `RotationHost`+`RotationRunner` against the same DynamoDB Local container, then proves the live list query follows the flip to `media-collections_v2` and back on rollback (via a base-vs-pending row-count divergence, polling one snapshot TTL). Tool unit tests (§12.8) still optional (would need a tools test project). Dev runbook written (`src/tools/ProjectionReplay/RUNBOOK.md`).

---

## 7. Conventions to lock before coding

- **Pending table name format:** `"{active}_v{n}"` (recommend) vs `"{active}_rebuild_{n}"` (the platform's commented pseudocode). Pick one; put it in `ProjectionRotationOptions.TableNameSuffixFormat`. Watch the DynamoDB 255-char limit and the `^[a-zA-Z0-9_.-]{1,255}$` `TableName` regex.
- **Rotation key:** `TableId` (logical table identity) — RESOLVED, see §8.1 / M2.
- **Snapshot TTL default:** 10s (flip latency ceiling).
- **Metadata table name:** `read-model-metadata` (unchanged), subject to the global `TableSuffix`.

---

## 8. Open decisions (resolve at kickoff)

1. **Rotation unit — read-model vs table.** ✅ **RESOLVED 2026-07-24: key rotation by `TableId` (the stable logical table identity)** — not read-model type name, not physical table name. Verified: read models already share physical tables (`media-item-versions` and `media-record-types` each back two read models, M2), so read-model keying would orphan co-located siblings; and the physical name is what a rotation *changes*, so it can't be the key. `TableId` is stable across renames and shared by co-located read models. Rotating a `TableId` rebuilds all read models mapped to it, together, and keeps multiple-projections-per-table support intact. See Decision addendum (top).
2. **Verification depth for the flip gate.** Item counts (cheap, fast) vs sampled checksum (stronger, slower). **Recommendation: counts by default, checksum opt-in via `--verify checksum`.**
3. **Runtime table creation vs CDK provisioning** (M4). **Recommendation: runtime creation** for true no-deploy rotation; revisit only if infra policy forbids app-created tables.
4. **Keep or delete the orphaned `IReplayProjectionStore<TEvent>` / stub `DynamoDbProjectionReplayStore`.** **Recommendation: delete the stub, add a purpose-built `IProjectionRotationOrchestrator`** rather than forcing the old shape.
5. **Global-only now, or leave a seam for `TableNamePerTenant`.** **Recommendation: global-only; leave the read-model-name key as the seam, don't build per-tenant.**

---

## 9. Suggested PR sequence (each independently reviewable/mergeable)

**aspnetcore-platform**
1. `feature/platform/projection-rotation-metadata` — P1 (record + store + migration, bug fixes 1–4) + unit tests. No behavior change to live paths.
2. `feature/platform/projection-rotation-resolver` — P2 (snapshot, replay context, rotation-aware `Resolve`) + P2.4 options + tests. Live paths unchanged when no metadata rows exist (assert this).
3. `feature/platform/projection-rotation-orchestrator` — P3 (provisioner) + P4 (orchestrator, abort/rollback/verify/resume) + P6 abstractions + tests.
4. `feature/platform/projection-rotation-di` — P5 (`UseDynamoDbStore` registration + metadata migration) + host smoke tests.

**magiq-media** (after platform packages publish; versions via `Directory.Packages.props`)
5. `feature/chase/<ticket>-projection-rotation-cli` — M1 commands + M2 identity audit + integration tests.
6. `feature/chase/<ticket>-projection-rotation-verify` — host boot verification (M3), dev runbook, optional CDK (M4).

Follow repo branching conventions (`feature/<user>/<ticket>-<slug>`, cut from `develop`). Spec/ADR note: capture the rotation design as an ADR in `magiq-media/docs/adrs/` in the same PR as M1.

---

## 10. Definition of done

- Operator runs `projections rotate --read-model <X> --confirm` against **dev** while the app serves traffic; queries stay correct throughout; after flip they read from `<X>_v2`; a write issued mid-rotation is present post-flip; **no redeploy occurred**.
- `projections rollback --read-model <X>` returns to `<X>` (v1) instantly with no data loss.
- Read models that are never rotated are byte-for-byte unaffected (static names, no metadata rows).
- Metadata table auto-provisioned by every projection-using host at startup.
- ADR merged; dev runbook written.

---

## 11. magiq-media — adopting the updated platform (2026-07-25)

Prerequisite: the platform packages carrying the rotation subsystem (PR1 metadata store, PR2
resolver/snapshot/replay-context, PR3 provisioner/orchestrator/verifier) are published. This section
supersedes the old M1 (which assumed in-process CLI commands in the deployed app).

### 11.1 Platform version bump
- Bump `MagiqPlatformVersion` (`Directory.Packages.props` — every `Magiq.Platform.*` / `Magiq.AspNetCore.*`
  package is pinned to `$(MagiqPlatformVersion)`) to the release that contains the rotation subsystem.
  One property, whole solution.

### 11.2 Platform prerequisite — register `ITableSchemaBuilder` (the DI gap)
- The orchestrator injects `ITableSchemaBuilder`, which nothing registers today: `TableMigrationManager`
  constructs `new TableSchemaBuilder(...)` by hand and assigns it to each migration's `SchemaBuilder`
  property — it never enters the container. So resolving `IProjectionRotationOrchestrator` throws.
- **Fix in the platform**, not the app: add `services.TryAddTransient<ITableSchemaBuilder, TableSchemaBuilder>()`
  to `AddDynamoDbMigrations` (`Magiq.AspNetCore.DynamoDb.Migrations/MagiqPlatformBuilderExtensions.cs`,
  both the per-tenant and host-level branches). `TableSchemaBuilder`'s ctor deps (`IAmazonDynamoDB`,
  `ISchemaCommandRunner`, `ITableResolver`, `IEnumerable<DynamoDbContextType>`) are all already registered
  there. Any host/tool that calls `AddDynamoDbMigrations` then resolves the orchestrator. Deployed hosts
  get the registration too — harmless, they never resolve it. Ship this in the same platform release.

### 11.3 Deployed hosts — no code changes
- Rotation services ride on `UseDynamoDbStore`, invoked transitively by the module projector
  registrations already present in Api/QueryApi/Projectors.* (`AddCatalogReadModelProjectors`, etc.).
  Hosts get the resolver, snapshot, replay context, and metadata store automatically — no Startup edits.
- The `read-model-metadata` table: descriptor registered by `UseDynamoDbStore`; the physical table is
  created by `ProjectionsTableMigration` at startup and provisioned by CDK. With `Platform__DynamoDB__TableSuffix`
  empty and no prefix, the physical name resolves to `read-model-metadata` — matching the CDK table.
  No app-side naming/mapping needed (decision 2026-07-25: keep the name as-is).
- Verify after the bump: each host boots, provisions `read-model-metadata`, and resolves live tables
  exactly as before (no metadata rows → static names).

### 11.4 CDK (done)
- `read-model-metadata` added to `lib/constructs/dynamodb/platform-tables.construct.ts` + `PlatformTables.all`;
  `media-*` data-plane wildcard added to the host roles for the post-flip cutover. No further CDK for adoption.

---

## 12. Operator replay tool — implementation plan (2026-07-25)

A separate, operator-run console app that performs blue-green rotations against a deployed environment.
Kept out of the deployed services (replay is not run in-process) **and** out of the general-purpose
`src/tools/Cli` — so the elevated DynamoDB control-plane credentials stay on a minimal, single-purpose
tool. (Alternative, if isolation isn't wanted: add the same commands to the existing `Cli` — the command
logic below is identical; only the host wiring differs.)

### 12.1 Project
- New console project `src/tools/ProjectionReplay` (`Magiq.Media.ProjectionReplay`), added to the solution
  under the `tools` folder.
- Host modelled on `src/tools/Cli/HostFactory.cs`: `Host.CreateDefaultBuilder().UseNLogHost()`
  → `ConfigureAppConfiguration(AddMagiqMediaSecrets(env))` → `ConfigureServices(...)`. Reuse the `.env` /
  `--env` resolution and `AddMagiqMediaSecrets` from `Media.Shared.Configuration`, and the SDK credential
  chain (as the Cli does).
- Project references — mirror `Cli.csproj`: the Catalog / AssetManagement / Metadata read-model
  infrastructure + read-model projects, plus the write-model infrastructure, so `AddXReadModelProjectors()`
  wire the schemas and projectors (and thus `UseDynamoDbStore` + rotation services).
- Package references: platform packages via `$(MagiqPlatformVersion)`, plus
  `Magiq.AspNetCore.DynamoDb.Migrations` (for `AddDynamoDbMigrations`) and `Magiq.Platform.DynamoDb.Migrations`
  (only if registering `TableSchemaBuilder` in the app instead of via the 11.2 platform fix), `AWSSDK.DynamoDBv2`,
  `DotNetEnv`, `Magiq.Platform.ConsoleHost`, `Magiq.Platform.Tenants(.DynamoDb)`.

### 12.2 DI / host
- `services.AddMagiqPlatform().AddDynamoDb().AddTenants(t => t.AddDynamoDbTenantStore(...)).AddConsoleHost();`
- Module projector registrations (`AddCatalogReadModelProjectors()`, `AddAssetManagementReadModelProjectors()`,
  `AddMetadataReadModelProjectors()`, plus the write-model command/projector setup the rebuild path uses) →
  brings in `UseDynamoDbStore` and the rotation services, including the scoped `IProjectionRotationOrchestrator`.
- `services.AddDynamoDbMigrations(runPerTenant: false)` → registers `ISchemaCommandRunner` and the migration
  manager. With the 11.2 platform fix, this makes `ITableSchemaBuilder` resolvable → the orchestrator resolves.
- `services.AddInProcessMessageBus();` (as the rebuild path does — domain events dispatched to projectors
  without SNS/SQS).

### 12.3 Table → aggregate registry
- Rotation is keyed by `TableId`; replay is driven by aggregate types. Provide a registry mapping each
  rotatable projection table to the aggregate(s) whose events feed it (source the aggregate CLR types from
  the module namespaces, exactly as `ProjectionsRebuildCommand` does):

  | Table(s) | Aggregate |
  |----------|-----------|
  | media-collection, media-collections | Collection |
  | media-folder, media-folders, media-folder-children | Folder |
  | media-item, media-items, media-item-versions | MediaItem |
  | media-profile, media-profiles, media-profile-versions, media-profile-version | MediaProfile |
  | media-asset, media-assets | Asset |
  | media-registration, media-registrations | Registration |
  | media-record-type, media-record-types, media-record-type-versions | RecordType |
  | media-change-request, media-change-requests, media-change-request-comments | ChangeRequest |
  | media-processing-job, media-processing-jobs | ProcessingJob |

  (`media-item-versions` and `media-record-types` each back two read models — the whole physical table
  rotates as a unit, which is exactly why the rotation key is the `TableId`.)

### 12.4 Commands
- `rotate --table <name> [--verify counts|none] [--catch-up N] [--tenant <name>] [--dry-run] [--confirm]`
  - resolve table → aggregate types; resolve `IProjectionRotationOrchestrator`;
    `RotateAsync(new RotationOptions { TableId, Verification, CatchUpPasses, CountTolerance }, replayCallback)`.
    The **replay callback** (`Func<RotationReplayContext, CancellationToken, Task>`) enumerates tenants and, in
    each tenant scope, sets the write override via `IReplayContext.BeginPending` when `ctx.RedirectToPending`
    and drives `IProjectionReplayCoordinator.ReplayAsync` (mirror `ProjectionsRebuildCommand`'s scope +
    `IConsoleContextHolder`). Print the `RotationResult` (Flipped / ActiveTableName / PreviousTableName / Version / Message).
  - gate on `--confirm` (it creates a table and flips live reads/writes).
- `rollback --table <name> [--confirm]` → `RollbackAsync` (instant swap back to the previous physical table).
- `abort --table <name>` → `AbortAsync` (clears in-progress + drops the pending table).
- `drop-old --table <name> [--keep 1] [--confirm]` → delete retired `_v{n}` tables after a soak period.

### 12.5 Tenancy / execution scope — ✅ RESOLVED (per-tenant callback)
Verified against the code: the event scanner's `TenantId = null` prefix (`AGG#{type}#ID#`) only matches
**non-tenant-scoped** aggregates, so a global pass rebuilds nothing for magiq-media's `TENANT#…` aggregates.
The tool therefore rebuilds **per tenant** into the shared pending table. The platform orchestrator was
refactored to take a replay **callback**: it owns provision → begin → verify → flip → reconcile and calls the
callback (full + catch-up pre-flip, once post-flip). The callback loops all tenants (`ITenantDirectory.ListAsync`
→ `ITenantHost.GetScopeAsync`), and inside each tenant scope resolves `IReplayContext` + the coordinator from
the **same** scope and sets `BeginPending` when `ctx.RedirectToPending` — correct under per-tenant DI
containers (override and write path share one `IReplayContext`). `RotationOptions` no longer carries
`AggregateTypes`/`TenantId`/`Progress`; those live in the callback.

### 12.6 drop-old discovery
- Retired tables are `{base}_v{n}` for versions below the current. Prefer deriving their names from the
  metadata row (`Version` / `PreviousTableName`) so no `dynamodb:ListTables` (`*`-scoped) is needed; keep the
  newest `--keep`. Delete via `ITableSchemaBuilder.DeleteTableAsync` (requires deletion protection off — 12.7).

### 12.7 IAM / run model
- Operator-run with the elevated role carrying the rotation policy (control-plane + `media-*` data-plane +
  `read-model-metadata` + CMK) documented alongside M4. Not deployed by the app stack.
- **Deletion protection OFF for `_v{n}`:** configure `AddDynamoDbMigrations` / `TableMigrationOptions` so the
  provisioner creates the transient versioned tables unprotected — otherwise `abort` / `drop-old` cannot
  `DeleteTable`. (Live tables provisioned by CDK keep their protection; only the tool's runtime tables differ.)

### 12.8 Testing
- Integration (DynamoDB Local / Testcontainers, `Media.IntegrationTests.Shared` fixtures): rotate a seeded
  table end-to-end → live queries identical before and after the flip; a write landing during replay is
  present post-flip (tail closure); rollback restores v1; abort drops the pending table.
- Unit: `--confirm` / `--dry-run` gating; table→aggregate resolution; unknown-table handling.

### 12.9 Definition of done
- Operator runs `rotate --table media-item-versions --confirm` against **dev** while the app serves traffic;
  queries stay correct throughout; after the flip they read from `media-item-versions_v2`; a write issued
  mid-rotation is present post-flip; **no redeploy occurred**. `rollback --table media-item-versions` returns
  instantly with no data loss. Retired `_vN` tables dropped via `drop-old` after a soak. Dev runbook written.

**Status (2026-07-26):** tool + commands (rotate/rollback/abort/drop-old) built; dev runbook written (`src/tools/ProjectionReplay/RUNBOOK.md`); rotation design captured as an ADR section in `magiq-media/docs/adrs/persistence-and-eventing.md` (§Blue-Green Projection Table Rotation) and indexed in `docs/adrs/README.md`. Remaining before DoD is fully met: CDK deploy to dev, attach operator IAM policy, and the live dev DoD run.

### 12.10 Suggested PR (after the platform packages publish)
- `feature/chase/<ticket>-projection-replay-tool` — new `src/tools/ProjectionReplay` project (12.1–12.7) +
  integration tests (12.8) + dev runbook. Depends on 11.1 (version bump) and 11.2 (platform `ITableSchemaBuilder`
  registration).

### 12.11 Risks / open items
- ✅ Global vs per-tenant replay scope (12.5) — resolved: per-tenant callback (the `TenantId = null` scan matches no tenant-scoped aggregates).
- Count-verification tolerance under concurrent live writes — set `CountTolerance` or rely on the post-flip
  reconcile pass.
- `drop-old` name discovery — prefer metadata-derived names over `ListTables` to avoid a `*`-scoped action.
