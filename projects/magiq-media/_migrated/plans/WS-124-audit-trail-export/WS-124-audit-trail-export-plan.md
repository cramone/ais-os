---
id: MM-163
type: plan
project: magiq-media
workstream: WS-124-audit-trail-export
repo: magiq-media
tags: [magiq-media, audit-trail, access-log, read-model, mediaitem, cross-cutting, compliance]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-18
depends-on: MM-100
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Cross-cutting×http-routes
---

# WS-124 — Audit-trail export route — `/v1/items/{itemId}/audit-trail`

**Target repo:** `magiq-media`
**Spec source:** [`audit-trail.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/audit-trail.md)
**Depends on:** MM-100 (SDK errorCode slot)

## Problem

Spec [`audit-trail.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/audit-trail.md) names a per-item audit-trail export: the record's event stream (state changes) merged with its access-log entries (reads), ordered by `OccurredAt`, in the audit-trail export shape.

Code today:
- Zero `/audit-trail` endpoint
- Zero `media-access-log` projection — reads land no durable row today
- Zero merge-and-serialise component
- Zero `AuditTrailExportShape` records / schemas

## Scope

### Route (1)

| Verb | Path | Response |
|---|---|---|
| GET | `/v1/items/{itemId}/audit-trail?from=&to=` | `200 OK` · audit-trail JSON / NDJSON (format negotiable) |

### Access-log projection

- `media-access-log` DynamoDB table — one row per read (GET /v1/items/{itemId}, GET /download, GET /renditions/{type}/download, GET /package)
- PK `TENANT#{TenantId}#ITEM#{MediaItemId}#ACCESS_LOG`, SK `{OccurredAt}#{AccessLogId}`
- Row members: `MediaItemId`, `ActorId`, `ActorType`, `Operation`, `OccurredAt`, `IpAddress?`, `UserAgent?`, `AssetId?` (for download/rendition routes), `BytesServed?`
- Access-log emission in `QueryApi` host middleware — fires on every item read; async batched write

### Export shape

- Merged chronology: event-stream events (state changes) interleaved with access-log entries (reads)
- Each entry carries: `OccurredAt`, `EntryType` (`state-change` | `access`), `Operation`, `ActorId`, `ActorType`, payload (event-specific or access-log-specific)
- Pagination for large ranges — `from`/`to` + `limit` + `nextPageToken` sealed cursor per F093

### Authorization

- `MediaItem.Read` edge permission; resource predicate same as `GET /v1/items/{itemId}` (owner / edit-session editor / `.All` widening)
- Access-log entries attributable to System actor flagged `system: true`

## Phase 0 — Scope confirmation
- [ ] Read `audit-trail.md` end-to-end
- [ ] Confirm access-log emission scope: which read routes fire a row? (default: all item-scoped reads; refine with user)
- [ ] Confirm format negotiation: JSON single-blob vs NDJSON streaming (expected: NDJSON for large ranges)
- [ ] Confirm retention of access-log table (TTL vs permanent) — likely tied to item retention schedule

## Phase 1 — Access-log projection
- [ ] `media-access-log` CDK + schema + `IReadModel`
- [ ] `AccessLogWriter` middleware in `QueryApi` — batched async write via SQS or direct DynamoDB
- [ ] Row shape validated against spec export shape (reused for export)

## Phase 2 — Export route
- [ ] `GET /v1/items/{itemId}/audit-trail` endpoint on `QueryApi`
- [ ] Event-stream reader + access-log reader; k-way merge by `OccurredAt`
- [ ] NDJSON streaming response
- [ ] Sealed-cursor pagination per F093

## Phase 3 — Compliance mapping
- [ ] `docs/compliance/iso-15489-audit.md` + `pspf-event-logging.md` cite spec + ADR anchors
- [ ] `compliance_coverage.py` validates

## Breaking change

**API wire — additive.** 1 new read endpoint. Access-log emission adds per-read row writes (internal — no wire shape change on existing GET routes, latency impact bounded by batched async write). Breaking-changes.md entry under § Expected — API wire — additive.

## Session log

| Date | Progress |
|---|---|
| 2026-10-18 | Drafted from alignment-sweep Cross-cutting × http-routes cell |
