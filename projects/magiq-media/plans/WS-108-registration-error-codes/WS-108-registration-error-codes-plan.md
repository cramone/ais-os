---
id: MM-148
type: plan
project: magiq-media
workstream: WS-108-registration-error-codes
repo: magiq-media
tags: [magiq-media, registration, error-codes, problemdetails]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-100 (SDK errorCode slot), MM-032 (duplicate-id exception)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Registration × error-codes
---

# WS-108 — Registration error codes: 21 `RegistrationErrorCodes`

**Target repo:** `magiq-media`
**Depends on:** MM-100, MM-032

## Problem

Spec [`error-catalog.md § Registration`](../../../../docs/spec/shared/error-catalog.md) names 21 codes. Registration aggregate exists; handlers emit `DomainError.InvalidOperation(prose)` with no code; `RegistrationErrorCodes` constants class absent.

Spec codes (21):

| code | status | condition |
|---|---|---|
| `RegistrationNotFound` | 404 | Absent |
| `RegistrationAlreadyExists` | 409 | Duplicate caller `registrationId` (fresh id / treat as success) |
| `AmendmentNotFound` | 404 | Amendment id absent |
| `MediaItemNotFound` | 404 | Referenced item absent via registration-item-ref |
| `NotResourceOwner` | 403 | Caller not officer, no `.All` |
| `SystemActorRequired` | 403 | System route called by User |
| `InvalidStatusTransition` | 422 | Invalid from current status; carries `currentStatus` ext |
| `RegistrationConfirmed` | 422 | Cancel/attach on Confirmed |
| `RegistrationAlreadyCancelled` | 422 | Second cancel |
| `AmendmentNotPending` | 422 | Approve/reject on decided amendment |
| `ItemAlreadyAttached` | 409 | Item already attached |
| `DuplicatePendingAmendment` | 409 | Pending amendment for item exists |
| `NoDocumentsAttached` | 422 | Submit with no supporting docs |
| `ReferenceRequired` | 422 | Confirm/correct with empty reference |
| `RejectionReasonRequired` | 422 | Reject empty reason |
| `RegistrationAuthorityRequired` | 422 | Initiate blank authority |
| `AmendmentNotesTooLong` | 422 | `notes` > 1,000 |
| `MediaItemNotPublished` | 422 | Referenced item has no live published version |
| `RegistrationCapabilityNotEnabled` | 422 | Profile lacks `Registration` capability |
| `InvalidRegistrationItem` | 422 | Attach: profile is `Processing` |
| `SearchTermRequired` | 400 | `/search` with empty `q` |

## What the spec requires

- `RegistrationErrorCodes` static class with 21 `const string` entries.
- Every refusal path in `Registration` aggregate + handlers returns `DomainError.<Verb>(RegistrationErrorCodes.<Code>, prose)`.
- `InvalidStatusTransition` carries `currentStatus` extension payload.
- `AmendmentNotesTooLong` carries `maxLength` + `actualLength` extension payload.
- SDK slot (MM-100) carries the code to RFC 9457 ProblemDetails `errorCode` root.

## Wire-visibility

- Additive — new `errorCode` payload on 400/403/404/409/422 refusals from Registration routes.

## Scope boundary

- Constants class + handler-site uptake.
- Registration endpoints wire error-code emission.
- `MediaItemNotFound 404` emitted by Registration routes consuming item refs — code lives here but reads MediaItem reflection via `IExecutionContext` or registration-item-ref.
- `SystemActorRequired 403` applies to callback routes (adapter integration) — needs role-based auth per CLAUDE.md.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-108 (plan MM-148). MM-100 (SDK slot) + MM-032 must ship first.

## Phase 0 — Scope confirmation

- [ ] MM-100 shipped
- [ ] MM-032 shipped

## Phase 1 — Constants + extension payloads

- [ ] `RegistrationErrorCodes` static class with 21 `const string` entries
- [ ] `InvalidStatusTransition` carries `currentStatus` extension payload
- [ ] `AmendmentNotesTooLong` carries `maxLength` + `actualLength` extension payload

## Phase 2 — Handler-site uptake

- [ ] `Registration` aggregate refusals use `DomainError.<Verb>(RegistrationErrorCodes.<Code>, prose)`
- [ ] Amendment-flow commands emit `AmendmentNotPending`/`DuplicatePendingAmendment` as appropriate
- [ ] Submit flow emits `NoDocumentsAttached` on empty document list
- [ ] Attach flow emits `ItemAlreadyAttached`/`RegistrationCapabilityNotEnabled`/`InvalidRegistrationItem`/`MediaItemNotPublished` precondition set

## Phase 3 — Tests

- [ ] Unit: each code → ProblemDetails emits root-level `errorCode`
- [ ] Integration: `InvalidStatusTransition` → body carries `currentStatus`
- [ ] Integration: `AmendmentNotesTooLong` → body carries length fields
- [ ] Integration: `SystemActorRequired` on callback route called by `User` → 403 with code

## Phase 4 — Communicate change

- [ ] Breaking-changes.md entry — API wire additive

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-148 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-108 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell Registration × error-codes; 21 codes — identity + state + amendment + content + capability + search; mirror of established pattern)
