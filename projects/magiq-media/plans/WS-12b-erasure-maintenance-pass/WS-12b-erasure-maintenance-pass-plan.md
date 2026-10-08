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
**Depends on:** MM-024 (WS-12a SDK), MM-072 (WS-06 — `TimeoutScanner` → `MaintenanceScanner` rename)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-12b (plan MM-043). SDK (MM-024) ships `IErasureDriver`; `MaintenanceScanner` (MM-072) rename shipped.
>
> Add `ErasureRetryPass` to `MaintenanceScanner`: reads `media-erasure-pending`, invokes `IErasureDriver.AttemptErasureAsync` per row, handles `Succeeded / Retryable / Terminal`. Register per-TargetKind handlers (`AssetErasureHandler`, `EventStreamErasureHandler`, `SnapshotErasureHandler`, `SearchDocErasureHandler`).
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-024 + MM-072 shipped
- [ ] Confirm `media-erasure-pending` table provisioned in `cdk-magiq-media`

## Phase 1 — Per-`TargetKind` handlers
- [ ] `AssetErasureHandler`: deletes S3 originals + renditions per asset id
- [ ] `EventStreamErasureHandler`: KMS schedule-key-deletion for the stream's tenant key
- [ ] `SnapshotErasureHandler`: tombstones snapshot row
- [ ] `SearchDocErasureHandler`: deletes OpenSearch document

## Phase 2 — `MaintenanceScanner.ErasureRetryPass`
- [ ] Scan `media-erasure-pending` rows
- [ ] For each: open scanner-execution-context (via WS-15a factory), invoke `IErasureDriver.AttemptErasureAsync`
- [ ] `Succeeded` → delete row
- [ ] `Retryable` → update `AttemptCount` + `LastError` + `LastAttemptAt`
- [ ] `Terminal` → delete row + publish `ErasureFailedPermanent` is handled by SDK

## Phase 3 — Scheduling
- [ ] CloudWatch schedule → `MaintenanceScanner` runs ErasureRetryPass at configured cadence

## Phase 4 — Tests
- [ ] Unit per handler: dispatches to correct AWS resource
- [ ] Unit: Retryable → attempt-count increments
- [ ] Integration: full retry loop against LocalStack

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] F041: shipped (full)
- [ ] INTEGRATION-BACKLOG: WS-12b → § Shipped
- [ ] Remove `Erasure-retry driver` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-024 + MM-072 + user policy)
