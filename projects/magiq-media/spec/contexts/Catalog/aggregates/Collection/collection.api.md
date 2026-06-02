# Collection — API

_Context: `Catalog`_
_Aggregate: `Collection`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints.
- **Idempotency:** All mutating endpoints (POST, PUT, PATCH, DELETE) accept `IdempotencyKey: <uuid>`. Replaying the same key within the TTL returns the cached response. See [§Idempotency](../../../../shared/api-conventions.md#idempotency).
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457 `ProblemDetails`). See [§Error Contract](../../../../shared/api-conventions.md#error-contract--rfc-9457-problemdetails).

---

## Route Structure

```
POST   /v1/catalog/collections                                          Create
POST   /v1/catalog/collections/bulk                                     Bulk create
PATCH  /v1/catalog/collections/{collectionId}                           Update name / description / visibility
PUT    /v1/catalog/collections/{collectionId}/default-profile           Set default media-profile
POST   /v1/catalog/collections/{collectionId}/tags                      Replace tag list
POST   /v1/catalog/collections/{collectionId}/archive                   Archive
GET    /v1/catalog/collections/{collectionId}                           Get detail
GET    /v1/catalog/collections?ownerId=                                 List for owner
GET    /v1/catalog/collections/public                                   List public (unauthenticated)
```

---

## Authorization

| Endpoint | Requirement |
|---|---|
| Write endpoints | `caller.owner_id == collection.OwnerId` |
| `GET /v1/catalog/collections/{id}` | Owner or public visibility |
| `GET /v1/catalog/collections?ownerId=` | `caller.owner_id == ownerId` |

---

## Write Endpoints (Ingest API)

### `POST /v1/catalog/collections`

**Request:**
```json
{
  "collectionId": "018e4c7a-...",
  "name": "Q1 Campaign Assets",
  "description": "Assets for Q1 marketing campaign",
  "visibility": "Private",
  "defaultMediaProfileId": "018e4c7b-..."
}
```
`collectionId` is caller-generated (UUID v7).
`defaultMediaProfileId` optional — must be a `Published` MediaProfile.

**Response `201 Created`:**
```json
{ "id": "018e4c7a-..." }
```

**Errors:** `400`, `401`, `409` (if collectionId already exists for this owner)

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/collection-already-exists",
  "title": "Collection already exists",
  "status": 409,
  "detail": "A media-collection with id 018e4c7a-... already exists for this owner.",
  "extensions": { "errorCode": "CollectionAlreadyExists" }
}
```

---

### `PATCH /v1/catalog/collections/{collectionId}`

Partial update — any combination of `name`, `description`, `visibility`.

**Request:**
```json
{
  "name": "Q2 Campaign Assets",
  "description": "Updated description",
  "visibility": "Public"
}
```

**Response `204 No Content`** — no body.

**Errors:** `400`, `401`, `403`, `404`, `409` (archived)

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — archived):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/collection-archived",
  "title": "Collection is archived",
  "status": 409,
  "detail": "Collection 018e4c7a-... is archived and cannot be modified.",
  "extensions": { "errorCode": "CollectionArchived" }
}
```

---

### `PUT /v1/catalog/collections/{collectionId}/default-profile`

Sets the default `MediaProfile` for new media-items created in this media-collection. Must be a `Published` MediaProfile owned by the same owner.

**Request:**
```json
{ "mediaProfileId": "018e4c7c-..." }
```

**Response `204 No Content`** — no body.

**Errors:** `404` (media-collection or media-profile not found), `409` (archived), `422` (media-profile not Published or wrong owner)

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity`):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/profile-not-published",
  "title": "Media profile is not published",
  "status": 422,
  "detail": "MediaProfile 018e4c7c-... is in status Draft and cannot be set as the default media-profile.",
  "extensions": { "errorCode": "MediaProfileNotPublished" }
}
```

---

### `POST /v1/catalog/collections/{collectionId}/tags`

Replaces the entire tag list (full replacement, no append semantics).

**Request:**
```json
{ "tags": ["campaign", "q1", "approved"] }
```

**Response `204 No Content`** — no body.

_Accepts `IdempotencyKey` header._

**Error response example (`403 Forbidden`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/not-resource-owner",
  "title": "Not the resource owner",
  "status": 403,
  "detail": "Caller owner_B does not own Collection 018e4c7a-...",
  "extensions": { "errorCode": "NotResourceOwner" }
}
```

---

### `POST /v1/catalog/collections/{collectionId}/archive`

Soft-archives the media-collection. No write-side cascade.

**Response `204 No Content`** — no body.

**Errors:** `409` (already archived)

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/collection-already-archived",
  "title": "Collection is already archived",
  "status": 409,
  "detail": "Collection 018e4c7a-... is already in Archived status.",
  "extensions": { "errorCode": "CollectionAlreadyArchived" }
}
```

---

## Read Endpoints (Query API)

### `GET /v1/catalog/collections/{collectionId}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "ownerId": "owner_...",
  "name": "Q1 Campaign Assets",
  "description": "...",
  "visibility": "Private",
  "tags": ["campaign"],
  "defaultMediaProfileId": "018e4c7b-...",
  "isArchived": false,
  "createdAt": "2026-03-26T10:00:00Z"
}
```

---

### `GET /v1/catalog/collections?ownerId={ownerId}&pageToken=&pageSize=`

**Response `200 OK`:**
```json
{
  "collections": [ { "id": "...", "name": "...", "visibility": "Private", "isArchived": false, "createdAt": "..." } ],
  "nextPageToken": null
}
```

---

### `GET /v1/catalog/collections/public`

Returns publicly visible media-collections across all owners. No authentication required. Accepts optional `?pageToken=&pageSize=` params.

**Response `200 OK`:**
```json
{
  "collections": [ { "id": "...", "name": "...", "ownerId": "...", "visibility": "Public", "createdAt": "..." } ],
  "nextPageToken": null
}
```

---

## Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/collections` | `CreateCollectionCommand` | `CollectionCreated` | `CollectionProjector` → INSERT |
| `PATCH /v1/catalog/collections/{id}` (name) | `RenameCollectionCommand` | `CollectionRenamed` | `CollectionProjector` → UPDATE |
| `PATCH /v1/catalog/collections/{id}` (description) | `UpdateCollectionDescriptionCommand` | `CollectionDescriptionUpdated` | `CollectionProjector` → UPDATE `Description` |
| `PATCH /v1/catalog/collections/{id}` (visibility) | `SetCollectionVisibilityCommand` | `CollectionVisibilityChanged` | `CollectionProjector` → UPDATE + OpenSearch |
| `POST /v1/catalog/collections/{id}/tags` | `TagCollectionCommand` | `CollectionTagged` | `CollectionProjector` → UPDATE |
| `POST /v1/catalog/collections/{id}/archive` | `ArchiveCollectionCommand` | `CollectionArchived` | `CollectionProjector` → UPDATE `IsArchived`, `ArchivedAt` |
| `PUT /v1/catalog/collections/{id}/default-profile` | `SetDefaultMediaProfileCommand` | `CollectionDefaultProfileSet` | `CollectionProjector` → UPDATE |
| `GET /v1/catalog/collections/{id}` | `GetCollectionByIdQuery` | — | reads `media-collection-detail` |
| `GET /v1/catalog/collections/public` | `ListPublicCollectionsQuery` | — | reads `media-collections` (visibility filter) |

---

## Related

- [Collection Write Model](./media-collection.write-model.md)
- [Collection Read Model](./media-collection.read-model.md)

---

## Bulk Write Endpoints

> Bulk operations follow the shared partial-success envelope. See [`spec/shared/bulk-operations.md`](../../../../shared/bulk-operations.md) for the full conventions: `onError`, `onDuplicate`, `BulkItemError`, retry behaviour, and idempotency.

### `POST /v1/catalog/collections/bulk`

Creates up to 100 media-collections in a single request. Per-item name uniqueness is checked in a single `BatchGetItem` call (Tier 1) before any writes begin. The `onDuplicate` strategy determines handling for names already in use.

**Request:**
```json
{
  "items": [
    {
      "collectionId": "018f...",
      "name": "Q1 Campaign Assets",
      "description": "Assets for Q1 marketing campaign",
      "visibility": "Private",
      "defaultMediaProfileId": null
    },
    {
      "collectionId": "018g...",
      "name": "Brand Library",
      "visibility": "Public"
    }
  ],
  "onError": "ContinueOnError",
  "onDuplicate": "Reject"
}
```

`collectionId` is caller-generated (UUID v7). If omitted, the server generates one.  
`defaultMediaProfileId` is optional — must be a `Published` MediaProfile.

**Response `201 Created`** — all media-items succeeded:
```json
{
  "succeeded": [
    { "index": 0, "id": "018f...", "name": "Q1 Campaign Assets" },
    { "index": 1, "id": "018g...", "name": "Brand Library" }
  ],
  "failed": [],
  "skipped": []
}
```

**Response `202 Accepted`** — partial results:
```json
{
  "succeeded": [
    { "index": 0, "id": "018f...", "name": "Q1 Campaign Assets" }
  ],
  "failed": [
    {
      "index": 1,
      "name": "Brand Library",
      "errorCode": "DuplicateName",
      "message": "A media-collection named 'Brand Library' already exists.",
      "suggestedName": "Brand Library (1)"
    }
  ],
  "skipped": []
}
```

**Errors (request-level):**
- `400` — batch exceeds 100 media-items, or a required field is missing/malformed
- `401` — unauthenticated
- `403` — permission denied

**Per-item error codes:**

| `errorCode` | Cause |
|---|---|
| `DuplicateName` | Name already taken in this tenant scope (only when `onDuplicate = Reject`) |
| `AutoSuffixExhausted` | 99 suffix attempts all taken (only when `onDuplicate = AutoSuffix`) |
| `NameReservationFailed` | Concurrent writer claimed the name after pre-flight; retries exhausted |

_Accepts `IdempotencyKey` header._

---

## Updated Command → Event → Projection Traceability

_(Existing table entries unchanged — appended below)_

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/collections/bulk` | `BulkCreateCollectionsCommand` | `CollectionCreated` (×N) | `Collecti