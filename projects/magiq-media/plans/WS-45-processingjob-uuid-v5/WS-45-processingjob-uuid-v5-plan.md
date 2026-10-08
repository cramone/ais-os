---
id: MM-053
type: plan
project: magiq-media
workstream: WS-45-processingjob-uuid-v5
repo: magiq-media
tags: [magiq-media, processing, idempotency, uuid]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-45.
---

# WS-45 — `ProcessingJob` id as UUID v5 over `(TenantId, AssetId, AttemptNumber)` + absorb duplicate

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec: `JobId = ProcessingJobId.For(TenantId, AssetId, AttemptNumber)` (UUID v5). Create absorbs duplicate as success. Today handler mints fresh v7 per delivery → duplicate SQS delivery creates duplicate job.

## Session invocation

> Picking up WS-45 (plan MM-053). Add `ProcessingJobId.For(TenantId, AssetId, AttemptNumber)` UUID v5 helper. `CreateProcessingJob` handler uses it; catches `AggregateAlreadyExistsException` (post MM-007) → absorbs as success.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/processing/processingjob.write-model.md`
- [ ] Locate current `JobId` minting path
- [ ] Confirm MM-007 (`AggregateAlreadyExistsException`) available via SDK

## Phase 1 — `ProcessingJobId.For` helper
- [ ] UUID v5 over `(TenantId, AssetId, AttemptNumber)` with stable namespace
- [ ] Deterministic: same inputs → same id

## Phase 2 — Handler change
- [ ] `CreateProcessingJob` derives `JobId` via helper
- [ ] Catches `AggregateAlreadyExistsException` → returns success (idempotent)

## Phase 3 — Tests
- [ ] Unit: same inputs → same id
- [ ] Unit: duplicate delivery → success (job unchanged)
- [ ] Integration: duplicate SQS message doesn't create second job

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] spec-divergence/INDEX.md: WS-45 → § Shipped
- [ ] Remove `ProcessingJob create not idempotent` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
