---
id: MM-152
type: plan
project: magiq-media
workstream: WS-112-registration-write-model
repo: magiq-media
tags: [magiq-media, registration, write-model, dispatched, receipt, revoked, overdue, personal-data-erased, snapshot]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'MM-148, WS-57, WS-28'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell Registration × write-model
---

# WS-112 — Registration write-model: 6 new events + commands + snapshot bump

**Target repo:** `magiq-media`
**Depends on:** MM-148, WS-57, WS-28

## Problem

Spec names 16 Registration domain events. Code emits 10 unique (plus `RegistrationInitiated` v2 alias `RegistrationSubmissionRecorded`).

Missing (6):

| event | emitting command | integration event |
|---|---|---|
| `RegistrationDispatched` (v2) | `DispatchRegistrationCommand` (adapter callback, `SystemActorRequired`) | — (internal; adapter-only) |
| `RegistrationReceiptAcknowledged` | `RecordRegistrationReceiptCommand` (adapter callback) | — (internal) |
| `RegistrationRevoked` | `RevokeRegistrationCommand` | `media.registration.revoked` (MM-149) |
| `RegistrationReferenceCorrected` | `CorrectRegistrationReferenceCommand` | `media.registration.reference-corrected` (MM-149) |
| `RegistrationResponseOverdue` | `MaintenanceScanner` overdue pass (consumes `RegistrationByStatusIndex` GSI MM-151) | — (scanner-driven; refuses on terminal status) |
| `RegistrationPersonalDataErased` | `EraseRegistrationPersonalDataCommand` (`If-Match`-exempt per MM-150) | — (internal) |

Missing commands (5 user-facing + 1 scanner):

- `DispatchRegistrationCommand` (adapter)
- `RecordRegistrationReceiptCommand` (adapter)
- `RevokeRegistrationCommand`
- `CorrectRegistrationReferenceCommand`
- `MarkRegistrationResponseOverdueCommand` (scanner-dispatched; System actor)
- `EraseRegistrationPersonalDataCommand`

Supporting work:

- `RegistrationStatus` ordinals pinned explicitly (`Initiated=1`, `Submitted=2`, `Confirmed=3`, `Rejected=4`, `Cancelled=5`, `Revoked=6` — add Revoked).
- `RegistrationInitiated@2` + `RegistrationDispatched@2` upcasters per WS-28; alias `RegistrationSubmissionRecorded` registered on `RegistrationInitiated` via `IDomainEventRegistry`.
- `RegistrationSnapshot` revision bump per WS-57 — new `Revoked` state slot + `OverdueMarkedAt?` + `PersonalDataErasedAt?` + `ReferenceCorrections[]` history vector.
- `StatusChangedAt` state slot (populated on every status transition) consumed by MM-151's `RegistrationByStatusIndex` GSI.

## What the spec requires

- `RegistrationDispatched { TenantId, RegistrationId, DispatchedAt, DispatchedBy, AuthorityReference? }` — adapter callback marks transition Initiated → Dispatched; refuses non-Initiated status.
- `RegistrationReceiptAcknowledged { TenantId, RegistrationId, Receipt, AcknowledgedAt, AcknowledgedBy }` — adapter callback records authority receipt; refuses non-Dispatched.
- `RegistrationRevoked { TenantId, RegistrationId, RevokedAt, RevokedBy, Reason? }` — refuses non-Confirmed with `InvalidStatusTransition` (MM-148); emits integration event (MM-149).
- `RegistrationReferenceCorrected { TenantId, RegistrationId, OldReference, NewReference, CorrectedAt, CorrectedBy, Reason? }` — refuses when `OldReference == NewReference`; integration event (MM-149).
- `RegistrationResponseOverdue { TenantId, RegistrationId, DetectedAt }` — scanner-driven; refuses on terminal status (Confirmed/Rejected/Cancelled/Revoked).
- `RegistrationPersonalDataErased { TenantId, RegistrationId, ErasedAt, ErasedBy, Reason }` — anonymizes PII fields; `Reason` required.

## Scope boundary

- Aggregate + 6 commands + 6 handlers + 6 domain events + value-object additions + snapshot bump.
- Error codes → MM-148.
- Integration events → MM-149 (revoked + reference-corrected only).
- HTTP endpoints → MM-150.
- Read-model GSI + Status wire format → MM-151.
- `RegistrationInitiated@2` + `RegistrationDispatched@2` upcasters → WS-28 (coordinate).
- No wire — SNS captured by MM-149; HTTP by MM-150.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-112 (plan MM-152). MM-148 + WS-57 + WS-28 must be reachable. Siblings MM-149/150/151 land after this write-model core (SNS mapper + routes + read-model consume its domain events + commands).

## Phase 0 — Scope confirmation

- [ ] MM-148 constants reachable
- [ ] WS-57 snapshot revision mechanism available
- [ ] WS-28 upcaster framework available

## Phase 1 — Status enum

- [ ] `RegistrationStatus` ordinals pinned (`Initiated=1`, `Submitted=2`, `Confirmed=3`, `Rejected=4`, `Cancelled=5`, `Revoked=6`)

## Phase 2 — Domain events

- [ ] `RegistrationDispatched` (v2 upcaster per WS-28)
- [ ] `RegistrationReceiptAcknowledged`
- [ ] `RegistrationRevoked`
- [ ] `RegistrationReferenceCorrected`
- [ ] `RegistrationResponseOverdue`
- [ ] `RegistrationPersonalDataErased`
- [ ] `RegistrationInitiated@2` upcaster + alias `RegistrationSubmissionRecorded` registered

## Phase 3 — Aggregate state + methods

- [ ] `Registration.Revoked` state slot
- [ ] `Registration.OverdueMarkedAt: DateTime?`
- [ ] `Registration.PersonalDataErasedAt: DateTime?`
- [ ] `Registration.ReferenceCorrections[]` history vector
- [ ] `Registration.StatusChangedAt: DateTime` (populated on every status transition; feeds MM-151 GSI)
- [ ] `Registration.Dispatch(dispatchedBy, authorityReference?)` guard: status == Initiated
- [ ] `Registration.AcknowledgeReceipt(receipt, acknowledgedBy)` guard: status == Dispatched
- [ ] `Registration.Revoke(revokedBy, reason?)` guard: status == Confirmed
- [ ] `Registration.CorrectReference(newReference, correctedBy, reason?)` guard: current reference non-null, `oldReference != newReference`
- [ ] `Registration.MarkResponseOverdue()` guard: non-terminal status
- [ ] `Registration.ErasePersonalData(reason)` anonymizes PII members

## Phase 4 — Commands + handlers (6)

- [ ] `DispatchRegistrationCommand` + handler (System actor)
- [ ] `RecordRegistrationReceiptCommand` + handler (System actor)
- [ ] `RevokeRegistrationCommand` + handler
- [ ] `CorrectRegistrationReferenceCommand` + handler
- [ ] `MarkRegistrationResponseOverdueCommand` + handler (scanner-dispatched; System actor)
- [ ] `EraseRegistrationPersonalDataCommand` + handler

## Phase 5 — Snapshot revision

- [ ] `RegistrationSnapshot [Snapshot(Revision = 2)]` carries new state slots
- [ ] Stored revision-1 snapshots discarded + rebuilt (WS-57 mechanism)

## Phase 6 — Tests

- [ ] Unit: each aggregate method — happy path + guard precedence
- [ ] Unit: `CorrectReference` refuses no-op (same reference)
- [ ] Unit: `ErasePersonalData` wipes PII while retaining audit trail (`CorrectedBy`, `AcknowledgedBy`, etc. keep actor id for compliance)
- [ ] Integration: `Revoke` → emits `media.registration.revoked` (MM-149)
- [ ] Integration: `CorrectReference` → emits `media.registration.reference-corrected` (MM-149)

## Phase 7 — Communicate change

- [ ] No `breaking-changes.md` entry — wire captured by MM-149 (SNS) + MM-150 (HTTP)

## Phase 8 — Ship

- [ ] PR to `develop`

## Phase 9 — Close

- [ ] CLAUDE.md § KDPW: bullet removed (write-model lifecycle gaps)
- [ ] INTEGRATION-BACKLOG.md: MM-152 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-112 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell Registration × write-model; 6 missing events + commands + state slots + snapshot bump; depends on MM-148/149/150/151 + WS-57 + WS-28)
