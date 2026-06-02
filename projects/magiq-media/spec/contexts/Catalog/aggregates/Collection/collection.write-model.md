# Collection — Write Model

_Context: `Catalog`_
_Aggregate: `Collection`_
_Stream prefix: `media-collection_`_

---

## Purpose

Top-level organisational container. Owned by a single `OwnerId`. Acts as a namespace for Folders and MediaItems. Controls visibility for its entire hierarchy. Archiving is write-side only — no cascade on write; the `CollectionArchiveFanOutWorker` propagates `isAccessible = false` to descendants asynchronously via read model updates.

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| Not archived | `CollectionArchived` | `RenameCollection` |
| Not already archived | `CollectionAlreadyArchived` | `ArchiveCollection` |
| Profile must be `Published` (handler-side) | `ProfileNotPublished` | `SetDefaultMediaProfile`, `CreateCollection` (if defaultProfileId supplied) |

---

## Properties

| Property                | Type                   | Notes                                                                                            |
| ----------------------- | ---------------------- | ------------------------------------------------------------------------------------------------ |
| `CollectionId`          | `CollectionId`         | UUID v7-based. Caller-generated.                                                                 |
| `TenantId`              | `TenantId`             | Set from `CollectionCreated` (first field). Immutable.                                           |
| `OwnerId`               | `OwnerId`              | Immutable after creation.                                                                        |
| `Name`                  | `CollectionName`       | Max 255 chars. Unique within tenant scope (enforced handler-side via `ICollectionQueryService`). |
| `Description`           | `string?`              | Max 1,000 chars.                                                                                 |
| `Visibility`            | `CollectionVisibility` | `Private` \| `Unlisted` \| `Public`                                                              |
| `Tags`                  | `IReadOnlyList<Tag>`   | Full replacement semantics.                                                                      |
| `DefaultMediaProfileId` | `MediaProfileId?`      | Applied to MediaItems when no explicit media-profile given.                                            |
| `CreatedAt`             | `DateTimeOffset`       | Event-sourced from `CollectionCreated`.                                                          |
| `ArchivedAt`            | `DateTimeOffset?`      |                                                                                                  |

---

## Methods (Commands)

| Method | Description | Invariants |
|---|---|---|
| `Collection.Create(tenantId, id, ownerId, name, description?, visibility, defaultProfileId?)` | Factory. Raises `CollectionCreated` (+ optional `CollectionDescriptionUpdated`, `CollectionDefaultProfileSet`). | — |
| `Rename(newName)` | Raises `CollectionRenamed`. | Not archived |
| `UpdateDescription(newDescription?)` | Raises `CollectionDescriptionUpdated`. Idempotent guard: no-op if unchanged. | — |
| `SetVisibility(visibility)` | Raises `CollectionVisibilityChanged`. Idempotent guard. | — |
| `SetDefaultMediaProfile(profileId)` | Raises `CollectionDefaultProfileSet`. Idempotent guard. | — |
| `Tag(tags)` | Full replacement. Raises `CollectionTagged`. | — |
| `Archive()` | Raises `CollectionArchived`. | Not already archived |

---

## Domain Events

| Event | Key Payload Fields |
|---|---|
| `CollectionCreated` | `TenantId`†, `CollectionId`, `OwnerId`, `Name`, `Visibility`, `CreatedAt` |
| `CollectionRenamed` | `CollectionId`, `OldName`, `NewName` |
| `CollectionDescriptionUpdated` | `CollectionId`, `OldDescription?`, `NewDescription?` |
| `CollectionVisibilityChanged` | `CollectionId`, `OldVisibility`, `NewVisibility` |
| `CollectionDefaultProfileSet` | `CollectionId`, `MediaProfileId` |
| `CollectionTagged` | `CollectionId`, `Tags[]` (full replacement snapshot) |
| `CollectionArchived` | `CollectionId`, `ArchivedAt` |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command | Handler | Result |
|---|---|---|
| `CreateCollectionCommand(CollectionId, OwnerId, Name, Description?, Visibility, DefaultMediaProfileId?)` | `CreateCollectionHandler` | `Result<CollectionId, DomainError>` |
| `RenameCollectionCommand(CollectionId, NewName)` | `RenameCollectionHandler` | `Result<Unit, DomainError>` |
| `UpdateCollectionDescriptionCommand(CollectionId, NewDescription?)` | `UpdateCollectionDescriptionHandler` | `Result<Unit, DomainError>` |
| `SetCollectionVisibilityCommand(CollectionId, Visibility)` | `SetCollectionVisibilityHandler` | `Result<Unit, DomainError>` |
| `SetDefaultMediaProfileCommand(CollectionId, MediaProfileId)` | `SetDefaultMediaProfileHandler` | `Result<Unit, DomainError>` |
| `TagCollectionCommand(CollectionId, Tags[])` | `TagCollectionHandler` | `Result<Unit, DomainError>` |
| `ArchiveCollectionCommand(CollectionId)` | `ArchiveCollectionHandler` | `Result<Unit, DomainError>` |

**Handler pre-conditions (handler-side, not aggregate-side):**

| Handler | Pre-condition | Interface |
|---|---|---|
| `CreateCollectionHandler` | Name must be unique within tenant scope | `ICollectionQueryService.IsCollectionNameAvailable` |
| `CreateCollectionHandler` | If `DefaultMediaProfileId` supplied, media-profile must be `Published` | `IMediaProfileReadModel.IsPublishedAsync` |
| `RenameCollectionHandler` | New name must be unique within tenant scope (skipped when name is unchanged) | `ICollectionQueryService.IsCollectionNameAvailable` |
| `SetDefaultMediaProfileHandler` | Profile must be `Published` | `IMediaProfileReadModel.IsPublishedAsync` |

---

## Write Model Service Interfaces

```csharp
interface ICollectionQueryService {
    /// Returns true if the name is not currently in use within the tenant; false if already taken.
    Task<bool> IsCollectionNameAvailable(TenantId tenantId, string collectionName, CancellationToken ct = default);
}

interface IMediaProfileReadModel {
    Task<bool> IsPublishedAsync(MediaProfileId profileId, CancellationToken ct);
}
```

**`ICollectionQueryService` usage:**

| Handler | Call site | Guard |
|---|---|---|
| `CreateCollectionHandler` | Before `Collection.Create(...)` | `!IsCollectionNameAvailable` → `InvalidOperation("Collection name is already in use.")` |
| `RenameCollectionHandler` | After same-name short-circuit, before `collection.Rename(...)` | `!IsCollectionNameAvailable` → `InvalidOperation("Collection name is already in use.")` |

---

## Published Integration Events

| Message | Source Event | Purpose |
|---|---|---|
| `CollectionCreatedMessage` | `CollectionCreated` | Notifies Notifications and Billing of new media-collection |
| `CollectionRenamedMessage` | `CollectionRenamed` | Propagates name change to downstream indexes |
| `CollectionVisibilityChangedMessage` | `CollectionVisibilityChanged` | Allows Search/Discovery to react to visibility transitions |
| `CollectionTaggedMessage` | `CollectionTagged` | Full tag replacement to search indexing services |
| `CollectionArchivedMessage` | `CollectionArchived` | Signals media-collection and contents no longer active |

---

## Consumed Integration Events

**From Catalog (self) — consumer: `CollectionArchiveFanOutConsumer`**

The Collection write model self-consumes its own `CollectionArchivedMessage` via the `media-fan-out` SQS queue to drive the descendant archival fan-out. This is the only inbound integration event for this aggregate; no cross-context events are consumed.

| Integration Event | Source | Action |
|---|---|---|
| `CollectionArchivedMessage` | Catalog (self) | Enqueues a `CollectionArchiveFanOutJob`; `CollectionArchiveFanOutWorker` propagates `isAccessible = false` to all descendant `media-items` and `media-item-detail` read model entries. Processed shard-per-Lambda-invocation with checkpoint-per-page semantics. See Archive Fan-Out section below. |

---

## Archive Fan-Out

On `CollectionArchived`, the `CollectionProjector` enqueues a `CollectionArchiveFanOutJob` to `media-fan-out` SQS. The `CollectionArchiveFanOutWorker` then propagates `isAccessible = false` to all descendant `media-items` and `media-item-detail` read model entries. The worker uses a sharded `CollectionItemsIndex` and processes one shard per Lambda invocation with checkpoint-per-page semantics.

**Note:** Write-side aggregates (`Folder`, `MediaItem`) are not touched by archive. Archiving is fully reversible at the read layer — though no `UnarchiveCollection` command exists in v1.

---

## Constraint Enforcement — Implementation Notes

This section documents the implementation of `ICollectionQueryService` and the handler call sequence for `CreateCollectionHandler` and `RenameCollectionHandler`. These serve as the **canonical reference** for all uniqueness-enforcing handlers in the system. See [System Spec — Cross-Aggregate Constraint Enforcement](../../../../shared/system-spec.md#cross-aggregate-constraint-enforcement) for the pattern definition and summary table.

### `ICollectionQueryService` Implementation

Backed by `media-name-reservations`. Uses `ConsistentRead = true` so a reservation written by a concurrent handler is immediately visible to the Tier 1 check.

```csharp
sealed class CollectionQueryService(IAmazonDynamoDB dynamo) : ICollectionQueryService
{
    public async Task<bool> IsCollectionNameAvailableAsync(
        TenantId tenantId, string name, CancellationToken ct)
    {
        var key = NameReservationKey.For(tenantId, "COLLECTION", name.Trim().ToLowerInvariant());
        var response = await dynamo.GetItemAsync(new GetItemRequest
        {
            TableName = "media-name-reservations",
            Key = key,
            ConsistentRead = true
        }, ct);
        return !response.IsItemSet; // true = no reservation found = name is available
    }

    public async Task<bool> IsPublishedAsync(MediaProfileId profileId, CancellationToken ct)
    {
        var response = await dynamo.GetItemAsync(new GetItemRequest
        {
            TableName = "media-profiles",
            Key = DynamoKey.For(profileId),
            ProjectionExpression = "MediaProfileStatus"
        }, ct);
        return response.IsItemSet
            && response.Item["MediaProfileStatus"].S == "Published";
    }
}
```

### `CreateCollectionHandler` — Create with New Reservation

```csharp
sealed class CreateCollectionHandler(
    IRepository<Collection> repository,
    INameReservationService nameReservation,
    ICollectionQueryService collectionQuery,
    IExecutionContext ctx) : IRequestHandler<CreateCollectionCommand, Result<CollectionId, DomainError>>
{
    public async Task<Result<CollectionId, DomainError>> Handle(
        CreateCollectionCommand cmd, CancellationToken ct)
    {
        // 1. Tier 1 — early rejection via read-model check
        if (!await collectionQuery.IsCollectionNameAvailableAsync(ctx.TenantId, cmd.Name, ct))
            return DomainError.InvalidOperation("Collection name is already in use.");

        // 2. State check — default media-profile must be Published if supplied
        if (cmd.DefaultMediaProfileId is not null
            && !await collectionQuery.IsPublishedAsync(cmd.DefaultMediaProfileId, ct))
            return DomainError.InvalidOperation("Media profile is not published.");

        // 3+4. Factory — no prior aggregate load for creation
        var collection = Collection.Create(
            ctx.TenantId, cmd.CollectionId, ctx.Actor.Id,
            cmd.Name, cmd.Description, cmd.Visibility, cmd.DefaultMediaProfileId);

        // 5. Register event append with ambient ITransactionScope
        repository.Save(collection);

        // 6. Register reservation write with ambient ITransactionScope
        nameReservation.Reserve(
            NameReservation.Reserve(ctx.TenantId, ReservationScope.Collection, cmd.Name));

        // Both committed atomically by MediatR TransactionBehavior.
        // NameReservationConflictException handled by NameReservationConflictBehavior.
        return collection.Id;
    }
}
```

### `RenameCollectionHandler` — Atomic Reservation Swap

On rename, the old reservation is deleted and the new one is written atomically. No window exists where neither reservation exists.

```csharp
sealed class RenameCollectionHandler(
    IRepository<Collection> repository,
    INameReservationService nameReservation,
    ICollectionQueryService collectionQuery,
    IExecutionContext ctx) : IRequestHandler<RenameCollectionCommand, Result<Unit, DomainError>>
{
    public async Task<Result<Unit, DomainError>> Handle(
        RenameCollectionCommand cmd, CancellationToken ct)
    {
        var collection = await repository.LoadAsync(ctx.TenantId, cmd.CollectionId, ct);

        // Same-name short-circuit — no event, no reservation change
        if (collection.Name == cmd.NewName)
            return Unit.Value;

        // 1. Tier 1
        if (!await collectionQuery.IsCollectionNameAvailableAsync(ctx.TenantId, cmd.NewName, ct))
            return DomainError.InvalidOperation("Collection name is already in use.");

        var oldName = collection.Name; // capture before mutation

        collection.Rename(cmd.NewName); // raises CollectionRenamed

        repository.Save(collection);
        nameReservation.Reserve(
            NameReservation.Swap(ctx.TenantId, ReservationScope.Collection, oldName, cmd.NewName));

        return Unit.Value;
    }
}
```

### `ArchiveCollectionHandler` — Reservation Release

`ReleaseNameIntent` never produces a `NameReservationConflictException`.

```csharp
sealed class ArchiveCollectionHandler(
    IRepository<Collection> repository,
    INameReservationService nameReservation,
    IExecutionContext ctx) : IRequestHandler<ArchiveCollectionCommand, Result<Unit, DomainError>>
{
    public async Task<Result<Unit, DomainError>> Handle(
        ArchiveCollectionCommand cmd, CancellationToken ct)
    {
        var collection = await repository.LoadAsync(ctx.TenantId, cmd.CollectionId, ct);

        collection.Archive(); // aggregate guard: not already archived

        repository.Save(collection);
        nameReservation.Reserve(
            NameReservation.Release(ctx.TenantId, ReservationScope.Collection, collection.Name));

        return Unit.Value;
    }
}
```

---

## Reference Models

Reference models consumed by this write model's command handlers. All are read-only projections; this context never writes to them directly.

---

### `media-profiles` (DynamoDB — published status only)

**Owned by:** Catalog (same context — internal projection)  
**Consumed via:** `IMediaProfileReadModel` (`IsPublishedAsync`)  
**Used by:** `CreateCollectionHandler` (when `DefaultMediaProfileId` is supplied — media-profile must be `Published` before the media-collection is created), `SetDefaultMediaProfileHandler` (same guard — media-profile must be `Published` before the default is updated).

This is a narrower read than `IMediaProfileQueryService` used by `MediaItem` handlers — only the published/not-published boolean is needed; no snapshot data is consumed.

| Field | Type | Purpose |
|---|---|---|
| `MediaProfileId` | `string` | Lookup key |
| `Status` | `string` | Must equal `Published` — `IsPublishedAsync` returns false for any other status or missing record |

**Subscribed events (same-context projection — `media-projector` SQS queue):**

| Event | Write |
|---|---|
| `MediaProfilePublished` | UPSERT `Status = Published` |
| `MediaProfileDeprecated` | UPDATE `Status = Deprecated` |

---

## Related

- [Collection Read Model](./media-collection.read-model.md)
- [Collection API](./media-collection.api.md)
- [Catalog Business Scenarios](../../business-scenarios.md)
- [System Spec — Cross-Aggregate Constraint Enforcement](../../../../shared/system-spec.md#cross-aggregate-constraint-enforcement)
- [System Spec — Multi-Tenancy](../../../../shared/system-spec.md#multi-tenancy-strategy)
