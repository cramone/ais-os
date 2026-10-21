---
id: MM-150
type: plan
project: magiq-media
workstream: WS-110-registration-http-routes
repo: magiq-media
tags: [magiq-media, registration, http, routes, documents, correct-reference, erase, dispatch, receipt, revoke]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'Registration × write-model plan (new commands), MM-148 (error codes), MM-149 (integration events)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Registration × http-routes
---

# WS-110 — Registration HTTP routes: 5 missing + 1 non-spec deprecation

**Target repo:** `magiq-media`
**Depends on:** Registration × write-model, MM-148, MM-149

## Problem

Spec names 18 Registration routes. Code wires 13 (10 write + 3 read). Read-side matches spec (3 of 3). Write-side: 9 spec-matching + 1 non-spec = 10 total. Missing 5 of 15 write-side.

Missing (5):

| spec route | theme |
|---|---|
| `POST /v1/registrations/{registrationId}/correct-reference` | reference correction post-confirmation (`ReferenceRequired`) → emits `RegistrationReferenceCorrected` (MM-149) |
| `POST /v1/registrations/{registrationId}/erase-personal-data` | named `If-Match` exception |
| `POST /v1/registrations/{registrationId}/dispatch` | adapter callback — `SystemActorRequired` role; transitions Initiated → Submitted |
| `POST /v1/registrations/{registrationId}/receipt` | adapter callback — `SystemActorRequired` role; records authority receipt |
| `POST /v1/registrations/{registrationId}/revoke` | post-confirmation revocation (`RegistrationConfirmed` precedence) → emits `RegistrationRevoked` (MM-149) |

Spec→code map resolved under 2026-10-18 Arnica review re-diff:

| spec route | code endpoint folder (surprise) |
|---|---|
| `POST /registrations/{registrationId}/documents` | `AttachMediaItemToRegistration/AttachMediaItemToRegistrationEndpoint.cs` — endpoint-folder named for the Internal command concept, but route path matches spec exactly (`Post("/registrations/{registrationId}/documents")`). **Not missing.** Earlier draft listed it missing based on folder-name search; corrected on re-diff. Folder rename to `AttachRegistrationDocuments/` is an optional cleanup, not a scope item |

Non-spec code route (1):

| code endpoint | path | status |
|---|---|---|
| `RecordRegistrationSubmission` | `POST /registrations/{registrationId}/submission` | Non-spec — likely saga adapter callback masquerading as HTTP. Audit at Phase 1; deprecate for one release before removal if truly non-spec, or document as internal if dispatched by handler not HTTP |

## What the spec requires

- `CorrectRegistrationReferenceEndpoint` at `POST /correct-reference` → `CorrectRegistrationReferenceCommand`; refuses `ReferenceRequired 422`.
- `EraseRegistrationPersonalDataEndpoint` at `POST /erase-personal-data` — named `If-Match` exception per `api-conventions.md`.
- `DispatchRegistrationEndpoint` at `POST /dispatch` → `DispatchRegistrationCommand`; `SystemActorRequired 403` for `User` callers.
- `RecordRegistrationReceiptEndpoint` at `POST /receipt` → `RecordRegistrationReceiptCommand`; `SystemActorRequired 403`.
- `RevokeRegistrationEndpoint` at `POST /revoke` → `RevokeRegistrationCommand`; emits `RegistrationRevoked`.

## Wire-visibility

- Additive — 5 new routes.
- Dispatch + receipt bind to platform-integration `RegistrationAdapter` role (`actor.ActorType == "System"` required).
- Non-spec `POST /submission` deprecated for one release with `Deprecation: true` + `Sunset: <date>` headers before removal.

## Scope boundary

- Endpoint layer only.
- Commands + aggregate methods → MM-152 (Registration × write-model).
- Error codes → MM-148.
- Integration events for revoke / reference-correct / item-attached → MM-149.
- `RecordRegistrationSubmission` → audit at Phase 1; deprecate or document.
- `AttachMediaItemToRegistration` → **confirmed spec-matching** route (POST /registrations/{id}/documents); endpoint-folder rename to `AttachRegistrationDocuments/` optional.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-110 (plan MM-150). Registration × write-model must ship first (6 new commands). MM-148 + MM-149 land alongside.

## Phase 0 — Scope confirmation

- [ ] Registration × write-model plan shipped (6 new commands + aggregate methods)
- [ ] MM-148 constants reachable
- [ ] MM-149 integration events reachable

## Phase 1 — Audit non-spec code endpoints

- [ ] Trace `RecordRegistrationSubmission` (route `POST /submission`) — handler dispatch target? Decide retain-as-internal / deprecate-with-sunset / remove. Spec has no `/submission` route; its `POST /submit` is covered by `SubmitRegistration` endpoint
- [ ] `AttachMediaItemToRegistration` — **not non-spec** (confirmed on 2026-10-18 re-diff; route path matches spec `POST /registrations/{id}/documents`). Optional cleanup: rename endpoint folder to `AttachRegistrationDocuments/` for terminology alignment — not scoped to this plan

## Phase 2 — Missing endpoints (5)

- [ ] `CorrectRegistrationReferenceEndpoint` at `POST /v1/registrations/{registrationId}/correct-reference`
- [ ] `EraseRegistrationPersonalDataEndpoint` at `POST /v1/registrations/{registrationId}/erase-personal-data` (`If-Match` exempt)
- [ ] `DispatchRegistrationEndpoint` at `POST /v1/registrations/{registrationId}/dispatch` (`SystemActorRequired`)
- [ ] `RecordRegistrationReceiptEndpoint` at `POST /v1/registrations/{registrationId}/receipt` (`SystemActorRequired`)
- [ ] `RevokeRegistrationEndpoint` at `POST /v1/registrations/{registrationId}/revoke`

## Phase 2b — Non-spec deprecation

- [ ] If Phase 1 audit decides deprecate: `POST /submission` emits `Deprecation: true` + `Sunset: <ISO date>` headers for one release; sunset date lands in the migration note on breaking-changes.md

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
- 2026-10-18: re-diffed under Arnica review fix for finding #2 (narrow code scope). **Scope corrected: 6 → 5 missing.** `POST /registrations/{registrationId}/documents` was listed missing in draft; broader-glob code check confirms the route exists at `src/modules/Registration/Registrations.WriteModel.Endpoints/V1/Registrations/AttachMediaItemToRegistration/AttachMediaItemToRegistrationEndpoint.cs` (endpoint-folder named for the Internal command concept but route path matches spec exactly). Removed from missing list. 1 → 1 non-spec code route (`RecordRegistrationSubmission` at `POST /submission`); `AttachMediaItemToRegistration` reclassified clean. Code coverage: 13 of 18 spec routes (was undercounted as 12). Missing count 6 → 5. Title + Problem + What-spec-requires + Scope boundary + Phase 1 + Phase 2 updated.
