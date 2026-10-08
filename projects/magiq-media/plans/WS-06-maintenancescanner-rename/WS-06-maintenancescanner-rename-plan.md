---
id: MM-072
type: plan
project: magiq-media
workstream: WS-06-maintenancescanner-rename
repo: magiq-media
tags: [magiq-media, maintenance-scanner, saga, cleanup]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/saga-orchestration/INDEX.md#WS-06.
---

# WS-06 — `TimeoutScanner` → `MaintenanceScanner` rename (saga passes removed)

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.
**Unblocks:** MM-043 (WS-12b erasure-retry pass needs `MaintenanceScanner`)

Rename host; remove saga passes (post Step Functions pivot). Keep non-saga passes: upload expiry, registration-response overdue, retention reconciliation, reopen clear, retention-schedule deprecation, quarantine-move retry, erasure retry (added by MM-043).

## Session invocation

> Picking up WS-06 (plan MM-072). Rename host `TimeoutScanner` → `MaintenanceScanner`. Remove saga passes (sagas now Step Functions). Preserve non-saga passes. Update CDK references (coordinate with `cdk-magiq-media`).

## Phase 0 — Scope confirmation
- [ ] Enumerate current passes on `TimeoutScanner`
- [ ] Identify saga passes to remove
- [ ] Confirm non-saga passes to keep

## Phase 1 — Rename
- [ ] Project / assembly name `MaintenanceScanner`
- [ ] CloudWatch schedule rule rename (coordinate with `cdk-magiq-media`)

## Phase 2 — Remove saga passes
- [ ] Delete saga-related code paths
- [ ] Preserve non-saga passes (upload expiry, retention reconciliation, etc.)

## Phase 3 — Tests
- [ ] Unit per surviving pass
- [ ] Integration: scheduled run invokes passes

## Phase 4 — Ship
- [ ] PR to `develop` (coordinate CDK PR in `cdk-magiq-media`)

## Phase 5 — Close
- [ ] saga-orchestration/INDEX.md: WS-06 → § Shipped
- [ ] INTEGRATION-BACKLOG: unblocks MM-043 (WS-12b)
- [ ] Remove `TimeoutScanner renamed MaintenanceScanner` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
