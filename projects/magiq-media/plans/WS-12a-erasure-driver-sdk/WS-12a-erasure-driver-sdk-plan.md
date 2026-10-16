---
id: MM-024
type: plan
project: magiq-media
workstream: WS-12a-erasure-driver-sdk
repo: mgq-dotnet-platform
tags: [mgq-dotnet-platform, sdk, erasure, kms, retention]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-024-WS-12a-erasure-driver-sdk]
pr: https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/51
merge-sha: 8bbe6ade
shipped: 2026-10-13
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F041-erasure-key-store-and-retry-driver.md and INDEX.md#WS-12; no separate review document.
---

# WS-12a — Erasure retry driver SDK portion

**Target repo:** `mgq-dotnet-platform` — `D:\source\github\sprbrk-standard\mgq-dotnet-platform`
**Depends on:** none
**Unblocks:** MM-043 (WS-12b — `MaintenanceScanner` erasure-retry pass; also waits on MM-072 WS-06 rename)

Delivers F041 SDK portion: generic erasure-retry primitive. `IErasureDriver` + per-`TargetKind` handler strategy + KMS `ScheduleKeyDeletion` wrapper + pending-record contract + retry policy. **BC-agnostic.** Table name, KMS alias prefix, metric namespace, scope-type vocabulary = host concerns bound through options; no `media-*` identifiers in SDK code.

## BC-agnostic contract — scope correction (2026-10-13)

`mgq-dotnet-platform` is consumed by every Magiq bounded context (and future ones). The spec's `media-erasure-pending` table name, `media/erasure/{scope-type}/{scope-id}` KMS alias prefix, scope-type vocabulary (`registration` / `asset` / `comment` / `signing-session` / `mediaitem`) and `MediaErasurePending.*` metric names are magiq-media's concrete bindings — they belong in the magiq-media host (WS-12b), not SDK code. SDK publishes the mechanism + the config seams the host binds. Mirrors the pattern established by `IOutboxStore` (generic contract, host-named S3 keys), `IEventStore` (generic, host-named table) and `AddMagiqMetrics` (generic Meter names, host EMF namespace mapping).

| Repo | Owns |
|---|---|
| SDK (this plan) | `IErasureDriver`, `IErasureHandler<TKind>`, `IKmsKeyReleaseService`, `ErasurePendingRecord` (generic shape), outcome types, retry policy, scanner-pass base, Decrypt-exception wrapper, transactional write via `IEventStoreTransactionAccessor`, `erasure.*` counters on `Magiq.Platform.Erasure` meter, config options: `ErasurePendingTableOptions`, `KmsKeyAliasOptions`, `ErasureRetryOptions` |
| magiq-media host (WS-12b, MM-043) | Binds `TableName = "media-erasure-pending"`, `AliasPrefix = "media/erasure"`; registers per-aggregate `IErasureHandler<TKind>` for asset / event-stream / snapshot / search-doc; EMF namespace maps `Magiq.Platform.Erasure` → `MagiqMedia/Erasure` via WS-58a bridge |
| cdk-magiq-media | Provisions `media-erasure-pending` table + PITR disabled + IAM + alarms on `MediaErasurePending.*` |

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-dotnet-platform`. Paste:

> Picking up WS-12a (plan MM-024). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-12a-erasure-driver-sdk\WS-12a-erasure-driver-sdk-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F041-erasure-key-store-and-retry-driver.md`.
>
> **BC-agnostic surface.** No `media-*` strings in SDK code. Deliver `IErasureDriver.AttemptErasureAsync` returning `Succeeded | Retryable | Terminal`, pluggable `IErasureHandler<TKind>` per app-defined `TargetKind` string, `IKmsKeyReleaseService.ScheduleKeyDeletionAsync(keyId, pendingWindowDays, ct)` wrapper, `ErasurePendingRecord` shape, retry policy with backoff (`MaxAttempts` default 10), terminal publishes `ErasureFailedPermanent` via `IDomainEventPublisher`. Config seams: `ErasurePendingTableOptions.TableName`, `KmsKeyAliasOptions.Prefix`, `ErasureRetryOptions`. Counters on `Magiq.Platform.Erasure` meter, no `MediaErasurePending.*` names.
>
> Table provisioning + alias binding + handler registrations + metric namespace mapping = magiq-media host (WS-12b). PR to `mgq-dotnet-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F041 § Required-shape, § Detection signals, § Implementation requirements
- [ ] Confirm `mgq-dotnet-platform` has no `IErasureDriver` type today
- [ ] Confirm no `media-*` identifier appears in SDK code before edits (grep baseline)

## Phase 1 — Pending record + options
- [ ] `ErasurePendingRecord` in `Magiq.Platform.Erasure`: `TenantId`, `TargetKind` (string), `TargetId` (string), `KmsKeyId`, `ScheduledAt`, `AttemptCount`, `LastError`, `LastAttemptAt`. **No `media-*` members.**
- [ ] `ErasurePendingTableOptions.TableName` (host-bound; SDK has no default naming it `media-*`)
- [ ] PITR-exclusion attribute convention — written by SDK, enforced in CDK by host
- [ ] Transactional write path via `IEventStoreTransactionAccessor` — pending-row insert enlists on the ambient event-store transaction (same primitive as outbox WS-21a)

## Phase 2 — Driver interface
- [ ] `IErasureDriver.AttemptErasureAsync(record, ct)` → `Result<ErasureOutcome, DomainError>`
- [ ] Outcomes: `Succeeded`, `Retryable(reason)`, `Terminal(reason)`
- [ ] Pluggable per `TargetKind`: `IErasureHandler<TKind>` strategies via DI; SDK ships none (host registers)
- [ ] `IErasureScannerPass` base — magiq-media's `MaintenanceScanner` composes it (WS-12b)

## Phase 3 — KMS key-release helper
- [ ] `IKmsKeyReleaseService.ScheduleKeyDeletionAsync(keyId, pendingWindowDays, ct)` — accepts raw `keyId`; **no alias construction in SDK**
- [ ] `KmsKeyAliasOptions.Prefix` — host-bound (`"media/erasure"` for magiq-media); SDK offers an alias-builder helper taking `(prefix, scopeType, scopeId)` for host convenience, but driver internals never read a prefix
- [ ] Validates pending window (7–30 days per AWS KMS)
- [ ] Idempotent: already-scheduled key returns success
- [ ] Decrypt-exception wrapper: `KMSInvalidStateException` / `NotFoundException` on pending-deletion/deleted key → `erased` sentinel; other errors raise (BC-agnostic — any consumer of SDK encrypted payloads uses it)

## Phase 4 — Retry policy + metrics
- [ ] `ErasureRetryOptions`: `MaxAttempts` (10), `BaseBackoff`, `MaxBackoff`
- [ ] Driver computes next-attempt eligibility
- [ ] After `MaxAttempts`: record `Terminal`; publish `ErasureFailedPermanent` via `IDomainEventPublisher` (payload carries `TargetKind` + `TargetId` + `LastError` — no media-named members)
- [ ] Counters on `Magiq.Platform.Erasure` meter: `erasure.pending.depth` (gauge), `erasure.pending.oldest_age_seconds` (gauge), `erasure.schedule_key_deletion.failed` (counter), `erasure.attempts` (counter with `outcome` tag). **No `MediaErasurePending.*` names in SDK** — host EMF namespace resolver (WS-58a) maps the meter → `MagiqMedia/Erasure` and operators/dashboards see spec names on CloudWatch.
- [ ] `AddMagiqErasure(this IServiceCollection, Action<ErasureOptions>?)` DI entry point registers driver + options + meter

## Phase 5 — Tests
- [ ] Unit: dispatches to registered handler by `TargetKind` (string, arbitrary)
- [ ] Unit: retryable outcome schedules next attempt with backoff
- [ ] Unit: terminal outcome publishes `ErasureFailedPermanent`
- [ ] Unit: PITR-exclusion attribute set on writes
- [ ] Unit: Decrypt wrapper distinguishes `KMSInvalidStateException` vs throttle
- [ ] Unit: alias-builder helper produces `{prefix}/{scopeType}/{scopeId}` given options; driver works without using it (helper is opt-in host convenience)
- [ ] Unit: **no `media-*` string literal in SDK test fixtures** (fixtures use `test-pending` / `TestKind` / `test/erasure/...`)

## Phase 6 — Package + ship
- [ ] Bump `Magiq.Platform.*` version (deferred per batched-bump policy)
- [ ] PR to `mgq-dotnet-platform/main`

## Phase 7 — Close
- [ ] F041: `status: shipped (SDK portion — generic contract; magiq-media binding tracked in WS-12b)`
- [ ] platform-capabilities/INDEX.md: WS-12 split — `WS-12a shipped`, `WS-12b open (waits on MM-072)`
- [ ] INTEGRATION-BACKLOG: MM-043 (WS-12b) `Dep status: shipped (external SDK); still blocked on MM-072 (WS-06 rename)`

## Session log
- 2026-10-08: plan drafted
- 2026-10-13: BC-agnostic scope correction — media-prefixed table name, KMS alias prefix, scope-type vocab, metric namespace moved to WS-12b host binding; SDK ships generic contract + config seams. Pattern mirrors outbox / event-store / metrics.
- 2026-10-13: SDK implementation landed on local branch (not yet pushed/merged). Four new projects under `src/platform/Erasure/`:
  - `Magiq.Platform.Erasure.Abstractions` — `ErasurePendingRecord`, `ErasureOutcome` (`Succeeded`/`Retryable`/`Terminal`), `ErasureFailedPermanent` IDomainEvent, `IErasureHandler`, `IErasureDriver`, `IErasurePendingStore`, `IKmsKeyReleaseService` + `KmsKeyReleaseResult`/`KmsKeyReleaseClassification`, `IErasureScannerPass`, `IErasureBuilder`, `KmsKeyUnusableException`, `KmsKeyReleaseResultExtensions.ToOutcome()`, Options (`ErasureOptions` + `ErasurePendingTableOptions`/`KmsKeyAliasOptions`/`ErasureRetryOptions`).
  - `Magiq.Platform.Erasure` — `ErasureDriver`, `ErasureScannerPass`, `ErasureHandlerRegistry` (one handler per `TargetKind`, duplicate = `InvalidOperationException`), `ErasureRetryPolicy` (exponential backoff + jitter + `ShouldPark`), `ErasureMetrics` on `Magiq.Platform.Erasure` meter (counters `erasure.attempts`, `erasure.schedule_key_deletion.failed`; gauges `erasure.pending.depth`, `erasure.pending.oldest_age_seconds`), `AliasBuilder.For(prefix, scopeKind, scopeId)` opt-in helper, `KmsDecryptClassifier` static classifier (reflection-free, reads `Exception.GetType().Name`), `InMemoryErasurePendingStore` (txn-enlist on `InMemoryEventStoreTransaction`), `AddMagiqErasure(IServiceCollection, Action<ErasureOptions>?)` DI entry.
  - `Magiq.Platform.Erasure.DynamoDb` — `DynamoDbErasurePendingStore` (txn-enlist via `DynamoDbEventStoreTransaction.AddGenericWriteItem`; `DescribeTable.ItemCount` for depth gauge), `DynamoDbErasurePendingTableSchema` (PK `TENANT#{tid}#ERASURE#{kind}#{id}` + GSI `GSI_DueAt` keyed on constant `DUE` partition + `ScheduledAt` sort), `DynamoDbErasurePendingTableMigration`, `UseDynamoDb(tableName)` builder extension (binds `TableName` option + registers table id + migration).
  - `Magiq.Platform.Erasure.Aws` — `AwsKmsKeyReleaseService` (validates 7–30 day window; classifies `KMSInvalidStateException`/`NotFoundException` → `AlreadyScheduled`, `LimitExceededException`/`KMSInternalException`/`DependencyTimeoutException` → `Transient`, throttling via error code → `Transient`, else `Terminal`), `UseAwsKms()` builder extension.
  - Package: `AWSSDK.KeyManagementService 4.0.3.14` added to `Directory.Packages.props`.
  - Tests: `tests/Magiq.AspNetCore.Tests/Erasure/*` — 34 tests pass. Covers driver dispatch, succeeded/retryable/terminal/park paths, no-handler-registered → terminal, handler-throws → retryable, metric emission, alias builder shape + input validation, KMS classifier mapping, registry duplicate rejection, in-memory store surface + txn enlistment + rollback-leaves-unchanged, result-to-outcome mapping. No `media-*` string literal anywhere in SDK or tests.
  - Solution build clean: 0 errors, 12 pre-existing warnings in samples/tests (unrelated).
  - `Magiq.Platform.*` version bump deferred per batched-bump policy.
  - **Next:** push branch, open PR to `mgq-dotnet-platform/main`. After merge: flip F041 to shipped (SDK portion), move WS-12 row in `platform-capabilities/INDEX.md` to § Shipped, update INTEGRATION-BACKLOG for MM-043.
- 2026-10-13: PR #51 merged (merge commit `4024bd08`, feature commit `8bbe6ade`). Plan status flipped shipped. F041 flipped to `shipped (SDK portion)` with pr/shipped frontmatter. `docs/dependency-gaps/platform-capabilities/INDEX.md` WS-12 row split — WS-12a moved to § Shipped, WS-12b held in § Open (still blocked on MM-072 WS-06 rename). INTEGRATION-BACKLOG MM-024 moved to § Shipped (`8bbe6ade` / #51). MM-043 (WS-12b) stays `new` — external SDK dep now shipped, still waits on MM-072. Tower item for MM-024 flipped new→done. Residue: magiq-media CLAUDE.md "Erasure-retry driver" bullet keeps citing F041 (narrowed — SDK shipped, consumer binding still open under WS-12b); bullet drops when WS-12b ships.
