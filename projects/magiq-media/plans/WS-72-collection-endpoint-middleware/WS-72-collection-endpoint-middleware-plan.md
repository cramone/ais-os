---
id: MM-112
type: plan
project: magiq-media
workstream: WS-72-collection-endpoint-middleware
repo: magiq-media
tags: [magiq-media, catalog, collection, http, middleware, authorization, permissions, if-match, precondition, etag]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
depends-on: MM-100, MM-107, MM-109, MM-049
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Collection × middleware
---

# WS-72 — Collection endpoint middleware adoption: permission check + resource predicate + `If-Match` precondition

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot), MM-107 (Collection error codes), MM-109 (missing Collection routes), MM-049 (`VersionMismatch` → 412 + `InvalidIfMatch` 400)

## Problem

Collection's HTTP endpoints under `src/modules/Catalog/Catalog.{WriteModel,ReadModel}.Endpoints/V1/Collections/` wire none of the three middleware contracts stated in `docs/spec/shared/api-conventions.md` and `docs/spec/shared/api-permissions.md`:

1. **`IPermissionService` per-route permission check.** Zero call sites in Collection endpoints (confirmed by grep).
2. **Resource-predicate guards in handlers.** `api-conventions.md § Refusal precedence` requires `permission(403) → exists(404) → state(409/422) → resource predicate(403)`. Collection's resource predicate (owner/CreatedBy per each `collection.api.md § Authorization` row, widened by `.All`) is never checked in `*Handler.cs`.
3. **`If-Match` precondition on preconditioned routes.** Collection endpoints do not read `If-Match`, do not emit `ETag`, do not refuse 428/400.

Parallel to the Asset middleware adoption shipping under MM-106 / WS-66.

## What the spec requires

- Every Collection write route checks `IPermissionService.IsGranted(Permission, claims)` — refuse `403 PermissionDenied` (`errorCode: PermissionDenied`).
- Every Collection handler checks resource predicate per `collection.api.md § Authorization` row (owner/CreatedBy, widened by `.All`) — refuse `403 NotResourceOwner`.
- Guard precedence: permission → exists → state → resource predicate.
- Preconditioned routes (per `collection.api.md § Preconditions` — rename, visibility change, tag mutations, default-profile mutations, archive, unarchive) require `If-Match`. Missing → `428 PreconditionRequired`. Stale → `412 VersionMismatch` (WS-26). Weak-ETag match on `AggregateVersion`.
- Every 2xx mutating response emits `ETag: W/"<AggregateVersion>"`.
- The 202-async archive/unarchive routes (MM-109) also take `If-Match` on command acceptance — the ETag matches the `AggregateVersion` at command dispatch; cascade terminator updates version.

## Wire-visibility

Mirrors MM-106 for Asset. Callers who succeed today may refuse `403 NotResourceOwner` or `428 PreconditionRequired` after this change.

## Scope boundary

- **Collection endpoints only.** Folder / MediaItem / MediaProfile / ChangeRequest / etc. middleware adoption lands under those cells' plans.
- SDK primitives (`IPermissionService` exists; `UsePermission` fluent API, response-side ETag filter, `RequireIfMatch` middleware) — out of scope. Any missing primitive raises a `dependency-gaps/platform-capabilities/` note.

## Implementation requirements

Same three-phase shape as MM-106:
- Permission check per endpoint via SDK fluent API.
- Resource predicate per handler on loaded aggregate state.
- `If-Match` enforcement + `ETag` emission on preconditioned routes.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-72 (plan MM-112). Collection parallel of MM-106. All deps shipped. Mirror MM-106's three-concern adoption pattern on Collection endpoints + handlers. Coordinate with magiq-media-ui.

## Phase 0 — Scope confirmation

- [ ] MM-100, MM-107, MM-109, MM-049 shipped
- [ ] Collection endpoints enumerated (6 write + 3 read + 2 new async status under MM-109)
- [ ] SDK primitives confirmed available (align with MM-106's audit)

## Phase 1 — Permission check on endpoints

- [ ] Each `*CollectionEndpoint.cs` registers `UsePermission(Permission.CollectionXxx)` per `collection.api.md § Authorization`
- [ ] `CollectionPermissions` constants emitted
- [ ] Unit per route: unauthenticated → 401; authenticated without permission → 403 `PermissionDenied`

## Phase 2 — Resource-predicate guards in handlers

- [ ] Each Collection `*Handler.cs` reads loaded aggregate's owner / CreatedBy
- [ ] Guard precedence enforced per concern order
- [ ] Refuse `NotResourceOwner 403`
- [ ] Widen with `*.All` where permission grants

## Phase 3 — `If-Match` + `ETag` on preconditioned routes

- [ ] Mark preconditioned routes per `collection.api.md § Preconditions` with `RequireIfMatch`
- [ ] Status endpoints (`/archive-status`, `/unarchive-status`) exempt — read-only
- [ ] 202 async acceptance commands take `If-Match` at command dispatch (ETag matches current `AggregateVersion`)
- [ ] Every mutating 2xx emits `ETag: W/"<AggregateVersion>"`
- [ ] Unit per preconditioned route: missing header → 428; stale → 412; matching → proceeds

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry (added in this sweep's Phase 3)
- [ ] Release-notes line
- [ ] Coordinate with magiq-media-ui on new 4xx codes

## Phase 5 — Tests

- [ ] Integration: full guard precedence per Collection route
- [ ] Integration: `ETag` round-trip (read → write with `If-Match` → updated `ETag`)
- [ ] Integration: `*.All` role widens the resource predicate

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-112 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-72 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-15: plan drafted (alignment-sweep-2026-10-15 cell Collection × middleware; status candidate; mirror of MM-106 for Asset)
