# Request/Response Model Review

_Generated: 2026-07-06. Based on spec at `Z:\claudia\magiq\projects\magiq-media\spec\` vs code under `src/modules\`._

---

## Summary of Issue Categories

| # | Category | Count |
|---|---|---|
| 1 | `TenantId` in responses (should never be returned) | 9 |
| 2 | `Timestamp` used instead of semantic name (`CreatedAt`, `InitiatedAt`, etc.) | 3 |
| 3 | Missing client-provided ID field (`{entity}Id`) on create requests | 5 |
| 4 | Property naming diverges from spec | 14 |
| 5 | Duplicate properties in same model | 2 |
| 6 | Missing required/expected properties | 12 |
| 7 | Extra properties that should not exist | 8 |
| 8 | Pagination — `PageSize` missing from list responses | 4 |
| 9 | Response body present when spec says no body | 3 |
| 10 | Property ordering inconsistencies | 8 |

---

## AssetManagement

### `InitiateAssetUpload` — POST /assets/uploads

**Request (`InitiateAssetUploadRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `MediaContentType` | Spec: `contentType` |
| Wrong name | `ContentLength` | Spec: `FileSizeBytes` |
| Missing | — | Spec allows optional client-provided `assetId` for idempotency |

**Response (`InitiateAssetUploadResponse`):** OK — `Id, UploadUrl, ExpiresAt` matches spec.

---

### `ConfirmAssetUpload` — POST /assets/{assetId}/uploads/confirm

**Response (`ConfirmAssetUploadResponse`):**

| Issue | Detail |
|---|---|
| Extra response body | Spec says 202 no body. Code returns `{ Id, ConfirmedAt }`. Remove response body. |

---

### `GetAssetById` — GET /assets/{assetId}

**Response (`GetAssetByIdResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Should not exist | `TenantId` | Never in spec responses; derived from auth |
| Wrong name | `SizeBytes` | Spec uses `sizeBytes` in context of the file, but property should be `FileSizeBytes` — align with `AssetRenditionModel.FileSizeBytes` |
| Extra | `UpdatedAt` | Not in spec |
| Extra | `ArchivedAt` | Not in spec (spec has this only on Collection) |
| Extra | `DeletedAt` | Not in spec |
| Ordering | `OwnerId` before `MediaItemId` | Spec order: `id, mediaItemId, ownerId, status, contentType, originalFileName, roleName, isPrimary` |

---

### `ListAssets` — GET /assets

**Request (`ListAssetsRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `MediaItemId` | Spec query param: `itemId` |

**Nested `AssetSummaryModel`:**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `FileName` | Spec: `originalFileName` |
| Extra | `OwnerId` | Not in spec summary |
| Extra | `FileSizeBytes` | Not in spec summary |
| Extra | `Tags` | Not in spec summary |
| Extra | `UpdatedAt` | Not in spec summary |

---

### `GetAssetDownloadUrl` — GET /assets/{assetId}/download

**Response:** OK — `DownloadUrl, ExpiresAt, FileName, ContentType, FileSizeBytes` matches spec (`downloadUrl, expiresAt, fileName, contentType, sizeBytes`). Note: `FileSizeBytes` vs spec `sizeBytes` — minor naming delta.

---

### `TagAsset` — POST /assets/{assetId}/tags

**Response (`TagAssetResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `Timestamp` / `UpdatedAt` | Spec: `{ id, tags[], timestamp }` — code only returns `{ Id, Tags }` |

---

### `DeleteAsset` — DELETE /assets/{assetId}

**Request (`DeleteAssetRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Extra | `Reason` | Spec says DELETE has no body — remove |

---

### `ArchiveAsset` — POST /assets/{assetId}/archive

**Response (`ArchiveAssetResponse`):**

| Issue | Detail |
|---|---|
| Extra response body | Spec says 202 no body. Code returns `{ Id, ArchivedAt }`. Remove response body. |

---

### `InitiateMultipartUpload` — POST /assets/multipart-uploads

**Request:**

| Issue | Property | Detail |
|---|---|---|
| Inconsistency | `MediaItemId` | Single-upload uses `ItemId` for the same field — both should align. Spec uses `mediaItemId`, so both should use `MediaItemId` (rename `InitiateAssetUploadRequest.ItemId` → `MediaItemId`) |
| Missing | — | Spec allows optional client-provided `assetId` |

---

### `BulkInitiateAssetUpload` — POST /assets/uploads/bulk

**Nested `BulkInitiateAssetUploadRequestModel`:**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `FileSizeBytes` | Spec: `sizeBytes` |
| Missing | `AssetId` | Spec allows optional client-provided `assetId` per item |
| Ordering | — | Spec order: `assetId, mediaItemId, originalFileName, contentType, sizeBytes`. Code: `ContentType, MediaItemId, OriginalFileName, FileSizeBytes` |

**Nested `BulkInitiateAssetUploadFailedModel`:**

| Issue | Property | Detail |
|---|---|---|
| Naming | `Name` | Ambiguous — should be `OriginalFileName` or `AssetId` to identify which item failed |

---

### `BulkConfirmAssetUpload` — POST /assets/uploads/bulk-confirm

**Response (`BulkConfirmAssetUploadResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `Skipped` | Spec response includes `skipped[]`. Code only has `Succeeded, Failed`. |

---

## Catalog — Collections

### `CreateCollection` — POST /catalog/collections

**Request (`CreateCollectionRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `CollectionId` | Spec allows optional client-provided ID for idempotency |
| Missing | `DefaultMediaProfileId` | Spec includes optional `defaultMediaProfileId` on create |
| Ordering | `Description` before `Name` | Spec order: `name, description, visibility, defaultMediaProfileId` |

**Response (`CreateCollectionResponse`):**

| Issue | Detail |
|---|---|
| Extra fields | Spec says just `{ id }`. Code returns `{ Id, Name, Description, Visibility, CreatedAt }` — extra fields |

---

### `PatchCollection` — PATCH /catalog/collections/{collectionId}

**Request (`PatchCollectionRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Ordering | `Description` before `Name` | Should follow spec: `name, description, visibility` |

---

### `SetDefaultMediaProfile` — PUT /catalog/collections/{collectionId}/default-profile

**Request (`SetDefaultMediaProfileRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `ProfileId` | Spec: `mediaProfileId` |

---

### `TagCollection` — POST /catalog/collections/{collectionId}/tags

Response is 204 No Content — OK. Request looks fine.

---

## Catalog — Folders

### `CreateFolder` — POST /catalog/collections/{collectionId}/folders

**Request (`CreateFolderRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Extra | `Originator` | Not in spec for Create — spec only has `parentFolderId, name, description, openedDate, closedDate` |
| Ordering | `ClosedDate` before `Description` before `Name` | Spec order: `parentFolderId, name, description, openedDate, closedDate` |

**Response (`CreateFolderResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `Originator` | If `Originator` is accepted in request (even if spec doesn't define it), it should be reflected in response |
| Ordering | `OpenedDate` as `DateTimeOffset` (non-nullable) | Spec returns `openedDate` (optional) — response has non-nullable `OpenedDate` at position 7 |

---

### `MoveFolder` — PUT /catalog/folders/{folderId}/parent

**Request (`MoveFolderRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Extra | `CollectionId` | Not in spec — spec says request is just `newParentFolderId (optional)`. Route has `folderId`. |
| Ordering | `CollectionId` first | If kept, should be last (route params first, then body params) |

---

### `BulkCreateFolders` — POST /catalog/collections/{collectionId}/folders/bulk

**Request (`BulkCreateFoldersRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Ordering | `OnDuplicate` before `OnError` | All other bulk requests (`BulkCreateCollections`, `BulkCreateMediaItems`) order: `Items, OnError, OnDuplicate`. This has `Items, OnDuplicate, OnError`. |

---

### `BulkCreateFoldersByPath` — POST /catalog/collections/{collectionId}/folders/bulk-paths

**Request (`BulkCreateFoldersByPathRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Nullable mismatch | `CollectionId?` | Comes from route — should not be nullable |
| Ordering | `OnError, Paths, PathSeparator, RootFolderId` | Spec order: `paths[], rootFolderId, pathSeparator, onError`. Code has `OnError` first. |

---

### `GetFolderById` — GET /catalog/folders/{folderId}

**Response (`GetFolderByIdResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Should not exist | `TenantId` | Not in spec responses |
| **DUPLICATE** | `ArchivedAt` AND `ArchivedDate` | Both present — pick one. Spec uses `archivedAt`. Remove `ArchivedDate`. |
| **DUPLICATE** | `ClosedAt` AND `ClosedDate` | Both present — spec uses `closedAt`. But convention in domain uses `closedDate` as the business date. Clarify: `ClosedDate` = user-entered business date, `ClosedAt` = system timestamp. If both are valid, document their difference clearly. Currently both serialized = ambiguous to consumers. |
| Ordering | `TenantId` at position 1 | Spec/convention: `id` is always first |

---

## Catalog — Media Items

### `CreateMediaItem` — POST /catalog/items

**Request (`CreateMediaItemRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `MediaItemId` | Spec allows optional client-provided ID |
| Wrong name | `ProfileId` | Spec: `mediaProfileId` |
| Ordering | `Author, Description, FolderId, ProfileId, RecordDate, Title` | Spec order: `mediaItemId, mediaProfileId, title` then optional fields. `Title` should come before optional fields. |

**Response (`CreateMediaItemResponse`):**

| Issue | Detail |
|---|---|
| Extra fields | Spec says `{ id }`. Code returns `{ Id, Title, CreatedAt }`. |

---

### `CreateMediaItemInFolder` — POST /catalog/folders/{folderId}/items

**Request (`CreateMediaItemInFolderRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `ProfileId` | Spec: `mediaProfileId` |

**Response (`CreateMediaItemInFolderResponse`):** Matches spec `{ id, title, createdAt }` — OK.

---

### `BulkCreateMediaItems` — POST /catalog/items/bulk

**Nested `BulkCreateMediaItemModel`:**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | (need to verify) | Spec uses `media-items[]` key with `mediaItemId, mediaProfileId, title, description (optional), folderId`. Verify `ProfileId` vs `mediaProfileId` and field name consistency. |

---

### `PublishMediaItem` — POST /catalog/items/{itemId}/publish

**Request (`PublishMediaItemRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `CommentThreadId` | Spec includes optional `commentThreadId` |

**Response (`PublishMediaItemResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `VersionNumber` | Spec 200 response (auto-approve path): `{ status, versionNumber }` — code only has `ExpectedStatus` |
| Extra / naming | `ChangeRequestId` | Not in spec response body — spec puts this in the `Location` header for the 202 path |

---

### `GetMediaItemById` — GET /catalog/items/{itemId}

**Response (`GetMediaItemByIdResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Should not exist | `TenantId` | Not in spec |
| Missing | `CheckoutStatus` | Spec includes `checkoutStatus` |
| Missing | `ActiveMediaChangeRequestId` | Spec includes `activeMediaChangeRequestId` |
| Ordering | `Id, TenantId, OwnerId, MediaProfileId` | Spec order: `id, folderId, collectionId, ownerId, mediaProfileId` — `folderId, collectionId` should come before `ownerId` |

---

### `SearchMediaItems` — GET /catalog/items/search

**Response (`SearchMediaItemsResponse`):**

| Issue | Detail |
|---|---|
| Wrong item model | `Items` uses `GetMediaItemByIdResponse` (full detail model). Should use a summary model. This bloats search results and couples search to the detail contract. |

---

## Catalog — Media Profiles

### `CreateMediaProfile` — POST /catalog/profiles

**Request (`CreateMediaProfileRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `MediaProfileId` | Spec allows optional client-provided ID |

**Response (`CreateMediaProfileResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `Timestamp` | Spec says `id` only. If returning a timestamp, name it `CreatedAt`. |
| Extra | `Timestamp` | Spec says just `{ id }`. Remove or rename. |

---

### `CreateMediaProfileDraft` — POST /catalog/profiles/{profileId}/draft

**Request (`CreateMediaProfileDraftRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Extra / wrong | `HasDraft` (bool, default true) | Implementation detail leaking into API. Creating a draft endpoint should have no request body. Remove `HasDraft`. |

---

### `AddAssetDefinition` — POST /catalog/profiles/{profileId}/asset-definitions

**Request (`AddAssetDefinitionRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Ordering | `AcceptedContentTypes, AllowMultiple, DefaultAssetId, DimensionConstraints, DisplayName, DisplayOrder, IsRequired, MaxFileSizeBytes, ProfileId, PreferredStorageTier, RoleName` | Spec order: `roleName` first, then `acceptedContentTypes[], isRequired, allowMultiple, maxFileSizeBytes, dimensionConstraints`. Route params (`ProfileId`) should be logically last. |

---

### `UpdateAssetDefinition` — PATCH /catalog/profiles/{profileId}/asset-definitions/{roleName}

**Request (`UpdateAssetDefinitionRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `IsRequired` | `AddAssetDefinition` accepts `IsRequired`; `UpdateAssetDefinition` does not — inconsistent |
| Ordering | `AllowMultiple, DimensionConstraints, DisplayName, MaxFileSizeBytes, ProfileId, PreferredStorageTier, RoleName, NewRoleName` | Route params (`ProfileId, RoleName`) should be at top or logically separated; `NewRoleName` should be after `RoleName` — currently OK |

---

### `SetReviewPolicy` — PUT /catalog/profiles/{profileId}/review-policy

**Request (`SetReviewPolicyRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `Policy` | Spec: `reviewPolicy`. Should be `ReviewPolicy` (or at least the serialized JSON key must match) |

---

### `SetCheckoutPolicy` — PUT /catalog/profiles/{profileId}/checkout-policy

**Request (`SetCheckoutPolicyRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `Policy` | Spec: `checkoutPolicy`. Should be `CheckoutPolicy` |

---

### `GetMediaProfileById` — GET /catalog/profiles/{profileId}

**Response (`GetMediaProfileByIdResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Should not exist | `TenantId` | Not in spec |

---

### `ListMediaProfiles` — GET /catalog/profiles

**Response (`ListMediaProfilesResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `PageSize` | All other list responses include `PageSize`. This only has `Items, NextPageToken`. |

---

### `ListMediaProfileVersions` — GET /catalog/profiles/{profileId}/versions

**Response (`ListMediaProfileVersionsResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `PageSize` | Same issue as `ListMediaProfiles`. |

---

### `UpdatePinnedRecordTypeVersion` — PUT /catalog/profiles/{profileId}/record-types/{recordTypeId}/version

**Request (`UpdatePinnedRecordTypeVersionRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Ordering | `ProfileId, NewVersion, RecordTypeId` | Route params first: `ProfileId, RecordTypeId` then body: `NewVersion` |

---

### `AttachRecordType` — POST /catalog/profiles/{profileId}/record-types/{recordTypeId}

**Request (`AttachRecordTypeRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Extra | `Version` (int) | Spec doesn't mention pinning version at attach time — this is only in `UpdatePinnedRecordTypeVersion`. If intentional, needs spec entry. |

---

### `ReorderAssetDefinitions` — POST /catalog/profiles/{profileId}/asset-definitions/reorder

**Request (`ReorderAssetDefinitionsRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `FieldOrders` | Should be `AssetDefinitionOrders` — these are asset definitions, not fields |

---

## Metadata — RecordTypes

### `CreateRecordType` — POST /metadata/record-types

**Request (`CreateRecordTypeRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `RecordTypeId` | Spec allows optional client-provided ID |

**Response (`CreateRecordTypeResponse`):**

| Issue | Detail |
|---|---|
| Extra fields | Spec says `{ id }`. Code returns `{ Id, Name, CreatedAt }`. |

---

### `CreateRecordTypeDraft` — POST /metadata/record-types/{recordTypeId}/draft

**Request (`CreateRecordTypeDraftRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Extra / wrong | `HasDraft` (bool, default true) | Same issue as `CreateMediaProfileDraft` — implementation detail, should not be in API. Remove. |

---

### `GetRecordTypeById` — GET /metadata/record-types/{recordTypeId}

**Response (`GetRecordTypeByIdResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Should not exist | `TenantId` | Not in spec |
| Missing | `Aliases` | Spec includes `aliases[]` |
| Extra | `Description` | Not in spec response (spec only has `name`, no `description`) |
| Extra | `DisplayName` | Not in spec response |
| Extra | `Capabilities` | Not in spec response |
| Extra | `DraftBasedOnVersion` | Not in spec response |
| Ordering | `Id, TenantId, OwnerId` | Spec order: `id, ownerId, name, publishedVersion, publishedAt, aliases[], hasDraft, draftFields[], isDeprecated, createdAt` |

---

### `GetRecordTypeVersion` — GET /metadata/record-types/{recordTypeId}/versions/{version}

**Response (`GetRecordTypeVersionResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `RecordTypeId` | Spec: `id` |
| Missing | `Aliases` | Spec includes `aliases[]` |
| Extra | `Name` | Not in spec version response |
| Extra | `Capabilities` | Not in spec version response |

---

### `ListRecordTypeVersions` — GET /metadata/record-types/{recordTypeId}/versions

**Response (`ListRecordTypeVersionsResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `PageSize` | `ListRecordTypes` includes `PageSize`; this sibling endpoint does not — inconsistent. |

---

### `AddCapabilityToRecordType` — POST /metadata/record-types/{recordTypeId}/capabilities

Response is 204 No Content — spec says 202. Minor inconsistency.

---

---

## ChangeRequests

### `GetChangeRequestById` — GET /change-requests/{changeRequestId}

**Response (`GetChangeRequestByIdResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `OwnerId` | Spec: `createdById` |
| Extra | `UpdatedAt` | Not in spec |
| Ordering | `Id, OwnerId, MediaItemId` | Spec order: `id, mediaItemId, createdById, commentCount, createdAt` — `MediaItemId` should come before `OwnerId` |

---

### `ListChangeRequestComments` — GET /change-requests/{changeRequestId}/comments

**Response (`ListChangeRequestCommentsResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `PageSize` | All other paginated list responses include `PageSize`. Only has `Items, NextPageToken`. |

---

### `AddComment` — POST /change-requests/{changeRequestId}/comments

**Request (`AddCommentRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `CommentId` | Spec allows optional client-provided ID for idempotency |

**Response (`AddCommentResponse`):**

| Issue | Detail |
|---|---|
| Extra response body | Spec says 201 no body. Code returns `{ Id, CreatedAt }`. Remove response body. |

---

### `EditComment` — PATCH /change-requests/{changeRequestId}/comments/{commentId}

**Request (`EditCommentRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `NewBody` | Spec: `body` — the updated body is just `body`, not `newBody` |

---

---

## Registration

### `InitiateRegistration` — POST /catalog/items/{itemId}/registrations

**Request (`InitiateRegistrationRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `RegistrationId` | Spec allows optional client-provided ID |
| Missing | `Notes` | Spec includes optional `notes` |

**Response (`InitiateRegistrationResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `Timestamp` | Spec/convention: should be `InitiatedAt` (semantic name) |
| Missing | — | Spec says `{ id }` — code adds `MediaItemId, Timestamp`. Extra fields. |

---

### `ConfirmRegistration` — POST /registrations/{registrationId}/confirm

**Request (`ConfirmRegistrationRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Extra | `ConfirmedAt` | Should be server-generated timestamp, not accepted from client |

---

### `RejectRegistration` — POST /registrations/{registrationId}/reject

**Request (`RejectRegistrationRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `Reason` | Spec: `rejectionReason` |

---

### `RecordRegistrationSubmission` — POST /registrations/{registrationId}/submission

**Request (`RecordRegistrationSubmissionRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Extra | `ExternalReference` | Spec says this is a system endpoint with no body |
| Extra | `Notes` | Same — spec says no body for this system endpoint |

---

### `AttachMediaItemToRegistration` — POST /registrations/{registrationId}/documents

**Request (`AttachMediaItemToRegistrationRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `ItemId` | Spec: `mediaItemId` |

---

### `RequestAmendment` — POST /registrations/{registrationId}/amendments

**Request (`RequestAmendmentRequest`):**

| Issue | Property | Detail |
|---|---|---|
| Missing | `AmendmentId` | Spec allows optional client-provided ID |
| Wrong name | `ItemId` | Spec: `mediaItemId` |

**Response (`RequestAmendmentResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Wrong name | `Timestamp` | Should be `RequestedAt` |
| Extra | `RegistrationId` | Spec says `{ id }` only |

---

### `GetRegistrationById` — GET /registrations/{registrationId}

**Response (`GetRegistrationByIdResponse`):**

| Issue | Property | Detail |
|---|---|---|
| Should not exist | `TenantId` | Not in spec |
| Extra | `MediaProfileId` | Not in spec |
| Naming split | `ExternalReference` + `ReferenceNumber` | Spec has one field: `reference`. Code has two separate fields — clarify which is the spec `reference` and consolidate or document the difference |
| Extra | `RejectionReason` | Not in spec at top level (only `status` indicates rejection) |
| Extra | `ExpiresAt` | Not in spec |
| Wrong name | `Items` | Spec: `documents[]` |
| Ordering | `TenantId` at position 2 | `Id` should always be first; `TenantId` should not be present at all |

**Nested `RegistrationItemModel` (inside `Items`):**

| Issue | Property | Detail |
|---|---|---|
| Extra | `AddedViaAmendmentId` | Not in spec for document model |

---

### `RegistrationSummaryModel` (ListRegistrations, SearchRegistrations)

| Issue | Property | Detail |
|---|---|---|
| Should not exist | `TenantId` | Not in spec summary |

---

---

## Cross-Cutting Issues

### `TenantId` in Response Models

The following responses include `TenantId` which is **never** part of spec responses. TenantId is derived from JWT auth and returning it adds noise and breaks multi-tenant information hygiene.

- `GetCollectionByIdResponse`
- `GetFolderByIdResponse`
- `GetMediaItemByIdResponse`
- `GetAssetByIdResponse`
- `GetMediaProfileByIdResponse`
- `GetRecordTypeByIdResponse`
- `GetMediaItemVersionResponse`
- `GetRegistrationByIdResponse`
- `RegistrationSummaryModel`

**Action:** Remove `TenantId` from all response models.

---

### `Timestamp` Instead of Semantic Name

| Endpoint | Field | Should be |
|---|---|---|
| `CreateMediaProfile` response | `Timestamp` | `CreatedAt` |
| `InitiateRegistration` response | `Timestamp` | `InitiatedAt` |
| `RequestAmendment` response | `Timestamp` | `RequestedAt` |

---

### `PageSize` Missing from List Responses

The following list responses are missing `PageSize` (inconsistent with all other paginated list endpoints):

- `ListMediaProfilesResponse` — has `Items, NextPageToken` only
- `ListMediaProfileVersionsResponse` — has `Items, NextPageToken` only
- `ListRecordTypeVersionsResponse` — has `Items, NextPageToken` only
- `ListChangeRequestCommentsResponse` — has `Items, NextPageToken` only

---

### Missing Client-Provided ID on Create Requests

Spec allows an optional caller-supplied ID for idempotent creation on:

| Endpoint | Missing field |
|---|---|
| `CreateCollection` | `CollectionId` |
| `CreateMediaProfile` | `MediaProfileId` |
| `CreateRecordType` | `RecordTypeId` |
| `InitiateRegistration` | `RegistrationId` |
| `AddComment` | `CommentId` |
| `InitiateAssetUpload` | `AssetId` |
| `RequestAmendment` | `AmendmentId` |

---

### Redundant `HasDraft` Bool on Draft Creation Endpoints

Both `CreateMediaProfileDraft` and `CreateRecordTypeDraft` requests include `HasDraft: bool (default: true)` — an internal state field leaked into the API contract. Draft creation endpoints should accept no body (route param is sufficient). Remove `HasDraft` from both.

---

### `SearchMediaItems` Uses Full Detail Model for Items

`SearchMediaItemsResponse.Items` is typed as `IReadOnlyList<GetMediaItemByIdResponse>` — the full get-by-id response. Search results should use a lightweight summary model consistent with other list/search endpoints (`MediaItemSummaryModel`). This couples search to the detail contract and returns unnecessary data.

---

### Response Bodies When Spec Says No Body

| Endpoint | Code returns | Spec says |
|---|---|---|
| `ConfirmAssetUpload` (POST /assets/{assetId}/uploads/confirm) | `{ Id, ConfirmedAt }` | 202 no body |
| `ArchiveAsset` (POST /assets/{assetId}/archive) | `{ Id, ArchivedAt }` | 202 no body |
| `AddComment` (POST /change-requests/{changeRequestId}/comments) | `{ Id, CreatedAt }` | 201 no body |

---

### `GetFolderById` — Duplicate Semantic Fields

`GetFolderByIdResponse` contains:
- `ArchivedAt` AND `ArchivedDate` — both present. Spec uses `archivedAt`. **Remove `ArchivedDate`.**
- `ClosedAt` AND `ClosedDate` — both present. Spec uses `closedAt`. Note: `ClosedDate` may be a user-entered business date distinct from the system-generated `ClosedAt` timestamp — if so this distinction must be documented and the spec updated. Currently ambiguous to API consumers.

---

### `BulkCreateFolders` — `OnDuplicate`/`OnError` Ordering

`BulkCreateFoldersRequest` has `OnDuplicate` before `OnError`. Every other bulk request (`BulkCreateCollections`, `BulkCreateMediaItems`) orders `OnError` before `OnDuplicate`. Flip to be consistent.

---

### `MoveFolder` — Extra `CollectionId` in Request

`MoveFolderRequest` has `CollectionId` which is not in spec. Spec only requires `newParentFolderId` (optional). Remove `CollectionId`.

---

### `SetReviewPolicy` / `SetCheckoutPolicy` — Generic `Policy` Property Name

Both use `Policy` as the property name. Should be `ReviewPolicy` and `CheckoutPolicy` respectively to match spec field names and avoid ambiguity in the model.

---

### `ReorderAssetDefinitions` — Wrong Property Name

`ReorderAssetDefinitionsRequest.FieldOrders` should be `AssetDefinitionOrders` — these are asset definitions, not fields. `FieldOrders` is the pattern used in `ReorderFieldsInRecordType` and was copied incorrectly.

---

### `AttachRecordType` — Unspecified `Version` Field

`AttachRecordTypeRequest` includes `Version: int` but spec doesn't describe version-pinning at attach time (that's `UpdatePinnedRecordTypeVersion`). If this is intentional, the spec needs updating. If not, remove it.

---

### `ConfirmRegistration` — Client-Supplied `ConfirmedAt`

`ConfirmRegistrationRequest.ConfirmedAt: DateTimeOffset?` allows clients to supply the confirmation timestamp. This is a system/authority endpoint — the timestamp should be server-generated, not client-provided. Remove `ConfirmedAt`.

---

### `RecordRegistrationSubmission` — Body on System No-Body Endpoint

Spec says this is a system endpoint with no body. Code has `ExternalReference` and `Notes` in the request. If these are genuinely needed, the spec must be updated. Otherwise, remove.

---

## Property Ordering Reference

Spec-prescribed ordering conventions:
- **Create requests:** ID (optional) → required identifying fields → optional descriptive fields
- **Responses:** `id` always first → contextual foreign keys → descriptive fields → status/flags → timestamps last (`createdAt`, `updatedAt`)
- **Bulk requests:** `Items` → `OnError` → `OnDuplicate`
- **Route params in request models:** included at top of class but not serialized from body

Endpoints with notable ordering violations (beyond those already called out above):

| Endpoint | Issue |
|---|---|
| `GetCollectionByIdResponse` | `TenantId, Id, OwnerId` — `TenantId` should not exist; `Id` should be first |
| `GetMediaItemByIdResponse` | `Id, TenantId, OwnerId, MediaProfileId` — `FolderId, CollectionId` should precede `OwnerId` |
| `GetRegistrationByIdResponse` | `Id, TenantId, MediaItemId, OwnerId` — `TenantId` removal fixes ordering |
| `UpdatePinnedRecordTypeVersionRequest` | `ProfileId, NewVersion, RecordTypeId` — `RecordTypeId` should follow `ProfileId` before `NewVersion` |
| `AddAssetDefinitionRequest` | `RoleName` should be first (primary identifier of what's being added) |
