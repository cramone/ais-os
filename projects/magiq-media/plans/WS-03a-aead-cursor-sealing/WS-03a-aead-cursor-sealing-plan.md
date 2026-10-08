---
id: MM-020
type: plan
project: magiq-media
workstream: WS-03a-aead-cursor-sealing
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, security, pagination, aead]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/security/F093-pagination-cursor-sealing.md and INDEX.md#WS-03; no separate review document.
---

# WS-03a — AEAD-sealed pagination cursors bound to (tenant, route, params, issue time)

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-038 (WS-03b — magiq-media QueryApi + OpenSearch wiring); pre-staging-gate security.

Delivers F093. Today pagination returns raw base64url of DynamoDB `LastEvaluatedKey` + unsigned OpenSearch `sort` array — forgeable, cross-tenant, leaks internal key material.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-03a (plan MM-020). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-03a-aead-cursor-sealing\WS-03a-aead-cursor-sealing-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\security\F093-pagination-cursor-sealing.md`.
>
> Deliver `IPaginationCursorSealer`: AEAD (AES-256-GCM or ChaCha20-Poly1305). Payload `{ tenantId, routeKey, paramsHash, issuedAt, continuation }`. Associated data: `tenantId || routeKey || paramsHash` (tampering fails unseal). Key provider: KMS/Secrets. Key rotation via `KeyId` in payload. 24h TTL (configurable).
>
> Pre-staging security — careful review. PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F093 § Required-shape, § Detection signals, § Security property
- [ ] Locate current pagination plumbing — `IPaginationCursor` / `PageToken` serializer
- [ ] Enumerate call sites in SDK (not magiq-media; deferred to WS-03b)

## Phase 1 — Sealing key management
- [ ] `IPaginationCursorSealer` abstraction
- [ ] AEAD impl: AES-256-GCM or ChaCha20-Poly1305
- [ ] Key provider: `IPaginationSealingKeyProvider` reading from KMS / Secrets Manager
- [ ] Key rotation: cursor carries `KeyId`; unseal tries current + N previous

## Phase 2 — Cursor shape + binding
- [ ] Payload: `{ tenantId, routeKey, paramsHash, issuedAt, continuation }`
- [ ] AEAD associated data: `tenantId || routeKey || paramsHash`
- [ ] Output: base64url(sealed-ciphertext || keyId || nonce)

## Phase 3 — Seal / unseal API
- [ ] `SealAsync(continuation, context, ct)` → opaque string
- [ ] `UnsealAsync<T>(token, expectedContext, ct)` → `Result<T, PaginationCursorError>`
- [ ] Errors: `Invalid`, `TenantMismatch`, `RouteMismatch`, `ParamsMismatch`, `Expired`

## Phase 4 — Expiry
- [ ] `CursorTtl` (default 24h)
- [ ] Unseal checks `now - issuedAt < CursorTtl` → `Expired`
- [ ] XML doc: clients may re-paginate from start on expiry

## Phase 5 — Tests
- [ ] Unit: seal/unseal round-trip
- [ ] Unit: tenant swap → `TenantMismatch`
- [ ] Unit: route swap → `RouteMismatch`
- [ ] Unit: params change → `ParamsMismatch`
- [ ] Unit: tampering first byte → `Invalid`
- [ ] Unit: TTL expiry → `Expired`
- [ ] Unit: key rotation — previous key still unseals

## Phase 6 — Package + ship
- [ ] Bump `Magiq.AspNetCore.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 7 — Close
- [ ] F093: `status: shipped (SDK portion)`
- [ ] security/INDEX.md: WS-03 split — `WS-03a shipped`, `WS-03b open`
- [ ] INTEGRATION-BACKLOG: MM-038 (WS-03b) ready

## Session log
- 2026-10-08: plan drafted
