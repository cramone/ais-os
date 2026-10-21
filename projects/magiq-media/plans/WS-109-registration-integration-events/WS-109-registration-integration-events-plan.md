---
id: MM-149
type: plan
project: magiq-media
workstream: WS-109-registration-integration-events
repo: magiq-media
tags: [magiq-media, registration, integration-events, revoked, reference-corrected, item-attached, mapper, compliance]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-152 (Registration × write-model — RegistrationRevoked + RegistrationReferenceCorrected + RegistrationItemAttached domain events + AttachMediaItem + ApproveAmendment aggregate methods + commands)'
breaking-change: Process wire — additive
source: alignment-sweep-2026-10-15 cell Registration × integration-events
---

# WS-109 — Registration integration events: 3 missing types + Compliance + Catalog consumers

**Target repo:** `magiq-media`
**Depends on:** MM-152 (Registration × write-model)

## Problem

Spec names 9 Registration integration event types. Code publishes 6.

Covered (6):

| spec type | code contract |
|---|---|
| `media.registration.initiated` | `RegistrationInitiatedIntegrationEvent` ✓ |
| `media.registration.submitted` | `RegistrationSubmittedIntegrationEvent` ✓ |
| `media.registration.resubmitted` | `RegistrationResubmittedIntegrationEvent` ✓ |
| `media.registration.confirmed` | `RegistrationConfirmedIntegrationEvent` ✓ |
| `media.registration.rejected` | `RegistrationRejectedIntegrationEvent` ✓ |
| `media.registration.cancelled` | `RegistrationCancelledIntegrationEvent` ✓ |

Missing (3):

| spec type | domain event | consumer |
|---|---|---|
| `media.registration.revoked` | `RegistrationRevoked` | Notifications; Compliance; Catalog (not live) |
| `media.registration.reference-corrected` | `RegistrationReferenceCorrected` | Compliance |
| `media.registration.item-attached` | `RegistrationItemAttached` (direct attach via `AttachMediaItem` + amendment-approved attach via `ApproveAmendment`) | Catalog (records attached document on item's `RegistrationRefs` with `Role = Document` + `ItemType` carried from the message — surfaced in Arnica review re-diff) |

Underlying domain events absent in code (all 3 built under MM-152). `RegistrationDomainEventMapper` missing 3 `Map` overloads. CDK filter-policy entries absent for Compliance / Notifications / Catalog consumer queues.

**Cross-aggregate implication of item-attached.** Spec `cross-aggregate-rules.md § rule 13`: document entries on `MediaItem.RegistrationRefs` are fed by `media.registration.item-attached`. Without this event, Catalog never records attached documents — only subject refs land via `.initiated` / `.resubmitted`. The Catalog consumer dispatches `AddRegistrationRefCommand` with `Role = Document` + `ItemType` carried from the message (vs `Role = Subject` for `.initiated`/`.resubmitted`).

## What the spec requires

- `RegistrationRevokedIntegrationEvent { TenantId, RegistrationId, RegistrationItemId, RevokedAt, RevokedBy, Reason? }` — Catalog flips `media-registration-item-ref` to not-live; Compliance records revocation.
- `RegistrationReferenceCorrectedIntegrationEvent { TenantId, RegistrationId, OldReference, NewReference, CorrectedAt, CorrectedBy, Reason? }` — Compliance records correction audit trail.
- `RegistrationItemAttachedIntegrationEvent { TenantId, RegistrationId, MediaItemId, ItemType, AddedViaAmendmentId?, AttachedAt, EventVersion }` — Catalog records attached document on item's `RegistrationRefs` with `Role = Document` + `ItemType`. `AddedViaAmendmentId` is present when the attach rode through `ApproveAmendment`; absent on direct `AttachMediaItem`.
- `RegistrationDomainEventMapper` with 3 new `Map` overloads (one source domain event each; no fan-out).
- Catalog consumer handler on `media.registration.item-attached` → dispatches `AddRegistrationRefCommand(TenantId, MediaItemId, RegistrationId, Role=Document, ItemType, EventVersion, AddedAt)` using the message's `EventVersion` for idempotent apply (stale message succeeds + raises nothing).
- CDK filter policies in `cdk-magiq-media` admit the 3 new `type` values to Compliance + Notifications + Catalog registration-item-ref consumer queues.

## Wire-visibility

- Process wire additive on 3 new types. **Not safe without the SNS filter-policy migration** — see `docs/breaking-changes.md § Cross-cutting ordering constraint — SNS filter-policy scope`. Existing attribute-scoped subscriptions drop body-only publications; CDK filter-policy migration must deploy + propagate before host emits.

## Scope boundary

- Contract records (3) + mapper overloads (3) + Catalog consumer handler for item-attached + CDK filter-policy edits.
- Domain events + aggregate methods (`AttachMediaItem`, `ApproveAmendment`, `Revoke`, `CorrectReference`) → MM-152 (Registration × write-model).
- Catalog's `media-registration-item-ref` already consumes other Registration events; add revoked + item-attached handlers alongside.
- Error codes → MM-148.
- `RegistrationDispatched@2` upcaster (alias `RegistrationSubmissionRecorded`) → WS-28.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-109 (plan MM-149). MM-152 must ship first (RegistrationRevoked + RegistrationReferenceCorrected + RegistrationItemAttached domain events + AttachMediaItem + ApproveAmendment aggregate methods).

## Phase 0 — Scope confirmation

- [ ] MM-152 shipped (3 domain events + aggregate methods)
- [ ] MM-148 constants reachable (for revoke/correct refusals)
- [ ] Catalog `AddRegistrationRefCommand` reachable (dispatch target for item-attached consumer)

## Phase 1 — Contract records (3)

- [ ] `RegistrationRevokedIntegrationEvent` under `Registrations.Contracts/Events/`
- [ ] `RegistrationReferenceCorrectedIntegrationEvent`
- [ ] `RegistrationItemAttachedIntegrationEvent` carrying `TenantId, RegistrationId, MediaItemId, ItemType, AddedViaAmendmentId?, AttachedAt, EventVersion`

## Phase 2 — Mapper (3 overloads)

- [ ] `RegistrationDomainEventMapper.Map(RegistrationRevoked)` yields `RegistrationRevokedIntegrationEvent`
- [ ] `RegistrationDomainEventMapper.Map(RegistrationReferenceCorrected)` yields `RegistrationReferenceCorrectedIntegrationEvent`
- [ ] `RegistrationDomainEventMapper.Map(RegistrationItemAttached)` yields `RegistrationItemAttachedIntegrationEvent`

## Phase 3 — CDK filter policies

- [ ] **Precondition:** every existing subscription on `media-integration-events` migrated to `FilterPolicyScope: MessageBody` (per `docs/breaking-changes.md § Cross-cutting ordering constraint`). Cross-cutting prerequisite; deploy must land + propagate before any body-only publication fires
- [ ] `cdk-magiq-media` admits `media.registration.revoked` to Catalog + Notifications + Compliance queues
- [ ] `cdk-magiq-media` admits `media.registration.reference-corrected` to Compliance queue
- [ ] `cdk-magiq-media` admits `media.registration.item-attached` to Catalog `media-registration-item-ref` consumer queue
- [ ] `FilterPolicyScope: MessageBody` on `type`

## Phase 4 — Catalog consumers (2)

- [ ] `media-registration-item-ref` consumer handles `media.registration.revoked` → flips entry not-live
- [ ] `media-registration-item-ref` consumer handles `media.registration.item-attached` → dispatches `AddRegistrationRefCommand` with `Role = Document` + `ItemType` from the message. Idempotent via `EventVersion` guard on the `RegistrationRefs` entry (apply only when `eventVersion > LastEventVersion`)

## Phase 5 — Tests

- [ ] Integration: `RevokeRegistration` → outbox → SNS → body carries `type` + payload
- [ ] Integration: `CorrectRegistrationReference` → outbox → SNS → body carries new reference
- [ ] Integration: `AttachMediaItem` → `RegistrationItemAttached` → `media.registration.item-attached` → Catalog records `MediaItem.RegistrationRefs` entry with `Role = Document`
- [ ] Integration: `ApproveAmendment` with document-attach side effect → same wire type with `AddedViaAmendmentId` populated
- [ ] Integration: Catalog consumer flips registration-item-ref not-live on revoked
- [ ] Integration: stale item-attached message (lower `EventVersion`) acked + no state change

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
- 2026-10-18: re-diffed under Arnica review fix for finding #8 (catalog Phase 1 regression). Added `media.registration.item-attached` → 3rd missing type (source: `RegistrationItemAttached` from both direct `AttachMediaItem` + amendment-approved `ApproveAmendment`). Cross-aggregate implication: Catalog's `MediaItem.RegistrationRefs` document entries (per `cross-aggregate-rules.md § rule 13`) are fed by this event — without it, only subject refs land. Scope widened: 2 → 3 contract records + mapper overloads + CDK filter-policy entries; 1 → 2 Catalog consumer handlers (added item-attached → `AddRegistrationRefCommand` with Role=Document). Depends-on now cites MM-152 (3 absent domain events + AttachMediaItem + ApproveAmendment aggregate methods). Phase 3 CDK gains the SNS filter-policy ordering precondition. Phase 5 Tests add 3 integration tests (attach, approve-amendment-attach, stale-EventVersion idempotency).
