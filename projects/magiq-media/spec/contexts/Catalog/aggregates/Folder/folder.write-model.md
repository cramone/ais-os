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
| Folder must be empty (eventually consistent check) | `FolderNotEmpty` | `ArchiveFolder` |
| `ExpectedVersion` must match current `Version` | `ConcurrencyConflict` | All mutating commands |

---

## Properties

| Property         | Type             | Notes                                              |
| ---------------- | ---------------- | -------------------------------------------------- |
| `FolderId`       | `FolderId`       | UUID v7-based. Caller-generated.                   |
| `TenantId`       | `TenantId`       | Set from `FolderCreated` (first field). Immutable. |
| `CollectionId`   | `CollectionId`   | Immutable after creation.                          |
| `ParentFolderId` | `FolderId?`      | Null = root media-folder within Collection.              |
| `Name`           | `FolderName`     | Max 255 chars. Unique within parent scope.         |
| `OwnerId`        | `OwnerId`        | Denormalised from Collection at creation time.     |
| `IsArchived`     | `bool`           |                                                    |
| `Version`        | `int`            | Event sequence count — for optimistic concurrency. |
| `CreatedAt`      | `DateTimeOffset` |                                                    |
| `UpdatedAt`      | `DateTimeOffset` | Derived from last applied event.                   |

---

## Methods (Commands)

| Method                                                                            | Description                      | Preconditions                                                               |
| --------------------------------------------------------------------------------- | -------------------------------- | --------------------------------------------------------------------------- |
| `Folder.Create(tenantId, folderId, collectionId, parentFolderId?, name, ownerId)` | Factory. Raises `FolderCreated`. | Depth ≤ 10, no circular chain (handler-side)                                |
| `Rename(newName, expectedVersion)`                                                | Raises `FolderRenamed`.          | Not archived                                                                |
| `Move(newParentFolderId?, expectedVersion)`                                       | Raises `FolderMoved`.            | Not archived; same Collection; depth ≤ 10; no circular chain (handler-side) |
| `Archive(expectedVersion)`                                                        | Raises `FolderArchived`.         | Not already archived; empty (handler-side eventually consistent check)      |

---

## Domain Events

| Event                | Key Payload Fields                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `FolderCreated`      | `TenantId`†, `FolderId`, `CollectionId`, `ParentFolderId?`, `Name`, `OwnerId` |
| `FolderRenamed`      | `FolderId`, `OldName`, `NewName`                                                           |
| `FolderMoved`        | `FolderId`, `OldParentFolderId?`, `NewParentFolderId?`                                     |
| `FolderArchived`     | `FolderId`, `ArchivedAt`                                                                   |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command                                                                                           | Handler                     | Result                                     |
| ------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------ |
| `CreateFolderCommand(FolderId, CollectionId, ParentFolderId?, Name, ExpectedVersion?)` | `CreateFolderHandler`       | `Result<FolderId, DomainError>`            |
| `RenameFolderCommand(FolderId, NewName, ExpectedVersion)`                                         | `RenameFolderHandler`       | `Result<Unit, DomainError>`                |
| `MoveFolderCommand(FolderId, NewParentFolderId?, ExpectedVersion)`                                | `MoveFolderHandler`         | `Result<Unit, DomainError>`                |
| `ArchiveFolderCommand(FolderId, ExpectedVersion)`                                                 | `ArchiveFolderHandler`      | `Result<ArchiveFolderResult, DomainError>` |

**`ArchiveFolderResult`:** `(bool HasActiveRegistrations)` — returned to the caller so downstream media-registration clean-up can be triggered if needed; does not block the archive.

**Handler-side pre-conditions:**

| Handler | Pre-condition | Interface | Guard type |
|---|---|---|---|
| `CreateFolderHandler` | If `ParentFolderId` supplied: parent media-folder must exist | `IFolderHierarchyService.ParentExistsAsync` | Blocking — `ResourceNotFound` |
| `CreateFolderHandler` | Name must be unique within parent scope (Tier 1) | `IFolderHierarchyService.NameExistsInScopeAsync` | Blocking — `InvalidOperation` |
| `CreateFolderHandler` | Nesting depth must not exceed 10 | `IFolderHierarchyService.GetNestingDepthAsync` | Blocking — `InvalidOperation` |
| `RenameFolderHandler` | Same-name short-circuit — no-op when name unchanged | — | Returns success without state change |
| `RenameFolderHandler` | New name must be unique within parent scope (Tier 1) | `IFolderHierarchyService.NameExistsInScopeAsync` | Blocking — `InvalidOperation` |
| `MoveFolderHandler` | No-op move guard; parent exists; depth ≤ 10; no circular chain | `IFolderHierarchyService.CanMoveAsync` | Blocking — delegates error from service `Result` |
| `MoveFolderHandler` | Folder name must be unique in destination scope (Tier 1) | `IFolderHierarchyService.NameExistsInScopeAsync` | Blocking — `InvalidOperation` |
| `ArchiveFolderHandler` | Folder has no active child folders or media media-items | `IFolderDomainService.HasActiveChildrenAsync` | Blocking — `InvalidOperation` |
| `ArchiveFolderHandler` | Subtree active-registrations check | `IFolderDomainService.HasActiveRegistrationsInSubtreeAsync` | **Informational only** — result propagated via `ArchiveFolderResult`; does not block |

`CanMoveAsync` validates hierarchy invariants only; name uniqueness in the destination scope is a separate handler-side call to `NameExistsInScopeAsync` so the same Tier 1 abstraction is used by every command that touches a media-folder name.

---

## Published Integration Events

Published inline by `FolderIntegrationEventPublisher` (`Catalog.WriteModel`) immediately after the domain event is persisted. All events target the `media-integration-events` SNS topic.

| Integration Event | Source Domain Event | Notes |
|---|---|---|
| `FolderCreatedMessage` | `FolderCreated` | Consumed by Search/Discovery to index the media-folder hierarchy |
| `FolderRenamedMessage` | `FolderRenamed` | Carries `OldName`, `NewName` — consumed by Search/Discovery |
| `FolderMovedMessage` | `FolderMoved` | Carries `OldParentFolderId`, `NewParentFolderId` — consumed by Search/Discovery |
| `FolderArchivedMessage` | `FolderArchived` | Consumed by Search/Discovery to remove the folder from the hierarchy index. No read-model fan-out is required — `ArchiveFolder` enforces a non-empty precondition via `HasActiveChildrenAsync`, so no descendant items or child folders exist when this event fires. `FolderProjector` sets `IsArchived = true` on `media-folders` and `media-folder-detail`. |

---

## Consumed Integration Events

This write model consumes **no integration events**. All handler inputs arrive via direct API calls or intra-context command dispatch. The `IFolderHierarchyService` and `IFolderDomainService` reference models are backed by same-context DynamoDB queries on `media-folders` — no cross-context event subscription is required.

---

## Write Model Service Interfaces

```csharp
interface IFolderHierarchyService {
    /// Validates hierarchy invariants for a move: no-op move guard, parent
    /// existence, no-self-descendant cycle, and combined depth + subtree-height
    /// bound. Name uniqueness in the destination scope is the caller's
    /// responsibility — see NameExistsInScopeAsync (Tier 1) and
    /// INameReservationService.MoveAsync (Tier 2). Cross-collection moves are
    /// rejected by the Folder aggregate itself (CollectionId is immutable).
    Task<Result<Unit, IDomainError>> CanMoveAsync(Folder media-folder, FolderId? newParentId, CancellationToken ct = default);

    /// Returns the current nesting depth of parentFolderId (0 = root level).
    Task<int> GetNestingDepthAsync(TenantId tenantId, FolderId? parentFolderId, CancellationToken ct = default);

    /// Returns true if a media-folder with the given name already exists under parentFolderId
    /// (null = collection root) within the tenant.
    Task<bool> NameExistsInScopeAsync(TenantId tenantId, FolderId? parentFolderId, FolderName name, CancellationToken ct = default);

    /// Returns true if parentFolderId exists and is not archived within the tenant.
    Task<bool> ParentExistsAsync(TenantId tenantId, FolderId parentFolderId, CancellationToken ct = default);
}

interface IFolderDomainService {
    /// Returns true if the media-folder has any active (non-archived) child folders OR
    /// any active MediaItems directly inside it. Backed by two reference indexes
    /// combined with OR semantics — either signal blocks ArchiveFolder.
    Task<bool> HasActiveChildrenAsync(TenantId tenantId, FolderId folderId, CancellationToken ct = default);

    /// Returns true if any Registration in active status exists for any media-item in the media-folder subtree.
    /// Queries the read model — eventually consistent. Informational only.
    Task<bool> HasActiveRegistrationsInSubtreeAsync(TenantId tenantId, FolderId folderId, CancellationToken ct = default);
}
```

**`IFolderHierarchyService` usage:**

| Handler | Method | Call site | Guard |
|---|---|---|---|
| `CreateFolderHandler` | `ParentExistsAsync` | First check, if `ParentFolderId` is not null | `!result` → `ResourceNotFound("Parent media-folder not found.")` |
| `CreateFolderHandler` | `NameExistsInScopeAsync(TenantId, ParentFolderId, Name)` | After parent check | `result` → `InvalidOperation("Folder name is already in use.")` |
| `CreateFolderHandler` | `GetNestingDepthAsync(TenantId, ParentFolderId)` | After name check | `depth + 1 > 10` → `InvalidOperation("Folder nesting depth is too deep.")` |
| `RenameFolderHandler` | `NameExistsInScopeAsync(TenantId, folder.ParentFolderId, NewName)` | After same-name short-circuit, before `media-folder.Rename(...)` | `result` → `InvalidOperation("Folder name is already in use.")` |
| `MoveFolderHandler` | `CanMoveAsync(media-folder, NewParentFolderId)` | Before destination name check | `!result.IsSuccess` → `result.Error.ToDomainError()` |
| `MoveFolderHandler` | `NameExistsInScopeAsync(TenantId, NewParentFolderId, media-folder.Name)` | After `CanMoveAsync`, before `media-folder.Move(...)` | `result` → `InvalidOperation("A media-folder with this name already exists in the destination.")` |

**`IFolderDomainService` usage:**

| Handler | Method | Call site | Guard |
|---|---|---|---|
| `ArchiveFolderHandler` | `HasActiveChildrenAsync(TenantId, FolderId)` | Before `media-folder.Archive(...)` | `result` → `InvalidOperation("Folder has active children.")` |
| `ArchiveFolderHandler` | `HasActiveRegistrationsInSubtreeAsync(TenantId, FolderId)` | After `media-folder.Archive(...)`, before `repository.SaveAsync(...)` | Informational — stored in `ArchiveFolderResult.HasActiveRegistrations` |

---

## Constraint Enforcement — Implementation Notes

### `IFolderHierarchyService` Implementation

Backed by three reference-model indexes:

| Index | Used by |
|---|---|
| `FolderStatusIndex` | `ParentExistsAsync`, `GetNestingDepthAsync`, `CanMoveAsync` (ancestor walk) |
| `FolderNameScopeIndex` | `NameExistsInScopeAsync` |
| `FolderChildIndex` | `CanMoveAsync` (subtree-height BFS) |

```csharp
sealed class FolderHierarchyService(
    IReferenceLookup<FolderStatusIndex> folderStatusIndex,
    IReferenceLookup<FolderNameScopeIndex> folderNameScopeIndex,
    IReferenceLookup<FolderChildIndex> folderChildrenIndex) : IFolderHierarchyService
{
    /// Tier 1 — read-model name check. Queries the FolderNameScopeIndex
    /// projection of media-name-reservations. Returns true if a media-folder
    /// with the given name already exists in the parent scope.
    public async Task<bool> NameExistsInScopeAsync(
        TenantId tenantId, FolderId? parentFolderId, FolderName name, CancellationToken ct)
    {
        var entry = await folderNameScopeIndex.GetAsync(
            FolderNameScopeIndex.CreateKey(tenantId, parentFolderId, name.Value), ct);
        return entry is not null;
    }

    /// Walks the ancestor chain from parentFolderId via FolderStatusIndex
    /// point lookups. Capped at 10 reads by the nesting-depth invariant.
    public async Task<int> GetNestingDepthAsync(
        TenantId tenantId, FolderId? parentFolderId, CancellationToken ct) { /* … */ }

    /// True iff the parent media-folder exists and is not archived.
    public async Task<bool> ParentExistsAsync(
        TenantId tenantId, FolderId parentFolderId, CancellationToken ct) { /* … */ }

    /// Hierarchy invariants only. Name uniqueness in the destination scope
    /// is the caller's responsibility — see NameExistsInScopeAsync (Tier 1)
    /// and INameReservationService.MoveAsync (Tier 2).
    public async Task<Result<Unit, IDomainError>> CanMoveAsync(
        Folder media-folder, FolderId? newParentId, CancellationToken ct)
    {
        // 1. No-op move guard.
        if (newParentId == folder.ParentFolderId)
            return DomainError.InvalidOperation("Cannot move media-folder to its current parent.");

        // 2. Move to root — no further hierarchy checks needed.
        if (newParentId is null) return Unit.Value;

        // 3. Parent exists and is active.
        if (!await ParentExistsAsync(media-folder.TenantId, newParentId.Value, ct))
            return DomainError.InvalidOperation("Parent media-folder not found.");

        // 4. No-self-descendant cycle.
        if (await IsDescendantOfAsync(media-folder.TenantId, media-folder.Id, newParentId.Value, ct))
            return DomainError.InvalidOperation("Cannot move media-folder to a descendant of itself.");

        // 5. Combined depth + subtree-height bound.
        var newParentDepth = await GetNestingDepthAsync(media-folder.TenantId, newParentId, ct);
        var subtreeHeight = await GetSubtreeHeightAsync(media-folder.TenantId, media-folder.Id, ct);
        if (newParentDepth + subtreeHeight > 10)
            return DomainError.InvalidOperation("Folder nesting depth is too deep.");

        return Unit.Value;
    }

    // Private helpers: IsDescendantOfAsync walks the parent chain via FolderStatusIndex;
    // GetSubtreeHeightAsync runs a BFS over FolderChildIndex bounded by the depth-10 invariant.
}
```

For the canonical handler structure see [Collection — Constraint Enforcement](./Collection/media-collection.write-model.md#constraint-enforcement--implementation-notes).

Handlers call the platform `INameReservationService` directly using the imperative async methods exposed by `Magiq.Platform.UniquenessRegistry`. The Tier 2 call is wrapped in `try { … } catch (NameReservationConflictException)` and mapped to `InvalidOperation`. (The intent-based pattern documented in [System Spec — Cross-Aggregate Constraint Enforcement](../../../../shared/system-spec.md#cross-aggregate-constraint-enforcement) describes the long-term direction; the current platform surface is imperative.)

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

### `media-folders` (DynamoDB — hierarchy slice)

**Owned by:** Catalog (same context — internal projection)  
**Consumed via:** `IFolderHierarchyService` (`ParentExistsAsync`, `GetNestingDepthAsync`, `CanMoveAsync`), `IFolderDomainService` (`HasActiveChildrenAsync`)  
**Used by:** `CreateFolderHandler` (parent existence check, depth enforcement, child-name uniqueness), `RenameFolderHandler` (child-name uniqueness under same parent), `MoveFolderHandler` (cross-collection guard, cycle detection, depth re-check), `ArchiveFolderHandler` (active-children gate before archive).

| Field | Type | Purpose |
|---|---|---|
| `FolderId` | `string` | Lookup key |
| `ParentFolderId` | `string?` | Depth traversal and circular-reference detection on move |
| `CollectionId` | `string` | Cross-collection guard — move target must share `CollectionId` |
| `IsArchived` | `bool` | Active-parent check; archived parent rejects new children |
| `ActiveChildCount` | `int` | Backs `IFolderDomainService.HasActiveChildrenAsync` (child-folder side of the OR). Surfaced via `FolderChildCountIndex`. |
| `ActiveItemCount` | `int` | Backs `IFolderDomainService.HasActiveChildrenAsync` (active-item side of the OR). Surfaced via `FolderActiveItemCountIndex`. Either non-zero blocks `ArchiveFolder`. |

**Subscribed events (same-context projection — `media-projector` SQS queue):**

| Event | Write |
|---|---|
| `FolderCreated` | INSERT |
| `FolderRenamed` | UPDATE `Name` |
| `FolderMoved` | UPDATE `ParentFolderId`, `CollectionId` |
| `FolderArchived` | UPDATE `IsArchived = true` |
| `MediaItemCreated` (with `FolderId`) | Increments child-item count used by `HasActiveChildrenAsync` |
| `MediaItemArchived` / `MediaItemDeleted` | Decrements child-item count |

---

### `media-name-reservations` (DynamoDB — media-folder scope)

**Owned by:** Catalog (same context — internal projection)  
**Consumed via:** `IFolderHierarchyService.NameExistsInScopeAsync` (Tier 1) and `INameReservationService` (Tier 2)  
**Used by:** `CreateFolderHandler`, `RenameFolderHandler`, `MoveFolderHandler` — enforces media-folder name uniqueness within parent scope.

Scope keys (see `Catalog.WriteModel.ScopeKeys`):

| Caller | Scope key produced |
|---|---|
| `Folder(parentId)` | `parent:{ParentFolderId}` — non-root media-folder names uniqueness |
| `RootFolder(collectionId)` | `media-collection:{CollectionId}` — root media-folder names uniqueness within a media-collection |
| `MediaItemTitle(folderId)` | `media-item:{FolderId}` — distinct namespace from media-folder names |

Folder and media-item scope keys are **deliberately distinct** — a media media-item titled `"Foo"` and a child media-folder named `"Foo"` under the same parent do not collide.

| Field | Type | Purpose |
|---|---|---|
| `PK` | `string` | `TENANT#{TenantId}#SCOPE#{ScopeKey}#NAME#{NormalizedName}` |
| `SK` | `string` | (set by platform `INameReservationService` implementation) |

**Subscribed events (same-context projection — `media-projector` SQS queue):**

| Event | Write |
|---|---|
| `FolderCreated` | Driven by `CreateFolderHandler` Tier 2 `ReserveAsync` — reservation under the parent or root scope |
| `FolderRenamed` | Driven by `RenameFolderHandler` Tier 2 `SwapAsync` — atomic delete-old + insert-new in same scope |
| `FolderMoved` | Driven by `MoveFolderHandler` Tier 2 `MoveAsync` — atomic delete from old scope + insert into new scope |
| `FolderArchived` | Driven by `ArchiveFolderHandler` Tier 2 `ReleaseAsync` — name becomes available for reuse |

---

### `media-items` + Registration read model (informational — archive gate)

**Owned by:** Catalog / Registration  
**Consumed via:** `IFolderDomainService` (`HasActiveRegistrationsInSubtreeAsync`)  
**Used by:** `ArchiveFolderHandler` — queries Registration read model to surface whether any active media-registration exists in the subtree. Result is **informational only** — it does not block the archive; it is propagated to the caller via `ArchiveFolderResult.HasActiveRegistrations` so the API layer can surface a warning.

| Field | Type | Purpose |
|---|---|---|
| `FolderId` / subtree path | `string` | Scope for the subtree media-registration query |
| `RegistrationStatus` | `enum` | Active (`Initiated`, `PendingApproval`, `Confirmed`) statuses trigger the warning flag |

**Subscribed events:** Driven by Registration's own projector — no additional subscription required by Folder handlers.

---

## Related

- [Folder Read Model](./media-folder.read-model.md)
- [Folder API](./media-folder.api.md)
- [Catalog Business Scenarios](../../business-scenarios.md)
- [System Spec — Cross-Aggregate Constraint Enforcement](../../../../shared/system-spec.md#cross-aggregate-constraint-enforcement)
