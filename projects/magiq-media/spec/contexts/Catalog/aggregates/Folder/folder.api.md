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
GET    /v1/catalog/collections/{collectionId}/folders/hierarchy?nameContains=
PATCH  /v1/catalog/folders/{folderId}
PATCH  /v1/catalog/folders/{folderId}/description
PUT    /v1/catalog/folders/{folderId}/parent
POST   /v1/catalog/folders/{folderId}/archive
GET    /v1/catalog/folders/{folderId}
GET    /v1/catalog/folders/{folderId}/children?sortBy=&sortOrder=
GET    /v1/catalog/folders?collectionId=&parentFolderId=
```

---

## Write Endpoints

> **Concurrency note (R-22):** Several Folder mutating operations require a caller-supplied `expectedVersion` field. This is **intentional by design** — Folder supports nested hierarchies where concurrent moves can create depth-limit violations or circular references. Caller-supplied optimistic concurrency forces the caller to acknowledge the current version before making structural changes, preventing lost-update races in tree manipulation. This differs from other aggregates (e.g., MediaItem, Collection) where the server manages concurrency internally. See `system-spec.md §Concurrency` for the full rationale.

### `POST /v1/catalog/collections/{collectionId}/folders`

**Request:**
```json
{
  "folderId": "018e4c7a-...",
  "parentFolderId": null,
  "name": "Hero Images"
}
```

**Response `201 Created`:**
```json
{ "id": "018e4c7a-..." }
```

**Errors:** `400`, `401`, `404` (collectionId not found), `409` (depth > 10)

_Accepts `IdempotencyKey` header._

**Error response example (`404 Not Found`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/collection-not-found",
  "title": "Collection not found",
  "status": 404,
  "detail": "Collection 018e4c7b-... does not exist for this tenant.",
  "extensions": { "errorCode": "CollectionNotFound" }
}
```

---

### `PATCH /v1/catalog/folders/{folderId}`

Renames the media-folder.

**Request:**
```json
{
  "name": "Banner Images",
  "expectedVersion": 2
}
```

`expectedVersion` is required — see concurrency note above.

**Response `200 OK`** — no body.

**Errors:** `409` (concurrency conflict — `expectedVersion` mismatch)

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — concurrency):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/concurrency-conflict",
  "title": "Concurrency conflict",
  "status": 409,
  "detail": "Folder 018e4c7a-... expected version 2 but current version is 3.",
  "extensions": { "errorCode": "ConcurrencyConflict", "expectedVersion": 2, "currentVersion": 3 }
}
```

---

### `PATCH /v1/catalog/folders/{folderId}/description`

Updates only the media-folder description.

**Request:**
```json
{ "description": "Hero and banner images for Q2 campaign" }
```

**Response `200 OK`** — no body.

_Accepts `IdempotencyKey` header._

**Error response example (`403 Forbidden`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/not-resource-owner",
  "title": "Not the resource owner",
  "status": 403,
  "detail": "Caller owner_B does not own Folder 018e4c7a-...",
  "extensions": { "errorCode": "NotResourceOwner" }
}
```

---

### `PUT /v1/catalog/folders/{folderId}/parent`

**Request:**
```json
{
  "newParentFolderId": "018e4c7c-...",
  "expectedVersion": 3
}
```

`expectedVersion` is required — see concurrency note above. Set `newParentFolderId: null` to move to media-collection root.

**Response `204 No Content`** — no body.

**Errors:** `409` (depth > 10 or concurrency), `422` (circular reference or cross-collection move)

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity` — circular reference):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/circular-folder-reference",
  "title": "Circular folder reference",
  "status": 422,
  "detail": "Moving Folder 018e4c7a-... under Folder 018e4c7c-... would create a circular reference.",
  "extensions": { "errorCode": "CircularFolderReference" }
}
```

---

### `POST /v1/catalog/folders/{folderId}/archive`

**Request:**
```json
{ "expectedVersion": 4 }
```

`expectedVersion` is required — see concurrency note above.

**Response `204 No Content`** — no body.

**Errors:** `409` (not empty — eventually consistent)

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — media-folder not empty):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/folder-not-empty",
  "title": "Folder is not empty",
  "status": 409,
  "detail": "Folder 018e4c7a-... still contains media-items or child folders and cannot be archived.",
  "extensions": { "errorCode": "FolderNotEmpty" }
}
```

---

## Read Endpoints

### `GET /v1/catalog/collections/{collectionId}/folders/hierarchy`

Returns all folders in the collection as a **flat list**. Clients assemble the tree in memory using `parentFolderId` links.

> **Filter note:** `nameContains` is applied in-memory after a single DynamoDB GSI query (PK-only scan of `CollectionParentIndex`). It cannot be pushed to DynamoDB because the GSI SK (`{name_lower}#{folderId}`) only supports prefix matching, not substring. For large collections this is acceptable — the full node set is loaded in one read regardless.

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

> No pagination — all nodes are returned in a single response. The endpoint fetches all folders for the collection in one GSI query (`PagerParameters.AllOnOnePage()`).

**Errors:** `400`, `401`, `403`

---

### `GET /v1/catalog/folders/{folderId}/children`

Returns immediate child folders of the specified media-folder.

> 🔧 **Requires implementation (R-21 · Phase 5):** Sort parameters must be implemented. Default sort is `name asc`.

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
  "folders": [
    { "id": "...", "name": "Sub-folder A", "isArchived": false }
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
  "isArchived": false,
  "createdAt": "2026-03-26T10:00:00Z",
  "updatedAt": "2026-03-26T10:00:00Z"
}
```

---

### `GET /v1/catalog/folders?collectionId={id}&parentFolderId={id}`

> 🔧 **Requires implementation (R-21 · Phase 5):** Sort parameters must be implemented. Default sort is `name asc`.

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
    { "id": "...", "name": "Hero Images", "parentFolderId": null, "isArchived": false }
  ],
  "nextPageToken": null
}
```

---

## Command → Event → Projection Traceability

| API Call                          | Command                     | Domain Event         | Projection                             |
| --------------------------------- | --------------------------- | -------------------- | -------------------------------------- |
| `POST /v1/catalog/collections/{collectionId}/folders` | `CreateFolderCommand`          | `FolderCreated`          | `FolderProjector` → INSERT  |
| `PATCH /v1/catalog/folders/{id}` (name)              | `RenameFolderCommand`          | `FolderRenamed`          | `FolderProjector` → UPDATE  |
| `PATCH /v1/catalog/folders/{id}/description`         | `UpdateFolderDescriptionCommand` | `FolderDescriptionUpdated` | `FolderProjector` → UPDATE |
| `PUT /v1/catalog/folders/{id}/parent`                | `MoveFolderCommand`            | `FolderMoved`            | `FolderProjector` → UPDATE  |
| `POST /v1/catalog/folders/{id}/archive`              | `ArchiveFolderCommand`         | `FolderArchived`         | `FolderProjector` → UPDATE  |

---

## Related

- [Folder Write Model](./media-folder.write-model.md)
- [Folder Read Model](./media-folder.read-model.md)

---

## Bulk Write Endpoints

> Bulk operations follow the shared partial-success envelope. See [`spec/shared/bulk-operations.md`](../../../../shared/bulk-operations.md) for the full conventions: `onError`, `onDuplicate`, `BulkItemError`, retry behaviour, and idempotency.

### `POST /v1/catalog/collections/{collectionId}/folders/bulk`

Creates up to 200 media-folders in a single request within the specified media-collection. Supports in-batch parent-child relationships — a `folderId` in the batch can be referenced as the `parentFolderId` of another media-item in the same request.

**Ordering:** The handler performs a topological sort (Kahn's algorithm) before processing. Items with no in-batch dependency (root or external parent) are processed first; child media-items follow in subsequent waves. Circular dependencies within the batch return `400`.

**Depth limit:** Each media-item's nesting depth is validated before its write. Items that would exceed depth 10 are recorded as `Failed` with `errorCode = "DepthExceeded"`.

**Parent failure propagation:** If a parent media-folder fails to create, all in-batch children of that parent are automatically marked `Failed` with `errorCode = "ParentCreationFailed"` — they are never attempted.

**Request:**
```json
{
  "items": [
    { "folderId": "018f...", "parentFolderId": null,    "name": "Season 1" },
    { "folderId": "018g...", "parentFolderId": "018f..","name": "Episode 01" },
    { "folderId": "018h...", "parentFolderId": "018f..","name": "Episode 02" }
  ],
  "onError": "ContinueOnError",
  "onDuplicate": "Reject"
}
```

`folderId` is caller-generated (UUID v7). If omitted, the server generates one.  
`parentFolderId` may reference either an existing media-folder or another `folderId` within the same batch.

**Response `201 Created`** — all media-items succeeded:
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

**Response `202 Accepted`** — partial results (example: depth exceeded):
```json
{
  "succeeded": [
    { "index": 0, "id": "018f...", "name": "Season 1", "parentFolderId": null }
  ],
  "failed": [
    {
      "index": 1,
      "name": "Episode 01",
      "errorCode": "DepthExceeded",
      "message": "Folder nesting depth cannot exceed 10 levels."
    }
  ],
  "skipped": []
}
```

**Errors (request-level):**
- `400` — batch exceeds 200 media-items, circular dependency detected, or required fields missing
- `401` — unauthenticated
- `403` — permission denied
- `404` — `collectionId` not found

**Per-item error codes:**

| `errorCode` | Cause | Caller action |
|---|---|---|
| `DuplicateName` | Name already taken in the parent scope | Correct name or use `suggestedName` |
| `AutoSuffixExhausted` | 99 suffix attempts all taken | Manual rename required |
| `NameReservationFailed` | Concurrent write conflict; retries exhausted | Re-submit |
| `DepthExceeded` | Parent depth + 1 > 10 | Restructure hierarchy |
| `ParentNotFound` | External `parentFolderId` does not exist | Verify parent ID |
| `ParentCreationFailed` | In-batch parent failed; this media-item was not attempted | Fix parent, re-submit both |

_Accepts `IdempotencyKey` header._

---

## Updated Command → Event → Projection Traceability

_(Existing table entries unchanged — appended below)_

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/collections/{collectionId}/folders/bulk` | `BulkCreateFoldersCommand` | `FolderCreated` (×N) | `FolderProjector` → INSERT (×N), depth + child-folder counters |

---

### `POST /v1/catalog/collections/{collectionId}/folders/bulk-paths`

Creates a media-folder tree from an array of path strings. Intermediate segments are auto-created (`mkdir -p` semantics). Folders that already exist are **reused** — no error, no duplicate. Every node in the resolved tree is returned with its `folderId` and whether it was `Created` or `Existed`.

This is distinct from `POST /v1/catalog/collections/{collectionId}/folders/bulk` which requires explicit parent IDs. Use bulk-paths when the caller thinks in filesystem terms; use bulk when the caller controls IDs and topology explicitly.

> See [`spec/shared/bulk-operations.md`](../../../../shared/bulk-operations.md) for `onError` mode, batch size limits, and idempotency conventions.

**Path semantics:**
- Paths are relative to the media-collection root, or to `rootFolderId` if supplied
- Segments are separated by `pathSeparator` (default `/`)
- Common prefixes are deduplicated — `["A/B", "A/C"]` creates `A` once
- Depth is validated per segment; the entire path fails if any segment would exceed depth 10
- If a parent segment fails, all child segments in that subtree are also failed with `errorCode = "ParentCreationFailed"`

**Request:**
```json
POST /v1/catalog/collections/{collectionId}/folders/bulk-paths

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

`rootFolderId` is optional. If supplied, all paths are resolved relative to that existing media-folder.

**Response `201 Created`** — all nodes resolved:
```json
{
  "nodes": [
    { "path": "Season 1",              "id": "018f...", "action": "Created" },
    { "path": "Season 1/Episode 01",   "id": "018g...", "action": "Created" },
    { "path": "Season 1/Episode 02",   "id": "018h...", "action": "Created" },
    { "path": "Season 1/Episode 02/Scene A", "id": "018i...", "action": "Created" },
    { "path": "Season 2",              "id": "018j...", "action": "Created" }
  ],
  "failed": []
}
```

**Response `202 Accepted`** — partial success (existing media-folder reused, one segment failed):
```json
{
  "nodes": [
    { "path": "Season 1",            "id": "018f...", "action": "Existed" },
    { "path": "Season 1/Episode 01", "id": "018g...", "action": "Created" },
    { "path": "Season 2",            "id": "018j...", "action": "Created" }
  ],
  "failed": [
    {
      "path": "Season 1/Episode 02/Scene A",
      "errorCode": "DepthExceeded",
      "message": "Path 'Season 1/Episode 02/Scene A' would reach depth 11, exceeding the maximum of 10."
    }
  ]
}
```

> `action: "Existed"` means the media-folder already existed and was reused. Its `folderId` is the ID of the pre-existing media-folder so the caller can use it without a separate lookup.

**Errors (request-level):**
- `400` — no paths supplied, a path contains an empty segment, or the total distinct segment count exceeds `MaxFoldersPerRequest`
- `401` — unauthenticated
- `403` — permission denied
- `404` — `collectionId` or `rootFolderId` not found

**Per-path error codes:**

| `errorCode` | Cause | Caller action |
|---|---|---|
| `InvalidPath` | Path contains an empty segment (e.g. `A//B`) | Fix the path string |
| `DepthExceeded` | A segment in this path would exceed depth 10 | Flatten the hierarchy |
| `NameReservationFailed` | Concurrent writer; retries exhausted | Re-submit |
| `ParentCreationFailed` | An ancestor segment in this subtree failed | Fix the parent path, re-submit |

_Accepts `IdempotencyKey` header._

**Comparison with `POST .../folders/bulk`:**

| | `bulk` | `bulk-paths` |
|---|---|---|
| Input | Explicit `folderId` + `parentFolderId` per media-item | Path strings |
| Existing media-folders | Subject to `onDuplicate` strategy | Always reused (Existed) |
| Topology | Caller controls | Server parses from path |
| Response shape | Standard `succeeded/failed/skipped` envelope | `nodes` (with action) + `failed` |
| Best for | Import pipelines that own IDs | Directory-tree style ingestion |

---

## Updated Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/collections/{collectionId}/folders/bulk-paths` | `BulkCreateFoldersByPathCommand` | `FolderCreated` (×N created) | `FolderProjector` → INSERT (×N), depth + child-fo