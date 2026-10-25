---
id: MM-132
type: plan
project: magiq-media
workstream: WS-92-changerequest-endpoint-middleware
repo: magiq-media
tags: [magiq-media, change-requests, http, middleware, authorization, permissions, if-match, precondition, etag]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: MM-100, MM-128, MM-130, MM-049
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell ChangeRequest × middleware
---

# WS-92 — ChangeRequest endpoint middleware adoption

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot), MM-128 (ChangeRequest error codes), MM-130 (missing routes), MM-049 (`VersionMismatch` → 412 + `InvalidIfMatch` 400)

## Problem

ChangeRequest endpoints under `src/modules/ChangeRequests/ChangeRequests.{WriteModel,ReadModel}.Endpoints/V1/` wire none of three middleware contracts. Zero hits for `IPermissionService` / `If-Match` / `IfMatch` / `UsePermission`.

Mirrors MM-106/112/117/123/127. Three-concern adoption:

1. Per-route `IPermissionService.IsGranted` at edge.
2. Resource-predicate guard per handler (per `changerequest.api.md § Authorization` — owner or participant; comment author on edit/delete; widened by `.All`).
3. `If-Match` enforcement + `ETag` emission per preconditioned routes.

## ChangeRequest-specific notes

- **Dual-predicate authorization** — "non-owner non-participant" refuses `NotChangeRequestParticipant 403` (MM-128). "Non-author" on comment edit/delete refuses `NotCommentAuthor 403`. Handler-side guard runs both predicates in correct precedence (owner/participant first for CR-level ops; comment-author second for comment-level ops).
- **Lifecycle commands** (`resolve`, `abandon`, `reopen`, `redact`) — spec may require `If-Match` on each to confirm aggregate version at refuse-point. Align with `changerequest.api.md § Preconditions`.

## Wire-visibility

Mirrors other middleware cells.

## Scope boundary

- **ChangeRequest endpoints only.**
- Covers 7 existing + 7 new (MM-130) ChangeRequest routes.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-92 (plan MM-132). All deps shipped. Mirror MM-106/112/117/123/127 pattern on ChangeRequest endpoints + handlers. Dual-predicate auth (owner/participant for CR-level; comment-author for comment-level).

## Phase 0 — Scope confirmation

- [ ] MM-100, MM-128, MM-130, MM-049 shipped
- [ ] MM-131 shipped (ChangeRequest.Status / Participants state)
- [ ] ChangeRequest endpoints enumerated

## Phase 1 — Permission check on endpoints

- [ ] Each `*Endpoint.cs` registers `UsePermission(Permission.ChangeRequestXxx)` per `changerequest.api.md § Authorization`
- [ ] `ChangeRequestPermissions` constants emitted

## Phase 2 — Resource-predicate guards

- [ ] CR-level ops: owner-or-participant predicate → `NotChangeRequestParticipant 403` (MM-128)
- [ ] Comment-level ops (edit/delete/redact): comment-author predicate → `NotCommentAuthor 403` (MM-128)
- [ ] `.All` widening where permission grants
- [ ] Guard precedence: permission → exists → state → resource predicate

## Phase 3 — `If-Match` + `ETag` on preconditioned routes

- [ ] Mark preconditioned routes per `changerequest.api.md § Preconditions` with `RequireIfMatch`
- [ ] Every mutating 2xx emits `ETag: W/"<AggregateVersion>"`

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry
- [ ] Release-notes line

## Phase 5 — Tests

- [ ] Integration: full guard precedence per CR route
- [ ] Integration: comment-level ops refuse `NotCommentAuthor` for non-author
- [ ] Integration: `ETag` round-trip

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-132 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-92 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell ChangeRequest × middleware; status candidate; mirror of MM-106/112/117/123/127)
