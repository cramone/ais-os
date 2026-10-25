---
id: MM-142
type: plan
project: magiq-media
workstream: WS-102-retentionschedule-read-model
repo: magiq-media
tags: [magiq-media, metadata, retentionschedule, read-model, dynamodb, projector, catalog-index]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'RetentionSchedule × write-model (domain events), MM-140 (integration events feed Catalog consumer), MM-141 (readers)'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell RetentionSchedule × read-model
---

# WS-102 — RetentionSchedule read-model: 6 new tables + projectors + Catalog reference index

**Target repo:** `magiq-media`
**Depends on:** RetentionSchedule × write-model, MM-140, MM-141

## Problem

Spec names 6 read-model tables (5 Metadata-side + 1 Catalog reference index). Code has zero — aggregate wholly unbuilt.

| table | PK | SK | module | shape |
|---|---|---|---|---|
| `media-retention-schedule` | `TENANT#{TenantId}#RETENTION_SCHEDULE#{RetentionScheduleId}` | `DETAIL` | Metadata | `RetentionScheduleDetailReadModel` |
| `media-retention-schedule-history` | `TENANT#{TenantId}#RETENTION_SCHEDULE#{RetentionScheduleId}` | `{AggregateVersion:D10}` | Metadata | `RetentionScheduleHistoryReadModel` |
| `media-retention-schedule-version` | `TENANT#{TenantId}#RETENTION_SCHEDULE_VERSIONS#{RetentionScheduleId}` | `{Version:D10}` | Metadata | `RetentionScheduleVersionDetailReadModel` |
| `media-retention-schedule-versions` | `TENANT#{TenantId}#RETENTION_SCHEDULE_VERSIONS#{RetentionScheduleId}` | `{Version:D10}` | Metadata | `RetentionScheduleVersionSummaryReadModel` |
| `media-retention-schedules` | `TENANT#{TenantId}#RETENTION_SCHEDULES` | `SUMMARY#{RetentionScheduleId}` | Metadata | `RetentionScheduleSummaryReadModel` |
| `media-catalog-retention-schedule-index` | version `TENANT#{TenantId}#RETENTION_SCHEDULE#{RetentionScheduleId}`; marker `TENANT#{TenantId}#RETENTION_SCHEDULE#DEPRECATED` | version `{Version:D10}`; marker `{RetentionScheduleId}` | Catalog.WriteModel | `RetentionScheduleVersionReference` |

## What the spec requires

- 5 Metadata-side ReadModels + schemas + projectors subscribing to RetentionSchedule domain events (`RetentionScheduleCreated`, `RetentionScheduleDraftCreated`/`Updated`/`Discarded`, `RetentionSchedulePublished`, `RetentionScheduleMetadataUpdated`, `RetentionScheduleAbandoned`, `RetentionScheduleDeprecated`, `RetentionScheduleVersionDeprecated`, `RetentionScheduleSupersessionRecorded`).
- CDK: register all 5 tables + `read-model-metadata` seed rows (WS-55 mechanism).
- Catalog's `media-catalog-retention-schedule-index` + `RetentionScheduleVersionReference` entity + `RetentionSchedulePublishedEventHandler` + `RetentionScheduleDeprecatedEventHandler` + `RetentionScheduleVersionDeprecatedEventHandler` consuming MM-140 integration events.
- Projection replay CLI covers RetentionSchedule (adds to existing 6-of-11 count).

## Scope boundary

- Read-model shape + schemas + projectors + CDK table provision.
- Metadata-side domain events → RetentionSchedule × write-model.
- Catalog-side consumer handlers (fed by MM-140 SNS) land here (owning module = Catalog; cross-module OK).
- Projection replay CLI (`projections replay retention-schedule`) added to `src/tools/ProjectionReplay`.
- No wire visibility — row shapes only.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-102 (plan MM-142). RetentionSchedule × write-model must ship first (domain events). MM-140 (integration events) feeds the Catalog consumer.

## Phase 0 — Scope confirmation

- [ ] RetentionSchedule × write-model shipped
- [ ] MM-140 integration events reachable

## Phase 1 — Metadata-side tables (5)

- [ ] `RetentionScheduleDetailReadModel` + schema + projector for `media-retention-schedule`
- [ ] `RetentionScheduleHistoryReadModel` + schema + projector for `media-retention-schedule-history`
- [ ] `RetentionScheduleVersionDetailReadModel` + schema + projector for `media-retention-schedule-version`
- [ ] `RetentionScheduleVersionSummaryReadModel` + schema + projector for `media-retention-schedule-versions`
- [ ] `RetentionScheduleSummaryReadModel` + schema + projector for `media-retention-schedules`

## Phase 2 — Catalog-side reference index

- [ ] CDK: `media-catalog-retention-schedule-index` table in `cdk-magiq-media`
- [ ] `RetentionScheduleVersionReference` entity under `Catalog.WriteModel/References/`
- [ ] `RetentionSchedulePublishedEventHandler` consumer (MM-140 feed) writes version row
- [ ] `RetentionScheduleDeprecatedEventHandler` writes marker row
- [ ] `RetentionScheduleVersionDeprecatedEventHandler` flips version row to deprecated

## Phase 3 — CDK + seed

- [ ] All 6 tables registered in `cdk-magiq-media` manifest
- [ ] `read-model-metadata` seed row per table (WS-55 construct)

## Phase 4 — Replay CLI

- [ ] `projections replay retention-schedule` verb in `src/tools/ProjectionReplay` (expands coverage 6/11 → 7/11)

## Phase 5 — Tests

- [ ] Projector per table: domain event → row + `ProjectedVersion` monotonic
- [ ] Catalog consumer: MM-140 SNS → version-reference row + marker on deprecate
- [ ] Replay CLI: full stream → identical rows

## Phase 6 — Communicate change

- [ ] No `breaking-changes.md` entry — row shapes only

## Phase 7 — Ship

- [ ] PR to `develop` (magiq-media) + `spec/initial-alignment` (cdk-magiq-media)

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-142 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-102 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RetentionSchedule × read-model; aggregate wholly unbuilt; depends on write-model + MM-140 + MM-141)
