---
id: MM-150
type: plan
project: magiq-media
workstream: WS-110-registration-http-routes
repo: magiq-media
tags: [magiq-media, registration, http, routes, documents, correct-reference, erase, dispatch, receipt, revoke]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'Registration × write-model plan (new commands), MM-148 (error codes), MM-149 (integration events)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Registration × http-routes
---

# WS-110 — Registration HTTP routes: 6 missing + 2 non-spec

**Target repo:** `magiq-media`
**Depends on:** Registration × write-model, MM-148, MM-149

## Problem

Spec names 18 Registration routes. Code wires 12 (10 write + 3 read). Read-side matches spec (3 of 3). Write-side missing 6.

Missing (6):

| spec route | theme |
|---|---|
| `POST /v1/registrations/{registrationId}/documents` | attach supporting documents (`NoDocumentsAttached` precondition prep) |
| `POST /v1/registrations/{registrationId}/correct-reference` | reference correction post-confirmation (`ReferenceRequired`) → emits `RegistrationReferenceCorrected` (MM-149) |
| `POST /v1/registrations/{registrationId}/erase-personal-data` | named `If-Match` exception |
| `POST /v1/registrations/{registrationId}/dispatch` | adapter callback — `SystemActorRequired` role; transitions Initiated → Submitted |
| `POST /v1/registrations/{registrationId}/receipt` | adapter callback — `SystemActorRequired` role; records authority receipt |
| `POST /v1/registrations/{registrationId}/revoke` | post-confirmation revocation (`RegistrationConfirmed` precedence) → emits `RegistrationRevoked` (MM-149) |

Non-spec code routes to audit (possible internal handler endpoints):

| code endpoint | status |
|---|---|
| `AttachMediaItemToRegistration` | audit whether exposed over HTTP; spec attaches via `POST /items/{itemId}/registrations` body |
| `RecordRegistrationSubmission` | audit — likely handler-dispatched (saga adapter callback), not HTTP |

## What the spec requires

- `AttachRegistrationDocumentsEndpoint` at `POST /documents` → `AttachRegistrationDocumentsCommand`.
- `CorrectRegistrationReferenceEndpoint` at `POST /correct-reference` → `CorrectRegistrationReferenceCommand`; refuses `ReferenceRequired 422`.
- `EraseRegistrationPersonalDataEndpoint` at `POST /erase-personal-data` — named `If-Match` exception per `api-conventions.md`.
- `DispatchRegistrationEndpoint` at `POST /dispatch` → `DispatchRegistrationCommand`; `SystemActorRequired 403` for `User` callers.
- `RecordRegistrationReceiptEndpoint` at `POST /receipt` → `RecordRegistrationReceiptCommand`; `SystemActorRequired 403`.
- `RevokeRegistrationEndpoint` at `POST /revoke` → `RevokeRegistrationCommand`; emits `RegistrationRevoked`.

## Wire-visibility

- Additive — 6 new routes.
- Dispatch + receipt bind to platform-integration `RegistrationAdapter` role (`actor.ActorType == "System"` required).

## Scope boundary

- Endpoint layer only.
- Commands + aggregate methods → Registration × write-model.
- Error codes → MM-148.
- Integration events for revoke / reference-correct → MM-149.
- Non-spec `AttachMediaItemToRegistration` / `RecordRegistrationSubmission` — audit under this plan; migrate or document.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-110 (plan MM-150). Registration × write-model must ship first (6 new commands). MM-148 + MM-149 land alongside.

## Phase 0 — Scope confirmation

- [ ] Registration × write-model plan shipped (6 new commands + aggregate methods)
- [ ] MM-148 constants reachable
- [ ] MM-149 integration events reachable

## Phase 1 — Audit non-spec code endpoints

- [ ] Trace `AttachMediaItemToRegistration` — HTTP endpoint vs handler dispatch; decide retain / deprecate / rename
- [ ] Trace `RecordRegistrationSubmission` — likely saga adapter callback; retain if internal

## Phase 2 — Missing endpoints (6)

- [ ] `AttachRegistrationDocumentsEndpoint` at `POST /v1/registrations/{registrationId}/documents`
- [ ] `CorrectRegistrationReferenceEndpoint` at `POST /v1/registrations/{registrationId}/correct-reference`
- [ ] `EraseRegistrationPersonalDataEndpoint` at `POST /v1/registrations/{registrationId}/erase-personal-data` (`If-Match` exempt)
- [ ] `DispatchRegistrationEndpoint` at `POST /v1/registrations/{registrationId}/dispatch` (`SystemActorRequired`)
- [ ] `RecordRegistrationReceiptEndpoint` at `POST /v1/registrations/{registrationId}/receipt` (`SystemActorRequired`)
- [ ] `RevokeRegistrationEndpoint` at `POST /v1/registrations/{registrationId}/revoke`

## Phase 3 — Tests

- [ ] Integration per new route: happy path + guard precedence
- [ ] Integration: dispatch/receipt refuses `User` actor with `SystemActorRequired 403`
- [ ] Integration: revoke → emits `media.registration.revoked` (MM-149)
- [ ] Integration: correct-reference → emits `media.registration.reference-corrected` (MM-149)
- [ ] Integration: erase-personal-data without `If-Match` → 2xx (not 428)

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry — API wire additive (6 new routes)
- [ ] Release-notes line

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-150 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-110 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell Registration × http-routes; 6 missing routes incl. 2 adapter-callback `SystemActorRequired` + `erase-personal-data` If-Match exemption; depends on Registration × write-model + MM-148 + MM-149)
