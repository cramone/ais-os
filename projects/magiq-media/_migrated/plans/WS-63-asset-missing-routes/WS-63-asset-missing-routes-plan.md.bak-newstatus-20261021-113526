---
id: MM-103
type: plan
project: magiq-media
workstream: WS-63-asset-missing-routes
repo: magiq-media
tags: [magiq-media, asset-management, http-routes, api-wire]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
depends-on: -
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Asset×http-routes
---

# WS-63 — AssetManagement: 6 missing HTTP routes + tags shape

**Target repo:** `magiq-media`
**Depends on:** none

## Problem

Spec [`asset.api.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/contexts/AssetManagement/aggregates/Asset/asset.api.md) names 19 HTTP routes. Code (`AssetManagement.WriteModel.Endpoints/V1/`, `AssetManagement.ReadModel.Endpoints/V1/`) wires 13.

### Missing routes (6)

| Verb | Path | Purpose |
|---|---|---|
| POST | `/v1/assets/{assetId}/tags/add` | Add tags (additive) |
| POST | `/v1/assets/{assetId}/tags/remove` | Remove tags (additive) |
| POST | `/v1/assets/{assetId}/reprocess` | Re-run processing pipeline — `AssetReprocessingRequested` event |
| POST | `/v1/assets/{assetId}/erase-personal-data` | DSR erasure. Named exception from `If-Match` precondition |
| GET | `/v1/assets/{assetId}/quarantine/download` | Operator download of quarantined object. Resolves `media-quarantine` bucket |
| POST | `/v1/assets/uploads/bulk` | Bulk-initiate upload. Per-item outcome in bulk envelope's `failed[]` |

### Shape divergence

| Spec | Code | Impact |
|---|---|---|
| `POST /v1/assets/{assetId}/tags/add` + `POST /v1/assets/{assetId}/tags/remove` (two additive routes) | `PUT /assets/{assetId}/tags` (one whole-replace) | Replace semantics drops atomic tag deltas. Client cannot "add X" without reading the current set + resubmitting. Spec also makes the write idempotent per-tag — PUT whole-list is idempotent on the list, not the individual tags |

## Scope

### Add 6 routes

- `AddAssetTagsEndpoint` + `RemoveAssetTagsEndpoint` + commands `AddAssetTagsCommand(TenantId, AssetId, Tags[], OccurredAt)` / `RemoveAssetTagsCommand` + handlers
- `ReprocessAssetEndpoint` + `RequestReprocessingCommand(TenantId, AssetId, RequestedBy)` + handler dispatching to `Asset.RequestReprocessing`
- `EraseAssetPersonalDataEndpoint` + `EraseAssetPersonalDataCommand` + handler. Named exception from § Irreversible operations require `If-Match` — route **does not take** `If-Match` (per api-conventions.md § Irreversible operations)
- `GetQuarantineDownloadUrlEndpoint` on read side. Resolves `media-quarantine` bucket from asset status; aggregate must be in `ContainsVirus`. Permission scoped to operator role
- `BulkInitiateAssetUploadsEndpoint` + `BulkInitiateAssetUploadsCommand` + handler. Per-item outcome rides `BulkOperationResult` envelope. Code already has bulk-confirm half

### Shape change: tags

- Deprecate `PUT /v1/assets/{assetId}/tags` **replace** route
- Add two additive routes above
- Interim: both coexist for one release; `PUT` emits `Deprecation` + `Sunset` response headers per api-conventions.md § Deprecation Policy

## Phase 0 — Confirm
- [ ] Verify DSR erasure permission + scope per spec
- [ ] Verify quarantine download operator role name
- [ ] Confirm `AssetReprocessingRequested` domain event already exists (yes — in Domain/Aggregates/Events/)
- [ ] Confirm `AssetPersonalDataErased` domain event exists (grep says yes)

## Phase 1 — Commands + handlers (6)
- [ ] `AddAssetTagsCommand` + handler. Append-only semantics
- [ ] `RemoveAssetTagsCommand` + handler
- [ ] `RequestReprocessingCommand` + handler → dispatches `Asset.RequestReprocessing`
- [ ] `EraseAssetPersonalDataCommand` + handler → `Asset.ErasePersonalData` + emits `AssetPersonalDataErased`
- [ ] `BulkInitiateAssetUploadsCommand` + handler

## Phase 2 — Endpoints (6)
- [ ] `AddAssetTagsEndpoint` POST `/assets/{assetId}/tags/add`
- [ ] `RemoveAssetTagsEndpoint` POST `/assets/{assetId}/tags/remove`
- [ ] `ReprocessAssetEndpoint` POST `/assets/{assetId}/reprocess`
- [ ] `EraseAssetPersonalDataEndpoint` POST `/assets/{assetId}/erase-personal-data`. **No `If-Match` acceptance** per spec exception
- [ ] `GetQuarantineDownloadUrlEndpoint` GET `/assets/{assetId}/quarantine/download`
- [ ] `BulkInitiateAssetUploadsEndpoint` POST `/assets/uploads/bulk`

## Phase 3 — Deprecate `PUT /tags`
- [ ] `TagAssetEndpoint` (`PUT /assets/{assetId}/tags`): add `Deprecation: true` + `Sunset: <date>` response headers
- [ ] Removal scheduled release + 1

## Phase 4 — Tests
- [ ] Integration test per new route — happy path + each spec'd error code
- [ ] Operator-only quarantine download — refusal for non-operator caller
- [ ] Erase personal data refused under legal hold (`ErasureRefusedUnderLegalHold` 422)
- [ ] Bulk-initiate per-item outcomes land in `failed[]` with correct bulk codes

## Phase 5 — Ship
- [ ] PR to `develop`
- [ ] magiq-media CLAUDE.md: close Asset-routes gap bullet

## Acceptance criteria

- 19 Asset routes present per spec
- Tag mutations use additive `tags/add` + `tags/remove`
- `PUT /tags` deprecated with headers; removed next release
- Erase-personal-data route takes no `If-Match`

## Breaking-change note

Wire-visible: `PUT /tags` deprecation is a signalled change — clients that pin on it must migrate to the two additive routes within deprecation window. Adding 6 new routes is additive — no existing client affected.

## Session log

- 2026-10-15: plan drafted by alignment sweep (Asset×http-routes cell). `status: candidate` pending triage.
