# Folder — Read Model

_Context: `Catalog`_
_Aggregate: `Folder`_

---

## Read Models

### `media-folders` (DynamoDB)

Summary. Powers media-folder hierarchy list queries.

| Field              | Type      | Notes                          |
| ------------------ | --------- | ------------------------------ |
| `PK`               | `string`  | `TENANT#{TenantId}#{FolderId}` |
| `TenantId`         | `string`  |                                |
| `FolderId`         | `string`  |                                |
| `CollectionId`     | `string`  |                                |
| `ParentFolderId`   | `string?` |                                |
| `Name`             | `string`  |                                |
| `OwnerId`          | `string`  |                                |
| `IsArchived`       | `bool`    |                                |
| `ArchivedAt`       | `string?` |                                |
| `ClosedAt`         | `string?` | System timestamp when `CloseFolder` was executed. |
| `ClosedDate`       | `string?` | Business-supplied closed date. |
| `OpenedDate`       | `string?` | Business-supplied opened date. |
| `CreatedAt`        | `string`  |                                |
| `ProjectedVersion` | `long`    |                                |
| `EventId`          | `string`  |                                |

> `ActiveChildCount` and `ActiveItemCount` were removed. These counters previously backed the `HasActiveChildrenAsync` empty-folder check on `ArchiveFolder`. That precondition has been replaced by an active-registrations blocking check; `ArchiveFolder` now cascades to descendants rather than requiring the folder to be empty first.

**GSI:**
- `CollectionParentIndex` (`TENANT#{TenantId}#{CollectionId}` + `ParentFolderId`) — supports two access patterns:
  - `GetFolderHierarchyQuery`: query by PK only — returns all media-folders for a media-collection; client builds the tree in memory
  - `ListFoldersQuery`: query by PK + SK (`ParentFolderId`) — returns direct children of a specific parent; `null` SK matches root-level media-folders (stored as empty string sentinel `"ROOT"`)

> **Note:** Root-level media-folders (no parent) store `ParentFolderId = "ROOT"` in the GSI SK to make them queryable. The domain model treats this as `null`; the projection layer performs the translation.

### `media-folder-detail` (DynamoDB)

Full detail. Powers `GET /media-folders/{folderId}`.

All fields from `media-folders` plus:

| Field                    | Type      | Notes                                                             |
|--------------------------|-----------|-------------------------------------------------------------------|
| `Description`            | `string?` |                                                                   |
| `Metadata`               | `object`  | `{ current: {...}, draft: {...} \| null }` — `MetadataChangeset` |
| `MetadataSetBy`          | `string?` | Member ID who last modified the metadata draft                    |
| `MetadataAttributedTo`   | `string?` | Business-level attribution                                        |
| `MetadataAttributedDate` | `string?` | Business date of the attributed metadata change                   |
| `UpdatedAt`              | `string?` | Derived from last event                                           |

---

## Projection Handlers

### `FolderDetailProjector`

**Trigger:** `media-projector` SQS queue  
**Target:** `media-folder-detail`

| Event                      | Write                                                                                               |
| -------------------------- | --------------------------------------------------------------------------------------------------- |
| `FolderCreated`            | INSERT — all fields including `OpenedDate`, `ClosedDate`; `Metadata = { current: {}, draft: null }` |
| `FolderRenamed`            | UPDATE `Name`, `UpdatedAt`                                                                          |
| `FolderMoved`              | UPDATE `ParentFolderId`, `CollectionId`, `UpdatedAt`                                                |
| `FolderDescriptionUpdated` | UPDATE `Description`, `UpdatedAt`                                                                   |
| `FolderArchived`           | UPDATE `IsArchived = true`, `UpdatedAt`                                                             |
| `FolderClosed`             | UPDATE `ClosedAt`, `ClosedDate`, `UpdatedAt`                                                        |
| `FolderMetadataFieldSet`   | UPDATE `Metadata.Draft[FieldName] = Value`, `MetadataSetBy`, `MetadataAttributedTo`, `MetadataAttributedDate`, `UpdatedAt` |
| `FolderMetadataBatchSet`   | UPDATE `Metadata.Draft` (merge all fields), `MetadataSetBy`, `MetadataAttributedTo`, `MetadataAttributedDate`, `UpdatedAt` |
| `FolderMetadataCommitted`  | UPDATE `Metadata = { current: CommittedMetadata, draft: null }`, `UpdatedAt`                        |

### `FolderSummaryProjector`

**Trigger:** `media-projector` SQS queue  
**Target:** `media-folders`

| Event                      | Write                                                                  |
| -------------------------- | ---------------------------------------------------------------------- |
| `FolderCreated`            | INSERT — all fields including `OpenedDate`, `ClosedDate`               |
| `FolderRenamed`            | UPDATE `Name`, `UpdatedAt`                                             |
| `FolderMoved`              | UPDATE `ParentFolderId`, `CollectionId`, `UpdatedAt`                   |
| `FolderDescriptionUpdated` | UPDATE `UpdatedAt`                                                     |
| `FolderArchived`           | UPDATE `IsArchived = true`, `UpdatedAt`                                |
| `FolderClosed`             | UPDATE `ClosedAt`, `ClosedDate`, `UpdatedAt`                           |

### `FolderChildSummaryProjector`

**Trigger:** `media-projector` SQS queue  
**Target:** `child-items`

Handles both Folder and MediaItem events. Root-level folders (null `ParentFolderId`) are excluded via `ResolveKey` returning null.

| Event              | Write                                        |
| ------------------ | -------------------------------------------- |
| `FolderCreated`    | INSERT                                       |
| `FolderRenamed`    | UPDATE `Name`, `UpdatedAt`                   |
| `FolderMoved`      | UPDATE `ParentFolderId`, `CollectionId`, `UpdatedAt` |
| `FolderArchived`   | UPDATE `Status = Archived`, `UpdatedAt`      |
| `MediaItemCreated` | INSERT                                       |
| _(other MediaItem events)_ | UPDATE as appropriate               |

> `FolderClosed` does not currently update the child summary — closing is a detail-level concept not surfaced in navigation lists.

---

## Queries

| Query                                                                   | Description                                                                        |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `GetFolderByIdQuery(TenantId, FolderId)`                                | Full detail including `ArchivedAt`, `ClosedAt`, `ClosedDate`, `OpenedDate`, `UpdatedAt` |
| `ListFoldersQuery(TenantId, CollectionId, ParentFolderId?, PageToken?)` | Folder children — pass `ParentFolderId = null` for root-level media-folders        |
| `GetFolderHierarchyQuery(TenantId, CollectionId)`                       | Full subtree for a media-collection (shallow: IDs + names only; used for tree rendering) |

---

## Query Handlers

Handlers extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and inject `IReadModelReader<T>` from `Magiq.Platform.ReadModel`. PK construction is handled by the framework. Handlers return DTOs only — no domain objects or event payloads cross the read boundary.

| Handler | Reader | Method |
|---|---|---|
| `GetFolderByIdHandler` | `IReadModelReader<FolderDetailReadModel>` | `GetAsync(request, ct)` |
| `ListFoldersHandler` | `IReadModelReader<FolderSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `GetFolderHierarchyHandler` | `IReadModelReader<FolderSummaryReadModel>` | `QueryIndexAsync(request, PagerParameters.AllOnOnePage(), ct)` — fetches all nodes; caller builds the tree in memory |

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `FolderSummaryReadModel`

Targets `media-folders` (DynamoDB). Powers `ListFolders` and `GetFolderHierarchy`.

```csharp
record FolderSummaryReadModel(
    string TenantId,
    string CollectionId,
    string Id,
    string? ParentFolderId,
    string Name,
    string OwnerId,
    bool? IsArchived,
    DateTimeOffset? ArchivedAt,
    DateTimeOffset? ClosedAt,
    DateTimeOffset? ClosedDate,
    DateTimeOffset CreatedAt,
    DateTimeOffset? OpenedDate,
    DateTimeOffset? UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

### `FolderDetailReadModel`

Targets `media-folder-detail` (DynamoDB). Powers `GetFolderById`.

```csharp
record FolderDetailReadModel(
    string TenantId,
    string Id,
    string CollectionId,
    string? ParentFolderId,
    string Name,
    string? Description,
    string OwnerId,
    bool IsArchived,
    DateTimeOffset? ArchivedAt,
    DateTimeOffset? ClosedAt,
    DateTimeOffset? ClosedDate,
    DateTimeOffset CreatedAt,
    DateTimeOffset? OpenedDate,
    string? Originator,
    MetadataChangesetDto Metadata,
    string? MetadataSetBy,
    string? MetadataAttributedTo,
    DateTimeOffset? MetadataAttributedDate,
    DateTimeOffset? UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

### `FolderChildSummaryReadModel`

Targets `child-items` (DynamoDB). Powers `ListChildrenInFolder`. Unified model for both child folders and media items.

```csharp
record FolderChildSummaryReadModel(
    string TenantId,
    string ChildId,
    string ParentFolderId,
    ChildType ChildType,
    string Name,
    string CollectionId,
    string Status,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

---

## Related

- [Folder Write Model](./folder.write-model.md)
- [Folder API](./folder.api.md)
- [System Spec — Storage Boundaries](../../../../shared/system-spec.md#storage-boundaries)
