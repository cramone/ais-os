---
id: MM-141
type: plan
project: magiq-media
workstream: WS-101-retentionschedule-http-routes
repo: magiq-media
tags: [magiq-media, metadata, retentionschedule, http, routes, lifecycle]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'RetentionSchedule × write-model (commands + aggregate), RetentionSchedule × read-model (history/latest readers), MM-139, MM-140'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell RetentionSchedule × http-routes
---

# WS-101 — RetentionSchedule HTTP routes: 16 new endpoints

**Target repo:** `magiq-media`
**Depends on:** RetentionSchedule × write-model + read-model, MM-139, MM-140

## Problem

Spec names 16 RetentionSchedule HTTP routes. Code wires zero — aggregate wholly unbuilt.

| verb | path | kind |
|---|---|---|
| POST | `/v1/retention-schedules` | create |
| POST | `/v1/retention-schedules/{retentionScheduleId}/draft` | draft lifecycle |
| PUT | `/v1/retention-schedules/{retentionScheduleId}/draft` | draft edit |
| DELETE | `/v1/retention-schedules/{retentionScheduleId}/draft` | draft discard |
| POST | `/v1/retention-schedules/{retentionScheduleId}/publish` | publish |
| PATCH | `/v1/retention-schedules/{retentionScheduleId}` | metadata (display name, description) |
| POST | `/v1/retention-schedules/{retentionScheduleId}/abandon` | abandon pre-publish |
| POST | `/v1/retention-schedules/{retentionScheduleId}/deprecate` | whole-schedule deprecate |
| POST | `/v1/retention-schedules/{retentionScheduleId}/versions/{version}/deprecate` | version-level deprecate |
| POST | `/v1/retention-schedules/{retentionScheduleId}/supersession` | record supersession |
| GET | `/v1/retention-schedules` | list |
| GET | `/v1/retention-schedules/{retentionScheduleId}` | detail |
| GET | `/v1/retention-schedules/{retentionScheduleId}/versions` | version list |
| GET | `/v1/retention-schedules/{retentionScheduleId}/versions/{version}` | version detail |
| GET | `/v1/retention-schedules/{retentionScheduleId}/versions/latest` | latest published |
| GET | `/v1/retention-schedules/{retentionScheduleId}/history` | audit timeline |

## What the spec requires

- `CreateRetentionScheduleEndpoint` → `CreateRetentionScheduleCommand`; caller-supplied `retentionScheduleId` (UUID v7); `409 RetentionScheduleAlreadyExists` on duplicate; `409 RetentionScheduleNameConflict` carries `conflictingRetentionScheduleId` extension (MM-139).
- `CreateRetentionScheduleDraftEndpoint` → `CreateRetentionScheduleDraftCommand`; refuses `409 RetentionScheduleDraftAlreadyInProgress`, `422 RetentionScheduleNothingToRevise`.
- `UpdateRetentionScheduleDraftEndpoint` (PUT) → `UpdateRetentionScheduleDraftCommand`; whole-draft replace; `409 RetentionScheduleNoActiveDraft`.
- `DiscardRetentionScheduleDraftEndpoint` (DELETE) → `DiscardRetentionScheduleDraftCommand`; refuses `422 CannotDiscardInitialRetentionScheduleDraft`.
- `PublishRetentionScheduleEndpoint` → `PublishRetentionScheduleCommand`; emits `RetentionSchedulePublished` + integration event (MM-140); refuses `409 RetentionScheduleNoActiveDraft`.
- `UpdateRetentionScheduleMetadataEndpoint` (PATCH) → display-name/description patches.
- `AbandonRetentionScheduleEndpoint` → refuses `422 RetentionScheduleAlreadyPublished`.
- `DeprecateRetentionScheduleEndpoint` → whole-schedule; refuses `422 RetentionScheduleNotPublished`, `422 RetentionScheduleAlreadyDeprecated`.
- `DeprecateRetentionScheduleVersionEndpoint` → version-level; refuses `422 RetentionScheduleVersionAlreadyDeprecated`, `422 CannotDeprecateLastRetentionScheduleVersion`.
- `RecordRetentionScheduleSupersessionEndpoint` → `RecordRetentionScheduleSupersessionCommand`; refuses `422 RetentionScheduleNotDeprecated`, `422 RetentionScheduleSupersessionAlreadyRecorded`, `422 InvalidSupersededByRetentionSchedule`.
- 6 GET endpoints — list, detail, version list, version detail, latest, history. All driven by read-model.

## Wire-visibility

- Additive — 16 new routes.

## Scope boundary

- Endpoint layer only (`Metadata.WriteModel.Endpoints` + `Metadata.ReadModel.Endpoints`).
- Commands + aggregate → RetentionSchedule × write-model.
- Read-model shape + projector → RetentionSchedule × read-model.
- Error codes → MM-139.
- Integration events → MM-140.
- MediaItem's `PUT /items/{itemId}/retention-schedule` is MediaItem scope (MM-120).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-101 (plan MM-141). RetentionSchedule × write-model + read-model must ship first (commands, aggregate, read-models). MM-139 (error codes) + MM-140 (integration events) in flight.

## Phase 0 — Scope confirmation

- [ ] RetentionSchedule × write-model shipped (commands + aggregate)
- [ ] RetentionSchedule × read-model shipped (summary + detail + version + history readers)
- [ ] MM-139 constants reachable
- [ ] MM-140 integration events reachable

## Phase 1 — Write-side endpoints (10)

- [ ] `CreateRetentionScheduleEndpoint` at `POST /v1/retention-schedules`
- [ ] `CreateRetentionScheduleDraftEndpoint` at `POST /{id}/draft`
- [ ] `UpdateRetentionScheduleDraftEndpoint` at `PUT /{id}/draft`
- [ ] `DiscardRetentionScheduleDraftEndpoint` at `DELETE /{id}/draft`
- [ ] `PublishRetentionScheduleEndpoint` at `POST /{id}/publish`
- [ ] `UpdateRetentionScheduleMetadataEndpoint` at `PATCH /{id}`
- [ ] `AbandonRetentionScheduleEndpoint` at `POST /{id}/abandon`
- [ ] `DeprecateRetentionScheduleEndpoint` at `POST /{id}/deprecate`
- [ ] `DeprecateRetentionScheduleVersionEndpoint` at `POST /{id}/versions/{version}/deprecate`
- [ ] `RecordRetentionScheduleSupersessionEndpoint` at `POST /{id}/supersession`

## Phase 2 — Read-side endpoints (6)

- [ ] `ListRetentionSchedulesEndpoint` at `GET /v1/retention-schedules`
- [ ] `GetRetentionScheduleEndpoint` at `GET /{id}`
- [ ] `ListRetentionScheduleVersionsEndpoint` at `GET /{id}/versions`
- [ ] `GetRetentionScheduleVersionEndpoint` at `GET /{id}/versions/{version}`
- [ ] `GetLatestRetentionScheduleVersionEndpoint` at `GET /{id}/versions/latest`
- [ ] `GetRetentionScheduleHistoryEndpoint` at `GET /{id}/history`

## Phase 3 — Tests

- [ ] Integration per route: happy path + guard precedence
- [ ] Integration: publish → emits `media.retentionschedule.published` (MM-140)
- [ ] Integration: version-deprecate → emits `media.retentionschedule.version-deprecated` (MM-140)
- [ ] Integration: supersession → emits `media.retentionschedule.supersession-recorded` (MM-140)

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry — API wire additive
- [ ] Release-notes line

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-141 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-101 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RetentionSchedule × http-routes; aggregate wholly unbuilt; depends on write-model + read-model + MM-139 + MM-140)
