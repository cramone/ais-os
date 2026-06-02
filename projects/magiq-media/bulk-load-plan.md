# Bulk Load — Implementation Plan

_magiq-media · Catalog + AssetManagement_
_Date: 2026-05-11_

---

## Scope

Four bulk operations:

| Operation               | Context         | New Endpoint                                    |
| ----------------------- | --------------- | ----------------------------------------------- |
| Bulk create Collections | Catalog         | `POST /collections/bulk`                        |
| Bulk create Folders     | Catalog         | `POST /collections/{collectionId}/folders/bulk` |
| Bulk upload Assets      | AssetManagement | `POST /assets/bulk-upload`                      |
| Bulk confirm Assets     | AssetManagement | `POST /assets/bulk-confirm`                     |
| Bulk create Media Items | Catalog         | `POST /items/bulk`                              |

Each adds one new command, one new handler, and one new endpoint. No changes to existing handlers, aggregates, or domain events.

---

## Shared Design Foundations

### 1. Partial-success response envelope

All four bulk endpoints return `202 Accepted` with a typed envelope. Callers receive a complete account of what happened for every item in the request.

```csharp
sealed record BulkOperationResult<TSuccess>(
    IReadOnlyList<TSuccess>        Succeeded,
    IReadOnlyList<BulkItemError>   Failed,
    IReadOnlyList<BulkItemSkipped> Skipped
);

sealed record BulkItemError(
    int    Index,          // 0-based position in the request array
    string Name,           // or Title / FileName — human-readable identifier
    string ErrorCode,      // mirrors existing DomainError codes
    string Message,
    string? SuggestedName  // populated when ErrorCode == "DuplicateName" + strategy = Reject
);

sealed record BulkItemSkipped(
    int    Index,
    string Name,
    string Reason          // "DuplicateName" | "ParentNotFound" | etc.
);
```

A request with zero `Failed` and zero `Skipped` returns HTTP `201 Created` instead of `202`.

### 2. On-error mode

Every request body carries an optional `onError` field:

| Mode | Behaviour |
|---|---|
| `ContinueOnError` (default) | Process all items; accumulate failures; return partial results |
| `FailFast` | Abort at first failure; return nothing written; safe for all-or-nothing imports |

`FailFast` is implemented as a pre-flight-only pass followed by an abort before any writes if the pre-flight finds any issue.

### 3. Configuration — `BulkOperationsOptions`

All caps and concurrency values are driven by a single options class bound from `appsettings.json`. No handler or endpoint hardcodes these values. This keeps the synchronous path tunable without a code change, and makes lifting the caps for a future async/long-poll path a config-only operation.

```csharp
// Catalog.WriteModel.Infrastructure / AssetManagement.WriteModel.Infrastructure
// (shared by both modules via Magiq.Media.Shared or a common options assembly)

/// <summary>
/// Configuration for all bulk write operations.
/// Bound from the "BulkOperations" section of appsettings.json.
/// </summary>
public sealed class BulkOperationsOptions
{
    public const string SectionName = "BulkOperations";

    /// <summary>Maximum number of Collections per bulk-create request.</summary>
    public int MaxCollectionsPerRequest { get; init; } = 100;

    /// <summary>Maximum number of Folders per bulk-create request.</summary>
    public int MaxFoldersPerRequest { get; init; } = 200;

    /// <summary>Maximum number of Assets per bulk-upload or bulk-confirm request.</summary>
    public int MaxAssetsPerRequest { get; init; } = 50;

    /// <summary>Maximum number of Media Items per bulk-create request.</summary>
    public int MaxMediaItemsPerRequest { get; init; } = 200;

    /// <summary>
    /// Degree of parallelism for the write phase of every bulk handler.
    /// Bounds DynamoDB throughput and Lambda memory pressure.
    /// </summary>
    public int WritePhaseMaxDegreeOfParallelism { get; init; } = 10;

    /// <summary>
    /// Maximum number of retry attempts per item on ConcurrencyConflict
    /// or NameReservationConflictException before the item is marked Failed.
    /// </summary>
    public int MaxRetryAttemptsPerItem { get; init; } = 3;

    /// <summary>
    /// Base delay in milliseconds for the first retry back-off interval.
    /// Each subsequent attempt doubles: BaseRetryDelayMs, ×2, ×4, ...
    /// </summary>
    public int BaseRetryDelayMs { get; init; } = 100;
}
```

**Registration** — once in each module's `ServiceCollectionExtensions`:

```csharp
services.Configure<BulkOperationsOptions>(
    configuration.GetSection(BulkOperationsOptions.SectionName));
```

**`appsettings.json` defaults** (shown explicitly for clarity; these match the coded defaults so the file entry is optional):

```json
"BulkOperations": {
  "MaxCollectionsPerRequest": 100,
  "MaxFoldersPerRequest": 200,
  "MaxAssetsPerRequest": 50,
  "MaxMediaItemsPerRequest": 200,
  "WritePhaseMaxDegreeOfParallelism": 10,
  "MaxRetryAttemptsPerItem": 3,
  "BaseRetryDelayMs": 100
}
```

**Injection into handlers and endpoints:**

```csharp
// Handler — receives options via constructor injection
public sealed class BulkCreateCollectionsHandler(
    ICollectionRepository repository,
    INameReservationService nameReservationService,
    IAmazonDynamoDB dynamo,
    IOptions<BulkOperationsOptions> options) : CommandHandler<...>
{
    private readonly BulkOperationsOptions _options = options.Value;
    // use _options.WritePhaseMaxDegreeOfParallelism, _options.MaxRetryAttemptsPerItem, etc.
}

// Endpoint — validates request size before dispatching
public override async Task HandleAsync(BulkCreateCollectionsRequest req, CancellationToken ct)
{
    if (req.Items.Count > _options.MaxCollectionsPerRequest)
    {
        AddError($"Request exceeds the maximum of {_options.MaxCollectionsPerRequest} collections per request.");
        await SendErrorsAsync(400, ct);
        return;
    }
    // ...
}
```

The endpoint owns the size-cap guard (it's a transport concern). The handler owns retry count and DOP (they're processing concerns). Both read from the same `BulkOperationsOptions` instance.

### 4. Within-batch size limits

Caps are enforced by each endpoint before the command is dispatched, using `BulkOperationsOptions` values. Exceeded limits → `400 Bad Request` before any processing begins.

| Operation | Default cap | Config key |
|---|---|---|
| Collections | 100 | `MaxCollectionsPerRequest` |
| Folders | 200 | `MaxFoldersPerRequest` |
| Assets (upload + confirm) | 50 | `MaxAssetsPerRequest` |
| Media Items | 200 | `MaxMediaItemsPerRequest` |

### 5. Write-phase concurrency

Use `Parallel.ForEachAsync` with `MaxDegreeOfParallelism` sourced from `BulkOperationsOptions.WritePhaseMaxDegreeOfParallelism` (default: 10). This bounds DynamoDB throughput and Lambda memory pressure while still being ~10× faster than serial.

```csharp
await Parallel.ForEachAsync(validatedItems,
    new ParallelOptions { MaxDegreeOfParallelism = _options.WritePhaseMaxDegreeOfParallelism },
    async (item, ct) =>
    {
        // name reservation (Tier 2) + repository.SaveAsync
    });
```

### 6. Retry on concurrency conflict

For every individual write that raises `NameReservationConflictException` or returns `ConcurrencyConflict`, retry up to `BulkOperationsOptions.MaxRetryAttemptsPerItem` times (default: 3) with exponential back-off starting at `BaseRetryDelayMs` (default: 100 ms → 200 ms → 400 ms) — matching the existing single-item pattern. After exhausting retries, record as `Failed` with `ErrorCode = "ConcurrencyConflict"`.

### 7. Idempotency

Bulk endpoints accept the `IdempotencyKey` header. The platform `Magiq.AspNetCore.Idempotency` middleware caches the complete response envelope for the TTL window. A replayed key with the same payload returns the cached envelope — no re-processing.

### 8. Pre-flight batch name uniqueness check (Tier 1)

The most important performance optimisation. Instead of N sequential `IsNameAvailableAsync` point-reads, fire a single `BatchGetItem` against `media-name-reservations` covering every name in the request. DynamoDB `BatchGetItem` supports up to 100 keys per call; for requests exceeding 100 items, issue multiple concurrent batches.

```csharp
// Build all reservation keys for the batch
var keys = items.Select(i => new Dictionary<string, AttributeValue>
{
    ["PK"] = new AttributeValue { S = $"TENANT#{tenantId}#SCOPE#{scopeKey}#NAME#{i.Name.ToNormalizedKey()}" }
}).ToList();

// Issue in chunks of 100 (DynamoDB BatchGetItem limit)
var takenNames = new HashSet<string>();
foreach (var chunk in keys.Chunk(100))
{
    var response = await dynamo.BatchGetItemAsync(new BatchGetItemRequest
    {
        RequestItems = new Dictionary<string, KeysAndAttributes>
        {
            [NameReservationsTable] = new KeysAndAttributes
            {
                Keys = chunk.ToList(),
                ConsistentRead = true   // must be consistent — same as single-item Tier 1
            }
        }
    }, ct);
    foreach (var item in response.Responses[NameReservationsTable])
        takenNames.Add(item["NormalizedName"].S);
}
```

`ConsistentRead = true` is non-negotiable — same requirement as single-item Tier 1 checks.

### 9. Within-batch duplicate detection

Before the Tier 1 check, scan the request for duplicate names within the batch itself (normalised lower-case trim). Duplicates within a batch are a caller error — classify per the `onDuplicate` strategy (§ Name conflict resolution strategies below).

---

## Part 1 — Bulk Create Collections

### Pre-flight checks (before any writes)

1. Validate request size (≤ 100).
2. Normalise all names (`Trim().ToLowerInvariant()`).
3. Detect within-batch duplicates.
4. Single `BatchGetItem` (ConsistentRead) across all names in `media-name-reservations` at scope `collection`. Collect taken names.
5. Apply `onDuplicate` strategy to any taken or within-batch duplicate names (see § Name conflict resolution strategies).
6. If `onError = FailFast` and any items are invalid → return `400` with pre-flight failure list, no writes.

### Write phase

For each item surviving pre-flight, in parallel (DOP = 10):

1. `Collection.Create(...)` — aggregate factory, no load.
2. `nameReservationService.ReserveAsync(tenantId, ScopeKeys.Collection, name, collectionId)` — Tier 2.
3. `repository.SaveAsync(collection)`.
4. On `NameReservationConflictException` → retry up to 3× or record as `Failed`.

### New files

```
Catalog.WriteModel/Commands/Collections/BulkCreateCollections/
  BulkCreateCollectionsCommand.cs
  BulkCreateCollectionsHandler.cs
Catalog.WriteModel.Endpoints/V1/Collections/BulkCreateCollections/
  BulkCreateCollectionsEndpoint.cs
  BulkCreateCollectionsRequest.cs
  BulkCreateCollectionItem.cs         // per-item input shape
  BulkCreateCollectionsResponse.cs
```

### Request shape

```json
POST /collections/bulk

{
  "items": [
    {
      "collectionId": "018f...",        // caller-generated UUID v7; optional — server generates if omitted
      "name": "Q1 Campaign Assets",
      "description": "...",
      "visibility": "Private",
      "defaultMediaProfileId": null
    }
  ],
  "onError": "ContinueOnError",
  "onDuplicate": "Reject"
}
```

### Response shape (202)

```json
{
  "succeeded": [
    { "index": 0, "collectionId": "018f...", "name": "Q1 Campaign Assets" }
  ],
  "failed": [
    { "index": 1, "name": "Existing Name", "errorCode": "DuplicateName",
      "message": "A collection named 'Existing Name' already exists.",
      "suggestedName": "Existing Name (1)" }
  ],
  "skipped": []
}
```

### Handler outline

```csharp
public sealed class BulkCreateCollectionsHandler(
    ICollectionRepository repository,
    INameReservationService nameReservationService,
    IAmazonDynamoDB dynamo)
    : CommandHandler<BulkCreateCollectionsCommand, BulkOperationResult<BulkCreatedCollection>>
{
    protected override async Task<Result<BulkOperationResult<...>, IDomainError>> ExecuteAsync(
        BulkCreateCollectionsCommand command, CancellationToken ct)
    {
        // 1. Within-batch duplicate detection
        // 2. Tier 1 — batch name check (BatchGetItem, ConsistentRead)
        // 3. Apply onDuplicate strategy → partition into: toCreate / failed / skipped
        // 4. FailFast short-circuit if any failures and mode == FailFast
        // 5. Parallel write phase (DOP=10):
        //    Collection.Create → ReserveAsync (retry 3×) → repository.SaveAsync
        // 6. Return BulkOperationResult
    }
}
```

---

## Part 2 — Bulk Create Folders

Folders are the most complex bulk operation because:
- Name uniqueness is scoped per **parent folder** (or collection root), not globally.
- A bulk request may contain parent-child folder relationships that must respect creation order.
- Depth limit (max 10 levels) must be checked per item.

### Topological ordering

Before any processing, build a dependency graph for items whose `parentFolderId` is within the same batch. Topological sort (Kahn's algorithm) establishes creation order. Cycles → `400 Bad Request`. Items whose `parentFolderId` references an entity outside the batch (existing folder or null = root) have no intra-batch dependency and can be processed in the first wave.

```
Wave 0: items with parentFolderId = null or pointing to existing folder
Wave 1: items whose parent is in Wave 0
Wave 2: items whose parent is in Wave 1
...
```

Waves are processed sequentially. Within each wave, writes are parallel (DOP = 10).

### Pre-flight checks (per scope group)

1. Validate request size (≤ 200).
2. Resolve existing parent folders: batch `GetItem` for all unique `parentFolderId` values that are not in-batch. Collect depth counters.
3. Detect within-scope duplicates within the batch (normalise name per parent scope).
4. **Batch Tier 1 name check** — group items by scope key (`ScopeKeys.RootFolder(collectionId)` or `ScopeKeys.Folder(parentId)`). For each scope group, fire one `BatchGetItem` on `media-name-reservations`. This replaces N serial `IsNameAvailableAsync` calls with at most `ceil(N/100)` batch calls.
5. Check depth per item: parent depth (from counter or in-batch running depth) + 1 ≤ 10.
6. Apply `onDuplicate` strategy.
7. `FailFast` short-circuit.

### Write phase (wave-by-wave)

For each wave, for each item (parallel, DOP = 10):

1. `Folder.Create(...)`.
2. `nameReservationService.ReserveAsync(tenantId, scopeKey, name, folderId)` — Tier 2.
3. `counterService.IncrementCounterAsync(tenantId, parentScopeKey, "child-folders")`.
4. Set depth counter for the new folder (`counterService.IncrementCounterAsync` × depth levels — mirrors `CreateFolderHandler`).
5. `repository.SaveAsync(folder)`.

In-batch folder IDs are added to a local lookup map after their wave completes so child waves can resolve parent depth and scope keys without extra reads.

### New files

```
Catalog.WriteModel/Commands/Folders/BulkCreateFolders/
  BulkCreateFoldersCommand.cs
  BulkCreateFoldersHandler.cs
Catalog.WriteModel.Endpoints/V1/Folders/BulkCreateFolders/
  BulkCreateFoldersEndpoint.cs
  BulkCreateFoldersRequest.cs
  BulkCreateFolderItem.cs
  BulkCreateFoldersResponse.cs
```

### Request shape

```json
POST /collections/{collectionId}/folders/bulk

{
  "items": [
    { "folderId": "018f...", "parentFolderId": null,    "name": "Season 1" },
    { "folderId": "018g...", "parentFolderId": "018f..","name": "Episode 01" }
  ],
  "onError": "ContinueOnError",
  "onDuplicate": "Reject"
}
```

Note: `parentFolderId` can reference either an existing folder or another `folderId` within the same batch. Items referencing an in-batch parent that failed creation are automatically marked `Failed` with `ErrorCode = "ParentCreationFailed"`.

### Handler outline

```csharp
public sealed class BulkCreateFoldersHandler(...) : CommandHandler<...>
{
    protected override async Task<...> ExecuteAsync(BulkCreateFoldersCommand cmd, CancellationToken ct)
    {
        // 1. Resolve existing parents (batch GetItem)
        // 2. Topological sort → waves
        // 3. Per scope group: batch Tier 1 check (BatchGetItem, ConsistentRead)
        // 4. Apply onDuplicate strategy
        // 5. FailFast short-circuit
        // 6. Wave loop (sequential waves, parallel items within wave):
        //    - Folder.Create → ReserveAsync (retry 3×)
        //    - counterService depth + child-folder counters
        //    - repository.SaveAsync
        //    - Update in-batch lookup map for child waves
        // 7. Return BulkOperationResult
    }
}
```

---

## Part 3 — Bulk Upload Assets

Assets have no name-uniqueness constraint. The bulk upload path is primarily about:
- Efficient quota aggregation (one quota reservation for the total batch, not N individual calls).
- Per-item MediaItem existence + archive + file-size checks.
- Returning a pre-signed PUT URL per item so the client can upload in parallel.

### Pre-flight checks

1. Validate request size (≤ 50) and individual file sizes.
2. For items with `mediaItemId` set: batch `GetItem` on `media-item-capability-refs` for all distinct `mediaItemId` values. Classify: not found → `Failed`, archived → `Failed`, file too large → `Failed`.
3. Determine quota-exempt items (items whose `mediaItemId` references a profile without the `Processing` capability).
4. Aggregate total `SizeBytes` of non-exempt items. Fire a **single** `billing.CheckQuotaAsync(ownerId, totalNonExemptBytes)` call.
   - If quota fails → return `400 QuotaExceeded` for the entire request (quota is not partial).
   - This is more efficient than N individual quota calls and gives the billing system a single atomic check.

### Write phase (parallel, DOP = 10)

For each item:

1. `storageKeyGenerator.Generate(...)`.
2. `presignedUrlService.GeneratePutUrlAsync(...)` — 15-minute TTL, signed `Content-Type` + exact `Content-Length`.
3. `Asset.InitiateUpload(...)` aggregate factory.
4. `repository.SaveAsync(asset)`.

No name reservation. No retry needed (no concurrency conflict surface for new aggregates with UUID v7 IDs).

### New files

```
AssetManagement.WriteModel/Commands/BulkInitiateAssetUpload/
  BulkInitiateAssetUploadCommand.cs
  BulkInitiateAssetUploadHandler.cs
AssetManagement.WriteModel.Endpoints/V1/BulkInitiateAssetUpload/
  BulkInitiateAssetUploadEndpoint.cs
  BulkInitiateAssetUploadRequest.cs
  BulkInitiateAssetUploadItem.cs
  BulkInitiateAssetUploadResponse.cs
```

### Request shape

```json
POST /assets/bulk-upload

{
  "items": [
    {
      "assetId": "018f...",
      "mediaItemId": "018e...",   // optional
      "originalFileName": "hero.jpg",
      "contentType": "Image",
      "sizeBytes": 2048000
    }
  ],
  "onError": "ContinueOnError"
}
```

### Response shape (202)

```json
{
  "succeeded": [
    {
      "index": 0,
      "assetId": "018f...",
      "uploadUrl": "https://media-source.s3.amazonaws.com/...",
      "expiresAt": "2026-05-11T12:15:00Z"
    }
  ],
  "failed": [
    { "index": 1, "assetId": "018g...", "errorCode": "MediaItemArchived",
      "message": "Media item '018e...' is archived." }
  ],
  "skipped": []
}
```

After uploading each file to S3, clients call `POST /assets/bulk-confirm` (see Part 3b) to confirm all successfully uploaded assets in a single call.

### Quota strategy note

The single-call quota aggregation approach is a notable difference from the single-item path. The trade-off: if 1 of 50 items has an individual issue (wrong content type, archived item), that item is classified as `Failed` pre-flight and excluded from the quota total before the billing call is made. This prevents a large-batch quota rejection from masking per-item errors.

---

## Part 3b — Bulk Confirm Assets

The confirm step is the second half of the upload contract: the client has PUT each file to its pre-signed S3 URL and now calls a single endpoint to transition all successfully uploaded assets from `Pending → Validating`. This mirrors `POST /assets/{assetId}/confirm` but fans out across a batch, running each asset's defence-in-depth HEAD checks in parallel.

### What each confirm does (mirrors single-item handler)

For every asset in the request the handler reproduces the three-guard sequence from `ConfirmAssetUploadHandler` exactly:

1. Load asset; verify `Status == Pending` (idempotent exit if already `Validating` or `Active`).
2. `IS3InspectionService.HeadObjectAsync(asset.StorageKey)` — confirms the object exists in S3.
3. **Guard 1 — content-type**: actual `Content-Type` must match declared `asset.ContentType`.
4. **Guard 2 — declared-size check (primary)**: `actual ContentLength ≤ asset.SizeBytes`.
5. **Guard 3 — profile-limit check (secondary, item-scoped only)**: `actual ContentLength ≤ profile.MaxFileSizeBytes` (re-checked via `IMediaItemCapabilityService`).
6. `asset.ConfirmUpload(now)` → `Pending → Validating`.
7. `repository.SaveAsync(asset)`.

Any guard failure is recorded as `Failed` with a validation error code. The `onError` mode determines whether processing continues for remaining items.

### Pre-flight checks

1. Validate request size (≤ 50 — same cap as bulk upload; each item requires one S3 HEAD call).
2. Load all assets in parallel via a batch repository read. Assets not found → `Failed` with `ResourceNotFound`. Assets not in `Pending` state:
   - `Validating` / `Active` → idempotent `Succeeded` (already confirmed; no re-processing).
   - Any other terminal state (`ValidationFailed`, `ContainsVirus`, `MultipartAborted`, etc.) → `Failed` with `ErrorCode = "AssetNotConfirmable"` and the current status in the message.
   - `Multipart` mode assets in `Pending` state → `Failed` with `ErrorCode = "MultipartUploadPending"` — these must be completed via `CompleteMultipartUpload` first, not confirmed directly.

### Write phase (parallel, DOP = 10)

S3 HEAD calls are I/O-bound and independent — full DOP = 10 is appropriate here. The `MediaItemCapabilityService` calls (Guard 3) are also parallel; the service already handles per-tenant DynamoDB point reads.

```csharp
await Parallel.ForEachAsync(confirmableAssets, new ParallelOptions { MaxDegreeOfParallelism = 10 }, async (asset, ct) =>
{
    var meta = await s3InspectionService.HeadObjectAsync(asset.StorageKey, ct);
    // Guard 1, 2, 3 ...
    asset.ConfirmUpload(now);
    await repository.SaveAsync(asset, ct);
});
```

### New files

```
AssetManagement.WriteModel/Commands/BulkConfirmAssetUpload/
  BulkConfirmAssetUploadCommand.cs
  BulkConfirmAssetUploadHandler.cs
AssetManagement.WriteModel.Endpoints/V1/BulkConfirmAssetUpload/
  BulkConfirmAssetUploadEndpoint.cs
  BulkConfirmAssetUploadRequest.cs
  BulkConfirmAssetUploadResponse.cs
```

### Request shape

```json
POST /assets/bulk-confirm

{
  "assetIds": [
    "018f-...",
    "018g-...",
    "018h-..."
  ],
  "onError": "ContinueOnError"
}
```

The request is intentionally minimal — no per-item body beyond the ID. All required state (storage key, declared size, content type, media item link) lives on the already-persisted `Asset` aggregate.

### Response shape (202)

```json
{
  "succeeded": [
    { "index": 0, "assetId": "018f-..." },
    { "index": 1, "assetId": "018g-..." }
  ],
  "failed": [
    {
      "index": 2,
      "assetId": "018h-...",
      "errorCode": "S3ObjectNotFound",
      "message": "S3 object not found for asset 018h-.... The pre-signed URL may have expired before the upload completed."
    }
  ],
  "skipped": []
}
```

### Error codes specific to bulk confirm

| `errorCode` | Cause | Caller action |
|---|---|---|
| `S3ObjectNotFound` | Client never PUT to the pre-signed URL, or URL expired (15 min TTL) | Re-initiate upload via `POST /assets/bulk-upload` for this asset ID, then re-confirm |
| `ContentTypeMismatch` | Actual S3 object MIME type doesn't match declared `contentType` | Re-initiate with correct `contentType` |
| `DeclaredSizeExceeded` | Actual S3 object is larger than `asset.SizeBytes` (Guard 2) | Re-initiate with correct `sizeBytes`; investigate client for quota abuse |
| `ProfileLimitExceeded` | Actual size exceeds the profile's `MaxFileSizeBytes` (Guard 3) | Re-initiate with a smaller file or a profile with a higher limit |
| `MultipartUploadPending` | Asset is `Pending` with `UploadMode = Multipart` | Call `POST /assets/{assetId}/multipart/complete` first |
| `AssetNotConfirmable` | Asset is in a terminal state (e.g. `ValidationFailed`) | Cannot be confirmed; inspect current status |
| `ResourceNotFound` | Asset ID does not exist for this tenant | Verify the ID |

### Pairing with bulk upload

The typical client workflow for a full bulk ingest cycle:

```
1. POST /assets/bulk-upload         → receive { assetId, uploadUrl } per item
2. PUT  {uploadUrl}                 → client uploads each file directly to S3 (parallel, no server involvement)
3. POST /assets/bulk-confirm        → confirm all uploads in one call
4. (async) pipeline processes each asset: Validating → Active
```

Failed confirms (e.g. `S3ObjectNotFound`) indicate the client failed to upload that file in step 2. The caller re-submits only those asset IDs via `POST /assets/bulk-upload` (new pre-signed URLs are issued for the same `assetId`) and then re-confirms.

---

## Part 4 — Bulk Create Media Items

### Pre-flight checks

1. Validate request size (≤ 200).
2. Resolve all distinct `folderId` values: batch `GetItem` on `media-folders`. Build a map of `folderId → { CollectionId, IsArchived }`. Items targeting missing or archived folders → `Failed`.
3. Resolve all distinct `mediaProfileId` values: batch `GetItem` on `media-profiles` (projection: `Status`, `CompiledTemplate`, `AssetDefinitions`, `RecordTypeRefs`, `ReviewPolicy`, `CheckoutPolicy`, `Capabilities`). Items with missing or non-`Published` profiles → `Failed`. **Cache the snapshot per `MediaProfileId` within the handler** — avoids O(N) reads when many items share the same profile.
4. **Batch Tier 1 title check** — group items by `folderId`. For each folder group, fire one `BatchGetItem` on `media-name-reservations` at scope `ScopeKeys.MediaItemTitle(folderId)`. Collect taken titles.
5. Within-batch duplicate detection per folder scope (normalised titles).
6. Apply `onDuplicate` strategy.
7. `FailFast` short-circuit.

### Write phase (parallel, DOP = 10)

For each item:

1. Build `profileSnapshot = profile.CompiledTemplate.ToSnapshot()` (from cached profile read above — zero extra I/O).
2. Build `snapshotRecordTypeVersions` from cached `profile.RecordTypeRefs`.
3. `MediaItem.Create(...)` aggregate factory.
4. `nameReservationService.ReserveAsync(tenantId, ScopeKeys.MediaItemTitle(folderId), title, mediaItemId)` — Tier 2. Retry 3× on conflict.
5. `counterService.IncrementCounterAsync(tenantId, ScopeKeys.Folder(folderId), "active-items")`.
6. `repository.SaveAsync(mediaItem)`.

### New files

```
Catalog.WriteModel/Commands/MediaItems/BulkCreateMediaItems/
  BulkCreateMediaItemsCommand.cs
  BulkCreateMediaItemsHandler.cs
Catalog.WriteModel.Endpoints/V1/MediaItems/BulkCreateMediaItems/
  BulkCreateMediaItemsEndpoint.cs
  BulkCreateMediaItemsRequest.cs
  BulkCreateMediaItemItem.cs
  BulkCreateMediaItemsResponse.cs
```

### Request shape

```json
POST /items/bulk

{
  "items": [
    {
      "mediaItemId": "018f...",
      "mediaProfileId": "018e...",
      "title": "Chinatown — Director's Cut",
      "description": "...",
      "folderId": "018d..."
    }
  ],
  "onError": "ContinueOnError",
  "onDuplicate": "Reject"
}
```

### Handler outline

```csharp
public sealed class BulkCreateMediaItemsHandler(
    IMediaItemRepository repository,
    IFolderRepository folderRepository,
    IMediaProfileRepository mediaProfileRepository,
    INameReservationService nameReservationService,
    IUniquenessCounterService counterService,
    IAmazonDynamoDB dynamo)
    : CommandHandler<BulkCreateMediaItemsCommand, BulkOperationResult<BulkCreatedMediaItem>>
{
    protected override async Task<...> ExecuteAsync(BulkCreateMediaItemsCommand cmd, CancellationToken ct)
    {
        // 1. Batch GetItem for all distinct folderIds → folder map
        // 2. Batch GetItem for all distinct mediaProfileIds → profile cache
        // 3. Per-folder group: batch Tier 1 title check (BatchGetItem, ConsistentRead)
        // 4. Within-batch duplicate detection per folder scope
        // 5. Apply onDuplicate strategy
        // 6. FailFast short-circuit
        // 7. Parallel write phase (DOP=10):
        //    profileSnapshot = profileCache[profileId].CompiledTemplate.ToSnapshot()
        //    MediaItem.Create → ReserveAsync (retry 3×) → counterService.Increment → repository.SaveAsync
        // 8. Return BulkOperationResult
    }
}
```

---

## Name Conflict Resolution Strategies

All three Collection, Folder, and MediaItem bulk operations accept an `onDuplicate` field. Assets are excluded (no uniqueness constraint).

### Strategy 1: `Reject` (default)

Item is placed in the `failed` list with `ErrorCode = "DuplicateName"`. A `suggestedName` is computed by appending ` (1)`, ` (2)`, ... up to a max of 99 suffix attempts using the results of the Tier 1 batch check. If no suffix is free, `suggestedName` is omitted. The caller decides whether to retry with the suggested name.

```json
{
  "index": 2,
  "name": "Season 1",
  "errorCode": "DuplicateName",
  "message": "A folder named 'Season 1' already exists under this parent.",
  "suggestedName": "Season 1 (1)"
}
```

This is safe, explicit, and puts naming control in the caller's hands. Recommended for production imports.

### Strategy 2: `Skip`

Item is placed in the `skipped` list. No error is raised. Useful for idempotent re-runs of an import where some items were already created.

```json
{ "index": 2, "name": "Season 1", "reason": "DuplicateName" }
```

Note: `Skip` does not verify that the existing item has the same properties as the requested item. It only verifies name collision. If the caller needs to detect semantic differences (e.g., different `visibility` on a collection), they must query the existing item separately.

### Strategy 3: `AutoSuffix`

The handler automatically appends ` (1)`, ` (2)`, ... to the requested name until it finds an available name, up to a cap of 99 attempts per item. If no suffix resolves within 99 attempts, the item is placed in `failed` with `ErrorCode = "AutoSuffixExhausted"`.

`AutoSuffix` requires additional name-availability lookups during the write phase (sequential Tier 1 reads per attempt). Use it only when the caller cannot control name uniqueness (e.g., ingesting from an external source). For large batches, `Skip` or `Reject` are more predictable.

The auto-suffix walk uses a separate consistency check per attempt (not batch) since the suffix resolution is inherently sequential.

---

## Handling Failures, Retries, and Alterations

### Scenario matrix

| Failure | Mode | Recommended action |
|---|---|---|
| `DuplicateName` + `Reject` | `ContinueOnError` | Caller corrects name (or uses `suggestedName`) and re-submits only the failed items |
| `DuplicateName` + `Skip` | — | No action needed; item already exists |
| `DuplicateName` + `AutoSuffix` | — | Server resolves automatically |
| `ConcurrencyConflict` (after 3× retry) | Either | Caller re-submits failed items; server retries again |
| `ParentNotFound` (folder) | Either | Caller verifies parent ID or creates parent first |
| `ParentCreationFailed` (in-batch) | Either | Parent item is also in `failed`; fix the parent, re-submit both |
| `MediaItemArchived` (asset upload) | Either | Caller either un-archives the item first or chooses a different target |
| `QuotaExceeded` (asset bulk) | — | Request-level failure; reduce batch size or total `sizeBytes` |
| `ProfileNotPublished` (media item) | Either | Caller ensures profile is published before bulk ingest |
| `DepthExceeded` (folder) | Either | Restructure folder tree; max depth is 10 |

### Re-submission pattern

All bulk endpoints accept caller-generated IDs (UUID v7). A re-submission of a failed item with the same ID is safe: if the server already successfully wrote that ID (e.g., the response was lost in transit), the `attribute_not_exists(AggregateVersion)` conditional write will return `ConditionalCheckFailedException`, which the handler treats as success — the aggregate already exists. The platform idempotency middleware covers the full-request replay case.

For the altered-and-retry case (e.g., corrected name), the caller must supply a new caller-generated ID since the original ID was never persisted.

---

## Observability

Each bulk handler logs at the end of execution:

```
BulkCreateCollections: succeeded=87 failed=3 skipped=2 tenantId={} durationMs={}
```

Individual item failures are logged at `WARN` level with `index`, `name`, and `errorCode`. Use CloudWatch Metric Filters on `errorCode` to track `DuplicateName` rates per tenant (signals a client integration issue).

Add a structured property `bulkOperationType` to all log entries within a bulk handler so CloudWatch Insights can correlate across handler invocations.

---

## Implementation Sequence

1. **Shared infrastructure** — implement `BulkOperationsOptions` (with `appsettings.json` binding and `ServiceCollectionExtensions` registration), `BulkOperationResult<T>`, `BulkItemError`, `BulkItemSkipped`, and the `BatchGetItem` helper for name reservation checks. Add to `Catalog.WriteModel.Infrastructure` / `AssetManagement.WriteModel.Infrastructure`.

2. **Bulk Create Collections** — simplest case; no intra-item ordering, no profile resolution. Proves the pattern end-to-end including the partial-success envelope.

3. **Bulk Upload Assets** — no uniqueness concern; validates the quota-aggregation approach and the pre-signed URL fan-out response shape.

4. **Bulk Confirm Assets** — pairs directly with step 3; implement immediately after to complete the upload cycle. Validates the S3 HEAD fan-out pattern and the confirm-specific error taxonomy.

5. **Bulk Create Media Items** — adds profile snapshot caching and per-folder batch Tier 1 checks on top of the collection pattern.

6. **Bulk Create Folders** — most complex; adds topological sort and wave-based execution. Implement last once the other four are proven.

---

## Out of Scope

- Bulk multipart uploads — the `InitiateMultipartUpload` path has its own per-part URL generation complexity; excluded from this plan.
- Bulk update / bulk archive — these involve loading existing aggregates and carry different concurrency profiles. Separate plan.
- Progress streaming / long-poll — all four endpoints return synchronously within the Lambda timeout. If batch sizes grow beyond these limits, a job-queue pattern is warranted. Out of scope for v1 of bulk.
