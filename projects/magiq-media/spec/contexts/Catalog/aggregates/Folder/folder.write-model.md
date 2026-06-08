# Folder — Write Model

_Context: `Catalog`_
_Aggregate: `Folder`_
_Stream prefix: `media-folder_`_

---

## Purpose

Hierarchical container within a `Collection`. A Folder belongs to exactly one Collection and has an optional parent Folder. MediaItem membership is expressed via `MediaItem.FolderId` — the Folder aggregate does not hold media-item or child-folder ID lists. Archiving is write-side soft-archive only; the `FolderProjector` handles read model updates.

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| `CollectionId` is immutable — media-folders cannot move between media-collections | `FolderCollectionImmutable` | `MoveFolder` |
| Max 10 levels of nesting | `FolderDepthExceeded` | `CreateFolder`, `MoveFolder` |
| No circular parent chains | `CircularFolderReference` | `MoveFolder` |
| Not already archived | `FolderAlreadyArchived` | `ArchiveFolder` |
| Not already closed | `FolderAlreadyClosed` | `CloseFolder` |
| No media items in the subtree may have active registrations | `FolderHasActiveRegistrations` | `ArchiveFolder` |
| `ExpectedVersion` must match current `Version` | `ConcurrencyConflict` | All mutating commands |

---

## Properties

| Property         | Type             | Notes                                              |
| ---------------- | ---------------- | -------------------------------------------------- |
| `FolderId`       | `FolderId`       | UUID v7-based. Caller-generated.                   |
| `TenantId`       | `TenantId`       | Set from `FolderCreated` (first field). Immutable. |
| `CollectionId`   | `CollectionId`   | Immutable after creation.                          |
| `ParentFolderId` | `FolderId?`      | Null = root media-folder within Collection.        |
| `Name`           | `FolderName`     | Max 255 chars. Unique within parent scope.         |
| `OwnerId`        | `OwnerId`        | Denormalised from Collection at creation time.     |
| `IsArchived`     | `bool`           |                                                    |
| `IsClosed`       | `bool`           | Derived: `ClosedAt.HasValue`.                      |
| `OpenedDate`     | `DateTimeOffset?` | Business date the folder was opened. Optional; supplied by caller. |
| `ClosedDate`     | `DateTimeOffset?` | Business date the folder was closed. Optional; supplied by caller at creation or via `CloseFolder`. |
| `ClosedAt`       | `DateTimeOffset?` | System timestamp when `CloseFolder` was executed. Null until `Close()` is called. |
| `Version`        | `int`            | Event sequence count — for optimistic concurrency. |
| `CreatedAt`      | `DateTimeOffset` |                                                    |
| `UpdatedAt`      | `DateTimeOffset` | Derived from last applied event.                   |

---

## Methods (Commands)

| Method                                                                                                        | Description                       | Preconditions                                                               |
| ------------------------------------------------------------------------------------------------------------- | --------------------------------- | --------------------------------------------------------------------------- |
| `Folder.Create(tenantId, folderId, collectionId, parentFolderId?, name, description?, ownerId, createdAt, openedDate?, closedDate?)` | Factory. Raises `FolderCreated`. | Depth ≤ 10, no circular chain (handler-side) |
| `Rename(newName, expectedVersion)`                                                                            | Raises `FolderRenamed`.           | Not archived                                                                |
| `Move(newParentFolderId?, expectedVersion)`                                                                   | Raises `FolderMoved`.             | Not archived; same Collection; depth ≤ 10; no circular chain (handler-side) |
| `Archive(expectedVersion)`                                                                                    | Raises `FolderArchived`.          | Not already archived; no active registrations in subtree (handler-side blocking check) |
| `Close(closedAt, closedDate?)`                                                                                | Raises `FolderClosed`.            | Not already closed (`IsClosed` guard). |

---

## Domain Events

| Event                | Key Payload Fields                                                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `FolderCreated`      | `TenantId`†, `FolderId`, `CollectionId`, `ParentFolderId?`, `Name`, `Description?`, `OwnerId`, `CreatedAt`, `OpenedDate?`, `ClosedDate?` |
| `FolderRenamed`      | `FolderId`, `OldName`, `NewName`                                                                                          |
| `FolderMoved`        | `FolderId`, `OldParentFolderId?`, `NewParentFolderId?`                                                                    |
| `FolderArchived`     | `FolderId`, `ArchivedAt`                                                                                                  |
| `FolderClosed`       | `FolderId`, `CollectionId`, `ParentFolderId?`, `ClosedAt`, `ClosedDate?`                                                  |
| `FolderDescriptionUpdated` | `FolderId`, `CollectionId`, `ParentFolderId?`, `OldDescription?`, `NewDescription?`                              |

† `TenantId` is the **first field** on the creation event.

**`ClosedDate` vs `ClosedAt`:** `ClosedDate` is a business-supplied date (e.g. the financial or operational close date). `ClosedAt` is the system timestamp when `Close()` was called. Both are optional: `ClosedDate` may be provided at creation time or when closing; `ClosedAt` is only set by the `FolderClosed` event.

---

## Commands

| Command                                                                                           | Handler                     | Result                                     |
| ------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------ |
| `CreateFolderCommand(FolderId, CollectionId, ParentFolderId?, Name, Description?, OwnerId, OccurredAt, OpenedDate?, ClosedDate?)` | `CreateFolderHandler` | `Result<Unit, DomainError>` |
| `RenameFolderCommand(FolderId, NewName, ExpectedVersion)`                                         | `RenameFolderHandler`       | `Result<Unit, DomainError>`                |
| `MoveFolderCommand(FolderId, NewParentFolderId?, ExpectedVersion)`                                | `MoveFolderHandler`         | `Result<Unit, DomainError>`                |
| `ArchiveFolderCommand(FolderId, ExpectedVersion)`                                                 | `ArchiveFolderHandler`      | `Result<Unit, DomainError>`                |
| `CloseFolderCommand(FolderId, OccurredAt, ClosedDate?)`                                           | `CloseFolderHandler`        | `Result<Unit, DomainError>`                |

**Handler-side pre-conditions:**

| Handler | Pre-condition | Interface | Guard type |
|---|---|---|---|
| `CreateFolderHandler` | If `ParentFolderId` supplied: parent media-folder must exist | `IFolderRepository.GetByIdAsync` | Blocking — `ResourceNotFound` |
| `CreateFolderHandler` | Name must be unique within parent scope (Tier 1) | `INameReservationService.IsNameAvailableAsync` | Blocking — `InvalidOperation` |
| `CreateFolderHandler` | Nesting depth must not exceed 10 | `IUniquenessCounterService.GetCounterAsync` | Blocking — `InvalidOperation` |
| `RenameFolderHandler` | Same-name short-circuit — no-op when name unchanged | — | Returns success without state change |
| `RenameFolderHandler` | New name must be unique within parent scope (Tier 1) | `INameReservationService.IsNameAvailableAsync` | Blocking — `InvalidOperation` |
| `MoveFolderHandler` | No-op move guard; parent exists; depth ≤ 10; no circular chain | `IFolderHierarchyService.CanMoveAsync` | Blocking — delegates error from service `Result` |
| `MoveFolderHandler` | Folder name must be unique in destination scope (Tier 1) | `INameReservationService.IsNameAvailableAsync` | Blocking — `InvalidOperation` |
| `ArchiveFolderHandler` | No media items in the subtree have active registrations | `IFolderArchiveFanOutWorker.HasActiveRegistrationsAsync` | Blocking — `InvalidOperation` |
| `CloseFolderHandler` | Folder must not already be closed | Aggregate `IsClosed` guard | Blocking — `InvalidOperation` |

---

## Published Integration Events

Published inline by `FolderDomainEventMapper` (`Catalog.WriteModel`) immediately after the domain event is persisted. All events target the `media-integration-events` SNS topic.

| Integration Event | Source Domain Event | Notes |
|---|---|---|
| `FolderCreatedIntegrationEvent` | `FolderCreated` | Consumed by Search/Discovery to index the media-folder hierarchy |
| `FolderRenamedIntegrationEvent` | `FolderRenamed` | Carries `OldName`, `NewName` — consumed by Search/Discovery |
| `FolderMovedIntegrationEvent` | `FolderMoved` | Carries `OldParentFolderId`, `NewParentFolderId` — consumed by Search/Discovery |
| `FolderArchivedIntegrationEvent` | `FolderArchived` | Consumed by Search/Discovery to remove the folder from the hierarchy index. Because `ArchiveFolder` now cascades via `IFolderArchiveFanOutWorker`, descendant items and child folders are archived before this event fires for the root folder. |

> `FolderClosed` and `FolderDescriptionUpdated` do not currently produce integration events.

---

## Consumed Integration Events

This write model consumes **no integration events**. All handler inputs arrive via direct API calls or intra-context command dispatch.

---

## Write Model Service Interfaces

```csharp
interface IFolderCreationLockService {
    /// Acquires a per-collection distributed lock to serialise concurrent creates.
    Task<IFolderCreationLockHandle> AcquireAsync(TenantId tenantId, CollectionId collectionId, CancellationToken ct = default);
}

interface IFolderArchiveFanOutWorker {
    /// Returns true if any media item in the folder subtree has an active registration.
    Task<bool> HasActiveRegistrationsAsync(TenantId tenantId, FolderId folderId, CancellationToken ct = default);

    /// Archives all media items in the folder subtree, then descendant folders leaf-first.
    /// Does NOT archive folderId itself — that is the caller's responsibility.
    Task ArchiveDescendantsAsync(TenantId tenantId, FolderId folderId, DateTimeOffset archivedAt, CancellationToken ct = default);
}
```

---

## Constraint Enforcement — Implementation Notes

Handlers enforce constraints directly without a `FolderHierarchyService` intermediary:

**Parent existence** — `IFolderRepository.GetByIdAsync` loads the full aggregate. Strongly consistent; archived-parent check is done against the loaded aggregate's state.

**Depth enforcement** — `IUniquenessCounterService` maintains a strongly-consistent depth counter per folder, keyed by `ScopeKeys.Folder(folderId)` / `CounterKeys.Depth`. On create the counter is initialised to `depth` (1 for root, `parentDepth + 1` otherwise). On move the delta is applied. Rejected if the resulting depth would exceed 10.

**Name uniqueness** — `INameReservationService` (two-tier). Tier 1 is a read-model availability check; Tier 2 is an atomic `TransactWriteItems` reservation. The Tier 2 call is wrapped in `try { … } catch (NameReservationConflictException)` and mapped to `InvalidOperation`.

**Creation locking** — `IFolderCreationLockService` serialises concurrent single-folder creates against bulk operations in the same collection. Bulk operations hold the lock for the full reserve phase; single creates acquire the lock for their Tier 1 + Tier 2 window.

**Archive cascade** — `IFolderArchiveFanOutWorker` walks the subtree directly to check registrations and cascade the archive.

**Folder close** — `CloseFolderHandler` loads the aggregate, calls `folder.Close(closedAt, closedDate?)`, and saves. No lock, no name reservation changes — closing does not affect the name uniqueness scope.

Tier 2 call per handler:

| Handler | Tier 2 call |
|---|---|
| `CreateFolderHandler` | `nameReservationService.ReserveAsync(tenantId, FolderScope(parentId, collectionId), name, folderId)` |
| `RenameFolderHandler` | `nameReservationService.SwapAsync(tenantId, scope, oldName, newName, folderId)` |
| `MoveFolderHandler` | `nameReservationService.MoveAsync(tenantId, oldScope, newScope, name, folderId)` |
| `ArchiveFolderHandler` | `nameReservationService.ReleaseAsync(tenantId, scope, name)` |

`FolderScope(parentId, collectionId)` resolves to `ScopeKeys.RootFolder(collectionId)` when `parentId` is null and `ScopeKeys.Folder(parentId)` otherwise.

---

## Reference Models

Reference models consumed by this write model's command handlers. All are read-only projections; this context never writes to them directly.

---

### Folder aggregate (event store)

**Consumed via:** `IFolderRepository.GetByIdAsync`  
**Used by:** `CreateFolderHandler` (parent existence + archived-parent check), `MoveFolderHandler` (folder + destination parent load), `ArchiveFolderHandler` (folder load before cascade), `CloseFolderHandler` (folder load before close).

---

### Depth counters (`IUniquenessCounterService`)

**Owned by:** Catalog write model  
**Consumed via:** `IUniquenessCounterService.GetCounterAsync` / `IncrementCounterAsync` / `DecrementCounterAsync`  
**Used by:** `CreateFolderHandler`, `MoveFolderHandler` — enforces the 10-level nesting-depth invariant.

Counter key: `ScopeKeys.Folder(folderId)` / `CounterKeys.Depth`. Initialised on create to absolute depth (1 for root, `parentDepth + 1` otherwise). Adjusted by delta on move.

---

### `media-name-reservations` (DynamoDB — media-folder scope)

**Owned by:** Catalog (same context — internal projection)  
**Consumed via:** `INameReservationService.IsNameAvailableAsync` (Tier 1) and `INameReservationService.ReserveAsync/SwapAsync/MoveAsync/ReleaseAsync` (Tier 2)  
**Used by:** `CreateFolderHandler`, `RenameFolderHandler`, `MoveFolderHandler` — enforces media-folder name uniqueness within parent scope.

Scope keys (see `Catalog.WriteModel.ScopeKeys`):

| Caller | Scope key produced |
|---|---|
| `Folder(parentId)` | `parent:{ParentFolderId}` — non-root media-folder names uniqueness |
| `RootFolder(collectionId)` | `media-collection:{CollectionId}` — root media-folder names uniqueness within a media-collection |
| `MediaItemTitle(folderId)` | `media-item:{FolderId}` — distinct namespace from media-folder names |

---

### Registration counters (per-media-item — blocking archive gate)

**Owned by:** Catalog write model (`IUniquenessCounterService`)  
**Consumed via:** `IFolderArchiveFanOutWorker.HasActiveRegistrationsAsync`  
**Used by:** `ArchiveFolderHandler` — walks the folder subtree and checks each media item's `ActiveRegistrations` counter. Any item with a non-zero counter blocks the archive with `InvalidOperation`.

---

## Related

- [Folder Read Model](./folder.read-model.md)
- [Folder API](./folder.api.md)
- [Catalog Business Scenarios](../../business-scenarios.md)
- [System Spec — Cross-Aggregate Constraint Enforcement](../../../../shared/system-spec.md#cross-aggregate-constraint-enforcement)
