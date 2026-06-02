# MediaItem — Read Model

_Context: `Catalog`_
_Aggregate: `MediaItem`_

---

## Read Models

### `media-items` (DynamoDB)

Primary list table. Powers all filtered queries.

| Field                       | Type       | Notes                                                                       |
| --------------------------- | ---------- | --------------------------------------------------------------------------- |
| `PK`                        | `string`   | `TENANT#{TenantId}#{MediaItemId}`                                           |
| `TenantId`                  | `string`   | Plain attribute                                                             |
| `MediaItemId`               | `string`   |                                                                             |
| `FolderId`                  | `string?`  | Null for unassigned                                                         |
| `CollectionId`              | `string?`  |                                                                             |
| `OwnerId`                   | `string`   |                                                                             |
| `MediaProfileId`            | `string`   |                                                                             |
| `Title`                     | `string`   |                                                                             |
| `Status`                    | `string`   | `MediaItemStatus` enum                                                      |
| `Tags`                      | `string[]` |                                                                             |
| `CheckoutStatus`            | `string`   | `Available` \| `CheckedOut`                                                 |
| `CurrentVersionNumber`      | `int`      | 0 until first publish                                                       |
| `IsAccessible`              | `bool`     | Derived from Collection.IsArchived — set by `CollectionArchiveFanOutWorker` |
| `CreatedAt`                 | `string`   |                                                                             |
| `PublishedAt`               | `string?`  |                                                                             |
| `ProjectedVersion` | `long`     |                                                                             |
| `EventId`                   | `string`   |                                                                             |

**GSIs:**
- `FolderItemsIndex` (FolderId + MediaItemId) — sparse; assigned media-items only
- `UnassignedIndex` (OwnerId + CreatedAt) — sparse; null-FolderId media-items; removed on first assignment
- `OwnerStatusIndex` (OwnerId + Status + CreatedAt) — all media-items
- `ProfileIndex` (MediaProfileId + Status)

### `media-item-detail` (DynamoDB)

Full detail. Powers `GET /media-items/{mediaItemId}`.

All `media-items` fields plus:

| Field | Type | Notes |
|---|---|---|
| `Metadata` | `object` | `{ current: { fieldName: value }, draft?: { fieldName: value } }` |
| `Assets` | `object[]` | `[{ assetId, roleName }]` |
| `RegistrationIds` | `string[]` | |
| `ActiveSigningSessionId` | `string?` | |
| `ActiveMediaChangeRequestId` | `string?` | |
| `CheckedOutBy` | `string?` | |
| `CheckedOutAt` | `string?` | |
| `ArchivedAt` | `string?` | |
| `LastAssetEventVersion` | `long` | Per-stream dedup for Asset events that update MediaItem |

### `media-item-versions` (DynamoDB)

Full snapshot on each publish.

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#{MediaItemId}` |
| `SK` | `int` | `VersionNumber` |
| `TenantId` | `string` | |
| `MediaItemId` | `string` | |
| `VersionNumber` | `int` | |
| `ApprovedMetadataSnapshot` | `object` | Full metadata at time of approval |
| `ApprovedAt` | `string` | |
| `Assets` | `object[]` | Self-contained asset snapshot at approval time. Each entry: `{ AssetId, RoleName, FileName?, SourceStorageKey?, Renditions: [{ RenditionType, StorageKey, ContentType }] }`. S3 keys are snapshotted at approval — content cannot be deleted while a `VersionArtifact` exists. |

### `media-reference-models` (DynamoDB, write-side reference model) <a name="media-item-capability-index"></a>

Per-MediaItem snapshot of its published MediaProfile's capability set and upload constraints. Consumed by `AssetManagement.UploadAssetHandler` through `IMediaItemCapabilityReadModel` to enforce upload-time existence, archive, and size guards, and to resolve quota exemption.

| Field                       | Type       | Notes                                                                               |
| --------------------------- | ---------- | ----------------------------------------------------------------------------------- |
| `PK`                        | `string`   | `TENANT#{TenantId}#{MediaItemId}` — via `ProjectionKey<MediaItemCapabilityReference>`   |
| `TenantId`                  | `string`   |                                                                                     |
| `MediaItemId`               | `string`   |                                                                                     |
| `MediaProfileId`            | `string`   | Published media-profile id at media-item create time (pinned; updated on media-profile re-publish)    |
| `Capabilities`              | `string[]` | e.g. `["Processing", "Registration", "Signing"]` — from `MediaProfilePublishedSnapshot.Capabilities` |
| `MaxFileSizeBytes`          | `long?`    | Max across `AssetDefinitions[*].MaxFileSizeBytes`. Null if every definition is unbounded |
| `IsArchived`                | `bool`     | `true` after `MediaItemArchived`                                                    |
| `ProjectedVersion`          | `long`     | Standard reference-model version marker                                             |

**Consumer:** `MediaItemCapabilityIndexConsumer` (owned by AssetManagement; triggered by `media-cross-module-events` via `Media.IntegrationEventConsumers.Lambda`).

| Event | Write |
|---|---|
| `MediaItemCreated` | INSERT. Reads `PublishedMediaProfileIndex` + `MediaProfileIndex` for capabilities + computed `MaxFileSizeBytes`. |
| `MediaProfilePublished` | UPDATE all `MediaItemCapabilityIndex` rows pinned to that media-profile id (fan-out via `ProfileIndex` GSI on `media-items`) — refreshes `Capabilities`, `MaxFileSizeBytes`. |
| `MediaItemArchived` | UPDATE `IsArchived = true`. |

### `media-catalog-version-asset-ref` (DynamoDB, write-side reference model)

Per-version snapshot of the asset IDs snapshotted at approval time. Consumed by `PurgeMediaItemVersionHandler` via `IMediaItemVersionQueryService` / `IReferenceLookup<MediaItemVersionAssetReference>` to resolve which assets must be released when a version is purged, without crossing into the read-model layer.

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#{MediaItemId}#{VersionNumber}` — via `ProjectionKey<MediaItemVersionAssetReference>` |
| `TenantId` | `string` | |
| `MediaItemId` | `string` | |
| `VersionNumber` | `int` | |
| `AssetIds` | `string[]` | Asset IDs snapshotted at approval time |
| `ProjectedVersion` | `long` | Standard reference-model version marker |

**Consumer:** `MediaItemVersionAssetReferenceProjector` (owned by Catalog write model; triggered by `media-cross-module-events`).

| Event | Write |
|---|---|
| `MediaItemApprovedIntegrationEvent` | UPSERT. Stores `ApprovedAssets[*].AssetId` for the version. |
| `MediaItemVersionPurgedIntegrationEvent` | DELETE. Row removed after successful purge. |

### OpenSearch `media-items` Index

Full-text and faceted search.

| Field | Type |
|---|---|
| `tenantId`, `mediaItemId`, `collectionId`, `folderId`, `ownerId` | keyword |
| `title` | text (analyzed) |
| `status`, `mediaProfileId` | keyword |
| `isAccessible` | boolean |
| `tags` | keyword[] |
| `metadata` | object — `IsSearchable = true` fields only; per-FieldType mapping |
| `createdAt`, `publishedAt` | date |

---

## Projection Handlers

### `MediaItemProjector`

**Trigger:** `media-projector` SQS queue
**Targets:** `media-items` (all GSIs), `media-item-detail`, OpenSearch `media-items`

| Event | Write |
|---|---|
| `MediaItemCreated` | INSERT all targets; `UnassignedIndex` entry if FolderId null |
| `MediaItemAssignedToFolder` | UPDATE `FolderId`, `CollectionId`; remove `UnassignedIndex` entry |
| `MediaItemMoved` | UPDATE `FolderId`, `CollectionId` |
| `MediaItemTitleUpdated` | UPDATE `Title`; OpenSearch UPDATE |
| `MediaItemTagged` | UPDATE `Tags`; OpenSearch UPDATE |
| `MediaItemRevertedToDraft` | UPDATE `Status = Draft`; OpenSearch UPDATE |
| `MediaItemMetadataFieldSet` | UPDATE `Metadata.Draft.{fieldName}` in detail; OpenSearch UPDATE (if `IsSearchable`) |
| `MediaItemMetadataBatchSet` | UPDATE `Metadata.Draft` batch; OpenSearch UPDATE |
| `AssetAssignedToRole` | UPDATE `Assets` list in detail |
| `AssetUnassignedFromRole` | UPDATE `Assets` list in detail |
| `AssetReplacedInRole` | UPDATE `Assets` list in detail — swap `OldAssetId` entry for `NewAssetId` on the matching `RoleName` |
| `MediaItemSubmittedForReview` | UPDATE `Status = PendingApproval`; OpenSearch UPDATE |
| `MediaItemApproved` | UPDATE `Status = Published`, `CurrentVersionNumber`, `PublishedAt`; promote draft metadata to current; OpenSearch UPDATE |
| `MediaItemRejected` | UPDATE `Status = Rejected`; OpenSearch UPDATE |
| `MediaItemWithdrawn` | UPDATE `Status = Withdrawn`; OpenSearch UPDATE |
| `MediaItemArchived` | UPDATE `Status = Archived`, `ArchivedAt`; OpenSearch UPDATE |
| `MediaItemCheckedOut` | UPDATE `CheckoutStatus = CheckedOut`, `CheckedOutBy`, `CheckedOutAt` |
| `MediaItemCheckedIn` / `AbandonCheckout` / `ForceReleaseCheckout` | UPDATE `CheckoutStatus = Available`; clear `CheckedOutBy`, `CheckedOutAt` |
| `MediaChangeRequestLinked` | UPDATE `ActiveMediaChangeRequestId` |
| `MediaChangeRequestUnlinked` | UPDATE clear `ActiveMediaChangeRequestId` |
| `MediaItemSigningSessionLinked` | UPDATE `ActiveSigningSessionId` |
| `MediaItemSigningSessionUnlinked` | UPDATE clear `ActiveSigningSessionId` |
| `RegistrationRefAdded` | UPDATE `RegistrationIds` append |

### `MediaItemVersionDetailProjector`

**Trigger:** `media-projector` SQS queue
**Targets:** `media-item-versions`

| Event | Write |
|---|---|
| `MediaItemApproved` | INSERT self-contained version snapshot. Assets written as `VersionArtifactDto` with S3 keys captured from `ApprovedAssetSnapshot` on the domain event. No retroactive patching — storage keys are snapshotted at approval time. |
| `MediaItemVersionPurged` | DELETE version row. |

> **Removed:** Retroactive `AssetDeleted` patching of version rows. S3 keys are now protected by the `VersionArtifact` domain status on the asset — deletion is blocked at the aggregate level, so version snapshot rows remain authoritative.

---

## Queries

| Query | Description |
|---|---|
| `GetMediaItemByIdQuery(TenantId, MediaItemId)` | Full detail |
| `GetMediaItemVersionQuery(TenantId, MediaItemId, VersionNumber)` | Historical version detail |
| `ListMediaItemVersionsQuery(TenantId, MediaItemId, PageToken?)` | Version history |
| `ListMediaItemsByFolderQuery(TenantId, FolderId, Status?, PageToken?)` | Items in media-folder |
| `ListUnassignedMediaItemsQuery(TenantId, OwnerId, PageToken?)` | Unassigned pool |
| `ListMediaItemsByOwnerQuery(TenantId, OwnerId, Status?, PageToken?)` | Owner's media-items by status |
| `SearchMediaItemsQuery(TenantId, Query, Filters, PageToken?)` | OpenSearch full-text / faceted |

---

## Query Handlers

Handlers extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and inject `IReadModelReader<T>` from `Magiq.Platform.ReadModel`. PK construction is handled by the framework. Handlers return DTOs only — no domain objects or event payloads cross the read boundary.

| Handler | Reader | Method |
|---|---|---|
| `GetMediaItemByIdHandler` | `IReadModelReader<MediaItemDetailReadModel>` | `GetAsync(request, ct)` |
| `GetMediaItemVersionHandler` | `IReadModelReader<MediaItemVersionReadModel>` | `GetAsync(request, ct)` |
| `ListMediaItemVersionsHandler` | `IReadModelReader<MediaItemVersionReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `ListMediaItemsByFolderHandler` | `IReadModelReader<MediaItemSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `ListMediaItemsByOwnerHandler` | `IReadModelReader<MediaItemSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `ListUnassignedMediaItemsHandler` | `IReadModelReader<MediaItemSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `SearchMediaItemsHandler` | `IOpenSearchLowLevelClient` (direct) | OpenSearch DSL — `bool` query with tenant `term` filter + `multi_match` on `Title^3`, `Description`, `Tags`. Pagination via `from`/`size`. |

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `MediaItemSummaryReadModel`

Targets `media-items` (DynamoDB). Powers all list and search queries.

```csharp
record MediaItemSummaryReadModel(
    string MediaItemId,
    string TenantId,
    string OwnerId,
    string MediaProfileId,
    string Title,
    string? FolderId,
    string? CollectionId,
    MediaItemStatus Status,
    List<string> Tags,
    string CheckoutStatus,                  // Available | CheckedOut
    int CurrentVersionNumber,
    bool IsAccessible,
    DateTimeOffset CreatedAt,
    DateTimeOffset? PublishedAt,
    long ProjectedVersion) : IReadModel;
```

### `MediaItemDetailReadModel`

Targets `media-item-detail` (DynamoDB). Powers `GetMediaItemById`.

```csharp
record MediaItemDetailReadModel(
    string MediaItemId,
    string TenantId,
    string OwnerId,
    string MediaProfileId,
    string Title,
    string? Description,
    string? FolderId,
    string? CollectionId,
    MediaItemStatus Status,
    List<string> Tags,
    List<MediaAssetReferenceDto> Assets,
    MetadataChangesetDto Metadata,
    int CurrentVersionNumber,
    List<string> RegistrationIds,
    string CheckoutStatus,                  // Available | CheckedOut
    string? CheckedOutBy,
    DateTimeOffset? CheckedOutAt,
    string? ActiveSigningSessionId,
    string? ActiveMediaChangeRequestId,
    DateTimeOffset? PublishedAt,
    DateTimeOffset? ArchivedAt,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

### `MediaItemVersionReadModel`

Targets `media-item-versions` (DynamoDB). PK: `TENANT#{TenantId}#{MediaItemId}` / SK: `VersionNumber`.

```csharp
record MediaItemVersionReadModel(
    string MediaItemId,
    string TenantId,
    int VersionNumber,
    IReadOnlyDictionary<string, MetadataValue> ApprovedMetadataSnapshot,
    IReadOnlyList<VersionArtifactDto> Assets,
    DateTimeOffset ApprovedAt,
    long ProjectedVersion) : IReadModel;
```

### Embedded Types

```csharp
/// <summary>
/// Asset reference on the live media-item detail read model. Reflects current assignment only.
/// </summary>
record MediaAssetReferenceDto(string AssetId, string RoleName);

/// <summary>
/// Self-contained storage snapshot of an asset as it existed at the time a MediaItem version
/// was approved. S3 keys are snapshotted at approval time and protected by the VersionArtifact
/// status on the Asset aggregate — deletion is domain-blocked while this snapshot exists.
/// </summary>
record VersionArtifactDto(
    string AssetId,
    string RoleName,
    string? FileName,
    string? SourceStorageKey,
    IReadOnlyList<VersionArtifactRenditionDto> Renditions);

record VersionArtifactRenditionDto(string RenditionType, string StorageKey, string ContentType);

record MetadataChangesetDto(
    IReadOnlyDictionary<string, MetadataValue> Current,
    IReadOnlyDictionary<string, MetadataValue>? Draft);

public enum MediaItemStatus  
{  
    Draft, // Editable; initial state and post-rejection/withdrawal state  
    PendingApproval, // Publication requested with reviewers; writes blocked until all approve or any rejects  
    Published, // Approved and live  
    Archived // Terminal soft-archive; no recovery  
}
```

---

## Related

- [MediaItem Write Model](./mediaitem.write-model.md)
- [MediaItem API](./mediaitem.api.md)
- [System Spec — Storage Boundaries](../../../../shared/system-spec.md#storage-boundaries)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         