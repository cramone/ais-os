---
id: MM-125
type: plan
project: magiq-media
workstream: WS-85-mediaprofile-missing-routes
repo: magiq-media
tags: [magiq-media, catalog, mediaprofile, http, routes, change-request-policy, draft-name, abandon]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'MediaProfile × write-model plan'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell MediaProfile × http-routes
---

# WS-85 — MediaProfile missing routes (3) + non-spec detach deprecation

**Target repo:** `magiq-media`
**Depends on:** MediaProfile × write-model cell plan (provides `SetChangeRequestPolicyCommand`, `RenameMediaProfileDraftCommand`, `AbandonMediaProfileCommand`)

## Problem

Spec names 25 MediaProfile HTTP routes. Code wires 20 (plus 1 non-spec detach). 3 missing + 1 deprecation + 1 covered-elsewhere:

| spec route | plan |
|---|---|
| `PUT /v1/profiles/{profileId}/change-request-policy` | **this plan** |
| `PUT /v1/profiles/{profileId}/draft/name` | **this plan** |
| `POST /v1/profiles/{profileId}/abandon` | **this plan** |
| `GET /v1/capability-field-groups/{capability}/versions/{version}` | WS-54 (MM-030) |

Non-spec in code (1):
- `DELETE /v1/profiles/{profileId}/record-types/{recordTypeId}` (`DetachRecordTypeEndpoint`) — spec doesn't list this. Deprecate with `Deprecation` + `Sunset` headers for one release before removal. Migration: re-pin to a different version via `POST /record-types/{recordTypeId}` or re-publish without the record type.

## What the spec requires

- `SetChangeRequestPolicyEndpoint` at `PUT /v1/profiles/{profileId}/change-request-policy` → `SetChangeRequestPolicyCommand`. Payload per `mediaprofile.api.md § Request body` (`Policy: NotRequired | OptionalForEdit | RequiredForEdit`).
- `RenameMediaProfileDraftEndpoint` at `PUT /v1/profiles/{profileId}/draft/name` → `RenameMediaProfileDraftCommand`. Payload: `{ Name }`. Refuses `MediaProfileNameConflict 409` (MM-124) on duplicate.
- `AbandonMediaProfileEndpoint` at `POST /v1/profiles/{profileId}/abandon` → `AbandonMediaProfileCommand`. Terminates a draft that was never published; releases the name reservation.
- `DELETE /v1/profiles/{profileId}/record-types/{recordTypeId}` keeps 2xx + emits `Deprecation: true` + `Sunset: <ISO date>` for one release; removed after sunset.

## Wire-visibility

- Additive — 3 new routes.
- Breaking — `DELETE /record-types/{recordTypeId}` deprecated.

## Scope boundary

- **Endpoint layer only.** Commands + handlers + aggregate methods belong to MediaProfile × write-model cell plan. This plan dispatches commands.
- **Not in scope:** error-code wiring (MM-124), middleware (future MediaProfile × middleware cell), capability-field-groups route (WS-54).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-85 (plan MM-125). MediaProfile × write-model cell plan must ship first (SetChangeRequestPolicy, RenameMediaProfileDraft, AbandonMediaProfile commands). Wire 3 endpoints + deprecate DELETE /record-types/{recordTypeId}.

## Phase 0 — Scope confirmation

- [ ] MediaProfile × write-model plan shipped (3 new commands + aggregate methods)
- [ ] MM-124 error codes available
- [ ] WS-54 shipped (capability-field-groups route lands under it)

## Phase 1 — Additive routes

- [ ] `SetChangeRequestPolicyEndpoint` at `PUT /v1/profiles/{profileId}/change-request-policy`
- [ ] `RenameMediaProfileDraftEndpoint` at `PUT /v1/profiles/{profileId}/draft/name`
- [ ] `AbandonMediaProfileEndpoint` at `POST /v1/profiles/{profileId}/abandon`
- [ ] Each: guard precedence, 204 on success, `Version(1)`

## Phase 2 — Deprecate non-spec DELETE

- [ ] `DetachRecordTypeEndpoint` keeps `DELETE /v1/profiles/{profileId}/record-types/{recordTypeId}` route for one release
- [ ] Response emits `Deprecation: true` + `Sunset: <ISO date>` headers
- [ ] Release notes name sunset date + migration (re-pin via POST + republish or re-publish without record type)

## Phase 3 — Tests

- [ ] Integration per new route: happy path + guard precedence
- [ ] Integration: rename draft → name reservation collision refuses `MediaProfileNameConflict 409` (MM-124)
- [ ] Integration: abandon → draft disappears + name released
- [ ] Integration: `DELETE /record-types/{recordTypeId}` still works + emits deprecation headers

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry — API wire additive + deprecation
- [ ] Release notes
- [ ] Coordinate with magiq-media-ui

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-125 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-85 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaProfile × http-routes; status candidate; depends on MediaProfile × write-model plan)
