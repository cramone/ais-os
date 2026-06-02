# Registration — Read Model

_Context: `Registration`_
_Aggregate: `Registration`_

---

## Read Models

### `media-registrations` (DynamoDB)

Summary table. Powers media-registration list queries per MediaItem and per owner.

| Field                   | Type      | Notes                                               |
| ----------------------- | --------- | --------------------------------------------------- |
| `PK`                    | `string`  | `TENANT#{TenantId}#{RegistrationId}`                |
| `TenantId`              | `string`  |                                                     |
| `RegistrationId`        | `string`  |                                                     |
| `MediaItemId`           | `string`  |                                                     |
| `OwnerId`               | `string`  |                                                     |
| `RegistrationType`      | `string`  | `Electronic \| Physical`                            |
| `RegistrationAuthority` | `string`  | Normalised (trimmed, title-cased)                   |
| `Status`                | `string`  | `RegistrationStatus` enum                           |
| `Reference`             | `string?` | External reference number; populated on `Confirmed` |
| `SubmittedAt`           | `string?` | ISO 8601                                            |
| `ConfirmedAt`           | `string?` | ISO 8601                                            |
| `InitiatedAt`           | `string`  | ISO 8601                                            |
| `ProjectedVersion`      | `long`    | Idempotency dedup guard                             |
| `EventId`               | `string`  |                                                     |

**GSIs:**
- `MediaItemRegistrationsIndex` (`MediaItemId`) — list all media-registrations for a given MediaItem
- `OwnerStatusIndex` (`OwnerId + Status`) — list media-registrations by owner and status

---

### `media-registration-detail` (DynamoDB)

Full detail table. Includes documents (`Items`) and amendments.

| Field                   | Type       | Notes                                                                                        |
| ----------------------- | ---------- | -------------------------------------------------------------------------------------------- |
| `PK`                    | `string`   | `TENANT#{TenantId}#{RegistrationId}`                                                         |
| `TenantId`              | `string`   |                                                                                              |
| `RegistrationId`        | `string`   |                                                                                              |
| `MediaItemId`           | `string`   |                                                                                              |
| `OwnerId`               | `string`   |                                                                                              |
| `RegistrationType`      | `string`   |                                                                                              |
| `RegistrationAuthority` | `string`   |                                                                                              |
| `Status`                | `string`   |                                                                                              |
| `Reference`             | `string?`  |                                                                                              |
| `Notes`                 | `string?`  |                                                                                              |
| `SubmittedAt`           | `string?`  |                                                                                              |
| `ConfirmedAt`           | `string?`  |                                                                                              |
| `InitiatedAt`           | `string`   |                                                                                              |
| `Items`                 | `object[]` | `[{ MediaItemId, ItemType, AddedAt, AddedViaAmendmentId? }]`                                 |
| `Amendments`            | `object[]` | `[{ AmendmentId, MediaItemId, ItemType, RequestedAt, Status, ResolvedAt?, DecisionNotes? }]` |
| `ProjectedVersion`      | `long`     |                                                                                              |
| `EventId`               | `string`   |                                                                                              |

---

### `media-registrations` (OpenSearch)

Full-text and faceted search for media-registration discovery.

| Field | Type | Notes |
|---|---|---|
| `registrationId` | `keyword` | |
| `tenantId` | `keyword` | |
| `mediaItemId` | `keyword` | |
| `ownerId` | `keyword` | |
| `mediaProfileId` | `keyword` | Sourced from `RegistrationInitiated.MediaProfileId` |
| `registrationType` | `keyword` | |
| `registrationAuthority` | `text` (standard) + `keyword` sub-field | Full-text search + exact match / sort / facet |
| `status` | `keyword` | |
| `submittedAt` | `date` | |
| `confirmedAt` | `date` | |
| `updatedAt` | `date` | |

---

## Projection Handlers

### `RegistrationProjector`

**Trigger:** `media-projector` SQS queue
**Targets:** `media-registrations` (DynamoDB), OpenSearch `media-registrations`

| Event | Write |
|---|---|
| `RegistrationInitiated` | INSERT `media-registrations` (`status=Initiated`) |
| `RegistrationSubmitted` | UPDATE status → `Submitted`; set `SubmittedAt` |
| `RegistrationSubmissionRecorded` | UPDATE status → `SubmissionRecorded` |
| `RegistrationConfirmed` | UPDATE status → `Confirmed`; set `Reference`, `ConfirmedAt` |
| `RegistrationRejected` | UPDATE status → `Rejected` |
| `RegistrationResubmitted` | UPDATE status → `Submitted` |
| `RegistrationCancelled` | UPDATE status → `Cancelled` |

**TenantId extraction:** From SQS message attribute envelope — never from event payload body.
**Idempotency:** `ProjectedVersion` dedup guard on all writes. `ConditionalCheckFailedException` treated as success.

---

### `RegistrationDetailProjector`

**Trigger:** `media-projector` SQS queue
**Target:** `media-registration-detail` (DynamoDB)

| Event | Write |
|---|---|
| `RegistrationInitiated` | INSERT (`status=Initiated`, `Items=[]`, `Amendments=[]`) |
| `RegistrationSubmitted` | UPDATE status → `Submitted`; set `SubmittedAt` |
| `RegistrationSubmissionRecorded` | UPDATE status → `SubmissionRecorded`; set `ExternalReference`, `Notes` |
| `RegistrationConfirmed` | UPDATE status → `Confirmed`; set `ReferenceNumber`, `ConfirmedAt` |
| `RegistrationRejected` | UPDATE status → `Rejected`; set `RejectionReason`, `RejectedAt` |
| `RegistrationResubmitted` | UPDATE status → `Submitted`; update `SubmittedAt` |
| `RegistrationCancelled` | UPDATE status → `Cancelled`; set `CancelledAt` |
| `RegistrationItemAttached` | UPDATE — append to `Items[]` |
| `RegistrationAmendmentRequested` | UPDATE — append to `Amendments[]` (`status=Pending`); set aggregate `Status=AmendmentRequested` |
| `RegistrationAmendmentApproved` | UPDATE — set matching amendment `status=Approved`, `DecidedAt`, `DecisionNotes` |
| `RegistrationAmendmentRejected` | UPDATE — set matching amendment `status=Rejected`, `DecidedAt`, `DecisionNotes` |

**TenantId extraction:** From SQS message attribute envelope — never from event payload body.
**Idempotency:** `ProjectedVersion` dedup guard on all writes. `ConditionalCheckFailedException` treated as success.

---

## Queries

| Query | Description |
|---|---|
| `GetRegistrationByIdQuery(TenantId, RegistrationId)` | Full detail including `Items` and `Amendments` history |
| `ListRegistrationsByMediaItemQuery(TenantId, MediaItemId, PagerParameters)` | All media-registrations for a given MediaItem (via `MediaItemRegistrationsIndex`) |
| `ListRegistrationsByOwnerQuery(TenantId, OwnerId, PagerParameters)` | All media-registrations for an owner (via `OwnerStatusIndex`) |
| `SearchRegistrationsQuery(TenantId, SearchTerm, PagerParameters)` | Full-text search across `registrationAuthority`, `registrationType`, `referenceNumber` (OpenSearch) |

---

## Query Handlers

Handlers extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and return DTOs only — no domain objects or event payloads cross the read boundary. PK construction is handled by the framework except for `SearchRegistrationsHandler`, which uses `IOpenSearchLowLevelClient` directly.

| Handler | Reader | Method |
|---|---|---|
| `GetRegistrationByIdHandler` | `IReadModelReader<RegistrationDetailReadModel>` | `GetAsync(request, ct)` |
| `ListRegistrationsByMediaItemHandler` | `IReadModelReader<RegistrationDetailReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `ListRegistrationsByOwnerHandler` | `IReadModelReader<RegistrationDetailReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `SearchRegistrationsHandler` | `IOpenSearchLowLevelClient` (direct) | OpenSearch DSL — `bool` query with tenant `term` filter + `multi_match` on `RegistrationAuthority^2`, `ReferenceNumber^3`, `RegistrationType`, `Notes`. Pagination via `from`/`size`. |

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `RegistrationSummaryReadModel`

Targets `media-registrations` (DynamoDB). Powers all list and index queries.

```csharp
record RegistrationSummaryReadModel(
    string RegistrationId,
    string TenantId,
    string MediaItemId,
    string OwnerId,
    string RegistrationType,
    string RegistrationAuthority,
    string Status,
    string? Reference,
    DateTimeOffset? SubmittedAt,
    DateTimeOffset? ConfirmedAt,
    DateTimeOffset InitiatedAt,
    long ProjectedVersion) : IReadModel;
```

### `RegistrationDetailReadModel`

Targets `media-registration-detail` (DynamoDB). Powers `GetRegistrationById`.

```csharp
record RegistrationDetailReadModel(
    string RegistrationId,
    string TenantId,
    string MediaItemId,
    string OwnerId,
    string MediaProfileId,
    string RegistrationType,
    string RegistrationAuthority,
    string Status,
    string? ExternalReference,
    string? ReferenceNumber,
    string? Notes,
    string? RejectionReason,
    List<RegistrationItemDto> Items,
    List<RegistrationAmendmentDto> Amendments,
    DateTimeOffset? SubmittedAt,
    DateTimeOffset? ConfirmedAt,
    DateTimeOffset? RejectedAt,
    DateTimeOffset? CancelledAt,
    DateTimeOffset? ExpiresAt,
    DateTimeOffset InitiatedAt,
    long ProjectedVersion) : IReadModel;
```

### `RegistrationItemDto`

Carried by `RegistrationDetailReadModel.Items`.

```csharp
record RegistrationItemDto(
    string MediaItemId,
    string ItemType,           // RegistrationItemType enum value
    string? AddedViaAmendmentId,
    DateTimeOffset AttachedAt);
```

### `RegistrationAmendmentDto`

Carried by `RegistrationDetailReadModel.Amendments`.

```csharp
record RegistrationAmendmentDto(
    string AmendmentId,
    string RequestedBy,        // OwnerId of the requestor
    string MediaItemId,
    string ItemType,           // RegistrationItemType enum value
    string? Notes,
    string Status,             // Pending | Approved | Rejected
    DateTimeOffset RequestedAt,
    DateTimeOffset? DecidedAt,
    string? DecisionNotes);
    
public enum RegistrationStatus  
{  
    Initiated,              // Registration created; awaiting document attachment and submission  
    Submitted,              // Owner signalled ready; awaiting integration adapter dispatch  
    SubmissionRecorded,     // Integration adapter dispatched to external authority; awaiting decision  
    PendingConfirmation,    // Awaiting external authority decision  
    Approved,               // External authority approved  
    Rejected,               // External authority rejected; owner may resubmit  
    Resubmitted,            // Owner prepared revised submission after rejection  
    Confirmed,              // External authority confirmed — terminal; amendments only via RequestAmendment  
    AmendmentRequested,     // Owner requested amendment  
    AmendmentApproved,      // External authority approved amendment  
    AmendmentRejected,      // External authority rejected amendment  
    Cancelled               // Cancelled — terminal (permitted from any status except Confirmed and Cancelled)  
}
```

---

## Related

- [Registration Write Model](./media-registration.write-model.md)
- [Registration API](./media-registration.api.md)
- [Registration Context Overview](../../context-overview.md)