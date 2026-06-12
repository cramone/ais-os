# Asset — Write Model

_Context: `AssetManagement`_
_Aggregate: `Asset`_
_Stream prefix: `asset_`_

---

## Purpose

Represents a single uploaded file. Owns the full ingestion and processing lifecycle from pre-signed URL issuance through validation, processing, and final storage. Pipeline behaviour and quota eligibility are determined by the `Capabilities` of the owning `MediaItem`'s `MediaProfile` — specifically whether the `Processing` capability is present — not by any per-asset flag.

`MediaItemId` is nullable — an Asset can be uploaded standalone (drag-and-drop) before a `MediaItem` exists.

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| Status must be `Pending` | `AssetNotPending` | `ConfirmAssetUpload` |
| Status must be `Validating` | `AssetNotValidating` | `RecordValidationResult` |
| Status must be `Validating` or `Processing` | varies by `FailureCategory` | `FailAssetProcessing` |
| Status must be `Active` | `AssetNotActive` | `TagAsset`, `AssignAssetToRole` |
| Status must be `Active` or `ProcessingFailed` | `InvalidOperation` | `ArchiveAsset` |
| Status must be `Active`, `Archived`, `ValidationFailed`, or `ProcessingFailed` | `InvalidOperation` | `DeleteAsset` |
| Status must not be `VersionArtifact` | `InvalidOperation` | `DeleteAsset` — version artifacts cannot be deleted; use `PurgeVersion` on the owning MediaItem |
| Asset must not be assigned to a MediaItem role (`IsAssigned() = false`) unless status is `ValidationFailed` or `ProcessingFailed` | `InvalidOperation` | `DeleteAsset` — assigned assets are locked to the MediaItem lifecycle; unassign first or manage deletion through the MediaItem |
| Asset must not be set as `DefaultAssetId` on any `AssetDefinition` in a published `MediaProfile` (cross-context guard via `AssetProfileDefaultReference`) | `InvalidOperation` | `DeleteAsset` |
| `MediaItemId` must be null | `AssetAlreadyAttached` | `AttachAssetToMediaItem` (implicit via `AssignAssetToRole`) |
| `StorageKey` is immutable after `AssetUploadInitiated` | — | Structural invariant |

---

## Properties

| Property | Type | Notes |
|---|---|---|
| `AssetId` | `AssetId` | UUID v7-based. Caller-generated for idempotent upload initiation. |
| `TenantId` | `TenantId` | Set from creation event (first field). Immutable. |
| `MediaItemId` | `MediaItemId?` | Null for standalone upload. Set permanently on `AttachAssetToMediaItem`. Immutable once set. |
| `OwnerId` | `OwnerId` | Denormalised. |
| `RoleName` | `RoleName?` | The MediaProfile role this asset fills. Null until `AssignAssetToRole`. |
| `IsPrimary` | `bool` | For `AllowMultiple = true` roles. |
| `Status` | `AssetStatus` | See lifecycle below. |
| `UploadMode` | `UploadMode` | `SinglePart` (default) or `Multipart`. Set on creation; immutable. |
| `MultipartUploadId` | `string?` | S3 multipart `UploadId`. Non-null only when `UploadMode = Multipart`. Set on `AssetMultipartUploadInitiated`. |
| `OriginalFileName` | `FileName` | Sanitised at command time. |
| `ContentType` | `MediaContentType` | `Image` \| `Video` \| `Audio` \| `Document` \| `Archive` |
| `StorageKey` | `S3Key` | Immutable after creation event. Stamped by `StorageKeyGenerator`. |
| `StorageTier` | `StorageTier` | `Standard` at upload time. Not changed by `ArchiveAsset` — S3 storage class transitions are managed by AWS lifecycle policy on object creation date and are asynchronous. Updated only by `RecordStorageTierTransition` (system-only), dispatched when the storage tier scanner or S3 event notification confirms the actual transition has occurred. Reflects the last observed S3 storage class, not a speculative post-archive value. |
| `Renditions` | `IReadOnlyList<Rendition>` | Empty when `Processing` capability absent. |
| `Metadata` | `AssetMetadata` | Write-once; stamped by `CompleteAssetProcessing`. All null when `Processing` capability absent. |
| `Tags` | `IReadOnlyList<Tag>` | |
| `CreatedAt` | `DateTimeOffset` | |

---

## Status Lifecycle

```
Pending (SinglePart)  → (ConfirmAssetUpload)          → Validating
Pending (Multipart)   → (CompleteMultipartUpload)      → Validating
Pending (Multipart)   → (AbortMultipartUpload)         → MultipartAborted  [terminal]
Validating    → (RecordValidationResult: Pass)    → Validating (status unchanged; triggers pipeline branch)
Validating    → (RecordValidationResult: Fail)    → ValidationFailed
Validating    → (RecordValidationResult: Virus)   → ContainsVirus  [terminal]
Validating    → (ActivateDocumentAsset)           → Active  [document fast-exit; no Processing capability]
Validating    → (StartAssetProcessing)            → Processing  [capable asset; triggered by ProcessingJobStarted]
Processing    → (CompleteAssetProcessing)          → Active
Processing    → (FailAssetProcessing)              → ProcessingFailed
Active        → (ArchiveAsset)                    → Archived
ProcessingFailed → (ArchiveAsset)                 → Archived
Active        → (PromoteToVersionArtifact)        → VersionArtifact
Archived      → (PromoteToVersionArtifact)        → VersionArtifact
VersionArtifact → (ArchiveAsset)                  → ❌ BLOCKED — VersionArtifact lifecycle is managed by the owning MediaItem version
VersionArtifact → (ReleaseVersionArtifact)        → Active | Archived  [restores pre-promotion status]
Active        → (DeleteAsset)                     → Deleted  [soft; unassigned only]
Archived      → (DeleteAsset)                     → Deleted  [soft; unassigned only]
ValidationFailed → (DeleteAsset)                  → Deleted  [soft; always deletable — cleanup]
ProcessingFailed → (DeleteAsset)                  → Deleted  [soft; always deletable — cleanup]
VersionArtifact → (DeleteAsset)                   → ❌ BLOCKED — use PurgeVersion on owning MediaItem
Active (assigned) → (DeleteAsset)                 → ❌ BLOCKED — unassign from role before deleting
Archived (assigned) → (DeleteAsset)               → ❌ BLOCKED — unassign from role before deleting
```

**Pipeline branching (determined by `AssetIngestionSaga` at `AssetValidationPassed`, with `AssetProcessingWorker` as defensive fallback):**

- `MediaItemId` null (standalone) or MediaProfile **lacks `Processing` capability** → **document fast-exit**:
  `AssetIngestionSaga` dispatches `BypassProcessingJobCommand` → `ProcessingJobBypassed` integration event → `ActivateDocumentAssetCommand` → `Validating → Active`; `ProcessingStatus = Validated`, empty `Renditions`, `AssetMetadata.Empty()`.

- `MediaItemId` present + MediaProfile **has `Processing` capability** → **full pipeline**:
  `AssetIngestionSaga` dispatches `StartProcessingJobCommand` → `ProcessingJobStarted` integration event → `StartAssetProcessingCommand` → `Validating → Processing` → pipeline worker → `CompleteAssetProcessingCommand` → `Processing → Active`; `ProcessingStatus = Transcoded`.

---

## Value Objects

| Value Object | Description |
|---|---|
| `AssetId` | UUID v7 string, immutable |
| `FileName` | Sanitised original filename; trimmed; non-empty |
| `S3Key` | Bucket + key pair; immutable after assignment |
| `MediaContentType` | `Image` \| `Video` \| `Audio` \| `Document` \| `Archive` |
| `RoleName` | Normalised kebab-case string, max 64 chars |
| `Rendition` | `{ RenditionType, StorageKey, ContentType, Width?, Height?, SizeBytes }` |
| `AssetMetadata` | Write-once technical characteristics (format, dimensions, duration, EXIF, etc.) |
| `ArchiveMetadata` | Nested in `AssetMetadata.Archive` — populated only for `Archive` content type |
| `Tag` | Normalised lowercase string, max 64 chars |
| `AssetStatus` | `Pending \| Validating \| ValidationFailed \| ContainsVirus \| Processing \| ProcessingFailed \| Active \| Archived \| Deleted \| MultipartAborted \| VersionArtifact` |
| `UploadMode` | `SinglePart \| Multipart` — set at creation; immutable. Determines which completion path is valid. |
| `StorageTier` | `Standard \| StandardIA \| GlacierInstant \| DeepArchive` (`Glacier` is a legacy alias for `GlacierInstant`) |
| `ProcessingStatus` | `Validated` (virus scan only) \| `Transcoded` (full pipeline) — carried on `AssetProcessingCompleted` |
| `FailureCategory` | `ValidationError \| UploadExpired \| ValidationTimeout \| ProcessingTimeout \| ProcessingError` |

**`AssetMetadata` shape:**

| Field | Applies To |
|---|---|
| `Format?` | All |
| `Width?`, `Height?` | Image, Video |
| `DpiX?`, `DpiY?`, `ColorSpace?`, `BitDepth?` | Image only |
| `DurationSeconds?`, `AudioCodec?`, `AudioBitRate?`, `AudioSampleRate?`, `AudioChannels?` | Video, Audio |
| `FrameRate?`, `VideoBitRate?`, `VideoCodec?` | Video only |
| `PageCount?` | Document only |
| `Archive?` (`ArchiveMetadata`) | Archive only |
| `ExifData` | Image only (never null; empty dict for non-image) |

**S3 key patterns (from `StorageKeyGenerator`):**

| Condition | Bucket | Key |
|---|---|---|
| MediaProfile has `Processing`, or unattached | `media-source` | `{tenantId}/{shard}/{assetId}/original.{ext}` |
| Rendition | `media-renditions` | `{tenantId}/{shard}/{assetId}/{renditionType}.{ext}` |
| MediaProfile lacks `Processing` | `media-documents` | `{tenantId}/{shard}/{assetId}/document.{ext}` |

`{shard}` = `assetId.ToString("N")[^4..]`

---

## Methods (Commands)

| Method | Description | Preconditions |
|---|---|---|
| `Asset.InitiateUpload(tenantId, assetId, ownerId, mediaItemId?, fileName, contentType, sizeBytes, storageKey)` | Factory. Raises `AssetUploadInitiated`. `UploadMode = SinglePart`. | — |
| `Asset.InitiateMultipartUpload(tenantId, assetId, ownerId, mediaItemId?, fileName, contentType, sizeBytes, storageKey, multipartUploadId)` | Factory. Raises `AssetMultipartUploadInitiated`. `UploadMode = Multipart`. | — |
| `ConfirmUpload()` | Confirms S3 upload; transitions to Validating. Raises `AssetUploadConfirmed`. Rejected if `UploadMode = Multipart` — use `CompleteMultipartUpload` instead. | `Status = Pending`, `UploadMode = SinglePart` |
| `AbortMultipartUpload()` | Aborts a pending multipart upload. Raises `AssetMultipartUploadAborted`. Terminal. | `Status = Pending`, `UploadMode = Multipart` |
| `RecordValidationResult(outcome, jobId, hasProcessingCapability, reason?)` | Records virus scan / format check result. Raises `AssetValidationPassed` (includes `HasProcessingCapability` flag), `AssetValidationFailed`, or `AssetInfectionDetected`. | `Status = Validating` |
| `StartProcessing()` | Marks pipeline start. Raises `AssetProcessingStarted`. | `Status = Validating` (post-validation pass) |
| `CompleteProcessing(renditions, metadata, processingStatus)` | Stamps renditions + metadata. Raises `AssetProcessingCompleted`. | `Status = Processing` |
| `FailProcessing(category, reason)` | Records failure with category. Raises `AssetProcessingFailed`. | `Status = Validating` or `Processing` (category-dependent) |
| `Tag(tags)` | Full tag list replacement. Raises `AssetTagged`. | `Status = Active` |
| `Archive()` | Soft-archive. Raises `AssetArchived` only. Does not emit `AssetStorageTierTransitioned` — S3 storage class transitions are asynchronous, managed by AWS lifecycle policy on the object's creation date, and recorded separately via `RecordStorageTierTransition` when the actual transition is confirmed. | `Status = Active` or `ProcessingFailed`. Blocked for `VersionArtifact` — lifecycle managed by the owning MediaItem version. |
| `RecordStorageTierTransition(newTier, transitionedAt)` | System-only. Records a storage-class change initiated by AWS Lifecycle Policy. Raises `AssetStorageTierTransitioned`. No-op if `StorageTier == newTier`. | — |
| `Delete()` | Soft-delete. Raises `AssetDeleted`. | `Status ∈ {Active, Archived, ValidationFailed, ProcessingFailed}`. Blocked if `Status = VersionArtifact`. Blocked if `IsAssigned()` unless status is `ValidationFailed` or `ProcessingFailed` (failed assets can never be assigned). |
| `PromoteToVersionArtifact(mediaItemId, versionNumber, occurredAt)` | Marks the asset as a version artifact — snapshotted in an approved MediaItem version. Prevents deletion while the version exists. Raises `AssetPromotedToVersionArtifact`. Captures `_preVersionArtifactStatus` (rebuilt from event replay) before overwriting `Status`. | `Status = Active` or `Archived` |
| `ReleaseVersionArtifact(mediaItemId, versionNumber, releasedAt)` | Releases the asset from `VersionArtifact` protection back to its pre-promotion status (`Active` or `Archived`). Called when the owning MediaItem version is purged. Raises `AssetVersionArtifactReleased`. Guard: `Status == VersionArtifact`. | `Status = VersionArtifact` |
| `AttachToMediaItem(mediaItemId, roleName)` | Permanently binds asset to MediaItem. Raises `AssetAttachedToMediaItem`. | `MediaItemId = null`, `Status = Active` |
| `DetachFromMediaItem(mediaItemId)` | Detaches asset from MediaItem reference. Raises `AssetDetachedFromMediaItem`. | `MediaItemId` matches |

---

## Domain Events

| Event | Key Payload Fields | Status Transition |
|---|---|---|
| `AssetUploadInitiated` | `TenantId`†, `AssetId`, `OwnerId`, `MediaItemId?`, `OriginalFileName`, `ContentType`, `StorageKey`, `BucketName`, `StorageTier`, `Status`, `SizeBytes`, `UploadedAt` | → Pending (`UploadMode = SinglePart`) |
| `AssetMultipartUploadInitiated` | `TenantId`†, `AssetId`, `MediaItemId?`, `OwnerId`, `StorageKey`, `ContentType`, `OriginalFileName`, `SizeBytes`, `MultipartUploadId` | → Pending (`UploadMode = Multipart`) |
| `AssetUploadConfirmed` | `TenantId`, `AssetId`, `OwnerId`, `OriginalFileName`, `ContentType`, `StorageKey`, `BucketName`, `StorageTier`, `Status`, `SizeBytes`, `ConfirmedAt` | Pending → Validating |
| `AssetMultipartUploadAborted` | `AssetId`, `MultipartUploadId`, `AbortedAt` | Pending → MultipartAborted [terminal] |
| `AssetValidationPassed` | `AssetId`, `MediaItemId?`, `JobId`, `StorageKey`, `ContentType`, `HasProcessingCapability`, `PassedAt` | Validating → (Processing or Active) |
| `AssetValidationFailed` | `AssetId`, `Reason` | Validating → ValidationFailed |
| `AssetInfectionDetected` | `AssetId`, `OwnerId`, `MediaItemId?`, `OccurredAt` | Validating → ContainsVirus [terminal]. Emitted by `RecordValidationResult(VirusDetected)`. Handler **must** hard-delete the S3 object before appending this event. |
| `AssetProcessingStarted` | `AssetId` | → Processing |
| `AssetProcessingCompleted` | `AssetId`, `Renditions[]`, `Metadata`, `ProcessingStatus` | Processing → Active |
| `AssetProcessingFailed` | `AssetId`, `FailureCategory`, `Reason` | Processing/Validating → ProcessingFailed |
| `AssetTagged` | `AssetId`, `Tags[]` | — |
| `AssetArchived` | `AssetId`, `ArchivedAt` | Active → Archived |
| `AssetStorageTierTransitioned` | `AssetId`, `OldTier`, `NewTier`, `OccurredAt` | StorageTier updated. Emitted only by `RecordStorageTierTransition` (system-only command). Not emitted by `ArchiveAsset` — S3 storage class transitions are asynchronous and driven by AWS lifecycle policy (Standard → StandardIA → GlacierInstant → DeepArchive) based on object creation date. |
| `AssetDeleted` | `AssetId`, `DeletedAt` | → Deleted |
| `AssetPromotedToVersionArtifact` | `TenantId`†, `AssetId`, `MediaItemId`, `VersionNumber`, `PromotedAt` | Active/Archived → VersionArtifact. Raised by `PromoteToVersionArtifact`. Blocks deletion while this event is in the stream. Apply captures `_preVersionArtifactStatus` before overwriting `Status`. |
| `AssetVersionArtifactReleased` | `TenantId`†, `AssetId`, `MediaItemId`, `VersionNumber`, `ReleasedAt` | VersionArtifact → Active \| Archived (restores `_preVersionArtifactStatus`). Raised by `ReleaseVersionArtifact`. |
| `AssetAttachedToMediaItem` | `AssetId`, `MediaItemId`, `RoleName` | — |
| `AssetDetachedFromMediaItem` | `AssetId`, `MediaItemId`, `DetachedAt` | — |

† `TenantId` is the **first field** on the creation event per multi-tenancy convention. See [System Spec — Multi-Tenancy](../../../../shared/system-spec.md#multi-tenancy-strategy).

---

## Commands

| Command | Handler | Result |
|---|---|---|
| `InitiateAssetUploadCommand(AssetId, OwnerId, MediaItemId?, FileName, ContentType, SizeBytes)` | `InitiateAssetUploadHandler` | `Result<InitiateAssetUploadResult, DomainError>` — returns `AssetId` + pre-signed PUT URL |
| `InitiateMultipartUploadCommand(AssetId, OwnerId, MediaItemId?, FileName, ContentType, SizeBytes)` | `InitiateMultipartUploadHandler` | `Result<InitiateMultipartUploadResult, DomainError>` — returns `AssetId`, `UploadId`, `Parts[]` (pre-signed part URLs) |
| `CompleteMultipartUploadCommand(AssetId, Parts[{PartNumber, ETag}])` | `CompleteMultipartUploadHandler` | `Result<Unit, DomainError>` — calls S3 `CompleteMultipartUpload`, then transitions Pending → Validating |
| `AbortMultipartUploadCommand(AssetId)` | `AbortMultipartUploadHandler` | `Result<Unit, DomainError>` — calls S3 `AbortMultipartUpload`, then transitions Pending → MultipartAborted |
| `ConfirmAssetUploadCommand(AssetId)` | `ConfirmAssetUploadHandler` | `Result<Unit, DomainError>` — rejects if `UploadMode = Multipart` |
| `RecordValidationResultCommand(TenantId, AssetId, JobId, Outcome, FailureReason?)` | `RecordValidationResultHandler` — **Internal / System-only — no API endpoint.** Dispatched by `ProcessingJobScanResultEventHandler` on receipt of `ProcessingJobScanResultIntegrationEvent` from Processing. The handler resolves `HasProcessingCapability` via `IMediaItemCapabilityService` before calling the aggregate. | `Result<Unit, DomainError>` |
| `StartAssetProcessingCommand(AssetId)` | `StartAssetProcessingHandler` | `Result<Unit, DomainError>` |
| `CompleteAssetProcessingCommand(AssetId, Renditions[], Metadata, ProcessingStatus)` | `CompleteAssetProcessingHandler` | `Result<Unit, DomainError>` |
| `FailAssetProcessingCommand(AssetId, FailureCategory, Reason)` | `FailAssetProcessingHandler` | `Result<Unit, DomainError>` |
| `TagAssetCommand(AssetId, Tags[])` | `TagAssetHandler` | `Result<Unit, DomainError>` |
| `ArchiveAssetCommand(AssetId)` | `ArchiveAssetHandler` | `Result<Unit, DomainError>` |
| `DeleteAssetCommand(AssetId, Reason?, OccurredAt)` | `DeleteAssetHandler` | `Result<Unit, DomainError>` |
| `AttachAssetToMediaItemCommand(AssetId, MediaItemId, RoleName)` | Internal — dispatched by `AssignAssetToRoleHandler` in Catalog | `Result<Unit, DomainError>` |
| `DetachAssetFromMediaItemCommand(AssetId)` | Internal — dispatched by `UnassignAssetFromRoleHandler` in Catalog | `Result<Unit, DomainError>` |
| `RecordStorageTierTransitionCommand(AssetId, NewTier, TransitionedAt)` | **System-only — no API endpoint.** Dispatched by a system storage lifecycle process when AWS S3 Lifecycle Policy transitions an object's storage class. | `Result<Unit, DomainError>` |
| `PromoteAssetToVersionArtifactCommand(TenantId, AssetId, MediaItemId, VersionNumber, OccurredAt)` | **Internal — no API endpoint.** Dispatched by `MediaItemApprovedEventHandler` for each asset in the approved snapshot. Transitions `Active/Archived → VersionArtifact`. | `Result<Unit, DomainError>` |
| `ReleaseVersionArtifactCommand(TenantId, AssetId, MediaItemId, VersionNumber, OccurredAt)` | **Internal — no API endpoint.** Dispatched by `MediaItemVersionPurgedEventHandler` for each asset in `PurgedAssetIds`. Transitions `VersionArtifact → Active \| Archived`. | `Result<Unit, DomainError>` |

---

## Command Handlers

All handlers:
1. Inject `IExecutionContext ctx` — source `TenantId` and `OwnerId`
2. Load aggregate via `IEventStore.LoadAsync<Asset, AssetId>(ctx.TenantId, cmd.AssetId, ct)`
3. Call single aggregate method
4. Persist via `IEventStore.SaveAsync<Asset, AssetId>(asset, ct)`
5. Return `Result<T, DomainError>` — no domain exceptions escape

**`InitiateAssetUploadHandler` additional responsibilities:**

All capability lookups below resolve against the **`media-item-capability-refs` reference model** (owned by Catalog, consumed by AssetManagement via `IMediaItemCapabilityReadModel`). See [MediaItemCapabilityIndex](../../../Catalog/aggregates/MediaItem/media-item.read-model.md#media-item-capability-index) for the index contract.

When `cmd.MediaItemId` is set:
1. **Existence + lifecycle check** — `readModel.GetStatusAsync(ctx.TenantId, cmd.MediaItemId)` must return a non-null, non-`Archived` status. Otherwise return `DomainError.MediaItemNotFound` or `DomainError.MediaItemArchived`.
2. **Max file size enforcement** — if `readModel.GetMaxFileSizeBytesAsync(ctx.TenantId, cmd.MediaItemId)` returns a value, `cmd.SizeBytes` must be `<=` that value. Otherwise return `DomainError.AssetTooLarge`.
3. **Quota exemption resolution** — call `readModel.HasProcessingCapabilityAsync(ctx.TenantId, cmd.MediaItemId)`. If `false`, skip the billing call entirely — the asset is a document and is exempt from processing-bandwidth quota.

When `cmd.MediaItemId` is null (standalone upload):
- No existence or capability lookup runs.
- A **platform-default maximum file size** applies (configured per deployment via `AssetManagement:Upload:StandaloneMaxFileSizeBytes`). Violations return `DomainError.AssetTooLarge`.
- Quota is always evaluated (standalone media-assets always run the full processing pipeline).

After the guards pass:
- Call `IBillingAcl.CheckQuotaAsync(ctx.OwnerId, sizeBytes)` unless exempt above — non-`Allowed` results return `DomainError.QuotaExceeded`.
- Generate `StorageKey` via `IStorageKeyGenerator.Generate(ctx.TenantId, cmd.AssetId, contentType, fileName)`.
- Issue pre-signed S3 PUT URL (15-minute TTL) via `IPresignedUrlService`. The URL signs `Content-Type` and the exact declared `SizeBytes` as a required `Content-Length` header — S3 rejects any PUT whose headers don't match (SignatureDoesNotMatch). Note: `content-length-range` is a POST policy feature and is not available for pre-signed PUT URLs; exact `Content-Length` signing is the PUT equivalent. Upper-bound enforcement is delegated to the S3 bucket policy condition `s3:content-length-range` (CDK) and `ConfirmAssetUploadHandler` (server-side defence-in-depth).

**Defence-in-depth at `ConfirmAssetUpload`:** the handler performs HEAD on the S3 object and applies three guards in order:
1. **Content-Type** — actual type must match the declared type; mismatch returns a validation error.
2. **Declared-size check (primary, unconditional)** — `actual ContentLength > asset.SizeBytes` returns a validation error. Catches the case where a client declared a small size (to understate quota) then uploaded a larger file. The pre-signed PUT URL signs the exact `Content-Length`, so any bypass is caught here.
3. **Profile-limit check (secondary, item-scoped only)** — `actual ContentLength > media-profile.MaxFileSizeBytes` returns a validation error. Catches media-profile limits tightened after upload initiation.

All guard failures return a command-level validation error — the asset remains in `Pending` state and no domain event is emitted.

**`InitiateMultipartUploadHandler` responsibilities:**

Same guards as `UploadAssetHandler` (existence, archive state, max file size, quota). Additionally:
1. Calls `IMultipartUploadService.InitiateAsync(storageKey, mimeType, ct)` → receives S3 `UploadId`.
2. Computes `partCount = ceil(sizeBytes / partSizeBytes)` using configured `MultipartPartSizeBytes`.
3. Calls `IMultipartUploadService.GeneratePartUrlsAsync(storageKey, uploadId, partCount, ttl, ct)` → receives `PresignedPartUrl[]`.
4. Creates aggregate via `Asset.InitiateMultipartUpload(...)` factory.
5. Returns `InitiateMultipartUploadResult` containing `AssetId`, `UploadId`, and `Parts[]`.

**`CompleteMultipartUploadHandler` responsibilities:**
1. Loads aggregate. Guards: `Status = Pending`, `UploadMode = Multipart`.
2. Calls `IMultipartUploadService.CompleteAsync(asset.StorageKey, asset.MultipartUploadId, parts, ct)` — S3 assembles the object.
3. Calls `asset.ConfirmUpload(now)` → `Pending → Validating`.
4. Persists.

**`AbortMultipartUploadHandler` responsibilities:**
1. Loads aggregate. Guards: `Status = Pending`, `UploadMode = Multipart`.
2. Calls `IMultipartUploadService.AbortAsync(asset.StorageKey, asset.MultipartUploadId, ct)` — releases S3 part storage.
3. Calls `asset.AbortMultipartUpload(now)` → `Pending → MultipartAborted`.
4. Persists.

**`ConfirmAssetUploadHandler` guard (multipart):** If `asset.UploadMode = Multipart` and `asset.Status = Pending`, return `409 Conflict`. The asset must be completed via `CompleteMultipartUploadCommand`.

**Write model service interfaces required:**

```csharp
interface IStorageKeyGenerator {
    S3Key Generate(TenantId tenantId, AssetId assetId, MediaContentType contentType, FileName fileName);
}

interface IPresignedUrlService {
    // sizeBytes is the exact declared upload size — signed as Content-Length in the PUT URL.
    Task<PresignedUploadResult> GeneratePutUrlAsync(S3Key key, string mimeType, long sizeBytes, CancellationToken ct);
}

interface IMultipartUploadService {
    Task<string> InitiateAsync(S3Key key, string mimeType, CancellationToken ct);
    Task<IReadOnlyList<PresignedPartUrl>> GeneratePartUrlsAsync(S3Key key, string uploadId, int partCount, TimeSpan ttl, CancellationToken ct);
    Task CompleteAsync(S3Key key, string uploadId, IReadOnlyList<UploadPartInfo> parts, CancellationToken ct);
    Task AbortAsync(S3Key key, string uploadId, CancellationToken ct);
}

// UploadPartInfo carries the partNumber + ETag pair returned by S3 on each part PUT.
record UploadPartInfo(int PartNumber, string ETag);
record PresignedPartUrl(int PartNumber, string Url, DateTimeOffset ExpiresAt);

interface IBillingAcl {
    Task<QuotaCheckResult> CheckQuotaAsync(OwnerId ownerId, long sizeBytes, CancellationToken ct);
}

// Backed by the `media-item-capability-refs` reference model projected from
// MediaItemCreated + MediaProfilePublished + MediaItemArchived in Catalog.
interface IMediaItemCapabilityReadModel {
    Task<MediaItemStatus?> GetStatusAsync(TenantId tenantId, MediaItemId mediaItemId, CancellationToken ct);
    Task<bool> HasProcessingCapabilityAsync(TenantId tenantId, MediaItemId mediaItemId, CancellationToken ct);
    Task<long?> GetMaxFileSizeBytesAsync(TenantId tenantId, MediaItemId mediaItemId, CancellationToken ct);
}

// The upload path only cares about "does this media-item exist and is it still accepting uploads".
// Draft / UnderReview / Published / Rejected / Withdrawn all collapse to Active here;
// only Archived is terminal for upload purposes.
enum MediaItemStatus { Active, Archived }
```

---

## Published Integration Events

Published inline by `AssetDomainEventPublisher` (`AssetManagement.WriteModel`) immediately after the domain event is persisted. All events target the `media-integration-events` SNS topic.

| Integration Event                          | Source Domain Event        | Published When / Consumers                                                                                                 |
| ------------------------------------------ | -------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `AssetUploadInitiatedIntegrationEvent`     | `AssetUploadInitiated`     | Always — Processing (capability-gated), Notifications. `[MessageType("media.asset.upload-initiated")]`                     |
| `AssetUploadConfirmedIntegrationEvent`     | `AssetUploadConfirmed`     | Always — Processing (`AssetValidationWorker` via `media-processing` SQS), Notifications. Payload: `TenantId`, `AssetId`, `OwnerId`, `FileName`, `ContentType`, `StorageKey`, `Status` (`"Validating"`), `ConfirmedAt`, `EventVersion`. See [context-overview](../../context-overview.md#assetuploadconfirmedintegrationevent). |
| `AssetValidationPassedIntegrationEvent`    | `AssetValidationPassed`    | Always — SagaOrchestrator (`AssetValidationPassedSagaHandler`); advances `AssetIngestionSaga` to select processing branch. Carries `HasProcessingCapability` flag so the saga can dispatch `StartProcessingJobCommand` or `BypassProcessingJobCommand` without a cross-BC capability lookup. |
| `AssetProcessingCompletedIntegrationEvent` | `AssetProcessingCompleted` | Always — Notifications; Billing (filtered: forwarded only when `Processing` capability present on the linked MediaProfile) |
| `AssetProcessingFailedIntegrationEvent`    | `AssetProcessingFailed` \| `AssetValidationFailed` | Always — Notifications, SagaOrchestrator (for timeout compensation). `Status` and `FailureCategory` string values vary by source — see [context-overview `AssetProcessingFailedIntegrationEvent`](../../context-overview.md#assetprocessingfailedintegrationevent). |
| `AssetAttachedToMediaItemIntegrationEvent` | `AssetAttachedToMediaItem` | Always — Search/Discovery                                                                                                  |
| `AssetArchivedIntegrationEvent`            | `AssetArchived`            | Always — Notifications, Billing                                                                                            |
| `AssetDeletedIntegrationEvent`             | `AssetDeleted`             | Always — Notifications, Search/Discovery                                                                                   |
| `AssetInfectionDetectedIntegrationEvent`   | `AssetInfectionDetected`   | Always — Notifications; Security audit log                                                                                 |

---

## Consumed Integration Events

Consumed via the `media-cross-module-events` SQS queue. All consumers are registered in the `Media.IntegrationEventConsumers.Lambda` host.

**From Catalog — consumer: `MediaItemCapabilityConsumer`**

Maintains the `media-item-capability-refs` write-side reference model used by `UploadAssetHandler` to resolve MediaItem status, capabilities, and file size limits without loading the Catalog aggregate.

| Integration Event | Source | Command / Action |
|---|---|---|
| `MediaItemCreatedMessage` | Catalog | Materialises a new `media-item-capability-refs` entry; derives `Capabilities` and `MaxFileSizeBytes` from the embedded `MediaProfileSnapshot` |
| `MediaItemArchivedMessage` | Catalog | Sets `IsArchived = true` on the projection entry; prevents new uploads against archived media-items |

**From Catalog — consumer: `MediaItemApprovedEventHandler`**

Promotes each asset in an approved MediaItem snapshot to `VersionArtifact` status, domain-blocking deletion while the version exists. Per-asset failures are logged and skipped rather than failing the whole message.

| Integration Event | Source | Command Dispatched | Asset Transition |
|---|---|---|---|
| `MediaItemApprovedIntegrationEvent` | Catalog | `PromoteAssetToVersionArtifactCommand` — one per asset in `ApprovedAssets` | `Active/Archived → VersionArtifact` |

**From Catalog — consumer: `MediaItemVersionPurgedEventHandler`**

Releases each snapshotted asset from `VersionArtifact` protection when the owning MediaItem version is purged. Restores the asset to its pre-promotion status (`Active` or `Archived`), unblocking deletion. Per-asset failures are logged and skipped rather than failing the whole message.

| Integration Event | Source | Command Dispatched | Asset Transition |
|---|---|---|---|
| `MediaItemVersionPurgedIntegrationEvent` | Catalog | `ReleaseVersionArtifactCommand` — one per asset in `PurgedAssetIds` | `VersionArtifact → Active \| Archived` |

**From Processing — consumers: `ProcessingJobScanResultEventHandler`, `ProcessingJobStartedEventHandler`, `ProcessingJobCompletedEventHandler`, `ProcessingJobFailedEventHandler`**

Advances the `Asset` aggregate state machine in response to job-level outcomes from the Processing context. See [Processing write model](../../../Processing/aggregates/ProcessingJob/processingjob.write-model.md) for event contracts.

| Integration Event | Source | Command Dispatched | Asset Transition |
|---|---|---|---|
| `ProcessingJobScanResultIntegrationEvent` | Processing | `RecordValidationResultCommand` — handler resolves `HasProcessingCapability` via `IMediaItemCapabilityService` before calling the aggregate | `Validating → Validating` (emits `AssetValidationPassed` or failure variant) |
| `ProcessingJobStartedIntegrationEvent` | Processing | `StartAssetProcessingCommand` | `Validating → Processing` |
| `ProcessingJobCompletedIntegrationEvent` | Processing | `CompleteAssetProcessingCommand` | `Processing → Active`; renditions + metadata attached |
| `ProcessingJobFailedIntegrationEvent` | Processing | `FailAssetProcessingCommand` | `Processing → ProcessingFailed` |

---

## Sagas

### AssetIngestionSaga

Manages the async processing window for a single Asset. Triggered on `AssetValidationPassed`. Holds a `TimeoutAt` timestamp. `SagaTimeoutScanner` polls and dispatches `FailAssetProcessing(AssetId, FailureCategory.ProcessingTimeout)` if the processing window expires.

See: [System Spec — Saga Coordination](../../../../shared/system-spec.md#saga-coordination-patterns)

---

## Internal Consistency Rules

1. `StorageKey` is computed by `StorageKeyGenerator` at `InitiateUpload` time; stamped onto `AssetUploadInitiated`; immutable ther