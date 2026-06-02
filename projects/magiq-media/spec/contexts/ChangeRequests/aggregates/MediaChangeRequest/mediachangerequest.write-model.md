# MediaChangeRequest — Write Model

_Context: `ChangeRequests`_
_Aggregate: `MediaChangeRequest`_
_Stream prefix: `mcr_`_

---

## Overview

ChangeRequest is a comment thread attached to a MediaItem review cycle. It has no lifecycle status of its own — it exists to provide a comment space during review. Review decisions (approve/reject) are recorded directly on the `MediaItem` aggregate via its embedded `ReviewSession`.

> **System-created.** ChangeRequests are created automatically by the system when a MediaItem is published with reviewers. Clients do not call `CreateChangeRequest` directly — the `MediaItemPublicationRequestedEventHandler` creates the thread and passes the pre-generated `ChangeRequestId` back to the publish response as `commentThreadId`.

---

## State

| Property | Type | Description |
|---|---|---|
| `ChangeRequestId` | `GUID` | Unique identifier |
| `TenantId` | `GUID` | Tenant scope |
| `MediaItemId` | `GUID` | Owning media item |
| `CreatedById` | `GUID` | User who created the thread |
| `ReviewSessionId` | `string` | ID of the linked `ReviewSession` on `MediaItem` |
| `ParticipantIds` | `IReadOnlyList<MemberId>` | Snapshot of participants (submitter + reviewers) at creation time |
| `Comments` | `IReadOnlyList<CommentIndex>` | Validation-only index — `(CommentId, AuthorId, IsDeleted)` tuples. Bodies live in the event store and `media-change-request-comments`. |

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| Commenter must be a review participant (owner or assigned reviewer) | `Forbidden` | `AddComment` |
| `ParentCommentId` (if set) references existing, non-deleted comment | `CommentNotFound` / `CommentDeleted` | `AddComment` |
| `CommentId` exists and is not deleted | `CommentNotFound` / `CommentDeleted` | `EditComment` |
| Caller is original comment author | `CommentAuthorMismatch` | `EditComment`, `DeleteComment` |
| Body is non-empty, max 4 000 chars | `InvalidCommentBody` | `AddComment`, `EditComment` |

---

## Operations

### AddComment
- Body required (non-empty, max 4 000 chars)
- Any participant may comment (handler-side participant check)
- `ParentCommentId` optional — enables threaded replies

### EditComment
- Author only
- Body required (non-empty)
- Cannot edit a deleted comment
- `OldBody` supplied by handler from `ICommentReadModel`

### DeleteComment
- Author only
- Soft delete — comment body cleared to `"[deleted]"`, `IsDeleted = true`
- No Status gate — permitted at any time

---

## Value Objects

| Value Object | Description |
|---|---|
| `ChangeRequestId` | UUID v7 string, immutable |
| `CommentId` | UUID v7 string, caller-generated |
| `CommentBody` | Non-empty string, max 4 000 chars, regex `^[^\x00-\x08\x0B\x0C\x0E-\x1F\x7F]{1,4000}$` (LF, CR, TAB permitted) |

---

## Methods (Commands)

| Method | Description |
|---|---|
| `MediaChangeRequest.Create(tenantId, id, mediaItemId, createdById)` | Factory. Raises `ChangeRequestCreated`. |
| `AddComment(commentId, authorId, body, parentCommentId?)` | Any participant adds a comment. Guard: valid parent if threaded. |
| `EditComment(commentId, callerId, oldBody, newBody)` | Author edits their comment. Guard: not deleted; caller == author. `OldBody` supplied by handler from `ICommentReadModel`. |
| `DeleteComment(commentId, callerId)` | Author soft-deletes comment. Guard: not deleted; caller == author. |

---

## Domain Events

| Event | Key Payload Fields | Notes |
|---|---|---|
| `ChangeRequestCreated` | `TenantId`†, `ChangeRequestId`, `MediaItemId`, `CreatedById`, `CreatedAt` | Thread created |
| `ReviewCommentAdded` | `ChangeRequestId`, `CommentId`, `AuthorId`, `Body`, `ParentCommentId?`, `CreatedAt` | Full body in event — projected to `media-change-request-comments` |
| `ReviewCommentEdited` | `ChangeRequestId`, `CommentId`, `OldBody`, `NewBody`, `EditedAt` | `OldBody` from `ICommentReadModel` (not in aggregate state) |
| `ReviewCommentDeleted` | `ChangeRequestId`, `CommentId`, `DeletedAt` | Soft-delete — `isDeleted = true` in projector; body cleared to `"[deleted]"` |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command | Notes |
|---|---|
| `CreateChangeRequestCommand(ChangeRequestId, MediaItemId, CreatedById)` | User-facing — caller creates a comment thread for a review. |
| `AddCommentCommand(ChangeRequestId, CommentId, CallerUserId, Body, ParentCommentId?)` | `CommentId` caller-generated (UUID v7). |
| `EditCommentCommand(ChangeRequestId, CommentId, CallerUserId, NewBody)` | Handler reads `OldBody` from `ICommentReadModel`. |
| `DeleteCommentCommand(ChangeRequestId, CommentId, CallerUserId)` | Soft-delete. |

---

## Handler Pre-conditions

| Handler | Pre-condition | Error |
|---|---|---|
| `AddCommentHandler` | Caller is owner or participant of the linked `MediaItem` | `CommentAuthorNotParticipant` |
| `EditCommentHandler` | Same participant check; `ICommentReadModel.GetBodyAsync` returns non-null | `CommentAuthorNotParticipant` / `CommentNotFound` |
| `DeleteCommentHandler` | No participant check; authorship is aggregate-side only | n/a |

---

## Write Model Service Interfaces

```csharp
// Used by EditCommentHandler only.
// Comment bodies are not stored in aggregate state — handler reads current body
// to supply OldBody to the aggregate for event payload completeness.
interface ICommentReadModel {
    Task<string?> GetBodyAsync(
        ChangeRequestId changeRequestId,
        CommentId commentId,
        CancellationToken ct);
}
```

---

## Published Integration Events

Published inline by `ChangeRequestIntegrationEventPublisher` (`ChangeRequests.WriteModel`) immediately after the domain event is persisted.

| Integration Event | Source Domain Event | Notes |
|---|---|---|
| `ChangeRequestCreatedIntegrationEvent` | `ChangeRequestCreated` | Consumed by Notifications |

Comment events (`ReviewCommentAdded`, `ReviewCommentEdited`, `ReviewCommentDeleted`) are domain-internal only — they do not cross module boundaries.

---

## Design Notes

**Comment bodies never in aggregate state:** `Comments` holds only `(CommentId, AuthorId, IsDeleted)` tuples needed for command validation. Bodies live in the event store and are projected to `media-change-request-comments`. This prevents DynamoDB's 400 KB item limit from being breached on high-volume or long-running reviews.

**`DeleteComment` is status-agnostic:** Authors may soft-delete comments at any time.

**No lifecycle, no reviewers:** All review decision logic (approve/reject) lives on `MediaItem` via its embedded `ReviewSession`. `MediaChangeRequest` is a pure comment thread.

---

## Reference Models

### `media-change-request-comments` (DynamoDB)

**Owned by:** ChangeRequests (same context — internal projection)
**Consumed via:** `ICommentReadModel` (`GetBodyAsync`)
**Used by:** `EditCommentHandler` — comment bodies are intentionally excluded from aggregate state to avoid the DynamoDB 400 KB item limit on high-volume reviews.

| Field | Type | Purpose |
|---|---|---|
| `ChangeRequestId` | `string` | Partition key |
| `CommentId` | `string` | Sort key |
| `Body` | `string` | Current comment text — supplied as `OldBody` in event payload |
| `IsDeleted` | `bool` | `GetBodyAsync` returns null for deleted comments → `CommentNotFound` error |

**Subscribed events (same-context projection — `media-projector` SQS queue):**

| Event | Write |
|---|---|
| `ReviewCommentAdded` | INSERT `{CommentId, Body, IsDeleted = false}` |
| `ReviewCommentEdited` | UPDATE `Body` |
| `ReviewCommentDeleted` | UPDATE `IsDeleted = true` |

---

## Related

- [MediaChangeRequest Read Model](./mediachangerequest.read-model.md)
- [MediaChangeRequest API](./mediachangerequest.api.md)
- [ChangeRequests Business Scenarios](../../business-scenarios.md)
- [MediaItem Write Model](../../../Catalog/aggregates/MediaItem/mediaitem.write-model.md)
