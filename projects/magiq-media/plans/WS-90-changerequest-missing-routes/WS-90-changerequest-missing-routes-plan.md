---
id: MM-130
type: plan
project: magiq-media
workstream: WS-90-changerequest-missing-routes
repo: magiq-media
tags: [magiq-media, change-requests, http, routes, lifecycle, participants, redact]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'ChangeRequest × write-model plan'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell ChangeRequest × http-routes
---

# WS-90 — ChangeRequest missing routes (7)

**Target repo:** `magiq-media`
**Depends on:** ChangeRequest × write-model cell plan (provides `CreateChangeRequest` / `OpenChangeRequest`, `ResolveChangeRequest`, `AbandonChangeRequest`, `ReopenChangeRequest`, `AddChangeRequestParticipant`, `RemoveChangeRequestParticipant`, `RedactChangeRequestComment` commands)

## Problem

Spec names 14 ChangeRequest HTTP routes. Code wires 7. Missing 7:

| spec route | theme |
|---|---|
| `POST /v1/change-requests` | create |
| `POST /v1/change-requests/{changeRequestId}/resolve` | lifecycle |
| `POST /v1/change-requests/{changeRequestId}/abandon` | lifecycle |
| `POST /v1/change-requests/{changeRequestId}/reopen` | lifecycle |
| `POST /v1/change-requests/{changeRequestId}/participants` | participants |
| `DELETE /v1/change-requests/{changeRequestId}/participants/{memberId}` | participants |
| `POST /v1/change-requests/{changeRequestId}/comments/{commentId}/redact` | comment lifecycle |

## What the spec requires

- `CreateChangeRequestEndpoint` at `POST /v1/change-requests` → `CreateChangeRequestCommand` (per CLAUDE.md § Key conventions: aggregate id caller-supplied).
- `ResolveChangeRequestEndpoint`, `AbandonChangeRequestEndpoint`, `ReopenChangeRequestEndpoint` — each dispatches lifecycle command (MM-129 integration events depend on these).
- `AddParticipantEndpoint` + `RemoveParticipantEndpoint` — participant management; refuse on cap (`TooManyParticipants` 100, MM-128) or absent (`ParticipantNotFound` / `ParticipantAlreadyAdded`).
- `RedactCommentEndpoint` — redact comment body (soft-erase retaining comment id for audit).

## Wire-visibility

Additive — 7 new routes.

## Scope boundary

- **Endpoint layer only.** Commands + aggregate methods belong to ChangeRequest × write-model.
- Error codes = MM-128. Integration events = MM-129.
- Middleware adoption = future ChangeRequest × middleware cell plan.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-90 (plan MM-130). ChangeRequest × write-model cell plan must ship first (7 new commands). Wire 7 endpoints.

## Phase 0 — Scope confirmation

- [ ] ChangeRequest × write-model plan shipped
- [ ] MM-128 error codes available
- [ ] Confirm current 7 wired routes

## Phase 1 — Lifecycle routes

- [ ] `CreateChangeRequestEndpoint` at `POST /v1/change-requests`
- [ ] `ResolveChangeRequestEndpoint` at `POST /v1/change-requests/{changeRequestId}/resolve`
- [ ] `AbandonChangeRequestEndpoint` at `POST /v1/change-requests/{changeRequestId}/abandon`
- [ ] `ReopenChangeRequestEndpoint` at `POST /v1/change-requests/{changeRequestId}/reopen`

## Phase 2 — Participant routes

- [ ] `AddParticipantEndpoint` at `POST /v1/change-requests/{changeRequestId}/participants`
- [ ] `RemoveParticipantEndpoint` at `DELETE /v1/change-requests/{changeRequestId}/participants/{memberId}`

## Phase 3 — Comment redact

- [ ] `RedactCommentEndpoint` at `POST /v1/change-requests/{changeRequestId}/comments/{commentId}/redact`

## Phase 4 — Tests

- [ ] Integration per route: happy path + guard precedence
- [ ] Integration: abandon via consumer path (MM-129) still works independently of this endpoint

## Phase 5 — Communicate

- [ ] Breaking-changes.md entry
- [ ] Coordinate with magiq-media-ui

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-130 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-90 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell ChangeRequest × http-routes; status candidate; depends on ChangeRequest × write-model plan)
