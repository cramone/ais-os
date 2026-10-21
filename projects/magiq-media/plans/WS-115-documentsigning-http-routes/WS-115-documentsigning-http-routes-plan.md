---
id: MM-155
type: plan
project: magiq-media
workstream: WS-115-documentsigning-http-routes
repo: magiq-media
tags: [magiq-media, documentsigning, signingsession, http, routes, webhook, hmac, reconcile]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'DocumentSigningSession × write-model, DocumentSigningSession × read-model, MM-154'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell DocumentSigningSession × http-routes
---

# WS-115 — DocumentSigningSession HTTP routes: 8 new endpoints

**Target repo:** `magiq-media`
**Depends on:** DocumentSigningSession × write-model + read-model, MM-154

## Problem

Spec names 8 DocumentSigningSession HTTP routes. Code wires zero — aggregate wholly unbuilt per CLAUDE.md modules table.

| verb | path | kind |
|---|---|---|
| POST | `/v1/media-items/{mediaItemId}/signing-sessions` | initiate (mints `sessionId` server-side — see spec) |
| POST | `/v1/signing-sessions/{sessionId}/cancel` | lifecycle |
| POST | `/v1/signing-sessions/{sessionId}/reconcile` | operator-recovery (force-unlink stranded; `/items/{itemId}/signing-session/force-unlink` family) |
| POST | `/v1/signing-sessions/{sessionId}/erase-personal-data` | named `If-Match` exception |
| POST | `/v1/integrations/secured-signing/webhooks` | SecuredSigning adapter callback (**unauthenticated**; HMAC-guarded; tenant resolved via `media-signing-envelope-lookup` by client reference) |
| GET | `/v1/signing-sessions/{sessionId}` | detail |
| GET | `/v1/signing-sessions?mediaItemId={id}` | list by owning item |
| GET | `/v1/signing-sessions?status=Stranded` | list by status (ops) |

Spec hazards per CLAUDE.md:

- Initiate route **mints `sessionId` server-side** (not caller-supplied) — see [`document-signing.md § Webhook Callbacks Resolve the Tenant by Client Reference`](../../../../docs/adrs/document-signing.md#webhook-callbacks-resolve-the-tenant-by-client-reference). Caller-picked id would open a cross-tenant existence oracle on the unauthenticated webhook route.
- Webhook route is **unauthenticated**; HMAC check before tenant resolution; tenant lookup via `media-signing-envelope-lookup` on `SigningSessionId`.
- `reconcile` route invokes `ForceUnlinkSigningSessionCommand`; refuses `SigningSessionNotStranded 422` (MM-154).

## What the spec requires

- `InitiateSigningSessionEndpoint` at `POST /v1/media-items/{mediaItemId}/signing-sessions` → `InitiateSigningSessionCommand`; mints new `SigningSessionId` server-side (UUID v7 on server). Refuses `MediaItemNotCheckedOutByCaller 422`, `SigningCapabilityNotEnabled 422`, `InvalidSignerList 422`, `SigningSessionInProgress 409` (MM-154).
- `CancelSigningSessionEndpoint` at `POST /{sessionId}/cancel` → `CancelSigningSessionCommand`; refuses `SigningSessionNotCancellable 422`.
- `ReconcileSigningSessionEndpoint` at `POST /{sessionId}/reconcile` → `ForceUnlinkSigningSessionCommand`; refuses `SigningSessionNotStranded 422`.
- `EraseSigningSessionPersonalDataEndpoint` at `POST /{sessionId}/erase-personal-data` — named `If-Match` exception.
- `SecuredSigningWebhookEndpoint` at `POST /v1/integrations/secured-signing/webhooks` — unauthenticated route; HMAC middleware verifies signature → `HmacSignatureInvalid 401` on mismatch (MM-154); tenant resolved via `media-signing-envelope-lookup`; always returns `200 OK` to adapter (even on `SigningSessionLookupNotFound` — logs operator alert).
- 3 GET endpoints — detail + list-by-item + list-by-status. All driven by read-model.

## Wire-visibility

- Additive — 8 new routes.
- Server-side id minting is spec-mandated security boundary (prevents cross-tenant oracle on unauth webhook).

## Scope boundary

- Endpoint layer only.
- Commands + aggregate → DocumentSigningSession × write-model.
- Read-model → DocumentSigningSession × read-model.
- Error codes → MM-154.
- HMAC middleware + webhook unauth-route wiring → DocumentSigning × middleware (future cell).
- MediaItem's `POST /items/{itemId}/signing-session/force-unlink` is subsumed by `/signing-sessions/{sessionId}/reconcile` (MM-120 scope: verify no non-spec duplicate route lives on MediaItem).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-115 (plan MM-155). DocumentSigningSession × write-model + read-model must ship first. MM-154 (error codes) in flight.

## Phase 0 — Scope confirmation

- [ ] DocumentSigningSession × write-model shipped
- [ ] DocumentSigningSession × read-model shipped
- [ ] MM-154 constants reachable
- [ ] `media-signing-envelope-lookup` lookup table + reader available (per DocumentSigning × read-model)

## Phase 1 — Write-side endpoints (5)

- [ ] `InitiateSigningSessionEndpoint` at `POST /v1/media-items/{mediaItemId}/signing-sessions` — mints `SigningSessionId` server-side
- [ ] `CancelSigningSessionEndpoint` at `POST /{sessionId}/cancel`
- [ ] `ReconcileSigningSessionEndpoint` at `POST /{sessionId}/reconcile`
- [ ] `EraseSigningSessionPersonalDataEndpoint` at `POST /{sessionId}/erase-personal-data` (If-Match exempt)
- [ ] `SecuredSigningWebhookEndpoint` at `POST /v1/integrations/secured-signing/webhooks` (unauthenticated; HMAC-guarded)

## Phase 2 — Read-side endpoints (3)

- [ ] `GetSigningSessionEndpoint` at `GET /{sessionId}`
- [ ] `ListSigningSessionsByMediaItemEndpoint` at `GET /?mediaItemId=`
- [ ] `ListSigningSessionsByStatusEndpoint` at `GET /?status=`

## Phase 3 — Tests

- [ ] Integration per route: happy path + guard precedence
- [ ] Integration: initiate response echoes server-minted `sessionId` (caller-supplied id ignored or refused)
- [ ] Integration: webhook with valid HMAC → 200 + session state advanced; mismatch → 401 `HmacSignatureInvalid`; lookup miss → 200 + logged (adapter contract)
- [ ] Integration: reconcile on non-stranded → `422 SigningSessionNotStranded`
- [ ] Integration: erase-personal-data without `If-Match` → 2xx (exempt)

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry — API wire additive
- [ ] Release-notes line

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-155 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-115 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell DocumentSigningSession × http-routes; 8 missing routes incl. server-side-mint SigningSessionId + unauthenticated HMAC-guarded webhook + erase-personal-data If-Match exemption)
