---
id: MM-111
type: plan
project: magiq-media
workstream: WS-71-collection-write-model-additions
repo: magiq-media
tags: [magiq-media, catalog, collection, write-model, commands, domain-events, aggregate, tags, unarchive, cascade-terminator]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
depends-on: MM-108
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell Collection × write-model
---

# WS-71 — Collection write-model: 4 new commands + 6 new domain events

**Target repo:** `magiq-media`
**Depends on:** MM-108 (owns the 4 shared archive/unarchive domain events: `CollectionArchiveStarted`, `CollectionUnarchiveStarted`, `CollectionArchiveIncomplete`, `CollectionUnarchived`)

## Problem

Catalog slice from `catalog-write-model-events.md` names **17** Collection domain events; code implements **7**. Of the 10 missing:

- **4 covered by MM-108** (plan drafted): `CollectionArchiveStarted`, `CollectionArchiveIncomplete`, `CollectionUnarchiveStarted`, `CollectionUnarchived`.
- **6 not in any plan** (this plan): `CollectionDefaultProfileCleared`, `CollectionTagsAdded`, `CollectionTagsRemoved`, `CollectionArchiveCompleted`, `CollectionUnarchiveCompleted`, `CollectionUnarchiveIncomplete`.

Backing those 6 events: **4 new commands + aggregate methods** are also missing from code:

| Command | Aggregate method | Primary event(s) |
|---|---|---|
| `UnarchiveCollectionCommand` | `Collection.Unarchive(…)` | emits `CollectionUnarchiveStarted` (MM-108); cascade terminator emits `CollectionUnarchived` (MM-108) or `CollectionUnarchiveIncomplete` (this plan); on success a final `CollectionUnarchiveCompleted` (this plan) |
| `ClearDefaultMediaProfileCommand` | `Collection.ClearDefaultMediaProfile(…)` | `CollectionDefaultProfileCleared` |
| `AddCollectionTagsCommand` | `Collection.AddTags(IReadOnlyList<Tag>, …)` | `CollectionTagsAdded` |
| `RemoveCollectionTagsCommand` | `Collection.RemoveTags(IReadOnlyList<Tag>, …)` | `CollectionTagsRemoved` |

Cascade-terminator events (`CollectionArchiveCompleted`, `CollectionUnarchiveCompleted`, `CollectionUnarchiveIncomplete`) are emitted by handler-dispatched commands from cascade state-machine step Lambdas (MM-031 era); the aggregate exposes methods they call.

`CollectionCreated (v2)` noted in catalog carries [DomainEvent(Version=2, Aliases=…)] once WS-28 upcaster framework lands (platform-wide concern, not this plan).

**`CollectionTagged` disposition.** Code emits `CollectionTagged` from `Collection.ApplyTags` whole-replace. Spec retains `CollectionTagged` in the event list (row 9) for stream readability but new writes go through `CollectionTagsAdded`/`CollectionTagsRemoved` under MM-109's two additive routes. `PUT /tags` deprecates under MM-109 — once sunset, `CollectionTagged` emits only on the deprecated route until it is removed. Streams continue to carry historical `CollectionTagged` events; both apply.

## Scope boundary

This plan is **commands + aggregate methods + domain events only**. It does not:

- Add integration-event mapper handlers for the new domain events → `CollectionDomainEventMapper` additions are in **MM-108** (archive/unarchive family) + per-event mapper additions in this plan's PR (the `TagsAdded`/`TagsRemoved` both map to the existing `media.collection.tagged` integration type; `DefaultProfileCleared` has no integration event per catalog; cascade `Completed`/`UnarchiveIncomplete` are internal — not published).
- Build cascade-state-machine step Lambdas → belongs to the cascade orchestrator (future plan under the saga-orchestration theme).
- Wire the HTTP routes that dispatch these commands → **MM-109**.
- Wire error codes (`CollectionCascadeInProgress`, `CascadeRunNotCurrent`, `CollectionNotArchived`, `UnarchiveNameConflict`) to the new handlers → **MM-107 constants + wiring**.
- Build `media-catalog-archive-cascades` table → **MM-110**.

## Classification — why internal

API-wire-visible surface (new routes, new 4xx behaviour) is already captured in MM-109's breaking-changes entry. The write-model additions here are the backing commands/events those routes dispatch; nothing new surfaces at the wire that MM-109 did not already name. No breaking-changes.md entry.

## What the spec requires

- 6 new `[DomainEvent]`-registered records under `Catalog.Domain/Aggregates/Collections/Events/`
- 4 new command records + handlers under `Catalog.WriteModel/Commands/Collections/`
- 4 new aggregate methods on `Collection` + `When<>` subscriptions + `Apply` method bodies
- `CollectionSnapshot` gains any new state (e.g. `UnarchiveStartedAt`, `ArchivalRunId`) needed to express cascade state across restarts; bump revision per WS-57 (`[Snapshot(Revision = 2)]` once SDK slot ships)
- Tag-split: `AddTags(IReadOnlyList<Tag>, DateTimeOffset)` + `RemoveTags(IReadOnlyList<Tag>, DateTimeOffset)` compute delta vs current `Tags`, emit only when delta is non-empty, update `Tags` under their respective `Apply`s. Idempotent on empty delta (no event, success)

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-71 (plan MM-111). MM-108 ships 4 archive/unarchive domain events. Add 6 more + 4 new commands + 4 aggregate methods on `Collection`. Internal — route layer MM-109 covers wire; this plan is the backing write model.

## Phase 0 — Scope confirmation

- [ ] MM-108 shipped (archive/unarchive domain events present in `Catalog.Domain/Aggregates/Collections/Events/`)
- [ ] Code audit: 7 of 17 events present (sanity)
- [ ] Confirm `MM-107` constants reachable (handler refusals compile)

## Phase 1 — Domain events

- [ ] `CollectionDefaultProfileCleared` — payload `{ TenantId, CollectionId, PreviousMediaProfileId, ClearedAt }`
- [ ] `CollectionTagsAdded` — `{ TenantId, CollectionId, AddedTags: IReadOnlyList<string>, AddedAt }`
- [ ] `CollectionTagsRemoved` — `{ TenantId, CollectionId, RemovedTags: IReadOnlyList<string>, RemovedAt }`
- [ ] `CollectionArchiveCompleted` — `{ TenantId, CollectionId, CascadeRunId, CompletedAt }` (success terminal)
- [ ] `CollectionUnarchiveCompleted` — `{ TenantId, CollectionId, CascadeRunId, CompletedAt }`
- [ ] `CollectionUnarchiveIncomplete` — `{ TenantId, CollectionId, CascadeRunId, FailedNodes: IReadOnlyList<CascadeFailure>, OccurredAt }`
- [ ] Each `[DomainEvent]`-registered

## Phase 2 — Aggregate methods

- [ ] `Collection.Unarchive(CascadeRunId, DateTimeOffset)` — refuses with `CollectionNotArchived` (MM-107) if not archived; refuses with `CollectionCascadeInProgress` if cascade in flight; refuses with `UnarchiveNameConflict` if reservation re-apply fails; emits `CollectionUnarchiveStarted` (MM-108)
- [ ] `Collection.ClearDefaultMediaProfile(DateTimeOffset)` — no-op if null; emits `CollectionDefaultProfileCleared`
- [ ] `Collection.AddTags(IReadOnlyList<Tag>, DateTimeOffset)` — delta vs current; emits `CollectionTagsAdded` on non-empty
- [ ] `Collection.RemoveTags(IReadOnlyList<Tag>, DateTimeOffset)` — delta vs current; emits `CollectionTagsRemoved` on non-empty
- [ ] `Collection.CompleteArchive(CascadeRunId, DateTimeOffset)` — called by cascade terminator; refuses `CascadeRunNotCurrent` on stale run; emits `CollectionArchiveCompleted`
- [ ] `Collection.CompleteUnarchive(CascadeRunId, DateTimeOffset)` — emits `CollectionUnarchiveCompleted`
- [ ] `Collection.MarkUnarchiveIncomplete(CascadeRunId, FailedNodes, DateTimeOffset)` — emits `CollectionUnarchiveIncomplete`
- [ ] `When<>` + `Apply` for each new event
- [ ] `CollectionSnapshot` carries `UnarchiveStartedAt?`, `ArchivalRunId?`

## Phase 3 — Commands + handlers

- [ ] `UnarchiveCollectionCommand` + `UnarchiveCollectionHandler` — guard precedence per `api-conventions.md § Refusal precedence`; dispatch state-machine execution via `IStepFunctionsTaskClient` (WS-05)
- [ ] `ClearDefaultMediaProfileCommand` + `ClearDefaultMediaProfileHandler`
- [ ] `AddCollectionTagsCommand` + `AddCollectionTagsHandler`
- [ ] `RemoveCollectionTagsCommand` + `RemoveCollectionTagsHandler`

## Phase 4 — Mapper handlers

- [ ] `CollectionDomainEventMapper.Map(CollectionTagsAdded)` → `media.collection.tagged` integration event (reuse existing type)
- [ ] `CollectionDomainEventMapper.Map(CollectionTagsRemoved)` → `media.collection.tagged` integration event
- [ ] `CollectionDefaultProfileCleared` — no integration event (not in catalog)
- [ ] `CollectionArchiveCompleted` / `CollectionUnarchiveCompleted` / `CollectionUnarchiveIncomplete` — no integration event (not in catalog); internal cascade state only

## Phase 5 — Tests

- [ ] Unit per aggregate method: pre-state + command → expected event(s)
- [ ] Unit per handler: refuses per guard precedence
- [ ] Unit per idempotent command: empty-delta tags → no event
- [ ] Integration: cascade terminator step dispatches `CompleteArchive` / `CompleteUnarchive` → event appears in stream

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-111 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-71 close row

## Session log

- 2026-10-15: plan drafted (alignment-sweep-2026-10-15 cell Collection × write-model; status candidate; depends on MM-108)
