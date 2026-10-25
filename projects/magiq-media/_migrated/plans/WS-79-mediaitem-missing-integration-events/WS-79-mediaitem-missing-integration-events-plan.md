---
id: MM-119
type: plan
project: magiq-media
workstream: WS-79-mediaitem-missing-integration-events
repo: magiq-media
tags: [magiq-media, catalog, mediaitem, integration-events, withdrawn, unarchived, edit-session, asset-unassigned, legal-hold, registration-while-archived]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-122 (MediaItem × write-model — provides MediaItemWithdrawn, MediaItemUnarchived, LegalHoldPlaced, LegalHoldLifted, RegistrationRefAddedWhileArchived domain events + MediaItemSubmittedForReview rename)'
breaking-change: Process wire
source: alignment-sweep-2026-10-15 cell MediaItem × integration-events
---

# WS-79 — MediaItem missing integration events (7 types) + 1 shape rename

**Target repo:** `magiq-media`

## Problem

Spec names 13 MediaItem integration types (10 under `media.item.*` + 3 under `media.mediaitem.*`); code publishes 9 via `MediaItemDomainEventMapper`. Missing + divergent:

| spec type | source domain event | code state |
|---|---|---|
| `media.item.created` | `MediaItemCreated` | published |
| `media.item.assigned-to-folder` | `MediaItemAssignedToFolder` | published |
| `media.item.asset-assigned` | `AssetAssignedToRole` | published |
| `media.item.asset-unassigned` | `AssetUnassignedFromRole` | **missing — surfaced in Arnica review re-diff.** Domain event exists; integration event + mapper + Asset consumer missing |
| `media.item.submitted-for-review` | `MediaItemSubmittedForReview` | **source domain event mis-named** — code has `MediaItemPublicationRequested` |
| `media.item.approved` | `MediaItemApproved` | published |
| `media.item.rejected` | `MediaItemRejected` | published |
| `media.item.withdrawn` | `MediaItemWithdrawn` | **missing** |
| `media.item.archived` | `MediaItemArchived` | published |
| `media.item.unarchived` | `MediaItemUnarchived` | **missing** |
| `media.item.edit-session-changed` | `EditSessionOpened` / `EditSessionReopened` / `EditSessionClosed` (3 sources, 1 type) | **missing** |
| `media.item.deleted` | `MediaItemDeleted` | published |
| `media.item.version.purged` | `MediaItemVersionPurged` | published |
| `media.mediaitem.legal-hold-placed` | `LegalHoldPlaced` | **missing — surfaced in Arnica review re-diff.** Domain event absent (MM-122 scope); AssetManagement consumer wires `HoldersUnderHold` via `RecordHolderLegalHoldPlacedCommand` |
| `media.mediaitem.legal-hold-lifted` | `LegalHoldLifted` | **missing — surfaced in Arnica review re-diff.** Domain event absent (MM-122 scope); AssetManagement consumer wires `HoldersUnderHold` via `RecordHolderLegalHoldLiftedCommand` |
| `media.mediaitem.registration-added-while-archived` | `RegistrationRefAddedWhileArchived` | **missing — surfaced in Arnica review re-diff.** Domain event absent (MM-122 scope); operator-alert + Security audit log + `Catalog.ArchivedItemsWithActiveRegistrations` metric |

Missing integration events have **ripple on consumers**:

- `media.item.asset-unassigned` — AssetManagement **sole detach path**. Without it, assets stay attached to MediaItems in the AssetManagement module forever after a Catalog-side unassign. Critical cross-aggregate flow.
- `media.item.withdrawn` — ChangeRequests closes review thread, Registration drops registration, Search/Discovery removes from indexes, Billing stops.
- `media.item.unarchived` — AssetManagement sets `IsArchived=false`, Registration re-activates, Search/Discovery re-indexes, Billing resumes.
- `media.item.edit-session-changed` — AssetManagement edit-session editors for asset-read predicate; applied only on higher `EventVersion` (spec note).
- `media.mediaitem.legal-hold-placed` / `.lifted` — AssetManagement propagates to each `AffectedAssetId`'s `HoldersUnderHold`. Without these events, legal-hold placement never reaches assets (critical compliance flow).
- `media.mediaitem.registration-added-while-archived` — operator-alert channel + Security audit log + `Catalog.ArchivedItemsWithActiveRegistrations` metric. Non-zero metric reading signals a records-recovery call (un-archive the cascade root, or dispose with override authority).

Underlying domain events: `MediaItemWithdrawn`, `MediaItemUnarchived`, `LegalHoldPlaced`, `LegalHoldLifted`, `RegistrationRefAddedWhileArchived` absent (all MM-122 scope). `AssetUnassignedFromRole` **exists** at `Catalog.Domain/Aggregates/MediaItems/Events/AssetUnassignedFromRole.cs` — only the integration-event mapper + contract record are missing. `EditSessionOpened` / `Reopened` / `Closed` may exist (checkout flow); verify at Phase 0.

## Shape divergence — `MediaItemSubmittedForReview` naming

Code's `MediaItemPublicationRequested` → spec's `MediaItemSubmittedForReview`. Both map to `media.item.submitted-for-review` integration type (same wire). Rename is a write-model concern (Catalog × write-model cell) but the mapper handler site touches this plan — rename coordinated with that cell plan when it ships.

## Scope boundary

- Integration-event layer only: `*IntegrationEvent` contract records + `MediaItemDomainEventMapper` overloads for the 7 missing types.
- Domain-event dependencies (all on MM-122 Catalog × write-model): `MediaItemWithdrawn`, `MediaItemUnarchived`, `LegalHoldPlaced`, `LegalHoldLifted`, `RegistrationRefAddedWhileArchived`. `AssetUnassignedFromRole` already exists in code.
- `EditSessionOpened` / `Reopened` / `Closed` domain-event audit — if any missing, backfill them under MM-122.
- `MediaItemSubmittedForReview` rename — MM-122.
- `media.item.asset-unassigned` AssetManagement consumer wiring (sole detach path — `ApplyAssetUnassignmentHandler` → `DetachFromMediaItem`) — this plan builds the handler too, since its publication is dark without a consumer.
- `media.mediaitem.legal-hold-placed` / `.lifted` AssetManagement consumer handlers (`RecordHolderLegalHoldPlacedCommand` / `RecordHolderLegalHoldLiftedCommand` on each `AffectedAssetId`) — this plan builds them for the same reason.
- Fan-out consumer handler builds for the other missing types (ChangeRequests, Registration, Search/Discovery, Billing) — each consuming BC's own work; this plan is the publication side for those.

## What the spec requires

- `MediaItemAssetUnassignedIntegrationEvent` record under `Catalog.Contracts/Events/MediaItems/` with `[MessageType("media.item.asset-unassigned")]`.
- `MediaItemWithdrawnIntegrationEvent` record with `[MessageType("media.item.withdrawn")]`.
- `MediaItemUnarchivedIntegrationEvent` with `[MessageType("media.item.unarchived")]`.
- `MediaItemEditSessionChangedIntegrationEvent` with `[MessageType("media.item.edit-session-changed")]` carrying `SessionId`, `State` (Opened/Reopened/Closed), `OpenedBy`, `Editors`, `OpenedAt?`, `ClosedAt?`, `EventVersion`.
- `MediaItemLegalHoldPlacedIntegrationEvent` with `[MessageType("media.mediaitem.legal-hold-placed")]` carrying `TenantId`, `MediaItemId`, `HoldId`, `PlacedAt`, `AffectedAssetIds[]`, `EventVersion`.
- `MediaItemLegalHoldLiftedIntegrationEvent` with `[MessageType("media.mediaitem.legal-hold-lifted")]` carrying `TenantId`, `MediaItemId`, `HoldId`, `LiftedAt`, `AffectedAssetIds[]`, `EventVersion`.
- `MediaItemRegistrationAddedWhileArchivedIntegrationEvent` with `[MessageType("media.mediaitem.registration-added-while-archived")]` carrying `TenantId`, `MediaItemId`, `RegistrationId`, `Role`, `AddedAt`, `EventVersion`.
- `MediaItemDomainEventMapper` adds 9 overloads: `Map(AssetUnassignedFromRole)` → asset-unassigned; `Map(MediaItemWithdrawn)` → withdrawn; `Map(MediaItemUnarchived)` → unarchived; `Map(EditSessionOpened)` + `Map(EditSessionReopened)` + `Map(EditSessionClosed)` → each yields `MediaItemEditSessionChangedIntegrationEvent`; `Map(LegalHoldPlaced)` + `Map(LegalHoldLifted)`; `Map(RegistrationRefAddedWhileArchived)`.
- `ApplyAssetUnassignmentHandler` (AssetManagement) consumes `media.item.asset-unassigned` → `DetachFromMediaItem`. Sole detach path.
- Asset `HoldersUnderHold` consumers under AssetManagement for `media.mediaitem.legal-hold-placed` / `.lifted` — paginate `AffectedAssetIds`, dispatch `RecordHolderLegalHold<Placed|Lifted>Command` per asset.
- CDK coordination: `cdk-magiq-media` subscriber filter policies include the 7 new types.

## Wire-visibility

Process wire — additive on 7 new types. **Not safe without the SNS filter-policy migration** — see `docs/breaking-changes.md § Cross-cutting ordering constraint — SNS filter-policy scope`. Existing attribute-scoped subscriptions drop body-only publications; CDK filter-policy migration must deploy + propagate before host emits.

(Rename `MediaItemPublicationRequested` → `MediaItemSubmittedForReview` is write-model only — stream reads continue to decode historical events via `[DomainEvent(Aliases = ["mediaitempublicationrequested@1"])]` under WS-28 upcaster framework.)

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-79 (plan MM-119). MM-122 must ship first — provides MediaItemWithdrawn + MediaItemUnarchived + LegalHoldPlaced + LegalHoldLifted + RegistrationRefAddedWhileArchived domain events + MediaItemSubmittedForReview rename. AssetUnassignedFromRole domain event already exists. Add 7 integration-event records + 9 mapper overloads + 3 Asset consumer handlers (sole detach path + 2 legal-hold holder updates).

## Phase 0 — Scope confirmation

- [ ] MM-122 shipped (MediaItemWithdrawn, MediaItemUnarchived, LegalHoldPlaced, LegalHoldLifted, RegistrationRefAddedWhileArchived domain events + MediaItemSubmittedForReview rename)
- [ ] Confirm `AssetUnassignedFromRole` domain event exists at `Catalog.Domain/Aggregates/MediaItems/Events/AssetUnassignedFromRole.cs` (sanity — already present at Arnica re-diff time)
- [ ] Audit EditSessionOpened / EditSessionReopened / EditSessionClosed presence
- [ ] Confirm cdk-magiq-media filter-policy slots available for 7 new types

## Phase 1 — Integration event records (7)

- [ ] `MediaItemAssetUnassignedIntegrationEvent` with `[MessageType("media.item.asset-unassigned")]`
- [ ] `MediaItemWithdrawnIntegrationEvent` with `[MessageType("media.item.withdrawn")]`
- [ ] `MediaItemUnarchivedIntegrationEvent` with `[MessageType("media.item.unarchived")]`
- [ ] `MediaItemEditSessionChangedIntegrationEvent` with `[MessageType("media.item.edit-session-changed")]` carrying session state + editors + event version
- [ ] `MediaItemLegalHoldPlacedIntegrationEvent` with `[MessageType("media.mediaitem.legal-hold-placed")]` carrying `TenantId`, `MediaItemId`, `HoldId`, `PlacedAt`, `AffectedAssetIds[]`, `EventVersion`
- [ ] `MediaItemLegalHoldLiftedIntegrationEvent` with `[MessageType("media.mediaitem.legal-hold-lifted")]` carrying `TenantId`, `MediaItemId`, `HoldId`, `LiftedAt`, `AffectedAssetIds[]`, `EventVersion`
- [ ] `MediaItemRegistrationAddedWhileArchivedIntegrationEvent` with `[MessageType("media.mediaitem.registration-added-while-archived")]` carrying `TenantId`, `MediaItemId`, `RegistrationId`, `Role`, `AddedAt`, `EventVersion`

## Phase 2 — Mapper overloads (9)

- [ ] `IDomainEventMapper<AssetUnassignedFromRole>` + `Map(…)` → `MediaItemAssetUnassignedIntegrationEvent`
- [ ] `IDomainEventMapper<MediaItemWithdrawn>` → `MediaItemWithdrawnIntegrationEvent`
- [ ] `IDomainEventMapper<MediaItemUnarchived>` → `MediaItemUnarchivedIntegrationEvent`
- [ ] `IDomainEventMapper<EditSessionOpened>` / `IDomainEventMapper<EditSessionReopened>` / `IDomainEventMapper<EditSessionClosed>` — each yields `MediaItemEditSessionChangedIntegrationEvent` with correct `State` discriminator
- [ ] `IDomainEventMapper<LegalHoldPlaced>` → `MediaItemLegalHoldPlacedIntegrationEvent`
- [ ] `IDomainEventMapper<LegalHoldLifted>` → `MediaItemLegalHoldLiftedIntegrationEvent`
- [ ] `IDomainEventMapper<RegistrationRefAddedWhileArchived>` → `MediaItemRegistrationAddedWhileArchivedIntegrationEvent`
- [ ] Rename mapper call site `MediaItemPublicationRequested` → `MediaItemSubmittedForReview` (coordinate with MM-122)

## Phase 3 — AssetManagement consumer handlers (3)

- [ ] `ApplyAssetUnassignmentHandler` under `AssetManagement.WriteModel/IntegrationEvents/Consuming/Handlers/` — consumes `media.item.asset-unassigned`, dispatches `ApplyAssetUnassignmentCommand` which calls `DetachFromMediaItem` on the Asset carrying `DetachedBy`. **Sole detach path** — without this, assets stay attached forever after Catalog-side unassign.
- [ ] `MediaItemLegalHoldPlacedFanOutHandler` — consumes `media.mediaitem.legal-hold-placed`, paginates `AffectedAssetIds`, dispatches `RecordHolderLegalHoldPlacedCommand` per asset.
- [ ] `MediaItemLegalHoldLiftedFanOutHandler` — consumes `media.mediaitem.legal-hold-lifted`, paginates `AffectedAssetIds`, dispatches `RecordHolderLegalHoldLiftedCommand` per asset.
- [ ] Each handler reads tenant from `executionContext.TenantId` (not `e.TenantId`); idempotent on duplicate SQS delivery.

## Phase 4 — CDK coordination

- [ ] **Precondition:** every existing subscription on `media-integration-events` migrated to `FilterPolicyScope: MessageBody` (per `docs/breaking-changes.md § Cross-cutting ordering constraint`). Cross-cutting prerequisite; deploy must land + propagate before any body-only publication fires
- [ ] cdk-magiq-media subscriber filter-policy edits for the 7 new types (per consumer section in `event-store-and-messaging.md`)
- [ ] Confirm EventBridge rules + body-scope `type` filters on new types

## Phase 5 — Tests

- [ ] Unit per mapper overload: payload per spec + correct `[MessageType]` string (9 unit tests)
- [ ] Integration: `UnassignAssetFromRole` command → `media.item.asset-unassigned` → AssetManagement `ApplyAssetUnassignmentHandler` detaches the asset
- [ ] Integration: `WithdrawMediaItem` command → `media.item.withdrawn`
- [ ] Integration: `UnarchiveMediaItem` command → `media.item.unarchived`
- [ ] Integration: edit-session open/reopen/close each produce `media.item.edit-session-changed` with correct `State`
- [ ] Integration: legal-hold placed → each `AffectedAssetId`'s `HoldersUnderHold` updated via `RecordHolderLegalHoldPlacedCommand`
- [ ] Integration: legal-hold lifted → each asset's `HoldersUnderHold` cleared
- [ ] Integration: `AddRegistrationRef` on archived item emits `RegistrationRefAdded` **and** `RegistrationRefAddedWhileArchived` → `media.mediaitem.registration-added-while-archived` fires; `Catalog.ArchivedItemsWithActiveRegistrations` metric increments

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
- 2026-10-18: re-diffed under Arnica review fix for finding #8 (catalog Phase 1 regression). Added 4 missing types: `media.item.asset-unassigned` (sole detach path — AssetUnassignedFromRole domain event already exists; integration event + mapper + ApplyAssetUnassignmentHandler all missing), `media.mediaitem.legal-hold-placed`, `media.mediaitem.legal-hold-lifted` (both require AssetManagement HoldersUnderHold fan-out handler builds — compliance-critical), `media.mediaitem.registration-added-while-archived` (operator-alert + Security audit log + Catalog metric). Scope widened: 3 → 7 missing types, 3 → 7 integration-event records, 5 → 9 mapper overloads, 0 → 3 AssetManagement consumer handler builds. Depends-on now cites MM-122 for 5 absent domain events. Phase 4 CDK gains the SNS filter-policy ordering precondition.
