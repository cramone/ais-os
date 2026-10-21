---
id: MM-158
type: plan
project: magiq-media
workstream: WS-118-documentsigning-middleware-permissions-hmac-preconditions
repo: magiq-media
tags: [magiq-media, documentsigning, middleware, permission, if-match, etag, hmac, webhook, envelope-lookup, resource-predicate]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-100 (SDK errorCode slot), MM-154 (DocumentSigning error codes), MM-155 (routes), MM-156 (read-model incl. envelope-lookup + webhook-dedup), MM-157 (write-model), MM-049 (VersionMismatch 412)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell DocumentSigningSession × middleware
---

# WS-118 — DocumentSigningSession middleware: permissions + resource-predicate + If-Match + ETag + HMAC webhook + envelope-lookup tenant resolution

**Target repo:** `magiq-media`
**Depends on:** MM-100, MM-154, MM-155, MM-156, MM-157, MM-049

## Problem

Spec [`api-conventions.md § Refusal precedence`](../../../../docs/spec/shared/api-conventions.md#refusal-precedence--state-before-the-resource-predicate) + [`api-permissions.md`](../../../../docs/spec/shared/api-permissions.md) + [`document-signing.md` ADR](../../../../docs/adrs/document-signing.md#webhook-callbacks-resolve-the-tenant-by-client-reference): authenticated DocumentSigning routes carry standard middleware (permission + resource-predicate + If-Match + ETag); the SecuredSigning webhook route is **unauthenticated** with a bespoke HMAC + envelope-lookup pipeline.

Authenticated routes (`/signing-sessions/*`):

- Permission check at edge → `403 PermissionDenied`.
- Resource-predicate guard: caller matches `MediaItem.ReviewSession.InitiatedBy` or `.All` widening. **`InitiatedBy` is provenance, not auth** — spec says the owning MediaItem's edit-session editor is the real predicate (see CLAUDE.md § Auth & multi-tenancy). Verify with spec at implementation time.
- Preconditioned routes read `If-Match` → `428`/`412`/`400`.
- `erase-personal-data` named `If-Match` exception.
- 2xx carry `ETag: W/"<AggregateVersion>"`.

Webhook route (`POST /integrations/secured-signing/webhooks`):

- Unauthenticated — no JWT, no `IPermissionService`.
- `WebhookHmacMiddleware` reads `X-SecuredSigning-Signature` header → verifies HMAC-SHA256 over raw body with shared secret → refuses `401 HmacSignatureInvalid` (MM-154).
- After HMAC pass: parse body → extract `SigningSessionId` + `ProviderEventId`.
- Dedup middleware consults `IWebhookDedupStore.TryRecordAsync(tenantId, providerEventId)` → first write wins; duplicate returns `200 OK` to adapter (idempotent replay).
- Tenant resolution: `ISigningEnvelopeLookupReader.ResolveTenantAsync(sessionId)` → sets `IExecutionContext.TenantId` + `Actor { ActorType = System }`.
- Lookup miss → log operator alert; return `200 OK` to adapter (prevents retry storms per `document-signing.md` ADR).
- Handler load aggregate under resolved tenant.

Code: zero `IPermissionService`/`If-Match`/`ETag`/`Hmac` sites in `DocumentSigning` module.

## Scope

| Concern | Spec | Code |
|---|---|---|
| Permission check at edge | `IPermissionService.IsGranted(Permission, claims)` → `403 PermissionDenied` | not called |
| Resource-predicate guard | caller == owning MediaItem's edit-session editor or `.All` | handler layer absent |
| `If-Match` on preconditioned routes | cancel, reconcile | not read |
| `428 PreconditionRequired` when `If-Match` absent | — | — |
| `412 VersionMismatch` on mismatch (MM-049) | — | — |
| `ETag: W/"<AggregateVersion>"` on 2xx | not emitted | — |
| `erase-personal-data` `If-Match` exempt | named exception | — |
| Webhook HMAC-SHA256 verify | `X-SecuredSigning-Signature` over raw body with shared secret → `401 HmacSignatureInvalid` | not implemented |
| Webhook dedup | `media-signing-webhook-events` conditional write | not implemented |
| Webhook tenant resolution | `media-signing-envelope-lookup` by `SigningSessionId` | not implemented |
| Webhook always-200 | Lookup miss + duplicate = 200 to adapter | — |

## What the spec requires

- Authenticated endpoints declare `[Permission(SigningSessionPermissions.<Verb>)]`.
- `/erase-personal-data` is the named `If-Match` exception.
- Webhook route **bypasses** JWT auth; wires `WebhookHmacMiddleware` → `WebhookDedupMiddleware` → `WebhookTenantResolverMiddleware` → handler.
- HMAC algorithm: HMAC-SHA256 over raw request body; secret from host config (`SecuredSigning:WebhookSecret`).
- Dedup TTL defines window (e.g. 7 days per spec — audit).
- Envelope-lookup table is tenant-exempt per MM-156; tenant resolver sets context from lookup row's `TenantId` attribute.

## Wire-visibility

- Breaking — permission + If-Match + 412 flip + ETag; HMAC enforcement + dedup are first-ever wire behaviour for webhook endpoint.

## Scope boundary

- Endpoint + middleware wiring.
- `SigningSessionPermissions` constants = this plan's scope.
- SDK `IPermissionService` = MM-100.
- Error codes incl. `HmacSignatureInvalid` + `SigningSessionLookupNotFound` = MM-154.
- Envelope-lookup + dedup tables + readers = MM-156.
- Aggregate + handlers = MM-157.
- SecuredSigning adapter integration (outbound initiate call) = MM-157 scope.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-118 (plan MM-158). MM-100/154/155/156/157/049 must ship first. HMAC algorithm = HMAC-SHA256 over raw body with shared secret.

## Phase 0 — Scope confirmation

- [ ] MM-100 shipped
- [ ] MM-154 constants reachable (incl. `HmacSignatureInvalid`, `SigningSessionLookupNotFound`)
- [ ] MM-155 routes shipped (incl. webhook endpoint)
- [ ] MM-156 read-model shipped (envelope-lookup + webhook-dedup tables + reader interfaces)
- [ ] MM-157 write-model shipped
- [ ] MM-049 `VersionMismatch` 412 shipped

## Phase 1 — Permission constants

- [ ] `SigningSessionPermissions` constants — one slug per verb (`InitiateSigningSession`, `CancelSigningSession`, `ReconcileSigningSession`, `EraseSigningSessionPersonalData`, `ReadSigningSession`)

## Phase 2 — Authenticated-endpoint wiring

- [ ] 4 write-side + 3 read-side authenticated endpoints declare `[Permission(SigningSessionPermissions.<Verb>)]`
- [ ] FastEndpoints config calls `IPermissionService.IsGranted`; refuses `403 PermissionDenied`
- [ ] Resource-predicate guard: owning MediaItem's edit-session editor (via `IMediaItemQueryService`) + `.All` widening
- [ ] Preconditioned routes (cancel, reconcile) read `If-Match` → `428`/`412`/`400`
- [ ] `erase-personal-data` exempt — no `If-Match` enforcement
- [ ] 2xx responses carry `ETag: W/"<AggregateVersion>"`
- [ ] `GET /{sessionId}` emits `ETag` for conditional reads

## Phase 3 — Webhook pipeline (unauthenticated)

- [ ] `WebhookHmacMiddleware` — reads `X-SecuredSigning-Signature`; computes HMAC-SHA256 over raw body with shared secret; refuses `401 HmacSignatureInvalid` on mismatch; **runs before any body parse / aggregate load**
- [ ] `WebhookDedupMiddleware` — after HMAC pass; parses `ProviderEventId`; calls `IWebhookDedupStore.TryRecordAsync(tenantId, providerEventId)`; duplicate → returns `200 OK` without handler invocation
- [ ] `WebhookTenantResolverMiddleware` — after dedup; reads `SigningSessionId` from body; calls `ISigningEnvelopeLookupReader.ResolveTenantAsync(sessionId)`; sets `IExecutionContext.TenantId` + `Actor { ActorType = System, Roles = ["SecuredSigningAdapter"] }`; lookup miss → log + return `200 OK` without handler invocation (prevents adapter retry storms per `document-signing.md`)
- [ ] Webhook endpoint bypasses JWT auth (`AllowAnonymous`-equivalent in FastEndpoints)
- [ ] Shared secret config bound to `SecuredSigning:WebhookSecret`

## Phase 4 — Tests

- [ ] Integration per authenticated route: permission refusal → `403 PermissionDenied`
- [ ] Integration: `If-Match`-absent on cancel/reconcile → `428`
- [ ] Integration: `If-Match` mismatch → `412 VersionMismatch`
- [ ] Integration: `erase-personal-data` without `If-Match` → 2xx (exempt)
- [ ] Integration: webhook with valid HMAC → 200; mismatch → 401 `HmacSignatureInvalid`
- [ ] Integration: webhook duplicate `ProviderEventId` → 200 (idempotent)
- [ ] Integration: webhook with unknown `SigningSessionId` → 200 + operator log (no retry)
- [ ] Security: webhook replay with modified body → HMAC mismatch → 401

## Phase 5 — Communicate change

- [ ] Breaking-changes.md entry — API wire breaking: permission + 428/412 + ETag + HMAC webhook contract

## Phase 6 — Ship

- [ ] PR to `develop`

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-158 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-118 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell DocumentSigningSession × middleware; mirror of established pattern + 3-stage webhook middleware pipeline [HMAC → dedup → envelope-lookup tenant resolution] per `document-signing.md` ADR; HMAC-SHA256 over raw body; always-200 to adapter on lookup miss or duplicate)
