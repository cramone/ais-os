# MediaChangeRequest — Read Model

_Context: `ChangeRequests`_
_Aggregate: `MediaChangeRequest`_

---

## Read Models

### `media-change-requests` (DynamoDB)

Summary table. Powers list queries by MediaItem and by owner.

| Field                  | Type      | Notes                                                                      |
| ---------------------- | --------- | -------------------------------------------------------------------------- |
| `PK`                   | `string`  | `TENANT#{TenantId}#{MediaChangeRequestId}`                                 |
| `TenantId`             | `string`  |                                                                            |
| `MediaChangeRequestId` | `string`  |                                                                            |
| `MediaItemId`          | `string`  | The MediaItem under review                                                 |
| `OwnerId`              | `string`  |                                                                            |
| `InitiatedBy`          | `string`  | `UserId` of the submitter                                                  |
| `Status`               | `string`  | `MediaChangeRequestStatus` enum                                            |
| `Binding`              | `string`  | `CheckoutBound` or `SubmissionBound`. Set from `ChangeRequestCreated`. Immutable. |
| `CommentCount`         | `int`     | Incremented on `ReviewCommentAdded`; decremented on `ReviewCommentDeleted` |
| `CreatedAt`            | `string`  |                                                                            |
| `ResolvedAt`           | `string?` | Set on terminal state transition                                           |
| `RejectionReason`      | `string?` | Populated from `MediaChangeRequestRejected` payload                        |
| `ProjectedVersion`     | `long`    | Idempotency guard                                                          |
| `EventId`              | `string`  |                                                                            |

**GSIs:**
- `MediaItemIndex` (`MediaItemId + CreatedAt`) — lists all MCRs for a given MediaItem
- `OwnerStatusIndex` (`OwnerId + Status + CreatedAt`) — open/resolved reviews by owner

### `media-change-request-detail` (DynamoDB)

Full detail. Powers `GET /media-change-requests/{id}`. Includes the full reviewer list which is omitted from the summary table.

All `media-change-requests` fields plus:

| Field        | Type       | Notes                                                                |
| ------------ | ---------- | -------------------------------------------------------------------- |
| `Reviewers`  | `object[]` | `[{ reviewerId, assignedAt, status, decidedAt?, decisionComment? }]` |
| `UpdatedAt`  | `string`   | Derived from last event timestamp                                    |

### `media-change-request-comments` (DynamoDB)

Threaded comment store. Powers comment list queries.

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#{MediaChangeRequestId}` |
| `SK` | `string` | `COMMENT#{CommentId}` |
| `TenantId` | `string` | |
| `MediaChangeRequestId` | `string` | |
| `CommentId` | `string` | |
| `AuthorId` | `string?` | Cleared to null on soft-delete |
| `Body` | `string?` | Cleared to `"[deleted]"` on soft-delete |
| `ParentCommentId` | `string?` | Null for top-level comments |
| `CreatedAt` | `string` | |
| `EditedAt` | `string?` | Set on `ReviewCommentEdited` |
| `IsDeleted` | `bool` | Set to `true` on `ReviewCommentDeleted` |
| `ProjectedVersion` | `long` | |
| `EventId` | `string` | |

**Comment storage rules:**
- Comment bodies are **never** embedded in `media-change-requests`
- All comment retrieval goes through `media-change-request-comments`
- Default pagination: `pageSize = 50`, max `pageSize = 100`, ordered by `CreatedAt` ascending

---

## Projection Handlers

### `MediaChangeRequestProjector`

**Trigger:** `media-projector` SQS queue
**Targets:** `media-change-requests`, `media-change-request-detail`, `media-change-request-comments`

| Event | Write |
|---|---|
| `MediaChangeRequestCreated` | INSERT `media-change-requests` (`status = CheckoutBound` or `Open` per `Binding`, `binding`, `commentCount = 0`); INSERT `media-change-request-detail` (`reviewers = initialReviewers[]`) |
| `ChangeRequestActivatedForReview` | UPDATE `media-change-requests` — `status = SubmissionBound`; UPDATE `media-change-request-detail` — same |
| `ReviewerAssigned` | UPDATE `media-change-request-detail` — append to `reviewers[]` |
| `ReviewerRemoved` | UPDATE `media-change-request-detail` — remove from `reviewers[]` |
| `ReviewApproved` | UPDATE `media-change-request-detail` — set `reviewers[].status = Approved`, `decidedAt` |
| `ReviewRejected` | UPDATE `media-change-request-detail` — set `reviewers[].status = Rejected`, `decidedAt` |
| `ReviewerWithdrawn` | UPDATE `media-change-request-detail` — set `reviewers[].status = Withdrawn`, `withdrawnAt` |
| `MediaChangeRequestApproved` | UPDATE `media-change-requests` — `status = Approved`, set `resolvedAt`; UPDATE `media-change-request-detail` — same |
| `MediaChangeRequestRejected` | UPDATE `media-change-requests` — `status = Rejected`, set `resolvedAt`, `rejectionReason`; UPDATE `media-change-request-detail` — same |
| `MediaChangeRequestAbandoned` | UPDATE `media-change-requests` — `status = Abandoned`, set `resolvedAt`; UPDATE `media-change-request-detail` — same |
| `ReviewCommentAdded` | INSERT `media-change-request-comments` row; UPDATE `media-change-requests` — `commentCount += 1`; UPDATE `media-change-request-detail` — `commentCount += 1` |
| `ReviewCommentEdited` | UPDATE `media-change-request-comments` — set `body = newBody`, set `editedAt` |
| `ReviewCommentDeleted` | UPDATE `media-change-request-comments` — `isDeleted = true`, clear `body` to `"[deleted]"`, clear `authorId`; UPDATE `media-change-requests` — `commentCount -= 1`; UPDATE `media-change-request-detail` — `commentCount -= 1` |

---

## Queries

| Query | Description |
|---|---|
| `GetMediaChangeRequestByIdQuery(TenantId, MediaChangeRequestId)` | Full detail including reviewer list and comment count |
| `ListMediaChangeRequestsByMediaItemQuery(TenantId, MediaItemId, PageToken?)` | All MCRs for a MediaItem (history) |
| `ListMediaChangeRequestsByOwnerQuery(TenantId, OwnerId, Status?, PageToken?)` | Owner's open/resolved reviews |
| `ListCommentsQuery(TenantId, MediaChangeRequestId, PageToken?)` | Paginated comment thread for a MCR |

---

## Query Handlers

Handlers extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and inject `IReadModelReader<T>` from `Magiq.Platform.ReadModel`. PK construction is handled by the framework. Handlers return DTOs only — no domain objects or event payloads cross the read boundary.

| Handler | Reader | Method |
|---|---|---|
| `GetChangeRequestByIdHandler` | `IReadModelReader<ChangeRequestDetailReadModel>` | `GetAsync(request, ct)` |
| `ListChangeRequestsByMediaItemHandler` | `IReadModelReader<ChangeRequestSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `ListChangeRequestsByOwnerHandler` | `IReadModelReader<ChangeRequestSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `ListChangeRequestCommentsHandler` | `IReadModelReader<ChangeRequestCommentReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `ChangeRequestSummaryReadModel`

Targets `media-change-requests` (DynamoDB). Powers list queries.

```csharp
record ChangeRequestSummaryReadModel(
    string TenantId,
    string ChangeRequestId,
    string MediaItemId,
    ChangeRequestStatus Status,
    ChangeRequestBinding Binding,
    string OwnerId,
    DateTimeOffset CreatedAt,
    DateTimeOffset? ResolvedAt,
    long ProjectedVersion) : IReadModel;
```

### `ChangeRequestDetailReadModel`

Targets `media-change-request-detail` (DynamoDB). Powers `GetMediaChangeRequestById`. Includes full reviewer list.

```csharp
record ChangeRequestDetailReadModel(
    string TenantId,
    string ChangeRequestId,
    string OwnerId,
    string MediaItemId,
    ChangeRequestStatus Status,
    ChangeRequestBinding Binding,
    List<ReviewerDto> Reviewers,
    int CommentCount,
    string? RejectionReason,
    DateTimeOffset? ResolvedAt,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

### `ChangeRequestCommentReadModel`

Targets `media-change-request-comments` (DynamoDB). Powers `ListComments`.

```csharp
record ChangeRequestCommentReadModel(
    string CommentId,
    string TenantId,
    string ChangeRequestId,
    string AuthorId,
    string Body,
    string? ParentCommentId,
    DateTimeOffset AddedAt,
    DateTimeOffset? EditedAt,
    bool IsDeleted,
    long ProjectedVersion) : IReadModel;
```

### Embedded Types

```csharp
record ReviewerDto(
    string ReviewerId,
    ReviewerStatus Status, 
    DateTimeOffset AssignedAt,
    DateTimeOffset? DecidedAt,
    string? DecisionComment);
    
enum ReviewerStatus  
{  
    Pending,  
    Approved,  
    Rejected,  
    Withdrawn  
}

public enum ChangeRequestStatus  
{  
    CheckoutBound,   // CR created at checkout; change in progress; reviewers not yet notified
    SubmissionBound, // CR activated at submit; reviewers notified; review cycle active
    Open,            // Legacy submit-time CR (ReviewPolicy = RequiredForPublish, no checkout CR)
    Approved,        // All non-withdrawn reviewers approved; ≥1 approval  
    Rejected,        // Any reviewer rejected; immediate  
    Abandoned        // All reviewers withdrew with zero approvals; or force-released  
}

public enum ChangeRequestBinding
{
    CheckoutBound,   // Created at checkout time
    SubmissionBound  // Created at submit time (legacy path)
}
```

---

## Related

- [MediaChangeRequest Write Model](./mediachangerequest.write-model.md)
- [MediaChangeRequest API](./mediachangerequest.api.md)
- [System Spec — Storage Boundaries](../../../../shared/system-spec.md#storage-boundaries)
