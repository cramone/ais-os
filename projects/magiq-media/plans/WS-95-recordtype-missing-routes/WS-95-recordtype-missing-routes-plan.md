---
id: MM-135
type: plan
project: magiq-media
workstream: WS-95-recordtype-missing-routes
repo: magiq-media
tags: [magiq-media, metadata, recordtype, http, routes, clone, deprecate, reinstate, supersession, abandon, latest]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'RecordType × write-model plan, WS-53'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell RecordType × http-routes
---

# WS-95 — RecordType routes: 7 missing + 2 path divergences + 2 deprecations

**Target repo:** `magiq-media`
**Depends on:** RecordType × write-model cell plan (new commands); WS-53 (RecordType capabilities removal)

## Problem

Spec names 24 RecordType HTTP routes. Code wires 19 (plus 2 non-spec capabilities routes).

Missing (7):

| spec route | theme |
|---|---|
| `POST /v1/record-types/{recordTypeId}/clone` | create |
| `POST /v1/record-types/{recordTypeId}/versions/{version}/deprecate` | version lifecycle |
| `POST /v1/record-types/{recordTypeId}/reinstate` | lifecycle |
| `POST /v1/record-types/{recordTypeId}/supersession` | lifecycle |
| `POST /v1/record-types/{recordTypeId}/abandon` | lifecycle |
| `GET /v1/record-types/{recordTypeId}/versions/latest` | read |
| `GET /v1/record-types/{recordTypeId}/history` | read |

Path divergences (2):

| code route | spec route |
|---|---|
| `PUT /v1/record-types/{recordTypeId}/fields/{fieldName}` | `POST /v1/record-types/{recordTypeId}/fields/{fieldName}/replace` |
| `POST /v1/record-types/{recordTypeId}/draft/fields/{fieldName}/deprecate` | `POST /v1/record-types/{recordTypeId}/fields/{fieldName}/deprecate` (no `/draft/`) |

Non-spec deprecations (2) — WS-53 covers:

| code route | status |
|---|---|
| `POST /v1/record-types/{recordTypeId}/capabilities` | WS-53 removal |
| `DELETE /v1/record-types/{recordTypeId}/capabilities/{capabilityType}` | WS-53 removal |

## What the spec requires

- `CloneRecordTypeEndpoint` at `POST /clone` → `CloneRecordTypeCommand`.
- `DeprecateRecordTypeVersionEndpoint` at `POST /versions/{version}/deprecate` → `DeprecateRecordTypeVersionCommand`; emits `RecordTypeVersionDeprecated` (MM-134).
- `ReinstateRecordTypeEndpoint` at `POST /reinstate` → `ReinstateRecordTypeCommand`; emits `RecordTypeReinstated` (MM-134). Refuses `RecordTypeNotDeprecated 422` (MM-133).
- `SupersessionEndpoint` at `POST /supersession` → `RecordRecordTypeSupersessionCommand`; emits `RecordTypeSupersessionRecorded` (MM-134).
- `AbandonRecordTypeEndpoint` at `POST /abandon` → `AbandonRecordTypeCommand`; refuses `RecordTypeAlreadyPublished 422` (MM-133).
- `GetLatestRecordTypeVersionEndpoint` at `GET /versions/latest` — reads the latest published version row from `media-record-type-versions`.
- `GetRecordTypeHistoryEndpoint` at `GET /history` — reads `media-record-type-history` (per catalog table).

Path moves (2):
- Rename replace route: `PUT /fields/{fieldName}` → `POST /fields/{fieldName}/replace`. Deprecate PUT with `Deprecation`/`Sunset` headers; new POST starts serving simultaneously.
- Rename deprecate route: `POST /draft/fields/{fieldName}/deprecate` → `POST /fields/{fieldName}/deprecate`. Deprecate old path with headers; new path lands simultaneously.

Capabilities removal (2) — WS-53's scope; this plan just notes the removal in release notes alongside its own changes.

## Wire-visibility

- Additive — 7 new routes.
- Breaking — 2 path renames (deprecate window) + 2 capabilities routes removed by WS-53.

## Scope boundary

- Endpoint layer only. Commands + aggregate methods → RecordType × write-model.
- Error codes → MM-133.
- Integration events for `reinstate` / `supersession` / `version-deprecate` → MM-134.
- Capabilities removal → WS-53.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-95 (plan MM-135). RecordType × write-model cell plan must ship first (clone, deprecate-version, reinstate, supersession, abandon commands). WS-53 removes capabilities routes.

## Phase 0 — Scope confirmation

- [ ] RecordType × write-model plan shipped
- [ ] WS-53 shipped (capabilities removal)
- [ ] MM-133 reachable

## Phase 1 — Missing endpoints

- [ ] `CloneRecordTypeEndpoint` at `POST /v1/record-types/{recordTypeId}/clone`
- [ ] `DeprecateRecordTypeVersionEndpoint` at `POST /v1/record-types/{recordTypeId}/versions/{version}/deprecate`
- [ ] `ReinstateRecordTypeEndpoint` at `POST /v1/record-types/{recordTypeId}/reinstate`
- [ ] `SupersessionEndpoint` at `POST /v1/record-types/{recordTypeId}/supersession`
- [ ] `AbandonRecordTypeEndpoint` at `POST /v1/record-types/{recordTypeId}/abandon`
- [ ] `GetLatestRecordTypeVersionEndpoint` at `GET /v1/record-types/{recordTypeId}/versions/latest`
- [ ] `GetRecordTypeHistoryEndpoint` at `GET /v1/record-types/{recordTypeId}/history`

## Phase 2 — Path renames (deprecate window)

- [ ] `POST /fields/{fieldName}/replace` served alongside existing `PUT /fields/{fieldName}`; PUT emits `Deprecation`/`Sunset` headers
- [ ] `POST /fields/{fieldName}/deprecate` served alongside existing `/draft/fields/{fieldName}/deprecate`; old path emits `Deprecation`/`Sunset`

## Phase 3 — Tests

- [ ] Integration per new route: happy path + guard precedence
- [ ] Integration: `reinstate` → emits `media.recordtype.reinstated` (MM-134)
- [ ] Integration: `supersession` → emits `media.recordtype.supersession-recorded` (MM-134)
- [ ] Integration: path-rename deprecation headers emitted

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry — API wire additive + 2 path deprecations
- [ ] Release-notes line

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-135 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-95 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RecordType × http-routes; status candidate; depends on RecordType × write-model + WS-53)
