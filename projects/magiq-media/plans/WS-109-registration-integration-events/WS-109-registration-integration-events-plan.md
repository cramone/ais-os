---
id: MM-149
type: plan
project: magiq-media
workstream: WS-109-registration-integration-events
repo: magiq-media
tags: [magiq-media, registration, integration-events, revoked, reference-corrected, mapper, compliance]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'Registration × write-model plan (RegistrationRevoked + RegistrationReferenceCorrected domain events + commands)'
breaking-change: Process wire — additive
source: alignment-sweep-2026-10-15 cell Registration × integration-events
---

# WS-109 — Registration integration events: 2 missing types + Compliance consumers

**Target repo:** `magiq-media`
**Depends on:** Registration × write-model plan

## Problem

Spec names 8 Registration integration event types. Code publishes 6.

Covered (6):

| spec type | code contract |
|---|---|
| `media.registration.initiated` | `RegistrationInitiatedIntegrationEvent` ✓ |
| `media.registration.submitted` | `RegistrationSubmittedIntegrationEvent` ✓ |
| `media.registration.resubmitted` | `RegistrationResubmittedIntegrationEvent` ✓ |
| `media.registration.confirmed` | `RegistrationConfirmedIntegrationEvent` ✓ |
| `media.registration.rejected` | `RegistrationRejectedIntegrationEvent` ✓ |
| `media.registration.cancelled` | `RegistrationCancelledIntegrationEvent` ✓ |

Missing (2):

| spec type | domain event | consumer |
|---|---|---|
| `media.registration.revoked` | `RegistrationRevoked` | Notifications; Compliance; Catalog (not live) |
| `media.registration.reference-corrected` | `RegistrationReferenceCorrected` | Compliance |

Underlying domain events absent in code (both built under Registration × write-model plan). `RegistrationDomainEventMapper` missing 2 `Map` overloads. CDK filter-policy entries absent for Compliance / Notifications / Catalog consumer queues.

## What the spec requires

- `RegistrationRevokedIntegrationEvent { TenantId, RegistrationId, RegistrationItemId, RevokedAt, RevokedBy, Reason? }` — Catalog flips `media-registration-item-ref` to not-live; Compliance records revocation.
- `RegistrationReferenceCorrectedIntegrationEvent { TenantId, RegistrationId, OldReference, NewReference, CorrectedAt, CorrectedBy, Reason? }` — Compliance records correction audit trail.
- `RegistrationDomainEventMapper` with 2 new `Map` overloads.
- CDK filter policies in `cdk-magiq-media` admit the 2 new `type` values to Compliance + Notifications + Catalog registration-item-ref consumer queues.

## Wire-visibility

- Additive — 2 new SNS types; existing filter policies ignore unknown types until CDK edits land.

## Scope boundary

- Contract records + mapper + CDK filter-policy edits.
- Domain events + aggregate commands → Registration × write-model.
- Catalog's `media-registration-item-ref` already consumes other Registration events; add revoked handler alongside.
- Error codes → MM-148.
- `RegistrationDispatched@2` upcaster (alias `RegistrationSubmissionRecorded`) → WS-28.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-109 (plan MM-149). Registration × write-model must ship first (RegistrationRevoked + RegistrationReferenceCorrected domain events).

## Phase 0 — Scope confirmation

- [ ] Registration × write-model shipped (both domain events)
- [ ] MM-148 constants reachable (for revoke/correct refusals)

## Phase 1 — Contract records

- [ ] `RegistrationRevokedIntegrationEvent` under `Registrations.Contracts/Events/`
- [ ] `RegistrationReferenceCorrectedIntegrationEvent`

## Phase 2 — Mapper

- [ ] `RegistrationDomainEventMapper.Map(RegistrationRevoked)` yields `RegistrationRevokedIntegrationEvent`
- [ ] `RegistrationDomainEventMapper.Map(RegistrationReferenceCorrected)` yields `RegistrationReferenceCorrectedIntegrationEvent`

## Phase 3 — CDK filter policies

- [ ] `cdk-magiq-media` admits `media.registration.revoked` to Catalog + Notifications + Compliance queues
- [ ] `cdk-magiq-media` admits `media.registration.reference-corrected` to Compliance queue
- [ ] `FilterPolicyScope: MessageBody` on `type`

## Phase 4 — Catalog consumer

- [ ] `media-registration-item-ref` consumer handles `media.registration.revoked` → flips entry not-live

## Phase 5 — Tests

- [ ] Integration: `RevokeRegistration` → outbox → SNS → body carries `type` + payload
- [ ] Integration: `CorrectRegistrationReference` → outbox → SNS → body carries new reference
- [ ] Integration: Catalog consumer flips registration-item-ref not-live on revoked

## Phase 6 — Communicate change

- [ ] Breaking-changes.md entry — Process wire additive

## Phase 7 — Ship

- [ ] PR to `develop` (magiq-media) + `spec/initial-alignment` (cdk-magiq-media)

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-149 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-109 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell Registration × integration-events; 2 missing types `revoked` + `reference-corrected`; depends on Registration × write-model)
