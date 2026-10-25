---
id: MM-162
type: plan
project: magiq-media
workstream: WS-123-sip-dip-exports
repo: magiq-media
tags: [magiq-media, sip-dip, oais, veo, dod-5015, nara, transfer, export, mediaitem-lifecycle]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-18
depends-on: MM-100, MM-118, MM-122
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Cross-cutting×http-routes
---

# WS-123 — SIP/DIP export + `TransferRecord`/`ArchiveRecord` commands

**Target repo:** `magiq-media`
**Spec source:** [`sip-dip-exports.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/sip-dip-exports.md), [`preservation.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/preservation.md)
**Depends on:** MM-100 (SDK errorCode slot), MM-118 (MediaItem error codes — add transfer-destination codes), MM-122 (MediaItem write-model — add 2 lifecycle commands + 1 event)

## Problem

Spec [`sip-dip-exports.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/sip-dip-exports.md) names three destination profiles (VEO, DoD 5015.02 transfer, NARA transfer) and two lifecycle commands (`TransferRecord`, `ArchiveRecord`) that produce a SIP, plus a DIP read route for consumer retrieval.

Code today:
- Zero `TransferRecord` / `ArchiveRecord` / `RecordTransferred` references
- Zero `/package` endpoint
- Zero destination-profile packaging implementation (VEO XML, DoD 5015 ZIP, NARA EAD + METS)
- Zero transfer-bucket S3 writes
- Zero chain-of-custody receipt command

## Scope

### Routes (1 DIP read + 1 package status)

| Verb | Path | Response |
|---|---|---|
| GET | `/v1/items/{itemId}/package?profile=` | Sync for small records (`200 OK` + package bytes); async for large (`202 Accepted` + `Location: /v1/items/{itemId}/package-status`) |
| GET | `/v1/items/{itemId}/package-status` | `200 OK` package status + download URL when ready |

### Commands (2)

- `TransferRecord` (`MediaItem.Manage`) with `destinationProfile ∈ { veo, dod-5015-transfer, nara-transfer, custom }` → produces SIP → writes to transfer bucket → emits `RecordTransferred` on receipt ack
- `ArchiveRecord` (`MediaItem.Manage`) — long-term archive variant; same SIP pipeline but destination = tenant archive bucket

### Events (2 new on MediaItem)

- `MediaItemTransferInitiated` — SIP packaging requested + target destination recorded
- `MediaItemTransferred` — receipt acknowledgment received from destination; item moves to post-transfer state (disposed if `Transfer` disposition action)

### Packaging

Per destination profile:
- **VEO** — VERS v3 XML schema; multi-VEO shape for complex records (one per aggregate root + per linked content object with VERS relationship type)
- **DoD 5015.02 transfer** — ZIP containing metadata CSV + content objects per DoD 5015 § C2.2.6.4
- **NARA transfer** — EAD finding aid + METS wrapper + content objects

### Format-constraint preflight

- Export refused `AssetFormatConstraintNotMet 422` on destination format mismatch (per existing `AssetErrorCodes.AssetFormatConstraintNotMet` under MM-101)
- Fix: run `MigrateFormat` on asset (per `preservation.md § Format migration` — separate plan if not yet drafted)

### Chain of custody

- Receiving system appends receipt event through `AcknowledgeTransferReceipt` command
- Command dispatched from transfer-receipt-callback webhook (platform-integration System actor)

## Phase 0 — Scope confirmation
- [ ] Read `sip-dip-exports.md` + `preservation.md § Format migration` end-to-end
- [ ] Confirm 3 named profiles cover shipped scope (deferred: custom-profile builder for tenant-defined packages)
- [ ] Confirm `AcknowledgeTransferReceipt` auth boundary (platform-integration role vs tenant-admin role)
- [ ] Confirm transfer-bucket + archive-bucket CDK provisioning in `cdk-magiq-media` (likely new infra)

## Phase 1 — MediaItem lifecycle extension
- [ ] 2 commands (`TransferRecord`, `ArchiveRecord`) + 1 receipt-ack command
- [ ] 2 domain events (`MediaItemTransferInitiated`, `MediaItemTransferred`) + 1 receipt-ack event
- [ ] `MediaItem.TransferState` state (`Pending`/`Packaging`/`Transferred`/`Failed`)
- [ ] Snapshot bump per WS-57

## Phase 2 — Packaging engine
- [ ] `ISipBuilder` interface + 3 implementations (VEO, DoD, NARA)
- [ ] Each builder produces: metadata XML/CSV + content-object manifest + chain-of-custody excerpt
- [ ] Multi-VEO shape detection for complex records
- [ ] Processing module hosts the builders (large/async operation)

## Phase 3 — DIP route + status
- [ ] `GET /v1/items/{itemId}/package?profile=` endpoint — sync up to configurable size (default 100 MB), 202 above
- [ ] `GET /v1/items/{itemId}/package-status` for async
- [ ] Package served via pre-signed S3 URL

## Phase 4 — Transfer bucket + ack webhook
- [ ] CDK adds transfer bucket + archive bucket per tenant (via tenant-provisioning)
- [ ] `POST /v1/integrations/transfer-receipt/webhooks` — HMAC-guarded, resolves tenant via `media-transfer-envelope-lookup`
- [ ] Mirrors DocumentSigning webhook pattern (MM-158 bespoke 3-stage middleware)

## Phase 5 — Compliance mapping
- [ ] `docs/compliance/dod-5015.md`, `nara-transfer.md`, `vers-v3.md` cite spec + ADR anchors
- [ ] `compliance_coverage.py` validates

## Breaking change

**API wire — additive.** 2 new routes + 3 new MediaItem lifecycle commands + 1 webhook. Breaking-changes.md entry under § Expected — API wire — additive. Narrow — only hit by tenants exercising retention `Transfer` disposition or ad-hoc export.

## Session log

| Date | Progress |
|---|---|
| 2026-10-18 | Drafted from alignment-sweep Cross-cutting × http-routes cell |
