---
id: MM-136
type: plan
project: magiq-media
workstream: WS-96-recordtype-readmodel-history-and-list-index
repo: magiq-media
tags: [magiq-media, metadata, recordtype, read-model, history, list-index, gsi, projector]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'RecordType × write-model plan (MM-137 history-entry events), MM-135 (GET /history consumer)'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell RecordType × read-model
---

# WS-96 — RecordType read-model: `media-record-type-history` + `RecordTypeListIndex` GSI

**Target repo:** `magiq-media`
**Depends on:** RecordType × write-model plan (history-entry domain events); MM-135 (`GET /history` endpoint consumer)

## Problem

Spec names 6 RecordType read-model tables + 3 GSIs. Code has 5 tables + 2 GSIs.

Missing (2):

| spec row | status |
|---|---|
| `media-record-type-history` detail table | no `RecordTypeHistoryReadModel` file; no schema registration; no projector |
| `RecordTypeListIndex` GSI on `media-record-types` | id-ordered index per spec; code to register (CLAUDE.md KDPW) |

Covered (5 tables + 2 GSIs):

| row | code |
|---|---|
| `media-record-type` detail | `RecordTypeDetailReadModel` + schema |
| `media-record-type-version` detail | `RecordTypeVersionDetailReadModel` + schema |
| `media-record-type-versions` summary | `RecordTypeVersionSummaryReadModel` + schema |
| `media-record-types` summary | `RecordTypeSummaryReadModel` + schema |
| `media-catalog-record-type-index` (Catalog side) | `RecordTypeVersionReference` + projectors + handlers (7 files) |
| `RecordTypeByNameIndex` GSI | registered on `media-record-types` |
| `RecordTypeVersionByVersionIndex` GSI | registered on `media-record-type-versions` |

## What the spec requires

- `media-record-type-history` detail table — one row per lifecycle event per `RecordTypeId`. Keyed `TENANT#{TenantId}#RECORD_TYPE_HISTORY#{RecordTypeId}` / `EVENT#{EventTimestamp}#{EventType}`. Row members: `RecordTypeId`, `EventType`, `EventTimestamp`, `ActorId`, `ActorName`, `Payload` (polymorphic per lifecycle verb), `ProjectedVersion`.
- `RecordTypeListIndex` GSI on `media-record-types` — id-ordered for cross-tenant list enumeration under maintenance passes. Partition `TENANT#{TenantId}#RECORD_TYPE_LIST`, sort `{RecordTypeId}`. Already named in CLAUDE.md § KDPW ("spec defines an id-ordered index; code to register it on `media-record-types`").

## Scope boundary

- Read-model shape + projector only. Lifecycle domain events (`RecordTypeHistoryEntryRecorded` or per-verb emitters) are a RecordType × write-model concern.
- `GET /history` endpoint is MM-135 (http-routes) — consumer.
- No wire visibility — row shapes only. No `breaking-changes.md` entry.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-96 (plan MM-136). RecordType × write-model plan must ship first (lifecycle event emitters). MM-135 consumes `media-record-type-history`.

## Phase 0 — Scope confirmation

- [ ] RecordType × write-model plan shipped (lifecycle domain events emit history-entry payload or per-verb events)
- [ ] `read-model-metadata` seed infra available (WS-55 shipped)

## Phase 1 — `media-record-type-history` table

- [ ] CDK: add `media-record-type-history` to `cdk-magiq-media` manifest with `read-model-metadata` seed row
- [ ] `RecordTypeHistoryReadModel` record + `IReadModel` surface
- [ ] `RecordTypeHistoryReadModelSchema` + registration
- [ ] `RecordTypeHistoryProjector` — subscribes to RecordType domain events (create/publish/deprecate/reinstate/supersession/abandon/field-change/etc.); writes one row per event with `ProjectedVersion` guard

## Phase 2 — `RecordTypeListIndex` GSI

- [ ] CDK: add GSI3 to `media-record-types` (partition `TENANT#{TenantId}#RECORD_TYPE_LIST`, sort `{RecordTypeId}`, KEYS_ONLY)
- [ ] `IProjectionIndexSchema<RecordTypeSummaryReadModel>` registration
- [ ] `RecordTypeSummaryProjector` populates GSI3PK/SK on every write

## Phase 3 — Tests

- [ ] Projector: domain event → history row + `ProjectedVersion` monotonic
- [ ] GSI query: cross-tenant list enumeration returns id-ordered results
- [ ] Replay through `projections rebuild asset` (adapted for RecordType) rebuilds both

## Phase 4 — Communicate change

- [ ] CLAUDE.md § KDPW: `RecordTypeListIndex` bullet removed
- [ ] CLAUDE.md § KDPW: new bullet referencing `media-record-type-history` removed

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] INTEGRATION-BACKLOG.md: MM-136 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-96 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RecordType × read-model; status candidate; depends on RecordType × write-model + MM-135)
