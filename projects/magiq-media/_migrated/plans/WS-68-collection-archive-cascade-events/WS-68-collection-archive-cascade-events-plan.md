---
id: MM-108
type: plan
project: magiq-media
workstream: WS-68-collection-archive-cascade-events
repo: magiq-media
tags: [magiq-media, catalog, collection, integration-events, saga, step-functions, archive-cascade]
consumes: []
blocked-by-external: [MM-031]
status: new
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

`docs/spec/shared/event-store-and-messaging.md § Integration Events` names 10 Collection integration types. Code publishes 5 of 10 via `CollectionDomainEventMapper`:

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
| `media.collection.unarchive-completed` | **missing** — surfaced in Arnica review re-diff |

Underlying domain events absent in code for all five missing types: `CollectionArchiveStarted`, `CollectionUnarchiveStarted`, `CollectionArchiveIncomplete`, `CollectionUnarchived`, `CollectionUnarchiveCompleted`.

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
- `CollectionUnarchiveCompleted` domain event, `[DomainEvent]`-registered — emitted by the unarchive cascade terminator; consumed by Catalog to close `media-catalog-archive-cascades` SUMMARY row.
- 5 matching `*IntegrationEvent` records in `Catalog.Contracts/Events/Collections/`.
- `CollectionDomainEventMapper` adds 5 `Map(…)` overloads.
- `ArchiveCollectionHandler` emits `CollectionArchiveStarted` (not `CollectionArchived`) + dispatches state-machine execution.
- `CollectionArchived` is emitted by the cascade terminator, not inline.
- Cascade terminator emits `CollectionArchiveIncomplete` on partial failure path per `collection-archive-cascade` saga file.
- Unarchive cascade terminator emits `CollectionUnarchiveCompleted` on completion (closes `media-catalog-archive-cascades` SUMMARY row that `GET /unarchive-status` reads).
- Each new integration-event `type` string matches the spec row exactly (`FilterPolicyScope: MessageBody` on `type` — CDK filter policies on `cdk-magiq-media` subscribers add rows for the four new types in the same release).

## Wire-visibility (process wire — breaking)

- `media.collection.archived` moves from immediate-after-command publication to cascade-completion publication. Any consumer measuring archive latency changes meaning. Billing + Notifications currently acting on the immediate event now act on the cascade-end event — correct per spec; divergence vs today's observed timing.
- 5 new types enter the topic. Consumers must declare filter-policy rows if they want them; defaults filter them out. See `docs/breaking-changes.md § Cross-cutting ordering constraint — SNS filter-policy scope` — spec publishes body-only, so every existing attribute-scoped subscription on `media-integration-events` must be migrated to `FilterPolicyScope: MessageBody` before any new publication fires.

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
- [ ] `CollectionUnarchiveCompleted` — emitted by unarchive cascade terminator; carries `CollectionId`, `CompletedAt`, cascade run identifier
- [ ] Each `[DomainEvent(…)]`-registered + payload members per spec

## Phase 2 — Integration events + mapper

- [ ] `CollectionArchiveStartedIntegrationEvent`, `CollectionUnarchiveStartedIntegrationEvent`, `CollectionArchiveIncompleteIntegrationEvent`, `CollectionUnarchivedIntegrationEvent`, `CollectionUnarchiveCompletedIntegrationEvent` records under `Catalog.Contracts/Events/Collections/`
- [ ] Each with `[MessageType("media.collection.<kebab>")]` matching spec row exactly
- [ ] `CollectionDomainEventMapper` adds `Map(…)` overloads for each (5 new overloads total)

## Phase 3 — Publication-timing refactor

- [ ] `ArchiveCollectionHandler` emits `CollectionArchiveStarted` + dispatches `magiq-media-collection-archive-cascade` execution (via `IStepFunctionsTaskClient` — WS-05 shipped)
- [ ] Archive cascade terminator emits `CollectionArchived` or `CollectionArchiveIncomplete`
- [ ] Unarchive cascade terminator emits `CollectionUnarchiveCompleted` (closes `media-catalog-archive-cascades` SUMMARY row — reader is MM-109 `GET /unarchive-status` endpoint)
- [ ] Remove inline `Collection.Archive` call site that currently fires `CollectionArchived` immediately

## Phase 4 — CDK coordination

- [ ] **Precondition:** every existing subscription on `media-integration-events` migrated to `FilterPolicyScope: MessageBody` (per `docs/breaking-changes.md § Cross-cutting ordering constraint`). This is a cross-cutting prerequisite, not plan-specific; deploy must land + propagate before any body-only publication fires
- [ ] cdk-magiq-media filter-policy edits for the 5 new types — Billing on `.unarchived`, Notifications on `.archive-incomplete` + `.unarchived`, Catalog on `.unarchive-completed` (closes archive-cascade SUMMARY row). Nothing subscribes to `.archive-started` / `.unarchive-started` by default — cascade starts via EventBridge rule shipped under MM-031
- [ ] Confirm EventBridge rules on `media-saga-collection-archive-start` match `media.collection.archive-started` (not `media.collection.archived`)

## Phase 5 — Tests

- [ ] Unit: `ArchiveCollectionHandler` emits `CollectionArchiveStarted`, dispatches execution, does NOT emit `CollectionArchived` inline
- [ ] Integration: cascade success path → `CollectionArchived` on `media-integration-events` with payload per spec
- [ ] Integration: cascade partial-failure path → `CollectionArchiveIncomplete`
- [ ] Integration: unarchive success → `CollectionUnarchived` + `CollectionUnarchiveCompleted` (cascade terminator fires both; unarchived is the user-visible completion, unarchive-completed is the cascade-run closure for `GET /unarchive-status`)
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
- 2026-10-18: re-diffed under Arnica review fixes. Added `media.collection.unarchive-completed` (5th missing type; surfaced by catalog-integration-events.md Phase 1 regression recorded as finding #8). Scope: 4 → 5 new domain events + 4 → 5 new integration events + 4 → 5 mapper overloads. CDK Phase 4 gains the SNS filter-policy ordering precondition (body-only publication prerequisite). Status unchanged (`active`); dependency metadata (MM-100) added by the P2 batch frontmatter patch.
