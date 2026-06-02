# MediaChangeRequest — API

_Context: `ChangeRequests`_
_Aggregate: `MediaChangeRequest`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints.
- **Idempotency:** All mutating endpoints (POST, PUT, PATCH, DELETE) accept `IdempotencyKey: <uuid>`. Replaying the same key within the TTL returns the cached response. See [§Idempotency](../../../../shared/api-conventions.md#idempotency).
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457 `ProblemDetails`). See [§Error Contract](../../../../shared/api-conventions.md#error-contract--rfc-9457-problemdetails).

---

## Overview

`MediaChangeRequest` is a comment thread attached to a MediaItem review cycle. The API exposes only thread creation and comment management. Review decisions (approve/reject) are made directly on the MediaItem via `POST /catalog/items/{id}/approve` and `POST /catalog/items/{id}/reject`.

---

## Route Structure

```
POST   /v1/change-requests                                   Create comment thread
POST   /v1/change-requests/{changeRequestId}/comments        Add comment
PATCH  /v1/change-requests/{changeRequestId}/comments/{commentId}  Edit comment
DELETE /v1/change-requests/{changeRequestId}/comments/{commentId}  Delete comment

GET    /v1/change-requests/{changeRequestId}                 Get detail
GET    /v1/change-requests?itemId=                           List by MediaItem
GET    /v1/change-requests/{changeRequestId}/comments        List comments
GET    /v1/change-requests/{changeRequestId}/comments/{commentId}  Get single comment
```

---

## Authorization

| Endpoint | Requirement |
|---|---|
| `POST /v1/change-requests` | Caller must be owner of the linked MediaItem |
| `POST /v1/change-requests/{id}/comments` | Caller must be owner or assigned reviewer of the linked MediaItem |
| `PATCH /v1/change-requests/{id}/comments/{commentId}` | Original comment author only |
| `DELETE /v1/change-requests/{id}/comments/{commentId}` | Original comment author only |
| Read endpoints | Owner or assigned reviewer of the linked MediaItem |

---

## Write Endpoints

### `POST /v1/change-requests`

Creates a comment thread for a MediaItem review. Typically created at submit time and linked via `commentThreadId` in `POST /catalog/items/{id}/submit`.

**Request:**
```json
{
  "changeRequestId": "018e4c7a-...",
  "mediaItemId": "018e4c7b-..."
}
```

`changeRequestId` is caller-generated (UUID v7).

**Response `201 Created`:**
```json
{ "id": "018e4c7a-..." }
```

**Errors:**
- `403` — caller does not own the linked MediaItem
- `404` — MediaItem not found

_Accepts `IdempotencyKey` header._

---

### `POST /v1/change-requests/{changeRequestId}/comments`

**Request:**
```json
{
  "commentId": "018e4c7a-...",
  "body": "The title field looks truncated in the metadata.",
  "parentCommentId": null
}
```

`commentId` is caller-generated (UUID v7). `parentCommentId` is optional (threaded reply).

**Response `201 Created`** — no body.

**Errors:**
- `403` — caller is not owner or an assigned reviewer of the linked MediaItem
- `404` — `parentCommentId` not found or already deleted

_Accepts `IdempotencyKey` header._

**Error response example (`404 Not Found` — parent comment deleted):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/comment-not-found",
  "title": "Parent comment not found",
  "status": 404,
  "detail": "Comment cm-01 was not found or has been deleted.",
  "extensions": { "errorCode": "CommentNotFound" }
}
```

---

### `PATCH /v1/change-requests/{changeRequestId}/comments/{commentId}`

**Request:**
```json
{ "body": "The title field is truncated after 80 characters." }
```

**Response `204 No Content`** — no body.

**Errors:**
- `403` — caller is not the original comment author
- `404` — comment not found or already deleted

_Accepts `IdempotencyKey` header._

**Error response example (`403 Forbidden`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/not-comment-author",
  "title": "Not the comment author",
  "status": 403,
  "detail": "Only the original author of comment cm-01 may edit it.",
  "extensions": { "errorCode": "NotCommentAuthor" }
}
```

---

### `DELETE /v1/change-requests/{changeRequestId}/comments/{commentId}`

Soft-deletes the comment. Permitted at any time — no lifecycle gate.

**Response `204 No Content`** — no body.

**Errors:**
- `403` — caller is not the original comment author
- `404` — comment not found or already deleted

_Accepts `IdempotencyKey` header._

**Error response example (`404 Not Found`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/comment-not-found",
  "title": "Comment not found",
  "status": 404,
  "detail": "Comment cm-01 was not found or has already been deleted.",
  "extensions": { "errorCode": "CommentNotFound" }
}
```

---

## Read Endpoints

### `GET /v1/change-requests/{changeRequestId}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "mediaItemId": "018e4c7b-...",
  "createdById": "user_...",
  "commentCount": 2,
  "createdAt": "2026-03-26T10:00:00Z"
}
```

---

### `GET /v1/change-requests?itemId={id}`

```json
{
  "changeRequests": [
    {
      "id": "018e4c7a-...",
      "mediaItemId": "018e4c7b-...",
      "createdAt": "2026-03-26T09:00:00Z"
    }
  ],
  "nextPageToken": null
}
```

---

### `GET /v1/change-requests/{changeRequestId}/comments`

**Query params:** `pageToken?`, `pageSize?` (default 50, max 100)

```json
{
  "comments": [
    {
      "id": "cm-01",
      "authorId": "user_alice",
      "body": "The title field looks truncated in the metadata.",
      "parentCommentId": null,
      "createdAt": "2026-03-26T10:05:00Z",
      "editedAt": null,
      "isDeleted": false
    },
    {
      "id": "cm-02",
      "authorId": "owner_...",
      "body": "Good catch — will fix before resubmit.",
      "parentCommentId": "cm-01",
      "createdAt": "2026-03-26T10:10:00Z",
      "editedAt": null,
      "isDeleted": false
    }
  ],
  "nextPageToken": null
}
```

---

### `GET /v1/change-requests/{changeRequestId}/comments/{commentId}`

Returns a single comment by ID. Returns `404` if soft-deleted.

**Response `200 OK`:**
```json
{
  "id": "cm-01",
  "changeRequestId": "018e4c7a-...",
  "authorId": "user_alice",
  "body": "The title field looks truncated in the metadata.",
  "parentCommentId": null,
  "addedAt": "2026-03-26T10:05:00Z",
  "editedAt": null,
  "isDeleted": false
}
```

**Errors:** `401` · `403` · `404`

---

## Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/change-requests` | `CreateChangeRequestCommand` | `ChangeRequestCreated` | `MediaChangeRequestProjector` → INSERT |
| `POST /comments` | `AddCommentCommand` | `ReviewCommentAdded` | `ChangeRequestCommentProjector` → INSERT; `commentCount += 1` |
| `PATCH /comments/{id}` | `EditCommentCommand` | `ReviewCommentEdited` | `ChangeRequestCommentProjector` → UPDATE body, editedAt |
| `DELETE /comments/{id}` | `DeleteCommentCommand` | `ReviewCommentDeleted` | `ChangeRequestCommentProjector` → isDeleted=true; `commentCount -= 1` |
| `GET /v1/change-requests/{id}` | `GetChangeRequestByIdQuery` | — | reads `media-change-requests` |
| `GET /v1/change-requests/{id}/comments` | `ListChangeRequestCommentsQuery` | — | reads `media-change-request-comments` |
| `GET /v1/change-requests/{id}/comments/{commentId}` | `GetChangeRequestCommentQuery` | — | reads `media-change-request-comments` by `{ChangeRequestId}#{CommentId}` |

---

## Related

- [MediaChangeRequest Write Model](./mediachangerequest.write-model.md)
- [MediaChangeRequest Read Model](./mediachangerequest.read-model.md)
- [ChangeRequests Business Scenarios](../../business-scenarios.md)
- [MediaItem API](../../../Catalog/aggregates/MediaItem/mediaitem.api.md) — approve/reject endpoints
