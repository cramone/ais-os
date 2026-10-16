---
id: MM-119
type: plan
project: magiq-media
workstream: WS-79-mediaitem-missing-integration-events
repo: magiq-media
tags: [magiq-media, catalog, mediaitem, integration-events, withdrawn, unarchived, edit-session]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Process wire
source: alignment-sweep-2026-10-15 cell MediaItem × integration-events
---

# WS-79 — MediaItem missing integration events (3 types) + 1 shape rename

**Target repo:** `magiq-media`

## Problem

Spec names 12 MediaItem integration types; code publishes 9. Missing + divergent:

| spec type | source domain event | code state |
|---|---|---|
| `media.item.created` | `MediaItemCreated` | published |
| `media.item.assigned-to-folder` | `MediaItemAssignedToFolder` | published |
| `media.item.asset-assigned` | `AssetAssignedToRole` | published |
| `media.item.submitted-for-review` | `MediaItemSubmittedForReview` | **source domain event mis-named** — code has `MediaItemPublicationRequested` |
| `media.item.approved` | `MediaItemApproved` | published |
| `media.item.rejected` | `MediaItemRejected` | published |
| `media.item.withdrawn` | `MediaItemWithdrawn` | **missing** |
| `media.item.archived` | `MediaItemArchived` | published |
| `media.item.unarchived` | `MediaItemUnarchived` | **missing** |
| `media.item.edit-session-changed` | `EditSessionOpened` / `EditSessionReopened` / `EditSessionClosed` (3 sources, 1 type) | **missing** |
| `media.item.deleted` | `MediaItemDeleted` | published |
| `media.item.version.purged` | `MediaItemVersionPurged` | published |

Missing integration events have **ripple on consumers**:

- `media.item.withdrawn` — ChangeRequests closes review thread, Registration drops registration, Search/Discovery removes from indexes, Billing stops.
- `media.item.unarchived` — AssetManagement sets `IsArchived=false`, Registration re-activates, Search/Discovery re-indexes, Billing resumes.
- `media.item.edit-session-changed` — AssetManagement edit-session editors for asset-read predicate; applied only on higher `EventVersion` (spec note).

Underlying domain events absent for `MediaItemWithdrawn` and `MediaItemUnarchived`. `EditSessionOpened` / `Reopened` / `Closed` may exist (checkout flow); verify at Phase 0.

## Shape divergence — `MediaItemSubmittedForReview` naming

Code's `MediaItemPublicationRequested` → spec's `MediaItemSubmittedForReview`. Both map to `media.item.submitted-for-review` integration type (same wire). Rename is a write-model concern (Catalog × write-model cell) but the mapper handler site touches this plan — rename coordinated with that cell plan when it ships.

## Scope boundary

- Integration-event layer only: `*IntegrationEvent` contract records + `MediaItemDomainEventMapper` overloads for the 3 missing types.
- `EditSessionOpened` / `Reopened` / `Closed` domain-event audit — if any missing, backfill them under MediaItem × write-model cell plan.
- `MediaItemWithdrawn` + `MediaItemUnarchived` domain events — write-model cell plan builds them + the backing commands (`WithdrawMediaItem`, `UnarchiveMediaItem`).
- `MediaItemSubmittedForReview` rename — write-model cell plan.
- Fan-out consumer handler builds (ChangeRequests, Registration, Search/Discovery, Billing side effects) — each consuming BC's own work; this plan is the **publication** side.

## What the spec requires

- `MediaItemWithdrawnIntegrationEvent` record under `Catalog.Contracts/Events/MediaItems/` with `[MessageType("media.item.withdrawn")]`.
- `MediaItemUnarchivedIntegrationEvent` with `[MessageType("media.item.unarchived")]`.
- `MediaItemEditSessionChangedIntegrationEvent` with `[MessageType("media.item.edit-session-changed")]` carrying `SessionId`, `State` (Opened/Reopened/Closed), `OpenedBy`, `Editors`, `OpenedAt?`, `ClosedAt?`, `EventVersion`.
- `MediaItemDomainEventMapper` adds overloads: `Map(MediaItemWithdrawn)` → withdrawn; `Map(MediaItemUnarchived)` → unarchived; `Map(EditSessionOpened)` + `Map(EditSessionReopened)` + `Map(EditSessionClosed)` → each yields a `MediaItemEditSessionChangedIntegrationEvent`.
- CDK coordination: `cdk-magiq-media` subscriber filter policies include the 3 new types where consumers want them.

## Wire-visibility

Process wire — additive. 3 new types on `media-integration-events`. Existing filter policies ignore unknown types. CDK edits land before magiq-media ships.

(Rename `MediaItemPublicationRequested` → `MediaItemSubmittedForReview` is write-model only — stream reads continue to decode historical events via `[DomainEvent(Aliases = ["mediaitempublicationrequested@1"])]` under WS-28 upcaster framework.)

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-79 (plan MM-119). MediaItem × write-model cell plan must ship first (MediaItemWithdrawn + MediaItemUnarchived domain events + EditSessionOpened/Reopened/Closed audit + MediaItemSubmittedForReview rename). Add 3 missing integration event records + 5 mapper overloads.

## Phase 0 — Scope confirmation

- [ ] Confirm MediaItemWithdrawn + MediaItemUnarchived domain events exist (require MediaItem × write-model cell plan)
- [ ] Audit EditSessionOpened / EditSessionReopened / EditSessionClosed presence
- [ ] Confirm `MediaItemSubmittedForReview` rename shipped (via write-model cell plan)
- [ ] Confirm cdk-magiq-media filter-policy slots available

## Phase 1 — Integration event records

- [ ] `MediaItemWithdrawnIntegrationEvent` under `Catalog.Contracts/Events/MediaItems/`
- [ ] `MediaItemUnarchivedIntegrationEvent`
- [ ] `MediaItemEditSessionChangedIntegrationEvent` carrying session state + editors + event version
- [ ] Each with `[MessageType("media.item.<kebab>")]` matching spec

## Phase 2 — Mapper overloads

- [ ] `MediaItemDomainEventMapper` adds `IDomainEventMapper<MediaItemWithdrawn>` + `Map(…)` → `MediaItemWithdrawnIntegrationEvent`
- [ ] Adds `IDomainEventMapper<MediaItemUnarchived>` + `Map(…)` → `MediaItemUnarchivedIntegrationEvent`
- [ ] Adds `IDomainEventMapper<EditSessionOpened>` / `IDomainEventMapper<EditSessionReopened>` / `IDomainEventMapper<EditSessionClosed>` — each yields `MediaItemEditSessionChangedIntegrationEvent` with correct `State` discriminator
- [ ] Rename mapper call site `MediaItemPublicationRequested` → `MediaItemSubmittedForReview` (coordinate with write-model cell plan)

## Phase 3 — CDK coordination

- [ ] cdk-magiq-media subscriber filter-policy edits for the 3 new types (per consumer section in `event-store-and-messaging.md`)
- [ ] Confirm EventBridge rules + body-scope `type` filters on new types

## Phase 4 — Tests

- [ ] Unit per mapper overload: payload per spec + correct `[MessageType]` string
- [ ] Integration: `WithdrawMediaItem` command → `media.item.withdrawn` on `media-integration-events`
- [ ] Integration: `UnarchiveMediaItem` command → `media.item.unarchived`
- [ ] Integration: edit-session open/reopen/close each produce `media.item.edit-session-changed` with correct `State`

## Phase 5 — Communicate change

- [ ] Breaking-changes.md entry — process wire additive
- [ ] Coordinate with ChangeRequests + Registration + Search/Discovery + Billing + AssetManagement owners (consumer side effects)

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-119 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-79 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaItem × integration-events; status candidate; publication half of a flow whose write-model additions live in the next cell plan)
