---
id: MM-128
type: plan
project: magiq-media
workstream: WS-88-changerequest-error-codes
repo: magiq-media
tags: [magiq-media, change-requests, errors, error-codes, problemdetails, wire-contract]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: MM-100, MM-032
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell ChangeRequest × error-codes
---

# WS-88 — ChangeRequest coded error wiring (14 codes)

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot), MM-032 (`AggregateAlreadyExistsException` → `ChangeRequestAlreadyExists`)

## Problem

`docs/spec/shared/error-catalog.md § ChangeRequests` names 14 codes. Code emits every ChangeRequest refusal as `DomainError.InvalidOperation(prose)` with no `errorCode`. `ChangeRequestErrorCodes` constants class unbuilt.

14 codes:

| errorCode | HTTP | Condition |
|---|---|---|
| `ChangeRequestNotFound` | 404 | Absent |
| `ChangeRequestNotOpen` | 422 | Op requires Open |
| `CommentNotFound` | 404 | Comment id absent |
| `CommentDeleted` | 422 | Soft-deleted comment |
| `CommentRedacted` | 422 | Comment body erased |
| `ChangeRequestNotReopenable` | 422 | Reopen on open/resolved |
| `ParticipantAlreadyAdded` | 409 | Member already participant |
| `ParticipantNotFound` | 404 | Removal names non-participant |
| `TooManyParticipants` | 422 | > `MaxParticipantsPerRequest` (100) |
| `ChangeRequestCommentLimitReached` | 422 | > `MaxCommentsPerRequest` (1,000) |
| `ChangeRequestAlreadyExists` | 409 | Duplicate caller id |
| `NotChangeRequestParticipant` | 403 | Non-owner non-participant on scoped op |
| `NotCommentAuthor` | 403 | Edit/delete by non-author |
| `InvalidCommentBody` | 400 | Empty / > 4000 / C0 ctl |

## Code state today

- ChangeRequest handlers emit `DomainError.InvalidOperation(prose)` across every refusal site.
- `ChangeRequestErrorCodes` constants class unbuilt.
- Owner / participant / comment-author resource predicates refuse `NotChangeRequestParticipant` / `NotCommentAuthor` from handler-side guard (not aggregate-invariant per CLAUDE.md § Auth note on review vs change-request).
- `ChangeRequestAlreadyExists` depends on F020 / MM-032.
- Participant / comment-limit refusals belong to aggregate invariants.

## What the spec requires

- `ChangeRequestErrorCodes` constants class with 14 members.
- Every `ChangeRequest.*` refusal returns `DomainError.<factory>(errorCode: ChangeRequestErrorCodes.<code>, …)`.
- Every `*ChangeRequestHandler.cs` reports `errorCode` on refusals.
- `ChangeRequestAlreadyExists` from `AggregateAlreadyExistsException` (MM-032).
- `NotChangeRequestParticipant` / `NotCommentAuthor` as handler-side resource-predicate refusals.
- `InvalidCommentBody` on comment-body validation (empty / > 4000 / C0 control chars).
- Bulk envelope `BulkItemError.ErrorCode` lookup from `ChangeRequestErrorCodes` where applicable.

## Scope boundary

- **ChangeRequest only.**
- Does not build missing commands/handlers — ChangeRequest × write-model cell plan.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-88 (plan MM-128). MM-100 shipped. Wire 14 ChangeRequest error codes to aggregate + handlers.

## Phase 0 — Scope confirmation

- [ ] MM-100 shipped
- [ ] Grep `DomainError.InvalidOperation` sites in `ChangeRequests.Domain/` + `ChangeRequests.WriteModel/Commands/`
- [ ] Confirm aggregate carries participants + comments state

## Phase 1 — Constants + aggregate

- [ ] `ChangeRequestErrorCodes.cs` with 14 const strings
- [ ] `ChangeRequest.*` method refusals return `DomainError.<factory>(errorCode: ChangeRequestErrorCodes.<code>, message)`
- [ ] Participant/comment invariants: `ParticipantAlreadyAdded` (409), `ParticipantNotFound` (404), `TooManyParticipants` (422), `ChangeRequestCommentLimitReached` (422), `InvalidCommentBody` (400)
- [ ] Comment lifecycle: `CommentNotFound` (404), `CommentDeleted` (422), `CommentRedacted` (422)
- [ ] Lifecycle: `ChangeRequestNotOpen` (422), `ChangeRequestNotReopenable` (422)
- [ ] Snapshot test per factory: `.ErrorCode` set

## Phase 2 — Handlers

- [ ] Aggregate-missing → `ChangeRequestNotFound`
- [ ] `AggregateAlreadyExistsException` (MM-032) → `ChangeRequestAlreadyExists`
- [ ] Resource predicate (non-participant on scoped op) → `NotChangeRequestParticipant 403`
- [ ] Comment edit/delete by non-author → `NotCommentAuthor 403`
- [ ] Bulk envelope `BulkItemError.ErrorCode` uses `ChangeRequestErrorCodes` (if ChangeRequest has bulk flow)

## Phase 3 — Tests

- [ ] Integration per spec row: HTTP status + `errorCode` + `type`
- [ ] Unit per factory: `ErrorCode` set
- [ ] Guard precedence: owner/participant check order

## Phase 4 — Ship

- [ ] PR to `develop`

## Phase 5 — Close

- [ ] CLAUDE.md § KDPW: ChangeRequest bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-128 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-88 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell ChangeRequest × error-codes; status candidate; mirror of MM-101/MM-107/MM-113/MM-118/MM-124 pattern)
