---
id: MM-154
type: plan
project: magiq-media
workstream: WS-114-documentsigning-error-codes
repo: magiq-media
tags: [magiq-media, documentsigning, signingsession, error-codes, hmac, webhook, problemdetails]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-100 (SDK errorCode slot), MM-032 (duplicate-id exception)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell DocumentSigningSession × error-codes
---

# WS-114 — DocumentSigningSession error codes: 9 `DocumentSigningErrorCodes`

**Target repo:** `magiq-media`
**Depends on:** MM-100, MM-032

> **Scope boundary — constants only.** Aggregate wholly unbuilt per CLAUDE.md modules table. This plan ships the `DocumentSigningErrorCodes` constants class standalone. Uptake splits across two sibling plans: aggregate refusal-site uptake (`MediaItemNotCheckedOutByCaller`, `SigningCapabilityNotEnabled`, `InvalidSignerList`, `SigningSessionNotCancellable`, `SigningSessionNotStranded`, `SignersNotAllCompleted`, `SigningSessionInProgress`) lands with MM-157 (DocumentSigningSession × write-model); HMAC webhook refusal path (`HmacSignatureInvalid 401` + non-wire `SigningSessionLookupNotFound` log) lands with MM-158 (DocumentSigning × middleware/HMAC pipeline).

## Problem

Spec [`error-catalog.md § DocumentSigning — DocumentSigningSession`](../../../../docs/spec/shared/error-catalog.md) names 9 codes. Per CLAUDE.md modules table: `DocumentSigningSession` is "specified, no aggregate class exists". `DocumentSigningErrorCodes` constants class absent; no handler emits a code.

Spec codes (9):

| code | status | condition |
|---|---|---|
| `MediaItemNotCheckedOutByCaller` | 422 | Initiate: item has no session or held by another |
| `SigningSessionInProgress` | 409/422 | 409 on initiate/link; 422 on archive/dispose |
| `SigningCapabilityNotEnabled` | 422 | Profile lacks `Capability.Signing` |
| `InvalidSignerList` | 422 | Zero signers or shared email |
| `SigningSessionNotCancellable` | 422 | Cancel on non-`Initiated`/`EnvelopeCreated` |
| `SigningSessionNotStranded` | 422 | ForceUnlink on non-Stranded |
| `SignersNotAllCompleted` | 422 | RecordSigningCompleted while signer Pending |
| `HmacSignatureInvalid` | 401 | Webhook HMAC mismatch |
| `SigningSessionLookupNotFound` | — | Webhook lookup miss (operator-only; non-wire by catalog) |

## What the spec requires

- `DocumentSigningErrorCodes` static class with 9 `const string` entries.
- Every refusal path returns `DomainError.<Verb>(DocumentSigningErrorCodes.<Code>, prose)`.
- `SigningSessionInProgress` carries dual status mapping — `409` on initiate/link routes, `422` on archive/dispose; endpoint context decides which.
- `SigningSessionNotCancellable` carries `currentStatus` extension payload.
- `HmacSignatureInvalid 401` emitted on webhook route (unauthenticated per [`document-signing.md`](../../../../docs/adrs/document-signing.md)); HMAC check runs before any aggregate load so no tenant leak.
- `SigningSessionLookupNotFound` is operator-facing (log/alert); not emitted on wire — webhook route returns 200 to adapter even on miss to prevent retry storms.

## Wire-visibility

- Additive — new `errorCode` payload on 401/409/422 refusals from forthcoming DocumentSigning routes + webhook callback.

## Scope boundary

- Constants class + handler-site uptake.
- Aggregate build + handlers + endpoints → DocumentSigningSession × write-model.
- `SigningSessionInProgress 422` on MediaItem archive/dispose routes → emitted from MediaItem (MM-118) consulting signing session state.
- HMAC verification middleware for webhook route → DocumentSigning × middleware (future cell).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-114 (plan MM-154). MM-100 + MM-032 + DocumentSigningSession × write-model must ship first.

## Phase 0 — Scope confirmation

- [ ] MM-100 shipped
- [ ] MM-032 shipped
- [ ] DocumentSigningSession × write-model in flight (aggregate + handlers)

## Phase 1 — Constants + extension payloads

- [ ] `DocumentSigningErrorCodes` static class with 9 `const string` entries
- [ ] `SigningSessionNotCancellable` carries `currentStatus` extension payload
- [ ] `SigningSessionInProgress` status-mapping policy — endpoint context picks 409 vs 422

## Phase 2 — Handler-site uptake

- [ ] Signing aggregate refusals use `DomainError.<Verb>(DocumentSigningErrorCodes.<Code>, prose)`
- [ ] Initiate flow emits `MediaItemNotCheckedOutByCaller`/`SigningCapabilityNotEnabled`/`InvalidSignerList`
- [ ] Lifecycle commands emit `SigningSessionNotCancellable`/`SigningSessionNotStranded`
- [ ] RecordSigningCompleted emits `SignersNotAllCompleted` when any signer status != Completed
- [ ] Webhook route emits `HmacSignatureInvalid 401` from HMAC middleware; logs `SigningSessionLookupNotFound` without wire emission

## Phase 3 — Tests

- [ ] Unit: each code → ProblemDetails emits root-level `errorCode`
- [ ] Integration: `SigningSessionInProgress` on initiate → 409; on archive → 422
- [ ] Integration: webhook HMAC mismatch → 401 with `HmacSignatureInvalid`; lookup miss logs + returns 200 (adapter contract)

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry — API wire additive

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-154 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-114 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell DocumentSigningSession × error-codes; aggregate wholly unbuilt; mirror of established error-code pattern + dual status mapping on SigningSessionInProgress + HMAC auth boundary code)
