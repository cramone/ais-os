# Asset — Read Model

_Context: `AssetManagement`_
_Aggregate: `Asset`_

---

## Read Models

### `media-assets` (DynamoDB)

Summary table. Powers list queries by `MediaItemId` and status filters.

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#{AssetId}` |
| `TenantId` | `string` | Plain attribute |
| `AssetId` | `string` | |
| `MediaItemId` | `string?` | Null for standalone media-assets |
| `OwnerId` | `string` | |
| `Status` | `string` | `AssetStatus` enum value |
| `StorageTier` | `string` | `StorageTier` enum value (`Standard`, `StandardIA`, `GlacierInstant`, `DeepArchive`). Updated by `AssetStorageTierTransitioned`. |
| `ContentType` | `string` | `MediaContentType` enum value |
| `OriginalFileName` | `string` | |
| `RoleName` | `string?` | |
| `CreatedAt` | `string` | ISO 8601 |
| `ProjectedVersion` | `long` | Dedup guard |
| `EventId` | `string` | Last applied event ID (traceability) |

### `media-asset-detail` (DynamoDB)

Full detail table. Powers `GET /media-assets/{assetId}`.

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#{AssetId}` |
| `TenantId` | `string` | Plain attribute |
| `AssetId` | `string` | |
| `MediaItemId` | `string?` | |
| `OwnerId` | `string` | |
| `Status` | `string` | |
| `ContentType` | `string` | |
| `OriginalFileName` | `string` | |
| `StorageKey` | `string` | Bucket + key |
| `RoleName` | `string?` | |
| `IsPrimary` | `bool` | |
| `Tags` | `string[]` | |
| `Renditions` | `Rendition[]` | `{ renditionType, storageKey, contentType, width?, height?, sizeBytes }` |
| `Metadata` | `object` | Full `AssetMetadata` shape; null fields omitted |
| `CreatedAt` | `string` | ISO 8601 |
| `ArchivedAt` | `string?` | |
| `DeletedAt` | `string?` | |
| `ProjectedVersion` | `long` | Dedup guard |
| `LastAssetEventVersion` | `long` | Per-stream dedup for `AssetAttachedToMediaItem` events |
| `EventId` | `string` | |

---

## Projection Handlers

### `AssetSummaryProjector`

**Trigger:** `media-projector` SQS queue
**Target:** `media-assets`

| Event | Write |
|---|---|
| `AssetUploadInitiated` | INSERT row (status: `Pending`, `UploadMode: SinglePart`) |
| `AssetMultipartUploadInitiated` | INSERT row (status: `Pending`, `UploadMode: Multipart`) |
| `AssetUploadConfirmed` | UPDATE status → `Validating` |
| `AssetMultipartUploadAborted` | UPDATE status → `MultipartAborted` |
| `AssetValidationPassed` | UPDATE status → `Processing` or `Active` (per `HasProcessingCapability`) |
| `AssetValidationFailed` | UPDATE status → `ValidationFailed` |
| `AssetInfectionDetected` | UPDATE status → `ContainsVirus` |
| `AssetProcessingStarted` | UPDATE status → `Processing` |
| `AssetProcessingCompleted` | UPDATE status → `Active` |
| `AssetProcessingFailed` | UPDATE status → `ProcessingFailed` |
| `AssetTagged` | UPDATE `Tags` list |
| `AssetArchived` | UPDATE status → `Archived`; set `ArchivedAt` |
| `AssetStorageTierTransitioned` | UPDATE `StorageTier` |
| `AssetDeleted` | UPDATE status → `Deleted`; set `DeletedAt` |
| `AssetAttachedToMediaItem` | UPDATE `MediaItemId`, `RoleName` |
| `AssetDetachedFromMediaItem` | UPDATE clear `MediaItemId`, `RoleName` |

**TenantId extraction:** From SQS message attribute envelope — never from event payload body.
**Idempotency:** `ProjectedVersion` dedup guard on all writes. `ConditionalCheckFailedException` treated as success.

---

### `AssetDetailProjector`

**Trigger:** `media-projector` SQS queue
**Target:** `media-asset-detail`

| Event | Write |
|---|---|
| `AssetUploadInitiated` | INSERT row (status: `Pending`, `UploadMode: SinglePart`) |
| `AssetMultipartUploadInitiated` | INSERT row (status: `Pending`, `UploadMode: Multipart`) |
| `AssetUploadConfirmed` | UPDATE status → `Validating` |
| `AssetMultipartUploadAborted` | UPDATE status → `MultipartAborted` |
| `AssetValidationPassed` | UPDATE status → `Processing` or `Active` (per `HasProcessingCapability`) |
| `AssetValidationFailed` | UPDATE status → `ValidationFailed` |
| `AssetInfectionDetected` | UPDATE status → `ContainsVirus` |
| `AssetProcessingStarted` | UPDATE status → `Processing` |
| `AssetProcessingCompleted` | UPDATE status → `Active`; stamp `Renditions`, `Metadata` |
| `AssetProcessingFailed` | UPDATE status → `ProcessingFailed` |
| `AssetTagged` | UPDATE `Tags` list |
| `AssetArchived` | UPDATE status → `Archived`; set `ArchivedAt` |
| `AssetStorageTierTransitioned` | UPDATE `StorageTier` |
| `AssetDeleted` | UPDATE status → `Deleted`; set `DeletedAt` |
| `AssetAttachedToMediaItem` | UPDATE `MediaItemId`, `RoleName` |
| `AssetDetachedFromMediaItem` | UPDATE clear `MediaItemId`, `RoleName` |

**TenantId extraction:** From SQS message attribute envelope — never from event payload body.
**Idempotency:** `ProjectedVersion` dedup guard on all writes. `ConditionalCheckFailedException` treated as success.

---

## Queries

| Query | Description |
|---|---|
| `GetAssetByIdQuery(TenantId, AssetId)` | Load full asset detail |
| `ListAssetsByMediaItemQuery(TenantId, MediaItemId, Status?)` | List media-assets for a MediaItem, optionally filtered by status |

---

## Query Handlers

Handlers extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and inject `IReadModelReader<T>` from `Magiq.Platform.ReadModel`. PK construction and ownership resolution are handled by the framework. Handlers return DTOs only — no domain objects or event payloads cross the read boundary.

| Handler | Reader | Method |
|---|---|---|
| `GetAssetByIdHandler` | `IReadModelReader<AssetDetailReadModel>` | `GetAsync(request, ct)` |
| `ListAssetsByMediaItemHandler` | `IReadModelReader<AssetSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `AssetSummaryReadModel`

Targets `media-assets` (DynamoDB). Powers `ListAssetsByMediaItem`. Omits storage key, renditions, and metadata to keep list reads cheap.

```csharp
record AssetSummaryReadModel(
    string AssetId,
    string TenantId,
    string OwnerId,
    string? MediaItemId,
    string? RoleName,
    AssetStatus Status,             // Pending | Validating | ValidationFailed | Processing | ProcessingFailed | Active | Archived | Deleted
    string FileName,
    string ContentType,
    long? SizeBytes,
    List<string> Tags,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

### `AssetDetailReadModel`

Targets `media-asset-detail` (DynamoDB). Powers `GetAssetById`. Full detail including renditions, metadata, and per-stream dedup marker.

```csharp
record AssetDetailReadModel(
    string AssetId,
    string TenantId,
    string OwnerId,
    string? MediaItemId,
    string? RoleName,
    bool IsPrimary,
    AssetStatus Status,             // Pending | Validating | ValidationFailed | Processing | ProcessingFailed | Active | Archived | Deleted
    string StorageKey,
    string OriginalFileName,
    string ContentType,
    long? SizeBytes,
    List<RenditionDto> Renditions,
    AssetMetadataDto? Metadata,
    List<string> Tags,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    DateTimeOffset? ArchivedAt,
    DateTimeOffset? DeletedAt,
    long LastAssetEventVersion,
    long ProjectedVersion) : IReadModel;
```

### Embedded Types

```csharp
record RenditionDto(
    string RenditionType,
    string StorageKey,
    string ContentType,
    long FileSizeBytes,
    int? Width,
    int? Height);

record AssetMetadataDto(
    string? Format,
    int? Width,
    int? Height,
    int? DpiX,
    int? DpiY,
    string? ColorSpace,
    int? BitDepth,
    decimal? DurationSeconds,
    decimal? FrameRate,
    long? VideoBitRate,
    string? VideoCodec,
    string? AudioCodec,
    long? AudioBitRate,
    int? AudioSampleRate,
    int? PageCount,
    ArchiveMetadataDto? Archive,
    IReadOnlyDictionary<string, string> ExifData);

record ArchiveMetadataDto(
    string CompressionFormat,
    int FileCount,
    long UncompressedSizeBytes,
    decimal? CompressionRatio,
    IReadOnlyList<string> ContainedFileTypes,
    bool IsPasswordProtected);
```

---

## Related

- [Asset Write Model](./asset.write-model.md)
- [Asset API](./asset.api.md)
- [System Spec — Storage Boundaries](../../../../shared/system-spec.md#storage-boundaries)
- [System Spec — Messaging Patterns](../../../../shared/system-spec.md#messaging-patterns)
