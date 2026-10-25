---
id: MM-058
type: plan
project: magiq-media
workstream: WS-48-registration-id-caller-supplied
repo: magiq-media
tags: [magiq-media, registration, idempotency, api]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-48.
---

# WS-48 — `InitiateRegistrationCommand.RegistrationId` caller-supplied + endpoint default + `409 RegistrationAlreadyExists`

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec: caller-supplied id (optional on `POST /v1/items/{itemId}/registrations`, defaulted at endpoint when absent, echoed in response, 409 on duplicate). Today code mints server-side.

## Session invocation

> Picking up WS-48 (plan MM-058). Add optional `registrationId` to `InitiateRegistrationCommand`. Endpoint defaults to UUID v7 when absent. Catch `AggregateAlreadyExistsException` (MM-007) → `409 RegistrationAlreadyExists`. Echo id in 201 response.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-007 (`AggregateAlreadyExistsException`) available
- [ ] Locate `InitiateRegistrationCommand` + endpoint

## Phase 1 — Command field
- [ ] Add nullable `RegistrationId` to command
- [ ] Endpoint: default to UUID v7 when absent

## Phase 2 — Handler
- [ ] Use caller id in aggregate create
- [ ] Catch `AggregateAlreadyExistsException` → `Result.Failure(RegistrationAlreadyExists)`
- [ ] Map → `409 RegistrationAlreadyExists`

## Phase 3 — Tests
- [ ] Unit: caller supplies id → aggregate created with it
- [ ] Unit: no id → endpoint defaults; aggregate created with v7
- [ ] Unit: duplicate caller id → 409
- [ ] Integration: Idempotency-Key + caller id doubly-idempotent

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] spec-divergence/INDEX.md: WS-48 → § Shipped
- [ ] Remove `InitiateRegistrationCommand.RegistrationId is caller-supplied` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
