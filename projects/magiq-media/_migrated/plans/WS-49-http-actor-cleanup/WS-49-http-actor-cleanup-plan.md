---
id: MM-059
type: plan
project: magiq-media
workstream: WS-49-http-actor-cleanup
repo: magiq-media
tags: [magiq-media, api, commands, auth]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-49.
---

# WS-49 — HTTP command actor-member cleanup

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec: HTTP commands read caller from `IExecutionContext`. Drop `AuthorId`, `RequestingUserId`, `OwnerId` (BulkCreateMediaItems/InitiateRegistration), `OfficerId`. Rename `CreateChangeRequestCommand.CreatedById` → `OwnerId`. Handler/saga-dispatched commands keep domain-significant actors (`DetachedBy`, `InitiatedBy`).

## Session invocation

> Picking up WS-49 (plan MM-059). Drop actor fields from HTTP command DTOs: `AddCommentCommand.AuthorId`, `EditCommentCommand.AuthorId`, `DeleteCommentCommand.RequestingUserId`, `BulkCreateMediaItemsCommand.OwnerId`, `InitiateRegistrationCommand.OfficerId`. Rename `CreateChangeRequestCommand.CreatedById` → `OwnerId`. Handlers read actor from `IExecutionContext`.

## Phase 0 — Scope confirmation
- [ ] Grep each named field across commands + handlers + endpoints
- [ ] Confirm `IExecutionContext.Actor` carries caller via JWT path

## Phase 1 — Drop fields
- [ ] Remove `AuthorId`, `RequestingUserId`, `OwnerId`, `OfficerId` from HTTP command DTOs
- [ ] Handlers read `IExecutionContext.Actor.Id` instead
- [ ] Endpoint validators updated

## Phase 2 — Rename
- [ ] `CreateChangeRequestCommand.CreatedById` → `OwnerId`
- [ ] Update handler + any projection

## Phase 3 — Keep domain-significant actors
- [ ] `DetachedBy`, `InitiatedBy` on handler/saga-dispatched commands remain (not HTTP)

## Phase 4 — Tests
- [ ] Unit per command: handler uses `IExecutionContext.Actor.Id`
- [ ] Integration: endpoint accepts command without actor field; call succeeds

## Phase 5 — Ship
- [ ] PR to `develop`
- [ ] Breaking change — document for client SDKs

## Phase 6 — Close
- [ ] spec-divergence/INDEX.md: WS-49 → § Shipped
- [ ] Remove `HTTP commands still carry actor members` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
