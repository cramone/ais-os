---
id: MM-140
type: plan
project: magiq-media
workstream: WS-100-retentionschedule-integration-events
repo: magiq-media
tags: [magiq-media, metadata, retentionschedule, integration-events, mapper, sns, catalog-index]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'RetentionSchedule × write-model plan (domain events), MM-139 (error codes)'
breaking-change: Process wire — additive
source: alignment-sweep-2026-10-15 cell RetentionSchedule × integration-events
---

# WS-100 — RetentionSchedule integration events: 4 new types + Catalog consumer

**Target repo:** `magiq-media`
**Depends on:** RetentionSchedule × write-model plan (domain events + mapper), MM-139

## Problem

Spec names 4 RetentionSchedule integration event types. Code publishes zero — aggregate wholly unbuilt.

| spec type | domain event | consumer |
|---|---|---|
| `media.retentionschedule.published` | `RetentionSchedulePublished` | Catalog `media-catalog-retention-schedule-index` projector |
| `media.retentionschedule.deprecated` | `RetentionScheduleDeprecated` | Catalog (type marker) |
| `media.retentionschedule.version-deprecated` | `RetentionScheduleVersionDeprecated` | Catalog |
| `media.retentionschedule.supersession-recorded` | `RetentionScheduleSupersessionRecorded` | Catalog |

Underlying domain events absent in code (build under RetentionSchedule × write-model plan). `RetentionScheduleDomainEventMapper` + `Metadata.Contracts/Events/RetentionSchedules/*IntegrationEvent.cs` records absent. CDK filter-policy entries for Catalog consumers absent.

## What the spec requires

- `RetentionSchedulePublishedIntegrationEvent { TenantId, RetentionScheduleId, RetentionScheduleName, Version, PublishedAt, PublishedBy }` — carries the published definition needed by Catalog's index projector.
- `RetentionScheduleDeprecatedIntegrationEvent { TenantId, RetentionScheduleId, DeprecatedAt, Reason? }` — Catalog flips index row to deprecated.
- `RetentionScheduleVersionDeprecatedIntegrationEvent { TenantId, RetentionScheduleId, Version, DeprecatedAt, Reason? }`.
- `RetentionScheduleSupersessionRecordedIntegrationEvent { TenantId, RetentionScheduleId, SupersededByRetentionScheduleId, RecordedAt }`.
- `RetentionScheduleDomainEventMapper` with 4 `Map` overloads, registered with the module's integration-event publishing wire.
- CDK filter policies in `cdk-magiq-media` admit the 4 new `type` values to Catalog's `media-catalog-retention-schedule-index` projector queue.

## Wire-visibility

- Additive — 4 new SNS message types; existing filter policies ignore unknown types until CDK edits land.

## Scope boundary

- Contract records + mapper + CDK filter-policy edits.
- Domain events + aggregate → RetentionSchedule × write-model.
- Catalog projector + `media-catalog-retention-schedule-index` row-shape → Catalog × read-model plan (future / separate cell).
- Error codes → MM-139.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-100 (plan MM-140). RetentionSchedule × write-model must ship first (domain events). MM-139 (error codes) + Catalog × read-model (`media-catalog-retention-schedule-index` projector) land in parallel.

## Phase 0 — Scope confirmation

- [ ] RetentionSchedule × write-model shipped (domain events)
- [ ] MM-139 constants reachable

## Phase 1 — Contract records

- [ ] `RetentionSchedulePublishedIntegrationEvent` under `Metadata.Contracts/Events/RetentionSchedules/`
- [ ] `RetentionScheduleDeprecatedIntegrationEvent`
- [ ] `RetentionScheduleVersionDeprecatedIntegrationEvent`
- [ ] `RetentionScheduleSupersessionRecordedIntegrationEvent`

## Phase 2 — Mapper

- [ ] `RetentionScheduleDomainEventMapper` with `Map(RetentionSchedulePublished)` etc.
- [ ] Mapper registered on write-model publishing wire
- [ ] Each `type` string: `media.retentionschedule.<verb>` per catalog

## Phase 3 — CDK filter policies

- [ ] `cdk-magiq-media` admits the 4 new types to Catalog's retention-schedule-index projector queue; `FilterPolicyScope: MessageBody` on `type`
- [ ] Deployed before magiq-media host rollout

## Phase 4 — Tests

- [ ] Integration: `PublishRetentionSchedule` → outbox → SNS → body carries `type` + payload members
- [ ] Integration: each of 4 types routes to Catalog projector queue

## Phase 5 — Communicate change

- [ ] Breaking-changes.md entry — Process wire additive

## Phase 6 — Ship

- [ ] PR to `develop` (magiq-media) + `spec/initial-alignment` (cdk-magiq-media)

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-140 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-100 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RetentionSchedule × integration-events; mirror of MM-134 pattern; aggregate wholly unbuilt)
