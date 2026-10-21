---
id: MM-122
type: plan
project: magiq-media
workstream: WS-82-mediaitem-write-model-additions
repo: magiq-media
tags: [magiq-media, catalog, mediaitem, write-model, commands, domain-events, aggregate, checkout, legal-hold, retention, erasure, dispositions, review]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell MediaItem × write-model
---

# WS-82 — MediaItem write-model: ~12 new commands + ~20 new domain events + rename

**Target repo:** `magiq-media`

## Problem

Catalog slice names 45 MediaItem domain events; code implements 27. **20 missing + 1 rename.**

### Missing events (20)

**Content + metadata:**
- `MediaItemTextAlternativeUpdated`

**Role management:**
- `AssetsReorderedInRole` (MM-120 route `PUT /roles/{roleName}/order`)

**Review:**
- `ReviewerWithdrawn` (MM-120 route `DELETE /reviewers/{reviewerId}`)

**Lifecycle:**
- `MediaItemUnarchived` (also required by MM-119)

**Edit session / checkout (4):**
- `EditSessionOpened`
- `EditSessionRenewed`
- `EditSessionReopened`
- `EditSessionClosed`

**Legal hold (2):**
- `LegalHoldPlaced`
- `LegalHoldLifted`

**Retention (5):**
- `MediaItemRetentionScheduleSet`
- `RetentionScheduleDeprecationRecorded`
- `RetentionTriggered`
- `RetentionClockCleared`
- `ExternalRetentionEventPinned`

**Disposition / finalization / supersession (3):**
- `MediaItemDispositionReviewDecisionRecorded`
- `MediaItemFinalizationRecorded`
- `MediaItemSupersessionRecorded`

**Registration + erasure (2):**
- `RegistrationRefAddedWhileArchived`
- `MediaItemPersonalDataErased`

### Rename (1)

- Code's `MediaItemPublicationRequested` → spec's `MediaItemSubmittedForReview`. Add `[DomainEvent(Aliases = ["mediaitempublicationrequested@1"])]` so historical streams decode (once WS-28 upcaster framework ships). Mapper site touched by MM-119.

### Extra events in code not in spec (2)

- `RegistrationRefRemoved` — spec doesn't list; retain as internal (RegistrationManagement bridge) or deprecate if truly unused.
- `SigningSessionUnlinked` — same disposition question (spec lists `SigningSessionLinked` only).

Both audited at Phase 0; delete only if **zero** downstream consumers (streams + projectors + handlers) read them.

### Backing commands (~12)

Each new wire route (MM-120) + aggregate operation needs a command:

| Command | Aggregate method | Primary event(s) |
|---|---|---|
| `UpdateMediaItemTextAlternativeCommand` | `MediaItem.UpdateTextAlternative` | `MediaItemTextAlternativeUpdated` |
| `ReorderAssetsInRoleCommand` | `MediaItem.ReorderAssetsInRole` | `AssetsReorderedInRole` |
| `RemoveReviewerCommand` | `MediaItem.RemoveReviewer` | `ReviewerWithdrawn` |
| `UnarchiveMediaItemCommand` | `MediaItem.Unarchive` | `MediaItemUnarchived` |
| `CheckoutMediaItemCommand` | `MediaItem.OpenEditSession` | `EditSessionOpened` |
| `CheckinMediaItemCommand` | `MediaItem.CloseEditSession` | `EditSessionClosed` |
| `AbandonCheckoutCommand` | `MediaItem.CloseEditSession(abandoned: true)` | `EditSessionClosed` |
| `RenewCheckoutCommand` | `MediaItem.RenewEditSession` | `EditSessionRenewed` |
| `ForceReleaseCheckoutCommand` | `MediaItem.CloseEditSession(systemForceRelease: true)` | `EditSessionClosed` |
| `PlaceLegalHoldCommand` | `MediaItem.PlaceLegalHold` | `LegalHoldPlaced` |
| `LiftLegalHoldCommand` | `MediaItem.LiftLegalHold` | `LegalHoldLifted` |
| `PinRetentionScheduleCommand` | `MediaItem.PinRetentionSchedule` | `MediaItemRetentionScheduleSet` |
| `TriggerRetentionCommand` | `MediaItem.TriggerRetention` | `RetentionTriggered` |
| `PinExternalRetentionEventCommand` | `MediaItem.PinExternalRetentionEvent` | `ExternalRetentionEventPinned` |
| `RecordDispositionReviewDecisionCommand` | `MediaItem.RecordDispositionReviewDecision` | `MediaItemDispositionReviewDecisionRecorded` |
| `FinalizeMediaItemCommand` | `MediaItem.Finalize` | `MediaItemFinalizationRecorded` |
| `SupersedeMediaItemCommand` | `MediaItem.Supersede` | `MediaItemSupersessionRecorded` |
| `DisposeMediaItemCommand` | `MediaItem.Dispose` | lifecycle terminal (clock-cleared + any purge-side effects) |
| `ErasePersonalDataCommand` | `MediaItem.ErasePersonalData` | `MediaItemPersonalDataErased` |

### Aggregate state additions

- `MediaItem.ReviewSession` — `ReviewerAssignment[]` with per-reviewer `Decision`, `AssignedAt`, `DecidedAt?` (CLAUDE.md § Auth); aggregate-invariant refusals on `NotAssignedReviewer` / `ReviewerAlreadyDecided` (MM-118).
- `MediaItem.EditSession` — session state carrying `SessionId`, `OpenedBy`, `Editors[]`, `LeaseExpiresAt?`, `State: Open|Closed`.
- `MediaItem.ActiveHoldIds` — set carrying active legal-hold ids.
- `MediaItem.RetentionSchedule` — pinned schedule + run-state (`Clock: Running|Cleared`, `TriggeredAt?`, `ExternalEvent?`).
- `MediaItem.DispositionReviewOutcome?` — latest review decision.
- `MediaItem.FinalizationState: NotFinalized|Finalized` + `MediaItem.SupersededBy?` id.
- `MediaItem.FilingFolderId?` — for `MediaItemByFilingFolderIndex` (MM-121).
- `MediaItem.TextAlternative?` — content accessibility.

### `MediaItemSnapshot` revision bump

New state → add snapshot members + `[Snapshot(Revision = n)]` bump per WS-57.

## Classification — internal

Wire-visible facets already captured by MM-118 (error codes), MM-119 (integration events: `withdrawn`, `unarchived`, `edit-session-changed`), MM-120 (routes), MM-121 (GSIs). This plan is the backing write-model that each of those plans **depends on**.

## Scope boundary

- **Aggregate + commands + events only.** HTTP = MM-120. Integration events = MM-119. Error codes = MM-118. GSIs = MM-121.
- `MediaItemSubmittedForReview` rename coordinated with MM-119's mapper call-site change in the same release.
- Retention-schedule reconciliation + external-event-pin invariants + dispositions compliance behaviour live under the retention/disposition design in `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`. This plan builds the event + command surface; spec's richer invariants ride the handler Phase.
- Review commands' aggregate-invariant refusals (`NotAssignedReviewer`, `ReviewerAlreadyDecided`) are MM-118's wiring; this plan ensures `ReviewSession` carries the state they refuse against.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-82 (plan MM-122). Add 20 new MediaItem domain events + 12+ commands + aggregate methods + MediaItem state additions (ReviewSession, EditSession, ActiveHoldIds, RetentionSchedule, DispositionReviewOutcome, FinalizationState, SupersededBy, FilingFolderId, TextAlternative). Internal — route/error/integration-event wire captured by MM-120/118/119.

## Phase 0 — Scope confirmation

- [ ] Code audit: 27 of 45 events present. Run under broadened glob — walk `Catalog.Domain/Aggregates/MediaItems/Events/*.cs` **plus** `Catalog.Domain/Aggregates/MediaItems/ValueObjects/*.cs` for aggregate state slots that back the new events (per Arnica fix on narrow-glob code read scope). Narrow `MediaItem*.cs` glob at draft time still matched the Events/ folder correctly for this plan — re-verify in case any new event name doesn't start with `MediaItem`
- [ ] Confirm extras (`RegistrationRefRemoved`, `SigningSessionUnlinked`) have consumers before retaining; else deprecate
- [ ] WS-28 upcaster framework shipped (needed for `MediaItemSubmittedForReview` alias)

## Phase 1 — Content + metadata + role management

- [ ] `MediaItemTextAlternativeUpdated` event + `UpdateMediaItemTextAlternativeCommand` + aggregate method
- [ ] `AssetsReorderedInRole` event + `ReorderAssetsInRoleCommand` + aggregate method

## Phase 2 — Review

- [ ] `ReviewerWithdrawn` event + `RemoveReviewerCommand` + aggregate method
- [ ] `MediaItem.ReviewSession` state carrying `ReviewerAssignment[]` (identity-addressed, per-reviewer `Decision`/`AssignedAt`/`DecidedAt?`)
- [ ] Aggregate-invariant refusals on `NotAssignedReviewer` / `ReviewerAlreadyDecided` (MM-118 wiring)

## Phase 3 — Lifecycle unarchive

- [ ] `MediaItemUnarchived` event + `UnarchiveMediaItemCommand` + aggregate method

## Phase 4 — Edit session / checkout

- [ ] `EditSessionOpened` + `CheckoutMediaItemCommand`
- [ ] `EditSessionClosed` + `CheckinMediaItemCommand`, `AbandonCheckoutCommand`, `ForceReleaseCheckoutCommand`
- [ ] `EditSessionRenewed` + `RenewCheckoutCommand`
- [ ] `EditSessionReopened` (session reopen path)
- [ ] `MediaItem.EditSession` state + lease semantics; `CheckoutLeaseExpiresAt` on summary row for MM-121 GSI

## Phase 5 — Legal hold

- [ ] `LegalHoldPlaced` + `PlaceLegalHoldCommand`
- [ ] `LegalHoldLifted` + `LiftLegalHoldCommand`
- [ ] `MediaItem.ActiveHoldIds` state consulted by Archive/Delete/Erase guards

## Phase 6 — Retention

- [ ] `MediaItemRetentionScheduleSet` + `PinRetentionScheduleCommand`
- [ ] `RetentionScheduleDeprecationRecorded` (consumer: `MediaProfileDeprecatedEventHandler` propagates deprecation)
- [ ] `RetentionTriggered` + `TriggerRetentionCommand`
- [ ] `RetentionClockCleared`
- [ ] `ExternalRetentionEventPinned` + `PinExternalRetentionEventCommand`
- [ ] `MediaItem.RetentionSchedule` state (pinned schedule + run-state + external event pin)

## Phase 7 — Disposition / finalization / supersession

- [ ] `MediaItemDispositionReviewDecisionRecorded` + `RecordDispositionReviewDecisionCommand`
- [ ] `MediaItemFinalizationRecorded` + `FinalizeMediaItemCommand`
- [ ] `MediaItemSupersessionRecorded` + `SupersedeMediaItemCommand`
- [ ] `DisposeMediaItemCommand` + aggregate method
- [ ] `MediaItem.DispositionReviewOutcome?`, `FinalizationState`, `SupersededBy?` state

## Phase 8 — Registration + erasure

- [ ] `RegistrationRefAddedWhileArchived` event (distinct from `RegistrationRefAdded` — archived predicate)
- [ ] `MediaItemPersonalDataErased` + `ErasePersonalDataCommand`

## Phase 9 — Rename + snapshot bump

- [ ] Rename `MediaItemPublicationRequested` type → `MediaItemSubmittedForReview` with `[DomainEvent(Aliases = ["mediaitempublicationrequested@1"])]`
- [ ] `MediaItem.FilingFolderId?` + `MediaItem.TextAlternative?` state (feed GSIs + row members)
- [ ] `MediaItemSnapshot` + `[Snapshot(Revision = n)]` bump per WS-57; add new state members
- [ ] Snapshot test on each new event: event → Apply → state mutation

## Phase 10 — Tests

- [ ] Unit per aggregate method: pre-state + command → expected event(s)
- [ ] Unit per handler: guard precedence refuses per MM-118 codes
- [ ] Unit: aggregate-invariant review refusals
- [ ] Integration: end-to-end checkout → edit → checkin
- [ ] Integration: retention pin → clock → disposition review → finalization

## Phase 11 — Ship

- [ ] PR to `develop` (consider sub-split if PR too large — review Phase 4-7 as sub-PRs)

## Phase 12 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-122 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-82 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaItem × write-model; status candidate; largest write-model workstream; may split into sub-PRs during execution)
- 2026-10-18: re-diffed under Arnica review fixes (findings #2 narrow glob + #8 catalog Phase 1 regression). **Confirmed clean.** All 3 Arnica-surfaced events already covered: `LegalHoldPlaced` + `LegalHoldLifted` in Phase 5, `RegistrationRefAddedWhileArchived` in Phase 8. Rename `MediaItemPublicationRequested` → `MediaItemSubmittedForReview` in Phase 9. 4 EditSession events in Phase 4. 20-missing count unchanged (27 of 45 code events verified; 2 extras + 20 missing + 1 rename). AssetUnassignedFromRole already in code (not in missing list). Phase 0 note added instructing broadened-glob code audit including `Aggregates/MediaItems/ValueObjects/` for state-slot verification.
