---
id: MM-143
type: plan
project: magiq-media
workstream: WS-103-retentionschedule-write-model
repo: magiq-media
tags: [magiq-media, metadata, retentionschedule, write-model, aggregate, domain-events, commands, snapshot]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-139 (error codes constants), WS-57 (snapshot revision)'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell RetentionSchedule × write-model
---

# WS-103 — RetentionSchedule write-model: aggregate + 10 domain events + commands

**Target repo:** `magiq-media`
**Depends on:** MM-139 (error codes constants), WS-57

## Problem

Spec names 10 RetentionSchedule domain events + an aggregate class with ValueObjects (`RetentionScheduleId`, `RetentionScheduleName`, `RetentionDefinition`, `RetentionPeriod`, `RetentionBasis`, `RetentionAction`, `RetentionScheduleVersion`, `RetentionScheduleStatus`, `RetentionScheduleDraft`). Code has **zero** `RetentionSchedule*` hits in `src/` — aggregate class, commands, handlers, value-objects, snapshot, repository all absent.

Missing domain events (10):

| event | emitting command | integration event (MM-140) |
|---|---|---|
| `RetentionScheduleCreated` | `CreateRetentionScheduleCommand` | — |
| `RetentionScheduleRenamed` | `RenameRetentionScheduleCommand` (via PATCH) | — |
| `RetentionScheduleDraftCreated` | `CreateRetentionScheduleDraftCommand` | — |
| `RetentionScheduleDraftUpdated` | `UpdateRetentionScheduleDraftCommand` | — |
| `RetentionScheduleDraftDiscarded` | `DiscardRetentionScheduleDraftCommand` | — |
| `RetentionSchedulePublished` | `PublishRetentionScheduleCommand` | `media.retentionschedule.published` |
| `RetentionScheduleDeprecated` | `DeprecateRetentionScheduleCommand` | `media.retentionschedule.deprecated` |
| `RetentionScheduleVersionDeprecated` | `DeprecateRetentionScheduleVersionCommand` | `media.retentionschedule.version-deprecated` |
| `RetentionScheduleSupersessionRecorded` | `RecordRetentionScheduleSupersessionCommand` | `media.retentionschedule.supersession-recorded` |
| `RetentionScheduleAbandoned` | `AbandonRetentionScheduleCommand` | — |

Missing commands (10) — one per domain event above.

Missing supporting types:

| type | role |
|---|---|
| `RetentionSchedule` aggregate | `EventSourced<RetentionSchedule, RetentionScheduleId>`, `ITenantScoped`, `[AggregateType("media.retentionschedule")]` |
| `RetentionScheduleId` | strong id, UUID v7 |
| `RetentionScheduleName` | ≤128 chars, non-blank |
| `RetentionScheduleVersion` | monotonic int |
| `RetentionScheduleStatus` | `Draft=1`, `Published=2`, `Deprecated=3`, `Abandoned=4` — explicit ordinals |
| `RetentionScheduleDraft` | pending-version state carrier |
| `RetentionDefinition` | `Period` + `Basis` + `Action` + optional `YearEnd` + `Reason` |
| `RetentionPeriod` | ISO 8601 YMD duration with positive component |
| `RetentionBasis` | enum (`AfterLastAction`, `AfterClosure`, `AfterCreation`, `AfterYearEnd`, …) |
| `RetentionAction` | enum (`Destroy`, `TransferToArchives`, `RetainPermanently`, `ReviewAgain`) |
| `SupersededBy` | state slot (nullable `RetentionScheduleId`) |
| `RetentionScheduleRepository` | DynamoDB event-store repository |
| `RetentionScheduleSnapshot` | `[Snapshot(Revision = 1)]` carrying `Status`, `CurrentVersion`, `PublishedVersions[]`, `Draft?`, `SupersededBy?` |
| `RetentionScheduleDomainEventMapper` | 4 overloads → MM-140 integration events |

## What the spec requires

- `CreateRetentionScheduleCommand(TenantId, RetentionScheduleId, Name, Definition)` — caller-supplied id (UUID v7 idempotency token).
- `RetentionSchedule.Create(id, name, definition, actor)` factory emits `RetentionScheduleCreated` + initial `RetentionScheduleDraftCreated`.
- `RetentionSchedule.UpdateDraft(definition)` — refuses `409 RetentionScheduleNoActiveDraft` (MM-139).
- `RetentionSchedule.DiscardDraft()` — refuses `422 CannotDiscardInitialRetentionScheduleDraft` when only version is the initial draft (use `Abandon` instead).
- `RetentionSchedule.Publish()` — advances `CurrentVersion`, clears `Draft`, emits `RetentionSchedulePublished { TenantId, RetentionScheduleId, Name, Version, Definition, PublishedAt, PublishedBy }`.
- `RetentionSchedule.Rename(newName)` — reserves + releases name via `INameReservationService` under `media-retention-schedule` scope.
- `RetentionSchedule.Abandon()` — refuses `422 RetentionScheduleAlreadyPublished` (abandon only pre-publish; post-publish uses `Deprecate`).
- `RetentionSchedule.Deprecate(reason?)` — refuses `422 RetentionScheduleAlreadyDeprecated`, `422 RetentionScheduleNotPublished`.
- `RetentionSchedule.DeprecateVersion(version, reason?)` — refuses `422 RetentionScheduleVersionAlreadyDeprecated`, `422 CannotDeprecateLastRetentionScheduleVersion`.
- `RetentionSchedule.RecordSupersession(supersededBy)` — refuses `422 RetentionScheduleNotDeprecated`, `422 RetentionScheduleSupersessionAlreadyRecorded`, `422 InvalidSupersededByRetentionSchedule` when target is unknown / deprecated.
- Name-reservation: `media-retention-schedule` scope; `CatalogReservationProbe`-style owner probe for recovery.
- `RetentionDefinition` validation: `InvalidRetentionDefinition 400`, `InvalidRetentionPeriod 400`, `RetentionPeriodMismatch 422` (period/action mismatch), `PeriodBasisMismatch 422` (basis/yearEnd/period mismatch).

## Wire-visibility

- Internal — SNS wire captured by MM-140; HTTP wire by MM-141.

## Scope boundary

- Aggregate + commands + handlers + domain events + value-objects + repository + snapshot + mapper.
- Error codes → MM-139.
- Integration events → MM-140.
- HTTP endpoints → MM-141.
- Read-model → MM-142.
- No MediaItem retention-pin consumer wiring — that's MM-122 scope.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-103 (plan MM-143). MM-139 + WS-57 must be reachable. Largest unbuilt-aggregate plan — RetentionSchedule has zero files in `src/`. Siblings MM-140/141/142 land after this write-model core (they consume its domain events + commands).

## Phase 0 — Scope confirmation

- [ ] MM-139 constants reachable
- [ ] WS-57 snapshot revision mechanism available

## Phase 1 — Value objects

- [ ] `RetentionScheduleId`, `RetentionScheduleName`, `RetentionScheduleVersion`, `RetentionScheduleStatus` (ordinals pinned)
- [ ] `RetentionDefinition`, `RetentionPeriod`, `RetentionBasis` enum, `RetentionAction` enum
- [ ] `RetentionScheduleDraft`

## Phase 2 — Domain events

- [ ] 10 event records under `Metadata.Domain/Aggregates/Events/` with `[DomainEvent]` ordinals

## Phase 3 — Aggregate + repository

- [ ] `RetentionSchedule` aggregate with factory + 9 lifecycle methods
- [ ] `RetentionScheduleRepository`
- [ ] `RetentionScheduleSnapshot` with `[Snapshot(Revision = 1)]`

## Phase 4 — Commands + handlers (10)

- [ ] `CreateRetentionScheduleCommand` + handler
- [ ] `RenameRetentionScheduleCommand` + handler
- [ ] `CreateRetentionScheduleDraftCommand` + handler
- [ ] `UpdateRetentionScheduleDraftCommand` + handler
- [ ] `DiscardRetentionScheduleDraftCommand` + handler
- [ ] `PublishRetentionScheduleCommand` + handler
- [ ] `DeprecateRetentionScheduleCommand` + handler
- [ ] `DeprecateRetentionScheduleVersionCommand` + handler
- [ ] `RecordRetentionScheduleSupersessionCommand` + handler
- [ ] `AbandonRetentionScheduleCommand` + handler (releases name reservation after save)

## Phase 5 — Name reservation

- [ ] `media-retention-schedule` scope registered
- [ ] `RetentionScheduleReservationProbe` implementing `IReservationOwnerProbe`

## Phase 6 — Integration event mapper

- [ ] `RetentionScheduleDomainEventMapper` with 4 overloads wired to publishing

## Phase 7 — Tests

- [ ] Unit: each aggregate method — happy path + guard precedence
- [ ] Unit: `Deprecate` refuses non-published (`RetentionScheduleNotPublished`)
- [ ] Unit: `DeprecateVersion` refuses last live version (`CannotDeprecateLastRetentionScheduleVersion`)
- [ ] Unit: `Supersession` refuses non-deprecated (`RetentionScheduleNotDeprecated`)
- [ ] Unit: `RetentionDefinition` validation (`InvalidRetentionPeriod`, `RetentionPeriodMismatch`, `PeriodBasisMismatch`)
- [ ] Integration: command → event-store → projector (MM-142) + SNS (MM-140)

## Phase 8 — Communicate change

- [ ] No `breaking-changes.md` entry — wire visibility captured by MM-140 + MM-141

## Phase 9 — Ship

- [ ] PR to `develop`

## Phase 10 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-143 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-103 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RetentionSchedule × write-model; largest unbuilt-aggregate plan — zero `RetentionSchedule*` files in `src/`)
