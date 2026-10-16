---
id: MM-138
type: plan
project: magiq-media
workstream: WS-98-recordtype-middleware-permissions-preconditions
repo: magiq-media
tags: [magiq-media, metadata, recordtype, middleware, permission, if-match, etag, precondition, resource-predicate]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'MM-100 (SDK errorCode slot), MM-133 (RecordType error codes), MM-135 (routes), MM-137 (lifecycle commands), MM-049 (VersionMismatch 412)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell RecordType × middleware
---

# WS-98 — RecordType middleware: permissions + resource-predicate + If-Match + ETag

**Target repo:** `magiq-media`
**Depends on:** MM-100, MM-133, MM-135, MM-137, MM-049

## Problem

Spec [`api-conventions.md § Refusal precedence`](../../../../docs/spec/shared/api-conventions.md#refusal-precedence--state-before-the-resource-predicate) + [`api-permissions.md`](../../../../docs/spec/shared/api-permissions.md): every write route checks `IPermissionService.IsGranted(Permission, claims)` at the edge (`403 PermissionDenied`), then the handler checks the resource predicate per each `recordtype.api.md § Authorization` row (`403 NotResourceOwner`); preconditioned routes refuse `If-Match`-absent as `428 PreconditionRequired` and emit `ETag: W/"<AggregateVersion>"` on 2xx.

RecordType endpoints:

- Declare no permission.
- Run no resource match.
- Read no `If-Match`.
- Emit no `ETag`.

## Scope

| Concern | Spec | Code |
|---|---|---|
| Permission check at edge | `IPermissionService.IsGranted(Permission, claims)` → `403 PermissionDenied` | not called |
| Resource-predicate guard | tenant-level: edit permission widened by `.All` | handler returns `DomainError.InvalidOperation` |
| `If-Match` on preconditioned routes | publish, deprecate, deprecate-version, reinstate, supersession, abandon, add/update/replace/remove/deprecate field, rename, update-display-name, update-description, set-aliases | not read |
| `428 PreconditionRequired` when `If-Match` absent | returns 2xx and overwrites | — |
| `412 Precondition Failed` on mismatch (MM-049) | current code answers `409` | — |
| `ETag: W/"<AggregateVersion>"` on 2xx + conditional-safe `GET` | not emitted | — |
| `400 InvalidIfMatch` on malformed header | not covered | — |

## What the spec requires

- Every write endpoint declares `[Permission(RecordTypePermissions.<Verb>)]` matching the `recordtype.api.md § Authorization` cell.
- Handler orders refusal: permission → exists (`404`) → state (`409`/`422`) → resource predicate (`403`).
- Preconditioned write routes read `If-Match` → compare to `AggregateVersion` → `428` absent, `412` mismatch, `400` malformed. 2xx responses carry `ETag: W/"<version>"`.
- Clone route takes `If-Match` on the **source** aggregate (idempotency against mid-clone source edits).

## Wire-visibility

- Breaking — permission checks will refuse requests that currently succeed; `If-Match`-absent on preconditioned routes shifts from 2xx to 428; `VersionMismatch` goes 409 → 412 (MM-049); `ETag` added to responses.

## Scope boundary

- Endpoint + handler surface only.
- `RecordTypePermissions` constants class = this plan's scope.
- Platform-level `IPermissionService` wiring = MM-100 scope.
- `VersionMismatch` 409 → 412 flip = MM-049.
- Idempotency / pagination / ProblemDetails = covered elsewhere (F070/F072/F093/MM-100).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-98 (plan MM-138). MM-100/133/135/137/049 must ship first.

## Phase 0 — Scope confirmation

- [ ] MM-100 (SDK) shipped
- [ ] MM-133 constants reachable
- [ ] MM-135 routes shipped
- [ ] MM-137 lifecycle commands shipped
- [ ] MM-049 `VersionMismatch` 412 shipped

## Phase 1 — Permission constants

- [ ] `RecordTypePermissions` constants class — one slug per verb per `recordtype.api.md § Authorization` (`CreateRecordType`, `UpdateRecordType`, `DeleteRecordType`, `PublishRecordType`, `DeprecateRecordType`, `ReinstateRecordType`, `RecordSupersession`, `AbandonRecordType`, `CloneRecordType`, `AddField`, `UpdateField`, `ReplaceField`, `RemoveField`, `DeprecateField`, `ReorderFields`, `RenameRecordType`, `UpdateDisplayName`, `UpdateDescription`, `SetAliases`, `ReadRecordType`)

## Phase 2 — Endpoint-side permission wiring

- [ ] Every RecordType write endpoint declares `[Permission(RecordTypePermissions.<Verb>)]`
- [ ] FastEndpoints config calls `IPermissionService.IsGranted` on each inbound request; refuses `403 PermissionDenied`

## Phase 3 — Resource-predicate guard

- [ ] RecordType is tenant-scoped (no per-row owner); predicate = tenant match + widened `.All` role
- [ ] Handler returns `403 NotResourceOwner` on predicate failure

## Phase 4 — `If-Match` + `ETag`

- [ ] Preconditioned endpoints read `If-Match`; refuse `428 PreconditionRequired` absent, `412` mismatch, `400 InvalidIfMatch` malformed
- [ ] 2xx responses carry `ETag: W/"<AggregateVersion>"`
- [ ] Clone route reads source `If-Match` (idempotency)
- [ ] `GET /record-types/{id}`, `GET /versions/{v}`, `GET /versions/latest` emit `ETag` for conditional reads

## Phase 5 — Tests

- [ ] Integration per route: permission refusal → `403 PermissionDenied`
- [ ] Integration per route: `If-Match`-absent on preconditioned → `428`
- [ ] Integration per route: `If-Match` mismatch → `412 VersionMismatch`
- [ ] Integration: `ETag` emitted on 2xx + round-trips on conditional request
- [ ] Integration: Clone with mid-clone source edit refused `412`

## Phase 6 — Communicate change

- [ ] Breaking-changes.md entry — API wire breaking: permission refusals + 428/412 + ETag
- [ ] Release-notes line

## Phase 7 — Ship

- [ ] PR to `develop`

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-138 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-98 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RecordType × middleware; status candidate; mirror of MM-106/112/117/123/127/132 pattern)
