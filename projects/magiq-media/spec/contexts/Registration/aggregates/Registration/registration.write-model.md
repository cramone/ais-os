# Registration — Write Model

_Context: `Registration`_
_Aggregate: `Registration`_
_Stream prefix: `reg_`_

---

## Purpose

Tracks the formal media-registration lifecycle of a `MediaItem` with an external authority. Supports Electronic and Physical media-registration types. The lifecycle is owner-driven for initiation and document management; system-only commands advance status based on external authority responses.

A MediaItem may have multiple independent `Registration` aggregates of different types.

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| MediaItem must exist and be `Published` | `DomainError.MediaItemNotFound` / `InvalidOperation` | `InitiateRegistration` (handler) |
| MediaProfile must have `Registration` capability | `DomainError.CapabilityNotEnabled` | `InitiateRegistration` (handler) |
| `SubmitRegistration` requires `Status ∈ {Initiated, Resubmitted}` and ≥1 document attached | `DomainError.InvalidOperation` / `RegistrationHasNoDocuments` | `SubmitRegistration` |
| `ResubmitRegistration` requires `Status = Rejected` | `DomainError.InvalidOperation` | `ResubmitRegistration` |
| `CancelRegistration` requires `Status ∉ {Confirmed, Cancelled}` | `DomainError.RegistrationAlreadyConfirmed` / `RegistrationAlreadyCancelled` | `CancelRegistration` |
| `AttachItemToRegistration` — document must be `Published` MediaItem whose MediaProfile lacks `Processing` capability | `DomainError.InvalidRegistrationItem` | `AttachItemToRegistration` (handler) |
| Document `MediaItemId` not already in `Items` | `DomainError.DocumentAlreadyAttached` | `AttachItemToRegistration` |
| `AttachItemToRegistration` rejected when `Status = Confirmed` — use amendment workflow | `DomainError.UseAmendmentWorkflow` | `AttachItemToRegistration` |
| `RequestAmendment` only valid when `Status = Confirmed`; document must not have a `Pending` amendment | `DomainError.InvalidOperation` / `DuplicatePendingAmendment` | `RequestAmendment` |
| `RegistrationAuthority` normalised (trim + title-case) by handler before event is raised | (string transform, no error) | `InitiateRegistration` (handler) |

---

## Properties

| Property | Type | Notes |
|---|---|---|
| `RegistrationId` | `RegistrationId` | UUID v7-based |
| `TenantId` | `TenantId` | Set from `RegistrationInitiated`. Immutable. |
| `MediaItemId` | `MediaItemId` | The media-item being registered. Immutable. |
| `OwnerId` | `OwnerId` | Immutable. |
| `RegistrationType` | `RegistrationType` | `Electronic \| Physical` |
| `RegistrationAuthority` | `string` | Normalised (trimmed, title-cased) on write. |
| `Status` | `RegistrationStatus` | See lifecycle. |
| `Reference` | `RegistrationReference?` | External reference from authority; set on `RegistrationConfirmed`. |
| `Notes` | `string?` | Free text. |
| `SubmittedAt` | `DateTimeOffset?` | Set on `Submitted` transition. |
| `ConfirmedAt` | `DateTimeOffset?` | Set on `Confirmed` transition. |
| `Items` | `IReadOnlyList<RegistrationItem>` | Attached supporting documents. |
| `Amendments` | `IReadOnlyList<RegistrationAmendment>` | Post-confirmation document addition requests. |
| `InitiatedAt` | `DateTimeOffset` | |

---

## Status Lifecycle

```
Initiated
    │
    │  SubmitRegistration (≥1 document attached)
    ▼
Submitted
    │
    │  RecordRegistrationSubmission (System)
    ▼
PendingConfirmation
    │
    ├─ ConfirmRegistration (System) ────────────────▶ Confirmed (terminal — amendments only)
    │
    └─ RejectRegistration (System) ─────────────────▶ Rejected
                                                            │
                                                            │  ResubmitRegistration
                                                            ▼
                                                       Resubmitted
                                                            │
                                                            │  SubmitRegistration
                                                            ▼
                                                       Submitted ...

CancelRegistration is valid from any status except Confirmed and Cancelled → Cancelled (terminal)
```

---

## RegistrationItem Value Object

Represents a single attached supporting document.

| Property | Type | Notes |
|---|---|---|
| `MediaItemId` | `MediaItemId` | The document MediaItem |
| `ItemType` | `RegistrationItemType` | `ApplicationForm \| SupportingEvidence \| ConfirmationReceipt \| Other` |
| `AddedAt` | `DateTimeOffset` | Stamped in the event (not `UtcNow` at replay) |
| `AddedViaAmendmentId` | `AmendmentId?` | `null` for pre-confirmation attachments; set for amendment-approved additions |

---

## RegistrationAmendment Value Object

| Property | Type | Notes |
|---|---|---|
| `AmendmentId` | `AmendmentId` | UUID v7-based |
| `MediaItemId` | `MediaItemId` | The document requested to be added |
| `ItemType` | `RegistrationItemType` | |
| `RequestedAt` | `DateTimeOffset` | |
| `Status` | `AmendmentStatus` | `Pending \| Approved \| Rejected` |
| `ResolvedAt` | `DateTimeOffset?` | |
| `DecisionNotes` | `string?` | |

Only one `Pending` amendment per `MediaItemId` per media-registration is permitted (duplicate check is aggregate-side). Multiple pending amendments for different documents may exist simultaneously.

---

## Methods (Commands)

| Method | Description |
|---|---|
| `Registration.Initiate(tenantId, id, mediaItemId, ownerId, registrationType, authority, notes?, initiatedAt)` | Factory. Guard: capability check is handler-side. Raises `RegistrationInitiated`. Also raises `RegistrationRefAdded` on the MediaItem stream (via handler). |
| `Submit()` | Transitions `Initiated/Resubmitted → Submitted`. Guard: `Status ∈ {Initiated, Resubmitted}`; ≥1 media-item in `Items`. |
| `RecordSubmission()` | System. Transitions `Submitted → PendingConfirmation`. |
| `Confirm(reference)` | System. Transitions `PendingConfirmation → Confirmed`. Sets `Reference` and `ConfirmedAt`. |
| `Reject(reason)` | System. Transitions `PendingConfirmation → Rejected`. |
| `Resubmit()` | Transitions `Rejected → Resubmitted`. |
| `Cancel()` | Transitions any non-terminal status → `Cancelled`. Guard: `Status ∉ {Confirmed, Cancelled}`. |
| `AttachItem(mediaItemId, itemType)` | Attaches a document. Guard: `Status ≠ Confirmed`; `Status ≠ Cancelled`; `MediaItemId` not already in `Items`. Document validation (Published + no Processing capability) is handler-side. |
| `RequestAmendment(amendmentId, mediaItemId, itemType, requestedAt)` | Requests post-confirmation document addition. Guard: `Status = Confirmed`; no `Pending` amendment for same `MediaItemId`. Document validation is handler-side. |
| `ApproveAmendment(amendmentId, decisionNotes?)` | System. Raises `RegistrationAmendmentApproved` + `RegistrationItemAttached` atomically in same event-store write. |
| `RejectAmendment(amendmentId, decisionNotes?)` | System. |

---

## Domain Events

| Event | Key Payload Fields | Notes |
|---|---|---|
| `RegistrationInitiated` | `TenantId`†, `RegistrationId`, `MediaItemId`, `OwnerId`, `RegistrationType`, `RegistrationAuthority`, `Notes?`, `InitiatedAt` | `TenantId` is first field. `Status → Initiated`. |
| `RegistrationSubmitted` | `RegistrationId`, `SubmittedAt` | `Status → Submitted` |
| `RegistrationSubmissionRecorded` | `RegistrationId`, `RecordedAt` | System. `Status → PendingConfirmation` |
| `RegistrationConfirmed` | `RegistrationId`, `Reference`, `ConfirmedAt` | System. `Status → Confirmed` (terminal) |
| `RegistrationRejected` | `RegistrationId`, `RejectionReason`, `RejectedAt` | System. `Status → Rejected` |
| `RegistrationResubmitted` | `RegistrationId`, `ResubmittedAt` | `Status → Resubmitted` |
| `RegistrationCancelled` | `RegistrationId`, `CancelledAt`, `PreviousStatus` | `Status → Cancelled` (terminal) |
| `RegistrationItemAttached` | `RegistrationId`, `MediaItemId`, `ItemType`, `AddedViaAmendmentId?`, `AddedAt` | Raised by `AttachItem` (pre-confirmation) and by `ApproveAmendment` (post-confirmation, atomically) |
| `RegistrationAmendmentRequested` | `RegistrationId`, `AmendmentId`, `MediaItemId`, `ItemType`, `RequestedAt` | |
| `RegistrationAmendmentApproved` | `RegistrationId`, `AmendmentId`, `DecisionNotes?`, `ApprovedAt` | Followed atomically by `RegistrationItemAttached` (same event-store write) |
| `RegistrationAmendmentRejected` | `RegistrationId`, `AmendmentId`, `DecisionNotes?`, `RejectedAt` | |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command | Actor | Notes |
|---|---|---|
| `InitiateRegistrationCommand(RegistrationId, MediaItemId, OwnerId, RegistrationType, RegistrationAuthority, Notes?)` | Owner | Handler normalises `RegistrationAuthority`; validates MediaItem + capability |
| `SubmitRegistrationCommand(RegistrationId)` | Owner | |
| `ResubmitRegistrationCommand(RegistrationId)` | Owner | |
| `CancelRegistrationCommand(RegistrationId)` | Owner | |
| `AttachItemToRegistrationCommand(RegistrationId, MediaItemId, ItemType)` | Owner | Handler validates document MediaItem |
| `RequestAmendmentCommand(RegistrationId, AmendmentId, MediaItemId, ItemType)` | Owner | Handler validates document MediaItem |
| `RecordRegistrationSubmissionCommand(RegistrationId)` | System | Integration adapter |
| `ConfirmRegistrationCommand(RegistrationId, Reference)` | System | Integration adapter |
| `RejectRegistrationCommand(RegistrationId, RejectionReason)` | System | Integration adapter |
| `ApproveAmendmentCommand(RegistrationId, AmendmentId, DecisionNotes?)` | System | Integration adapter; aggregate raises two events atomically |
| `RejectAmendmentCommand(RegistrationId, AmendmentId, DecisionNotes?)` | System | Integration adapter |

---

## Handler Pre-Conditions

| Handler | Pre-condition | Error |
|---|---|---|
| `InitiateRegistrationHandler` | `MediaItem` must exist | `DomainError.MediaItemNotFound` |
| `InitiateRegistrationHandler` | `MediaItem` must be `Published` | `DomainError.InvalidOperation` |
| `InitiateRegistrationHandler` | MediaProfile must have `Registration` capability | `DomainError.CapabilityNotEnabled` |
| `InitiateRegistrationHandler` | `RegistrationAuthority` normalised (trim + title-case) before event | (transform, no error) |
| `AttachItemToRegistrationHandler` | Document `MediaItem` must exist | `DomainError.MediaItemNotFound` |
| `AttachItemToRegistrationHandler` | Document `MediaItem` must be `Published` | `DomainError.InvalidOperation` |
| `AttachItemToRegistrationHandler` | Document MediaProfile must lack `Processing` capability | `DomainError.InvalidRegistrationItem` |
| `RequestAmendmentHandler` | Document `MediaItem` must exist | `DomainError.MediaItemNotFound` |
| `RequestAmendmentHandler` | Document `MediaItem` must be `Published` | `DomainError.InvalidOperation` |
| `RequestAmendmentHandler` | Document MediaProfile must lack `Processing` capability | `DomainError.InvalidRegistrationItem` |
| `ConfirmRegistrationHandler` | `Reference` must be non-empty | `DomainError.InvalidOperation` |

---

## Write Model Service Interfaces

```csharp
// Used by InitiateRegistration, AttachItemToRegistration, and RequestAmendment handlers.
// Covers: MediaItem existence check, Published status check, MediaProfile capability lookup.
interface IMediaItemRegistrationContextService {
    Task<MediaItemRegistrationContext?> GetContextAsync(
        TenantId tenantId, MediaItemId mediaItemId, CancellationToken ct);
}

record MediaItemRegistrationContext(
    MediaItemId MediaItemId,
    bool IsPublished,
    bool HasRegistrationCapability,
    bool HasProcessingCapability);
```

---

## Published Integration Events

Published inline by `RegistrationIntegrationEventPublisher` (`Registration.WriteModel`) immediately after the domain event is persisted. All events target the `media-integration-events` SNS topic.

Amendment events (`RegistrationAmendmentRequested`, `RegistrationAmendmentApproved`, `RegistrationAmendmentRejected`) and `RegistrationItemAttached` are **domain-internal only** — they do not cross module boundaries.

| Integration Event | Source Domain Event | Notes |
|---|---|---|
| `RegistrationInitiatedMessage` | `RegistrationInitiated` | Consumed by Notifications; consumed by Catalog `RegistrationInitiatedConsumer` which dispatches `AddRegistrationRefCommand` to append the `RegistrationId` to the linked `MediaItem` stream |
| `RegistrationSubmittedMessage` | `RegistrationSubmitted` | Consumed by Notifications; consumed by saga orchestrator to trigger external authority submission |
| `RegistrationResubmittedMessage` | `RegistrationResubmitted` | Consumed by Notifications; consumed by saga orchestrator to retry authority submission |
| `RegistrationConfirmedMessage` | `RegistrationConfirmed` | Primary cross-module signal — reference number now available downstream; consumed by Compliance and Notifications |
| `RegistrationRejectedMessage` | `RegistrationRejected` | Consumed by Notifications to alert the owner with the rejection reason |
| `RegistrationCancelledMessage` | `RegistrationCancelled` | Consumed by Notifications; authority tracking cleanup |

---

## Consumed Integration Events

Consumed via the `media-cross-module-events` SQS queue. All consumers are registered in the `Media.IntegrationEventConsumers.Lambda` host.

**From Catalog — consumer: `MediaItemRegistrationContextConsumer`**

Maintains the `media-item-registration-refs` write-side reference model used by `InitiateRegistrationHandler`, `AttachItemToRegistrationHandler`, and `RequestAmendmentHandler` to resolve MediaItem existence, publish status, and capability eligibility without loading the Catalog aggregate directly.

| Integration Event | Source | Action |
|---|---|---|
| `MediaItemCreatedIntegrationEvent` | Catalog | INSERT entry; sets `IsPublished = false`, derives `HasRegistrationCapability` and `HasProcessingCapability` from `Capabilities` on the event |
| `MediaItemApprovedIntegrationEvent` | Catalog | UPDATE `IsPublished = true` |
| `MediaItemArchivedIntegrationEvent` | Catalog | UPDATE `IsPublished = false` — archived media-items can no longer be registered |

---

## Design Notes

**Two-event atomic write on `ApproveAmendment`:** `RegistrationAmendmentApproved` followed by `RegistrationItemAttached` (with `AddedViaAmendmentId` set) are appended in the same event-store write. The projector handles them as a pair — `RegistrationAmendmentApproved` resolves the amendment; `RegistrationItemAttached` adds the document to the read model. Handlers are unaware of the two-event pair.

**`RegistrationItemAttached.AddedAt` is event-stamped:** To ensure replay-correctness, `AddedAt` is stamped at event emission time and carried in the event payload — not re-derived from `UtcNow` on Apply.

**`RegistrationAuthority` normalisation:** Title-cased on write by the handler (e.g., `"US Copyright Office"` → `"Us Copyright Office"`). Controlled vocabulary is deferred to v2. Stored and indexed as-normalised.

---

## Reference Models

Reference models consumed by this write model's command handlers. All are read-only projections; this context never writes to them directly.

---

### `media-item-registration-refs` (DynamoDB — composite slice)

**Owned by:** Registration  
**Consumed via:** `IMediaItemRegistrationContextService` (`GetAsync`)  
**Used by:** `InitiateRegistrationHandler` (MediaItem must exist, be `Published`, have `Registration` capability, and lack `Processing` capability), `AttachItemToRegistrationHandler` and `RequestAmendmentHandler` (same document validation rules — media-items attached to media-registrations must be published documents, not processed media).

This is a single composite lookup that collapses a MediaItem existence check, its publish status, and two MediaProfile capability checks into one query, avoiding multiple round-trips across context boundaries. Populated entirely from Catalog integration events — Registration never reads Catalog's own DynamoDB tables directly.

| Field | Type | Purpose |
|---|---|---|
| `MediaItemId` | `string` | Lookup key |
| `MediaProfileId` | `string` | Carried for audit / future use |
| `IsPublished` | `bool` | MediaItem must be in `Published` status — draft, rejected, or withdrawn media-items cannot be registered |
| `HasRegistrationCapability` | `bool` | MediaProfile must expose the `Registration` capability — enforces the activation chain |
| `HasProcessingCapability` | `bool` | Must be `false` — media-items with `Processing` capability are processed media (video/audio/image), not documents or archives eligible for media-registration |

**Subscribed integration events (consumer handlers in `Media.IntegrationEventConsumers.Lambda`, consuming Catalog via `media-cross-module-events` SQS queue):**

| Integration Event | Source | Write |
|---|---|---|
| `MediaItemCreatedIntegrationEvent` | Catalog | INSERT with `IsPublished = false`; derives `HasRegistrationCapability` and `HasProcessingCapability` from `Capabilities` on the event |
| `MediaItemApprovedIntegrationEvent` | Catalog | UPDATE `IsPublished = true` |
| `MediaItemArchivedIntegrationEvent` | Catalog | UPDATE `IsPublished = false` — archived media-items can no longer be registered |

---

## Retention Semantics

### Legal Hold

A `Confirmed` registration represents an external legal record — it has been submitted to and acknowledged by an official registration authority. The following immutability rules apply:

- A `Confirmed` registration **cannot be cancelled** on the platform. It is a permanent record of the filing. (`RegistrationConfirmed` error on cancel attempt.)
- A `Confirmed` registration **cannot be modified** except via the Amendment process (`POST /registrations/{id}/amendments`), which requires explicit system-actor approval for each document change.
- `Confirmed` registrations are **never hard-deleted** from the platform, even on tenant offboarding. They are archived to cold storage and retained for the statutory minimum period applicable to the registration authority's jurisdiction (default: **10 years**).
- The `media-registration-detail` and `media-registrations` read model records are retained for the same period. Event store records (`media-events`) for `Confirmed` registrations are considered immutable legal records and must not be purged.

### Right to Erasure (GDPR / Privacy)

Registration records occupy a special legal category — they document filings with public authorities and may contain legally binding information. Right-to-erasure requests are handled as follows:

| Field category | Erasure treatment |
|---|---|
| Personally identifiable fields (`OwnerId`, `Notes`, actor-derived fields in events) | Replaced with a tombstone value (`"[erased]"`) in a separate PII erasure pass. The structural event record is retained. |
| Registration reference number (`Reference`) | **Retained** — it identifies a public record that exists independently of the platform. |
| Document MediaItem references | `MediaItemId` references are retained; the MediaItem content itself is subject to the MediaItem's own erasure policy. |
| `Confirmed` registration record (status, authority, type, dates) | **Retained** — this is a public legal record. Erasure of a confirmed registration is not supported without a formal authority request. |

Erasure requests that touch `Confirmed` registrations must be escalated to the legal/compliance team before processing. The platform records the erasure request in an audit log but does not automatically purge confirmed registration data.

### Deletion and Archival Lifecycle

Registrations do not have a soft-delete path in the same sense as Assets or MediaItems. The lifecycle is:

```
Initiated → Submitted → PendingConfirmation → Confirmed  [terminal — permanent legal record]
         → Rejected → Resubmitted → ... (retry cycle)
         → Cancelled  [terminal — owner-initiated before confirmation]
```

**Terminal states:**

| Status | Retention | Notes |
|---|---|---|
| `Confirmed` | **10 years minimum** (statutory). Retained in cold storage after tenant offboarding. | Legal record — immutable. |
| `Cancelled` | **3 years** (audit trail). Purged after retention period on tenant data export or erasure request. | Not a legal record. |

**Tenant offboarding:**

When a tenant is offboarded:
1. All `Confirmed` registrations are exported to a compliance archive bucket (`media-compliance-archive/{tenantId}/registrations/`) in NDJSON format.
2. All read model records for the tenant are purged.
3. Event store records for `Confirmed` registrations are transferred to the compliance archive and marked with `LegalHold = true` in the archive manifest — they are not deleted from the event store until the 10-year statutory retention period elapses.
4. `Cancelled` registrations are included in the standard tenant data export and purged on schedule.

This policy is implemented by the tenant offboarding process (see SPEC-17 — not yet implemented). Until SPEC-17 is delivered, tenant offboarding requires a manual compliance review.
