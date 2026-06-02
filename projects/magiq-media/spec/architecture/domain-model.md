# Domain Model — Media Management

_Last updated: 2026-04-26_

> **Note:** This document is a summary reference for the domain model. The authoritative spec is `specs/media-management-domain-spec.md`, which includes full command tables, validation rules, read models, API endpoints, and business scenarios.

---

## Bounded Context

**Media Management** is responsible for the ingestion, processing, storage, cataloguing, and retrieval of media assets. It does not own user identity or billing — those are external bounded contexts consumed via anti-corruption layers.

---

## Core Domain: Media Asset Lifecycle

```
Upload → Validate → Process → Store → Catalogue → Serve
```

---

## Aggregates

---

### `RecordType`

Defines a reusable metadata schema — a named set of typed field definitions. Referenced by `MediaProfile` to declare what metadata a `MediaItem` must carry. Configuration aggregate; not transactional. Follows the **Draft → Publish** versioning model — structural mutations operate on a draft; `PublishRecordType` creates an immutable version snapshot.

Owner-scoped. Use `OwnerId = "owner_system"` for platform-level types. Query pattern: `OwnerId IN [ownerId, "owner_system"]`.

| Field | Type | Notes |
|---|---|---|
| `RecordTypeId` | `RecordTypeId` | UUID v7-based |
| `Name` | `NonEmptyString` | Unique within owner scope |
| `Description` | `string?` | |
| `OwnerId` | `OwnerId` | Non-nullable |
| `Version` | `int` | Current **published** version number; `0` before first publish; incremented only by `PublishRecordType` |
| `PublishedAt` | `DateTimeOffset?` | Null before first publish |
| `IsDeprecated` | `bool` | No new MediaProfiles may reference a deprecated RecordType |
| `Draft` | `RecordTypeDraft?` | Present when an editing cycle is in progress (`Fields`, `BasedOnVersion?`, `CreatedAt`) |

**Versioning lifecycle:** `CreateRecordType` (opens draft) → field mutations on draft → `PublishRecordType` (immutable snapshot, version++) → `CreateRecordTypeDraft` (open next revision) → repeat.

**Key domain events:** `RecordTypeCreated`, `RecordTypeDraftCreated`, `FieldAddedToRecordType`, `FieldDefinitionUpdated`, `FieldReplacedInRecordType`, `FieldRemovedFromRecordType`, `FieldsReorderedInRecordType`, `RecordTypePublished`, `RecordTypeDraftDiscarded`, `RecordTypeDeprecated`, `RecordTypeRenamed`

---

### `MediaProfile`

Defines the structural contract for a `MediaItem` type — which assets are required/optional, which `RecordType`s supply its metadata schema, and which domain module `Capabilities` are active for all conforming items. MediaItems declare conformance to a MediaProfile at creation. Follows the **Draft → Publish** versioning model — published profiles are immutable; structural mutations operate on a draft revision. **Capabilities defined on the profile activate domain modules for all MediaItems assigned to it — MediaItem itself carries no behavioral role.** The activation chain is: `MediaItem → MediaProfile → Capabilities → Domain Modules`.

Owner-scoped. Use `OwnerId = "owner_system"` for platform-level profiles. Only `Published` profiles can be assigned to MediaItems (regardless of whether a draft revision is in progress).

| Field | Type | Notes |
|---|---|---|
| `MediaProfileId` | `MediaProfileId` | UUID v7-based |
| `Name` | `NonEmptyString` | Unique per owner; reflects published name |
| `Description` | `string?` | |
| `OwnerId` | `OwnerId` | Non-nullable |
| `AssetDefinitions` | `IReadOnlyList<AssetDefinition>` | **Immutable published state** — last published asset roles |
| `RecordTypeRefs` | `IReadOnlyList<RecordTypeVersion>` | **Immutable published state** — last published RecordType attachments |
| `Capabilities` | `IReadOnlyList<Capability>` | **Immutable published state** — domain modules active for all conforming MediaItems. See `Capability` enum in the domain spec. Empty list is valid (lightweight profile with no active modules). |
| `PublishedVersion` | `int` | Current published version; `0` before first publish; incremented only by `PublishMediaProfile` |
| `Status` | `MediaProfileStatus` | `Draft` (never published) \| `Published` \| `Deprecated` |
| `CheckoutPolicy` | `CheckoutPolicy` | **Immutable published state** — `None` \| `RequiredForEdit` |
| `ReviewPolicy` | `ReviewPolicy` | **Immutable published state** — `None` \| `RequiredForPublish` |
| `CreatedAt` | `DateTimeOffset` | |
| `PublishedAt` | `DateTimeOffset?` | Null before first publish |
| `Draft` | `MediaProfileDraft?` | Present when a revision is in progress. Contains the full working set of `AssetDefinitions`, `RecordTypeRefs`, `Capabilities`, policies, name, and description. |

**Versioning lifecycle:** `CreateMediaProfile` (opens initial draft) → mutations on draft → `PublishMediaProfile` (immutable snapshot v1) → `CreateMediaProfileRevision` (open revision draft) → mutations → `PublishMediaProfile` (v2) → ... → `DeprecateMediaProfile`.

**Key domain events:** `MediaProfileCreated`, `MediaProfileDraftCreated`, `AssetDefinitionAdded`, `AssetDefinitionUpdated`, `AssetDefinitionRemoved`, `AssetDefinitionsReordered`, `AssetDefinitionDefaultSet`, `RecordTypeAttachedToProfile`, `RecordTypeVersionPinnedOnProfile`, `RecordTypeDetachedFromProfile`, `ReviewPolicySet`, `CheckoutPolicySet`, `MediaProfileCapabilitiesSet`, `MediaProfilePublished`, `MediaProfileDraftDiscarded`, `MediaProfileDeprecated`

---

### `Collection`

Top-level organisational container. Owned by a single `OwnerId`. Acts as a namespace for Folders and MediaItems. Archiving is read-layer only — no write-side cascade.

| Field | Type | Notes |
|---|---|---|
| `CollectionId` | `CollectionId` | UUID v7-based |
| `OwnerId` | `OwnerId` | Immutable after creation |
| `Name` | `NonEmptyString` | |
| `Description` | `string?` | |
| `Visibility` | `CollectionVisibility` | `Private` \| `Unlisted` \| `Public` |
| `Tags` | `IReadOnlyList<Tag>` | |
| `DefaultMediaProfileId` | `MediaProfileId?` | Applied to MediaItems if no explicit profile given |
| `CreatedAt` | `DateTimeOffset` | |
| `ArchivedAt` | `DateTimeOffset?` | |

**Key domain events:** `CollectionCreated`, `CollectionRenamed`, `CollectionVisibilityChanged`, `CollectionDefaultProfileSet`, `CollectionTagged`, `CollectionArchived`

---

### `Folder`

Hierarchical container within a `Collection`. A Folder belongs to exactly one Collection and has an optional parent Folder. MediaItem membership is expressed via `MediaItem.FolderId` — the Folder aggregate does not hold item or child-folder ID lists.

| Field | Type | Notes |
|---|---|---|
| `FolderId` | `FolderId` | UUID v7-based |
| `CollectionId` | `CollectionId` | Immutable; the owning collection |
| `ParentFolderId` | `FolderId?` | Null = root folder |
| `Name` | `NonEmptyString` | Unique within parent scope |
| `OwnerId` | `OwnerId` | Denormalised from Collection |
| `IsArchived` | `bool` | |
| `Version` | `int` | Event sequence count; used for optimistic concurrency control |
| `CreatedAt` | `DateTimeOffset` | |
| `UpdatedAt` | `DateTimeOffset` | Derived from last applied event |

**Constraints:** Max 10 levels of nesting (enforced by `FolderHierarchyService`). `CollectionId` is immutable — folders cannot move between collections. All mutating commands accept `ExpectedVersion` for optimistic concurrency.

**Key domain events:** `FolderCreated`, `FolderRenamed`, `FolderMoved`, `FolderArchived`

---

### `MediaItem`

The core cataloguing unit. Represents a single catalogued item (e.g., a film, a photograph, a document record) stored within a Folder. Declares conformance to a `MediaProfile`, owns Asset references, carries validated metadata, and tracks its registration lifecycle.

`FolderId` and `CollectionId` are nullable. Unassigned is a **creation-time-only** state — once assigned to a folder the item can only be moved, never returned to unassigned.

| Field | Type | Notes |
|---|---|---|
| `MediaItemId` | `MediaItemId` | UUID v7-based |
| `FolderId` | `FolderId?` | Null when unassigned (creation-time only). Once assigned, always non-null. |
| `CollectionId` | `CollectionId?` | Derived from target Folder at assignment time — never supplied by caller. Updated on cross-collection moves. |
| `OwnerId` | `OwnerId` | |
| `MediaProfileId` | `MediaProfileId` | The profile this item conforms to. Determines active capabilities and therefore which domain modules are enabled for this item. |
| `Title` | `NonEmptyString` | |
| `Status` | `MediaItemStatus` | See lifecycle |
| `Metadata` | `MetadataChangeset` | `Current` (approved) + `Draft?` (pending changes) |
| `Assets` | `IReadOnlyList<MediaAssetReference>` | `{AssetId, RoleName}` pairs |
| `RegistrationIds` | `IReadOnlyList<RegistrationId>` | References to Registration aggregates |
| `Tags` | `IReadOnlyList<Tag>` | |
| `CurrentVersionNumber` | `int` | 0 until first publish; increments on each `ApproveMediaItem` |
| `CheckoutStatus` | `CheckoutStatus` | `Available` \| `CheckedOut` |
| `CheckedOutBy` | `OwnerId?` | |
| `CheckedOutAt` | `DateTimeOffset?` | |
| `ActiveSigningSessionId` | `SigningSessionId?` | Set during active signing session |
| `ActiveMediaChangeRequestId` | `MediaChangeRequestId?` | Set when a `MediaChangeRequest` is open for the current draft |
| `CreatedAt` | `DateTimeOffset` | |
| `PublishedAt` | `DateTimeOffset?` | |
| `ArchivedAt` | `DateTimeOffset?` | |

**Status lifecycle:**
```
Draft → PendingApproval → Published (version N) → Archived
                        → Draft (any reviewer rejects)    → Withdrawn

Draft → Published (immediate, no reviewers)
Published → Withdrawn → Draft
```

**Assignment lifecycle:**
```
Unassigned (FolderId = null)         ← creation-time only
    │
    ▼  AssignMediaItemToFolder        (one-way — cannot return to Unassigned)
Assigned (FolderId set, CollectionId derived)
    │
    ▼  MoveMediaItem
Assigned (new FolderId; CollectionId re-derived — cross-collection permitted)
```

> **Capability model:** `MediaItem` carries no behavioral role field. All domain module activation derives from the `Capabilities` set on its assigned `MediaProfile`. For example: items whose MediaProfile has the `Processing` capability go through the full processing pipeline and count toward storage quota; items whose MediaProfile lacks `Processing` fast-exit after virus scan and are quota-exempt. Items whose MediaProfile has the `Registration` capability may have `Registration` aggregates attached. The activation chain is: `MediaItem → MediaProfile → Capabilities → Domain Modules`.

**Key domain events:** `MediaItemCreated`, `MediaItemAssignedToFolder`, `MediaItemTitleUpdated`, `MediaItemMoved`, `MediaItemMetadataFieldSet`, `MediaItemMetadataBatchSet`, `AssetAssignedToRole`, `AssetUnassignedFromRole`, `MediaItemSubmittedForReview`, `MediaItemApproved`, `MediaItemRejected`, `MediaItemWithdrawn`, `MediaItemArchived`, `MediaItemTagged`, `RegistrationRefAdded`, `MediaItemSigningSessionLinked`, `MediaItemSigningSessionUnlinked`

---

### `Asset`

Represents a single uploaded file. Owns the full ingestion and processing lifecycle. Pipeline behaviour and quota eligibility are determined by the `Capabilities` of the owning MediaItem's `MediaProfile` — specifically whether the `Processing` capability is present — not by a per-asset flag.

`MediaItemId` is nullable — an Asset can be uploaded standalone (e.g., drag-and-drop) before a MediaItem exists.

| Field | Type | Notes |
|---|---|---|
| `AssetId` | `AssetId` | UUID v7-based |
| `MediaItemId` | `MediaItemId?` | Null for standalone upload. Set permanently on `AssignAssetToRole` (raises `AssetAttachedToMediaItem`). Immutable once set. |
| `OwnerId` | `OwnerId` | Denormalised |
| `RoleName` | `RoleName?` | The MediaProfile role this asset fills. Null until `AssignAssetToRole` is called. Null when the owning MediaItem's MediaProfile lacks the `Processing` capability (assets on lightweight profiles are uploaded but not placed into named asset roles). |
| `IsPrimary` | `bool` | For `AllowMultiple = true` roles |
| `Status` | `AssetStatus` | See lifecycle |
| `OriginalFileName` | `FileName` | Sanitised |
| `ContentType` | `MediaContentType` | |
| `StorageKey` | `S3Key` | Immutable after assignment |
| `Renditions` | `IReadOnlyList<Rendition>` | Empty when the owning MediaItem's MediaProfile lacks the `Processing` capability |
| `Metadata` | `AssetMetadata` | Technical file characteristics extracted by the Processing Worker. Fields populated per `ContentType` — dimensions, codec, frame rate, EXIF, archive manifest, etc. Empty (all null / empty collections) when the owning MediaItem's MediaProfile lacks the `Processing` capability. |
| `Tags` | `IReadOnlyList<Tag>` | |
| `CreatedAt` | `DateTimeOffset` | |

**Status lifecycle:**
```
Pending → Validating → ValidationFailed
                     → Processing → ProcessingFailed
                                  → Active → Archived
                                           → Deleted (soft)
```

> When the owning MediaItem's MediaProfile **lacks the `Processing` capability**: Processing Worker fast-exits after virus scan — no renditions generated, no metadata extracted. Asset transitions directly `Validating → Active` on a clean scan.
> When the owning MediaItem's MediaProfile **has the `Processing` capability**: full pipeline runs — renditions generated, metadata/EXIF extracted.
> When `MediaItemId` is null at processing time (standalone upload): Processing Worker defaults to the full processing pipeline.

**Key domain events:** `AssetUploaded`, `AssetUploadConfirmed`, `AssetValidationPassed`, `AssetValidationFailed`, `AssetInfectionDetected`, `AssetProcessingStarted`, `AssetProcessingCompleted`, `AssetProcessingFailed`, `AssetTagged`, `AssetArchived`, `AssetDeleted`, `AssetAttachedToMediaItem`, `AssetDetachedFromMediaItem`

> **Note:** `AssetProcessingStarted` / `AssetProcessingCompleted` / `AssetProcessingFailed` on the Asset aggregate are signalled by the Processing Worker via `StartProcessingJob` / `CompleteProcessingJob` / `FailProcessingJob` commands — the Asset aggregate receives these transitions as a result of the `ProcessingJob` lifecycle completing. See `ProcessingJob` aggregate below.

**S3 path conventions:**

| Purpose | Bucket | Key |
|---|---|---|
| Media originals (owning MediaProfile has `Processing` capability, or unattached) | `media-source` | `{tenantId}/{shard}/{assetId}/original.{ext}` |
| Media renditions | `media-renditions` | `{tenantId}/{shard}/{assetId}/{renditionType}.{ext}` |
| Document assets (owning MediaProfile lacks `Processing` capability) | `media-documents` | `{tenantId}/{shard}/{assetId}/document.{ext}` |

`{shard}` = last 4 hex chars of UUID v7 `AssetId` (no dashes): `assetId.ToString("N")[^4..]` — from random bits 112–127, 65,536 distinct prefixes, no hashing needed.

---

### `ProcessingJob`

Tracks the lifecycle of a single asset processing job — virus scan, rendition generation, and metadata extraction. Only created for assets whose owning MediaItem's `MediaProfile` has the `Processing` capability. Assets on profiles without `Processing` are virus-scanned only via the fast-exit path (no `ProcessingJob` aggregate is created for them).

Created by `AssetUploadEventHandler` in the Integration Event Consumers Lambda when an `AssetUploadConfirmed` integration event is received. Executed by the Processing Lambda.

| Field | Type | Notes |
|---|---|---|
| `ProcessingJobId` | `ProcessingJobId` | UUID v7-based |
| `AssetId` | `AssetId` | The asset being processed |
| `TenantId` | `TenantId` | Multi-tenancy boundary |
| `Status` | `ProcessingJobStatus` | See lifecycle |
| `StorageKey` | `string` | S3 key of the original asset; immutable after creation |
| `ContentType` | `string` | MIME content type; immutable after creation |
| `Renditions` | `IReadOnlyList<RenditionResult>` | Populated on success |
| `Metadata` | `ExtractedMetadata?` | Technical metadata extracted by Processing Worker; null until succeeded |
| `FailureReason` | `string?` | Set on failure |
| `CompletedAt` | `DateTimeOffset?` | Set on success or failure |

**Status lifecycle:**
```
Queued → Running → Succeeded
                 → Failed
```

**Key domain events:** `ProcessingJobCreated`, `ProcessingJobStarted`, `ProcessingJobSucceeded`, `ProcessingJobFailed`

---

### `Registration`

Tracks the formal registration lifecycle of a `MediaItem` — electronic (e.g., digital copyright filing) or physical (e.g., paper submission). A MediaItem may have multiple Registrations of different types.

| Field | Type | Notes |
|---|---|---|
| `RegistrationId` | `RegistrationId` | UUID v7-based |
| `MediaItemId` | `MediaItemId` | The item being registered |
| `OwnerId` | `OwnerId` | |
| `RegistrationType` | `RegistrationType` | `Electronic` \| `Physical` |
| `RegistrationAuthority` | `string` | Free text; trimmed and title-cased on write; indexed as keyword in OpenSearch |
| `Status` | `RegistrationStatus` | See lifecycle |
| `Reference` | `RegistrationReference?` | External reference number (filled on confirmation) |
| `SubmittedAt` | `DateTimeOffset?` | |
| `ConfirmedAt` | `DateTimeOffset?` | |
| `ExpiresAt` | `DateTimeOffset?` | |
| `Notes` | `string?` | |
| `Items` | `IReadOnlyList<RegistrationItem>` | MediaItems attached to the registration (the primary item plus any supporting document items). Each `RegistrationItem` carries `{ MediaItemId, ItemType, AddedViaAmendmentId? }`. |
| `Amendments` | `IReadOnlyList<RegistrationAmendment>` | Amendment requests raised after the registration has been submitted. Each `RegistrationAmendment` carries `{ AmendmentId, RequestedBy, ItemType, Notes?, Status, RequestedAt, ResolvedAt? }`. |

**Status lifecycle:**
```
Initiated → Submitted → PendingConfirmation → Confirmed
                      ↑                    → Rejected → Resubmitted → ...
                      │
                      └── RegistrationSubmissionRecorded  (records dispatch/reference details without state change)
          → Cancelled
```

**Amendment workflow:** A `RegistrationAmendmentRequested` event opens an amendment on a submitted or confirmed registration. It is resolved by `RegistrationAmendmentApproved` or `RegistrationAmendmentRejected`. An approved amendment may attach additional items via `RegistrationItemAttached`.

**Key domain events:** `RegistrationInitiated`, `RegistrationSubmitted`, `RegistrationSubmissionRecorded`, `RegistrationConfirmed`, `RegistrationRejected`, `RegistrationResubmitted`, `RegistrationCancelled`, `RegistrationItemAttached`, `RegistrationAmendmentRequested`, `RegistrationAmendmentApproved`, `RegistrationAmendmentRejected`, `RegistrationExpiryRecorded`

> **Spec delta:** `RegistrationDocumentAttached` (old spec) has been replaced by `RegistrationItemAttached`, which uses `RegistrationItemType` to classify the attachment. `RegistrationSubmissionRecorded`, `RegistrationAmendmentRequested`, `RegistrationAmendmentApproved`, and `RegistrationAmendmentRejected` are new events present in code but absent from the previous spec. The `Documents` field has been replaced by `Items` to reflect the generalised `RegistrationItem` model.

---

### `MediaChangeRequest`

Owns the comment thread for a single review cycle of a `MediaItem`. Created by `Publish` when reviewers are assigned. Tracks assigned reviewers, their decisions, and threaded comments.

| Field | Type | Notes |
|---|---|---|
| `MediaChangeRequestId` | `MediaChangeRequestId` | UUID v7-based |
| `MediaItemId` | `MediaItemId` | The item under review |
| `OwnerId` | `OwnerId` | The MediaItem owner who initiated the review |
| `Status` | `MediaChangeRequestStatus` | `Open` \| `Approved` \| `Rejected` \| `Abandoned` |
| `Reviewers` | `IReadOnlyList<Reviewer>` | Assigned reviewers with decision state |
| `Comments` | `IReadOnlyList<ReviewComment>` | Threaded conversation |
| `CreatedAt` | `DateTimeOffset` | |
| `ResolvedAt` | `DateTimeOffset?` | |

**Status lifecycle:**
```
Open → Approved   (all non-withdrawn reviewers approved; ≥1 approval)
     → Rejected   (any reviewer rejects; immediate)
     → Abandoned  (MediaItem archived or withdrawn while review is open)
```

Auto-resolution: on `Approved`, command handler issues `ApproveMediaItem` on the linked `MediaItem`. On `Rejected`, issues `RejectMediaItem`. `Abandoned` is raised when the owning `MediaItem` is archived or withdrawn — the open change request is forcibly closed without a reviewer decision.

**Key domain events:** `ChangeRequestCreated`, `ReviewerAssigned`, `ReviewerRemoved`, `ReviewApproved`, `ReviewRejected`, `ReviewerWithdrawn`, `ChangeRequestApproved`, `ChangeRequestRejected`, `ChangeRequestAbandoned`, `ReviewCommentAdded`, `ReviewCommentEdited`, `ReviewCommentDeleted`

> **Spec delta:** `ChangeRequestAbandoned` is a new event present in code but absent from the previous spec. `MediaChangeRequestCreated` / `MediaChangeRequestApproved` / `MediaChangeRequestRejected` were renamed to `ChangeRequestCreated` / `ChangeRequestApproved` / `ChangeRequestRejected` — the domain event class names dropped the `Media` prefix.

---

### `DocumentSigningSession` ⚠️ *Partially implemented*

> **Implementation status:** Domain events and aggregate are fully defined. The `DocumentSigning.WriteModel` has no command handlers — command stubs and integration event folders exist but are empty. `SigningSessionSummaryProjector` is registered as a `// todo:` placeholder. The `DocumentSigningSaga` is absent from `SagaRegistrations`. The `SigningSessionDetailProjector` is implemented. Write-side commands and the saga remain planned/deferred.

Owns the full lifecycle of a SecuredSigning envelope for a single `MediaItem` checkout. Isolated from `MediaItem` to keep SecuredSigning-specific state (envelope ID, signer list, webhook events) out of the core domain aggregate.

| Field | Type | Notes |
|---|---|---|
| `SigningSessionId` | `SigningSessionId` | UUID v7-based |
| `MediaItemId` | `MediaItemId` | The item being signed |
| `OwnerId` | `OwnerId` | |
| `InitiatedBy` | `OwnerId` | The user who initiated signing |
| `Status` | `SigningSessionStatus` | See lifecycle |
| `EnvelopeId` | `string?` | SecuredSigning envelope ID; set after creation |
| `Signers` | `IReadOnlyList<Signer>` | |
| `SignedAssetId` | `AssetId?` | Asset produced on signing completion |
| `InitiatedAt` | `DateTimeOffset` | |
| `CompletedAt` | `DateTimeOffset?` | |
| `VoidedAt` | `DateTimeOffset?` | |
| `VoidReason` | `string?` | |

**Status lifecycle:**
```
Initiated → EnvelopeCreated → Sent → Completed
                                   → Voided
          → Cancelled
          → TimedOut
```

**Key domain events:** `SigningSessionInitiated`, `SigningEnvelopeCreated`, `SigningEnvelopeSent`, `SignerCompleted`, `SigningCompleted`, `SignedAssetRecorded`, `SigningEnvelopeVoided`, `SigningSessionCancelled`, `SigningSessionTimedOut`

> **Spec delta:** `SigningSessionTimedOut` is a new event present in code but absent from the previous spec. The `TimedOut` terminal state is raised by the `SagaTimeoutScanner` — however, `DocumentSigningTimeoutScanner` does not exist yet (only `AssetIngestionTimeoutScanner` is implemented).

---

## Value Objects

| Value Object | Description |
|---|---|
| `AssetId` | UUID v7 string, immutable |
| `MediaItemId` | UUID v7 string, immutable |
| `CollectionId` | UUID v7 string, immutable |
| `FolderId` | UUID v7 string, immutable |
| `RegistrationId` | UUID v7 string, immutable |
| `RecordTypeId` | UUID v7 string, immutable |
| `MediaProfileId` | UUID v7 string, immutable |
| `MediaChangeRequestId` | UUID v7 string, immutable |
| `SigningSessionId` | UUID v7 string, immutable |
| `ProcessingJobId` | UUID v7 string, immutable |
| `AmendmentId` | UUID v7 string, immutable — identifies a `RegistrationAmendment` within a `Registration` |
| `TenantId` | string, immutable tenant identifier sourced exclusively from JWT `tenant_id` claim via `IExecutionContext`. Never derived from `OwnerId`. Never stored as `OwnerId`. Prefixes all DynamoDB PKs (`TENANT#{TenantId}#...`), S3 keys, and event store externalized payload paths. |
| `OwnerId` | string, equals `context.Actor.Id` at resource creation time. Not a JWT claim. `"owner_system"` reserved for platform-level config aggregates. |
| `S3Key` | bucket + key pair, immutable |
| `FileName` | sanitised original name |
| `MediaContentType` | strongly typed (`Image` \| `Video` \| `Audio` \| `Document` \| `Archive`) |
| `Tag` | normalised lowercase string, max 64 chars |
| `RoleName` | normalised kebab-case string, max 64 chars — identifies a MediaProfile asset role |
| `Rendition` | `{ RenditionType, StorageKey, ContentType, Width?, Height?, SizeBytes }` — `Width`/`Height` set for Image and Video renditions only |
| `StorageTier` | `Standard` \| `StandardIA` \| `GlacierInstant` \| `DeepArchive` — used by `Asset.StorageTier` (last-confirmed S3 storage class) and `AssetDefinition.PreferredStorageTier`. `Glacier` is a legacy alias retained for event-store backward compatibility. |
| `AssetMetadata` | Expanded per-content-type shape. Common: `Format?`. Image+Video: `Width?`, `Height?`. Image: `DpiX?`, `DpiY?`, `ColorSpace?`, `BitDepth?`. Video+Audio: `DurationSeconds?`, `AudioCodec?`, `AudioBitRate?`, `AudioSampleRate?`, `AudioChannels?`. Video: `FrameRate?`, `VideoBitRate?`, `VideoCodec?`. Document: `PageCount?`. Archive: `Archive: ArchiveMetadata?`. Image only: `ExifData` (empty dict otherwise, never null). Write-once — stamped by `CompleteAssetProcessing`. All fields are null / empty when the owning MediaItem's MediaProfile lacks the `Processing` capability. |
| `ArchiveMetadata` | Nested within `AssetMetadata.Archive`. `{ CompressionFormat, FileCount, UncompressedSizeBytes, CompressionRatio?, ContainedFileTypes, IsPasswordProtected }` — populated only when `Asset.ContentType = Archive`. |
| `MediaAssetReference` | `{ AssetId, RoleName }` — collocates role info on `MediaItem.Assets` |
| `MetadataChangeset` | `{ Current: IReadOnlyDictionary<string, MetadataValue>, Draft?: IReadOnlyDictionary<string, MetadataValue> }` |
| `FieldDefinition` | `{ FieldName, DisplayName, Description?, FieldType, Order, IsRequired, IsImmutable, IsSearchable, constraints... }` |
| `RecordTypeVersion` | `{ RecordTypeId, Version }` — pinned reference to a specific schema version |
| `AssetDefinition` | `{ RoleName, DisplayName, AcceptedContentTypes, IsRequired, MaxFileSizeBytes?, AllowMultiple, DisplayOrder, DefaultAssetId?, DimensionConstraints?, PreferredStorageTier }` |
| `DimensionConstraints` | `{ MinWidth?, MaxWidth?, MinHeight?, MaxHeight?, MinDurationSeconds?, MaxDurationSeconds? }` |
| `RegistrationItem` | `{ MediaItemId, ItemType: RegistrationItemType, AddedViaAmendmentId? }` — a MediaItem attached to a Registration. `RegistrationItemType` classifies the attachment (primary subject, supporting document, etc.). Replaces the old `RegistrationDocument` shape. |
| `RegistrationAmendment` | `{ AmendmentId, RequestedBy: OwnerId, ItemType: RegistrationItemType, Notes?, Status: AmendmentStatus, RequestedAt, ResolvedAt? }` — an amendment request on a submitted or confirmed Registration. |
| `RegistrationReference` | External reference number from registration authority |
| `Reviewer` | `{ ReviewerId, AssignedAt, Status, DecidedAt?, DecisionComment? }` |
| `ReviewComment` | `{ CommentId, AuthorId, Body, ParentCommentId?, CreatedAt, EditedAt?, IsDeleted }` |
| `Signer` | `{ SignerId, Name, Email, RoutingOrder, SignedAt? }` |

---

## Domain Services

| Service | Responsibility |
|---|---|
| `AssetValidator` | Coordinates format check, size limit enforcement, virus scan result interpretation |
| `RenditionFactory` | Determines which rendition profiles apply to a given `MediaContentType`. Returns an empty list for `Document` and `Archive` content types (no renditions generated). Not invoked at all when the owning MediaItem's MediaProfile lacks the `Processing` capability. |
| `StorageKeyGenerator` | Deterministic S3 key from `TenantId` + `AssetId`. Signature: `Generate(TenantId, AssetId, MediaContentType, FileName) → S3Key`. Computes `{shard}` = `assetId.ToString("N")[^4..]`. Key is stamped onto `AssetUploaded` event and is immutable thereafter. `TenantId` sourced from `IExecutionContext` by the command handler — never from `OwnerId`. `OwnerId` is deliberately excluded from S3 keys because ownership is mutable; keys must remain stable across ownership transfers. |
| `MetadataValidator` | Validates metadata field values against pinned `RecordTypeVersion` schemas on `SetMetadataField` and `Publish` |
| `FolderHierarchyService` | Enforces 10-level depth limit on `CreateFolder` / `MoveFolder`; detects circular parent chains |
| `FolderDomainService` | Queries `media-items` read model to check folder emptiness before `ArchiveFolder` (eventually consistent) |

---

## Supporting Domains

| Context | Relationship | Integration |
|---|---|---|
| Identity | Upstream | JWT validated at API Gateway; `IdentityAcl` resolves `IActor` from claims. `OwnerId` on resources is stamped from `Actor.Id` at creation — not a JWT claim. No direct DB call to Identity at runtime. `"owner_system"` reserved for platform-level config aggregates. |
| Billing / Quotas | Upstream | Storage usage events published; quota check via ACL before issuing upload URL. Items whose MediaProfile lacks the `Processing` capability are quota-exempt — the Billing ACL resolves capability state via the `media-items` read model. |
| Search / Discovery | Downstream | OpenSearch projector consumes domain events; `media-items` and `media-registrations` indexes maintained. |
| Notifications | Downstream | Processing completion, failure, and registration events trigger user alerts via SQS fan-out. |
| SecuredSigning | External (via adapter) | `DocumentSigningSession` aggregate drives signing lifecycle. Digital Signing Adapter Lambda handles API calls and webhook ingestion. |

---

## Ubiquitous Language

| Term | Meaning |
|---|---|
| Asset | A single uploaded file and all its derived representations |
| MediaItem | The core cataloguing unit — a single catalogued item conforming to a MediaProfile |
| Rendition | A processed derivative of the original (thumbnail, compressed, transcoded) |
| Ingestion | The full pipeline from upload receipt to Active status |
| Projection | A read model built from the event stream |
| Collection | An owner-defined namespace for Folders and MediaItems; controls visibility |
| Folder | A hierarchical container within a Collection; item membership expressed via `MediaItem.FolderId` |
| Processing | The async pipeline that generates renditions and extracts metadata |
| MediaProfile | The structural contract for a MediaItem type — asset roles, metadata schemas, and active capabilities |
| Capability | A domain module switch set on a `MediaProfile`. Capabilities activate domain modules (`Processing`, `Registration`, `Review`, `CheckInOut`, `VersionControl`, `Retention`, `Distribution`, `Governance`) for all MediaItems conforming to that profile. `MediaItem` itself never stores capabilities. |
| RecordType | A reusable metadata schema; a named set of typed field definitions |
| Registration | The formal registration lifecycle of a MediaItem (electronic or physical) |
| MediaChangeRequest | The review lifecycle for a single draft cycle; owns reviewer assignments and decisions |
| DocumentSigningSession | The SecuredSigning envelope lifecycle for a MediaItem checkout |
| Unassigned | A MediaItem with no FolderId — creation-time-only transient state |
| Document item | A `MediaItem` whose `MediaProfile` lacks the `Processing` capability — quota-exempt, fast-exits after virus scan, stored in `media-documents`, typically used as a supporting registration document |
| CheckoutPolicy | `None` or `RequiredForEdit` — controls whether checkout is mandatory before writes |
| ReviewPolicy | `None` or `RequiredForPublish` — controls whether a `MediaChangeRequest` approval is required before publishing |
| Shard | Last 4 hex chars of a UUID v7 AssetId — used as S3 key prefix for partition distribution |
| TenantId | The immutable identifier for the tenant (organisation) that owns the deployment scope. Prefixes all DynamoDB PKs, S3 keys, and event store externalized payload paths. Distinct from `OwnerId` — `OwnerId` identifies a specific owner within a tenant; `TenantId` identifies the tenant boundary itself. |
