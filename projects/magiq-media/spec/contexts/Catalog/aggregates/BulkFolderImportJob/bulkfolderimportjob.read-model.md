# BulkFolderImportJob — Read Model

_Context: `Catalog`_
_Aggregate: `BulkFolderImportJob`_

---

## Purpose

Query-facing projections for bulk folder import job status, history, and per-item results. Supports progress tracking UI, failure analysis, and audit trail for large-volume imports.

---

## Read Model Tables

### 1. `media-bulk-folder-import-jobs` (DynamoDB)

**Purpose:** Job summary for status polling and job history listing.

**Partition Key:** `JobId`

| Field | Type | Notes |
|---|---|---|
| `JobId` | `string` | PK |
| `TenantId` | `string` | GSI1-PK |
| `CollectionId` | `string` | GSI2-PK |
| `Status` | `string` | `Queued | Processing | Completed | Failed | Cancelled` |
| `InputFormat` | `string` | `LineDelimited | CSV | JSON` |
| `TotalItems` | `int` | |
| `ProcessedCount` | `int` | |
| `SucceededCount` | `int` | |
| `FailedCount` | `int` | |
| `CreatedAt` | `string` (ISO 8601) | GSI1-SK, GSI2-SK |
| `CompletedAt` | `string?` (ISO 8601) | Null if job not terminal |
| `FailureReason` | `string?` | Only set if Status = Failed |

**GSI1:** `TenantId` (PK) + `CreatedAt` (SK)  
**Purpose:** List all import jobs for a tenant, newest first

**GSI2:** `CollectionId` (PK) + `CreatedAt` (SK)  
**Purpose:** List all import jobs for a collection, newest first

**Projector:** `BulkFolderImportJobSummaryProjector`

**Subscribed Events:**

| Event | Write Operation |
|---|---|
| `BulkFolderImportJobCreated` | INSERT |
| `BulkFolderImportJobBatchProcessed` | UPDATE `ProcessedCount`, `SucceededCount`, `FailedCount` |
| `BulkFolderImportJobCompleted` | UPDATE `Status = Completed`, `CompletedAt` |
| `BulkFolderImportJobFailed` | UPDATE `Status = Failed`, `CompletedAt`, `FailureReason` |
| `BulkFolderImportJobCancelled` | UPDATE `Status = Cancelled`, `CompletedAt` |

---

### 2. `media-bulk-import-job-items` (DynamoDB)

**Purpose:** Per-item results for failure analysis and retry. Supports paginated query of failed items.

**Partition Key:** `TENANT#{TenantId}#JOB#{JobId}`  
**Sort Key:** `ITEM#{Index}`

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#JOB#{JobId}` |
| `SK` | `string` | `ITEM#{Index}` (0-padded to 10 digits for correct sort: `ITEM#0000000042`) |
| `Path` | `string` | Input path string |
| `FolderId` | `string?` | Null if failed |
| `Status` | `string` | `succeeded | failed` |
| `ErrorCode` | `string?` | Null if succeeded |
| `ErrorMessage` | `string?` | Null if succeeded |
| `ProcessedAt` | `string` (ISO 8601) | |

**Query Pattern:**
- `GET /v1/catalog/import-jobs/{jobId}/items` → Query PK, optionally filter by `Status` in-memory (or via FilterExpression)
- `GET /v1/catalog/import-jobs/{jobId}/items?status=failed` → Query PK with FilterExpression `Status = :failed`

**Write Pattern:**
- Written by `BulkFolderImportWorker` Lambda directly (not via projector) after each batch completes
- Items written in batch via `BatchWriteItem` (25 items per API call)

**No projector** — this table is written directly by the worker, not via domain event subscription. Worker has both command dispatch responsibility (creating folders) and result recording responsibility (writing to this table).

---

### 3. `media-bulk-folder-import-job-detail` (DynamoDB)

**Purpose:** Full job detail including input payload (if inline) or S3 key reference.

**Partition Key:** `JobId`

| Field | Type | Notes |
|---|---|---|
| `JobId` | `string` | PK |
| `TenantId` | `string` | |
| `CollectionId` | `string` | |
| `Status` | `string` | |
| `InputFormat` | `string` | |
| `InputStorageKey` | `string?` | S3 key if input >10KB |
| `InputPayload` | `string?` | Inline input if ≤10KB |
| `TotalItems` | `int` | |
| `ProcessedCount` | `int` | |
| `SucceededCount` | `int` | |
| `FailedCount` | `int` | |
| `CreatedAt` | `string` (ISO 8601) | |
| `CompletedAt` | `string?` (ISO 8601) | |
| `FailureReason` | `string?` | |

**Projector:** `BulkFolderImportJobDetailProjector`

**Subscribed Events:** Same as summary projector

**Usage:** `GET /v1/catalog/import-jobs/{jobId}` endpoint — returns full detail

---

## Query Endpoints → Read Model Mapping

| Endpoint | Table | Index |
|---|---|---|
| `GET /v1/catalog/import-jobs/{jobId}` | `media-bulk-folder-import-job-detail` | PK lookup |
| `GET /v1/catalog/import-jobs/{jobId}/items` | `media-bulk-import-job-items` | Query on PK |
| `GET /v1/catalog/import-jobs?tenantId={id}` | `media-bulk-folder-import-jobs` | GSI1 query |
| `GET /v1/catalog/import-jobs?collectionId={id}` | `media-bulk-folder-import-jobs` | GSI2 query |

---

## Related

- [BulkFolderImportJob Write Model](./bulkfolderimportjob.write-model.md)
- [BulkFolderImportJob API](./bulkfolderimportjob.api.md)
