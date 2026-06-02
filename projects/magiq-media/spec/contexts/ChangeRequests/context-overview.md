# ChangeRequests — Context Overview

_Context: `ChangeRequests`_

---

## Purpose

Manages the change request lifecycle for MediaItem edits and publication. A `MediaChangeRequest` (MCR) can be created at **checkout time** (CR-first model) or at **submit time** (legacy path, `ReviewPolicy = RequiredForPublish`). The MCR owns the reviewer roster, records decisions, and emits resolution events that sagas use to dispatch `ApproveMediaItem` or `RejectMediaItem` on the linked MediaItem.

---

## Responsibilities

- Create and track `MediaChangeRequest` instances — one per checkout or submission cycle
- Manage CR lifecycle: `CheckoutBound → SubmissionBound → Approved / Rejected / Abandoned`
- Manage reviewer assignment, removal, and decision recording (approve / reject / withdraw)
- Auto-resolve MCR to terminal state based on reviewer decision counts
- Track threaded review comments — persisted in `media-change-request-comments`
- Emit resolution events for `MediaItemReviewSaga` and `MediaItemCheckoutReviewSaga` to act on
- Maintain read models for review status and comment threads

**Out of scope:** Direct modification of MediaItem state. The MCR emits events only — sagas dispatch cross-aggregate commands.

---

## Aggregates

| Aggregate | Description |
|---|---|
| `MediaChangeRequest` | Peer-review workflow for a single MediaItem submission cycle |

---

## Service Boundaries

- **Owns:** `media-change-requests`, `media-change-request-comments` DynamoDB tables
- **Does not own:** MediaItem state — outcome commands (`ApproveMediaItem`, `RejectMediaItem`) are dispatched by the `MediaItemReviewSaga`
- **Event stream prefix:** `mcr_`

---

## External Dependencies

| Dependency | Type | Usage |
|---|---|---|
| `Catalog` context | Event consumer | `MediaItemReviewSaga` observes `MediaItemSubmittedForReview` to trigger MCR creation |
| `Metadata` context | None direct | `ReviewPolicy` is defined on `MediaProfile` (Metadata context) but read by `Publish` handler in Catalog |

---

## Event Flows

### Inbound (triggers)

| Event | Source | Handling |
|---|---|---|
| `MediaItemCheckedOut` (with `CheckoutChangeRequestId`) | Catalog / MediaItem | `MediaItemCheckoutReviewSaga` dispatches `CreateCheckoutChangeRequestCommand` |
| `MediaItemSubmittedForReview` (with `CheckoutChangeRequestId`) | Catalog / MediaItem | `MediaItemReviewSaga` dispatches `ActivateChangeRequestForReviewCommand` |
| `MediaItemSubmittedForReview` (no `CheckoutChangeRequestId`, `ReviewPolicy = RequiredForPublish`) | Catalog / MediaItem | `MediaItemReviewSaga` dispatches `CreateMediaChangeRequestCommand` (legacy path) |
| `MediaItemCheckoutForceReleased` | Catalog / MediaItem | `MediaItemCheckoutReviewSaga` dispatches `AbandonChangeRequestCommand` if CR present |

### Outbound (emitted by this context)

| Event | Consumer |
|---|---|
| `ChangeRequestCreated` (`CheckoutBound`) | `MediaItemCheckoutReviewSaga` → tracks CR through checkout cycle |
| `ChangeRequestCreated` (`Open` / legacy) | `MediaItemReviewSaga` → dispatches `LinkMediaChangeRequest` to MediaItem |
| `ChangeRequestActivatedForReview` | Notifications → alerts reviewers; `MediaItemReviewSaga` → begins review wait |
| `ReviewerAssigned` | `MediaChangeRequestProjector` → updates `media-change-requests` |
| `ReviewApproved` | `MediaChangeRequestProjector`; may trigger `ChangeRequestApproved` auto-resolution |
| `ReviewRejected` + `ChangeRequestRejected` | `MediaItemReviewSaga` → dispatches `RejectMediaItem` |
| `ChangeRequestApproved` | `MediaItemReviewSaga` → dispatches `ApproveMediaItem` |
| `ChangeRequestAbandoned` | `MediaItemReviewSaga` → dispatches `RejectMediaItem(reason: "AllReviewersWithdrawn")` |
| `ReviewCommentAdded/Edited/Deleted` | `MediaChangeRequestProjector` → `media-change-request-comments` |

---

## Integration Events

### Published

Published inline by `ChangeRequestIntegrationEventPublisher` (`ChangeRequests.WriteModel`) immediately after the corresponding domain event is persisted. All events target the `media-integration-events` SNS topic.

| C# Record Type | Trigger Domain Event | Consumers |
|---|---|---|
| `ChangeRequestCreatedIntegrationEvent` | `ChangeRequestCreated` | SagaOrchestrator (`ChangeRequestCreatedSagaHandler` — routes to `MediaItemCheckoutReviewSaga` if `Binding = CheckoutBound`, else `MediaItemReviewSaga`); Catalog (`ChangeRequestCreatedEventHandler` → `ChangeRequestReference` index) |
| `ChangeRequestActivatedForReviewIntegrationEvent` | `ChangeRequestActivatedForReview` | Notifications (reviewer alert); SagaOrchestrator (`ChangeRequestActivatedSagaHandler` → `MediaItemReviewSaga` begins `AwaitingReview` state) |
| `ChangeRequestApprovedIntegrationEvent` | `ChangeRequestApproved` | SagaOrchestrator (`MediaChangeRequestApprovedSagaHandler` → dispatches `ApproveMediaItem`); Catalog (`ChangeRequestApprovedEventHandler` → `ChangeRequestReference` status → `Approved`) |
| `ChangeRequestRejectedIntegrationEvent` | `ChangeRequestRejected` | SagaOrchestrator (`MediaChangeRequestRejectedSagaHandler` → dispatches `RejectMediaItem`); Catalog (`ChangeRequestRejectedEventHandler` → `ChangeRequestReference` status → `Rejected`) |
| `ChangeRequestAbandonedIntegrationEvent` | `ChangeRequestAbandoned` | SagaOrchestrator (`MediaChangeRequestAbandonedSagaHandler` → dispatches `RejectMediaItem(reason: "AllReviewersWithdrawn")`); Catalog (`ChangeRequestAbandonedEventHandler` → `ChangeRequestReference` status → `Abandoned`) |

### Consumed

| Event | Source | Consumer | Handling |
|---|---|---|---|
| `MediaItemCheckedOutMessage` | Catalog | `MediaItemCheckedOutConsumer` (`ChangeRequests.WriteModel`) | When `CheckoutChangeRequestId` is present, dispatches `CreateCheckoutChangeRequestCommand`. No-op when null. |
| `MediaItemSubmittedForReviewMessage` | Catalog | `MediaItemSubmittedForReviewConsumer` (`ChangeRequests.WriteModel`) | When `CheckoutChangeRequestId` is present, dispatches `ActivateChangeRequestForReviewCommand`. When `ChangeRequestId` is present (legacy), dispatches `CreateMediaChangeRequestCommand`. No-op when both null. |
| `MediaItemCheckoutForceReleasedMessage` | Catalog | `MediaItemCheckoutForceReleasedConsumer` (`ChangeRequests.WriteModel`) | When `CheckoutChangeRequestId` is present, dispatches `AbandonChangeRequestCommand`. No-op when null. |

## Integration Event Contracts

### Published

#### `ChangeRequestCreatedIntegrationEvent`

**Publisher:** `ChangeRequestDomainEventMapper` — triggered by `ChangeRequestCreated`  
**SNS message type:** `media.changerequest.created`

```csharp
record ChangeRequestCreatedIntegrationEvent(
    string TenantId,
    string ChangeRequestId,
    string OwnerId,
    string MediaItemId,
    string Binding,           // "CheckoutBound" or "SubmissionBound" (legacy: "Open")
    DateTimeOffset CreatedAt,
    long EventVersion
);
```

> **Consumers:** `ChangeRequestCreatedSagaHandler` (SagaOrchestrator) — routes to `MediaItemCheckoutReviewSaga` when `Binding = CheckoutBound`, else `MediaItemReviewSaga`; `ChangeRequestCreatedEventHandler` (Integration Event Consumers Lambda → Catalog) — inserts `ChangeRequestReference`.

#### `ChangeRequestActivatedForReviewIntegrationEvent`

**Publisher:** `ChangeRequestDomainEventMapper` — triggered by `ChangeRequestActivatedForReview`  
**SNS message type:** `media.changerequest.activated-for-review`

```csharp
record ChangeRequestActivatedForReviewIntegrationEvent(
    string TenantId,
    string ChangeRequestId,
    string MediaItemId,
    string[] ReviewerIds,     // notified reviewers
    DateTimeOffset ActivatedAt,
    long EventVersion
);
```

> **Consumers:** Notifications (alerts reviewers); `ChangeRequestActivatedSagaHandler` (SagaOrchestrator → `MediaItemReviewSaga` enters `AwaitingReview` state).

#### `ChangeRequestApprovedIntegrationEvent`

**SNS message type:** `media.changerequest.approved`

```csharp
record ChangeRequestApprovedIntegrationEvent(
    string TenantId,
    string ChangeRequestId,
    string MediaItemId,
    DateTimeOffset ApprovedAt,
    long EventVersion
);
```

> **Consumers:** `MediaChangeRequestApprovedSagaHandler` (SagaOrchestrator) — dispatches `ApproveMediaItem` to Catalog; `ChangeRequestApprovedEventHandler` (Integration Event Consumers Lambda → Catalog) — updates `ChangeRequestReference` status → `Approved`.

#### `ChangeRequestRejectedIntegrationEvent`

**SNS message type:** `media.changerequest.rejected`

```csharp
record ChangeRequestRejectedIntegrationEvent(
    string TenantId,
    string ChangeRequestId,
    string MediaItemId,
    string RejectedByUserId,
    string RejectionReason,
    DateTimeOffset RejectedAt,
    long EventVersion
);
```

> **Consumers:** `MediaChangeRequestRejectedSagaHandler` (SagaOrchestrator) — dispatches `RejectMediaItem` to Catalog; `ChangeRequestRejectedEventHandler` (Integration Event Consumers Lambda → Catalog) — updates `ChangeRequestReference` status → `Rejected`.

#### `ChangeRequestAbandonedIntegrationEvent`

**SNS message type:** `media.changerequest.abandoned`

```csharp
record ChangeRequestAbandonedIntegrationEvent(
    string TenantId,
    string ChangeRequestId,
    string MediaItemId,
    DateTimeOffset AbandonedAt,
    long EventVersion
);
```

> Published when all reviewers have withdrawn (auto-resolution). **Consumers:** `MediaChangeRequestAbandonedSagaHandler` (SagaOrchestrator) — dispatches `RejectMediaItem(reason: "AllReviewersWithdrawn")`; `ChangeRequestAbandonedEventHandler` (Integration Event Consumers Lambda → Catalog) — updates `ChangeRequestReference` status → `Abandoned`.

### Consumed

#### `MediaItemCheckedOutMessage`

**Source:** Catalog context  
**SNS message type:** `media.mediaitem.checked-out`  
**Consumer:** `MediaItemCheckedOutConsumer` (`ChangeRequests.WriteModel`)

```csharp
record MediaItemCheckedOutMessage(
    string TenantId,
    string MediaItemId,
    string CheckedOutBy,
    string OwnerId,
    string? CheckoutChangeRequestId,   // present when WithChangeRequest = true
    string[]? ReviewerIds,             // present when CheckoutChangeRequestId is set
    DateTimeOffset CheckedOutAt,
    long EventVersion
);
```

**Behaviour:** When `CheckoutChangeRequestId` is non-null, dispatches `CreateCheckoutChangeRequestCommand(TenantId, CheckoutChangeRequestId, MediaItemId, OwnerId, InitiatedBy: CheckedOutBy, ReviewerIds, CheckedOutAt)`. No-op when null.

---

#### `MediaItemSubmittedForReviewMessage`

**Source:** Catalog context  
**Consumer:** `MediaItemSubmittedForReviewConsumer` (`ChangeRequests.WriteModel`)  

```csharp
record MediaItemSubmittedForReviewMessage(
    string TenantId,
    string MediaItemId,
    string OwnerId,
    string SubmittedBy,
    string? CheckoutChangeRequestId,   // present when CR-first checkout was used
    string? ChangeRequestId,           // present on legacy path (ReviewPolicy = RequiredForPublish, no checkout CR)
    string[]? InitialReviewerIds,      // present on legacy path only
    DateTimeOffset SubmittedAt,
    long EventVersion
);
```

**Behaviour:**
- `CheckoutChangeRequestId` non-null → dispatches `ActivateChangeRequestForReviewCommand(TenantId, CheckoutChangeRequestId)`. CR transitions `CheckoutBound → SubmissionBound`.
- `ChangeRequestId` non-null (legacy) → dispatches `CreateMediaChangeRequestCommand(TenantId, ChangeRequestId, MediaItemId, OwnerId, InitiatedBy: SubmittedBy, InitialReviewerIds, SubmittedAt)`.
- Both null (`ReviewPolicy = None`) → no-op.

---

#### `MediaItemCheckoutForceReleasedMessage`

**Source:** Catalog context  
**SNS message type:** `media.mediaitem.checkout-force-released`  
**Consumer:** `MediaItemCheckoutForceReleasedConsumer` (`ChangeRequests.WriteModel`)

```csharp
record MediaItemCheckoutForceReleasedMessage(
    string TenantId,
    string MediaItemId,
    string? CheckoutChangeRequestId,   // present when checkout had an associated CR
    string ReleasedBy,
    string Reason,
    DateTimeOffset ReleasedAt,
    long EventVersion
);
```

**Behaviour:** When `CheckoutChangeRequestId` is non-null, dispatches `AbandonChangeRequestCommand(TenantId, CheckoutChangeRequestId, Reason: "CheckoutForceReleased")`. No-op when null.

---

## Ubiquitous Language

| Term | Definition |
|---|---|
| `MediaChangeRequest` (MCR) | A single change request instance for one MediaItem checkout or submission cycle. |
| `CheckoutBound` | CR created at checkout time. Change is in progress. Reviewers not yet notified. |
| `SubmissionBound` | CR transitioned from `CheckoutBound` at submit time. Reviewers notified. Review cycle active. |
| `ActivateForReview` | Command that transitions a CR from `CheckoutBound → SubmissionBound` and notifies reviewers. |
| `Reviewer` | A user assigned to evaluate and decide on the MCR. Must not be the `InitiatedBy` user. |
| `InitiatedBy` | The user (`caller.sub`) who checked out or submitted the MediaItem. Immutable after creation. |
| `ReviewPolicy` | Setting on `MediaProfile`: `None` (auto-approve on submit) or `RequiredForPublish` (CR required at checkout). |
| Auto-resolution | MCR transitions to `Approved` or `Abandoned` automatically when no pending reviewers remain. |
| `CommentIndex` | In-memory dictionary in the aggregate: `(CommentId → (AuthorId, IsDeleted))`. Comment bodies live in the event store and `media-change-request-comments` only. |
| `ReviewerStatus` | `Pending → Approved / Rejected / Withdrawn` |
| `MediaChangeRequestStatus` | `CheckoutBound → SubmissionBound → Approved / Rejected / Abandoned` (CR-first path). `Open → Approved / Rejected / Abandoned` (legacy submit-time path). |

---

## Related

- [MediaChangeRequest Write Model](./aggregates/MediaChangeRequest/mediachangerequest.write-model.md)
- [MediaChangeRequest Read Model](./aggregates/MediaChangeRequest/mediachangerequest.read-model.md)
- [MediaChangeRequest API](./aggregates/MediaChangeRequest/mediachangerequest.api.md)
- [ChangeRequests Business Scenarios](./business-scenarios.md)
- [Catalog Context — MediaItem](../Catalog/aggregates/MediaItem/mediaitem.write-model.md)
- [System Spec — Saga Coordination](../../shared/system-spec.md#saga-coordination-patterns)
