# Plan: Endpoint Response Model Separation from ReadModel Types

**Date:** 2026-06-18  
**Branch:** `bugfix/endpoint-response-models` (or similar)  
**Scope:** All `*.ReadModel.Endpoints` projects  

---

## Problem

Every `*.ReadModel.Endpoints` project directly references `*.ReadModel` assembly types (e.g. `AssetDetailReadModel`, `CollectionSummaryReadModel`) as endpoint response types. This couples the public API contract to the internal read projection schema — any ReadModel change breaks the API surface.

The `*.WriteModel.Endpoints` projects are clean. Only ReadModel.Endpoints are affected.

---

## Approach

1. Create endpoint-owned response models (records) that mirror the ReadModel shape.
2. Nested ReadModel DTOs (e.g. `RenditionDto`, `MetadataChangesetDto`) also get endpoint-layer equivalents.
3. Update each `*Response.cs` file to use the new model instead of the ReadModel type.
4. Update each `*Endpoint.cs` to project the query result (ReadModel) into the new response model.
5. Remove `using` statements referencing `*.ReadModel` namespaces from endpoint projects.

**Naming convention:**
- Single-resource response: `Get{Resource}Response` / `Get{Resource}VersionResponse`
- List item: `{Resource}SummaryModel` / `{Resource}DetailModel`
- Nested value types: `{Concept}Model` (drop `Dto` suffix)
- Shared nested types: live in a `Contracts/` subfolder within the endpoint module's `V1/` directory

**Implicit operator pattern:** Add an `implicit operator` on each new model for conversion from the ReadModel type. This keeps endpoint `HandleAsync` methods clean — they project at one line.

**Important — existing Contracts files:** Several Contracts models already exist but **still reference ReadModel DTOs internally**. They need to be updated as part of this work (see per-file notes below).

---

## Existing Contracts Files That Need Updating

These files exist and have implicit operators from ReadModel types, but their properties still reference ReadModel DTOs — they are **not yet clean**:

| File | Problem |
|------|---------|
| `Catalog.ReadModel.Endpoints/V1/MediaProfiles/Contracts/MediaProfileVersionDetailModel.cs` | `Snapshot` property is `MediaProfileSnapshotDto` (ReadModel type) |
| `Catalog.ReadModel.Endpoints/V1/MediaProfiles/Contracts/MediaProfileDraftModel.cs` | `AssetDefinitions` is `List<AssetDefinitionDto>`, `RecordTypeRefs` is `List<RecordTypeRefDto>` (ReadModel types) |
| `Metadata.ReadModel.Endpoints/V1/RecordTypes/Contracts/RecordTypeVersionDetailModel.cs` | `FieldSnapshot` is `List<FieldDefinitionDto>` (ReadModel type) |
| `Metadata.ReadModel.Endpoints/V1/RecordTypes/Contracts/RecordTypeVersionSummaryModel.cs` | `FieldSnapshot` is `IReadOnlyList<FieldDefinitionDto>` (ReadModel type) |

`FolderChildSummaryModel.cs` and `MediaProfileVersionSummaryModel.cs` are **already clean** — no ReadModel references in their properties.

---

## Module 1: AssetManagement.ReadModel.Endpoints

### Affected endpoints

| Endpoint | Response type (current → new) |
|----------|-------------------------------|
| `GetAssetByIdEndpoint` | `AssetDetailReadModel` → `GetAssetByIdResponse` |
| `ListAssetsEndpoint` | `PagedResult<AssetSummaryReadModel>` → `ListAssetsResponse` |

### New files to create

#### `V1/Contracts/AssetRenditionModel.cs`
```csharp
namespace Magiq.Media.AssetManagement.Endpoints.V1.Contracts;

public sealed record AssetRenditionModel(
    string RenditionType,
    string StorageKey,
    string ContentType,
    long FileSizeBytes,
    int? Width,
    int? Height)
{
    public static implicit operator AssetRenditionModel(RenditionDto dto) =>
        new(dto.RenditionType, dto.StorageKey, dto.ContentType, dto.FileSizeBytes, dto.Width, dto.Height);
}
```

#### `V1/Contracts/ArchiveMetadataModel.cs`
```csharp
namespace Magiq.Media.AssetManagement.Endpoints.V1.Contracts;

public sealed record ArchiveMetadataModel(
    string CompressionFormat,
    int FileCount,
    long UncompressedSizeBytes,
    decimal? CompressionRatio,
    IReadOnlyList<string> ContainedFileTypes,
    bool IsPasswordProtected)
{
    public static implicit operator ArchiveMetadataModel(ArchiveMetadataDto dto) =>
        new(dto.CompressionFormat, dto.FileCount, dto.UncompressedSizeBytes,
            dto.CompressionRatio, dto.ContainedFileTypes, dto.IsPasswordProtected);
}
```

#### `V1/Contracts/AssetMetadataModel.cs`
```csharp
namespace Magiq.Media.AssetManagement.Endpoints.V1.Contracts;

public sealed record AssetMetadataModel(
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
    ArchiveMetadataModel? Archive,
    IReadOnlyDictionary<string, string> ExifData)
{
    public static implicit operator AssetMetadataModel(AssetMetadataDto dto) =>
        new(dto.Format, dto.Width, dto.Height, dto.DpiX, dto.DpiY,
            dto.ColorSpace, dto.BitDepth, dto.DurationSeconds, dto.FrameRate,
            dto.VideoBitRate, dto.VideoCodec, dto.AudioCodec, dto.AudioBitRate,
            dto.AudioSampleRate, dto.PageCount,
            dto.Archive is null ? null : (ArchiveMetadataModel)dto.Archive,
            dto.ExifData);
}
```

#### `V1/Contracts/AssetSummaryModel.cs`
```csharp
namespace Magiq.Media.AssetManagement.Endpoints.V1.Contracts;

public sealed record AssetSummaryModel(
    string Id,
    string TenantId,
    string OwnerId,
    string? MediaItemId,
    string? RoleName,
    string Status,
    string StorageTier,
    string FileName,
    string ContentType,
    long? SizeBytes,
    List<string> Tags,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion)
{
    public static implicit operator AssetSummaryModel(AssetSummaryReadModel rm) =>
        new(rm.Id, rm.TenantId, rm.OwnerId, rm.MediaItemId, rm.RoleName,
            rm.Status.ToString(), rm.StorageTier.ToString(), rm.FileName,
            rm.ContentType, rm.SizeBytes, rm.Tags, rm.CreatedAt, rm.UpdatedAt,
            rm.ProjectedVersion);
}
```

### Files to update

#### `V1/GetAssetById/GetAssetByIdResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.AssetManagement.Endpoints.V1.GetAssetById;

public sealed record GetAssetByIdResponse(
    string Id,
    string TenantId,
    string OwnerId,
    string? MediaItemId,
    string? RoleName,
    bool IsPrimary,
    string Status,
    string StorageKey,
    string BucketName,
    string OriginalFileName,
    string ContentType,
    long? SizeBytes,
    List<AssetRenditionModel> Renditions,
    AssetMetadataModel? Metadata,
    List<string> Tags,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    DateTimeOffset? ArchivedAt,
    DateTimeOffset? DeletedAt,
    long ProjectedVersion)
{
    public static implicit operator GetAssetByIdResponse(AssetDetailReadModel rm) =>
        new(rm.Id, rm.TenantId, rm.OwnerId, rm.MediaItemId, rm.RoleName,
            rm.IsPrimary, rm.Status.ToString(), rm.StorageKey, rm.BucketName,
            rm.OriginalFileName, rm.ContentType, rm.SizeBytes,
            rm.Renditions.Select(r => (AssetRenditionModel)r).ToList(),
            rm.Metadata is null ? null : (AssetMetadataModel)rm.Metadata,
            rm.Tags, rm.CreatedAt, rm.UpdatedAt, rm.ArchivedAt, rm.DeletedAt,
            rm.ProjectedVersion);
}
```

#### `V1/ListAssets/ListAssetsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.AssetManagement.Endpoints.V1.ListAssets;

public sealed record ListAssetsResponse(
    List<AssetSummaryModel> Items,
    string? NextPageToken);
```

#### `V1/ListAssets/ListAssetsEndpoint.cs`
- Change `Endpoint<TRequest, TResponse>` generic to `ListAssetsResponse`
- In `HandleAsync`: project query result items via `(AssetSummaryModel)item` (implicit operator)

---

## Module 2: Catalog.ReadModel.Endpoints — Collections

### Affected endpoints

| Endpoint | Response type (current → new) |
|----------|-------------------------------|
| `GetCollectionByIdEndpoint` | `CollectionDetailReadModel` → `GetCollectionByIdResponse` |
| `ListCollectionsEndpoint` | `PagedResult<CollectionSummaryReadModel>` → `ListCollectionsResponse` |
| `ListPublicCollectionsEndpoint` | `PagedResult<CollectionSummaryReadModel>` → `ListPublicCollectionsResponse` |

### New files to create

#### `V1/Collections/Contracts/CollectionSummaryModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Collections.Contracts;

public sealed record CollectionSummaryModel(
    string TenantId,
    string Id,
    string OwnerId,
    string Name,
    string Visibility,
    string[] Tags,
    bool? IsArchived,
    DateTimeOffset CreatedAt,
    DateTimeOffset? UpdatedAt,
    DateTimeOffset? ArchivedAt,
    long ProjectedVersion)
{
    public static implicit operator CollectionSummaryModel(CollectionSummaryReadModel rm) =>
        new(rm.TenantId, rm.Id, rm.OwnerId, rm.Name, rm.Visibility, rm.Tags,
            rm.IsArchived, rm.CreatedAt, rm.UpdatedAt, rm.ArchivedAt, rm.ProjectedVersion);
}
```

### Files to update

#### `V1/Collections/GetCollectionById/GetCollectionByIdResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Collections.GetCollectionById;

public sealed record GetCollectionByIdResponse(
    string TenantId,
    string Id,
    string OwnerId,
    string Name,
    string? Description,
    string Visibility,
    string? DefaultMediaProfileId,
    IReadOnlyList<string> Tags,
    bool IsArchived,
    DateTimeOffset? ArchivedAt,
    DateTimeOffset CreatedAt,
    DateTimeOffset? UpdatedAt,
    long ProjectedVersion)
{
    public static implicit operator GetCollectionByIdResponse(CollectionDetailReadModel rm) =>
        new(rm.TenantId, rm.Id, rm.OwnerId, rm.Name, rm.Description, rm.Visibility,
            rm.DefaultMediaProfileId, rm.Tags, rm.IsArchived, rm.ArchivedAt,
            rm.CreatedAt, rm.UpdatedAt, rm.ProjectedVersion);
}
```

#### `V1/Collections/ListCollections/ListCollectionsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Collections.ListCollections;

public sealed record ListCollectionsResponse(
    List<CollectionSummaryModel> Items,
    string? NextPageToken);
```

#### `V1/Collections/ListPublicCollections/ListPublicCollectionsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Collections.ListPublicCollections;

public sealed record ListPublicCollectionsResponse(
    List<CollectionSummaryModel> Items,
    string? NextPageToken);
```

Update `ListCollectionsEndpoint.cs` and `ListPublicCollectionsEndpoint.cs` generic type args and Map calls.

---

## Module 2: Catalog.ReadModel.Endpoints — Folders

### Affected endpoints

| Endpoint | Response type (current → new) |
|----------|-------------------------------|
| `GetFolderByIdEndpoint` | `FolderDetailReadModel` → `GetFolderByIdResponse` |
| `GetFolderHierarchyEndpoint` | `List<FolderSummaryReadModel>` → `GetFolderHierarchyResponse` |
| `ListFoldersEndpoint` | `PagedResult<FolderSummaryReadModel>` → `ListFoldersResponse` |
| `ListFolderChildrenEndpoint` | `PagedResult<FolderChildSummaryReadModel>` → `ListFolderChildrenResponse` |

**`FolderChildSummaryModel.cs` is already clean** — no action needed on the model itself. Just ensure `ListFolderChildrenResponse.cs` and `ListFolderChildrenEndpoint.cs` use it.

### New files to create

#### `V1/Folders/Contracts/MetadataChangesetModel.cs`

> **Note on `MetadataValue`:** `MetadataValue` is a domain abstract record with 10 sealed subtypes (`StringValue`, `IntegerValue`, `BooleanValue`, etc.). At the API boundary, serialize it as a `JsonElement` or `object` to stay polymorphism-agnostic, **or** replicate the discriminated union. Recommended: use `JsonElement` for simplicity unless the API consumers need typed access.

```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Folders.Contracts;

using System.Text.Json;

public sealed record MetadataChangesetModel(
    IReadOnlyDictionary<string, JsonElement> Current,
    IReadOnlyDictionary<string, JsonElement>? Draft);
```

> If the existing serialization already serializes `MetadataValue` subtypes as `JsonElement`, this is a straight passthrough. If the current response serializes the full discriminated union, replicate the subtype structure (see MetadataValue.cs for all 10 subtypes).

#### `V1/Folders/Contracts/FolderSummaryModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Folders.Contracts;

public sealed record FolderSummaryModel(
    string TenantId,
    string CollectionId,
    string Id,
    string? ParentFolderId,
    string Name,
    string OwnerId,
    bool? IsArchived,
    DateTimeOffset? ArchivedAt,
    DateTimeOffset? ArchivedDate,
    DateTimeOffset? ClosedAt,
    DateTimeOffset? ClosedDate,
    DateTimeOffset CreatedAt,
    DateTimeOffset? OpenedDate,
    string? Originator,
    DateTimeOffset? UpdatedAt,
    long ProjectedVersion)
{
    public static implicit operator FolderSummaryModel(FolderSummaryReadModel rm) =>
        new(rm.TenantId, rm.CollectionId, rm.Id, rm.ParentFolderId, rm.Name,
            rm.OwnerId, rm.IsArchived, rm.ArchivedAt, rm.ArchivedDate,
            rm.ClosedAt, rm.ClosedDate, rm.CreatedAt, rm.OpenedDate,
            rm.Originator, rm.UpdatedAt, rm.ProjectedVersion);
}
```

### Files to update

#### `V1/Folders/GetFolderById/GetFolderByIdResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Folders.GetFolderById;

public sealed record GetFolderByIdResponse(
    string TenantId,
    string Id,
    string CollectionId,
    string? ParentFolderId,
    string Name,
    string? Description,
    string OwnerId,
    bool IsArchived,
    DateTimeOffset? ArchivedAt,
    DateTimeOffset? ArchivedDate,
    DateTimeOffset? ClosedAt,
    DateTimeOffset? ClosedDate,
    DateTimeOffset CreatedAt,
    DateTimeOffset? OpenedDate,
    string? Originator,
    MetadataChangesetModel Metadata,
    string? MetadataSetBy,
    string? MetadataAttributedTo,
    DateTimeOffset? MetadataAttributedDate,
    DateTimeOffset? UpdatedAt,
    long ProjectedVersion);
```

> The `MetadataChangesetModel` mapping (from `MetadataChangesetDto`) requires serializing `MetadataValue` instances. Do this in the endpoint's `HandleAsync` or in a static factory method on `GetFolderByIdResponse`. The exact approach depends on how `MetadataValue` is currently serialized — check the existing `HandleAsync` implementation.

#### `V1/Folders/GetFolderHierarchy/GetFolderHierarchyResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Folders.GetFolderHierarchy;

public sealed record GetFolderHierarchyResponse(
    List<FolderSummaryModel> Folders);
```

#### `V1/Folders/ListFolders/ListFoldersResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.Folders.ListFolders;

public sealed record ListFoldersResponse(
    List<FolderSummaryModel> Items,
    string? NextPageToken);
```

#### `V1/Folders/ListFolderChildren/ListFolderChildrenResponse.cs`
Replace `FolderChildSummaryReadModel` reference with `FolderChildSummaryModel` (already clean in Contracts).

Update `ListFoldersEndpoint.cs`, `GetFolderHierarchyEndpoint.cs`, `ListFolderChildrenEndpoint.cs` generic type args and Map calls.

---

## Module 2: Catalog.ReadModel.Endpoints — MediaItems

### Affected endpoints

| Endpoint | Response type (current → new) |
|----------|-------------------------------|
| `GetMediaItemByIdEndpoint` | `MediaItemDetailReadModel` → `GetMediaItemByIdResponse` |
| `GetMediaItemVersionEndpoint` | `MediaItemVersionDetailReadModel` → `GetMediaItemVersionResponse` |
| `ListMediaItemsEndpoint` | `PagedResult<MediaItemSummaryReadModel>` → `ListMediaItemsResponse` |
| `ListMediaItemVersionsEndpoint` | `PagedResult<MediaItemVersionSummaryReadModel>` → `ListMediaItemVersionsResponse` |
| `SearchMediaItemsEndpoint` | `PagedResult<MediaItemDetailReadModel>` → `SearchMediaItemsResponse` |

### New files to create

#### `V1/MediaItems/Contracts/MediaAssetReferenceModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.Contracts;

public sealed record MediaAssetReferenceModel(
    string AssetId,
    string RoleName,
    string? AssetStatus)
{
    public static implicit operator MediaAssetReferenceModel(MediaAssetReferenceDto dto) =>
        new(dto.AssetId, dto.RoleName, dto.AssetStatus);
}
```

#### `V1/MediaItems/Contracts/ConformanceGapModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.Contracts;

public sealed record ConformanceGapModel(
    string GapType,
    string Identifier)
{
    public static implicit operator ConformanceGapModel(ConformanceGapDto dto) =>
        new(dto.GapType, dto.Identifier);
}
```

#### `V1/MediaItems/Contracts/VersionArtifactRenditionModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.Contracts;

public sealed record VersionArtifactRenditionModel(
    string RenditionType,
    string StorageKey,
    string ContentType)
{
    public static implicit operator VersionArtifactRenditionModel(VersionArtifactRenditionDto dto) =>
        new(dto.RenditionType, dto.StorageKey, dto.ContentType);
}
```

#### `V1/MediaItems/Contracts/VersionArtifactModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.Contracts;

public sealed record VersionArtifactModel(
    string AssetId,
    string RoleName,
    string? FileName,
    string? SourceStorageKey,
    IReadOnlyList<VersionArtifactRenditionModel> Renditions)
{
    public static implicit operator VersionArtifactModel(VersionArtifactDto dto) =>
        new(dto.AssetId, dto.RoleName, dto.FileName, dto.SourceStorageKey,
            dto.Renditions.Select(r => (VersionArtifactRenditionModel)r).ToList());
}
```

#### `V1/MediaItems/Contracts/MediaItemSummaryModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.Contracts;

public sealed record MediaItemSummaryModel(
    string Id,
    string TenantId,
    string OwnerId,
    string MediaProfileId,
    string Title,
    string? FolderId,
    string? CollectionId,
    string Status,
    List<string> Tags,
    int CurrentVersionNumber,
    bool IsAccessible,
    DateTimeOffset CreatedAt,
    DateTimeOffset? RecordDate,
    string? Author,
    DateTimeOffset? PublishedAt,
    long ProjectedVersion,
    string ConformanceStatus)
{
    public static implicit operator MediaItemSummaryModel(MediaItemSummaryReadModel rm) =>
        new(rm.Id, rm.TenantId, rm.OwnerId, rm.MediaProfileId, rm.Title,
            rm.FolderId, rm.CollectionId, rm.Status, rm.Tags,
            rm.CurrentVersionNumber, rm.IsAccessible, rm.CreatedAt,
            rm.RecordDate, rm.Author, rm.PublishedAt, rm.ProjectedVersion,
            rm.ConformanceStatus);
}
```

#### `V1/MediaItems/Contracts/MediaItemVersionSummaryModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.Contracts;

public sealed record MediaItemVersionSummaryModel(
    string MediaItemId,
    string TenantId,
    int VersionNumber,
    string Title,
    string Status,
    DateTimeOffset CreatedAt,
    DateTimeOffset? ApprovedAt,
    long ProjectedVersion)
{
    public static implicit operator MediaItemVersionSummaryModel(MediaItemVersionSummaryReadModel rm) =>
        new(rm.MediaItemId, rm.TenantId, rm.VersionNumber, rm.Title, rm.Status,
            rm.CreatedAt, rm.ApprovedAt, rm.ProjectedVersion);
}
```

### Files to update

#### `V1/MediaItems/GetMediaItemById/GetMediaItemByIdResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.GetMediaItemById;

public sealed record GetMediaItemByIdResponse(
    string Id,
    string TenantId,
    string OwnerId,
    string MediaProfileId,
    string Title,
    string? Description,
    string? FolderId,
    string? CollectionId,
    string Status,
    List<string> Tags,
    List<MediaAssetReferenceModel> Assets,
    MetadataChangesetModel Metadata,
    int CurrentVersionNumber,
    List<string> RegistrationIds,
    string? ActiveSigningSessionId,
    DateTimeOffset? PublishedAt,
    DateTimeOffset? ArchivedAt,
    bool HasAccessibleAssets,
    DateTimeOffset CreatedAt,
    DateTimeOffset? RecordDate,
    string? Author,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion,
    string ConformanceStatus,
    IReadOnlyList<ConformanceGapModel>? ConformanceGaps,
    string? MetadataSetBy,
    string? MetadataAttributedTo,
    DateTimeOffset? MetadataAttributedDate);
```

> `MetadataChangesetModel` mapping: same `MetadataValue` serialization note as folders above.

#### `V1/MediaItems/GetMediaItemVersion/GetMediaItemVersionResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.GetMediaItemVersion;

public sealed record GetMediaItemVersionResponse(
    string MediaItemId,
    string TenantId,
    int VersionNumber,
    string Title,
    string? Description,
    IReadOnlyDictionary<string, JsonElement> MetadataSnapshot,
    IReadOnlyList<VersionArtifactModel> Assets,
    DateTimeOffset? ApprovedAt,
    long ProjectedVersion);
```

> `MetadataSnapshot` is `IReadOnlyDictionary<string, MetadataValue>` in the ReadModel — same `MetadataValue` serialization consideration applies.

#### `V1/MediaItems/ListMediaItems/ListMediaItemsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.ListMediaItems;

public sealed record ListMediaItemsResponse(
    List<MediaItemSummaryModel> Items,
    string? NextPageToken);
```

#### `V1/MediaItems/ListMediaItemVersions/ListMediaItemVersionsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.ListMediaItemVersions;

public sealed record ListMediaItemVersionsResponse(
    List<MediaItemVersionSummaryModel> Items,
    string? NextPageToken);
```

#### `V1/MediaItems/SearchMediaItems/SearchMediaItemsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.SearchMediaItems;

public sealed record SearchMediaItemsResponse(
    List<GetMediaItemByIdResponse> Items,
    string? NextPageToken);
```

Update all five endpoint `.cs` files: generic type args + Map projections.

---

## Module 2: Catalog.ReadModel.Endpoints — MediaProfiles

### Affected endpoints

| Endpoint | Response type (current → new) |
|----------|-------------------------------|
| `GetMediaProfileByIdEndpoint` | `MediaProfileDetailReadModel` → `GetMediaProfileByIdResponse` |
| `GetMediaProfileVersionEndpoint` | `MediaProfileVersionDetailReadModel` → `GetMediaProfileVersionResponse` |
| `ListMediaProfilesEndpoint` | `PagedResult<MediaProfileDetailReadModel>` → `ListMediaProfilesResponse` |
| `ListMediaProfileVersionsEndpoint` | `PagedResult<MediaProfileVersionSummaryReadModel>` → `ListMediaProfileVersionsResponse` |

### New files to create

#### `V1/MediaProfiles/Contracts/DimensionConstraintsModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.Contracts;

public sealed record DimensionConstraintsModel(
    decimal? MaxDurationSeconds,
    int? MaxHeight,
    int? MaxWidth,
    decimal? MinDurationSeconds,
    int? MinHeight,
    int? MinWidth)
{
    public static implicit operator DimensionConstraintsModel(DimensionConstraintsDto dto) =>
        new(dto.MaxDurationSeconds, dto.MaxHeight, dto.MaxWidth,
            dto.MinDurationSeconds, dto.MinHeight, dto.MinWidth);
}
```

#### `V1/MediaProfiles/Contracts/RecordTypeRefModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.Contracts;

public sealed record RecordTypeRefModel(
    string RecordTypeId,
    int Version)
{
    public static implicit operator RecordTypeRefModel(RecordTypeRefDto dto) =>
        new(dto.RecordTypeId, dto.Version);
}
```

#### `V1/MediaProfiles/Contracts/AssetDefinitionModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.Contracts;

public sealed record AssetDefinitionModel(
    string RoleName,
    string DisplayName,
    List<string> AcceptedContentTypes,
    bool IsRequired,
    long? MaxFileSizeBytes,
    bool AllowMultiple,
    int DisplayOrder,
    string? DefaultAssetId,
    DimensionConstraintsModel? DimensionConstraints,
    string PreferredStorageTier)
{
    public static implicit operator AssetDefinitionModel(AssetDefinitionDto dto) =>
        new(dto.RoleName, dto.DisplayName, dto.AcceptedContentTypes,
            dto.IsRequired, dto.MaxFileSizeBytes, dto.AllowMultiple,
            dto.DisplayOrder, dto.DefaultAssetId,
            dto.DimensionConstraints is null ? null : (DimensionConstraintsModel)dto.DimensionConstraints,
            dto.PreferredStorageTier);
}
```

#### `V1/MediaProfiles/Contracts/MediaProfileSnapshotModel.cs`
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.Contracts;

public sealed record MediaProfileSnapshotModel(
    string Name,
    string? Description,
    List<AssetDefinitionModel> AssetDefinitions,
    List<RecordTypeRefModel> RecordTypeRefs,
    List<string> Capabilities,
    string ReviewPolicy,
    string CheckoutPolicy,
    bool AutoSubmitOnComplete)
{
    public static implicit operator MediaProfileSnapshotModel(MediaProfileSnapshotDto dto) =>
        new(dto.Name, dto.Description,
            dto.AssetDefinitions.Select(a => (AssetDefinitionModel)a).ToList(),
            dto.RecordTypeRefs.Select(r => (RecordTypeRefModel)r).ToList(),
            dto.Capabilities, dto.ReviewPolicy, dto.CheckoutPolicy,
            dto.AutoSubmitOnComplete);
}
```

### Files to update

#### `V1/MediaProfiles/Contracts/MediaProfileDraftModel.cs` — update properties (keep implicit operator)

Replace `List<AssetDefinitionDto>` and `List<RecordTypeRefDto>` with endpoint-layer types:

```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.Contracts;

public sealed record MediaProfileDraftModel(
    string Name,
    string? Description,
    List<AssetDefinitionModel> AssetDefinitions,
    List<RecordTypeRefModel> RecordTypeRefs,
    string CheckoutPolicy,
    string ReviewPolicy,
    List<string> Capabilities,
    int? BasedOnVersion,
    DateTimeOffset CreatedAt,
    bool AutoSubmitOnComplete)
{
    public static implicit operator MediaProfileDraftModel(MediaProfileDraftDto dto) =>
        new(dto.Name, dto.Description,
            dto.AssetDefinitions.Select(a => (AssetDefinitionModel)a).ToList(),
            dto.RecordTypeRefs.Select(r => (RecordTypeRefModel)r).ToList(),
            dto.CheckoutPolicy, dto.ReviewPolicy, dto.Capabilities,
            dto.BasedOnVersion, dto.CreatedAt, dto.AutoSubmitOnComplete);
}
```

#### `V1/MediaProfiles/Contracts/MediaProfileVersionDetailModel.cs` — update `Snapshot` property

Replace `MediaProfileSnapshotDto Snapshot` with `MediaProfileSnapshotModel Snapshot`:

```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.Contracts;

public sealed record MediaProfileVersionDetailModel(
    string MediaProfileId,
    int Version,
    MediaProfileSnapshotModel Snapshot,
    DateTimeOffset PublishedAt)
{
    public static implicit operator MediaProfileVersionDetailModel(MediaProfileVersionDetailReadModel rm) =>
        new(rm.MediaProfileId, rm.Version, (MediaProfileSnapshotModel)rm.Snapshot, rm.PublishedAt);
}
```

#### `V1/MediaProfiles/GetMediaProfileById/GetMediaProfileByIdResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.GetMediaProfileById;

public sealed record GetMediaProfileByIdResponse(
    string Id,
    string TenantId,
    string OwnerId,
    string Name,
    string? Description,
    string Status,
    int PublishedVersion,
    DateTimeOffset? PublishedAt,
    List<AssetDefinitionModel> AssetDefinitions,
    List<RecordTypeRefModel> RecordTypeRefs,
    string CheckoutPolicy,
    string ReviewPolicy,
    List<string> Capabilities,
    MediaProfileDraftModel? Draft,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion,
    bool AutoSubmitOnComplete)
{
    public static implicit operator GetMediaProfileByIdResponse(MediaProfileDetailReadModel rm) =>
        new(rm.Id, rm.TenantId, rm.OwnerId, rm.Name, rm.Description,
            rm.Status.ToString(), rm.PublishedVersion, rm.PublishedAt,
            rm.AssetDefinitions.Select(a => (AssetDefinitionModel)a).ToList(),
            rm.RecordTypeRefs.Select(r => (RecordTypeRefModel)r).ToList(),
            rm.CheckoutPolicy, rm.ReviewPolicy, rm.Capabilities,
            rm.Draft is null ? null : (MediaProfileDraftModel)rm.Draft,
            rm.CreatedAt, rm.UpdatedAt, rm.ProjectedVersion, rm.AutoSubmitOnComplete);
}
```

#### `V1/MediaProfiles/GetMediaProfileVersion/GetMediaProfileVersionResponse.cs` — replace entirely

```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.GetMediaProfileVersion;

public sealed record GetMediaProfileVersionResponse(
    string MediaProfileId,
    int Version,
    MediaProfileSnapshotModel Snapshot,
    DateTimeOffset PublishedAt,
    long ProjectedVersion)
{
    public static implicit operator GetMediaProfileVersionResponse(MediaProfileVersionDetailReadModel rm) =>
        new(rm.MediaProfileId, rm.Version, (MediaProfileSnapshotModel)rm.Snapshot,
            rm.PublishedAt, rm.ProjectedVersion);
}
```

#### `V1/MediaProfiles/ListMediaProfiles/ListMediaProfilesResponse.cs` — replace entirely

```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.ListMediaProfiles;

public sealed record ListMediaProfilesResponse(
    List<GetMediaProfileByIdResponse> Items,
    string? NextPageToken);
```

> The current list uses `MediaProfileDetailReadModel` (full detail) — preserving that shape. If a lighter summary is preferred, create `MediaProfileSummaryModel` with a subset of fields instead.

#### `V1/MediaProfiles/ListMediaProfileVersions/ListMediaProfileVersionsResponse.cs` — replace entirely

```csharp
namespace Magiq.Media.Catalog.Endpoints.V1.MediaProfiles.ListMediaProfileVersions;

public sealed record ListMediaProfileVersionsResponse(
    List<MediaProfileVersionSummaryModel> Items,
    string? NextPageToken);
```

> `MediaProfileVersionSummaryModel` already exists in Contracts and is clean — no changes needed to it.

Update all four endpoint `.cs` files: generic type args + Map projections.

---

## Module 3: ChangeRequests.ReadModel.Endpoints

### Affected endpoints

| Endpoint | Response type (current → new) |
|----------|-------------------------------|
| `GetChangeRequestByIdEndpoint` | `ChangeRequestDetailReadModel` → `GetChangeRequestByIdResponse` |
| `GetChangeRequestCommentEndpoint` | `ChangeRequestCommentReadModel` → `GetChangeRequestCommentResponse` |
| `ListChangeRequestsEndpoint` | `PagedResult<ChangeRequestSummaryReadModel>` → `ListChangeRequestsResponse` |
| `ListChangeRequestCommentsEndpoint` | `PagedResult<ChangeRequestCommentReadModel>` → `ListChangeRequestCommentsResponse` |

### New files to create

#### `V1/ChangeRequests/Contracts/ChangeRequestSummaryModel.cs`
```csharp
namespace Magiq.Media.ChangeRequests.Endpoints.V1.Contracts;

public sealed record ChangeRequestSummaryModel(
    string TenantId,
    string Id,
    string MediaItemId,
    string OwnerId,
    DateTimeOffset CreatedAt,
    long ProjectedVersion)
{
    public static implicit operator ChangeRequestSummaryModel(ChangeRequestSummaryReadModel rm) =>
        new(rm.TenantId, rm.Id, rm.MediaItemId, rm.OwnerId, rm.CreatedAt, rm.ProjectedVersion);
}
```

#### `V1/ChangeRequests/Contracts/ChangeRequestCommentModel.cs`
```csharp
namespace Magiq.Media.ChangeRequests.Endpoints.V1.Contracts;

public sealed record ChangeRequestCommentModel(
    string TenantId,
    string Id,
    string ChangeRequestId,
    string AuthorId,
    string Body,
    string? ParentCommentId,
    DateTimeOffset AddedAt,
    DateTimeOffset? EditedAt,
    bool IsDeleted,
    long ProjectedVersion)
{
    public static implicit operator ChangeRequestCommentModel(ChangeRequestCommentReadModel rm) =>
        new(rm.TenantId, rm.Id, rm.ChangeRequestId, rm.AuthorId, rm.Body,
            rm.ParentCommentId, rm.AddedAt, rm.EditedAt, rm.IsDeleted, rm.ProjectedVersion);
}
```

### Files to update

#### `V1/ChangeRequests/GetChangeRequestById/GetChangeRequestByIdResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.ChangeRequests.Endpoints.V1.ChangeRequests.GetChangeRequestById;

public sealed record GetChangeRequestByIdResponse(
    string TenantId,
    string Id,
    string OwnerId,
    string MediaItemId,
    int CommentCount,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion,
    string ReviewSessionId)
{
    public static implicit operator GetChangeRequestByIdResponse(ChangeRequestDetailReadModel rm) =>
        new(rm.TenantId, rm.Id, rm.OwnerId, rm.MediaItemId, rm.CommentCount,
            rm.CreatedAt, rm.UpdatedAt, rm.ProjectedVersion, rm.ReviewSessionId);
}
```

#### `V1/ChangeRequests/GetChangeRequestComment/GetChangeRequestCommentResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.ChangeRequests.Endpoints.V1.ChangeRequests.GetChangeRequestComment;

public sealed record GetChangeRequestCommentResponse(
    string TenantId,
    string Id,
    string ChangeRequestId,
    string AuthorId,
    string Body,
    string? ParentCommentId,
    DateTimeOffset AddedAt,
    DateTimeOffset? EditedAt,
    bool IsDeleted,
    long ProjectedVersion)
{
    public static implicit operator GetChangeRequestCommentResponse(ChangeRequestCommentReadModel rm) =>
        new(rm.TenantId, rm.Id, rm.ChangeRequestId, rm.AuthorId, rm.Body,
            rm.ParentCommentId, rm.AddedAt, rm.EditedAt, rm.IsDeleted, rm.ProjectedVersion);
}
```

#### `V1/ChangeRequests/ListChangeRequests/ListChangeRequestsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.ChangeRequests.Endpoints.V1.ChangeRequests.ListChangeRequests;

public sealed record ListChangeRequestsResponse(
    List<ChangeRequestSummaryModel> Items,
    string? NextPageToken);
```

#### `V1/ChangeRequests/ListComments/ListChangeRequestCommentsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.ChangeRequests.Endpoints.V1.ChangeRequests.ListComments;

public sealed record ListChangeRequestCommentsResponse(
    List<ChangeRequestCommentModel> Items,
    string? NextPageToken);
```

Update `GetChangeRequestByIdEndpoint.cs`, `ListChangeRequestsEndpoint.cs`, `ListChangeRequestCommentsEndpoint.cs` generic type args and Map projections.

---

## Module 4: Metadata.ReadModel.Endpoints

### Affected endpoints

| Endpoint | Response type (current → new) |
|----------|-------------------------------|
| `GetRecordTypeByIdEndpoint` | `RecordTypeDetailReadModel` → `GetRecordTypeByIdResponse` |
| `GetRecordTypeVersionEndpoint` | `RecordTypeVersionDetailReadModel` → `GetRecordTypeVersionResponse` |
| `ListRecordTypesEndpoint` | `PagedResult<RecordTypeSummaryReadModel>` → `ListRecordTypesResponse` |
| `ListRecordTypeVersionsEndpoint` | `PagedResult<RecordTypeVersionSummaryReadModel>` → `ListRecordTypeVersionsResponse` |

### New files to create

#### `V1/RecordTypes/Contracts/FieldConstraintsModel.cs`
```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.Contracts;

public sealed record FieldConstraintsModel(
    decimal? MinValue,
    decimal? MaxValue,
    int? MaxLength,
    List<string>? AllowedValues)
{
    public static implicit operator FieldConstraintsModel(FieldConstraintsDto dto) =>
        new(dto.MinValue, dto.MaxValue, dto.MaxLength, dto.AllowedValues);
}
```

#### `V1/RecordTypes/Contracts/FieldDefinitionModel.cs`
```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.Contracts;

public sealed record FieldDefinitionModel(
    string FieldName,
    string FieldType,
    bool IsRequired,
    bool IsSearchable,
    bool IsDeprecated,
    bool IsImmutable,
    int Order,
    string? Description,
    FieldConstraintsModel? Constraints)
{
    public static implicit operator FieldDefinitionModel(FieldDefinitionDto dto) =>
        new(dto.FieldName, dto.FieldType, dto.IsRequired, dto.IsSearchable,
            dto.IsDeprecated, dto.IsImmutable, dto.Order, dto.Description,
            dto.Constraints is null ? null : (FieldConstraintsModel)dto.Constraints);
}
```

#### `V1/RecordTypes/Contracts/RecordTypeSummaryModel.cs`
```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.Contracts;

public sealed record RecordTypeSummaryModel(
    string TenantId,
    string Id,
    string Name,
    string? Description,
    string DisplayName,
    int PublishedVersion,
    bool HasDraft,
    bool IsDeprecated,
    DateTimeOffset CreatedAt,
    long ProjectedVersion)
{
    public static implicit operator RecordTypeSummaryModel(RecordTypeSummaryReadModel rm) =>
        new(rm.TenantId, rm.Id, rm.Name, rm.Description, rm.DisplayName,
            rm.PublishedVersion, rm.HasDraft, rm.IsDeprecated, rm.CreatedAt,
            rm.ProjectedVersion);
}
```

### Files to update

#### `V1/RecordTypes/Contracts/RecordTypeVersionDetailModel.cs` — update `FieldSnapshot` property

Replace `List<FieldDefinitionDto>` with `List<FieldDefinitionModel>`:

```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.Contracts;

public sealed record RecordTypeVersionDetailModel(
    string RecordTypeId,
    string Name,
    int Version,
    List<FieldDefinitionModel> FieldSnapshot,
    List<string> Capabilities,
    DateTimeOffset PublishedAt)
{
    public static implicit operator RecordTypeVersionDetailModel(RecordTypeVersionDetailReadModel rm) =>
        new(rm.RecordTypeId, rm.Name, rm.Version,
            rm.FieldSnapshot.Select(f => (FieldDefinitionModel)f).ToList(),
            rm.Capabilities, rm.PublishedAt);
}
```

#### `V1/RecordTypes/Contracts/RecordTypeVersionSummaryModel.cs` — update `FieldSnapshot` property

Replace `IReadOnlyList<FieldDefinitionDto>` with `IReadOnlyList<FieldDefinitionModel>`:

```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.Contracts;

public sealed record RecordTypeVersionSummaryModel(
    string RecordTypeId,
    long Version,
    IReadOnlyList<FieldDefinitionModel> FieldSnapshot,
    DateTimeOffset PublishedAt)
{
    public static implicit operator RecordTypeVersionSummaryModel(RecordTypeVersionSummaryReadModel rm) =>
        new(rm.RecordTypeId, rm.Version,
            rm.FieldSnapshot.Select(f => (FieldDefinitionModel)f).ToList(),
            rm.PublishedAt);
}
```

#### `V1/RecordTypes/GetRecordTypeById/GetRecordTypeByIdResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.GetRecordTypeById;

public sealed record GetRecordTypeByIdResponse(
    string Id,
    string TenantId,
    string OwnerId,
    string Name,
    string? Description,
    string DisplayName,
    int PublishedVersion,
    DateTimeOffset? PublishedAt,
    bool IsDeprecated,
    bool HasDraft,
    List<string> Capabilities,
    List<FieldDefinitionModel>? DraftFields,
    int? DraftBasedOnVersion,
    DateTimeOffset CreatedAt,
    long ProjectedVersion)
{
    public static implicit operator GetRecordTypeByIdResponse(RecordTypeDetailReadModel rm) =>
        new(rm.Id, rm.TenantId, rm.OwnerId, rm.Name, rm.Description,
            rm.DisplayName, rm.PublishedVersion, rm.PublishedAt, rm.IsDeprecated,
            rm.HasDraft, rm.Capabilities,
            rm.DraftFields?.Select(f => (FieldDefinitionModel)f).ToList(),
            rm.DraftBasedOnVersion, rm.CreatedAt, rm.ProjectedVersion);
}
```

#### `V1/RecordTypes/GetRecordTypeVersion/GetRecordTypeVersionResponse.cs` — replace entirely

Use existing `RecordTypeVersionDetailModel` from Contracts (updated above):

```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.GetRecordTypeVersion;

public sealed record GetRecordTypeVersionResponse(
    string RecordTypeId,
    string Name,
    int Version,
    List<FieldDefinitionModel> FieldSnapshot,
    List<string> Capabilities,
    DateTimeOffset PublishedAt,
    long ProjectedVersion)
{
    public static implicit operator GetRecordTypeVersionResponse(RecordTypeVersionDetailReadModel rm) =>
        new(rm.RecordTypeId, rm.Name, rm.Version,
            rm.FieldSnapshot.Select(f => (FieldDefinitionModel)f).ToList(),
            rm.Capabilities, rm.PublishedAt, rm.ProjectedVersion);
}
```

#### `V1/RecordTypes/ListRecordTypes/ListRecordTypesResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.ListRecordTypes;

public sealed record ListRecordTypesResponse(
    List<RecordTypeSummaryModel> Items,
    string? NextPageToken);
```

#### `V1/RecordTypes/ListRecordTypeVersions/ListRecordTypeVersionsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Metadata.Endpoints.V1.RecordTypes.ListRecordTypeVersions;

public sealed record ListRecordTypeVersionsResponse(
    List<RecordTypeVersionSummaryModel> Items,
    string? NextPageToken);
```

Update all four endpoint `.cs` files: generic type args + Map projections.

---

## Module 5: Registrations.ReadModel.Endpoints

### Affected endpoints

| Endpoint | Response type (current → new) |
|----------|-------------------------------|
| `GetRegistrationByIdEndpoint` | `RegistrationDetailReadModel` → `GetRegistrationByIdResponse` |
| `ListRegistrationsEndpoint` | `PagedResult<RegistrationSummaryReadModel>` → `ListRegistrationsResponse` |
| `SearchRegistrationsEndpoint` | `PagedResult<RegistrationDetailReadModel>` → `SearchRegistrationsResponse` |

### New files to create

#### `V1/Registrations/Contracts/RegistrationItemModel.cs`
```csharp
namespace Magiq.Media.Registrations.Endpoints.V1.Contracts;

public sealed record RegistrationItemModel(
    string MediaItemId,
    string ItemType,
    string? AddedViaAmendmentId,
    DateTimeOffset AttachedAt)
{
    public static implicit operator RegistrationItemModel(RegistrationItemDto dto) =>
        new(dto.MediaItemId, dto.ItemType, dto.AddedViaAmendmentId, dto.AttachedAt);
}
```

#### `V1/Registrations/Contracts/RegistrationAmendmentModel.cs`
```csharp
namespace Magiq.Media.Registrations.Endpoints.V1.Contracts;

public sealed record RegistrationAmendmentModel(
    string AmendmentId,
    string RequestedBy,
    string MediaItemId,
    string ItemType,
    string? Notes,
    string Status,
    DateTimeOffset RequestedAt,
    DateTimeOffset? DecidedAt,
    string? DecisionNotes)
{
    public static implicit operator RegistrationAmendmentModel(RegistrationAmendmentDto dto) =>
        new(dto.AmendmentId, dto.RequestedBy, dto.MediaItemId, dto.ItemType,
            dto.Notes, dto.Status.ToString(), dto.RequestedAt, dto.DecidedAt,
            dto.DecisionNotes);
}
```

#### `V1/Registrations/Contracts/RegistrationSummaryModel.cs`
```csharp
namespace Magiq.Media.Registrations.Endpoints.V1.Contracts;

public sealed record RegistrationSummaryModel(
    string Id,
    string TenantId,
    string MediaItemId,
    string OwnerId,
    string RegistrationType,
    string RegistrationAuthority,
    string Status,
    string? Reference,
    DateTimeOffset? SubmittedAt,
    DateTimeOffset? ConfirmedAt,
    DateTimeOffset InitiatedAt,
    long ProjectedVersion)
{
    public static implicit operator RegistrationSummaryModel(RegistrationSummaryReadModel rm) =>
        new(rm.Id, rm.TenantId, rm.MediaItemId, rm.OwnerId, rm.RegistrationType,
            rm.RegistrationAuthority, rm.Status.ToString(), rm.Reference,
            rm.SubmittedAt, rm.ConfirmedAt, rm.InitiatedAt, rm.ProjectedVersion);
}
```

### Files to update

#### `V1/Registrations/GetRegistrationById/GetRegistrationByIdResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Registrations.Endpoints.V1.Registrations.GetRegistrationById;

public sealed record GetRegistrationByIdResponse(
    string Id,
    string TenantId,
    string MediaItemId,
    string OwnerId,
    string MediaProfileId,
    string RegistrationType,
    string RegistrationAuthority,
    string Status,
    string? ExternalReference,
    string? ReferenceNumber,
    string? Notes,
    string? RejectionReason,
    List<RegistrationItemModel> Items,
    List<RegistrationAmendmentModel> Amendments,
    DateTimeOffset? SubmittedAt,
    DateTimeOffset? ConfirmedAt,
    DateTimeOffset? RejectedAt,
    DateTimeOffset? CancelledAt,
    DateTimeOffset? ExpiresAt,
    DateTimeOffset InitiatedAt,
    long ProjectedVersion)
{
    public static implicit operator GetRegistrationByIdResponse(RegistrationDetailReadModel rm) =>
        new(rm.Id, rm.TenantId, rm.MediaItemId, rm.OwnerId, rm.MediaProfileId,
            rm.RegistrationType, rm.RegistrationAuthority, rm.Status.ToString(),
            rm.ExternalReference, rm.ReferenceNumber, rm.Notes, rm.RejectionReason,
            rm.Items.Select(i => (RegistrationItemModel)i).ToList(),
            rm.Amendments.Select(a => (RegistrationAmendmentModel)a).ToList(),
            rm.SubmittedAt, rm.ConfirmedAt, rm.RejectedAt, rm.CancelledAt,
            rm.ExpiresAt, rm.InitiatedAt, rm.ProjectedVersion);
}
```

#### `V1/Registrations/ListRegistrations/ListRegistrationsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Registrations.Endpoints.V1.Registrations.ListRegistrations;

public sealed record ListRegistrationsResponse(
    List<RegistrationSummaryModel> Items,
    string? NextPageToken);
```

#### `V1/Registrations/SearchRegistrations/SearchRegistrationsResponse.cs` — replace entirely
```csharp
namespace Magiq.Media.Registrations.Endpoints.V1.Registrations.SearchRegistrations;

public sealed record SearchRegistrationsResponse(
    List<GetRegistrationByIdResponse> Items,
    string? NextPageToken);
```

Update `GetRegistrationByIdEndpoint.cs`, `ListRegistrationsEndpoint.cs`, `SearchRegistrationsEndpoint.cs` generic type args and Map projections.

---

## MetadataValue Serialization Decision

`MetadataValue` is used in `FolderDetailReadModel.Metadata` and `MediaItemDetailReadModel.Metadata` (both `MetadataChangesetDto`) and in `MediaItemVersionDetailReadModel.MetadataSnapshot`. It is an abstract record with 10 sealed subtypes.

**Two options — choose one before implementing:**

| Option | Approach | Tradeoff |
|--------|----------|----------|
| **A — JsonElement** | Store each value as `JsonElement` in the response model | Simple, no type loss if the existing JSON serializer already writes subtypes correctly. Consumers must parse the `JsonElement`. |
| **B — Discriminated union** | Create `MetadataValueModel` with 10 subtypes matching `MetadataValue` | Strongly typed at the API boundary. More code. Required if consumers need typed access (e.g. SDK generation). |

For Option B, the model set is:
```csharp
[JsonPolymorphic(TypeDiscriminatorPropertyName = "$type")]
[JsonDerivedType(typeof(StringValueModel), "string")]
[JsonDerivedType(typeof(TextValueModel), "text")]
[JsonDerivedType(typeof(IntegerValueModel), "integer")]
[JsonDerivedType(typeof(NumberValueModel), "number")]
[JsonDerivedType(typeof(BooleanValueModel), "boolean")]
[JsonDerivedType(typeof(DateValueModel), "date")]
[JsonDerivedType(typeof(DateTimeValueModel), "dateTime")]
[JsonDerivedType(typeof(StringArrayValueModel), "stringArray")]
[JsonDerivedType(typeof(IntegerArrayValueModel), "integerArray")]
[JsonDerivedType(typeof(NumberArrayValueModel), "numberArray")]
public abstract record MetadataValueModel;
public sealed record StringValueModel(string Value) : MetadataValueModel;
public sealed record TextValueModel(string Value) : MetadataValueModel;
public sealed record IntegerValueModel(long Value) : MetadataValueModel;
public sealed record NumberValueModel(double Value) : MetadataValueModel;
public sealed record BooleanValueModel(bool Value) : MetadataValueModel;
public sealed record DateValueModel(DateOnly Value) : MetadataValueModel;
public sealed record DateTimeValueModel(DateTimeOffset Value) : MetadataValueModel;
public sealed record StringArrayValueModel(IReadOnlyList<string> Values) : MetadataValueModel;
public sealed record IntegerArrayValueModel(IReadOnlyList<long> Values) : MetadataValueModel;
public sealed record NumberArrayValueModel(IReadOnlyList<double> Values) : MetadataValueModel;
```

Place in `Catalog.ReadModel.Endpoints/V1/Contracts/` (shared by Folders and MediaItems).

---

## Complete File Checklist

### AssetManagement.ReadModel.Endpoints
- [ ] `V1/Contracts/AssetRenditionModel.cs` — create
- [ ] `V1/Contracts/ArchiveMetadataModel.cs` — create
- [ ] `V1/Contracts/AssetMetadataModel.cs` — create
- [ ] `V1/Contracts/AssetSummaryModel.cs` — create
- [ ] `V1/GetAssetById/GetAssetByIdResponse.cs` — replace
- [ ] `V1/ListAssets/ListAssetsResponse.cs` — replace
- [ ] `V1/ListAssets/ListAssetsEndpoint.cs` — update generics + Map

### Catalog.ReadModel.Endpoints — Collections
- [ ] `V1/Collections/Contracts/CollectionSummaryModel.cs` — create
- [ ] `V1/Collections/GetCollectionById/GetCollectionByIdResponse.cs` — replace
- [ ] `V1/Collections/ListCollections/ListCollectionsResponse.cs` — replace
- [ ] `V1/Collections/ListPublicCollections/ListPublicCollectionsResponse.cs` — replace
- [ ] `V1/Collections/ListCollections/ListCollectionsEndpoint.cs` — update
- [ ] `V1/Collections/ListPublicCollections/ListPublicCollectionsEndpoint.cs` — update

### Catalog.ReadModel.Endpoints — Folders
- [ ] `V1/Contracts/MetadataChangesetModel.cs` (+ `MetadataValueModel` if option B) — create
- [ ] `V1/Folders/Contracts/FolderSummaryModel.cs` — create
- [ ] `V1/Folders/GetFolderById/GetFolderByIdResponse.cs` — replace
- [ ] `V1/Folders/GetFolderHierarchy/GetFolderHierarchyResponse.cs` — replace
- [ ] `V1/Folders/ListFolders/ListFoldersResponse.cs` — replace
- [ ] `V1/Folders/ListFolderChildren/ListFolderChildrenResponse.cs` — replace (use existing FolderChildSummaryModel)
- [ ] `V1/Folders/ListFolders/ListFoldersEndpoint.cs` — update
- [ ] `V1/Folders/GetFolderHierarchy/GetFolderHierarchyEndpoint.cs` — update
- [ ] `V1/Folders/ListFolderChildren/ListFolderChildrenEndpoint.cs` — update

### Catalog.ReadModel.Endpoints — MediaItems
- [ ] `V1/MediaItems/Contracts/MediaAssetReferenceModel.cs` — create
- [ ] `V1/MediaItems/Contracts/ConformanceGapModel.cs` — create
- [ ] `V1/MediaItems/Contracts/VersionArtifactRenditionModel.cs` — create
- [ ] `V1/MediaItems/Contracts/VersionArtifactModel.cs` — create
- [ ] `V1/MediaItems/Contracts/MediaItemSummaryModel.cs` — create
- [ ] `V1/MediaItems/Contracts/MediaItemVersionSummaryModel.cs` — create
- [ ] `V1/MediaItems/GetMediaItemById/GetMediaItemByIdResponse.cs` — replace
- [ ] `V1/MediaItems/GetMediaItemVersion/GetMediaItemVersionResponse.cs` — replace
- [ ] `V1/MediaItems/ListMediaItems/ListMediaItemsResponse.cs` — replace
- [ ] `V1/MediaItems/ListMediaItemVersions/ListMediaItemVersionsResponse.cs` — replace
- [ ] `V1/MediaItems/SearchMediaItems/SearchMediaItemsResponse.cs` — replace
- [ ] `V1/MediaItems/ListMediaItems/ListMediaItemsEndpoint.cs` — update
- [ ] `V1/MediaItems/ListMediaItemVersions/ListMediaItemVersionsEndpoint.cs` — update
- [ ] `V1/MediaItems/SearchMediaItems/SearchMediaItemsEndpoint.cs` — update

### Catalog.ReadModel.Endpoints — MediaProfiles
- [ ] `V1/MediaProfiles/Contracts/DimensionConstraintsModel.cs` — create
- [ ] `V1/MediaProfiles/Contracts/RecordTypeRefModel.cs` — create
- [ ] `V1/MediaProfiles/Contracts/AssetDefinitionModel.cs` — create
- [ ] `V1/MediaProfiles/Contracts/MediaProfileSnapshotModel.cs` — create
- [ ] `V1/MediaProfiles/Contracts/MediaProfileDraftModel.cs` — **update** (replace ReadModel DTOs)
- [ ] `V1/MediaProfiles/Contracts/MediaProfileVersionDetailModel.cs` — **update** (replace `MediaProfileSnapshotDto`)
- [ ] `V1/MediaProfiles/GetMediaProfileById/GetMediaProfileByIdResponse.cs` — replace
- [ ] `V1/MediaProfiles/GetMediaProfileVersion/GetMediaProfileVersionResponse.cs` — replace
- [ ] `V1/MediaProfiles/ListMediaProfiles/ListMediaProfilesResponse.cs` — replace
- [ ] `V1/MediaProfiles/ListMediaProfileVersions/ListMediaProfileVersionsResponse.cs` — replace
- [ ] `V1/MediaProfiles/ListMediaProfiles/ListMediaProfilesEndpoint.cs` — update
- [ ] `V1/MediaProfiles/ListMediaProfileVersions/ListMediaProfileVersionsEndpoint.cs` — update

### ChangeRequests.ReadModel.Endpoints
- [ ] `V1/ChangeRequests/Contracts/ChangeRequestSummaryModel.cs` — create
- [ ] `V1/ChangeRequests/Contracts/ChangeRequestCommentModel.cs` — create
- [ ] `V1/ChangeRequests/GetChangeRequestById/GetChangeRequestByIdResponse.cs` — replace
- [ ] `V1/ChangeRequests/GetChangeRequestComment/GetChangeRequestCommentResponse.cs` — replace
- [ ] `V1/ChangeRequests/ListChangeRequests/ListChangeRequestsResponse.cs` — replace
- [ ] `V1/ChangeRequests/ListComments/ListChangeRequestCommentsResponse.cs` — replace
- [ ] `V1/ChangeRequests/GetChangeRequestById/GetChangeRequestByIdEndpoint.cs` — update
- [ ] `V1/ChangeRequests/ListChangeRequests/ListChangeRequestsEndpoint.cs` — update
- [ ] `V1/ChangeRequests/ListComments/ListChangeRequestCommentsEndpoint.cs` — update

### Metadata.ReadModel.Endpoints
- [ ] `V1/RecordTypes/Contracts/FieldConstraintsModel.cs` — create
- [ ] `V1/RecordTypes/Contracts/FieldDefinitionModel.cs` — create
- [ ] `V1/RecordTypes/Contracts/RecordTypeSummaryModel.cs` — create
- [ ] `V1/RecordTypes/Contracts/RecordTypeVersionDetailModel.cs` — **update** (replace `FieldDefinitionDto`)
- [ ] `V1/RecordTypes/Contracts/RecordTypeVersionSummaryModel.cs` — **update** (replace `FieldDefinitionDto`)
- [ ] `V1/RecordTypes/GetRecordTypeById/GetRecordTypeByIdResponse.cs` — replace
- [ ] `V1/RecordTypes/GetRecordTypeVersion/GetRecordTypeVersionResponse.cs` — replace
- [ ] `V1/RecordTypes/ListRecordTypes/ListRecordTypesResponse.cs` — replace
- [ ] `V1/RecordTypes/ListRecordTypeVersions/ListRecordTypeVersionsResponse.cs` — replace
- [ ] `V1/RecordTypes/ListRecordTypes/ListRecordTypesEndpoint.cs` — update
- [ ] `V1/RecordTypes/ListRecordTypeVersions/ListRecordTypeVersionsEndpoint.cs` — update

### Registrations.ReadModel.Endpoints
- [ ] `V1/Registrations/Contracts/RegistrationItemModel.cs` — create
- [ ] `V1/Registrations/Contracts/RegistrationAmendmentModel.cs` — create
- [ ] `V1/Registrations/Contracts/RegistrationSummaryModel.cs` — create
- [ ] `V1/Registrations/GetRegistrationById/GetRegistrationByIdResponse.cs` — replace
- [ ] `V1/Registrations/ListRegistrations/ListRegistrationsResponse.cs` — replace
- [ ] `V1/Registrations/SearchRegistrations/SearchRegistrationsResponse.cs` — replace
- [ ] `V1/Registrations/ListRegistrations/ListRegistrationsEndpoint.cs` — update
- [ ] `V1/Registrations/SearchRegistrations/SearchRegistrationsEndpoint.cs` — update
