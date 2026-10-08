---
id: MM-024
type: plan
project: magiq-media
workstream: WS-12a-erasure-driver-sdk
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, erasure, kms, retention]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F041-erasure-key-store-and-retry-driver.md and INDEX.md#WS-12; no separate review document.
---

# WS-12a — Erasure retry driver SDK portion

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-043 (WS-12b — `MaintenanceScanner` erasure-retry pass; also waits on MM-072 WS-06 rename)

Delivers F041 SDK portion. `media-erasure-pending` table + retry driver that releases erasure keys / crypto-shreds target rows + wraps KMS `ScheduleKeyDeletion` with PITR-exclusion hooks.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-12a (plan MM-024). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-12a-erasure-driver-sdk\WS-12a-erasure-driver-sdk-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F041-erasure-key-store-and-retry-driver.md`.
>
> Deliver `media-erasure-pending` table shape + `IErasureDriver.AttemptErasureAsync` returning `Succeeded | Retryable | Terminal`. Pluggable `IErasureHandler<TKind>` strategies per `TargetKind` (asset / event-stream / snapshot / search-doc). `IKmsKeyReleaseService.ScheduleKeyDeletionAsync` wrapper. Retry policy with backoff; `MaxAttempts` default 10; terminal publishes `ErasureFailedPermanent`.
>
> Infra (table + PITR) scheduled separately in `cdk-magiq-media`. PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F041 § Required-shape, § Detection signals
- [ ] Confirm `aspnetcore-platform` has no `IErasureDriver` type today
- [ ] Review retention + crypto-shredding sections in `docs/spec/`

## Phase 1 — Table shape + record
- [ ] `media-erasure-pending` DynamoDB table shape in `Magiq.Platform.Erasure`
- [ ] `ErasurePendingRecord`: `TenantId`, `TargetKind`, `TargetId`, `ScheduledAt`, `AttemptCount`, `LastError`, `LastAttemptAt`
- [ ] PITR-exclusion attribute

## Phase 2 — Driver interface
- [ ] `IErasureDriver.AttemptErasureAsync(record, ct)` → `Result<ErasureOutcome, DomainError>`
- [ ] Outcomes: `Succeeded`, `Retryable(reason)`, `Terminal(reason)`
- [ ] Pluggable per `TargetKind`: `IErasureHandler<TKind>` strategies via DI

## Phase 3 — KMS key-release helper
- [ ] `IKmsKeyReleaseService.ScheduleKeyDeletionAsync(keyId, pendingWindowDays, ct)`
- [ ] Validates pending window (7–30 days per AWS KMS)
- [ ] Idempotent: already-scheduled key returns success

## Phase 4 — Retry policy
- [ ] `ErasureRetryOptions`: `MaxAttempts` (10), `BaseBackoff`, `MaxBackoff`
- [ ] Driver computes next-attempt eligibility
- [ ] After `MaxAttempts`: record `Terminal`; publish `ErasureFailedPermanent` via `IDomainEventPublisher`

## Phase 5 — Tests
- [ ] Unit: dispatches to registered handler by `TargetKind`
- [ ] Unit: retryable outcome schedules next attempt with backoff
- [ ] Unit: terminal outcome publishes `ErasureFailedPermanent`
- [ ] Unit: PITR-exclusion attribute set on writes

## Phase 6 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 7 — Close
- [ ] F041: `status: shipped (SDK portion)`
- [ ] platform-capabilities/INDEX.md: WS-12 split — `WS-12a shipped`, `WS-12b open (waits on MM-072)`
- [ ] INTEGRATION-BACKLOG: MM-043 (WS-12b) `Dep status: shipped (external SDK); still blocked on MM-072 (WS-06 rename)`

## Session log
- 2026-10-08: plan drafted
