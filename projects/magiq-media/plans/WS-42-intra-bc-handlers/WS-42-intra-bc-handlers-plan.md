---
id: MM-062
type: plan
project: magiq-media
workstream: WS-42-intra-bc-handlers
repo: magiq-media
tags: [magiq-media, intra-bc, handlers, catalog, change-requests]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-42.
---

# WS-42 — Intra-BC handlers + `MediaProfileNameConflict` on taken name

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Build:
- `AssetUploadConfirmedReferenceHandler`
- `AssetProcessingBypassedEventHandler`
- `AssetProcessingTimeoutRecoveredEventHandler`
- `AssetMultipartUploadAbortedEventHandler`
- `ChangeRequestLifecycleEventHandler`
- `ReviewChangeRequestCloser`

Plus: MediaProfile handlers raise `MediaProfileNameConflict` (409) on taken name.

## Session invocation

> Picking up WS-42 (plan MM-062). Six intra-BC event handlers to build + MediaProfileNameConflict raise. Read each handler's intended behaviour from `docs/spec/`. Register in appropriate module's event-consumer host.

## Phase 0 — Scope confirmation
- [ ] For each handler: read spec event + consumer contract
- [ ] Confirm MM-015 ships Tier-1 refusal shape (optional for MediaProfileNameConflict mapping)

## Phase 1 — Catalog asset-reference handlers
- [ ] `AssetUploadConfirmedReferenceHandler` on `AssetUploadConfirmedIntegrationEvent`
- [ ] `AssetProcessingBypassedEventHandler` on bypass path
- [ ] `AssetProcessingTimeoutRecoveredEventHandler` on timeout-recovered path
- [ ] `AssetMultipartUploadAbortedEventHandler` on multipart-abort path

## Phase 2 — ChangeRequest handlers
- [ ] `ChangeRequestLifecycleEventHandler`
- [ ] `ReviewChangeRequestCloser`

## Phase 3 — MediaProfileNameConflict
- [ ] MediaProfile create/rename raises on taken name → 409

## Phase 4 — Tests
- [ ] Unit per handler
- [ ] Integration: event → handler dispatch → aggregate update

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] spec-divergence/INDEX.md: WS-42 → § Shipped
- [ ] Remove `Intra-BC handlers not built` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
