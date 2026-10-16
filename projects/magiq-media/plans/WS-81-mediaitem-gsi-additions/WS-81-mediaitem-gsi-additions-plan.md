---
id: MM-121
type: plan
project: magiq-media
workstream: WS-81-mediaitem-gsi-additions
repo: magiq-media
tags: [magiq-media, catalog, mediaitem, read-model, dynamodb, gsi, checkout-lease, filing-folder]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell MediaItem × read-model
---

# WS-81 — MediaItem GSIs: `MediaItemByLeaseExpiryIndex` + `MediaItemByFilingFolderIndex`

**Target repo:** `magiq-media` + `cdk-magiq-media`

## Problem

Spec names 4 MediaItem GSIs; code registers 2. Missing:

| GSI | Shape | Purpose |
|---|---|---|
| `MediaItemByLeaseExpiryIndex` | PK **constant** `"CHECKOUT_LEASE"` (**not tenant-partitioned**) · SK `{CheckoutLeaseExpiresAt:O}#{MediaItemId}` | Cross-tenant lease-expiry scanner (F079: `MediaItemLeaseExpiryScanner`). Sparse on open checkout lease |
| `MediaItemByFilingFolderIndex` | PK `TENANT#{TenantId}#FILING_FOLDER#{FolderId}#ITEMS` · sparse | `FolderClosedRetentionFanOutHandler` (MM-114) paginates items by their **filing** folder (distinct from containing folder); retention-pin fan-out source |

Existing GSIs:
- `MediaItemByFolderIndex` — registered (`MediaItemByFolderIndexSchema`)
- `MediaItemVersionByMediaItemIndex` — registered

## Why missing

- `MediaItemByLeaseExpiryIndex`: checkout flow not built (MM-120 missing 5 checkout verbs; MM-118 missing checkout error codes; underlying checkout aggregate state not built — belongs to MediaItem × write-model cell plan). GSI landing requires the row to carry `CheckoutLeaseExpiresAt` member, which is set when checkout opens.
- `MediaItemByFilingFolderIndex`: `FilingFolderId` member on MediaItem detail/summary row not surfaced to GSI. MM-114's `FolderClosedRetentionFanOutHandler` scans this index when a folder closes.

## Scope boundary

- **GSI definitions + sparse-write semantics only.**
- Row-member additions (`CheckoutLeaseExpiresAt`, `FilingFolderId`) are a write-model concern — MediaItem × write-model cell plan.
- Scanner implementation (`MediaItemLeaseExpiryScanner`) is a magiq-media host build under F079 WS-15b or a separate `MaintenanceScanner` pass plan.
- Retention-pin fan-out handler build (consumer) is MM-114.
- Cross-tenant partition semantics for `MediaItemByLeaseExpiryIndex` require F079 scanner-friendly execution-context factory (shipped — see `IScannerExecutionContextFactory`).

## What the spec requires

- `MediaItemByLeaseExpiryIndex` GSI on `media-item` table (or whichever table carries `CheckoutLeaseExpiresAt`). PK `S` constant `"CHECKOUT_LEASE"`. SK `S` `{CheckoutLeaseExpiresAt:O}#{MediaItemId}`. Sparse — only rows with open checkout lease are projected.
- `MediaItemByFilingFolderIndex` GSI on `media-items` summary table. PK `S` `TENANT#{TenantId}#FILING_FOLDER#{FolderId}#ITEMS`. Sparse — only rows with non-null `FilingFolderId` are projected.
- CDK provisions both; magiq-media registers schemas; projectors populate GSI attributes on relevant events (CheckoutOpened/Closed/Expired for lease; FilingFolder set/clear for filing).

## Classification — internal

No wire shape changes. GSIs are query-side only. Dependent features (`MediaItemLeaseExpiryScanner`, `FolderClosedRetentionFanOutHandler`) are wire-visible but captured in their own plans (F079 WS-15b; MM-114).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Also open `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`. Paste:

> Picking up WS-81 (plan MM-121). Depends on MediaItem × write-model plan (CheckoutLeaseExpiresAt + FilingFolderId row members). Add 2 GSIs: lease-expiry (constant-partition, cross-tenant) + filing-folder (sparse).

## Phase 0 — Scope confirmation

- [ ] MediaItem × write-model plan shipped (row members present)
- [ ] F079 WS-15b shipped (scanner-friendly context factory available)
- [ ] Confirm `media-item` + `media-items` schemas registered (sanity)

## Phase 1 — CDK (cdk-magiq-media)

- [ ] `MediaItemByLeaseExpiryIndex` GSI on `media-item` table: PK `S` + SK `S`, projection `KEYS_ONLY` (scanner only reads keys + dispatches by id)
- [ ] `MediaItemByFilingFolderIndex` GSI on `media-items` table: PK `S` + SK `S`, projection `KEYS_ONLY`
- [ ] IAM — grant `MaintenanceScanner` role Query on `MediaItemByLeaseExpiryIndex`
- [ ] IAM — grant `EventConsumers` role Query on `MediaItemByFilingFolderIndex` (closure fan-out source)
- [ ] Deploy manifest + `read-model-metadata` seed entries (if GSI additions trigger version bump — align with WS-55 pattern)

## Phase 2 — magiq-media schema registration

- [ ] `MediaItemByLeaseExpiryIndexSchema` under `Catalog.ReadModel.Infrastructure/Queries/Schemas/MediaItems/` with `IProjectionIndexSchema<MediaItemDetailReadModel, ListExpiredLeasesQuery>` (new query added for scanner)
- [ ] `MediaItemByFilingFolderIndexSchema` under same folder with `IProjectionIndexSchema<MediaItemSummaryReadModel, ListItemsByFilingFolderQuery>`
- [ ] Register in `AddCatalogReadModel` DI

## Phase 3 — Projector population

- [ ] `MediaItemDetailProjector` (or summary projector for filing-folder) writes GSI attributes
- [ ] Lease-expiry: on `CheckoutOpened` set `LeaseIndexPK = "CHECKOUT_LEASE"`, `LeaseIndexSK = "{expiresAt:O}#{id}"`; on `CheckoutClosed`/`CheckoutExpired` clear both (sparse)
- [ ] Filing-folder: on filing-set/clear event, set/clear GSI attributes (sparse)

## Phase 4 — Tests

- [ ] Integration: open checkout → row appears in `MediaItemByLeaseExpiryIndex`
- [ ] Integration: close checkout → row disappears (sparse)
- [ ] Integration: set filing folder → row appears in `MediaItemByFilingFolderIndex`
- [ ] Integration: cross-tenant Query on `MediaItemByLeaseExpiryIndex` returns rows from multiple tenants

## Phase 5 — Ship

- [ ] PR to `develop` on cdk-magiq-media
- [ ] PR to `develop` on magiq-media
- [ ] Coordinate: CDK first, then host

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-121 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-81 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaItem × read-model; status candidate; depends on MediaItem × write-model plan for row members)
