# Bulk Import Spec Updates Summary

This document lists changes needed to existing spec files to integrate bulk folder and media import functionality.

---

## New Aggregates Created

1. **`BulkFolderImportJob`** — `contexts/Catalog/aggregates/BulkFolderImportJob/`
   - `bulkfolderimportjob.write-model.md`
   - `bulkfolderimportjob.read-model.md`
   - `bulkfolderimportjob.api.md`

2. **`BulkMediaImportJob`** — `contexts/Catalog/aggregates/BulkMediaImportJob/`
   - `bulkmediaimportjob.write-model.md`
   - `bulkmediaimportjob.read-model.md`
   - `bulkmediaimportjob.api.md`

---

## Changes to Existing Spec Files

### 1. `architecture/system-architecture.md`

**Section: Services**

Add two new Lambda services:

```markdown
| Service | Runtime | Trigger | Responsibility |
|---|---|---|---|
| ... (existing services) ... |
| **BulkFolderImportWorker** | Lambda | SQS `media-bulk-folder-imports` queue (`BulkFolderImportJobCreatedMessage`) | Parse input (line-delimited, CSV, JSON); split into chunks of 200; dispatch `BulkCreateFoldersByPathCommand` per chunk; record per-item results; advance job state |
| **BulkMediaImportWorker** | Lambda | SQS `media-bulk-media-imports` queue (`BulkMediaImportJobCreatedMessage`) | Multi-phase: (1) issue pre-signed upload URLs, (2) await confirmations, (3) validate uploads, (4) catalog MediaItems in batches of 50, (5) track processing pipeline completion; record per-item results; advance job state |
```

**Section: SNS/SQS Topology Diagram**

Update diagram to include:

```markdown
┌───────────────────────┐
│  SNS Topic            │
│  media-integration-   │
│  events               │
└────────┬──────────────┘
         │
         ├──▶ media-cross-module-events SQS
         ├──▶ media-sagas SQS
         ├──▶ media-document-signing SQS
         ├──▶ media-bulk-folder-imports SQS → BulkFolderImportWorker Lambda  ← NEW
         ├──▶ media-bulk-media-imports SQS → BulkMediaImportWorker Lambda    ← NEW
         ├──▶ Notifications-owned SQS
         ├──▶ Search/Discovery-owned SQS
         ├──▶ Billing-owned SQS
         └──▶ Compliance-owned SQS
```

**Section: DynamoDB Tables**

Add new read model tables:

```markdown
| Table | Purpose | Owned By |
|---|---|---|
| ... (existing tables) ... |
| `media-bulk-folder-import-jobs` | Job status for async folder imports | Catalog |
| `media-bulk-media-import-jobs` | Job status for async media imports | Catalog |
| `media-bulk-import-job-items` | Per-item results for all bulk import jobs (shared) | Catalog |
| `media-bulk-folder-import-job-detail` | Full detail for folder import jobs | Catalog |
| `media-bulk-media-import-job-detail` | Full detail for media import jobs | Catalog |
| `media-bulk-import-upload-urls` | Temporary pre-signed URLs for media uploads (TTL 24h) | Catalog |
```

**Section: S3 Buckets**

Add new bucket:

```markdown
| Bucket | Purpose |
|---|---|
| ... (existing buckets) ... |
| `media-bulk-import-inputs` | Stores large import manifests (>10KB); input format agnostic; TTL 7 days |
```

---

### 2. `shared/bulk-operations.md`

**New Section: Async Bulk Import Jobs**

Add after existing bulk conventions:

```markdown
## Async Bulk Import Jobs

For imports exceeding inline HTTP timeout limits (>1000 items or >30sec processing), use async job pattern.

### Pattern

1. **Initiate:** `POST /v1/catalog/.../import` → Returns `jobId` immediately (202 Accepted)
2. **Process:** Worker Lambda consumes job creation event from SQS, processes in chunks
3. **Poll Status:** `GET /v1/catalog/import-jobs/{jobId}` → Returns progress counts
4. **Retrieve Results:** `GET /v1/catalog/import-jobs/{jobId}/items?status=failed` → Per-item failures

### Job Types

| Job Type | Aggregate | Input Formats | Batch Size | Phases |
|---|---|---|---|---|
| Folder Import | `BulkFolderImportJob` | Line-delimited, CSV, JSON | 200 | Single-phase (creation) |
| Media Import | `BulkMediaImportJob` | JSON, CSV | 50 | Multi-phase (upload → validate → catalog → process) |

### Shared Infrastructure

- **Status API:** `GET /v1/catalog/import-jobs/{jobId}` — polymorphic response shape per job type
- **Items API:** `GET /v1/catalog/import-jobs/{jobId}/items` — shared table `media-bulk-import-job-items` with `JobType` discriminator
- **SNS Topic:** `media-integration-events` — job created events published here with message type filtering

### Input Storage Strategy

| Size | Storage | Key Pattern |
|---|---|---|
| ≤10KB | Inline in aggregate event payload | N/A |
| >10KB | S3 `media-bulk-import-inputs` bucket | `{tenantId}/{job-type}/{jobId}.{ext}` |

### Job Lifecycle

```
Initiate (API) → Queued → Processing (Worker) → Completed
                                            ↘ Failed
                                            ↘ Cancelled (user-requested)
```

### Comparison: Inline vs Async

| | Inline Bulk (`/bulk`, `/bulk-paths`) | Async Import (`/import`) |
|---|---|---|
| Response | Synchronous — 201/202 with full results | Async — 202 with jobId |
| Size limit | ~1000 items or 30sec processing | Unlimited (chunked) |
| Progress | None (all-at-once) | Polled via status endpoint |
| Failure detail | Immediate in response | Query via items endpoint |
| Use case | Small-to-medium batches | Large-volume migrations |
```

---

### 3. `contexts/Catalog/aggregates/Folder/folder.api.md`

**Section: Route Structure**

Add new route after existing bulk endpoints:

```markdown
POST   /v1/catalog/collections/{collectionId}/folders
POST   /v1/catalog/collections/{collectionId}/folders/bulk
POST   /v1/catalog/collections/{collectionId}/folders/bulk-paths
POST   /v1/catalog/collections/{collectionId}/folders/import          ← NEW
GET    /v1/catalog/collections/{collectionId}/folders/hierarchy
...
```

**Section: Bulk Write Endpoints**

Add reference to async import at end of section:

```markdown
### Large-Volume Imports

For imports exceeding 1000 folders or 30-second processing time, use the async import endpoint:

**See:** [BulkFolderImportJob API](../BulkFolderImportJob/bulkfolderimportjob.api.md)

```

---

### 4. `contexts/Catalog/aggregates/MediaItem/mediaitem.api.md`

**Section: Route Structure**

Add new import route:

```markdown
POST   /v1/catalog/media-items
POST   /v1/catalog/media-items/import                                 ← NEW
GET    /v1/catalog/media-items/{id}
...
```

**New Section: Bulk Write Endpoints**

Add after existing single-item endpoints:

```markdown
## Bulk Write Endpoints

### Large-Volume Imports

For media imports with binary uploads and asset processing pipeline, use the async import endpoint:

**See:** [BulkMediaImportJob API](../BulkMediaImportJob/bulkmediaimportjob.api.md)

**Key Differences from Inline Bulk:**
- Supports pre-signed S3 upload workflow (client-side uploads)
- Tracks multi-phase progress (upload → validate → catalog → process)
- Lower batch limit (50 vs 200) due to asset processing overhead
- Async-only (no synchronous bulk endpoint for media items)

**Workflow:**
1. `POST /v1/catalog/collections/{id}/media-items/import` with manifest → receive `jobId`
2. `GET /v1/catalog/import-jobs/{jobId}/upload-urls` → retrieve pre-signed URLs
3. Client uploads binaries to S3 via URLs
4. `POST /v1/catalog/import-jobs/{jobId}/confirm-uploads`
5. Poll `GET /v1/catalog/import-jobs/{jobId}` for progress
6. Retrieve failures via `GET /v1/catalog/import-jobs/{jobId}/items?status=failed`
```

---

### 5. `contexts/Catalog/context-overview.md`

**Section: Aggregate Ownership**

Add two new aggregates:

```markdown
| Aggregate | Responsibilities |
|---|---|
| ... (existing aggregates) ... |
| **BulkFolderImportJob** | Async large-volume folder hierarchy imports; tracks job lifecycle, chunk processing progress, per-item results |
| **BulkMediaImportJob** | Async large-volume media item imports; coordinates upload → validation → cataloging → processing pipeline; tracks multi-phase progress |
```

---

### 6. New Worker Lambda Configuration Files (Implementation)

These would be added to the codebase (not spec), but documented here for reference:

**`src/hosts/Workers.BulkFolderImport/`**
- Entry point: `BulkFolderImportWorker.cs`
- SQS trigger: `media-bulk-folder-imports` queue
- Consumes: `BulkFolderImportJobCreatedMessage`
- Dispatches: `BulkCreateFoldersByPathCommand` (existing), `RecordBulkFolderImportJobBatchResultCommand`, `CompleteBulkFolderImportJobCommand`
- Writes directly to: `media-bulk-import-job-items` table (per-item results)

**`src/hosts/Workers.BulkMediaImport/`**
- Entry point: `BulkMediaImportWorker.cs`
- SQS trigger: `media-bulk-media-imports` queue
- Consumes: `BulkMediaImportJobCreatedMessage`
- Multi-phase state machine:
  1. Issue upload URLs via `UploadAssetCommand`
  2. Wait for confirmations
  3. Subscribe to validation events
  4. Dispatch `BulkCreateMediaItemsCommand` (NEW — requires MediaItem write model extension)
  5. Subscribe to processing completion events
- Writes directly to: `media-bulk-import-job-items`, `media-bulk-import-upload-urls` tables

---

## New Integration Events

Add to `shared/integration-events.md` (if exists):

### Published by `BulkFolderImportJob`

```csharp
[MessageType("media.bulkfolderimportjob.created")]
record BulkFolderImportJobCreatedMessage(
    string TenantId,
    string JobId,
    string CollectionId,
    string InputFormat,      // "LineDelimited" | "CSV" | "JSON"
    string? InputStorageKey,
    int TotalItems,
    DateTimeOffset CreatedAt
);

[MessageType("media.bulkfolderimportjob.completed")]
record BulkFolderImportJobCompletedMessage(
    string TenantId,
    string JobId,
    int TotalSucceeded,
    int TotalFailed,
    DateTimeOffset CompletedAt
);

[MessageType("media.bulkfolderimportjob.failed")]
record BulkFolderImportJobFailedMessage(
    string TenantId,
    string JobId,
    string FailureReason,
    DateTimeOffset FailedAt
);
```

### Published by `BulkMediaImportJob`

```csharp
[MessageType("media.bulkmediaimportjob.created")]
record BulkMediaImportJobCreatedMessage(
    string TenantId,
    string JobId,
    string CollectionId,
    string InputFormat,      // "JSON" | "CSV"
    string? InputStorageKey,
    int TotalItems,
    DateTimeOffset CreatedAt
);

[MessageType("media.bulkmediaimportjob.completed")]
record BulkMediaImportJobCompletedMessage(
    string TenantId,
    string JobId,
    int TotalSucceeded,
    int TotalFailed,
    DateTimeOffset CompletedAt
);

[MessageType("media.bulkmediaimportjob.failed")]
record BulkMediaImportJobFailedMessage(
    string TenantId,
    string JobId,
    string FailureReason,
    DateTimeOffset FailedAt
);
```

---

## Queue Configuration

### SQS Queue: `media-bulk-folder-imports`

- **Subscribed to:** `media-integration-events` SNS topic
- **Filter Policy:**
  ```json
  {
    "message_type": ["media.bulkfolderimportjob.created"]
  }
  ```
- **Dead Letter Queue:** `media-bulk-folder-imports-dlq`
- **Visibility Timeout:** 900 seconds (15 min — chunk processing + DynamoDB writes)
- **Max Receive Count:** 3
- **Batch Size:** 1 (one job per invocation — job internally chunks to 200)

### SQS Queue: `media-bulk-media-imports`

- **Subscribed to:** `media-integration-events` SNS topic
- **Filter Policy:**
  ```json
  {
    "message_type": ["media.bulkmediaimportjob.created"]
  }
  ```
- **Dead Letter Queue:** `media-bulk-media-imports-dlq`
- **Visibility Timeout:** 1800 seconds (30 min — multi-phase processing)
- **Max Receive Count:** 3
- **Batch Size:** 1

---

## Infrastructure Summary

### New Lambda Functions
- `BulkFolderImportWorker` (triggered by `media-bulk-folder-imports` SQS)
- `BulkMediaImportWorker` (triggered by `media-bulk-media-imports` SQS)

### New SQS Queues
- `media-bulk-folder-imports` + DLQ
- `media-bulk-media-imports` + DLQ

### New DynamoDB Tables
- `media-bulk-folder-import-jobs` (+ GSI1: TenantId+CreatedAt, GSI2: CollectionId+CreatedAt)
- `media-bulk-media-import-jobs` (+ GSI1: TenantId+CreatedAt, GSI2: CollectionId+CreatedAt)
- `media-bulk-import-job-items` (shared, PK=TENANT#JOB#, SK=ITEM#)
- `media-bulk-folder-import-job-detail` (PK=JobId)
- `media-bulk-media-import-job-detail` (PK=JobId)
- `media-bulk-import-upload-urls` (PK=TENANT#JOB#, SK=ITEM#, TTL enabled)

### New S3 Bucket
- `media-bulk-import-inputs` (TTL: 7 days)

### Projectors to Register
- `BulkFolderImportJobSummaryProjector` (in `Projectors.ReadModel` host)
- `BulkFolderImportJobDetailProjector`
- `BulkMediaImportJobSummaryProjector`
- `BulkMediaImportJobDetailProjector`

### Integration Event Publishers to Add
- `BulkFolderImportJobIntegrationEventPublisher` (in `Catalog.WriteModel`)
- `BulkMediaImportJobIntegrationEventPublisher` (in `Catalog.WriteModel`)

---

## Related Existing Commands That Need Extension

### MediaItem Bulk Create (NEW)

`BulkMediaImportWorker` requires a new command:

**Command:** `BulkCreateMediaItemsCommand`  
**Location:** `contexts/Catalog/aggregates/MediaItem/` write model  
**Signature:**
```csharp
record BulkCreateMediaItemsCommand(
    IReadOnlyList<MediaItemCreationRequest> Items,
    BulkOperationsOptions Options
);

record MediaItemCreationRequest(
    MediaItemId MediaItemId,
    AssetId AssetId,
    FolderId FolderId,
    MediaItemTitle Title,
    RecordTypeId RecordTypeId
);
```

**Handler:** Similar to `BulkCreateFoldersCommand` handler — processes in parallel with `MaxDegreeOfParallelism = 10`, returns `succeeded`/`failed` per-item results.

---

## Testing Considerations

### Unit Tests
- `BulkFolderImportJob` aggregate state machine
- `BulkMediaImportJob` phase transitions
- Input parsers (line-delimited, CSV, JSON)

### Integration Tests
- Worker chunk processing (200-item folder batches)
- Worker multi-phase media pipeline
- Per-item result recording
- Upload URL generation + confirmation flow

### Load Tests
- 100k folder import
- 10k media import with S3 uploads
- Queue throughput and Lambda scaling

---

## Migration Path

**Phase 1:** Folder Import (simpler, no binary uploads)
1. Implement `BulkFolderImportJob` aggregate + handlers
2. Deploy `BulkFolderImportWorker` Lambda
3. Create SQS queue + SNS subscription
4. Add projectors
5. Deploy API endpoints

**Phase 2:** Media Import (complex, multi-phase)
1. Implement `BulkMediaImportJob` aggregate + handlers
2. Extend `MediaItem` write model with `BulkCreateMediaItemsCommand`
3. Deploy `BulkMediaImportWorker` Lambda
4. Create SQS queue + SNS subscription
5. Add projectors + upload URL temp table
6. Deploy API endpoints
7. Test upload confirmation flow

**Phase 3:** Monitoring & Optimization
1. CloudWatch dashboards for job throughput, failure rates
2. DLQ monitoring + replay tooling
3. Auto-retry failed chunks (idempotent batch processing)
