---
id: MM-114
type: plan
project: magiq-media
workstream: WS-74-folder-closed-integration-event
repo: magiq-media
tags: [magiq-media, catalog, folder, integration-events, retention, cascade-triggers]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
depends-on: '-'
breaking-change: Process wire
source: alignment-sweep-2026-10-15 cell Folder × integration-events
---

# WS-74 — `media.folder.closed` integration event + retention fan-out handler

**Target repo:** `magiq-media`

## Problem

`docs/spec/shared/event-store-and-messaging.md § Integration Events` names 5 Folder integration types. Code's `FolderDomainEventMapper` publishes 4. Missing: `media.folder.closed`.

| spec type | status |
|---|---|
| `media.folder.created` | published |
| `media.folder.renamed` | published |
| `media.folder.moved` | published |
| `media.folder.archived` | published (publication-timing refactor to cascade terminator covered by WS-11) |
| `media.folder.closed` | **missing** |

Underlying `FolderClosed` **domain event exists** at `Catalog.Domain/Aggregates/Folders/Events/FolderClosed.cs` — only the integration-event mapper + contract record are missing.

**Companion handler also missing.** Spec names `FolderClosedRetentionFanOutHandler` as the intra-BC consumer: closing a folder retention-pins every MediaItem inside it. The handler reaches magiq-media via `media-cascade-triggers` SQS queue (WS-27b wires filter policy + subscription — ready). The handler logic itself is a magiq-media build (not just subscription wiring).

Without the integration event, the entire retention-pin-on-folder-close flow is dark: closing a folder in code today emits a domain event, projects to read models, but no SNS message leaves the module and no retention pin lands on MediaItems inside the folder.

## Scope boundary

This plan covers **both halves** of the gap:

- (A) The publication side — `FolderClosedIntegrationEvent` record + `IDomainEventMapper<FolderClosed>` mapper method.
- (B) The consumption side — `FolderClosedRetentionFanOutHandler` intra-BC worker that reads the SNS event via `media-cascade-triggers` (per WS-27b) and dispatches retention pins to MediaItems in the folder.

(B) is scoped to this plan — not deferred to a write-model cell — because without the handler the integration-event publication is meaningless, and the handler is single-purpose intra-BC fan-out specific to this event type.

## What the spec requires

- `FolderClosedIntegrationEvent` record under `Catalog.Contracts/Events/Folders/` with `[MessageType("media.folder.closed")]` and payload `{ TenantId, FolderId, CollectionId, ClosedAt, ClosedDate, AggregateVersion }`.
- `FolderDomainEventMapper` adds `IDomainEventMapper<FolderClosed>` + `Map(FolderClosed e)` method.
- `FolderClosedRetentionFanOutHandler` subscribes to the event on `media-cascade-triggers` (per WS-27b filter policy on `type == media.folder.closed`), paginates MediaItems in the folder, dispatches retention-pin commands per MediaItem.
- CDK coordination: `media-cascade-triggers` SQS filter policy on `type` includes `media.folder.closed` (per WS-27b scope — ready).

## Wire-visibility

Process wire — additive. New type on `media-integration-events`. Existing subscribers' filter policies ignore it unless they declare the row. CDK edits land before magiq-media ships.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-74 (plan MM-114). FolderClosed domain event exists; add integration event record + mapper method + retention fan-out handler. Coordinate with cdk-magiq-media for cascade-triggers filter policy addition.

## Phase 0 — Scope confirmation

- [ ] `FolderClosed.cs` domain event exists (sanity)
- [ ] `FolderDomainEventMapper` currently has 4 overloads (sanity)
- [ ] `FolderClosedIntegrationEvent` record absent (sanity)
- [ ] `FolderClosedRetentionFanOutHandler` absent (sanity)
- [ ] WS-27b `media-cascade-triggers` wiring state

## Phase 1 — Integration event record

- [ ] `Catalog.Contracts/Events/Folders/FolderClosedIntegrationEvent.cs`
- [ ] `[MessageType("media.folder.closed")]` attribute
- [ ] Payload: `TenantId`, `FolderId`, `CollectionId`, `ClosedAt`, `ClosedDate`, `AggregateVersion`

## Phase 2 — Mapper method

- [ ] `FolderDomainEventMapper` implements `IDomainEventMapper<FolderClosed>`
- [ ] `Map(FolderClosed e)` yields a `FolderClosedIntegrationEvent`

## Phase 3 — Retention fan-out handler

- [ ] `FolderClosedRetentionFanOutHandler` under `Catalog.WriteModel/IntegrationEvents/Consuming/Handlers/`
- [ ] `IIntegrationEventHandler<FolderClosedIntegrationEvent>`
- [ ] Reads tenant from `executionContext.TenantId` (not `e.TenantId`)
- [ ] Paginates `FolderMediaItemsIndex` for the folder
- [ ] Dispatches `PinRetentionCommand` (or equivalent spec-named retention-pin command) per MediaItem
- [ ] Idempotent on duplicate SQS delivery
- [ ] Honours per-tenant fan-out budget (same cascade-triggers budget shared with Collection fan-out)

## Phase 4 — CDK coordination

- [ ] cdk-magiq-media `media-cascade-triggers` SQS filter policy on `type` includes `media.folder.closed` (WS-27b scope — verify not already shipped)

## Phase 5 — Tests

- [ ] Unit: `Map(FolderClosed)` yields correct `[MessageType]` + payload
- [ ] Integration: closing a folder with N MediaItems retention-pins all N
- [ ] Integration: duplicate SQS delivery idempotent

## Phase 6 — Communicate change

- [ ] Breaking-changes.md entry — process wire additive
- [ ] Coordinate with any external subscriber owning `media.folder.closed` filter row

## Phase 7 — Ship

- [ ] PR to `develop`

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-114 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-74 close row

## Session log

- 2026-10-15: plan drafted (alignment-sweep-2026-10-15 cell Folder × integration-events; status candidate; FolderClosed domain event already in code — gap is mapper + contract + fan-out handler)
