---
id: MM-043
type: plan
project: magiq-media
workstream: WS-12b-erasure-maintenance-pass
repo: magiq-media
tags: [magiq-media, maintenance-scanner, erasure, retention]
consumes: []
blocked-by-external: [MM-024, MM-072]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-12 F041.
---

# WS-12b — `MaintenanceScanner` erasure-retry pass + domain integration

**Target repo:** `magiq-media`
**Depends on:** MM-024 (WS-12a SDK — BC-agnostic erasure primitive + options), MM-072 (WS-06 — `TimeoutScanner` → `MaintenanceScanner` rename)
**User policy gate:** no magiq-media code change until all external deps ship.

## Scope — SDK is BC-agnostic; host owns names

WS-12a SDK (MM-024) ships generic `IErasureDriver` + `IErasureHandler<TKind>` + `IKmsKeyReleaseService` + `IErasureScannerPass` + options (`ErasurePendingTableOptions`, `KmsKeyAliasOptions`, `ErasureRetryOptions`, meter `Magiq.Platform.Erasure`). All `media-*` identifiers (`media-erasure-pending` table name, `media/erasure/{scope-type}/{scope-id}` KMS alias prefix, scope-type vocab, `MediaErasurePending.*` CloudWatch metric names) are host-side bindings landed here.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-12b (plan MM-043). SDK (MM-024) ships generic `IErasureDriver` + options; `MaintenanceScanner` (MM-072) rename shipped. magiq-media binds names.
>
> Call `AddMagiqErasure` on `MaintenanceScanner` host with `TableName = "media-erasure-pending"`, `AliasPrefix = "media/erasure"`. Register scope types (`registration`, `asset`, `comment`, `signing-session`, `mediaitem`). Register `IErasureHandler<TKind>` per aggregate (`AssetErasureHandler`, `EventStreamErasureHandler`, `SnapshotErasureHandler`, `SearchDocErasureHandler`). Compose SDK's `IErasureScannerPass` into `MaintenanceScanner.ErasureRetryPass`. Map `Magiq.Platform.Erasure` counters → `MagiqMedia/Erasure` EMF namespace with per-counter rename (→ `MediaErasurePending.QueueDepth` / `.OldestAttemptAge` / `.FailureRate`).
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-024 + MM-072 shipped
- [ ] Confirm `media-erasure-pending` table provisioned in `cdk-magiq-media`
- [ ] Confirm WS-58a EMF bridge available on magiq-media Lambda hosts (metric rename needs it)

## Phase 1 — Options binding + DI entry
- [ ] `MaintenanceScanner` host program: `AddMagiqErasure(o => { o.Table.TableName = "media-erasure-pending"; o.KmsAlias.Prefix = "media/erasure"; o.Retry.MaxAttempts = 10; })`
- [ ] Scope-type constants in a magiq-media `ErasureScopeTypes` static class: `Registration`, `Asset`, `Comment`, `SigningSession`, `MediaItem` — passed as `TargetKind` strings when erasure handlers write rows and when driver dispatches
- [ ] Per-scope `KmsKeyAlias` resolver uses SDK `AliasBuilder.For(prefix, scopeType, scopeId)` → produces `media/erasure/{scope-type}/{scope-id}`

## Phase 2 — Per-`TargetKind` handlers
- [ ] `AssetErasureHandler : IErasureHandler<"asset">`: KMS schedule-key-deletion for the asset's scope key; cleanup = handled through crypto-shred, not explicit S3 delete
- [ ] `EventStreamErasureHandler : IErasureHandler<"event-stream">`: KMS schedule-key-deletion for the stream's scope key
- [ ] `SnapshotErasureHandler : IErasureHandler<"snapshot">`: KMS schedule-key-deletion for the snapshot's scope key (same scope as owning aggregate)
- [ ] `SearchDocErasureHandler : IErasureHandler<"search-doc">`: KMS schedule-key-deletion for the search doc's scope key
- [ ] All four register through DI as `IErasureHandler<TKind>` with matching `TargetKind` string

## Phase 3 — Write-model wiring (`*PersonalDataErased` → pending row)
- [ ] Each erase command handler enlists pending-row insert on ambient `IEventStoreTransactionAccessor` so event append + pending row commit atomically (same primitive as outbox): `EraseRegistrationPersonalData`, `EraseAssetPersonalData`, `RedactComment`, `EraseSigningSessionPersonalData`, `EraseMediaItemPersonalData`
- [ ] `UseTransactionalOutbox()` on `IWriteModelBuilder` already opts the module in — pending-row insert reuses the same ambient-txn pattern

## Phase 4 — `MaintenanceScanner.ErasureRetryPass`
- [ ] Compose SDK's `IErasureScannerPass` into `MaintenanceScanner` on 5-minute EventBridge cadence (per `operations.md` § Standing Reconciliation)
- [ ] Per-row scanner-execution-context from WS-15a factory, invoke `IErasureDriver.AttemptErasureAsync`
- [ ] `Succeeded` → SDK deletes row
- [ ] `Retryable` → SDK updates `AttemptCount` + `LastError` + `LastAttemptAt`
- [ ] `Terminal` → SDK publishes `ErasureFailedPermanent` via `IDomainEventPublisher`

## Phase 5 — Metric namespace mapping (EMF bridge)
- [ ] Extend magiq-media's EMF resolver (WS-58c `AddMagiqMetrics` config) to map `Magiq.Platform.Erasure` → `MagiqMedia/Erasure`
- [ ] Per-counter rename: `erasure.pending.depth` → `MediaErasurePending.QueueDepth`, `erasure.pending.oldest_age_seconds` → `MediaErasurePending.OldestAttemptAge`, `erasure.schedule_key_deletion.failed` → ratio aggregator → `MediaErasurePending.FailureRate`
- [ ] Alarm thresholds per `operations.md` § Observability (P3 queue-depth, P2 oldest-attempt > 1h, P2 failure rate > 5% over 10m) land in cdk-magiq-media (not this PR)

## Phase 6 — Tests
- [ ] Unit: each handler dispatches to correct scope-type key via KMS wrapper
- [ ] Unit: scope-type constants align with alias prefix produced by `AliasBuilder.For`
- [ ] Unit: `Retryable` → attempt-count increments through SDK path
- [ ] Unit: EMF resolver maps meter + counter names correctly
- [ ] Integration: full retry loop against LocalStack with `media-erasure-pending` + KMS

## Phase 7 — Ship
- [ ] PR to `develop`

## Phase 8 — Close
- [ ] F041: shipped (full)
- [ ] INTEGRATION-BACKLOG: WS-12b → § Shipped
- [ ] Remove `Erasure-retry driver` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-024 + MM-072 + user policy)
- 2026-10-13: expanded to carry all magiq-media bindings previously conflated with SDK — options binding, scope-type vocab, alias prefix, EMF namespace + per-counter rename, write-model txn wiring. SDK stays BC-agnostic per MM-024 scope correction.
