---
id: MM-123
type: plan
project: magiq-media
workstream: WS-83-mediaitem-endpoint-middleware
repo: magiq-media
tags: [magiq-media, catalog, mediaitem, http, middleware, authorization, permissions, if-match, precondition, etag]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: MM-100, MM-118, MM-120, MM-049
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell MediaItem × middleware
---

# WS-83 — MediaItem endpoint middleware adoption: permission check + resource predicate + `If-Match` precondition

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot), MM-118 (MediaItem error codes), MM-120 (missing MediaItem routes), MM-049 (`VersionMismatch` → 412 + `InvalidIfMatch` 400)

## Problem

MediaItem endpoints under `src/modules/Catalog/Catalog.{WriteModel,ReadModel}.Endpoints/V1/MediaItems/` wire none of the three middleware contracts stated in `docs/spec/shared/api-conventions.md` + `docs/spec/shared/api-permissions.md`. Zero hits for `IPermissionService` / `If-Match` / `IfMatch` / `ETag` / `PreconditionRequired` / `RequireIfMatch` / `UsePermission` across MediaItem endpoint files.

Mirrors MM-106 (Asset) + MM-112 (Collection) + MM-117 (Folder). Three-concern adoption:

1. Per-route `IPermissionService.IsGranted` at the edge.
2. Resource-predicate guard per handler (per `mediaitem.api.md § Authorization` row — owner, MediaItem edit-session editor, review-roster-member on review commands, widened by `.All`).
3. `If-Match` enforcement on preconditioned routes + `ETag: W/"<AggregateVersion>"` on every mutating 2xx.

## MediaItem-specific notes

- **Four whole-state-replace commands take `If-Match`** per spec [`api-conventions.md § A whole-state replace on a shared working set requires If-Match`]: `UpdateMediaItemCommand` (PATCH), `TagMediaItemCommand` (PUT `/tags`), `SetMetadataBatchCommand` (PUT `/metadata`), `ReplaceAssetInRoleCommand` (PUT `/roles/{roleName}/assets`). Irreversible routes (`DELETE /items/{itemId}`, `DELETE /items/{itemId}/versions/{versionNumber}`) also take `If-Match`. `POST /erase-personal-data` is a named `If-Match` exception.
- **Review commands bypass handler-side auth** — `ApproveMediaItem` / `RejectMediaItem` resolve against `MediaItem.ReviewSession.Reviewers[]` **inside the aggregate** (MM-118/MM-122). Edge permission still applies (`MediaItem.Review` or equivalent); the resource predicate is "caller holds an assignment on the active session", enforced aggregate-side.
- **`POST /checkout/force-release`** (MM-120) admits `System` actor **alongside** the resource predicate — per CLAUDE.md § Auth. Middleware adoption on this route lets `System` pass the resource-predicate branch; the alongside-admission is handler shape, not an SDK primitive change.

## Wire-visibility

Mirrors MM-106 / MM-112 / MM-117. New 403/428 refusals.

## Scope boundary

- **MediaItem endpoints only.**
- SDK primitives (`IPermissionService` exists; fluent API, response-side `ETag` filter, `RequireIfMatch` middleware) — out of scope.
- Covers 27 existing + 12 new (MM-120) + 2 async (if any) MediaItem routes.

## Implementation requirements

Three-phase per MM-106:
- Permission check per endpoint via SDK fluent API.
- Resource predicate per handler on loaded aggregate state (owner, edit-session editor, `.All` widening; review commands' aggregate-invariant branch is MM-118/MM-122).
- `If-Match` enforcement + `ETag` emission on preconditioned routes (4 whole-state replaces + 2 irreversible deletes) + `erase-personal-data` named exception.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-83 (plan MM-123). All deps shipped. Mirror MM-106 / MM-112 / MM-117 pattern on MediaItem endpoints + handlers. Four whole-state-replace commands take If-Match. Review commands keep aggregate-invariant auth. Force-release admits System alongside predicate. Breaking — coordinate with magiq-media-ui.

## Phase 0 — Scope confirmation

- [ ] MM-100, MM-118, MM-120, MM-049 shipped
- [ ] MM-122 shipped (ReviewSession state enables aggregate-invariant review refusals)
- [ ] MediaItem endpoints enumerated (27 existing + 12 new MM-120)
- [ ] SDK primitives confirmed available

## Phase 1 — Permission check on endpoints

- [ ] Each `*MediaItemEndpoint.cs` registers `UsePermission(Permission.MediaItemXxx)` per `mediaitem.api.md § Authorization`
- [ ] `MediaItemPermissions` constants emitted
- [ ] Unit per route: unauthenticated → 401; authenticated without permission → 403 `PermissionDenied`

## Phase 2 — Resource-predicate guards in handlers

- [ ] Each MediaItem `*Handler.cs` reads loaded aggregate's owner / edit-session editor list
- [ ] Guard precedence enforced (permission → exists → state → resource predicate)
- [ ] Refuse `NotResourceOwner 403`
- [ ] Widen with `*.All` where permission grants
- [ ] `POST /checkout/force-release` admits `System` actor alongside predicate
- [ ] Review commands (`Approve`/`Reject`) rely on `MediaItem.ReviewSession` aggregate-invariant refusals (MM-118 `NotAssignedReviewer`/`ReviewerAlreadyDecided`); edge permission still applies

## Phase 3 — `If-Match` + `ETag` on preconditioned routes

- [ ] Mark 4 whole-state-replace routes with `RequireIfMatch`: PATCH `/items/{id}`, PUT `/tags`, PUT `/metadata`, PUT `/roles/{roleName}/assets`
- [ ] Mark 2 irreversible routes with `RequireIfMatch`: DELETE `/items/{id}` (deprecated per MM-120 but keeps `If-Match` during window), DELETE `/items/{id}/versions/{versionNumber}`
- [ ] Mark any additional spec-named preconditioned routes per `mediaitem.api.md § Preconditions`
- [ ] `POST /erase-personal-data` exempt — spec-named exception
- [ ] Every mutating 2xx emits `ETag: W/"<AggregateVersion>"`
- [ ] Unit per preconditioned route: missing header → 428; stale → 412; matching → proceeds

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry (added in this sweep's Phase 3)
- [ ] Release-notes line
- [ ] Coordinate with magiq-media-ui on new 4xx codes

## Phase 5 — Tests

- [ ] Integration: full guard precedence per MediaItem route
- [ ] Integration: `ETag` round-trip (read → write with `If-Match` → updated `ETag`)
- [ ] Integration: `*.All` role widens the resource predicate
- [ ] Integration: `POST /checkout/force-release` as `System` actor without resource-predicate match
- [ ] Integration: review command as non-roster caller → 403 `NotAssignedReviewer`

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-123 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-83 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaItem × middleware; status candidate; mirror of MM-106 + MM-112 + MM-117)
