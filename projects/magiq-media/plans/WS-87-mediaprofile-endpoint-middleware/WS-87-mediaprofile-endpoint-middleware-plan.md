---
id: MM-127
type: plan
project: magiq-media
workstream: WS-87-mediaprofile-endpoint-middleware
repo: magiq-media
tags: [magiq-media, catalog, mediaprofile, http, middleware, authorization, permissions, if-match, precondition, etag]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: MM-100, MM-124, MM-125, MM-049
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell MediaProfile × middleware
---

# WS-87 — MediaProfile endpoint middleware adoption: permission check + resource predicate + `If-Match` precondition

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot), MM-124 (MediaProfile error codes), MM-125 (missing MediaProfile routes), MM-049 (`VersionMismatch` → 412 + `InvalidIfMatch` 400)

## Problem

MediaProfile endpoints under `src/modules/Catalog/Catalog.{WriteModel,ReadModel}.Endpoints/V1/MediaProfiles/` wire none of the three middleware contracts. Zero hits for `IPermissionService` / `If-Match` / `IfMatch` / `ETag` / `PreconditionRequired` / `RequireIfMatch` / `UsePermission`.

Mirrors MM-106 (Asset) + MM-112 (Collection) + MM-117 (Folder) + MM-123 (MediaItem). Three-concern adoption:

1. Per-route `IPermissionService.IsGranted` at the edge.
2. Resource-predicate guard per handler (per `mediaprofile.api.md § Authorization` row — owner / `.All` widening).
3. `If-Match` enforcement on preconditioned routes + `ETag: W/"<AggregateVersion>"` on every mutating 2xx.

## MediaProfile-specific notes

- **`PlatformProfileImmutable` (403) refusal** per MM-124 — Platform-origin profiles refuse tenant write. Edge permission still runs; the Platform-origin branch returns 403 before resource predicate. Specific to MediaProfile among aggregates.
- **Publish route semantics** — `POST /profiles/{profileId}/publish` is irreversible from the published-version's perspective (version numbers monotonically increase; a published version can only be deprecated, not retracted). Spec may require `If-Match` on publish to confirm which draft the caller intends to publish.
- **Draft lifecycle commands** (`PUT /draft/name`, `POST /abandon` under MM-125) are **not** irreversible per spec but take `If-Match` on preconditioned routes per `mediaprofile.api.md § Preconditions`.

## Wire-visibility

Mirrors MM-106 / MM-112 / MM-117 / MM-123. New 403/428 refusals.

## Scope boundary

- **MediaProfile endpoints only.**
- SDK primitives — out of scope.
- Covers 20 existing + 3 new (MM-125) MediaProfile routes.

## Implementation requirements

Three-phase per MM-106:
- Permission check per endpoint via SDK fluent API.
- Resource predicate per handler on loaded aggregate state (owner, `.All` widening). Platform-origin branch refuses `PlatformProfileImmutable 403` before predicate (WS-47 behaviour).
- `If-Match` enforcement + `ETag` emission per `mediaprofile.api.md § Preconditions`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-87 (plan MM-127). All deps shipped. Mirror MM-106 / MM-112 / MM-117 / MM-123 pattern on MediaProfile endpoints + handlers. Platform-origin refusal path exists via WS-47; this plan coordinates ordering with resource predicate. Breaking — coordinate with magiq-media-ui.

## Phase 0 — Scope confirmation

- [ ] MM-100, MM-124, MM-125, MM-049 shipped
- [ ] WS-47 (platform-origin refusal) shipped
- [ ] MediaProfile endpoints enumerated (20 existing + 3 MM-125)
- [ ] SDK primitives confirmed available

## Phase 1 — Permission check on endpoints

- [ ] Each `*MediaProfileEndpoint.cs` registers `UsePermission(Permission.MediaProfileXxx)` per `mediaprofile.api.md § Authorization`
- [ ] `MediaProfilePermissions` constants emitted
- [ ] Unit per route: unauthenticated → 401; without permission → 403 `PermissionDenied`

## Phase 2 — Resource-predicate guards in handlers

- [ ] Each MediaProfile `*Handler.cs` reads loaded aggregate's owner
- [ ] Guard precedence: permission (edge) → exists (404) → state (409/422) → platform-origin (403 `PlatformProfileImmutable` from WS-47) → resource predicate (403 `NotResourceOwner`)
- [ ] Widen with `*.All` where permission grants

## Phase 3 — `If-Match` + `ETag` on preconditioned routes

- [ ] Mark preconditioned routes per `mediaprofile.api.md § Preconditions` with `RequireIfMatch` (publish, deprecate, abandon, draft-level mutations)
- [ ] Every mutating 2xx emits `ETag: W/"<AggregateVersion>"`
- [ ] Unit per preconditioned route: missing → 428; stale → 412 (WS-26); matching → proceeds

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry (added in this sweep's Phase 3)
- [ ] Release-notes line
- [ ] Coordinate with magiq-media-ui

## Phase 5 — Tests

- [ ] Integration: full guard precedence per MediaProfile route
- [ ] Integration: `ETag` round-trip
- [ ] Integration: platform-origin refusal before resource predicate

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-127 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-87 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaProfile × middleware; status candidate; mirror of MM-106/112/117/123; adds Platform-origin branch ordering ahead of resource predicate)
