---
id: MM-116
type: plan
project: magiq-media
workstream: WS-76-folder-write-model-additions
repo: magiq-media
tags: [magiq-media, catalog, folder, write-model, commands, domain-events, aggregate, originator, reopen, unarchive, retention-fanout]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell Folder × write-model
---

# WS-76 — Folder write-model: 4 new commands + 4 new domain events

**Target repo:** `magiq-media`

## Problem

Catalog slice names **13** Folder domain events; code implements **9**. Missing (4):

| event | needed by |
|---|---|
| `FolderOriginatorSet` | MM-115 (`PUT /folders/{folderId}/originator` route) |
| `FolderUnarchived` | WS-11 (unarchive route) + MM-113 (`FolderNotArchived` / `ArchivedUnderAnotherRoot` codes) |
| `FolderReopened` | MM-115 (`POST /folders/{folderId}/reopen` route) + MM-113 (`FolderNotClosed` code) |
| `FolderRetentionFanoutCompleted` | MM-114 (`FolderClosedRetentionFanOutHandler` emits a completion marker so a retry on duplicate SQS delivery is idempotent) |

Backing commands + aggregate methods missing (4):

| Command | Aggregate method | Primary event |
|---|---|---|
| `SetFolderOriginatorCommand` | `Folder.SetOriginator(OriginatorId, OriginatorName, DateTimeOffset)` | `FolderOriginatorSet` |
| `UnarchiveFolderCommand` | `Folder.Unarchive(CascadeRunId, DateTimeOffset)` | `FolderUnarchived` |
| `ReopenFolderCommand` | `Folder.Reopen(DateTimeOffset)` | `FolderReopened` |
| `MarkFolderRetentionFanoutCompletedCommand` | `Folder.MarkRetentionFanoutCompleted(RetentionRunId, DateTimeOffset)` | `FolderRetentionFanoutCompleted` |

## Classification — why internal

Wire-visible facets already captured by MM-115 (new routes), WS-11 (unarchive 202-async + status endpoint), MM-114 (retention fan-out handler + integration event), MM-113 (error-code wiring). This plan is the write-model backing those routes/consumers dispatch.

## What the spec requires

- 4 new `[DomainEvent]`-registered records under `Catalog.Domain/Aggregates/Folders/Events/`
- 4 new command records + handlers under `Catalog.WriteModel/Commands/Folders/`
- 4 new aggregate methods on `Folder` + `When<>` subscriptions + `Apply` method bodies
- `FolderSnapshot` gains any new state (e.g. `OriginatorId?`, `OriginatorName?`, `UnarchiveRunId?`, `LastRetentionFanoutRunId?`) with revision bump per WS-57
- `Unarchive` refuses `FolderNotArchived 422` (MM-113) if not archived; refuses `ArchivedUnderAnotherRoot 422` if un-archive scope mismatches
- `Reopen` refuses `FolderNotClosed 422` (MM-113) if not closed
- `MarkRetentionFanoutCompleted` idempotent on duplicate RetentionRunId

## Scope boundary

- **Write-model aggregate + commands + events only.**
- HTTP routes = MM-115 (originator + reopen) + WS-11 (unarchive + status). Error codes = MM-113. Fan-out handler = MM-114. Cascade state machine = MM-031.
- Does not add integration-event mapper handlers for the 4 new events — none are specified in `catalog-integration-events.md § Folder` for publication. `FolderClosed` already maps under MM-114; `FolderArchived` already maps; others internal.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-76 (plan MM-116). Add 4 new Folder domain events + 4 new commands + 4 aggregate methods. Internal — route layer MM-115 + WS-11 captures wire; this plan is the backing write model.

## Phase 0 — Scope confirmation

- [ ] Code audit: 9 of 13 events present (sanity)
- [ ] MM-113 shipped (error codes reachable)
- [ ] Confirm no mapper changes required (sanity)

## Phase 1 — Domain events

- [ ] `FolderOriginatorSet` — `{ TenantId, FolderId, PreviousOriginatorId?, OriginatorId, OriginatorName, SetAt }`
- [ ] `FolderUnarchived` — `{ TenantId, FolderId, CollectionId, UnarchiveRunId, UnarchivedAt }`
- [ ] `FolderReopened` — `{ TenantId, FolderId, ReopenedAt }`
- [ ] `FolderRetentionFanoutCompleted` — `{ TenantId, FolderId, RetentionRunId, ItemsPinned, CompletedAt }`
- [ ] Each `[DomainEvent]`-registered

## Phase 2 — Aggregate methods on `Folder`

- [ ] `SetOriginator(OriginatorId, OriginatorName, DateTimeOffset)` — refuses on archived; no-op if unchanged; emits `FolderOriginatorSet`
- [ ] `Unarchive(CascadeRunId, DateTimeOffset)` — refuses `FolderNotArchived` if not archived, `ArchivedUnderAnotherRoot` if root mismatch; emits `FolderUnarchived`
- [ ] `Reopen(DateTimeOffset)` — refuses `FolderNotClosed` if not closed; emits `FolderReopened`
- [ ] `MarkRetentionFanoutCompleted(RetentionRunId, int itemsPinned, DateTimeOffset)` — idempotent on duplicate `RetentionRunId`; emits `FolderRetentionFanoutCompleted`
- [ ] `When<>` + `Apply` for each new event; update `FolderSnapshot` members + revision bump

## Phase 3 — Commands + handlers

- [ ] `SetFolderOriginatorCommand` + `SetFolderOriginatorHandler`
- [ ] `UnarchiveFolderCommand` + `UnarchiveFolderHandler` — guard precedence; dispatches state-machine execution via `IStepFunctionsTaskClient` (WS-05)
- [ ] `ReopenFolderCommand` + `ReopenFolderHandler`
- [ ] `MarkFolderRetentionFanoutCompletedCommand` + handler — called by `FolderClosedRetentionFanOutHandler` after N items pinned

## Phase 4 — Tests

- [ ] Unit per aggregate method: pre-state + command → expected event(s)
- [ ] Unit per handler: guard precedence refuses with correct error code
- [ ] Unit: idempotent `MarkRetentionFanoutCompleted` on duplicate run
- [ ] Integration: full un-archive flow emits `FolderUnarchived` under cascade run id

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-116 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-76 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell Folder × write-model; status candidate; mirrors MM-111 pattern for Collection)
