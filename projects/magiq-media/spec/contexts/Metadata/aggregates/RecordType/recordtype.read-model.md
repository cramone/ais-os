# RecordType — Read Model

_Context: `Metadata`_
_Aggregate: `RecordType`_

---

## Read Models

### `media-record-types` (DynamoDB)

Single table holding summary rows, full-detail rows, and immutable version-snapshot rows for the RecordType aggregate. All three C# read-model types (`RecordTypeSummaryReadModel`, `RecordTypeDetailReadModel`, `RecordTypeVersionSnapshotReadModel`) are registered against this table; the platform's type-qualified key isolates each row type within the same physical table.

**GSIs:**
- `OwnerIndex` (`OwnerId + Name`) — sparse on summary/detail rows; powers `ListRecordTypesByOwner`

#### Summary Rows (`RecordTypeSummaryReadModel`)

Powers `ListRecordTypesByOwner`. Written on all lifecycle events.

| Field              | Type      | Notes                              |
| ------------------ | --------- | ---------------------------------- |
| `PK`               | `string`  | `TENANT#{TenantId}#{RecordTypeId}` |
| `TenantId`         | `string`  |                                    |
| `RecordTypeId`     | `string`  |                                    |
| `OwnerId`          | `string`  |                                    |
| `Name`             | `string`  |                                    |
| `PublishedVersion` | `int`     | `0` before first publish           |
| `PublishedAt`      | `string?` |                                    |
| `HasDraft`         | `bool`    | `true` when a draft is open        |
| `IsDeprecated`     | `bool`    |                                    |
| `CreatedAt`        | `string`  |                                    |
| `ProjectedVersion` | `long`    |                                    |
| `EventId`          | `string`  |                                    |

#### Detail Rows (`RecordTypeDetailReadModel`)

Powers `GetRecordTypeById`. Superset of summary rows — includes draft field list and description. Written on all lifecycle events.

All summary fields plus:

| Field                 | Type        | Notes                                       |
| --------------------- | ----------- | ------------------------------------------- |
| `Description`         | `string?`   |                                             |
| `DraftFields`         | `object[]?` | Full draft `FieldDefinition[]` when `HasDraft = true` |
| `DraftBasedOnVersion` | `int?`      | Version the draft was branched from         |
| `UpdatedAt`           | `string`    | Derived from last event timestamp           |

#### Version-Snapshot Rows (`RecordTypeVersionSnapshotReadModel`)

Immutable. One row per `RecordTypePublished` event. Powers schema validation and version history.

| Field | Type | Notes |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#{RecordTypeId}` |
| `SK` | `int` | `Version` |
| `TenantId` | `string` | |
| `RecordTypeId` | `string` | |
| `Version` | `int` | |
| `FieldSnapshot` | `object[]` | Full `FieldDefinition[]` at time of publish — used by `IMetadataValidator` |
| `PublishedAt` | `string` | |

The version-snapshot rows are the authoritative source for schema validation. `IMetadataValidator` reads from `media-record-types` (version-snapshot rows) using the `{RecordTypeId, Version}` pinned on the MediaProfile — never from the current draft.

---

## Projection Handlers

### `RecordTypeProjector`

**Trigger:** `media-projector` SQS queue
**Targets:** `media-record-types` (summary rows, detail rows, and version-snapshot rows)

| Event | Write |
|---|---|
| `RecordTypeCreated` | INSERT `media-record-types` (`publishedVersion=0`, `hasDraft=false`); INSERT `media-record-types` (detail row) |
| `RecordTypeDraftCreated` | UPDATE `media-record-types` — `hasDraft=true`; UPDATE `media-record-types` (detail row) — `hasDraft=true`, `draftBasedOnVersion`, `draftFields` copy |
| `FieldAddedToRecordType` | UPDATE `media-record-types` (detail row) — append to `draftFields` |
| `FieldDefinitionUpdated` | UPDATE `media-record-types` (detail row) — update field in `draftFields` |
| `FieldReplacedInRecordType` | UPDATE `media-record-types` (detail row) — replace field in `draftFields` |
| `FieldRemovedFromRecordType` | UPDATE `media-record-types` (detail row) — remove from `draftFields` |
| `FieldsReorderedInRecordType` | UPDATE `media-record-types` (detail row) — reorder `draftFields` |
| `RecordTypeDraftDiscarded` | UPDATE `media-record-types` — `hasDraft=false`; UPDATE `media-record-types` (detail row) — `hasDraft=false`, clear `draftFields`, clear `draftBasedOnVersion` |
| `RecordTypePublished` | UPDATE `media-record-types` — `publishedVersion++`, `hasDraft=false`; UPDATE `media-record-types` (detail row) — same, clear `draftFields`; INSERT `media-record-types` (version-snapshot row) (version row with `fieldSnapshot`) |
| `RecordTypeRenamed` | UPDATE `media-record-types` — `Name`; UPDATE `media-record-types` (detail row) — `Name` |
| `RecordTypeDeprecated` | UPDATE `media-record-types` — `isDeprecated=true`; UPDATE `media-record-types` (detail row) — `isDeprecated=true` |

---

## Queries

| Query | Description |
|---|---|
| `GetRecordTypeByIdQuery(TenantId, RecordTypeId)` | Full detail including draft state |
| `ListRecordTypeVersionsQuery(TenantId, RecordTypeId, PageToken?)` | Version history |
| `GetRecordTypeVersionQuery(TenantId, RecordTypeId, Version)` | Specific version snapshot (used by `IMetadataValidator`) |
| `ListRecordTypesByOwnerQuery(TenantId, OwnerId, PageToken?)` | Paginated list for an owner; pass `"owner_system"` for platform-level types |

---

## Query Handlers

Handlers extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and inject `IReadModelReader<T>` from `Magiq.Platform.ReadModel`. PK construction is handled by the framework. Handlers return DTOs only — no domain objects or event payloads cross the read boundary.

| Handler | Reader | Method |
|---|---|---|
| `GetRecordTypeByIdHandler` | `IReadModelReader<RecordTypeDetailReadModel>` | `GetAsync(request, ct)` |
| `GetRecordTypeVersionHandler` | `IReadModelReader<RecordTypeVersionSummaryReadModel>` | `GetAsync(request, ct)` |
| `ListRecordTypesByOwnerHandler` | `IReadModelReader<RecordTypeDetailReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |
| `ListRecordTypeVersionsHandler` | `IReadModelReader<RecordTypeVersionSummaryReadModel>` | `QueryIndexAsync(request, request.PagerParameters, ct)` |

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `RecordTypeSummaryReadModel`

Targets `media-record-types` (DynamoDB, summary rows). Powers `ListRecordTypesByOwner`.

```csharp
record RecordTypeSummaryReadModel(
    string TenantId,
    string RecordTypeId,
    string Name,
    int PublishedVersion,
    bool HasDraft,
    bool IsDeprecated,
    DateTime CreatedAt,
    long ProjectedVersion) : IReadModel;
```

> **Note:** `RecordTypeSummaryReadModel` exists in the codebase but is not currently used by any handler. `ListRecordTypesByOwnerHandler` injects `IReadModelReader<RecordTypeDetailReadModel>` and returns the full detail shape for list queries.

### `RecordTypeDetailReadModel`

Targets `media-record-types` (DynamoDB, detail rows). Powers `GetRecordTypeById`. Includes draft field list and description.

```csharp
record RecordTypeDetailReadModel(
    string RecordTypeId,
    string TenantId,
    string OwnerId,
    string Name,
    string? Description,
    int PublishedVersion,           // 0 before first publish
    DateTimeOffset? PublishedAt,
    bool IsDeprecated,
    bool HasDraft,
    List<FieldDefinitionDto>? DraftFields,
    int? DraftBasedOnVersion,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

### `RecordTypeVersionSnapshotReadModel`

Targets `media-record-types` (DynamoDB, version-snapshot rows). PK: `TENANT#{TenantId}#{RecordTypeId}` / SK: `Version`. Powers `GetRecordTypeVersion`. Carries the full field schema — used by `IMetadataValidator` for schema validation against pinned versions.

```csharp
record RecordTypeVersionSnapshotReadModel(
    string RecordTypeId,
    string TenantId,
    int Version,
    List<FieldDefinitionDto> FieldSnapshot,
    DateTimeOffset PublishedAt,
    long ProjectedVersion) : IReadModel;
```

### `RecordTypeVersionSummaryReadModel`

Targets `media-record-types` (DynamoDB, version-snapshot rows). Powers `ListRecordTypeVersions`. Lightweight — omits `FieldSnapshot` to keep list reads cheap.

```csharp
record RecordTypeVersionSummaryReadModel(
    string RecordTypeId,
    string TenantId,
    int Version,
    DateTimeOffset PublishedAt,
    long ProjectedVersion) : IReadModel;
```

> **Note:** Both `GetRecordTypeVersionHandler` and `ListRecordTypeVersionsHandler` inject `IReadModelReader<RecordTypeVersionSummaryReadModel>`. The `GetRecordTypeVersion` query therefore returns the summary shape (no `FieldSnapshot`). `RecordTypeVersionSnapshotReadModel` is reserved for `IMetadataValidator` internal use — it is not surfaced via the query API.

### Embedded Types

```csharp
record FieldDefinitionDto(
    string FieldName,
    string FieldType,               // Text | Number | Date | Boolean | Url | Enum | MultiEnum
    bool IsRequired,
    bool IsSearchable,
    int Order,
    string? Description,
    FieldConstraintsDto? Constraints);

record FieldConstraintsDto(
    decimal? MinValue,              // Number
    decimal? MaxValue,              // Number
    int? MaxLength,                 // Text
    List<string>? AllowedValues);  // Enum | MultiEnum
```

---

## Related

- [RecordType Write Model](./recordtype.write-model.md)
- [RecordType API](./recordtype.api.md)
- [System Spec — Storage Boundaries](../../../../shared/system-spec.md#storage-boundaries)