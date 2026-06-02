# Collection — Read Model

_Context: `Catalog`_
_Aggregate: `Collection`_

---

## Read Models

### `media-collections` (DynamoDB)

Summary table. Powers list queries.

| Field              | Type       | Notes                              |
| ------------------ | ---------- | ---------------------------------- |
| `PK`               | `string`   | `TENANT#{TenantId}#{CollectionId}` |
| `TenantId`         | `string`   | Plain attribute                    |
| `CollectionId`     | `string`   |                                    |
| `OwnerId`          | `string`   |                                    |
| `Name`             | `string`   |                                    |
| `Visibility`       | `string`   | `CollectionVisibility` enum        |
| `Tags`             | `string[]` |                                    |
| `IsArchived`       | `bool`     |                                    |
| `CreatedAt`        | `string`   | ISO 8601                           |
| `ProjectedVersion` | `long`     | Dedup guard                        |
| `EventId`          | `string`   |                                    |

**GSI:** `VisibilityIndex` (Visibility + CreatedAt) — public media-collection discovery.

### `media-collection-detail` (DynamoDB)

Full detail table. Powers `GET /media-collections/{collectionId}`.

| Field                   | Type       | Notes                                                                |
| ----------------------- | ---------- | -------------------------------------------------------------------- |
| `PK`                    | `string`   | `TENANT#{TenantId}#{CollectionId}`                                   |
| `TenantId`              | `string`   | Plain attribute                                                      |
| `CollectionId`          | `string`   |                                                                      |
| `OwnerId`               | `string`   |                                                                      |
| `Name`                  | `string`   |                                                                      |
| `Description`           | `string?`  |                                                                      |
| `Visibility`            | `string`   |                                                                      |
| `Tags`                  | `string[]` |                                                                      |
| `DefaultMediaProfileId` | `string?`  |                                                                      |
| `IsArchived`            | `bool`     |                                                                      |
| `CreatedAt`             | `string`   |                                                                      |
| `ArchivedAt`            | `string?`  |                                                                      |
| `ProjectedVersion`      | `long`     |                                                                      |
| `EventId`               | `string`   |                                                                      |

---

## Projection Handlers

### `CollectionProjector`

**Trigger:** `media-projector` SQS queue
**Targets:** `media-collections`, `media-collection-detail`

| Event | Write |
|---|---|
| `CollectionCreated` | INSERT both tables |
| `CollectionRenamed` | UPDATE `Name` |
| `CollectionDescriptionUpdated` | UPDATE `Description` |
| `CollectionVisibilityChanged` | UPDATE `Visibility` |
| `CollectionDefaultProfileSet` | UPDATE `DefaultMediaProfileId` (detail table only) |
| `CollectionTagged` | UPDATE `Tags` |
| `CollectionArchived` | UPDATE `IsArchived = true`, `ArchivedAt` |

---

## Queries

| Query                                            | Description                                 |
| ------------------------------------------------ | ------------------------------------------- |
| `GetCollectionByIdQuery(TenantId, CollectionId)` | Full detail                                 |
| `ListCollections(TenantId, PageToken?)`          | Paginated list of owner's media-collections       |
| `ListPublicCollectionsQuery(PageToken?)`         | Public media-collections (uses `VisibilityIndex`) |

---

## Query Handlers

Handlers extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and inject `IReadModelReader<T>` from `Magiq.Platform.ReadModel`. PK construction is handled by the framework. Handlers return DTOs only — no domain objects or event payloads cross the read boundary.

| Handler | Reader | Method |
|---|---|---|
| `GetCollectionByIdHandler` | `IReadModelReader<CollectionDetailReadModel>` | `GetAsync(request, ct)` |
| `ListCollectionsHandler` | `IReadModelReader<CollectionSummaryReadModel>` | `ListAsync(request.TenantId, request.PagerParameters, ct)` |
| `ListPublicCollectionsHandler` | `IReadModelReader<CollectionSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `CollectionSummaryReadModel`

Targets `media-collections` (DynamoDB). Powers list and public discovery queries.

```csharp
record CollectionSummaryReadModel(
    string TenantId,
    string CollectionId,
    string OwnerId,
    string Name,
    string Visibility,
    string[] Tags,
    bool? IsArchived,
    DateTimeOffset CreatedAt,
    DateTimeOffset? UpdatedAt,
    DateTimeOffset? ArchivedAt,
    long ProjectedVersion) : IReadModel;
```

### `CollectionDetailReadModel`

Targets `media-collection-detail` (DynamoDB). Powers `GetCollectionById`.

```csharp
record CollectionDetailReadModel(
    string TenantId,
    string CollectionId,
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
    long ProjectedVersion) : IReadModel;
```

---

## Related

- [Collection Write Model](./media-collection.write-model.md)
- [Collection API](./media-collection.api.md)
- [System Spec — Storage Boundaries](../../../../shared/system-spec.md#storage-boundaries)