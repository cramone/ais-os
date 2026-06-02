# MediaProfile — Read Model

_Context: `Catalog`_
_Aggregate: `MediaProfile`_

---

## Read Models

### `media-profiles` (DynamoDB)

Single table holding both current-state rows (no SK) and immutable version-snapshot rows (SK: `Version`). Both `MediaProfileDetailReadModel` and `MediaProfileVersionReadModel` are registered against this table; the platform's type-qualified key (`TENANT#{TenantId}#{TypeName}#{MediaProfileId}`) keeps them isolated within the same physical table.

**GSIs:**
- `OwnerStatusIndex` (`OwnerId + Status`) — sparse on current-state rows only; powers list queries

#### Current-State Rows (`MediaProfileDetailReadModel`)

Powers list queries and `GetMediaProfileById`. Written on every media-profile lifecycle event.

| Field              | Type       | Notes                                                                   |
| ------------------ | ---------- | ----------------------------------------------------------------------- |
| `PK`               | `string`   | `TENANT#{TenantId}#{MediaProfileId}`                                    |
| `TenantId`         | `string`   |                                                                         |
| `MediaProfileId`   | `string`   |                                                                         |
| `OwnerId`          | `string`   |                                                                         |
| `Name`             | `string`   |                                                                         |
| `Description`      | `string?`  |                                                                         |
| `Status`           | `string`   | `MediaProfileStatus` enum (`Draft \| Published \| Deprecated`)          |
| `PublishedVersion` | `int`      | `0` before first publish                                                |
| `HasDraft`         | `bool`     |                                                                         |
| `Capabilities`     | `string[]` | Published capabilities list (for quick lookup at asset processing time) |
| `ReviewPolicy`     | `string`   | Published `ReviewPolicy`                                                |
| `CheckoutPolicy`   | `string`   | Published `CheckoutPolicy`                                              |
| `CreatedAt`        | `string`   |                                                                         |
| `PublishedAt`      | `string?`  |                                                                         |
| `ProjectedVersion` | `long`     |                                                                         |
| `EventId`          | `string`   |                                                                         |

#### Version-Snapshot Rows (`MediaProfileVersionReadModel`)

Immutable. Written once per `MediaProfilePublished` event. Powers `GetMediaProfileVersionQuery`.

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#{MediaProfileId}` |
| `SK` | `int` | `Version` |
| `TenantId` | `string` | |
| `MediaProfileId` | `string` | |
| `Version` | `int` | |
| `Snapshot` | `object` | Full media-profile state: `{ AssetDefinitions[], RecordTypeRefs[], Capabilities[], ReviewPolicy, CheckoutPolicy, Name, Description? }` |
| `PublishedAt` | `string` | |

---

## Projection Handlers

### `MediaProfileProjector`

**Trigger:** `media-projector` SQS queue
**Targets:** `media-profiles` (current-state rows and version-snapshot rows)

| Event | Write |
|---|---|
| `MediaProfileCreated` | INSERT `media-profiles` (`status=Draft`, `publishedVersion=0`, `hasDraft=false`) |
| `MediaProfileDraftCreated` | UPDATE `media-profiles` — `hasDraft=true` |
| `AssetDefinitionAdded` | UPDATE `media-profiles` — update draft snapshot in cache (if tracked) |
| `AssetDefinitionUpdated` | UPDATE draft snapshot |
| `AssetDefinitionRemoved` | UPDATE draft snapshot |
| `AssetDefinitionsReordered` | UPDATE draft snapshot |
| `AssetDefinitionDefaultSet` | UPDATE draft snapshot — set `DefaultAssetId` on matching `AssetDefinition` by `RoleName` |
| `RecordTypeAttachedToProfile` | UPDATE draft snapshot |
| `RecordTypeVersionPinnedOnProfile` | UPDATE draft snapshot |
| `RecordTypeDetachedFromProfile` | UPDATE draft snapshot |
| `ReviewPolicySet` | UPDATE draft snapshot |
| `CheckoutPolicySet` | UPDATE draft snapshot |
| `MediaProfileCapabilitiesSet` | UPDATE draft snapshot |
| `MediaProfileDraftDiscarded` | UPDATE `media-profiles` — `hasDraft=false` |
| `MediaProfilePublished` | UPDATE `media-profiles` (`status=Published`, `publishedVersion++`, `hasDraft=false`, update `Capabilities`, `ReviewPolicy`, `CheckoutPolicy`); INSERT `media-profiles` (version row with full `Snapshot`) |
| `MediaProfileDeprecated` | UPDATE `media-profiles` — `status=Deprecated` |

---

## Queries

| Query | Description |
|---|---|
| `GetMediaProfileByIdQuery(TenantId, MediaProfileId)` | Full media-profile detail including draft if present |
| `ListMediaProfilesByOwnerQuery(TenantId, OwnerId, PagerParameters)` | All media-profiles for an owner (via `OwnerStatusIndex`) |
| `GetMediaProfileVersionQuery(TenantId, MediaProfileId, Version)` | Immutable snapshot for a specific published version |

---

## Query Handlers

Handlers extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and inject `IReadModelReader<T>` from `Magiq.Platform.ReadModel`. PK construction is handled by the framework. Handlers return DTOs only — no domain objects or event payloads cross the read boundary.

| Handler | Reader | Method |
|---|---|---|
| `GetMediaProfileByIdHandler` | `IReadModelReader<MediaProfileDetailReadModel>` | `GetAsync(request, ct)` |
| `ListMediaProfilesByOwnerHandler` | `IReadModelReader<MediaProfileDetailReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `GetMediaProfileVersionHandler` | `IReadModelReader<MediaProfileVersionReadModel>` | `GetAsync(request, ct)` |

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `MediaProfileDetailReadModel`

Targets `media-profiles` (DynamoDB). Powers `GetMediaProfileById` and `ListMediaProfilesByOwner`.

```csharp
record MediaProfileDetailReadModel(
    string MediaProfileId,
    string TenantId,
    string OwnerId,
    string Name,
    string? Description,
    MediaProfileStatus Status,
    int PublishedVersion,
    DateTimeOffset? PublishedAt,
    List<AssetDefinitionDto> AssetDefinitions,
    List<RecordTypeRefDto> RecordTypeRefs,
    string CheckoutPolicy,                  // None | RequiredForEdit
    string ReviewPolicy,                    // None | RequiredForPublish
    List<string> Capabilities,
    MediaProfileDraftDto? Draft,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

### `MediaProfileVersionReadModel`

Targets `media-profiles` (DynamoDB). PK: `TENANT#{TenantId}#{MediaProfileId}` / SK: `Version`.

```csharp
record MediaProfileVersionReadModel(
    string MediaProfileId,
    string TenantId,
    int Version,
    MediaProfileSnapshotDto Snapshot,
    DateTimeOffset PublishedAt,
    long ProjectedVersion) : IReadModel;
```

### Embedded Types

```csharp
record AssetDefinitionDto(
    string RoleName,
    string DisplayName,
    List<string> AcceptedContentTypes,
    bool IsRequired,
    long? MaxFileSizeBytes,
    bool AllowMultiple,
    int DisplayOrder,
    string? DefaultAssetId,
    DimensionConstraintsDto? DimensionConstraints,
    string PreferredStorageTier);           // Standard | StandardIA | Glacier

record DimensionConstraintsDto(
    int? MinWidth, int? MaxWidth,
    int? MinHeight, int? MaxHeight,
    decimal? MinDurationSeconds, decimal? MaxDurationSeconds);

record RecordTypeRefDto(string RecordTypeId, int Version);

record MediaProfileSnapshotDto(
    string Name,
    string? Description,
    List<AssetDefinitionDto> AssetDefinitions,
    List<RecordTypeRefDto> RecordTypeRefs,
    List<string> Capabilities,
    string ReviewPolicy,
    string CheckoutPolicy);

record MediaProfileDraftDto(
    string Name,
    string? Description,
    List<AssetDefinitionDto> AssetDefinitions,
    List<RecordTypeRefDto> RecordTypeRefs,
    string CheckoutPolicy,
    string ReviewPolicy,
    List<string> Capabilities,
    int? BasedOnVersion,
    DateTimeOffset CreatedAt);
    
enum MediaProfileStatus  
{  
    Draft, // Never published  
    Published,  
    Deprecated  
}    
```

---

## Related

- [MediaProfile Write Model](./mediaprofile.write-model.md)
- [MediaProfile API](./mediaprofile.api.md)
- 