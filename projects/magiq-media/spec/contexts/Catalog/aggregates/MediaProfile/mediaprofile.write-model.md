# MediaProfile — Write Model

_Context: `Catalog`_
_Aggregate: `MediaProfile`_
_Stream prefix: `mp_`_

---

## Purpose

Defines the structural contract for a `MediaItem` type: which media-assets are required or optional, which RecordType schemas supply the metadata schema (pinned to a specific published version), which domain module capabilities are active, and what review/checkout policies apply. MediaItems declare conformance at creation — `MediaProfileId` is immutable after creation.

Follows the **Draft → Publish** versioning model. Published media-profiles are immutable; structural mutations operate on a draft revision. Only `Published` media-profiles may be assigned to MediaItems.

**Capability activation:** `MediaItem → MediaProfile → Capabilities → Domain Modules`. The media-profile's `Capabilities` list is the sole activation mechanism for domain modules — MediaItem carries no behavioral role field.

Owner-scoped. `OwnerId = "owner_system"` for platform-level media-profiles. Query pattern: `OwnerId IN [ownerId, "owner_system"]`. See [Platform Default Profiles](./mediaprofile.defaults.md) for the seeded baseline set.

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| `Name` unique within tenant scope (enforced handler-side via `IMediaProfileService`) | `MediaProfileNameNotUnique` | `CreateMediaProfile` |
| Draft must be non-null to publish | `NoDraftToPublish` | `PublishMediaProfile` |
| Profile must have ≥1 AssetDefinition or RecordTypeRef before publish | `MediaProfileEmpty` | `PublishMediaProfile` |
| Only one draft open at a time | `DraftAlreadyExists` | `CreateMediaProfileRevision` |
| `AttachRecordType` validates version exists in `media-record-types` (draft versions cannot be pinned) | `RecordTypeVersionNotFound` | `AttachRecordTypeToProfile` |
| `UpdatePinnedRecordTypeVersion` only valid for already-attached RecordType | `RecordTypeNotAttached` | `UpdatePinnedRecordTypeVersion` |
| Cannot assign a `Deprecated` MediaProfile to new MediaItems | `MediaProfileDeprecated` | (handler-side on `CreateMediaItem`) |
| `RoleName` unique within draft `AssetDefinitions` | `RoleNameNotUnique` | `AddAssetDefinition` |

---

## Properties

| Property           | Type                               | Notes                                                    |
| ------------------ | ---------------------------------- | -------------------------------------------------------- |
| `MediaProfileId`   | `MediaProfileId`                   | UUID v7-based                                            |
| `TenantId`         | `TenantId`                         | Set from `MediaProfileCreated`. Immutable.               |
| `Name`             | `MediaProfileName`                 | Unique per tenant; reflects published name               |
| `Description`      | `string?`                          |                                                          |
| `OwnerId`          | `OwnerId`                          | Non-nullable                                             |
| `Status`           | `MediaProfileStatus`               | `Draft` (never published) \| `Published` \| `Deprecated` |
| `PublishedVersion` | `int`                              | `0` before first publish                                 |
| `AssetDefinitions` | `IReadOnlyList<AssetDefinition>`   | Published state — immutable between versions             |
| `RecordTypeRefs`   | `IReadOnlyList<RecordTypeVersion>` | Published state — pinned `{RecordTypeId, Version}` pairs |
| `Capabilities`     | `IReadOnlyList<Capability>`        | Published state — domain module activators               |
| `ReviewPolicy`     | `ReviewPolicy`                     | Published state — `None \| RequiredForPublish`           |
| `CheckoutPolicy`   | `CheckoutPolicy`                   | Published state — `None \| RequiredForEdit`              |
| `CompiledTemplate` | `CompiledMetadataTemplate?`        | Null before first publish. Set exclusively by `Apply(MetadataTemplateCompiled)`. Merged field definition list across all pinned RecordType versions at the time of publish. |
| `CreatedAt`        | `DateTimeOffset`                   |                                                          |
| `PublishedAt`      | `DateTimeOffset?`                  |                                                          |
| `Draft`            | `MediaProfileDraft?`               | Present when a revision is in progress                   |

---

## MediaProfileDraft

Contains the full working set of mutations before publish. The draft is a complete copy of the working state:

| Property | Type |
|---|---|
| `BasedOnVersion` | `int?` (`null` for initial draft) |
| `AssetDefinitions` | `IReadOnlyList<AssetDefinition>` |
| `RecordTypeRefs` | `IReadOnlyList<RecordTypeVersion>` |
| `Capabilities` | `IReadOnlyList<Capability>` |
| `ReviewPolicy` | `ReviewPolicy` |
| `CheckoutPolicy` | `CheckoutPolicy` |
| `Name` | `MediaProfileName` |
| `Description` | `string?` |
| `CreatedAt` | `DateTimeOffset` |

---

## AssetDefinition Value Object

| Property               | Type                    | Notes                                            |
| ---------------------- | ----------------------- | ------------------------------------------------ |
| `RoleName`             | `RoleName`              | Unique within media-profile                            |
| `AcceptedContentTypes` | `ContentTypeGroup[]`    | `Image \| Video \| Audio \| Document \| Archive` |
| `IsRequired`           | `bool`                  |                                                  |
| `AllowMultiple`        | `bool`                  | Permits multiple media-assets in this role             |
| `MaxFileSizeBytes`     | `long?`                 |                                                  |
| `DimensionConstraints` | `DimensionConstraints?` | Optional; for image/video roles                  |
| `IsDefault`            | `bool`                  | Only one default per media-profile                     |

---

## Capability Enum

| Value | Effect |
|---|---|
| `Registration` | Registration aggregates may be attached |
| `CheckInOut` | Check-in / check-out lifecycle is available |
| `Retention` | Retention and disposal policies apply |
| `Review` | Review and approval workflow is available |
| `Processing` | Full rendition pipeline; quota tracking; `AssetIngestionSaga` |
| `Distribution` | External publishing and distribution workflows are enabled |
| `Governance` | Audit and compliance policy evaluation is active |
| `VersionControl` | Draft → publish immutable version lifecycle is enforced |
| `Signing` | _(planned)_ Formal document signing lifecycle is available; required for `DocumentSigningSession` initiation |

---

## Status Lifecycle

```
Draft (Status = Draft, never published)
    │
    │  PublishMediaProfile (v1)
    ▼
Published (Status = Published, PublishedVersion = 1)
    │
    │  CreateMediaProfileRevision → draft mutations → PublishMediaProfile (v2, v3, ...)
    ▼
Published (PublishedVersion = N)
    │
    │  DeprecateMediaProfile
    ▼
Deprecated
```

Published media-profiles are immutable between versions. A draft revision (`CreateMediaProfileRevision`) does not affect the published state until `PublishMediaProfile` is called.

---

## Methods (Commands)

| Method | Description |
|---|---|
| `MediaProfile.Create(tenantId, id, ownerId, name, description?)` | Factory. Opens initial draft. Raises `MediaProfileCreated` + `MediaProfileDraftCreated({basedOnVersion: null})`. |
| `CreateRevision()` | Opens a revision draft from the current published state. Guard: no draft open. |
| `AddAssetDefinition(definition)` | Adds asset role to draft. Guard: `RoleName` unique. |
| `UpdateAssetDefinition(roleName, updates)` | Updates existing asset definition in draft. |
| `RemoveAssetDefinition(roleName)` | Removes asset role from draft. |
| `ReorderAssetDefinitions(orderedRoleNames)` | Sets display order in draft. |
| `SetDefaultAssetDefinition(roleName)` | Sets `IsDefault = true`; clears prior default. |
| `AttachRecordType(recordTypeId, version)` | Pins a published RecordType version to draft. Handler validates version exists. |
| `UpdatePinnedRecordTypeVersion(recordTypeId, newVersion)` | Updates pinned version for already-attached RecordType. |
| `DetachRecordType(recordTypeId)` | Removes a RecordType from draft. |
| `SetReviewPolicy(policy)` | Sets `ReviewPolicy` on draft. |
| `SetCheckoutPolicy(policy)` | Sets `CheckoutPolicy` on draft. |
| `SetCapabilities(capabilities)` | Replaces full capabilities list on draft. |
| `DiscardDraft()` | Discards the current draft. |
| `Publish(compiledTemplate, publishedAt)` | Publishes draft as next version. Guard: draft non-null; ≥1 asset def or record type. `compiledTemplate` is always supplied by the handler — never produced internally. Raises `MetadataTemplateCompiled` then `MediaProfilePublished` in the same atomic append. |
| `Deprecate()` | Marks as deprecated. Must have been published. |

---

## Domain Events

| Event | Key Payload Fields | Notes |
|---|---|---|
| `MediaProfileCreated` | `TenantId`†, `MediaProfileId`, `OwnerId`, `Name`, `Description?`, `CreatedAt` | `Status = Draft` |
| `MediaProfileDraftCreated` | `MediaProfileId`, `BasedOnVersion?`, `DraftSnapshot`, `CreatedAt` | `DraftSnapshot` is full copy of base version (or empty for initial) |
| `AssetDefinitionAdded` | `MediaProfileId`, `AssetDefinition`, `AddedAt` | |
| `AssetDefinitionUpdated` | `MediaProfileId`, `RoleName`, `Updates`, `UpdatedAt` | |
| `AssetDefinitionRemoved` | `MediaProfileId`, `RoleName`, `RemovedAt` | |
| `AssetDefinitionsReordered` | `MediaProfileId`, `OrderedRoleNames[]`, `ReorderedAt` | |
| `AssetDefinitionDefaultSet` | `MediaProfileId`, `RoleName`, `SetAt` | |
| `RecordTypeAttachedToProfile` | `MediaProfileId`, `RecordTypeId`, `Version`, `AttachedAt` | |
| `RecordTypeVersionPinnedOnProfile` | `MediaProfileId`, `RecordTypeId`, `OldVersion`, `NewVersion`, `PinnedAt` | |
| `RecordTypeDetachedFromProfile` | `MediaProfileId`, `RecordTypeId`, `DetachedAt` | |
| `ReviewPolicySet` | `MediaProfileId`, `ReviewPolicy`, `SetAt` | Applied to draft |
| `CheckoutPolicySet` | `MediaProfileId`, `CheckoutPolicy`, `SetAt` | Applied to draft |
| `MediaProfileCapabilitiesSet` | `MediaProfileId`, `Capabilities[]`, `SetAt` | Full replacement |
| `MediaProfileDraftDiscarded` | `MediaProfileId`, `DiscardedAt` | |
| `MetadataTemplateCompiled` | `TenantId`, `MediaProfileId`, `NewVersion`, `CompiledTemplate`, `OccurredAt` | Raised atomically **before** `MediaProfilePublished` in the same append. The sole mutation point for `CompiledTemplate` on the aggregate. |
| `MediaProfilePublished` | `MediaProfileId`, `NewVersion`, `Snapshot`, `PublishedAt` | `Snapshot` (`MediaProfilePublishedSnapshot`) = `{ Name, Description?, AssetDefinitions, RecordTypeRefs, CheckoutPolicy, ReviewPolicy, Capabilities, CompiledTemplate }`. `Status → Published`. |
| `MediaProfileDeprecated` | `MediaProfileId`, `DeprecatedAt` | |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command | Notes |
|---|---|
| `CreateMediaProfileCommand(MediaProfileId, OwnerId, Name, Description?)` | |
| `CreateMediaProfileRevisionCommand(MediaProfileId)` | Opens draft from current published |
| `AddAssetDefinitionCommand(MediaProfileId, AssetDefinition)` | |
| `UpdateAssetDefinitionCommand(MediaProfileId, RoleName, Updates)` | |
| `RemoveAssetDefinitionCommand(MediaProfileId, RoleName)` | |
| `ReorderAssetDefinitionsCommand(MediaProfileId, OrderedRoleNames[])` | |
| `SetDefaultAssetDefinitionCommand(MediaProfileId, RoleName)` | |
| `AttachRecordTypeToProfileCommand(MediaProfileId, RecordTypeId, Version)` | Handler validates version in `media-record-types` |
| `UpdatePinnedRecordTypeVersionCommand(MediaProfileId, RecordTypeId, NewVersion)` | Handler validates new version |
| `DetachRecordTypeFromProfileCommand(MediaProfileId, RecordTypeId)` | |
| `SetReviewPolicyCommand(MediaProfileId, ReviewPolicy)` | |
| `SetCheckoutPolicyCommand(MediaProfileId, CheckoutPolicy)` | |
| `SetMediaProfileCapabilitiesCommand(MediaProfileId, Capabilities[])` | |
| `DiscardMediaProfileDraftCommand(MediaProfileId)` | |
| `PublishMediaProfileCommand(MediaProfileId)` | |
| `DeprecateMediaProfileCommand(MediaProfileId)` | |

---

## Published Integration Events

Published inline by the implicit `MediaProfile` integration event publisher (registered in `IntegrationEventPublisherRegistrations`, `Catalog.WriteModel`) immediately after the domain event is persisted. All events target the `media-integration-events` SNS topic.

| Integration Event | Source Domain Event | Notes |
|---|---|---|
| `MediaProfilePublishedMessage` | `MediaProfilePublished` | Carries the full `MediaProfilePublishedSnapshot` — consumed by Catalog's own projectors (fan-out update to `media-item-capability-refs` (AssetManagement) and `media-item-registration-refs` (Registration) for all pinned MediaItems), AssetManagement, DocumentSigning, and Registration to refresh their local media-profile reference models |
| `MediaProfileDeprecatedMessage` | `MediaProfileDeprecated` | Consumed by downstream contexts to mark deprecated media-profiles as no longer assignable |

---

## Consumed Integration Events

Consumed via the `media-cross-module-events` SQS queue.

**From Metadata — consumer: `RecordTypeVersionConsumer`**

Maintains the `media-record-types` write-side reference model used by `AttachRecordTypeHandler`, `PublishMediaProfileHandler`, and `UpdatePinnedRecordTypeVersionHandler` to validate that pinned schema versions exist and are not deprecated.

| Integration Event             | Source   | Action on `media-record-types`                                           |
| ----------------------------- | -------- | ------------------------------------------------------------------------ |
| `RecordTypePublishedMessage`  | Metadata | INSERT new version row (`{RecordTypeId, Version, IsDeprecated = false}`) |
| `RecordTypeDeprecatedMessage` | Metadata | UPDATE `IsDeprecated = true` on all version rows for that `RecordTypeId` |

> `IRecordTypeVersionReadModel` queries this table directly at command time — no command dispatch occurs.

---

## Handler-side Pre-conditions

| Handler                                | Service                                               | Guard type                                 | Condition                                                                                                                                 |
| -------------------------------------- | ----------------------------------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `CreateMediaProfileHandler`            | `IMediaProfileService.NameExistsAsync`                | Blocking — `InvalidOperation`              | Reject if name already in use within tenant scope                                                                                         |
| `AttachRecordTypeHandler`              | `IRecordTypeVersionReadModel.VersionExistsAsync`      | Blocking — `InvalidOperation`              | Reject if the requested `{RecordTypeId, Version}` does not exist                                                                          |
| `AttachRecordTypeHandler`              | `IRecordTypeVersionReadModel.IsDeprecatedAsync`       | Blocking — `InvalidOperation`              | Reject if the record type is deprecated                                                                                                   |
| `PublishMediaProfileHandler`           | `IMediaProfileService.NameExistsAsync`                | Blocking — `InvalidOperation`              | Only when `draft.Name != profile.Name` (name changed in draft); reject if the new name is already in use within tenant scope. Skipped when name is unchanged. See [Cross-Aggregate Constraint Enforcement](../../../../../shared/system-spec.md#cross-aggregate-constraint-enforcement). |
| `PublishMediaProfileHandler`           | `IRecordTypeVersionReadModel.VersionExistsAsync`      | Blocking — `InvalidOperation`              | Per each `draft.RecordTypeRefs` entry — reject if any pinned version no longer exists                                                     |
| `PublishMediaProfileHandler`           | `IRecordTypeVersionReadModel.IsDeprecatedAsync`       | Blocking — `InvalidOperation`              | Per each `draft.RecordTypeRefs` entry — reject if any pinned record type is deprecated                                                    |
| `PublishMediaProfileHandler`           | `IMediaProfileDomainService.CheckRevisionBreaksAsync` | Blocking — delegates from service `Result` | Only called when `draft.BasedOnVersion > 0`; best-effort, non-transactional break detection                                               |
| `PublishMediaProfileHandler`           | `IMediaProfileDomainService.CompileTemplateAsync`     | Blocking — delegates from service `Result` | Always called; compiles merged metadata template from all pinned RecordType versions; result passed into `media-profile.Publish(template, ...)` |
| `SetAssetDefinitionDefaultHandler`     | `IMediaProfileAssetQueryService.GetSummaryAsync`      | Blocking — `InvalidOperation`              | Only called when `DefaultAssetId` is not null; asset must be `Active` and its `ContentType` must be accepted by the role                  |
| `UpdatePinnedRecordTypeVersionHandler` | `IRecordTypeVersionReadModel.VersionExistsAsync`      | Blocking — `InvalidOperation`              | Reject if the new version does not exist                                                                                                  |
| `UpdatePinnedRecordTypeVersionHandler` | `IRecordTypeVersionReadModel.IsDeprecatedAsync`       | Blocking — `InvalidOperation`              | Reject if the record type is deprecated                                                                                                   |

---

## Write Model Service Interfaces

```csharp
/// <summary>
/// Write-side query service for MediaProfile state checks.
/// Used by CreateMediaProfile to enforce name uniqueness within a tenant.
/// </summary>
interface IMediaProfileService {
    Task<bool> IsPublishedAsync(TenantId tenantId, MediaProfileId mediaProfileId, CancellationToken ct = default);
    Task<bool> NameExistsAsync(TenantId tenantId, MediaProfileName name, CancellationToken ct = default);
}

/// <summary>
/// Write-side read model for validating RecordType version references on a MediaProfile draft.
/// </summary>
interface IRecordTypeVersionReadModel {
    Task<bool> VersionExistsAsync(TenantId tenantId, RecordTypeId recordTypeId, int version, CancellationToken ct = default);
    Task<bool> IsDeprecatedAsync(TenantId tenantId, RecordTypeId recordTypeId, CancellationToken ct = default);
}

/// <summary>
/// Domain service for MediaProfile publish-time operations.
/// Handles revision break detection and metadata template compilation.
/// </summary>
interface IMediaProfileDomainService {
    Task<Result<Unit, DomainError>> CheckRevisionBreaksAsync(
        TenantId tenantId,
        MediaProfileId profileId,
        MediaProfileDraft draft,
        int basedOnVersion,
        CancellationToken ct = default);

    Task<Result<CompiledMetadataTemplate, DomainError>> CompileTemplateAsync(
        IReadOnlyList<RecordTypeVersion> recordTypeRefs,
        CancellationToken ct = default);
}

/// <summary>
/// Write-side asset query service for SetAssetDefinitionDefault validation.
/// Returns a lightweight summary of an asset's status and content type.
/// </summary>
interface IMediaProfileAssetQueryService {
    Task<MediaProfileAssetReference?> GetSummaryAsync(TenantId tenantId, AssetId assetId, CancellationToken ct = default);
}

/// <summary>Supporting record returned by IMediaProfileAssetQueryService.</summary>
sealed record MediaProfileAssetReference(AssetId AssetId, AssetStatus Status, MediaContentType ContentType);
```

### `IMediaProfileService` — usage

| Handler | Method | When |
|---|---|---|
| `CreateMediaProfileHandler` | `NameExistsAsync` | Before `MediaProfile.Create(...)` — blocks if name taken |
| `PublishMediaProfileHandler` | `NameExistsAsync` | Before version checks, only when `draft.Name != profile.Name` — blocks if new name taken |

### `IRecordTypeVersionReadModel` — usage

| Handler | Method | When |
|---|---|---|
| `AttachRecordTypeHandler` | `VersionExistsAsync` | Before `repository.GetByIdAsync` |
| `AttachRecordTypeHandler` | `IsDeprecatedAsync` | After `VersionExistsAsync` passes |
| `PublishMediaProfileHandler` | `VersionExistsAsync` | Iterates `draft.RecordTypeRefs` before domain service calls |
| `PublishMediaProfileHandler` | `IsDeprecatedAsync` | Iterates `draft.RecordTypeRefs` after each `VersionExistsAsync` passes |
| `UpdatePinnedRecordTypeVersionHandler` | `VersionExistsAsync` | Before `repository.GetByIdAsync` |
| `UpdatePinnedRecordTypeVersionHandler` | `IsDeprecatedAsync` | After `VersionExistsAsync` passes |

### `IMediaProfileDomainService` — usage

| Handler                      | Method                     | When                                                                                                                       |
| ---------------------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `PublishMediaProfileHandler` | `CheckRevisionBreaksAsync` | After all version checks pass; only when `draft.BasedOnVersion > 0`                                                        |
| `PublishMediaProfileHandler` | `CompileTemplateAsync`     | After `CheckRevisionBreaksAsync` (or directly if `BasedOnVersion == 0`); result passed to `media-profile.Publish(template, ...)` |

### `IMediaProfileAssetQueryService` — usage

| Handler | Method | When |
|---|---|---|
| `SetAssetDefinitionDefaultHandler` | `GetSummaryAsync` | When `command.DefaultAssetId` is not null; validates `Status == Active` and `ContentType` is accepted by the role |

---

## Constraint Enforcement — Implementation Notes

### `IMediaProfileService` Implementation

`NameExistsAsync` is backed by `media-name-reservations` using scope key `MEDIAPROFILE`. `IsPublishedAsync` queries `media-profiles`.

```csharp
sealed class MediaProfileService(IAmazonDynamoDB dynamo) : IMediaProfileService
{
    /// Returns true if the name is already reserved within the tenant.
    /// Scope key: MEDIAPROFILE (global per tenant).
    /// ConsistentRead = true — reservation written by a concurrent handler is immediately visible.
    public async Task<bool> NameExistsAsync(
        TenantId tenantId, MediaProfileName name, CancellationToken ct)
    {
        var key = NameReservationKey.For(
            tenantId, "MEDIAPROFILE", name.Value.Trim().ToLowerInvariant());
        var response = await dynamo.GetItemAsync(new GetItemRequest
        {
            TableName = "media-name-reservations",
            Key = key,
            ConsistentRead = true
        }, ct);
        return response.IsItemSet; // true = name taken
    }

    /// Returns true if the media-profile exists and its status is Published.
    /// Used by Collection handlers to validate DefaultMediaProfileId.
    public async Task<bool> IsPublishedAsync(
        TenantId tenantId, MediaProfileId profileId, CancellationToken ct)
    {
        var response = await dynamo.GetItemAsync(new GetItemRequest
        {
            TableName = "media-profiles",
            Key = DynamoKey.For(tenantId, profileId),
            ProjectionExpression = "MediaProfileStatus"
        }, ct);
        return response.IsItemSet
            && response.Item["MediaProfileStatus"].S == "Published";
    }
}
```

All handlers call `repository.Save(media-profile)` and `nameReservationService.Reserve(intent)` — both register with the ambient `ITransactionScope` and are committed atomically by the MediatR `TransactionBehavior`. `NameReservationConflictException` is handled by the `NameReservationConflictBehavior`; handlers never catch it directly.

Intent per operation: `CreateMediaProfileHandler` → `NameReservation.Reserve(tenantId, ReservationScope.MediaProfile, name)`. `PublishMediaProfileHandler` (when `draft.Name != profile.Name`) → `NameReservation.Swap(tenantId, ReservationScope.MediaProfile, oldName, newName)`. `DeprecateMediaProfileHandler` → `NameReservation.Release(tenantId, ReservationScope.MediaProfile, name)`.

For the canonical handler structure see [Collection — Constraint Enforcement](../Collection/media-collection.write-model.md#constraint-enforcement--implementation-notes).

---

## Reference Models

Reference models consumed by this write model's command handlers. All are read-only projections; this context never writes to them directly.

---

### `media-record-types` (DynamoDB — version/status slice)

**Owned by:** Metadata  
**Consumed via:** `IRecordTypeVersionReadModel` (`VersionExistsAsync`, `IsDeprecatedAsync`)  
**Used by:** `AttachRecordTypeHandler` (pinned version must exist and not be deprecated), `PublishMediaProfileHandler` (re-validates every `RecordTypeRef` in `draft.RecordTypeRefs` — any missing or deprecated version blocks publish), `UpdatePinnedRecordTypeVersionHandler` (new version must exist and not be deprecated).

| Field | Type | Purpose |
|---|---|---|
| `RecordTypeId` | `string` | Lookup key |
| `Version` | `int` | SK — confirms the specific pinned version exists |
| `IsDeprecated` | `bool` | Blocks attaching, pinning, or publishing with deprecated record types |

**Subscribed integration events (projector owned by Catalog, consuming Metadata via `media-projector` SQS queue):**

| Event | Source | Write |
|---|---|---|
| `RecordTypeCreated` | Metadata | INSERT with `Version = 1`, `IsDeprecated = false` |
| `RecordTypeVersionPublished` | Metadata | INSERT new version row |
| `RecordTypeDeprecated` | Metadata | UPDATE `IsDeprecated = true` on all versions |

---

### `media-assets` (DynamoDB — active asset slice)

**Owned by:** AssetManagement  
**Consumed via:** `IMediaProfileAssetQueryService` (`GetSummaryAsync`)  
**Used by:** `SetAssetDefinitionDefaultHandler` — only when `DefaultAssetId` is non-null; the referenced asset must be `Active` and its `ContentType` must be accepted by the target role definition.

| Field | Type | Purpose |
|---|---|---|
| `AssetId` | `string` | Lookup key |
| `Status` | `AssetStatus` | Must be `Active` |
| `ContentType` | `MediaContentType` | Must match `AcceptedContentTypes` of the target `AssetDefinition` role |

**Subscribed integration events (projector owned by Catalog, consuming AssetManagement via `media-projector` SQS queue):**

| Event | Source | Write |
|---|---|---|
| `AssetUploaded` | AssetManagement | INSERT with `Status = Pending`, `ContentType` |
| `AssetProcessingCompleted` | AssetManagement | UPDATE `Status = Active` |
| `AssetValidationPassed` (fast-exit path) | AssetManagement | UPDATE `Status = Active` |
| `AssetArchived` | AssetManagement | UPDATE `Status = Archived` |
| `AssetDeleted` | AssetManagement | UPDATE `Status = Deleted` |

---

## Related

- [MediaProfile Read Model](./mediaprofile.read-model.md)
- [MediaProfile API](./mediaprofile.api.md)
- [Platform Default Profiles](./mediaprofile.defaults.md)
- [RecordType Write Model](../../../Metadata/aggregates/RecordType/recordtype.write-model.md)
- [Catalog Business Scenarios](../../business-scenarios.md)
- [MediaItem Write Model](../MediaItem/mediaitem.write-model.md)
- [System Spec — Cross-Aggregate Constraint Enforcement](../../../../shared/system-spec.md#cross-aggregate-constraint-enforcement)
