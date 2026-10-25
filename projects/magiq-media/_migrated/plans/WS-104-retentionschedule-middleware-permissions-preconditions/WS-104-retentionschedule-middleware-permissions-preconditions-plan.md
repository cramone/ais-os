---
id: MM-144
type: plan
project: magiq-media
workstream: WS-104-retentionschedule-middleware-permissions-preconditions
repo: magiq-media
tags: [magiq-media, metadata, retentionschedule, middleware, permission, if-match, etag, precondition, resource-predicate]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-100 (SDK errorCode slot), MM-139 (RetentionSchedule error codes), MM-141 (routes), MM-143 (write-model), MM-049 (VersionMismatch 412)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell RetentionSchedule × middleware
---

# WS-104 — RetentionSchedule middleware: permissions + resource-predicate + If-Match + ETag

**Target repo:** `magiq-media`
**Depends on:** MM-100, MM-139, MM-141, MM-143, MM-049

## Problem

Spec [`api-conventions.md § Refusal precedence`](../../../../docs/spec/shared/api-conventions.md#refusal-precedence--state-before-the-resource-predicate) + [`api-permissions.md`](../../../../docs/spec/shared/api-permissions.md): every write route checks `IPermissionService.IsGranted(Permission, claims)` at the edge (`403 PermissionDenied`), then the handler checks the resource predicate per each `retentionschedule.api.md § Authorization` row (`403 NotResourceOwner`); preconditioned routes refuse `If-Match`-absent as `428 PreconditionRequired` and emit `ETag: W/"<AggregateVersion>"` on 2xx.

RetentionSchedule aggregate wholly unbuilt — nothing to extend. Future endpoints (MM-141) land with middleware pre-wired.

## Scope

| Concern | Spec | Code |
|---|---|---|
| Permission check at edge | `IPermissionService.IsGranted(Permission, claims)` → `403 PermissionDenied` | not called (routes absent) |
| Resource-predicate guard | tenant-level: edit permission widened by `.All` | handler layer absent |
| `If-Match` on preconditioned routes | publish, deprecate, deprecate-version, supersession, abandon, draft PUT/DELETE, PATCH metadata | not read |
| `428 PreconditionRequired` when `If-Match` absent | — | — |
| `412 VersionMismatch` on mismatch (MM-049) | — | — |
| `ETag: W/"<AggregateVersion>"` on 2xx + conditional-safe `GET` | not emitted | — |
| `400 InvalidIfMatch` on malformed header | not covered | — |

## What the spec requires

- Every write endpoint declares `[Permission(RetentionSchedulePermissions.<Verb>)]`.
- Handler orders refusal: permission → exists (`404`) → state (`409`/`422`) → resource predicate (`403`).
- Preconditioned write routes read `If-Match` → compare to `AggregateVersion` → `428` absent, `412` mismatch, `400` malformed. 2xx responses carry `ETag: W/"<version>"`.
- RetentionSchedule is tenant-scoped (no per-row owner); resource predicate = tenant match + widened `.All` role.

## Wire-visibility

- Breaking — permission checks + `If-Match` enforcement land with the first-ever RetentionSchedule request. Treated as breaking because downstream clients wiring to the endpoints must branch on 428/412 and add Permission claims; routes themselves are additive (MM-141) but middleware behavior is wire-contract.

## Scope boundary

- Endpoint + handler surface only — wires on MM-141 routes.
- `RetentionSchedulePermissions` constants class = this plan's scope.
- Platform-level `IPermissionService` wiring = MM-100 scope.
- `VersionMismatch` 409 → 412 flip = MM-049.
- Idempotency / pagination / ProblemDetails = covered elsewhere.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-104 (plan MM-144). MM-100/139/141/143/049 must ship first. Middleware wires alongside MM-141 endpoints.

## Phase 0 — Scope confirmation

- [ ] MM-100 (SDK) shipped
- [ ] MM-139 constants reachable
- [ ] MM-141 routes shipped
- [ ] MM-143 write-model shipped
- [ ] MM-049 `VersionMismatch` 412 shipped

## Phase 1 — Permission constants

- [ ] `RetentionSchedulePermissions` constants class — one slug per verb per `retentionschedule.api.md § Authorization` (`CreateRetentionSchedule`, `UpdateRetentionScheduleMetadata`, `CreateRetentionScheduleDraft`, `UpdateRetentionScheduleDraft`, `DiscardRetentionScheduleDraft`, `PublishRetentionSchedule`, `AbandonRetentionSchedule`, `DeprecateRetentionSchedule`, `DeprecateRetentionScheduleVersion`, `RecordRetentionScheduleSupersession`, `ReadRetentionSchedule`)

## Phase 2 — Endpoint-side permission wiring

- [ ] Every RetentionSchedule write endpoint declares `[Permission(RetentionSchedulePermissions.<Verb>)]`
- [ ] FastEndpoints config calls `IPermissionService.IsGranted` on each inbound request; refuses `403 PermissionDenied`

## Phase 3 — Resource-predicate guard

- [ ] Tenant match + widened `.All` role check
- [ ] Handler returns `403 NotResourceOwner` on predicate failure

## Phase 4 — `If-Match` + `ETag`

- [ ] Preconditioned endpoints (publish, deprecate, deprecate-version, supersession, abandon, draft PUT/DELETE, PATCH metadata) read `If-Match`; refuse `428 PreconditionRequired` absent, `412 VersionMismatch` mismatch, `400 InvalidIfMatch` malformed
- [ ] 2xx responses carry `ETag: W/"<AggregateVersion>"`
- [ ] `GET /retention-schedules/{id}`, `GET /versions/{v}`, `GET /versions/latest` emit `ETag`

## Phase 5 — Tests

- [ ] Integration per route: permission refusal → `403 PermissionDenied`
- [ ] Integration per route: `If-Match`-absent on preconditioned → `428`
- [ ] Integration per route: `If-Match` mismatch → `412 VersionMismatch`
- [ ] Integration: `ETag` round-trips on conditional request

## Phase 6 — Communicate change

- [ ] Breaking-changes.md entry — API wire breaking: permission + 428/412 + ETag
- [ ] Release-notes line

## Phase 7 — Ship

- [ ] PR to `develop`

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-144 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-104 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RetentionSchedule × middleware; mirror of MM-106/112/117/123/127/132/138 pattern)
