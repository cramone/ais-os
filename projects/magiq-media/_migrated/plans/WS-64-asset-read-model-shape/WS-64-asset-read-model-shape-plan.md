---
id: MM-104
type: plan
project: magiq-media
workstream: WS-64-asset-read-model-shape
repo: magiq-media
tags: [magiq-media, asset-management, read-model, stored-shape, projections]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-15
depends-on: MM-068
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell Asset×read-model
---

# WS-64 — AssetManagement: `media-assets` SK + two sparse GSIs

**Target repo:** `magiq-media`
**Depends on:** MM-068 (`projections rebuild-index` CLI — needed for GSI backfill without full projector rebuild) + MM-067 (replay CLI covers Asset)

## Problem

Spec [`event-store-and-messaging.md § DynamoDB Tables`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/event-store-and-messaging.md#dynamodb-tables) and § DynamoDB Table GSIs name:

| Table / Index | Spec SK or GSI shape | Code |
|---|---|---|
| `media-assets` SK | `{AssetId}` (bare — list tables carry no prefix per § DynamoDB Tables) | `SUMMARY#{AssetId}` (deployed under `AssetSummarySchema.SortKeyPrefix = "SUMMARY#"`) |
| `media-assets.PendingAssetByInitiationIndex` GSI | sparse; `TENANT#{TenantId}#ASSETS#PENDING` · `{CreatedAt}#{AssetId}` — upload-expiry scanner reads it | **Not registered** |
| `media-assets.ContainsVirusAwaitingQuarantineIndex` GSI | sparse; `TENANT#{TenantId}#ASSETS#AWAITING_QUARANTINE` · `{InfectionDetectedAt}#{AssetId}` — `MaintenanceScanner` quarantine-retry pass | **Not registered** |

Consequences:
- `media-assets.SK` deployed value disagrees with spec. CLAUDE.md § Key conventions footnote names `media-assets` as a bare-id list table — current prefix means the stored rows cannot be read spec-style.
- Upload-expiry pass has no index to walk; must scan whole table.
- Quarantine-move retry pass has no index; `MaintenanceScanner` quarantine-retry pass cannot do its job without the sparse index — infected rows accumulate undetected post-process.

## Scope

### `media-assets.SK` migration

- `AssetSummarySchema` drops the `SUMMARY#` prefix. New schema version bumps `read-model-metadata.schemaVersion` for `media-assets`.
- Deploy under `media-assets-v2`; projector replay (MM-067 covers Asset — shipped) rebuilds rows under the correct SK.
- Cutover via `read-model-metadata.ActiveVersion` flip.

### Register two sparse GSIs

- `PendingAssetByInitiationIndex` (`GSI2PK` / `GSI2SK`) — projector writes `GSI2PK = TENANT#{TenantId}#ASSETS#PENDING` + `GSI2SK = {CreatedAt}#{AssetId}` **only while `Status = Pending`**. Row drops off GSI on status transition (sparse — attribute absence removes).
- `ContainsVirusAwaitingQuarantineIndex` (`GSI3PK` / `GSI3SK`) — projector writes `GSI3PK = TENANT#{TenantId}#ASSETS#AWAITING_QUARANTINE` + `GSI3SK = {InfectionDetectedAt}#{AssetId}` **only while `Status = ContainsVirus` and `QuarantineMoveConfirmedAt is null`**. Drops after confirm.
- Schema types: `PendingAssetByInitiationIndexSchema`, `ContainsVirusAwaitingQuarantineIndexSchema` under `IProjectionIndexSchema<AssetSummaryReadModel>` pattern (reuse of `AssetByMediaItemIndexSchema` as template).

### CDK side

- `cdk-magiq-media` provisions `GSI2` + `GSI3` on `media-assets-v2` with the names above. Projection-friendly: KEYS_ONLY or ALL depending on scanner needs.

## Phase 0 — Confirm
- [ ] Verify no production data loss from SK change — projector replay from Asset event stream produces the correct rows
- [ ] Confirm MM-067 (replay CLI covers Asset) has shipped — yes, `MM-077 WS-55 shipped 2026-10-15`, but check `rebuild-index` (MM-068 / WS-34) status before scheduling
- [ ] Confirm scanner pass code paths that would consume the new indexes (`UploadExpiryScanner`, `MaintenanceScanner` quarantine-retry)

## Phase 1 — SDK verify (no change expected)
- [ ] `IProjectionIndexSchema<TRow>` supports sparse semantics by projector returning null for `WritePartitionKeyValue` — verify in SDK

## Phase 2 — Schema registrations (magiq-media)
- [ ] `AssetSummarySchema` drops `SortKeyPrefix` — new SK is bare `{AssetId}`
- [ ] Bump `media-assets.schemaVersion` to v2
- [ ] `read-model-metadata` seed row for new version carries `retainedPreviousVersions: ["v1"]`
- [ ] `PendingAssetByInitiationIndexSchema` registered — sparse write via nullable
- [ ] `ContainsVirusAwaitingQuarantineIndexSchema` registered — sparse write via nullable

## Phase 3 — Projector wiring
- [ ] `AssetSummaryProjector` writes the two GSI partitions under the correct status predicates
- [ ] Status-transition events clear the sparse attributes (projector emits GSI PKs as null)

## Phase 4 — CDK
- [ ] Separate `cdk-magiq-media` PR provisions `media-assets-v2` with GSI2 + GSI3
- [ ] Deploy order: CDK first (table + GSIs exist), then magiq-media (projector writes to them)

## Phase 5 — Replay
- [ ] `ProjectionReplay rotate --read-model media-assets --tenant <id>` per tenant to populate v2
- [ ] Flip `read-model-metadata.ActiveVersion` for `media-assets`
- [ ] Retain v1 for one release

## Phase 6 — Tests
- [ ] Unit: projector writes sparse GSI attributes only when status matches
- [ ] Integration: Pending asset → row appears on `PendingAssetByInitiationIndex`; confirm → row drops
- [ ] Integration: Infected asset → row appears on `ContainsVirusAwaitingQuarantineIndex`; quarantine-move-confirmed → row drops

## Phase 7 — Ship
- [ ] magiq-media CLAUDE.md: close Asset read-model shape bullet

## Acceptance criteria

- `media-assets` SK matches spec (bare `{AssetId}`)
- Both sparse GSIs register + projector writes correctly
- `MaintenanceScanner` quarantine-retry pass can walk the sparse index

## Breaking-change note

Internal (stored shape). No API wire change. Downstream consumers of `media-assets` are internal projectors + scanners only; migration via `read-model-metadata` version flip means cutover is atomic.

## Session log

- 2026-10-15: plan drafted by alignment sweep (Asset×read-model cell). `status: candidate` pending triage. Depends on MM-068 (rebuild-index CLI); MM-067 flipped `ready` on MM-077 ship.
