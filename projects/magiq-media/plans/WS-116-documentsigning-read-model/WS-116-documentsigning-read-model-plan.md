---
id: MM-156
type: plan
project: magiq-media
workstream: WS-116-documentsigning-read-model
repo: magiq-media
tags: [magiq-media, documentsigning, read-model, dynamodb, projector, envelope-lookup, webhook-dedup, tenant-exception]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'DocumentSigningSession × write-model, MM-155'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell DocumentSigningSession × read-model
---

# WS-116 — DocumentSigningSession read-model: 4 tables + 2 GSIs + envelope lookup + webhook dedup

**Target repo:** `magiq-media`
**Depends on:** DocumentSigningSession × write-model, MM-155

## Problem

Spec names 4 read-model tables + 2 GSIs. Code has zero — aggregate wholly unbuilt per CLAUDE.md modules table.

| table | PK | SK | role |
|---|---|---|---|
| `media-signing-sessions` | `TENANT#{TenantId}#SIGNING_SESSION#{SigningSessionId}` | `SUMMARY` | summary row for list views + GSI backing |
| `media-signing-session-detail` | `TENANT#{TenantId}#SIGNING_SESSION#{SigningSessionId}` | `DETAIL` | full detail for `GET /{sessionId}` |
| `media-signing-envelope-lookup` | `SigningSessionId` | `LOOKUP` | **only table outside `TENANT#` prefix rule**; feeds webhook tenant resolution |
| `media-signing-webhook-events` | `TENANT#{TenantId}#{ProviderEventId}` | — | webhook deduplication with TTL (`Ttl` attribute) |

GSIs on `media-signing-sessions`:

| GSI | partition | sort | source |
|---|---|---|---|
| `MediaItemIndex` | `TENANT#{TenantId}#ITEM#{MediaItemId}#SIGNING_SESSIONS` | `{CreatedAt}#{SigningSessionId}` | list by owning MediaItem (MM-155 `GET /?mediaItemId=`) |
| `StrandedSessionIndex` (sparse) | `TENANT#{TenantId}#SIGNING_SESSIONS#STRANDED` | `{StrandedAt}#{SigningSessionId}` | ops list (MM-155 `GET /?status=Stranded`) |

Also CLAUDE.md KDPW: "DocumentSigning read-model keys — spec keys detail and summary rows `TENANT#{TenantId}#SIGNING_SESSION#{SigningSessionId}`; code registers no schema identifier."

## What the spec requires

- 2 ReadModels (summary + detail) + schemas + projectors subscribing to signing session domain events.
- `media-signing-envelope-lookup` — **tenant-exempt** table keyed on `SigningSessionId` only; populated at session initiation with `TenantId` attribute; read by unauthenticated webhook route to resolve `TenantId` before HMAC-authenticated handler load (MM-155).
- `media-signing-webhook-events` — webhook idempotency guard. Writes `{ProviderEventId}` conditional on `attribute_not_exists`; TTL purges rows after settle window (e.g. 7 days).
- 2 GSIs on `media-signing-sessions` populated by projector on status change.
- `MaintenanceScanner` quarantine-signing-stranded pass consumes `StrandedSessionIndex` (future scanner workstream).

## Scope boundary

- Read-model shape + schemas + projectors + CDK table provision.
- `media-signing-envelope-lookup` is intentionally outside `TENANT#` prefix per CLAUDE.md key conventions — document explicitly in schema registration + CDK + CLAUDE.md § Key conventions.
- Webhook-dedup middleware → DocumentSigning × middleware (future cell).
- No wire visibility — row shapes only.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-116 (plan MM-156). DocumentSigningSession × write-model must ship first. `media-signing-envelope-lookup` is the one table outside `TENANT#` prefix — document in CDK + CLAUDE.md § Key conventions.

## Phase 0 — Scope confirmation

- [ ] DocumentSigningSession × write-model shipped (domain events)
- [ ] `read-model-metadata` seed infra reachable (WS-55)

## Phase 1 — Primary tables (2)

- [ ] `SigningSessionSummaryReadModel` + schema + projector for `media-signing-sessions`
- [ ] `SigningSessionDetailReadModel` + schema + projector for `media-signing-session-detail`

## Phase 2 — Envelope lookup

- [ ] CDK: `media-signing-envelope-lookup` table in `cdk-magiq-media` — PK `SigningSessionId`, no tenant prefix (intentional)
- [ ] `SigningEnvelopeLookupReadModel { SigningSessionId, TenantId, ClientReference, CreatedAt }` + schema
- [ ] Projector writes lookup row on `SigningSessionInitiated` domain event (first write)
- [ ] Reader interface `ISigningEnvelopeLookupReader.ResolveTenantAsync(sessionId)` returns `TenantId?`

## Phase 3 — Webhook dedup

- [ ] CDK: `media-signing-webhook-events` table with `Ttl` attribute enabled
- [ ] `WebhookEventRecord { TenantId, ProviderEventId, ReceivedAt, Ttl }` + schema
- [ ] `IWebhookDedupStore.TryRecordAsync(tenantId, providerEventId)` → true on first, false on duplicate (conditional `attribute_not_exists`)

## Phase 4 — GSIs (2)

- [ ] `MediaItemIndex` on `media-signing-sessions` + schema registration
- [ ] `StrandedSessionIndex` (sparse) + schema registration

## Phase 5 — Replay CLI

- [ ] `projections replay signing-session` verb (expands coverage N/11)

## Phase 6 — Tests

- [ ] Projector per table: domain event → row + `ProjectedVersion` monotonic
- [ ] Envelope lookup: webhook flow `ResolveTenantAsync(sessionId)` returns correct tenant
- [ ] Webhook dedup: first write succeeds; duplicate refused with `attribute_not_exists`
- [ ] GSI query: list-by-MediaItem returns chronological; `?status=Stranded` returns only stranded

## Phase 7 — Communicate change

- [ ] No `breaking-changes.md` entry — row shapes only
- [ ] CLAUDE.md § Key conventions: document `media-signing-envelope-lookup` tenant-exempt exception alongside existing `media-tenants`/`media-migrations`/`read-model-metadata` exceptions

## Phase 8 — Ship

- [ ] PR to `develop` (magiq-media) + `spec/initial-alignment` (cdk-magiq-media)

## Phase 9 — Close

- [ ] CLAUDE.md § KDPW: bullet removed (DocumentSigning read-model keys)
- [ ] INTEGRATION-BACKLOG.md: MM-156 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-116 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell DocumentSigningSession × read-model; 4 tables + 2 GSIs; `media-signing-envelope-lookup` is the one table outside `TENANT#` prefix rule, feeds unauth webhook tenant resolution per `document-signing.md` ADR)
