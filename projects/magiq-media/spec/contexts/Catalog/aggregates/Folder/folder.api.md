# Folder — API

_Context: `Catalog`_
_Aggregate: `Folder`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints.
- **Idempotency:** All mutating endpoints (POST, PUT, PATCH, DELETE) accept `IdempotencyKey: <uuid>`. Replaying the same key within the TTL returns the cached response. See [§Idempotency](../../../../shared/api-conventions.md#idempotency).
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457 `ProblemDetails`). See [§Error Contract](../../../../shared/api-conventions.md#error-contract--rfc-9457-problemdetails).

> **Route pattern note (R-46):** Folder creation uses a nested route (`POST /v1/catalog/collections/{collectionId}/folders`) because the parent collection is required at creation time. All subsequent individual folder operations use the flat route (`/v1/catalog/folders/{folderId}`) because the collection context is already encoded in the resource. This is intentional — see [§Route Pattern](../../../../shared/api-conventions.md#route-pattern--nested-creation-flat-operations).

---

## Route Structure

```
POST   /v1/catalog/collections/{collectionId}/folders
POST   /v1/catalog/collections/{collectionId}/folders/bulk
POST   /v1/catalog/collections/{collectionId}/folders/bulk-paths
POST   /v1/catalog/collections/{collectionId}/folders/import
GET    /v1/catalog/collections/{collectionId}/folders/hierarchy?nameContains=
PATCH  /v1/catalog/folders/{folderId}
PATCH  /v1/catalog/folders/{folderId}/description
PUT    /v1/catalog/folders/{folderId}/parent
POST   /v1/catalog/folders/{folderId}/archive
POST   /v1/catalog/folders/{folderId}/close
PATCH  /v1/catalog/folders/{folderId}/metadata/{fieldName}
PUT    /v1/catalog/folders/{folderId}/metadata
POST   /v1/catalog/folders/{folderId}/metadata/commit
GET    /v1/catalog/folders/{folderId}
GET    /v1/catalog/folders/{folderId}/children?sortBy=&sortOrder=
GET    /v1/catalog/folders?collectionId=&parentFolderId=
```

---

## Write Endpoints

### `POST /v1/catalog/collections/{collectionId}/folders`

**Request:**
```json
{
  "parentFolderId": null,
  "name": "Hero Images",
  "description": "Campaign hero shots",
  "openedDate": "2026-01-01T00:00:00Z",
  "closedDate": null
}
```

`openedDate` — optional business date the folder was opened (e.g. start of a project or reporting period).  
`closedDate` — optional business date the folder was closed. Can be supplied at creation for pre-closed or imported folders.

**Response `201 Created`:**
```json
{
  "id": "018e4c7a-...",
  "name": "Hero Images",
  "description": "Campaign hero shots",
  "collectionId": "018e4c7b-...",
  "parentFolderId": null,
  "createdAt": "2026-06-07T10:00:00Z",
  "openedDate": "2026-01-01T00:00:00Z",
  "closedDate": null
}
```

**Errors:** `400`, `401`, `404` (collectionId or parentFolderId not found), `409` (depth > 10 or name taken)

_Accepts `IdempotencyKey` header._

---

### `PATCH /v1/catalog/folders/{folderId}`

Renames and/or updates the description of the folder (partial update).

**Request:**
```json
{
  "name": "Banner Images",
  "description": "Q2 banner assets"
}
```

Both fields are optional. Omitting a field leaves it unchanged. Setting `description` to `null` clears it.

**Response `204 No Content`**

**Errors:** `400` (neither field supplied), `404`, `409` (name taken in scope)

_Accepts `IdempotencyKey` header._

---

### `PATCH /v1/catalog/folders/{folderId}/description`

Updates only the folder description.

**Request:**
```json
{ "description": "Hero and banner images for Q2 campaign" }
```

**Response `204 No Content`**

_Accepts `IdempotencyKey` header._

---

### `PUT /v1/catalog/folders/{folderId}/parent`

**Request:**
```json
{
  "newParentFolderId": "018e4c7c-..."
}
```

Set `newParentFolderId: null` to move to collection root.

**Response `204 No Content`**

**Errors:** `409` (depth > 10), `422` (circular reference or cross-collection move)

_Accepts `IdempotencyKey` header._

---

### `POST /v1/catalog/folders/{folderId}/archive`

Archives the folder and cascades to all descendants and media items. Blocked if any item in the subtree has an active registration.

**Response `204 No Content`**

**Errors:** `404`, `409` (already archived or active registrations in subtree)

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — already archived):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/folder-already-archived",
  "title": "Folder already archived",
  "status": 409,
  "detail": "Folder 018e4c7a-... is already archived.",
  "extensions": { "errorCode": "FolderAlreadyArchived" }
}
```

---

### `POST /v1/catalog/folders/{folderId}/close`

Marks the folder as closed. Records the system timestamp (`closedAt`) and an optional business-supplied `closedDate`. Closing does not affect the folder's archived status and does not cascade to children.

**Request:**
```json
{
  "closedDate": "2026-03-31T00:00:00Z"
}
```

`closedDate` is optional. Omit to close with no business date (system timestamp only).

**Response `204 No Content`**

**Errors:** `404`, `409` (already closed)

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — already closed):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/folder-already-closed",
  "title": "Folder already closed",
  "status": 409,
  "detail": "Folder 018e4c7a-... is already closed.",
  "extensions": { "errorCode": "FolderAlreadyClosed" }
}
```

---

### `PATCH /v1/catalog/folders/{folderId}/metadata/{fieldName}`

Sets a single metadata field on the folder. The value is written to the draft; call `/metadata/commit` to promote.

**Request:**
```json
{
  "value": "Campaign 2026",
  "fieldType": "String",
  "attributedTo": null,
  "attributedDate": null
}
```

`fieldType` — required. One of: `Boolean`, `Integer`, `IntegerArray`, `Number`, `NumberArray`, `String`, `StringArray`, `Text`, `Date`, `DateTime`.

**Response `204 No Content`**

**Errors:** `400` (unknown fieldType), `404`, `422` (archived folder or type mismatch)

_Accepts `IdempotencyKey` header._

---

### `PUT /v1/catalog/folders/{folderId}/metadata`

Sets multiple metadata fields atomically. All fields must pass type validation or the entire batch is rejected.

**Request:**
```json
{
  "fields": {
    "campaign": { "value": "Campaign 2026", "fieldType": "String" },
    "year":     { "value": 2026,            "fieldType": "Integer" }
  },
  "attributedTo": null,
  "attributedDate": null
}
```

**Response `204 No Content`**

**Errors:** `400` (unknown fieldType in any field), `404`, `422` (archived folder or type mismatch in any field)

_Accepts `IdempotencyKey` header._

---

### `POST /v1/catalog/folders/{folderId}/metadata/commit`

Promotes the pending metadata draft to current. Returns 422 if no draft exists.

**Response `204 No Content`**

**Errors:** `404`, `422` (no pending draft or folder archived)

_Accepts `IdempotencyKey` header._

---

## Read Endpoints

### `GET /v1/catalog/collections/{collectionId}/folders/hierarchy`

Returns all folders in the collection as a **flat list**. Clients assemble the tree in memory using `parentFolderId` links.

**Query parameters:**

| Param | Type | Notes |
|---|---|---|
| `nameContains` | `string?` | Case-insensitive substring filter on folder name |

**Response `200 OK`:**
```json
{
  "folders": [
    { "id": "018f...", "parentFolderId": null,    "name": "Season 1",   "isArchived": false },
    { "id": "018g...", "parentFolderId": "018f..","name": "Episode 01", "isArchived": false }
  ]
}
```

> No pagination — all nodes are returned in a single response.

**Errors:** `400`, `401`, `403`

---

### `GET /v1/catalog/folders/{folderId}/children`

Returns immediate child folders and media items of the specified folder.

**Query parameters:**

| Param | Type | Notes |
|---|---|---|
| `sortBy` | `string?` | `name` (default) \| `createdAt` |
| `sortOrder` | `string?` | `asc` (default) \| `desc` |
| `pageToken` | `string?` | Pagination cursor |
| `pageSize` | `int?` | Default 20, max 100 |

**Response `200 OK`:**
```json
{
  "items": [
    { "id": "...", "name": "Sub-folder A", "childType": "Folder", "status": "Active" }
  ],
  "nextPageToken": null
}
```

---

### `GET /v1/catalog/folders/{folderId}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "collectionId": "018e4c7b-...",
  "parentFolderId": null,
  "name": "Hero Images",
  "description": "Campaign hero shots",
  "ownerId": "018e4c7c-...",
  "isArchived": false,
  "archivedAt": null,
  "closedAt": "2026-03-31T09:15:00Z",
  "closedDate": "2026-03-31T00:00:00Z",
  "createdAt": "2026-01-01T10:00:00Z",
  "openedDate": "2026-01-01T00:00:00Z",
  "metadata": {
    "current": { "campaign": "Hero 2026", "year": 2026 },
    "draft": null
  },
  "updatedAt": "2026-03-31T09:15:00Z"
}
```

---

### `GET /v1/catalog/folders?collectionId={id}&parentFolderId={id}`

**Query parameters:**

| Param | Type | Notes |
|---|---|---|
| `collectionId` | `string` | Required |
| `parentFolderId` | `string?` | Filter by parent — omit for root media-folders |
| `sortBy` | `string?` | `name` (default) \| `createdAt` |
| `sortOrder` | `string?` | `asc` (default) \| `desc` |
| `pageToken` | `string?` | Pagination cursor |
| `pageSize` | `int?` | Default 20, max 100 |

**Response `200 OK`:**
```json
{
  "folders": [
    {
      "id": "...",
      "name": "Hero Images",
      "parentFolderId": null,
      "isArchived": false,
      "closedAt": null,
      "closedDate": null,
      "openedDate": "2026-01-01T00:00:00Z"
    }
  ],
  "nextPageToken": null
}
```

---

## Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
| --------------------------------- | --------------------------- | -------------------- | -------------------------------------- |
| `POST /v1/catalog/collections/{collectionId}/folders` | `CreateFolderCommand` | `FolderCreated` | `FolderDetailProjector` → INSERT, `FolderSummaryProjector` → INSERT |
| `PATCH /v1/catalog/folders/{id}` (name) | `RenameFolderCommand` | `FolderRenamed` | `FolderDetailProjector` → UPDATE, `FolderSummaryProjector` → UPDATE |
| `PATCH /v1/catalog/folders/{id}/description` | `UpdateFolderDescriptionCommand` | `FolderDescriptionUpdated` | `FolderDetailProjector` → UPDATE |
| `PUT /v1/catalog/folders/{id}/parent` | `MoveFolderCommand` | `FolderMoved` | `FolderDetailProjector` → UPDATE, `FolderSummaryProjector` → UPDATE |
| `POST /v1/catalog/folders/{id}/archive` | `ArchiveFolderCommand` | `FolderArchived` | `FolderDetailProjector` → UPDATE, `FolderSummaryProjector` → UPDATE |
| `POST /v1/catalog/folders/{id}/close` | `CloseFolderCommand` | `FolderClosed` | `FolderDetailProjector` → UPDATE, `FolderSummaryProjector` → UPDATE |
| `POST /v1/catalog/collections/{collectionId}/folders/bulk` | `BulkCreateFoldersCommand` | `FolderCreated` (×N) | `FolderDetailProjector` → INSERT (×N), `FolderSummaryProjector` → INSERT (×N) |
| `POST /v1/catalog/collections/{collectionId}/folders/bulk-paths` | `BulkCreateFoldersByPathCommand` | `FolderCreated` (×N created) | `FolderDetailProjector` → INSERT (×N), `FolderSummaryProjector` → INSERT (×N) |
| `PATCH /v1/catalog/folders/{id}/metadata/{fieldName}` | `SetFolderMetadataFieldCommand` | `FolderMetadataFieldSet` | `FolderDetailProjector` → UPDATE `Metadata.Draft` |
| `PUT /v1/catalog/folders/{id}/metadata` | `SetFolderMetadataBatchCommand` | `FolderMetadataBatchSet` | `FolderDetailProjector` → UPDATE `Metadata.Draft` |
| `POST /v1/catalog/folders/{id}/metadata/commit` | `CommitFolderMetadataCommand` | `FolderMetadataCommitted` | `FolderDetailProjector` → UPDATE `Metadata.Current`, clear Draft |

---

## Bulk Write Endpoints

> Bulk operations follow the shared partial-success envelope. See [`spec/shared/bulk-operations.md`](../../../../shared/bulk-operations.md) for the full conventions: `onError`, `onDuplicate`, `BulkItemError`, retry behaviour, and idempotency.

### `POST /v1/catalog/collections/{collectionId}/folders/bulk`

Creates up to 200 media-folders in a single request. Supports in-batch parent-child relationships and per-item `openedDate`/`closedDate`.

**Request:**
```json
{
  "items": [
    { "parentFolderId": null,    "name": "Season 1",   "openedDate": "2026-01-01T00:00:00Z" },
    { "parentFolderId": "018f..","name": "Episode 01" },
    { "parentFolderId": "018f..","name": "Episode 02" }
  ],
  "onError": "ContinueOnError",
  "onDuplicate": "Reject"
}
```

**Response `201 Created`** — all succeeded:
```json
{
  "succeeded": [
    { "index": 0, "id": "018f...", "name": "Season 1",   "parentFolderId": null },
    { "index": 1, "id": "018g...", "name": "Episode 01", "parentFolderId": "018f..." },
    { "index": 2, "id": "018h...", "name": "Episode 02", "parentFolderId": "018f..." }
  ],
  "failed": [],
  "skipped": []
}
```

**Response `202 Accepted`** — partial results.

**Per-item error codes:**

| `errorCode` | Cause | Caller action |
|---|---|---|
| `DuplicateName` | Name already taken in the parent scope | Correct name or use `suggestedName` |
| `AutoSuffixExhausted` | 99 suffix attempts all taken | Manual rename required |
| `NameReservationFailed` | Concurrent write conflict | Re-submit |
| `DepthExceeded` | Parent depth + 1 > 10 | Restructure hierarchy |
| `ParentNotFound` | External `parentFolderId` does not exist | Verify parent ID |
| `ParentCreationFailed` | In-batch parent failed | Fix parent, re-submit both |

_Accepts `IdempotencyKey` header._

---

### `POST /v1/catalog/collections/{collectionId}/folders/bulk-paths`

Creates a folder tree from path strings (`mkdir -p` semantics). Existing folders are reused.

**Request:**
```json
{
  "paths": [
    "Season 1/Episode 01",
    "Season 1/Episode 02/Scene A",
    "Season 2"
  ],
  "rootFolderId": null,
  "pathSeparator": "/",
  "onError": "ContinueOnError"
}
```

**Response `201 Created`:**
```json
{
  "nodes": [
    { "path": "Season 1",              "id": "018f...", "action": "Created" },
    { "path": "Season 1/Episode 01",   "id": "018g...", "action": "Created" },
    { "path": "Season 2",              "id": "018j...", "action": "Created" }
  ],
  "failed": []
}
```

`action: "Existed"` — folder already existed; `folderId` is the pre-existing ID.

**Per-path error codes:**

| `errorCode` | Cause | Caller action |
|---|---|---|
| `InvalidPath` | Path contains an empty segment | Fix the path string |
| `DepthExceeded` | A segment would exceed depth 10 | Flatten the hierarchy |
| `NameReservationFailed` | Concurrent writer | Re-submit |
| `ParentCreationFailed` | Ancestor segment failed | Fix the parent path, re-submit |

_Accepts `IdempotencyKey` header._

---

### Large-Volume Imports

For imports exceeding 1000 folders or 30-second processing time, use the async import endpoint:

**Endpoint:** `POST /v1/catalog/collections/{collectionId}/folders/import`

**See:** [BulkFolderImportJob API](../BulkFolderImportJob/bulkfolderimportjob.api.md)

---

## Related

- [Folder Write Model](./folder.write-model.md)
- [Folder Read Model](./folder.read-model.md)
