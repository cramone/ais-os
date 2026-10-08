---
id: MM-061
type: plan
project: magiq-media
workstream: WS-43-document-signing-read-model-keys
repo: magiq-media
tags: [magiq-media, document-signing, read-model, dynamodb]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-43.
---

# WS-43 — `DocumentSigning` read-model keys

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec: detail + summary rows keyed `TENANT#{TenantId}#SIGNING_SESSION#{SigningSessionId}`. Code registers no schema identifier today.

## Session invocation

> Picking up WS-43 (plan MM-061). Register key convention for `media-document-signing-sessions` detail + summary. Projector + endpoint read it. Confirm no existing deployed data (greenfield).

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/document-signing/signingsession.read-model.md`
- [ ] Current DocumentSigning read-model schema

## Phase 1 — Key registration
- [ ] PK: `TENANT#{TenantId}#SIGNING_SESSION#{SigningSessionId}`
- [ ] SK pattern per spec (detail + summary rows)
- [ ] Projector writes to these keys

## Phase 2 — Endpoint reads
- [ ] `GET /v1/signing-sessions/{id}` reads detail row
- [ ] List endpoint reads summary rows

## Phase 3 — Tests
- [ ] Unit: projector writes correct keys
- [ ] Integration: endpoints resolve

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] spec-divergence/INDEX.md: WS-43 → § Shipped
- [ ] Remove `DocumentSigning read-model keys` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
