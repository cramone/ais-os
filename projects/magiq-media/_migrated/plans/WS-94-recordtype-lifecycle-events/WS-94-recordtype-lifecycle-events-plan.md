---
id: MM-134
type: plan
project: magiq-media
workstream: WS-94-recordtype-lifecycle-events
repo: magiq-media
tags: [magiq-media, metadata, recordtype, integration-events, version-deprecated, reinstated, supersession]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'RecordType × write-model plan'
breaking-change: Process wire
source: alignment-sweep-2026-10-15 cell RecordType × integration-events
---

# WS-94 — RecordType missing integration events (3)

**Target repo:** `magiq-media`
**Depends on:** RecordType × write-model cell plan (adds `RecordTypeVersionDeprecated`, `RecordTypeReinstated`, `RecordTypeSupersessionRecorded` domain events + backing commands)

## Problem

Spec names 5 RecordType integration types. Code publishes 2. Missing 3:

| spec type | source domain event | status |
|---|---|---|
| `media.recordtype.published` | `RecordTypePublished` | published |
| `media.recordtype.deprecated` | `RecordTypeDeprecated` | published |
| `media.recordtype.version-deprecated` | `RecordTypeVersionDeprecated` | **missing** |
| `media.recordtype.reinstated` | `RecordTypeReinstated` | **missing** |
| `media.recordtype.supersession-recorded` | `RecordTypeSupersessionRecorded` | **missing** |

Underlying domain events absent for all three.

## Consumer impact

Per catalog:
- `media.recordtype.version-deprecated` → Catalog marks one version
- `media.recordtype.reinstated` → Notifications + Catalog clears type marker
- `media.recordtype.supersession-recorded` → Catalog fills superseding pointer

Without these events: Catalog's `media-catalog-record-type-index` cannot reflect version-level deprecation, reinstatement, or supersession.

## Scope boundary

- **Integration-event layer only.** Domain events + backing commands = RecordType × write-model cell plan.

## What the spec requires

- `RecordTypeVersionDeprecatedIntegrationEvent` with `[MessageType("media.recordtype.version-deprecated")]`
- `RecordTypeReinstatedIntegrationEvent` with `[MessageType("media.recordtype.reinstated")]`
- `RecordTypeSupersessionRecordedIntegrationEvent` with `[MessageType("media.recordtype.supersession-recorded")]`
- `RecordTypeDomainEventMapper` adds `IDomainEventMapper<T>` + mapper for each

## Wire-visibility

Process wire — additive.

## Session invocation

> Picking up WS-94 (plan MM-134). RecordType × write-model cell plan must ship first. Add 3 integration events + 3 mapper overloads.

## Phase 0 — Scope confirmation

- [ ] RecordType × write-model plan shipped (3 domain events + commands)
- [ ] Confirm `RecordTypeDomainEventMapper` has 2 overloads today

## Phase 1 — Integration event records

- [ ] `RecordTypeVersionDeprecatedIntegrationEvent`
- [ ] `RecordTypeReinstatedIntegrationEvent`
- [ ] `RecordTypeSupersessionRecordedIntegrationEvent`

## Phase 2 — Mapper overloads

- [ ] `RecordTypeDomainEventMapper` adds `IDomainEventMapper<RecordTypeVersionDeprecated>`, `<RecordTypeReinstated>`, `<RecordTypeSupersessionRecorded>` + mappers

## Phase 3 — CDK coordination

- [ ] cdk-magiq-media subscriber filter policies include 3 new types for Catalog consumers (`media-catalog-record-type-index` projector)

## Phase 4 — Tests

- [ ] Unit per mapper: `[MessageType]` + payload per spec
- [ ] Integration: deprecate version → `media.recordtype.version-deprecated`
- [ ] Integration: reinstate → `media.recordtype.reinstated`
- [ ] Integration: record supersession → `media.recordtype.supersession-recorded`

## Phase 5 — Communicate change

- [ ] Breaking-changes.md entry — process wire additive

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-134 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-94 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RecordType × integration-events; status candidate; publication half of lifecycle whose write-model builds under next cell)
