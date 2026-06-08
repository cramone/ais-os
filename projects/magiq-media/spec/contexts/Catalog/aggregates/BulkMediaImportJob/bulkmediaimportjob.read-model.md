# BulkMediaImportJob — Read Model

_Context: `Catalog`_
_Aggregate: `BulkMediaImportJob`_

---

## Purpose

Query-facing projections for bulk media import job status, multi-phase progress tracking, and per-item results across upload → validation → cataloging → processing pipeline.

---

## Read Model Tables

### 1. `media-bulk-media-import-jobs` (DynamoDB)

**Purpose:** Job summary with phase-level progress for status polling.

**Partition Key:** `JobId`

| Field | Type | Notes |
|---|---|---|
| `JobId` | `string` | PK |
| `TenantId` | `string` | GSI1-PK |
| `CollectionId` | `string` | GSI2-PK |
| `Status` | `string` | `Queued | AwaitingUploads | Validating | Cataloging | Processing | Completed | Failed | Cancelled` |
| `InputFormat` | `string` | `JSON | CSV` |
| `TotalItems` | `int` | |
| `UploadedCount` | `int` | Phase 1 progress |
| `ValidatedCount` | `int` | Phase 2 progress |
| `CatalogedCount` | `int` | Phase 3 progress |
| `ProcessedCount` | `int` | Phase 4 progress |
| `FailedCount` | `int` | Cumulative failures across all phases |
| `CreatedAt` | `string` (ISO 8601) | GSI1-SK, GSI2-SK |
| `CompletedAt` | `string?` (ISO 8601) | |
| `FailureReason` | `string?` | Only if Status = Failed |

**GSI1:** `TenantId` (PK) + `CreatedAt` (SK)  
**GSI2:** `CollectionId` (PK) + `CreatedAt` (SK)

**Projector:** `BulkMediaImportJobSummaryProjector`

**Subscribed Events:**

| Event | Write Operation |
|---|---|
| `BulkMediaImportJobCreated` | INSERT |
| `BulkMediaImportJobUploadsStarted` | UPDATE `Status = AwaitingUploads` |
| `BulkMediaImportJobUploadConfirmationsRecorded` | UPDATE `UploadedCount` |
| `BulkMediaImportJobValidationStarted` | UPDATE `Status = Validating` |
| `BulkMediaImportJobValidationResultsRecorded` | UPDATE `ValidatedCount`, `FailedCount` |
| `BulkMediaImportJobCatalogingStarted` | UPDATE `Status = Cataloging` |
| `BulkMediaImportJobCatalogingResultsRecorded` | UPDATE `CatalogedCount`, `FailedCount` |
| `BulkMediaImportJobProcessingStarted` | UPDATE `Status = Processing` |
| `BulkMediaImportJobProcessingResultsRecorded` | UPDATE `ProcessedCount`, `FailedCount` |
| `BulkMediaImportJobCompleted` | UPDATE `Status = Completed`, `CompletedAt` |
| `BulkMediaImportJobFailed` | UPDATE `Status = Failed`, `CompletedAt`, `FailureReason` |
| `BulkMediaImportJobCancelled` | UPDATE `Status = Cancelled`, `CompletedAt` |

---

### 2. `media-bulk-import-job-items` (DynamoDB) — Shared with Folder Imports

**Purpose:** Per-item results across all import job types. Reuses same table as `BulkFolderImportJob` with additional fields for media-specific pipeline phases.

**Partition Key:** `TENANT#{TenantId}#JOB#{JobId}`  
**Sort Key:** `ITEM#{Index}`

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#JOB#{JobId}` |
| `SK` | `string` | `ITEM#{Index}` (0-padded: `ITEM#0000000042`) |
| `JobType` | `string` | `FolderImport | MediaImport` — discriminator |
| `Title` | `string?` | Media title (MediaImport only) |
| `FileName` | `string?` | Original filename (MediaImport only) |
| `Path` | `string?` | Folder path (FolderImport only) |
| `FolderId` | `string?` | Target folder (MediaImport only) |
| `MediaItemId` | `string?` | Created MediaItem ID (MediaImport only) |
| `AssetId` | `string?` | Created Asset ID (MediaImport only) |
| `Status` | `string` | `pending | uploaded | validated | cataloged | processed | failed` |
| `Phase` | `string?` | Last phase reached: `upload | validation | cataloging | processing` |
| `ErrorCode` | `string?` | Only if failed |
| `ErrorMessage` | `string?` | Only if failed |
| `ProcessedAt` | `string?` (ISO 8601) | When final state reached |

**Query Pattern:**
- `GET /v1/catalog/import-jobs/{jobId}/items` → Query PK
- `GET /v1/catalog/import-jobs/{jobId}/items?status=failed&phase=validation` → FilterExpression

**Write Pattern:**
- Written by `BulkMediaImportWorker` Lambda directly after each phase completes
- Updated in-place as item progresses through phases

---

### 3. `media-bulk-media-import-job-detail` (DynamoDB)

**Purpose:** Full job detail including manifest reference and upload URL table pointer.

**Partition Key:** `JobId`

| Field | Type | Notes |
|---|---|---|
| `JobId` | `string` | PK |
| `TenantId` | `string` | |
| `CollectionId` | `string` | |
| `Status` | `string` | |
| `InputFormat` | `string` | |
| `InputStorageKey` | `string?` | S3 key for manifest if >10KB |
| `InputPayload` | `string?` | Inline manifest if ≤10KB |
| `UploadUrlsTableKey` | `string?` | Reference to `media-bulk-import-upload-urls` entries |
| `TotalItems` | `int` | |
| `UploadedCount` | `int` | |
| `ValidatedCount` | `int` | |
| `CatalogedCount` | `int` | |
| `ProcessedCount` | `int` | |
| `FailedCount` | `int` | |
| `CreatedAt` | `string` (ISO 8601) | |
| `CompletedAt` | `string?` (ISO 8601) | |
| `FailureReason` | `string?` | |

**Projector:** `BulkMediaImportJobDetailProjector`

---

### 4. `media-bulk-import-upload-urls` (DynamoDB) — Temporary Table

**Purpose:** Pre-signed upload URLs for client-side asset uploads. TTL-enabled (24h).

**Partition Key:** `TENANT#{TenantId}#JOB#{JobId}`  
**Sort Key:** `ITEM#{Index}`

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#JOB#{JobId}` |
| `SK` | `string` | `ITEM#{Index}` |
| `AssetId` | `string` | Generated by worker |
| `UploadUrl` | `string` | Pre-signed S3 URL (24h expiry) |
| `ConfirmationToken` | `string` | UUID — client sends this on confirm |
| `Uploaded` | `bool` | Set to `true` on confirmation |
| `ExpiresAt` | `number` | Unix timestamp for DynamoDB TTL |

**Query Pattern:**
- `GET /v1/catalog/import-jobs/{jobId}/upload-urls` → Query PK (paginated)
- Client polls this endpoint to retrieve upload URLs batch-by-batch

**Write Pattern:**
- Written by `BulkMediaImportWorker` during Phase 1
- Updated by `POST /v1/catalog/import-jobs/{jobId}/confirm-uploads` endpoint

**TTL:** Items auto-deleted 24h after `ExpiresAt` via DynamoDB TTL

---

## Query Endpoints → Read Model Mapping

| Endpoint | Table | Index |
|---|---|---|
| `GET /v1/catalog/import-jobs/{jobId}` | `media-bulk-media-import-job-detail` | PK lookup |
| `GET /v1/catalog/import-jobs/{jobId}/items` | `media-bulk-import-job-items` | Query on PK |
| `GET /v1/catalog/import-jobs/{jobId}/upload-urls` | `media-bulk-import-upload-urls` | Query on PK |
| `GET /v1/catalog/import-jobs?collectionId={id}` | `media-bulk-media-import-jobs` | GSI2 query |

---

## Related

- [BulkMediaImportJob Write Model](./bulkmediaimportjob.write-model.md)
- [BulkMediaImportJob API](./bulkmediaimportjob.api.md)
