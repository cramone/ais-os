---
id: MM-147
type: plan
project: magiq-media
workstream: WS-107-processingjob-write-model
repo: magiq-media
tags: [magiq-media, processing, processingjob, write-model, superseded, idempotent-create, uuid-v5]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-145 (error codes), MM-146 (integration events)'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell ProcessingJob × write-model
---

# WS-107 — ProcessingJob write-model: `ProcessingJobSuperseded` + idempotent create

**Target repo:** `magiq-media`
**Depends on:** MM-145, MM-146

## Problem

Spec names 8 ProcessingJob domain events. Code emits 7.

Missing (1):

| event | emitting command |
|---|---|
| `ProcessingJobSuperseded` | emitted when a new attempt arrives for the same `(TenantId, AssetId, AttemptNumber+1)` tuple; prior attempt moved to `Superseded` terminal state and raises the event |

Additional divergence (CLAUDE.md KDPW):

- **`ProcessingJob` create not idempotent** — spec derives `JobId` as UUID v5 over `(TenantId, AssetId, AttemptNumber)` via `ProcessingJobId.For(...)` and absorbs a duplicate as success. Handler currently mints a fresh v7 per delivery; duplicate SQS redelivery creates duplicate jobs.

`ProcessingJobStatus` + `ProcessingJobFailureCategory` ordinals pinned — code compliant from day one per CLAUDE.md.

## What the spec requires

- `ProcessingJobSuperseded { TenantId, JobId, AssetId, AttemptNumber, SupersededAt, SupersededByJobId }` + `[DomainEvent]` ordinal pinned.
- `ProcessingJob.Supersede(supersededByJobId)` aggregate method: terminal transition — refuses when job already terminal, emits event.
- `CreateProcessingJobCommand.ExecuteAsync` reads `ProcessingJobId.For(TenantId, AssetId, AttemptNumber)` (UUID v5) + attempts `SaveAsync`; on `EventConcurrencyException` (duplicate id) returns success and skips event emission.
- `ProcessingJobId.For(TenantId, AssetId, AttemptNumber)` factory under `Processing.Domain.ValueObjects`.

## Scope boundary

- Domain event + aggregate method + command handler + id factory.
- Integration event wire for `ProcessingJobSuperseded` → mapper under MM-146 (if downstream subscribers need it; audit).
- Error codes already shipped under MM-145.
- No snapshot change needed (status already carries `Superseded` state via existing `ProcessingJobStatus` enum).

## Wire-visibility

- Internal — handler idempotency becomes success-on-duplicate (currently create-duplicate). No SNS type added by `ProcessingJobSuperseded` emission unless MM-146 audit extends mapper (separate decision).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-107 (plan MM-147). MM-145 (codes) + MM-146 (integration events) must be reachable. UUID v5 derivation per `ProcessingJobId.For`.

## Phase 0 — Scope confirmation

- [ ] MM-145 constants reachable
- [ ] MM-146 mapper reachable
- [ ] UUID v5 helper (`Guid.NewV5(namespace, name)`) available in SDK or shim locally

## Phase 1 — Id factory

- [ ] `ProcessingJobId.For(TenantId, AssetId, AttemptNumber)` — stable UUID v5 over the tuple

## Phase 2 — Domain event + aggregate method

- [ ] `ProcessingJobSuperseded` domain event + ordinal pinned
- [ ] `ProcessingJob.Supersede(supersededByJobId)` aggregate method; terminal; refuses non-active status (`ProcessingJobStatusInvalid` from MM-145)

## Phase 3 — Handler idempotency

- [ ] `CreateProcessingJobCommand.ExecuteAsync` reads id from `ProcessingJobId.For(...)` + catches `EventConcurrencyException` + returns success
- [ ] `ProcessingJobCreatedSagaHandler` (SNS consumer) → absorbs duplicate SQS redelivery as success

## Phase 4 — Supersede call site

- [ ] Wire `Supersede(newJobId)` into the saga state transition where a new attempt replaces a running attempt (`AssetIngestionSaga` likely)

## Phase 5 — Tests

- [ ] Unit: `Supersede` → `ProcessingJobSuperseded` emitted; refuses non-active
- [ ] Integration: duplicate `CreateProcessingJobCommand` with same `(TenantId, AssetId, AttemptNumber)` → single row + single SNS fire
- [ ] Integration: AttemptNumber increment flow → prior job state becomes `Superseded`

## Phase 6 — Communicate change

- [ ] No `breaking-changes.md` entry — internal (success-on-duplicate is handler-side idempotency, visible only as absence of duplicate event emission)
- [ ] If MM-146 audit admits `media.processingjob.superseded` SNS type, that's a Process wire — additive entry on MM-146

## Phase 7 — Ship

- [ ] PR to `develop`

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: `ProcessingJob create not idempotent` bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-147 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-107 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell ProcessingJob × write-model; 1 missing event `ProcessingJobSuperseded` + idempotent create via UUID v5 derivation; depends on MM-145 + MM-146)
