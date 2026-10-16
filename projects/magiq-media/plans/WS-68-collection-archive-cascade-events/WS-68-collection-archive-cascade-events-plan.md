---
id: MM-108
type: plan
project: magiq-media
workstream: WS-68-collection-archive-cascade-events
repo: magiq-media
tags: [magiq-media, catalog, collection, integration-events, saga, step-functions, archive-cascade]
consumes: []
blocked-by-external: [MM-031]
status: active
branches: []
created: 2026-10-15
depends-on: MM-031
breaking-change: Process wire
source: alignment-sweep-2026-10-15 cell Collection × integration-events
---

# WS-68 — Collection archive/unarchive cascade integration events (4 missing types + publication-timing refactor)

**Target repo:** `magiq-media`
**Depends on:** MM-031 (WS-04 CDK — `magiq-media-collection-archive-cascade` state machine shipped on `spec/initial-alignment`)

## Problem

`docs/spec/shared/event-store-and-messaging.md § Integration Events` names 9 Collection integration types. Code publishes 5 of 9 via `CollectionDomainEventMapper`:

| spec type | status |
|---|---|
| `media.collection.created` | published |
| `media.collection.renamed` | published |
| `media.collection.tagged` | published |
| `media.collection.visibility-changed` | published |
| `media.collection.archived` | published **but at wrong moment** — see below |
| `media.collection.archive-started` | **missing** |
| `media.collection.unarchive-started` | **missing** |
| `media.collection.archive-incomplete` | **missing** |
| `media.collection.unarchived` | **missing** |

Underlying domain events absent in code for all four missing types: `CollectionArchiveStarted`, `CollectionUnarchiveStarted`, `CollectionArchiveIncomplete`, `CollectionUnarchived`.

**Publication-timing divergence on `media.collection.archived`.** Spec: archive is long-running — the command publishes `CollectionArchiveStarted` + starts the `magiq-media-collection-archive-cascade` state machine; cascade terminator emits `CollectionArchived` (success) or `CollectionArchiveIncomplete` (partial failure). Code: `ArchiveCollectionHandler` dispatches `Collection.Archive(occurredAt)` inline → `CollectionArchived` emitted immediately → `media.collection.archived` published before any cascade runs.

Any subscriber branching on `media.collection.archived` sees the inline publication today; under spec it fires only on cascade success. Subscribers that assume "archived means descendants' isAccessible is false" are correct per spec, not per code — the code's early emission precedes cascade completion.

## Scope boundary

This plan is the **integration-events layer** of the Collection archive/unarchive long-running cascade. Three adjacent concerns are not in scope:

- **HTTP route change to `202 Accepted` + status endpoint.** Lands under the http-routes cell (future Collection × http-routes diff).
- **`UnarchiveCollection` command + handler + aggregate method.** Lands under write-model (future Collection × write-model).
- **Error codes (`CollectionCascadeInProgress`, `CascadeRunNotCurrent`, `CascadeReportNotFound`, `CollectionNotArchived`, `UnarchiveNameConflict`).** Carried as constants under MM-107 / WS-67, wired to call sites when owning commands land.

This plan is the integration-event-type additions + `[DomainEvent]` registrations + mapper handlers + publication-timing refactor on `CollectionArchived`.

## What the spec requires

- `CollectionArchiveStarted` domain event, `[DomainEvent]`-registered.
- `CollectionUnarchiveStarted` domain event, `[DomainEvent]`-registered.
- `CollectionArchiveIncomplete` domain event, `[DomainEvent]`-registered.
- `CollectionUnarchived` domain event, `[DomainEvent]`-registered.
- 4 matching `*IntegrationEvent` records in `Catalog.Contracts/Events/Collections/`.
- `CollectionDomainEventMapper` adds 4 `Map(…)` overloads.
- `ArchiveCollectionHandler` emits `CollectionArchiveStarted` (not `CollectionArchived`) + dispatches state-machine execution.
- `CollectionArchived` is emitted by the cascade terminator, not inline.
- Cascade terminator emits `CollectionArchiveIncomplete` on partial failure path per `collection-archive-cascade` saga file.
- Each new integration-event `type` string matches the spec row exactly (`FilterPolicyScope: MessageBody` on `type` — CDK filter policies on `cdk-magiq-media` subscribers add rows for the four new types in the same release).

## Wire-visibility (process wire — breaking)

- `media.collection.archived` moves from immediate-after-command publication to cascade-completion publication. Any consumer measuring archive latency changes meaning. Billing + Notifications currently acting on the immediate event now act on the cascade-end event — correct per spec; divergence vs today's observed timing.
- 4 new types enter the topic. Consumers must declare filter-policy rows if they want them; defaults filter them out.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-68 (plan MM-108). MM-031 shipped (`collection-archive-cascade` state machine). Add 4 Collection domain events + integration events + mapper handlers; move `CollectionArchived` emission from inline to cascade terminator. Coordinate with cdk-magiq-media for consumer filter-policy additions.

## Phase 0 — Scope confirmation

- [ ] MM-031 shipped (`magiq-media-collection-archive-cascade` state machine on `spec/initial-alignment`)
- [ ] Confirm no unarchive flow in code (sanity check)
- [ ] Current `CollectionDomainEventMapper` publishes 5 types — confirm

## Phase 1 — Domain events

- [ ] `CollectionArchiveStarted` record under `Catalog.Domain/Aggregates/Collections/Events/`
- [ ] `CollectionUnarchiveStarted`
- [ ] `CollectionArchiveIncomplete`
- [ ] `CollectionUnarchived`
- [ ] Each `[DomainEvent(…)]`-registered + payload members per spec

## Phase 2 — Integration events + mapper

- [ ] `CollectionArchiveStartedIntegrationEvent`, `CollectionUnarchiveStartedIntegrationEvent`, `CollectionArchiveIncompleteIntegrationEvent`, `CollectionUnarchivedIntegrationEvent` records under `Catalog.Contracts/Events/Collections/`
- [ ] Each with `[MessageType("media.collection.<kebab>")]` matching spec row exactly
- [ ] `CollectionDomainEventMapper` adds `Map(…)` overloads for each

## Phase 3 — Publication-timing refactor

- [ ] `ArchiveCollectionHandler` emits `CollectionArchiveStarted` + dispatches `magiq-media-collection-archive-cascade` execution (via `IStepFunctionsTaskClient` — WS-05 shipped)
- [ ] Cascade terminator emits `CollectionArchived` or `CollectionArchiveIncomplete`
- [ ] Remove inline `Collection.Archive` call site that currently fires `CollectionArchived` immediately

## Phase 4 — CDK coordination

- [ ] cdk-magiq-media filter-policy edits — subscribers that want the 4 new types declare rows (Billing on `.unarchived`, Notifications on `.archive-incomplete` + `.unarchived`; nothing subscribes to `.archive-started` / `.unarchive-started` by default — cascade starts via EventBridge rule shipped under MM-031)
- [ ] Confirm EventBridge rules on `media-saga-collection-archive-start` match `media.collection.archive-started` (not `media.collection.archived`)

## Phase 5 — Tests

- [ ] Unit: `ArchiveCollectionHandler` emits `CollectionArchiveStarted`, dispatches execution, does NOT emit `CollectionArchived` inline
- [ ] Integration: cascade success path → `CollectionArchived` on `media-integration-events` with payload per spec
- [ ] Integration: cascade partial-failure path → `CollectionArchiveIncomplete`
- [ ] Integration: unarchive success → `CollectionUnarchived`
- [ ] Unit: each `[MessageType]` matches spec string exactly

## Phase 6 — Communicate change

- [ ] Breaking-changes.md entry — process wire breaking (publication-timing shift on `media.collection.archived`)
- [ ] Breaking-changes.md entry — process wire additive (4 new types)
- [ ] Coordinate with Billing + Notifications owners on timing shift

## Phase 7 — Ship

- [ ] PR to `develop`

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-108 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-68 close row

## Session log

- 2026-10-15: plan drafted (alignment-sweep-2026-10-15 cell Collection × integration-events; status candidate; depends on MM-031 shipped; coordinates with future Collection × http-routes + write-model cell plans)
