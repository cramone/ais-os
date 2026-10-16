---
id: MM-117
type: plan
project: magiq-media
workstream: WS-77-folder-endpoint-middleware
repo: magiq-media
tags: [magiq-media, catalog, folder, http, middleware, authorization, permissions, if-match, precondition, etag]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: MM-100, MM-113, MM-115, MM-049
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Folder × middleware
---

# WS-77 — Folder endpoint middleware adoption: permission check + resource predicate + `If-Match` precondition

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot), MM-113 (Folder error codes), MM-115 (missing Folder routes), MM-049 (`VersionMismatch` → 412 + `InvalidIfMatch` 400). Coordinates with WS-11 (unarchive 202-async + status endpoints also take `If-Match`).

## Problem

Folder endpoints under `src/modules/Catalog/Catalog.{WriteModel,ReadModel}.Endpoints/V1/Folders/` wire none of the three middleware contracts stated in `docs/spec/shared/api-conventions.md` and `docs/spec/shared/api-permissions.md`. Zero hits for `IPermissionService` / `If-Match` / `IfMatch` / `ETag` / `PreconditionRequired` / `RequireIfMatch` / `UsePermission` across Folder endpoint files.

Mirrors MM-106 (Asset) + MM-112 (Collection) — three-concern adoption:

1. Per-route `IPermissionService.IsGranted` check at the edge.
2. Resource-predicate guard per handler (per `folder.api.md § Authorization` row — owner/CreatedBy, widened by `.All`).
3. `If-Match` enforcement on preconditioned routes + `ETag: W/"<AggregateVersion>"` on every mutating 2xx.

## Wire-visibility

Callers who succeed today may refuse `403 NotResourceOwner` or `428 PreconditionRequired` after this change. Mirrors Collection + Asset.

## Scope boundary

- **Folder endpoints only.** Collection = MM-112. Asset = MM-106. MediaItem/etc. = future.
- SDK primitives (`IPermissionService` exists; fluent `UsePermission`, response-side `ETag` filter, `RequireIfMatch` middleware) — out of scope. Any missing primitive raises a dependency-gap note.
- The 2 new routes added by MM-115 (`PUT /originator`, `POST /reopen`) + WS-11's unarchive route adopt the same middleware pattern — this plan covers all 17 Folder write routes (15 existing + 2 from MM-115) and the WS-11 async routes.

## Implementation requirements

Three-phase per MM-106:

- Permission check per endpoint via SDK fluent API.
- Resource predicate per handler on loaded aggregate state (owner/CreatedBy, `.All` widening).
- `If-Match` enforcement + `ETag` emission on preconditioned routes per `folder.api.md § Preconditions`. 202-async archive/unarchive routes (WS-11) also take `If-Match` at command acceptance.
- Status endpoints (`/archive-status`, `/unarchive-status`) exempt — read-only.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-77 (plan MM-117). All deps shipped. Mirror MM-106 / MM-112 pattern on Folder endpoints + handlers. Coordinate with WS-11 for 202-async routes' If-Match semantics. Breaking change — coordinate with magiq-media-ui.

## Phase 0 — Scope confirmation

- [ ] MM-100, MM-113, MM-115, MM-049 shipped
- [ ] WS-11 state (unarchive route + status endpoints landing concurrently)
- [ ] Folder endpoints enumerated (11 write + 4 read + 2 MM-115 + 2 WS-11 async)
- [ ] SDK primitives confirmed available (align with MM-106 audit)

## Phase 1 — Permission check on endpoints

- [ ] Each `*FolderEndpoint.cs` registers `UsePermission(Permission.FolderXxx)` per `folder.api.md § Authorization`
- [ ] `FolderPermissions` constants emitted
- [ ] Unit per route: unauthenticated → 401; authenticated without permission → 403 `PermissionDenied`

## Phase 2 — Resource-predicate guards in handlers

- [ ] Each Folder `*Handler.cs` reads loaded aggregate's owner / CreatedBy
- [ ] Guard precedence enforced (permission → exists → state → resource predicate)
- [ ] Refuse `NotResourceOwner 403`
- [ ] Widen with `*.All` where permission grants

## Phase 3 — `If-Match` + `ETag` on preconditioned routes

- [ ] Mark preconditioned routes per `folder.api.md § Preconditions` with `RequireIfMatch`
- [ ] 202-async archive + unarchive (WS-11) take `If-Match` at command acceptance; ETag matches AggregateVersion at dispatch; cascade terminator updates version
- [ ] Status endpoints exempt — read-only, no If-Match
- [ ] Every mutating 2xx emits `ETag: W/"<AggregateVersion>"`
- [ ] Unit per preconditioned route: missing header → 428 `PreconditionRequired`; stale → 412 `VersionMismatch` (WS-26); matching → proceeds

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry (added in this sweep's Phase 3)
- [ ] Release-notes line
- [ ] Coordinate with magiq-media-ui on new 4xx codes

## Phase 5 — Tests

- [ ] Integration: full guard precedence per Folder route
- [ ] Integration: `ETag` round-trip (read → write with `If-Match` → updated `ETag`)
- [ ] Integration: `*.All` role widens the resource predicate

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-117 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-77 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell Folder × middleware; status candidate; mirror of MM-106 + MM-112)
