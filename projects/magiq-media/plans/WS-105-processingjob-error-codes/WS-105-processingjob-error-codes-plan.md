---
id: MM-145
type: plan
project: magiq-media
workstream: WS-105-processingjob-error-codes
repo: magiq-media
tags: [magiq-media, processing, processingjob, error-codes, problemdetails]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-100 (SDK errorCode slot), MM-032 (duplicate-id exception)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell ProcessingJob × error-codes
---

# WS-105 — ProcessingJob error codes: 2 `ProcessingJobErrorCodes`

**Target repo:** `magiq-media`
**Depends on:** MM-100, MM-032

## Problem

Spec [`error-catalog.md § Processing — ProcessingJob`](../../../../docs/spec/shared/error-catalog.md) names 2 codes. ProcessingJob aggregate exists in code but handlers emit `DomainError.InvalidOperation(prose)` with no code; `ProcessingJobErrorCodes` constants class absent.

| code | status | condition |
|---|---|---|
| `ProcessingJobNotFound` | 404 | Absent |
| `ProcessingJobStatusInvalid` | 422 | Transition from wrong status, or superseded by next attempt |

Note: `ProcessingJobAlreadyExists 409` would carry the duplicate-caller-id path per CLAUDE.md KDPW ("ProcessingJob create not idempotent — spec derives `JobId` as UUID v5"). That belongs to a separate workstream fixing the idempotent-id derivation (not this cell's scope). Spec `error-catalog.md § Processing` names 2 codes only — this plan ships 2.

## What the spec requires

- `ProcessingJobErrorCodes` static class with 2 `const string` entries.
- Every refusal path in `ProcessingJob` + handlers returns `DomainError.<Verb>(ProcessingJobErrorCodes.<Code>, prose)`.
- `ProcessingJobStatusInvalid` extension payload: `currentStatus`, `expectedStatus` (optional), `attemptNumber`.
- SDK slot (MM-100) carries the code to RFC 9457 ProblemDetails `errorCode` root.

## Wire-visibility

- Additive — new `errorCode` payload on 404/422 refusals.

## Scope boundary

- Constants class + handler-site uptake.
- Processing endpoints (if any — ProcessingJob is primarily SNS-driven, not HTTP) wire error-code emission.
- `ProcessingJob create not idempotent` (CLAUDE.md KDPW) → separate workstream (UUID v5 derivation).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-105 (plan MM-145). MM-100 (SDK slot) must ship first.

## Phase 0 — Scope confirmation

- [ ] MM-100 shipped
- [ ] MM-032 shipped

## Phase 1 — Constants + extension payload

- [ ] `ProcessingJobErrorCodes` static class with 2 `const string` entries
- [ ] `ProcessingJobStatusInvalid` carries `currentStatus`, `expectedStatus?`, `attemptNumber` extension payload

## Phase 2 — Handler-site uptake

- [ ] `ProcessingJob` aggregate refusals use `DomainError.<Verb>(ProcessingJobErrorCodes.<Code>, prose)`
- [ ] All status-transition guards return `ProcessingJobStatusInvalid` with payload

## Phase 3 — Tests

- [ ] Unit: each code → ProblemDetails emits root-level `errorCode`
- [ ] Integration: status-transition refusal → body carries `currentStatus`/`expectedStatus`/`attemptNumber`

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry — API wire additive

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-145 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-105 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell ProcessingJob × error-codes; smallest aggregate code set in catalog; mirror of pattern)
