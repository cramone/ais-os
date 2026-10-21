---
id: MM-160
type: plan
project: magiq-media
workstream: WS-121-dsr-aggregate-and-routes
repo: magiq-media
tags: [magiq-media, dsr, privacy, cross-cutting, aggregate-build, http-routes]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-18
depends-on: MM-100, MM-159
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Cross-cutting×http-routes
---

# WS-121 — `DataSubjectRequest` aggregate + 6 DSR routes

**Target repo:** `magiq-media`
**Spec source:** [`privacy-and-pii.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/privacy-and-pii.md)
**Depends on:** MM-100 (SDK `errorCode` slot), MM-159 (DSR error-code constants ship forward-compat)

## Problem

Spec [`privacy-and-pii.md § DSR endpoints`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/privacy-and-pii.md#dsr-endpoints) names 5 write + 1 read DSR routes with `Tenant.DSR` auth predicate. Each operation is an event-sourced `DataSubjectRequest` aggregate.

Code today:
- Zero `/v1/dsr/*` endpoint files
- Zero `DataSubjectRequest` aggregate / handler / command / event files
- Zero `Tenant.DSR` permission references
- Zero `subjectIdentifierScheme` / `identifierScheme` references
- 3 error-code constants scaffolded in MM-159's `CrossCuttingErrorCodes` (dead until this plan ships)

## Scope

### Routes (6)

| Verb | Path | Body | Response |
|---|---|---|---|
| POST | `/v1/dsr/access` | `{ subjectIdentifier, identifierScheme, scope? }` | `202 Accepted` · `Location: /v1/dsr/access/{requestId}` |
| POST | `/v1/dsr/correction` | `{ subjectIdentifier, identifierScheme, corrections: [{ aggregateId, field, newValue }] }` | `202 Accepted` · `Location: /v1/dsr/correction/{requestId}` |
| POST | `/v1/dsr/erasure` | `{ subjectIdentifier, identifierScheme, scope? }` | `202 Accepted` · `Location: /v1/dsr/erasure/{requestId}` |
| POST | `/v1/dsr/portability` | `{ subjectIdentifier, identifierScheme, format: json \| xml \| csv }` | `202 Accepted` · `Location: /v1/dsr/portability/{requestId}` |
| POST | `/v1/dsr/objection` | `{ subjectIdentifier, identifierScheme, scope: processing-type }` | `201 Created` · body: `{ objectionId }` |
| GET | `/v1/dsr/{right}/{requestId}` | — | `200 OK` · current state + aggregated response + discharge outcome |

### Aggregate

New module `src/modules/Dsr/` with Domain + Contracts + WriteModel + WriteModel.Endpoints + WriteModel.Infrastructure + ReadModel + ReadModel.Endpoints + ReadModel.Infrastructure projects.

- `DataSubjectRequest` aggregate (`EventSourced<DataSubjectRequest, DataSubjectRequestId>`, `ITenantScoped`, `[AggregateType("media.dsr")]`)
- Events: `DsrOpened`, `DsrDischarged`, `DsrPartiallyFulfilled`, `DsrRejected`, `DsrOverdue`, per-right subtype events (`DsrErasureItemRefused`, `DsrAccessPackageAssembled`, `DsrCorrectionApplied`, `DsrPortabilityExported`, `DsrObjectionRecorded`)
- State: `OpenedAt`, `DischargedAt?`, `SubjectIdentifier`, `IdentifierScheme`, `Right`, `Scope`, `Result`, `RefusalReason?`
- `DsrScheduleRetirementScanner` → `MaintenanceScanner` pass driven by `Tenant:DSR:StatutoryWindow` setting; emits `DsrOverdue` + alarm when `OpenedAt + StatutoryWindow < now` and `DischargedAt is null`

### Authorization

- Edge: `Tenant.DSR` permission (held by tenant admin + DPO roles)
- Resource predicate: subject's records resolve inside the authenticated `TenantId`; cross-tenant scope refused `403 DsrScopeOutsideTenant`
- Erasure under legal hold: `422 DsrAllTargetsOnLegalHold` with hold reason in body
- Unknown identifier: `404 SubjectIdentifierNotKnown`

### Read model

- `media-dsr-requests` (summary; one row per request)
- `media-dsr-request` (detail)
- `media-dsr-overdue` projection (per [`privacy-and-pii.md § Statutory window`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/privacy-and-pii.md))

## Phase 0 — Scope confirmation
- [ ] Read `privacy-and-pii.md` + `multi-tenancy-and-auth.md` DSR sections end-to-end
- [ ] Confirm `Tenant:DSR:StatutoryWindow` tenant-setting + `Tenant.DSR` permission constants live in `magiq-auth`
- [ ] Confirm `subjectIdentifierScheme` catalog (expected: `email`, `nationalId`, `clientReference`, …) is a tenant-config list

## Phase 1 — DSR module scaffold
- [ ] `src/modules/Dsr/` folder tree + csproj + csproj refs
- [ ] `DataSubjectRequestId` strongly-typed value-object (UUID v7, caller-supplied on create)
- [ ] Aggregate class + events + commands
- [ ] `IPermissionService` edge check `Tenant.DSR`
- [ ] `IExecutionContext.TenantId` scope check → `403 DsrScopeOutsideTenant` on cross-tenant

## Phase 2 — Routes + endpoints
- [ ] 5 POST write endpoints (`FastEndpoints`); 202/201 responses
- [ ] 1 GET status endpoint; aggregated response shape per right
- [ ] `Idempotency-Key` required (per `api-conventions.md`)
- [ ] `errorCode` emission uses `CrossCuttingErrorCodes.SubjectIdentifierNotKnown` / `DsrScopeOutsideTenant` / `DsrAllTargetsOnLegalHold` (ship via MM-159)

## Phase 3 — Erasure orchestration
- [ ] Erasure dispatches `ErasePersonalData` commands against affected aggregates (MediaItem, Registration, Asset, DocumentSigningSession)
- [ ] Legal-hold gate: aggregate refuses `ErasureRefusedUnderLegalHold 422`; DSR partially-fulfils per-item or fully-fulfils with refusal list
- [ ] Discharge → `DsrDischarged` with aggregate `Result: fulfilled | partially-fulfilled | refused`

## Phase 4 — Overdue + alarms
- [ ] `MaintenanceScanner` DSR-overdue pass
- [ ] Overdue alarm (CloudWatch → `media-alarms-pager`); dashboard row on `media-projection-lag` or own `media-dsr` dashboard
- [ ] Integration event `media.dsr.overdue` optional for tenant-side consumers

## Phase 5 — Audit + compliance
- [ ] DSR aggregate stream = immutable audit per `audit-trail.md`
- [ ] Compliance mapping file `docs/compliance/privacy-gdpr-ccpa.md` cites spec + ADR anchors; `compliance_coverage.py` validates

## Breaking change

**API wire — additive.** Six new endpoints land; existing clients unaffected. Breaking-changes.md entry under § Expected — API wire — additive. Spec section cite = `privacy-and-pii.md § DSR endpoints`.

## Session log

| Date | Progress |
|---|---|
| 2026-10-18 | Drafted from alignment-sweep Cross-cutting × http-routes cell |
