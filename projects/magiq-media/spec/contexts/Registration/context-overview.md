# Registration — Context Overview

_Context: `Registration`_

---

## Purpose

The Registration context tracks the formal media-registration lifecycle of a `MediaItem` — electronic (e.g., digital copyright filing) or physical (e.g., paper submission). It is activated by the `Registration` capability on a MediaItem's MediaProfile. A single MediaItem may have multiple independent Registration aggregates of different types.

The lifecycle is owner-driven for initiation and document management; system-only commands advance status transitions that depend on external authority responses (submission confirmation, confirmation, rejection). The integration adapter bridges the external authority system and the Command Handler for system-only commands.

---

## Responsibilities

- Initiate media-registrations (Electronic or Physical) linked to a published MediaItem
- Manage media-registration documents — attach published "document media-items" (MediaItems whose MediaProfile lacks `Processing` capability) before and after confirmation (via amendment workflow)
- Track submission to external authority and its response (confirmation or rejection)
- Support resubmission after rejection
- Expose amendment workflow for adding documents post-confirmation
- Publish integration events for downstream Notifications and authority-tracking consumers

---

## Aggregates

| Aggregate | Description |
|---|---|
| `Registration` | Owns the media-registration lifecycle for a single MediaItem-to-authority submission |

---

## Capability Gate

Registration functionality is activated by the `Registration` capability on a MediaProfile. The handler enforces this at initiation time (`InitiateRegistrationHandler` checks MediaProfile capabilities via `IMediaItemRegistrationContextService`).

---

## Command Authorization

| Command | Actor | Note |
|---|---|---|
| `InitiateRegistration` | User (owner) | Creates the Registration aggregate; caller becomes `OwnerId` |
| `SubmitRegistration` | User (owner) | Transitions `Initiated/Resubmitted → Submitted` |
| `ResubmitRegistration` | User (owner) | Transitions `Rejected → Resubmitted` |
| `CancelRegistration` | User (owner) | Cancels from any non-terminal status |
| `AttachItemToRegistration` | User (owner) | Attaches document before confirmation |
| `RequestAmendment` | User (owner) | Requests document addition post-confirmation |
| `RecordRegistrationSubmission` | System | Records external dispatch by integration adapter (`Submitted → PendingConfirmation`) |
| `ConfirmRegistration` | System | External authority confirmed (`PendingConfirmation → Confirmed`) |
| `RejectRegistration` | System | External authority rejected (`PendingConfirmation → Rejected`) |
| `ApproveAmendment` | System | Integration adapter approved post-confirmation document addition |
| `RejectAmendment` | System | Integration adapter rejected amendment request |

User commands enforce `context.Actor.Id == registration.OwnerId` handler-side. System commands enforce `context.Actor.ActorType == "System"` handler-side. The aggregate enforces status invariants only.

---

## Event Flows

**Inbound (domain events consumed by Registration):** none — `Registration` is self-contained.

**Outbound (integration events published to `media-integration-events`):**

Published inline by `RegistrationIntegrationEventPublisher` (`Registration.WriteModel`).

| C# Record Type | Trigger Domain Event | Purpose |
|---|---|---|
| `RegistrationInitiatedMessage` | `RegistrationInitiated` | Notifications; Catalog (`RegistrationInitiatedConsumer` links ref to MediaItem) |
| `RegistrationSubmittedMessage` | `RegistrationSubmitted` | Notifications; saga orchestrator triggers external authority submission |
| `RegistrationResubmittedMessage` | `RegistrationResubmitted` | Notifications; saga orchestrator retries authority submission |
| `RegistrationConfirmedMessage` | `RegistrationConfirmed` | Primary cross-module signal; reference number available downstream; Compliance |
| `RegistrationRejectedMessage` | `RegistrationRejected` | Notifications alert with rejection reason |
| `RegistrationCancelledMessage` | `RegistrationCancelled` | Cleanup; Notifications; authority tracking update |

Amendment events (`RegistrationAmendmentRequested`, `RegistrationAmendmentApproved`, `RegistrationAmendmentRejected`) and `RegistrationItemAttached` are **domain-internal only** — they do not cross module boundaries.

---

## Cross-Aggregate Dependencies

| Dependency | Where | Why |
|---|---|---|
| `MediaItem` (Catalog) | `InitiateRegistrationHandler`, `AttachItemToRegistrationHandler`, `RequestAmendmentHandler` | Validate MediaItem exists, is `Published`, and has the correct capability state |
| `media-items` read model | Handler-side via `IMediaItemRegistrationContextService` | Cross-aggregate validation; never direct aggregate-to-aggregate call |

---

## Ubiquitous Language

| Term | Meaning |
|---|---|
| Registration | A formal media-registration submission of a MediaItem to an authority (Electronic or Physical) |
| Registration document | A published "document media-item" (MediaItem whose MediaProfile lacks `Processing`) attached as supporting evidence |
| Document media-item | A MediaItem whose MediaProfile lacks the `Processing` capability — quota-exempt, virus scan only, stored in `media-documents` |
| Amendment | A request to add a supporting document after the Registration is `Confirmed` |
| RegistrationItem | Value object representing an attached document: `{MediaItemId, ItemType, AddedAt, AddedViaAmendmentId?}` |
| RegistrationAuthority | Free text; normalised (trimmed, title-cased) by the handler on write |
| PendingConfirmation | Status between external dispatch and authority decision |
| System actor | An `IActor` with `ActorType = "System"`. Used by integration adapters to advance status based on external authority responses. Not subject to ownership checks — System is an actor type, not an ownership role. |

---

## Integration Event Contracts

### Published

**Publisher:** `RegistrationIntegrationEventPublisher` (`Registration.WriteModel`) for all six events.

#### `RegistrationInitiatedMessage`

```csharp
record RegistrationInitiatedMessage(
    string TenantId,
    string RegistrationId,
    string OwnerId,
    string MediaItemId,
    string MediaProfileId,
    string RegistrationType,        // RegistrationType enum value as string: "Electronic" | "Physical"
    string RegistrationAuthority,
    DateTimeOffset InitiatedAt
);
```

> Catalog's `RegistrationInitiatedConsumer` subscribes — dispatches `AddRegistrationRefCommand` to link the media-registration reference on the `MediaItem`.

#### `RegistrationSubmittedMessage`

```csharp
record RegistrationSubmittedMessage(
    string TenantId,
    string RegistrationId,
    DateTimeOffset SubmittedAt
);
```

> Minimal payload — saga orchestrator and Notifications subscribers resolve full context from their own read models or prior `RegistrationInitiatedMessage`.

#### `RegistrationResubmittedMessage`

```csharp
record RegistrationResubmittedMessage(
    string TenantId,
    string RegistrationId,
    DateTimeOffset SubmittedAt
);
```

> Published when a previously rejected media-registration is resubmitted. Downstream consumers react to retry external authority submission.

#### `RegistrationConfirmedMessage`

```csharp
record RegistrationConfirmedMessage(
    string TenantId,
    string RegistrationId,
    string OwnerId,
    string MediaItemId,
    string RegistrationReference,   // Official reference number from the registering authority
    string RegistrationType,        // RegistrationType enum value as string
    string RegistrationAuthority,
    DateTimeOffset ConfirmedAt
);
```

> `RegistrationReference` is the authoritative identifier assigned by the external authority. Compliance context subscribes to this event.

#### `RegistrationRejectedMessage`

```csharp
record RegistrationRejectedMessage(
    string TenantId,
    string RegistrationId,
    string OwnerId,
    string MediaItemId,
    string Reason,
    DateTimeOffset RejectedAt
);
```

#### `RegistrationCancelledMessage`

```csharp
record RegistrationCancelledMessage(
    string TenantId,
    string RegistrationId,
    string OwnerId,
    string MediaItemId,
    string PreviousStatus,          // RegistrationStatus enum value as string
    DateTimeOffset CancelledAt
);
```

---

## Related

- [Registration Business Scenarios](./business-scenarios.md)
- [Registration Write Model](./aggregates/Registration/media-registration.write-model.md)
- [Registration Read Model](./aggregates/Registration/media-registration.read-model.md)
- [Registration API](./aggregates/Registration/media-registration.api.md)
- [MediaItem Write Model](../Catalog/aggregates/MediaItem/mediaitem.write-model.md) — `RegistrationRefAdded` event
