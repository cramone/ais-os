# Catalog — Context Overview

_Bounded context: `Catalog`_
_Service: `Catalog` module_

---

## Purpose

Owns the organisational and cataloguing layer of the platform. Manages how media media-assets are grouped, structured, and published. The `MediaItem` is the core cataloguing unit that binds media-assets, metadata, and lifecycle state together under a structural contract defined by a `MediaProfile`.

---

## Responsibilities

- Creating and managing `Collection` namespaces (visibility, tags, archiving)
- Creating and managing `Folder` hierarchies within Collections (max 10 levels deep)
- Creating, assigning, moving, and publishing `MediaItem` entries
- Tracking MediaItem lifecycle: Draft → PendingApproval → Published → Withdrawn/Archived
- Managing checkout/locking state (`CheckedOut` / `Available`)
- Managing asset role assignments on MediaItems
- Managing metadata field values against `RecordType` schema versions
- Linking `Registration`, `MediaChangeRequest`, and `DocumentSigningSession` references
- Publishing visibility and lifecycle integration events for downstream consumers
- Defining and versioning structural contracts for MediaItem types (`MediaProfile`)
- Activating domain modules for conforming MediaItems via the `MediaProfile` Capability model

---

## Aggregate List

| Aggregate | Description |
|---|---|
| `Collection` | Top-level organisational namespace. Controls visibility (`Private`, `Unlisted`, `Public`) and scopes Folders and MediaItems. |
| `Folder` | Hierarchical container within a Collection. Max 10 levels. MediaItem membership expressed via `MediaItem.FolderId`. |
| `MediaItem` | Core cataloguing unit. Conforms to a `MediaProfile`. Owns asset references, validated metadata, and lifecycle state. |
| `MediaProfile` | Structural contract for a MediaItem type. Defines asset role definitions, pinned RecordType schemas, capabilities, and review/checkout policies. Follows the Draft → Publish versioning model. |
| `BulkFolderImportJob` | Tracks lifecycle of async large-volume folder hierarchy imports. Processes line-delimited paths, CSV, or JSON input formats. Splits into chunks of 200, tracks progress, records per-item results. |
| `BulkMediaImportJob` | Tracks lifecycle of async large-volume media item imports. Coordinates multi-phase upload → validation → cataloging → processing pipeline. Tracks per-phase progress, issues pre-signed upload URLs, records per-item results. |

---

## Platform Default Profiles

Five platform-level `MediaProfile` aggregates are seeded at tenant provisioning time with `OwnerId = "owner_system"` and made available to all tenants. They cover the primary content types and governance tiers:

| Profile | Content Types | Processing | Governance |
|---|---|---|---|
| `Simple Image` | Image | ✓ | None |
| `Simple Video` | Video (+ optional Image thumbnail) | ✓ | None |
| `Simple Audio` | Audio (+ optional Image artwork) | ✓ | None |
| `Document` | Document | ✗ (fast-exit) | None |
| `Governed Media Record` | Image \| Video \| Audio (+ optional Document) | ✓ | Review + Checkout + Registration |

The `Document` profile intentionally omits the `Processing` capability — assets on this profile take the fast-exit saga path (virus scan only, stored in `media-documents`). It is the required structural contract for registration supporting documents.

See [MediaProfile Platform Default Profiles](./aggregates/MediaProfile/mediaprofile.defaults.md) for full asset definitions, capability lists, and seeding behaviour.

---

## Service Boundaries

**Owns:**
- `Collection`, `Folder`, `MediaItem`, `MediaProfile` aggregate event streams
- `media-collections`, `media-collection-detail`, `media-folders`, `media-folder-detail`, `media-items`, `media-item-detail`, `media-item-versions` DynamoDB read model tables
- `media-profiles`, `media-profiles` DynamoDB tables
- OpenSearch `media-items` index

**Does not own:**
- Asset binary storage (→ AssetManagement)
- Metadata schema definitions (→ Metadata — `RecordType`)
- Review decision logic (→ ChangeRequests)
- Signing envelope lifecycle (→ DocumentSigning)
- Registration lifecycle (→ Registration)

**Coupling rules:**
- `MediaItem` holds `MediaProfileId` — capabilities are resolved via the `media-profiles` read model at command time
- `MediaItem` holds `RegistrationIds` — append-only reference list; Registration context owns the Registration aggregates
- `MediaItem` holds `ActiveSigningSessionId` and `ActiveMediaChangeRequestId` — set/cleared via events from Sagas
- `MediaProfile` pins `RecordTypeVersion` references — handler validates against `media-record-types` (owned by Metadata)

---

## External Dependencies

| Dependency | Direction | Pattern |
|---|---|---|
| Metadata (RecordType) | Internal cross-context | `MediaProfile` pins published RecordType versions; `IMetadataValidator` validates `Metadata.Draft` at `Publish` |
| AssetManagement (Asset) | Internal cross-context | Asset role assignments reference Assets by ID |
| ChangeRequests | Internal cross-context | `MediaItemReviewSaga` drives review-gated publish; MCR linked via `MediaChangeRequestLinked` event |
| DocumentSigning | Internal cross-context | `DocumentSigningSaga` manages checkout lock during signing |
| Registration | Internal cross-context | `RegistrationIds` added via `RegistrationRefAdded` event |
| Search / Discovery | Downstream | `media.mediaitem.published`, `media.mediaitem.archived`, `media.collection.visibility-changed`, `media.folder.created` |
| Billing | Downstream | `media.mediaitem.published`, `media.mediaitem.archived` |
| Notifications | Downstream | `media.mediaitem.published`, `media.collection.created` |

---

## High-Level Event Flows

### Collection Events
```
CollectionCreated → CollectionRenamed / CollectionTagged / CollectionVisibilityChanged
CollectionDefaultProfileSet → CollectionArchived
```

### Folder Events
```
FolderCreated → FolderRenamed / FolderMoved → FolderArchived
```

### MediaItem Events
```
MediaItemCreated → [MediaItemAssignedToFolder]
→ MediaItemTitleUpdated / MediaItemTagged / MediaItemMetadataFieldSet
→ AssetAssignedToRole / AssetUnassignedFromRole
→ MediaItemPublicationRequested (→ PendingApproval) → MediaItemApproved (published) / MediaItemRejected
MediaItemApproved → MediaItemRevertedToDraft (on any write post-publish)
MediaItemApproved → MediaItemWithdrawn / MediaItemArchived
MediaItemCheckedOut → MediaItemCheckedIn / MediaItemCheckoutAbandoned / MediaItemCheckoutForceReleased
```

### MediaProfile Events
```
MediaProfileCreated → [draft mutations: AssetDefinitionAdded, RecordTypeAttachedToProfile, ...]
→ MediaProfilePublished (v1)
→ [CreateMediaProfileRevision → draft mutations → MediaProfilePublished (v2, v3, ...)]
→ MediaProfileDeprecated
```

### Published Integration Events

Published inline by context-specific publisher classes in `Catalog.WriteModel` immediately after the domain event is persisted. All events target the `media-integration-events` SNS topic.

**Collections** — publisher: `CollectionIntegrationEventPublisher`

| C# Record Type | Trigger Domain Event |
|---|---|
| `CollectionCreatedMessage` | `CollectionCreated` |
| `CollectionRenamedMessage` | `CollectionRenamed` |
| `CollectionTaggedMessage` | `CollectionTagged` |
| `CollectionVisibilityChangedMessage` | `CollectionVisibilityChanged` |
| `CollectionArchivedMessage` | `CollectionArchived` |

**Folders** — publisher: `FolderIntegrationEventPublisher`

| C# Record Type | Trigger Domain Event |
|---|---|
| `FolderCreatedMessage` | `FolderCreated` |
| `FolderRenamedMessage` | `FolderRenamed` |
| `FolderMovedMessage` | `FolderMoved` |
| `FolderArchivedMessage` | `FolderArchived` |

**MediaItems** — publisher: `MediaItemIntegrationEventPublisher`

| C# Record Type | Trigger Domain Event | Notes |
|---|---|---|
| `MediaItemCreatedMessage` | `MediaItemCreated` | Enriched with capabilities and `MaxFileSizeBytes` from the published `MediaProfile` |
| `MediaItemAssignedToFolderMessage` | `MediaItemAssignedToFolder` | |
| `MediaItemSubmittedForReviewMessage` | `MediaItemPublicationRequested` | |
| `MediaItemApprovedMessage` | `MediaItemApproved` | |
| `MediaItemRejectedMessage` | `MediaItemRejected` | |
| `MediaItemArchivedMessage` | `MediaItemArchived` | |

**MediaProfiles** — publisher: implicit (registered in `IntegrationEventPublisherRegistrations`)

| C# Record Type | Trigger Domain Event |
|---|---|
| `MediaProfilePublishedMessage` | `MediaProfilePublished` |
| `MediaProfileDeprecatedMessage` | `MediaProfileDeprecated` |

### Consumed Integration Events

Catalog consumes integration events from peer contexts via the `media-cross-module-events` SQS queue.

**From Registration** — consumer: `RegistrationInitiatedConsumer` (`Catalog.WriteModel`)

| Event | Handling |
|---|---|
| `RegistrationInitiatedMessage` | Dispatches `AddRegistrationRefCommand` to append `RegistrationId` to the linked `MediaItem`. Cross-context link established via message bus, no direct aggregate access. |

**From ChangeRequests** — consumers: `ChangeRequest*EventHandler` classes (`Catalog.WriteModel.Infrastructure`)

Maintains the `ChangeRequestReference` write-side reference model (DynamoDB, keyed by `TenantId` + `ChangeRequestId`). Used by `IMediaChangeRequestQueryService.IsApproved` to gate `ApproveMediaItem` when `ReviewPolicy = RequiredForPublish`.

| Event | Consumer | Action |
|---|---|---|
| `ChangeRequestCreatedIntegrationEvent` | `ChangeRequestCreatedEventHandler` | INSERT `ChangeRequestReference` with `Status = Open` |
| `ChangeRequestApprovedIntegrationEvent` | `ChangeRequestApprovedEventHandler` | UPDATE `ChangeRequestReference` status → `Approved` |
| `ChangeRequestRejectedIntegrationEvent` | `ChangeRequestRejectedEventHandler` | UPDATE `ChangeRequestReference` status → `Rejected` |
| `ChangeRequestAbandonedIntegrationEvent` | `ChangeRequestAbandonedEventHandler` | UPDATE `ChangeRequestReference` status → `Abandoned` |

> `ChangeRequestCreatedIntegrationEvent` also fans out to `ChangeRequestCreatedSagaHandler` in the ChangeRequests module (two handlers, same message).

**From Catalog (self — archive fan-out)** — consumer: `CollectionArchiveFanOutJob` (`Catalog.WriteModel`)

| Event | Handling |
|---|---|
| `CollectionArchivedMessage` | Fans out archival of all media-folders and media media-items within the media-collection's subtree. Delegates BFS traversal to `ICollectionArchiveFanOutWorker`; archives media media-items in parallel and media-folders leaf-first. |

---

## Ubiquitous Language

| Term | Meaning |
|---|---|
| Collection | An owner-defined namespace for Folders and MediaItems; controls visibility |
| Folder | A hierarchical container within a Collection; MediaItem membership expressed via `MediaItem.FolderId` |
| MediaItem | The core cataloguing unit — a single catalogued media-item conforming to a MediaProfile |
| MediaProfile | The structural contract for a MediaItem type. Defines asset roles, RecordType schema pins, capabilities, and policies. Published versions are immutable. |
| AssetDefinition | An asset role on a media-profile: `{ RoleName, AcceptedContentTypes, IsRequired, AllowMultiple, MaxFileSizeBytes?, DimensionConstraints? }` |
| Capability | A domain module activator set on a `MediaProfile`. `MediaItem → MediaProfile → Capabilities → Domain Modules`. |
| ReviewPolicy | `None` or `RequiredForPublish` — controls whether `MediaChangeRequest` approval is required before publishing |
| CheckoutPolicy | `None` or `RequiredForEdit` — controls whether checkout is mandatory before writes |
| Unassigned | A MediaItem with no `FolderId` — creation-time-only transient state |
| Version (MediaItem) | Incremented on each `ApproveMediaItem`; 0 until first publish |
| Document Item | A `MediaItem` whose `MediaProfile` lacks the `Processing` capability — quota-exempt, fast-exit after virus scan |

---

## Integration Event Contracts

### Collections

#### `CollectionCreatedMessage`

**Publisher:** `CollectionIntegrationEventPublisher` — triggered by `CollectionCreated`

```csharp
record CollectionCreatedMessage(
    string TenantId,
    string CollectionId,
    string OwnerId,
    string Name,
    string Visibility,    // CollectionVisibility enum value as string: "Private" | "Unlisted" | "Public"
    DateTimeOffset OccurredAt
);
```

#### `CollectionRenamedMessage`

```csharp
record CollectionRenamedMessage(
    string TenantId,
    string CollectionId,
    string OldName,
    string NewName,
    DateTimeOffset OccurredAt
);
```

#### `CollectionTaggedMessage`

```csharp
record CollectionTaggedMessage(
    string TenantId,
    string CollectionId,
    IReadOnlyList<string> Tags,    // Full replacement list, not a delta
    DateTimeOffset OccurredAt
);
```

#### `CollectionVisibilityChangedMessage`

```csharp
record CollectionVisibilityChangedMessage(
    string TenantId,
    string CollectionId,
    string OldVisibility,    // CollectionVisibility enum value as string
    string NewVisibility,    // CollectionVisibility enum value as string
    DateTimeOffset OccurredAt
);
```

#### `CollectionArchivedMessage`

```csharp
record CollectionArchivedMessage(
    string TenantId,
    string CollectionId,
    DateTimeOffset ArchivedAt
);
```

---

### Folders

#### `FolderCreatedMessage`

**Publisher:** `FolderIntegrationEventPublisher` — triggered by `FolderCreated`

```csharp
record FolderCreatedMessage(
    string TenantId,
    string FolderId,
    string OwnerId,
    string CollectionId,
    string? ParentFolderId,    // null = root media-folder in media-collection
    string Name,
    DateTimeOffset OccurredAt
);
```

#### `FolderRenamedMessage`

```csharp
record FolderRenamedMessage(
    string TenantId,
    string FolderId,
    string OldName,
    string NewName,
    DateTimeOffset OccurredAt
);
```

#### `FolderMovedMessage`

```csharp
record FolderMovedMessage(
    string TenantId,
    string FolderId,
    string CollectionId,
    string? OldParentFolderId,    // null = was a root media-folder
    string? NewParentFolderId,    // null = moved to root
    DateTimeOffset OccurredAt
);
```

#### `FolderArchivedMessage`

```csharp
record FolderArchivedMessage(
    string TenantId,
    string FolderId,
    string CollectionId,
    DateTimeOffset ArchivedAt
);
```

---

### MediaItems

#### `MediaItemCreatedMessage`

**Publisher:** `MediaItemIntegrationEventPublisher` — triggered by `MediaItemCreated`

```csharp
record MediaItemCreatedMessage(
    string TenantId,
    string MediaItemId,
    string OwnerId,
    string MediaProfileId,
    string? FolderId,                      // null = unassigned (media-item pool)
    string? CollectionId,                  // null = unassigned
    string Title,
    string? Description,
    IReadOnlyList<string> Capabilities,    // Resolved from published MediaProfile at publish time
    long? MaxFileSizeBytes,                // null = no per-profile ceiling; max across all AssetDefinitions
    DateTimeOffset CreatedAt
);
```

> `Capabilities` and `MaxFileSizeBytes` are enriched from the published `MediaProfile` at event-publish time by calling `IMediaItemProfileQueryService`. Downstream contexts (e.g. AssetManagement) use these fields to gate upload and processing behaviour without querying Catalog.

#### `MediaItemAssignedToFolderMessage`

```csharp
record MediaItemAssignedToFolderMessage(
    string TenantId,
    string MediaItemId,
    string FolderId,
    string CollectionId,
    DateTimeOffset AssignedAt
);
```

#### `MediaItemSubmittedForReviewMessage`

```csharp
record MediaItemSubmittedForReviewMessage(
    string TenantId,
    string MediaItemId,
    string MediaProfileId,
    string? CollectionId,
    string RequestingUserId,
    string? ChangeRequestId,               // null when ReviewPolicy = None
    IReadOnlyList<string> InitialReviewerIds,
    DateTimeOffset SubmittedAt
);
```

> When `ChangeRequestId` is non-null (`ReviewPolicy = RequiredForPublish`), ChangeRequests context consumer creates the `MediaChangeRequest` aggregate using the pre-supplied ID.

#### `MediaItemApprovedMessage`

```csharp
record MediaItemApprovedMessage(
    string TenantId,
    string MediaItemId,
    int VersionNumber,
    string Title,
    DateTimeOffset ApprovedAt
);
```

#### `MediaItemRejectedMessage`

```csharp
record MediaItemRejectedMessage(
    string TenantId,
    string MediaItemId,
    string Reason,
    DateTimeOffset RejectedAt
);
```

#### `MediaItemArchivedMessage`

```csharp
record MediaItemArchivedMessage(
    string TenantId,
    string MediaItemId,
    DateTimeOffset ArchivedAt
);
```

---

### MediaProfiles

#### `MediaProfilePublishedMessage`

```csharp
record MediaProfilePublishedMessage(
    string TenantId,
    string MediaProfileId,
    string Name,
    int Version,
    IReadOnlyList<string> Capabilities,    // e.g. ["Processing", "Review", "Registration"]
    DateTimeOffset PublishedAt
);
```

#### `MediaProfileDeprecatedMessage`

```csharp
record MediaProfileDeprecatedMessage(
    string TenantId,
    string MediaProfileId,
    DateTimeOffset DeprecatedAt
);
```

---

### Consumed

#### `RegistrationInitiatedMessage`

**Source:** Registration context  
**Consumer:** `RegistrationInitiatedConsumer` (`Catalog.WriteModel`)  

Contract — see [Registration Integration Event Contracts](../Registration/context-overview.md#integration-event-contracts).

Behaviour: Dispatches `AddRegistrationRefCommand(TenantId, MediaItemId, RegistrationId, InitiatedAt)` to the Catalog command handler. On failure, logs and discards — does not rethrow (media-registration ref addition is a best-effort cross-context link).

#### `CollectionArchivedMessage`

**Source:** Catalog (self — archive fan-out)  
**Consumer:** `CollectionArchiveFanOutJob` (`Catalog.WriteModel`)  

Behaviour: Calls `ICollectionArchiveFanOutWorker.ArchiveSubtreeAsync(tenantId, collectionId, archivedAt)`. The worker performs a BFS traversal of the media-collection's media-folder hierarchy, archiving media media-items in parallel batches and media-folders leaf-first.

---

## Relat