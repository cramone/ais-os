# BulkFolderImportJob — API

_Context: `Catalog`_
_Aggregate: `BulkFolderImportJob`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints.
- **Idempotency:** All mutating endpoints accept `IdempotencyKey: <uuid>`.
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457).

---

## Route Structure

```
POST   /v1/catalog/collections/{collectionId}/folders/import
GET    /v1/catalog/import-jobs/{jobId}
GET    /v1/catalog/import-jobs/{jobId}/items
DELETE /v1/catalog/import-jobs/{jobId}
GET    /v1/catalog/import-jobs
```

---

## Write Endpoints

### `POST /v1/catalog/collections/{collectionId}/folders/import`

Initiates async bulk folder import job. Accepts line-delimited paths, CSV, or JSON. Returns immediately with `jobId`. Client polls `GET /v1/catalog/import-jobs/{jobId}` for progress.

**Content-Type:** `text/plain | text/csv | application/json`

---

#### Format 1: Line-Delimited Paths (`text/plain`)

**Request:**
```
POST /v1/catalog/collections/{collectionId}/folders/import
Content-Type: text/plain

Season 1/Episode 01
Season 1/Episode 02/Scene A
Season 2
```

Each line = folder path relative to collection root. Path separator = `/` (configurable via query param).

**Query Parameters:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `pathSeparator` | `string?` | `/` | Path segment delimiter |
| `rootFolderId` | `string?` | null | Root all paths under this existing folder |

---

#### Format 2: CSV (`text/csv`)

**Request:**
```
POST /v1/catalog/collections/{collectionId}/folders/import
Content-Type: text/csv

Season 1,Episode 01,Episode 02,Season 2
```

Each value = separate root folder (flat list). Hierarchical structure not supported via CSV — use line-delimited paths instead.

---

#### Format 3: JSON (`application/json`)

**Request:**
```json
POST /v1/catalog/collections/{collectionId}/folders/import
Content-Type: application/json

{
  "paths": [
    "Season 1/Episode 01",
    "Season 1/Episode 02/Scene A",
    "Season 2"
  ],
  "pathSeparator": "/",
  "rootFolderId": null
}
```

---

**Response `202 Accepted`:**
```json
{
  "jobId": "018f1a2b-3c4d-7e8f-9a0b-1c2d3e4f5a6b",
  "status": "Queued",
  "estimatedItems": 3
}
```

**Errors:**

| Status | Condition |
|---|---|
| `400` | Invalid input format, empty input, or `collectionId` malformed |
| `401` | Unauthenticated |
| `403` | Caller does not own collection |
| `404` | `collectionId` or `rootFolderId` not found |
| `413` | Input exceeds 50MB |

_Accepts `IdempotencyKey` header — replaying same key returns existing job._

---

## Read Endpoints

### `GET /v1/catalog/import-jobs/{jobId}`

Returns job status and summary statistics.

**Response `200 OK`:**
```json
{
  "jobId": "018f1a2b-3c4d-7e8f-9a0b-1c2d3e4f5a6b",
  "jobType": "FolderImport",
  "collectionId": "018e4c7b-...",
  "status": "Processing",
  "inputFormat": "LineDelimited",
  "totalItems": 10000,
  "processedCount": 7200,
  "succeededCount": 7150,
  "failedCount": 50,
  "createdAt": "2026-06-04T07:00:00Z",
  "completedAt": null
}
```

**Status values:** `Queued | Processing | Completed | Failed | Cancelled`

**Errors:** `404` (job not found or not owned by caller's tenant)

---

### `GET /v1/catalog/import-jobs/{jobId}/items`

Returns per-item results. Paginated.

**Query Parameters:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `status` | `string?` | all | Filter: `succeeded | failed` |
| `pageToken` | `string?` | null | Continuation token |
| `pageSize` | `int?` | 100 | Max 500 |

**Response `200 OK`:**
```json
{
  "items": [
    {
      "index": 42,
      "path": "Season 1/Episode 02",
      "folderId": "018f...",
      "status": "succeeded"
    },
    {
      "index": 43,
      "path": "Season 3",
      "status": "failed",
      "errorCode": "DepthExceeded",
      "errorMessage": "Path 'Season 3/...' would exceed depth 10."
    }
  ],
  "nextPageToken": "eyJ..."
}
```

**Errors:** `404` (job not found)

---

### `GET /v1/catalog/import-jobs`

Lists import jobs. Supports filtering by tenant or collection.

**Query Parameters:**

| Param | Type | Required | Notes |
|---|---|---|---|
| `collectionId` | `string?` | No | Filter by collection |
| `status` | `string?` | No | Filter by status |
| `pageToken` | `string?` | No | Continuation token |
| `pageSize` | `int?` | No | Default 20, max 100 |

If `collectionId` omitted: returns all jobs for caller's tenant.

**Response `200 OK`:**
```json
{
  "jobs": [
    {
      "jobId": "018f...",
      "collectionId": "018e...",
      "status": "Completed",
      "totalItems": 5000,
      "succeededCount": 4950,
      "failedCount": 50,
      "createdAt": "2026-06-03T12:00:00Z",
      "completedAt": "2026-06-03T12:05:30Z"
    }
  ],
  "nextPageToken": null
}
```

---

### `DELETE /v1/catalog/import-jobs/{jobId}`

Cancels a queued or in-progress job. No-op if already completed.

**Response `204 No Content`**

**Errors:** `404` (job not found), `409` (job already completed — cannot cancel)

_Accepts `IdempotencyKey` header._

---

## Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/collections/{id}/folders/import` | `CreateBulkFolderImportJobCommand` | `BulkFolderImportJobCreated` | `BulkFolderImportJobSummaryProjector`, `BulkFolderImportJobDetailProjector` |
| `DELETE /v1/catalog/import-jobs/{id}` | `CancelBulkFolderImportJobCommand` | `BulkFolderImportJobCancelled` | Projectors UPDATE status |
| (Worker) | `RecordBulkFolderImportJobBatchResultCommand` | `BulkFolderImportJobBatchProcessed` | Projectors UPDATE counts |
| (Worker) | `CompleteBulkFolderImportJobCommand` | `BulkFolderImportJobCompleted` | Projectors UPDATE status, set `CompletedAt` |

---

## Related

- [BulkFolderImportJob Write Model](./bulkfolderimportjob.write-model.md)
- [BulkFolderImportJob Read Model](./bulkfolderimportjob.read-model.md)
- [Folder API](../Folder/folder.api.md)
- [Bulk Operations](../../../../shared/bulk-operations.md)
