# Handler Status Code Review

_Scope: AssetManagement · Catalog · ChangeRequests · Metadata · Registration_
_Reviewed: 2026-07-13_
_Reviewer: Claude (automated audit — every handler and endpoint read)_

---

## Purpose

Exhaustive audit of every command handler and its corresponding endpoint across all five modules. Four finding categories:

- **WRONG TYPE** — incorrect `DomainErrors.*` helper used (emits the wrong HTTP status for the semantic).
- **UNDECLARED** — the handler can emit a status code absent from the endpoint's `ProducesProblem(N)` list.
- **STALE** — the endpoint declares `ProducesProblem(N)` for a code no handler path can actually produce.
- **RESPONSE CODE MISMATCH** — the send method used in the endpoint emits a different HTTP status than what `Produces(N)` declares.

Handlers/endpoints with no findings of any category are marked **CLEAN**.

System-only handlers (no HTTP endpoint) are noted as such and excluded from endpoint analysis.

### SDK error-type → HTTP mapping (from `ErrorType.cs`)

| Helper | HTTP |
|---|---|
| `InvalidOperation` | **422** |
| `EntityAlreadyExists` | **409** |
| `ResourceNotFound` | **404** |
| `ValidationFailure` | **400** |
| `ConcurrencyViolation` | **409** |
| `VersionMismatch` | **409** |
| `Forbidden` | **403** |
| `Unauthorized` | **401** |
| `ExternalServiceUnavailable` | **503** |
| `Unexpected` | **500** |
| `PersistenceFailure` | **500** |
| `MappingFailure` | **500** |
| `Timeout` | **504** |

---

## Summary table

| Module | Handler / Endpoint | Category | Detail |
|---|---|---|---|
| AssetManagement | AbortAssetMultipartUpload | UNDECLARED 422 | Handler emits InvalidOperation → 422; endpoint missing ProducesProblem(422) |
| AssetManagement | AbortAssetMultipartUpload | STALE 409 | No handler path emits EntityAlreadyExists/ConcurrencyViolation |
| AssetManagement | AbortAssetMultipartUploadEndpoint | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendOkAsync → sends 200 |
| AssetManagement | ArchiveAsset | UNDECLARED 404 | Handler emits ResourceNotFound; endpoint missing ProducesProblem(404) |
| AssetManagement | BulkInitiateAssetUpload | WRONG TYPE | Quota uses InvalidOperation → 422; endpoint declares ProducesProblem(413) |
| AssetManagement | BulkInitiateAssetUpload | UNDECLARED 422 | Quota path emits 422; no ProducesProblem(422) |
| AssetManagement | BulkInitiateAssetUpload | STALE 413 | No SDK helper maps to 413; never emitted |
| AssetManagement | CompleteMultipartUpload | STALE 409 | All state violations use InvalidOperation → 422 |
| AssetManagement | ConfirmAssetUpload | UNDECLARED 404 | Handler emits ResourceNotFound; endpoint missing ProducesProblem(404) |
| AssetManagement | ConfirmAssetUpload | STALE 409 | No 409-producing helper reachable |
| AssetManagement | DeleteAsset | UNDECLARED 422 | Profile-default guard returns InvalidOperation → 422; not declared |
| AssetManagement | InitiateAssetMultipartUpload | UNDECLARED 422 | Multiple InvalidOperation paths; no ProducesProblem(422) |
| AssetManagement | InitiateAssetMultipartUpload | STALE 409 | MediaItem-archived path uses InvalidOperation → 422 |
| AssetManagement | InitiateAssetMultipartUpload | STALE 413 | No SDK helper maps to 413 |
| AssetManagement | InitiateAssetUpload | UNDECLARED 404 | MediaItem not found → ResourceNotFound; not declared |
| AssetManagement | InitiateAssetUpload | UNDECLARED 422 | Archived/quota paths emit InvalidOperation → 422; not declared |
| AssetManagement | TagAsset | UNDECLARED 422 | Aggregate state violations → InvalidOperation → 422; not declared |
| AssetManagement | TagAsset | STALE 409 | Summary says 409 for not-Active; actual code is InvalidOperation → 422 |
| Catalog | ArchiveCollectionEndpoint | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Catalog | ArchiveCollection | UNDECLARED 422 | Aggregate state violations → InvalidOperation → 422; endpoint missing 422 |
| Catalog | ArchiveCollection | STALE 409 | No 409-producing helper reachable |
| Catalog | BulkCreateFoldersByPath | WRONG TYPE | NameReservationConflictException caught → ExternalServiceUnavailable (503); should be EntityAlreadyExists (409) |
| Catalog | CreateCollection | WRONG TYPE | Name conflict uses InvalidOperation → 422; should be EntityAlreadyExists → 409 |
| Catalog | CreateCollection | UNDECLARED 422 | Name conflict emits 422; not declared |
| Catalog | CreateCollection | STALE 404 | No handler path returns ResourceNotFound |
| Catalog | CreateFolder | WRONG TYPE | Name conflict uses InvalidOperation → 422; should be EntityAlreadyExists → 409 |
| Catalog | CreateFolder | UNDECLARED 422 | Name conflict + depth exceeded emit 422; not declared |
| Catalog | CreateFolder | UNDECLARED 503 | Lock unavailable → ExternalServiceUnavailable → 503; not declared |
| Catalog | MoveFolder | WRONG TYPE | Name conflict in destination uses InvalidOperation → 422 |
| Catalog | MoveFolder | UNDECLARED 422 | Multiple InvalidOperation paths; no ProducesProblem(422) |
| Catalog | MoveFolder | STALE 409 | MoveFolderEndpoint declares 409; all state violations emit 422 |
| Catalog | PatchCollection (via RenameCollection) | WRONG TYPE | Name conflict uses InvalidOperation → 422 |
| Catalog | PatchCollection | UNDECLARED 422 | Name conflict + aggregate errors emit 422; not declared |
| Catalog | PatchFolder (via RenameFolder) | WRONG TYPE | Name conflict uses InvalidOperation → 422 |
| Catalog | PatchFolder | UNDECLARED 422 | Name conflict + aggregate errors emit 422; not declared |
| Catalog | RenameCollection | WRONG TYPE | Name conflict uses InvalidOperation × 2 (pre-check + exception catch) |
| Catalog | RenameFolder | WRONG TYPE | Name conflict uses InvalidOperation × 2 |
| Catalog | SetDefaultMediaProfile | UNDECLARED 422 | Profile not published → InvalidOperation → 422; endpoint missing 422 |
| Catalog | SetFolderMetadataBatch | WRONG TYPE | Input parse error → InvalidOperation → 422; should be ValidationFailure → 400 |
| Catalog | SetFolderMetadataField | WRONG TYPE | Input parse error → InvalidOperation → 422; should be ValidationFailure → 400 |
| Catalog | ArchiveFolder | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Catalog | ArchiveFolder | UNDECLARED 422 | Active-registrations guard → InvalidOperation → 422; not declared |
| Catalog | BulkCreateFolders | UNDECLARED 503 | Lock unavailable → ExternalServiceUnavailable → 503; not declared |
| Catalog | CloseFolder | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Catalog | CommitFolderMetadata | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Catalog | ApproveReview | UNDECLARED 422 | Virus-detected asset → InvalidOperation → 422; ApproveMediaItemEndpoint missing 422 |
| Catalog | ArchiveMediaItem | UNDECLARED 422 | Aggregate state violations → InvalidOperation → 422; ArchiveMediaItemEndpoint missing 422 |
| Catalog | AssignAssetToRole | WRONG TYPE | Media profile null → InvalidOperation; should be ResourceNotFound |
| Catalog | AssignAssetToRole | WRONG TYPE | Asset null → InvalidOperation; should be ResourceNotFound |
| Catalog | AssignAssetToRole | WRONG TYPE | Role not found → InvalidOperation; should be ResourceNotFound |
| Catalog | AssignAssetToRole | UNDECLARED 422 | All current InvalidOperation paths emit 422; not declared |
| Catalog | AssignAssetToRole | STALE 409 | No 409-producing helper reachable |
| Catalog | AssignMediaItemToFolder | WRONG TYPE | NameReservationConflictException → InvalidOperation; should be EntityAlreadyExists |
| Catalog | AssignOrMoveMediaItemFolder | UNDECLARED 422 | Both inner handlers can emit 422; endpoint declares no 422 |
| Catalog | CreateMediaItem | WRONG TYPE | Profile null → InvalidOperation; should be ResourceNotFound |
| Catalog | CreateMediaItem | WRONG TYPE | Folder null → InvalidOperation; should be ResourceNotFound |
| Catalog | CreateMediaItem | WRONG TYPE | NameReservationConflictException → InvalidOperation; should be EntityAlreadyExists |
| Catalog | CreateMediaItem | UNDECLARED 422 | Multiple InvalidOperation paths; endpoint missing 422 |
| Catalog | CreateMediaItemInFolder | UNDECLARED 422 | Dispatches CreateMediaItemCommand; same issues; endpoint missing 422 |
| Catalog | MoveMediaItem | WRONG TYPE | NameReservationConflictException → InvalidOperation; should be EntityAlreadyExists |
| Catalog | MoveMediaItem | UNDECLARED 422 | Name conflict + aggregate errors emit 422; not declared via AssignOrMoveEndpoint |
| Catalog | PublishMediaItem | WRONG TYPE | Profile not found → InvalidOperation; should be ResourceNotFound |
| Catalog | PublishMediaItem | UNDECLARED 422 | Multiple InvalidOperation paths; endpoint missing 422 |
| Catalog | PublishMediaItem | STALE 409 | No 409-producing helper reachable |
| Catalog | ReplaceAssetInRole | WRONG TYPE | New asset null → InvalidOperation; should be ResourceNotFound |
| Catalog | ReplaceAssetInRole | WRONG TYPE | Profile null → InvalidOperation; should be ResourceNotFound |
| Catalog | ReplaceAssetInRole | UNDECLARED 422 | Multiple InvalidOperation paths; endpoint missing 422 |
| Catalog | ReplaceAssetInRole | STALE 409 | No 409-producing helper reachable |
| Catalog | SetMetadataBatch | WRONG TYPE | Input parse error → InvalidOperation → 422; should be ValidationFailure → 400 |
| Catalog | SetMetadataField | WRONG TYPE | Input parse error → InvalidOperation → 422; should be ValidationFailure → 400 |
| Catalog | UpdateMediaItem (via UpdateMediaItemTitle) | WRONG TYPE | NameReservationConflictException → InvalidOperation; should be EntityAlreadyExists |
| Catalog | UpdateMediaItemEndpoint | UNDECLARED 422 | UpdateMediaItemTitleHandler can emit 422; endpoint missing 422 |
| Catalog | AttachRecordType | WRONG TYPE | Record type version null → InvalidOperation; should be ResourceNotFound |
| Catalog | CreateMediaProfile | WRONG TYPE | NameReservationConflictException → InvalidOperation → 422; should be EntityAlreadyExists → 409 |
| Catalog | CreateMediaProfileEndpoint | STALE 409 | Handler emits 422 for name conflict; declared 409 is never reached |
| Catalog | DetachRecordType | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Catalog | DiscardMediaProfileDraft | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendOkAsync → sends 200 |
| Catalog | PublishMediaProfile | WRONG TYPE | Name conflict → InvalidOperation; should be EntityAlreadyExists |
| Catalog | PublishMediaProfile | WRONG TYPE | Record type version null → InvalidOperation; should be ResourceNotFound |
| Catalog | PublishMediaProfile | STALE 409 | Handler uses InvalidOperation for "no draft" → 422; declared 409 unreachable |
| Catalog | RemoveAssetDefinition | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendOkAsync → sends 200 |
| Catalog | SetAssetDefinitionDefault | WRONG TYPE | Null asset conflated with wrong-state asset → single InvalidOperation message |
| Catalog | SetAssetDefinitionDefault | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendNoContentAsync → sends 204 |
| Catalog | SetCheckoutPolicy | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendNoContentAsync → sends 204 |
| Catalog | UpdateAssetDefinition | WRONG TYPE | Role not found → InvalidOperation; should be ResourceNotFound |
| Catalog | UpdateAssetDefinition | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendNoContentAsync → sends 204 |
| Catalog | UpdatePinnedRecordTypeVersion | WRONG TYPE | Record type version null → InvalidOperation; should be ResourceNotFound |
| ChangeRequests | DeleteComment | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Metadata | CreateRecordTypeDraft | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendNoContentAsync → sends 204 |
| Metadata | DiscardRecordTypeDraft | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendOkAsync → sends 200 |
| Metadata | RemoveCapabilityFromRecordType | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Metadata | RemoveFieldFromRecordType | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendOkAsync → sends 200 |
| Metadata | ReorderFieldsInRecordType | RESPONSE CODE MISMATCH | Declares Produces(202) but calls SendNoContentAsync → sends 204 |
| Registration | AttachMediaItemToRegistration | WRONG TYPE | Media item null → InvalidOperation; should be ResourceNotFound |
| Registration | CancelRegistration | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Registration | CancelRegistration | UNDECLARED 422 | Aggregate state violations → InvalidOperation → 422; endpoint missing 422 |
| Registration | InitiateRegistration | WRONG TYPE | Media item null → InvalidOperation; should be ResourceNotFound |
| Registration | InitiateRegistration | UNDECLARED 422 | Not-published / no-capability paths emit 422; endpoint missing 422 |
| Registration | RejectAmendment | UNDECLARED 422 | Aggregate state violations → InvalidOperation → 422; endpoint missing 422 |
| Registration | RequestAmendment | WRONG TYPE | Media item null → InvalidOperation; should be ResourceNotFound |
| Registration | ResubmitRegistration | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |
| Registration | SubmitRegistration | RESPONSE CODE MISMATCH | Declares Produces(204) but calls SendOkAsync → sends 200 |

---

## AssetManagement

### AbortAssetMultipartUploadHandler

Route: `DELETE /v1/assets/{assetId}/parts`
Endpoint declares: 202, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Handler returns `InvalidOperation` for "asset is not pending multipart" → 422. No `ProducesProblem(422)`. |
| 2 | STALE 409 | No handler path reaches `EntityAlreadyExists` or `ConcurrencyViolation`. All state violations use `InvalidOperation` → 422. |
| 3 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendOkAsync` → actual response is HTTP 200. |

### ActivateDocumentAssetHandler

System-only (no HTTP endpoint). CLEAN.

### ArchiveAssetHandler

Route: `POST /v1/assets/{assetId}/archive`
Endpoint declares: 204, 400, 401, 403, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 404 | Handler returns `ResourceNotFound` when asset lookup fails → 404. `ProducesProblem(404)` is missing. |

### AttachAssetToMediaItemHandler

System-only. CLEAN.

### BulkConfirmAssetUploadHandler

Route: `POST /v1/assets/confirm/bulk`

CLEAN — handler-level errors are `BulkOperationResult`; no `IDomainError` propagates to the endpoint.

### BulkInitiateAssetUploadHandler

Route: `POST /v1/assets/upload/bulk`
Endpoint declares: 201, 202, 400, 401, 403, 413

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Quota exceeded returns `InvalidOperation("QuotaExceeded: ...")` → 422. Error catalog lists `StorageQuotaExceeded` → 413, but no SDK helper maps to 413. The handler emits 422. |
| 2 | UNDECLARED 422 | Quota path emits `InvalidOperation` → 422. No `ProducesProblem(422)`. |
| 3 | STALE 413 | `ProducesProblem(413)` declared. No SDK helper produces 413; never emitted. |

### CompleteAssetProcessingHandler / FailAssetProcessingHandler / StartAssetProcessingHandler

System-only. CLEAN.

### CompleteMultipartUploadHandler

Route: `POST /v1/assets/{assetId}/parts/complete`
Endpoint declares: 202, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | STALE 409 | All state violations in handler ("asset is not pending multipart", "file size exceeded") use `InvalidOperation` → 422. No `EntityAlreadyExists` or `ConcurrencyViolation` path exists. `ProducesProblem(409)` is unreachable. |

### ConfirmAssetUploadHandler

Route: `POST /v1/assets/{assetId}/confirm`
Endpoint declares: 202, 400, 401, 403, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 404 | Handler returns `ResourceNotFound` when asset is not found → 404. `ProducesProblem(404)` is missing. |
| 2 | STALE 409 | All handler state violations use `ValidationFailure` (→ 400) or `InvalidOperation` (→ 422). No 409-producing helper is reachable. |

### DeleteAssetHandler

Route: `DELETE /v1/assets/{assetId}`
Endpoint declares: 204, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Handler returns `InvalidOperation("Asset cannot be deleted because it is the default asset for a media profile.")` → 422. `ProducesProblem(422)` is missing. |

### DetachAssetFromMediaItemHandler / PromoteAssetToVersionArtifactHandler / RecordStorageTierTransitionHandler / RecordValidationResultHandler / ReleaseVersionArtifactHandler

System-only. CLEAN.

### InitiateAssetMultipartUploadHandler

Route: `POST /v1/assets/{assetId}/parts`
Endpoint declares: 202, 400, 401, 403, 404, 409, 413

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Handler returns `InvalidOperation` → 422 for: media item archived, quota exceeded, part count validation. No `ProducesProblem(422)`. |
| 2 | STALE 409 | "Media item archived" path uses `InvalidOperation` → 422, not any 409-producing helper. `ProducesProblem(409)` is unreachable. |
| 3 | STALE 413 | `ProducesProblem(413)` declared. Quota uses `InvalidOperation` → 422; 413 is never emitted. |

### InitiateAssetUploadHandler

Route: `POST /v1/assets/upload`
Endpoint declares: 202, 400, 401, 403

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 404 | Handler returns `ResourceNotFound` when the referenced media item is not found → 404. Not declared. |
| 2 | UNDECLARED 422 | Handler returns `InvalidOperation` → 422 for: media item archived, quota exceeded. Not declared. |

### TagAssetHandler

Route: `PUT /v1/assets/{assetId}/tags`
Endpoint declares: 200, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Aggregate state violations (e.g. tagging a non-Active asset) propagate as `InvalidOperation` → 422. `ProducesProblem(422)` is missing. |
| 2 | STALE 409 | Endpoint summary says "409 — asset not in Active status". That state violation comes from the aggregate as `InvalidOperation` → 422. No 409-producing helper is reachable. |

---

## Catalog — Collections

### ArchiveCollectionHandler

Route: `POST /v1/collections/{collectionId}/archive`
Endpoint declares: 204, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |
| 2 | UNDECLARED 422 | Aggregate state violations propagate as `InvalidOperation` → 422. `ProducesProblem(422)` is missing. |
| 3 | STALE 409 | All state violations use `InvalidOperation` → 422. No 409-producing helper is reachable. |

### BulkCreateCollectionsHandler

Route: `POST /v1/collections/bulk`

CLEAN — handler returns `BulkOperationResult`; no handler-level `IDomainError` propagates.

### CreateCollectionHandler

Route: `POST /v1/collections`
Endpoint declares: 201, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Pre-check `IsNameAvailableAsync` failure returns `InvalidOperation("Collection name is already in use.")` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |
| 3 | UNDECLARED 422 | Both name-conflict paths emit 422. No `ProducesProblem(422)`. |
| 4 | STALE 404 | No handler path returns `ResourceNotFound`. No entity lookup that can fail. `ProducesProblem(404)` is unreachable. |

_Note: After fixing to `EntityAlreadyExists`, endpoint should declare `ProducesProblem(409)` and remove the stale `ProducesProblem(404)`._

### RenameCollectionHandler (dispatched by PatchCollectionEndpoint)

Route: `PATCH /v1/collections/{collectionId}`
Endpoint declares: 204, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Pre-check returns `InvalidOperation("Collection name is already in use.")` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |
| 3 | UNDECLARED 422 | Both name-conflict paths (+ aggregate state violations) emit 422. `PatchCollectionEndpoint` has no `ProducesProblem(422)`. |

### SetCollectionVisibilityHandler / TagCollectionHandler / UpdateCollectionDescriptionHandler

CLEAN.

### SetDefaultMediaProfileHandler

Route: `PUT /v1/collections/{collectionId}/default-profile`
Endpoint declares: 204, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Handler returns `InvalidOperation("Media profile is not published.")` → 422. No `ProducesProblem(422)`. |

---

## Catalog — Folders

### ArchiveFolderHandler

Route: `POST /v1/folders/{folderId}/archive`
Endpoint declares: 204, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |
| 2 | UNDECLARED 422 | Handler returns `InvalidOperation` → 422 for "folder has active registrations". No `ProducesProblem(422)`. |

### BulkCreateFoldersHandler

Route: `POST /v1/collections/{collectionId}/folders/bulk`
Endpoint declares: 201, 202, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 503 | Handler returns `ExternalServiceUnavailable` → 503 when the distributed folder-creation lock is unavailable. No `ProducesProblem(503)`. |

### BulkCreateFoldersByPathHandler

Route: `POST /v1/collections/{collectionId}/folders/by-path` (and auto variant)
Endpoint declares: 201, 202, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `NameReservationConflictException` caught inside bulk loop → returned as `ExternalServiceUnavailable` → 503. A name conflict is not a service-availability failure. Should be `EntityAlreadyExists` → 409 (or a per-item `BulkItemError`). |

### CloseFolderHandler

Route: `POST /v1/folders/{folderId}/close`
Endpoint declares: 204, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |

### CommitFolderMetadataHandler

Route: `POST /v1/folders/{folderId}/metadata/commit`
Endpoint declares: 204, 400, 401, 403, 404, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |

### CreateFolderHandler

Route: `POST /v1/collections/{collectionId}/folders`
Endpoint declares: 201, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `IsNameAvailableAsync` failure returns `InvalidOperation("A folder with this name already exists.")` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |
| 3 | UNDECLARED 422 | Name conflict and depth-exceeded both emit `InvalidOperation` → 422. No `ProducesProblem(422)`. |
| 4 | UNDECLARED 503 | Handler returns `ExternalServiceUnavailable` → 503 when the distributed lock is unavailable. No `ProducesProblem(503)`. |

### MoveFolderHandler

Route: `PUT /v1/folders/{folderId}/parent`
Endpoint declares: 204, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Name-availability check and `NameReservationConflictException` catch both return `InvalidOperation("A folder with this name already exists in the destination.")` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | UNDECLARED 422 | Name conflict and aggregate state violations emit `InvalidOperation` → 422. No `ProducesProblem(422)`. |
| 3 | STALE 409 | `ProducesProblem(409)` declared. All state violations use `InvalidOperation` → 422. No 409-producing helper is reachable. |

### PatchFolderEndpoint (dispatches RenameFolderCommand)

Route: `PATCH /v1/folders/{folderId}`
Endpoint declares: 204, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | `RenameFolderHandler` can emit `InvalidOperation` → 422 from name conflict (WRONG TYPE) and aggregate state violations. No `ProducesProblem(422)`. |

### RenameFolderHandler (dispatched by PatchFolderEndpoint)

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Pre-check returns `InvalidOperation("A folder with this name already exists.")` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |

### SetFolderMetadataBatchHandler

Route: `PUT /v1/folders/{folderId}/metadata`
Endpoint declares: 204, 400, 401, 403, 404, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Internal `InvalidOperationException` from metadata field parsing caught → returned as `InvalidOperation(...)` → 422. These are input field type/format errors — client input validation failures — and should be `ValidationFailure` → 400. Endpoint declares 422 but the semantic is wrong. |

### SetFolderMetadataFieldHandler

Route: `PUT /v1/folders/{folderId}/metadata/{fieldName}`
Endpoint declares: 204, 400, 401, 403, 404, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Same pattern as `SetFolderMetadataBatchHandler`. Internal `InvalidOperationException` from field parsing returned as `InvalidOperation` → 422 instead of `ValidationFailure` → 400. |

### UpdateFolderDescriptionHandler

CLEAN.

---

## Catalog — MediaItems

### AddRegistrationRefHandler / BeginRevisionHandler / DeleteMediaItemHandler / DiscardRevisionHandler / LinkSigningSessionHandler / PurgeMediaItemVersionHandler / RejectMediaItemHandler / RejectReviewHandler / RemoveRegistrationRefHandler / TagMediaItemHandler / UnassignAssetFromRoleHandler / UnlinkSigningSessionHandler / UpdateMediaItemConformanceStatusHandler / UpdateMediaItemDescriptionHandler / WithdrawMediaItemHandler

CLEAN.

### ApproveReviewHandler

Route: `POST /v1/items/{itemId}/review/approve`
Endpoint declares: 204, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Handler returns `InvalidOperation` → 422 for "asset is virus-detected". `ApproveMediaItemEndpoint` has no `ProducesProblem(422)`. |

### ArchiveMediaItemHandler

Route: `POST /v1/items/{itemId}/archive`
Endpoint declares: 204, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Aggregate state violations from `MediaItem.Archive()` propagate as `InvalidOperation` → 422. `ArchiveMediaItemEndpoint` has no `ProducesProblem(422)`. |

### AssignAssetToRoleHandler

Route: `PUT /v1/items/{itemId}/roles/{roleName}`
Endpoint declares: 204, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Media profile not found.")` when profile lookup returns null → 422. Should be `ResourceNotFound` → 404. |
| 2 | WRONG TYPE | `InvalidOperation("Asset not found.")` when asset lookup returns null → 422. Should be `ResourceNotFound` → 404. |
| 3 | WRONG TYPE | `InvalidOperation("Asset role not found.")` when the role name does not exist on the profile → 422. Should be `ResourceNotFound` → 404. |
| 4 | UNDECLARED 422 | All current `InvalidOperation` paths (including WRONG TYPE cases above, plus: profile not published, content type not accepted, role already filled) emit 422. No `ProducesProblem(422)`. |
| 5 | STALE 409 | `ProducesProblem(409)` declared. No handler path uses a 409-producing helper. |

### AssignMediaItemToFolderHandler (dispatched by AssignOrMoveMediaItemFolderEndpoint)

Route: `PUT /v1/items/{itemId}/folder`
Endpoint declares: 204, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | UNDECLARED 422 | Name conflict + aggregate state violations emit `InvalidOperation` → 422. `AssignOrMoveMediaItemFolderEndpoint` has no `ProducesProblem(422)`. |

### AssignOrMoveMediaItemFolderEndpoint

Route: `PUT /v1/items/{itemId}/folder`
Endpoint declares: 204, 400, 401, 403, 404

_Note: This endpoint dispatches `AssignMediaItemToFolderCommand` and, if that returns an `InvalidOperation` (422), dispatches `MoveMediaItemCommand` instead, treating 422 as the "already assigned" sentinel. Other 422 errors from either inner handler also propagate._

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Both inner handlers can emit non-sentinel `InvalidOperation` → 422 errors (aggregate state violations, name conflicts on move). These propagate to the caller. No `ProducesProblem(422)`. |

### BulkCreateMediaItemsHandler

Route: `POST /v1/items/bulk`

CLEAN — per-item errors are `BulkItemError`; no `IDomainError` propagates to the endpoint level.

### BulkSetMetadataHandler

Route: `PATCH /v1/items/bulk/metadata`

CLEAN — per-item errors captured as `BulkItemError`. Internal `InvalidOperationException` from metadata parsing is added as a per-item error, not a handler-level domain error.

### CreateMediaItemHandler

Route: `POST /v1/items`
Endpoint declares: 201, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Media profile not found.")` when profile is null → 422. Should be `ResourceNotFound` → 404. |
| 2 | WRONG TYPE | `InvalidOperation("Folder not found.")` when folder lookup returns null → 422. Should be `ResourceNotFound` → 404. |
| 3 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |
| 4 | UNDECLARED 422 | All `InvalidOperation` paths (WRONG TYPE cases above + "profile not published" guard) emit 422. No `ProducesProblem(422)`. |

### CreateMediaItemInFolderEndpoint

Route: `POST /v1/folders/{folderId}/items`
Endpoint declares: 201, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Dispatches `CreateMediaItemCommand`. All `InvalidOperation` paths from that handler emit 422. No `ProducesProblem(422)`. |

### MoveMediaItemHandler (dispatched by AssignOrMoveMediaItemFolderEndpoint)

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | UNDECLARED 422 | Name conflict + aggregate state violations emit `InvalidOperation` → 422. Not declared on the endpoint. |

### PublishMediaItemHandler

Route: `POST /v1/items/{itemId}/publish`
Endpoint declares: 202, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Media profile not found or not published.")` — the null case (profile doesn't exist) should be `ResourceNotFound` → 404. The not-published case is legitimately `InvalidOperation` → 422. These two conditions are conflated in one message. |
| 2 | UNDECLARED 422 | Multiple `InvalidOperation` → 422 paths: profile issues, missing required roles, assets not ready. No `ProducesProblem(422)`. |
| 3 | STALE 409 | `ProducesProblem(409)` declared. All state violations use `InvalidOperation` → 422. No 409-producing helper is reachable. |

### ReplaceAssetInRoleHandler

Route: `PUT /v1/items/{itemId}/roles/{roleName}/asset`
Endpoint declares: 204, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("New asset not found.")` when new asset lookup returns null → 422. Should be `ResourceNotFound` → 404. |
| 2 | WRONG TYPE | `InvalidOperation("Media profile not found or not published.")` — the null case should be `ResourceNotFound` → 404. |
| 3 | UNDECLARED 422 | All `InvalidOperation` paths (WRONG TYPE cases + content type mismatch, role not found, asset not Active, asset archived, asset already in role) emit 422. No `ProducesProblem(422)`. |
| 4 | STALE 409 | `ProducesProblem(409)` declared. No handler path uses a 409-producing helper. |

### SetMetadataBatchHandler

Route: `PUT /v1/items/{itemId}/metadata`
Endpoint declares: 204, 400, 401, 403, 404, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Internal `InvalidOperationException` from metadata field parsing caught → returned as `InvalidOperation` → 422. Input field type/format errors are client-side validation failures and should be `ValidationFailure` → 400. |

### SetMetadataFieldHandler

Route: `PUT /v1/items/{itemId}/metadata/{fieldName}`
Endpoint declares: 204, 400, 401, 403, 404, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Same as `SetMetadataBatchHandler`. Internal `InvalidOperationException` from field parsing returned as `InvalidOperation` → 422 instead of `ValidationFailure` → 400. |

### UpdateMediaItemTitleHandler (dispatched by UpdateMediaItemEndpoint)

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |

### UpdateMediaItemEndpoint

Route: `PATCH /v1/items/{itemId}`
Endpoint declares: 204, 400, 401, 403, 404

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Dispatches `UpdateMediaItemTitleCommand`. Handler can return `InvalidOperation` → 422 from name conflict and aggregate state violations. No `ProducesProblem(422)`. |

---

## Catalog — MediaProfiles

### AddAssetDefinitionHandler

Route: `POST /v1/profiles/{profileId}/asset-definitions`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN.

### AttachRecordTypeHandler

Route: `POST /v1/profiles/{profileId}/record-types`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Record type version not found.")` when the record type version lookup returns null → 422. Should be `ResourceNotFound` → 404. Endpoint already declares 404, so the fix is handler-only; the wrong-type means a 404 situation emits 422. |

### CreateMediaProfileHandler

Route: `POST /v1/profiles`
Endpoint declares: 201, 400, 401, 403, 409

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | STALE 409 | Endpoint declares `ProducesProblem(409)` (intended for name conflict), but handler currently emits 422 for that case. The 409 declaration is the correct intended code; the handler implementation is the bug. |

### CreateMediaProfileRevisionHandler / DeprecateMediaProfileHandler / DiscardMediaProfileDraftHandler / RemoveAssetDefinitionHandler / ReorderAssetDefinitionsHandler / SetAutoSubmitOnCompleteHandler / SetCapabilitiesHandler / SetCheckoutPolicyHandler / SetReviewPolicyHandler

CLEAN at handler level. See endpoint-level response code mismatches below for some of these.

### DetachRecordTypeEndpoint

Route: `DELETE /v1/profiles/{profileId}/record-types/{recordTypeId}`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |

### DiscardMediaProfileDraftEndpoint

Route: `DELETE /v1/profiles/{profileId}/draft`
Endpoint declares: 202, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendOkAsync` → sends HTTP 200. |

### PublishMediaProfileHandler

Route: `POST /v1/profiles/{profileId}/publish`
Endpoint declares: 200, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Name-availability check returns `InvalidOperation("...name is already in use...")` → 422. Should be `EntityAlreadyExists` → 409. |
| 2 | WRONG TYPE | `NameReservationConflictException` catch returns `InvalidOperation(...)` → 422. Should be `EntityAlreadyExists` → 409. |
| 3 | WRONG TYPE | `InvalidOperation("Record type version not found.")` when record type version lookup returns null → 422. Should be `ResourceNotFound` → 404. |
| 4 | STALE 409 | Endpoint declares `ProducesProblem(409)` for "No draft exists to publish". Handler uses `InvalidOperation` (→ 422) for that case. The intended 409 is the correct semantic but the implementation is wrong. |

### RemoveAssetDefinitionEndpoint

Route: `DELETE /v1/profiles/{profileId}/asset-definitions/{roleName}`
Endpoint declares: 202, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendOkAsync` → sends HTTP 200. |

### SetAssetDefinitionDefaultHandler

Route: `POST /v1/profiles/{profileId}/asset-definitions/{roleName}/default`
Endpoint declares: 202, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | Handler returns `InvalidOperation("Asset must be Active.")` both when the asset lookup returns null AND when the asset exists but is in the wrong status. The null case conflates "not found" with "wrong state" in a single message and error type. The not-found case should return `ResourceNotFound` → 404. |

### SetAssetDefinitionDefaultEndpoint

Route: `POST /v1/profiles/{profileId}/asset-definitions/{roleName}/default`

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendNoContentAsync` → sends HTTP 204. |

### SetCheckoutPolicyEndpoint

Route: `POST /v1/profiles/{profileId}/checkout-policy`

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendNoContentAsync` → sends HTTP 204. |

### UpdateAssetDefinitionHandler

Route: `PUT /v1/profiles/{profileId}/asset-definitions/{roleName}`
Endpoint declares: 202, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Role not found.")` when the asset role lookup fails → 422. Should be `ResourceNotFound` → 404. Endpoint already declares 404; this is a handler-only fix. |

### UpdateAssetDefinitionEndpoint

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendNoContentAsync` → sends HTTP 204. |

### UpdatePinnedRecordTypeVersionHandler

Route: `PATCH /v1/profiles/{profileId}/record-types/{recordTypeId}/version`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Record type version not found.")` when record type version lookup returns null → 422. Should be `ResourceNotFound` → 404. Endpoint already declares 404; this is a handler-only fix. |

---

## ChangeRequests

### AddCommentHandler / EditCommentHandler

CLEAN.

### CreateChangeRequestHandler

System-only. CLEAN.

### DeleteCommentHandler

Route: `DELETE /v1/change-requests/{changeRequestId}/comments/{commentId}`
Endpoint declares: 204, 400, 401, 403, 404, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |

---

## Metadata

### AddCapabilityToRecordTypeHandler

Route: `POST /v1/record-types/{recordTypeId}/capabilities`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN. Handler correctly uses `ResourceNotFound` for missing record type. Aggregate errors propagate.

### AddFieldToRecordTypeHandler

Route: `POST /v1/record-types/{recordTypeId}/fields`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN. `constraintValidator.Validate` returns a Result failure; both 400 and 422 are declared.

### CreateRecordTypeHandler

Route: `POST /v1/record-types`
Endpoint declares: 201, 400, 401, 403, 409

CLEAN. Correctly uses `EntityAlreadyExists` for both the pre-check and `NameReservationConflictException` catch. Reference implementation for name-conflict handling.

### CreateRecordTypeDraftHandler

Route: `POST /v1/record-types/{recordTypeId}/draft`
Endpoint declares: 202, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendNoContentAsync` → sends HTTP 204. |

### DeprecateFieldInRecordTypeHandler

Route: `POST /v1/record-types/{recordTypeId}/draft/fields/{fieldName}/deprecate`
Endpoint declares: 204, 400, 401, 403, 404, 409

CLEAN.

### DeprecateRecordTypeHandler

Route: `POST /v1/record-types/{recordTypeId}/deprecate`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN. Handler correctly uses `ResourceNotFound`. `nameReservationService.ReleaseAsync` unchecked but that is an infrastructure concern outside the domain error contract.

### DiscardRecordTypeDraftHandler

Route: `DELETE /v1/record-types/{recordTypeId}/draft`
Endpoint declares: 202, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendOkAsync` → sends HTTP 200. |

### PublishRecordTypeHandler

Route: `POST /v1/record-types/{recordTypeId}/publish`
Endpoint declares: 200, 400, 401, 403, 404, 409, 422

CLEAN.

### RemoveCapabilityFromRecordTypeHandler

Route: `DELETE /v1/record-types/{recordTypeId}/capabilities/{capabilityType}`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |

### RemoveFieldFromRecordTypeHandler

Route: `DELETE /v1/record-types/{recordTypeId}/fields/{fieldName}`
Endpoint declares: 202, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendOkAsync` → sends HTTP 200. |

### RenameRecordTypeHandler (dispatched by PatchRecordTypeEndpoint)

Route: `PATCH /v1/record-types/{recordTypeId}`
Endpoint declares: 204, 400, 401, 403, 404, 409

CLEAN. Correctly uses `EntityAlreadyExists` for both the pre-check and `NameReservationConflictException` catch. Reference implementation.

### ReorderFieldsInRecordTypeHandler

Route: `POST /v1/record-types/{recordTypeId}/fields/reorder`
Endpoint declares: 202, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(202)` but calls `SendNoContentAsync` → sends HTTP 204. |

### ReplaceFieldInRecordTypeHandler

Route: `PUT /v1/record-types/{recordTypeId}/fields/{fieldName}`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN.

### SetRecordTypeAliasesHandler

Route: `PUT /v1/record-types/{recordTypeId}/aliases`
Endpoint declares: 204, 400, 401, 403, 404, 409

CLEAN. Correctly uses `EntityAlreadyExists` for both pre-check and `NameReservationConflictException` catch.

### UpdateFieldInRecordTypeHandler

Route: `PATCH /v1/record-types/{recordTypeId}/fields/{fieldName}`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN.

### UpdateRecordTypeDescriptionHandler / UpdateRecordTypeDisplayNameHandler

CLEAN.

---

## Registration

### ApproveAmendmentHandler

Route: `POST /v1/registrations/{registrationId}/amendments/{amendmentId}/approve`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN.

### AttachMediaItemToRegistrationHandler

Route: `POST /v1/registrations/{registrationId}/documents`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Media item not found in registration context.")` when `registrationContextService.GetAsync` returns null → 422. Should be `ResourceNotFound` → 404. Endpoint already declares 404; fix is handler-only. After fix, the remaining 422 paths (not published, no capability) are correct. |

### CancelRegistrationHandler

Route: `POST /v1/registrations/{registrationId}/cancel`
Endpoint declares: 204, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |
| 2 | UNDECLARED 422 | Aggregate state violations from `Registration.Cancel()` propagate as `InvalidOperation` → 422. No `ProducesProblem(422)`. |

### ConfirmRegistrationHandler

Route: `POST /v1/registrations/{registrationId}/confirm`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN.

### InitiateRegistrationHandler

Route: `POST /v1/items/{itemId}/registrations`
Endpoint declares: 201, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Media item not found.")` when `registrationContextService.GetAsync` returns null → 422. Should be `ResourceNotFound` → 404. Endpoint already declares 404. |
| 2 | UNDECLARED 422 | Handler returns `InvalidOperation` → 422 for: not published, no registration capability. No `ProducesProblem(422)`. |

### RecordRegistrationSubmissionHandler

Route: `POST /v1/registrations/{registrationId}/submission`
Endpoint declares: 204, 400, 401, 403, 404, 422

CLEAN.

### RejectAmendmentHandler

Route: `POST /v1/registrations/{registrationId}/amendments/{amendmentId}/reject`
Endpoint declares: 204, 400, 401, 403, 404, 409

| # | Category | Detail |
|---|---|---|
| 1 | UNDECLARED 422 | Aggregate state violations from `Registration.RejectAmendment()` propagate as `InvalidOperation` → 422. No `ProducesProblem(422)`. |

### RejectRegistrationHandler

Route: `POST /v1/registrations/{registrationId}/reject`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

CLEAN.

### RequestAmendmentHandler

Route: `POST /v1/registrations/{registrationId}/amendments`
Endpoint declares: 201, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | WRONG TYPE | `InvalidOperation("Media item not found.")` when `registrationContextService.GetAsync` returns null → 422. Should be `ResourceNotFound` → 404. Endpoint already declares 404 and 422; the 422 declaration remains correct for the not-published and no-capability paths. Fix is handler-only. |

### ResubmitRegistrationHandler

Route: `POST /v1/registrations/{registrationId}/resubmit`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |

### SubmitRegistrationHandler

Route: `POST /v1/registrations/{registrationId}/submit`
Endpoint declares: 204, 400, 401, 403, 404, 409, 422

| # | Category | Detail |
|---|---|---|
| 1 | RESPONSE CODE MISMATCH | Endpoint declares `Produces(204)` but calls `SendOkAsync` → sends HTTP 200. |

---

## Error Catalog Discrepancies

File: `docs/spec/shared/error-catalog.md`

### Critical: InvalidOperation documented as HTTP 409

The error catalog (Common section) documents `InvalidOperation → 409 Conflict`. The platform SDK (`ErrorType.cs`) maps `InvalidOperation → 422 Unprocessable Entity`.

This single discrepancy cascades to every downstream catalog entry that documents a state-machine violation code as HTTP 409. The following catalog entries all state HTTP 409 but the actual emitted code is 422:

| Section | errorCode | Catalog | Actual |
|---|---|---|---|
| Common | `InvalidOperation` | 409 | **422** |
| AssetManagement | `AssetNotPending` | 409 | **422** |
| AssetManagement | `AssetNotPendingMultipart` | 409 | **422** |
| AssetManagement | `AssetNotActive` | 409 | **422** |
| AssetManagement | `AssetNotArchivable` | 409 | **422** |
| AssetManagement | `AssetNotArchived` | 409 | **422** |
| AssetManagement | `AssetAlreadyDeleted` | 409 | **422** |
| AssetManagement | `MediaItemArchived` | 409 | **422** |
| AssetManagement | `StorageQuotaExceeded` | 413 | **422** (no SDK helper maps to 413) |
| Catalog Collections | `CollectionAlreadyExists` | 409 | **422** (WRONG TYPE — handler uses InvalidOperation) |
| Catalog Collections | `CollectionAlreadyArchived` | 409 | **422** |
| Catalog Collections | `CollectionArchived` | 409 | **422** |
| Catalog Collections | `DuplicateName` | 409 | **422** (WRONG TYPE) |
| Catalog Folders | `CircularFolderReference` | 409 | **422** |
| Catalog MediaItems | `MediaItemAlreadyExists` | 409 | **422** (WRONG TYPE) |
| Catalog MediaItems | `DuplicateTitle` | 409 | **422** (WRONG TYPE) |
| Catalog MediaItems | `MediaItemCheckedOut` | 409 | **422** |
| Catalog MediaItems | `MediaItemNotCheckedOut` | 409 | **422** |
| Catalog MediaItems | `RoleAssignmentNotFound` | 404 | **422** (WRONG TYPE — handler uses InvalidOperation) |
| ChangeRequests | `ChangeRequestNotOpen` | 409 | **422** |
| ChangeRequests | `ReviewerAlreadyAssigned` | 409 | **422** |
| ChangeRequests | `ReviewerAlreadyDecided` | 409 | **422** |
| ChangeRequests | `ReviewerNotPending` | 409 | **422** |
| Registration | `RegistrationConfirmed` | 409 | **422** |
| Registration | `DuplicatePendingAmendment` | 409 | **422** |
| Registration | `AmendmentNotPending` | 409 | **422** |

`MediaProfileNotPublished → 422` is the one catalog entry that is correct.

**Root cause**: The SDK maps `InvalidOperation` to 422; the catalog was written assuming 409 for state violations. These are two reasonable but conflicting conventions. The SDK is authoritative; the catalog must be updated.

**Recommended fix**: Update `docs/spec/shared/error-catalog.md`:
1. Change `InvalidOperation → 409` to `InvalidOperation → 422` in the Common table.
2. Update all per-code HTTP columns above from 409 → 422 (or 413 → 422 for StorageQuotaExceeded).
3. Entries for `CollectionAlreadyExists`, `DuplicateName`, `MediaItemAlreadyExists`, `DuplicateTitle` should document 409 as the _intended_ code once WRONG TYPE issues are fixed in handlers.

---

## Recommended Fix Priority

### P0 — Breaks API contract (observable by clients today)

**Response code mismatches** (22 instances): Clients observe a different status code than documented. Generated SDK clients with typed error handling break silently.

| Endpoint | Declares | Sends |
|---|---|---|
| AbortAssetMultipartUpload | 202 | 200 |
| ArchiveCollection | 204 | 200 |
| ArchiveFolder | 204 | 200 |
| CloseFolder | 204 | 200 |
| CommitFolderMetadata | 204 | 200 |
| DeleteComment (ChangeRequests) | 204 | 200 |
| DetachRecordType | 204 | 200 |
| DiscardMediaProfileDraft | 202 | 200 |
| RemoveAssetDefinition | 202 | 200 |
| SetAssetDefinitionDefault | 202 | 204 |
| SetCheckoutPolicy | 202 | 204 |
| UpdateAssetDefinition | 202 | 204 |
| CreateRecordTypeDraft | 202 | 204 |
| DiscardRecordTypeDraft | 202 | 200 |
| RemoveCapabilityFromRecordType | 204 | 200 |
| RemoveFieldFromRecordType | 202 | 200 |
| ReorderFieldsInRecordType | 202 | 204 |
| CancelRegistration | 204 | 200 |
| ResubmitRegistration | 204 | 200 |
| SubmitRegistration | 204 | 200 |

**Undeclared 422** (widespread): OpenAPI spec is missing the 422 response model on many endpoints. Generated clients have no error model for it. API gateways may reject undeclared codes. Endpoints with missing `ProducesProblem(422)`:

`AbortAssetMultipartUpload`, `ArchiveAsset`, `BulkInitiateAssetUpload`, `DeleteAsset`, `InitiateAssetMultipartUpload`, `InitiateAssetUpload`, `TagAsset`, `ArchiveCollection`, `PatchCollection`, `SetDefaultMediaProfile`, `ArchiveFolder`, `BulkCreateFolders`, `CreateFolder`, `MoveFolder`, `PatchFolder`, `ApproveReview`, `ArchiveMediaItem`, `AssignAssetToRole`, `AssignOrMoveMediaItemFolder`, `CreateMediaItem`, `CreateMediaItemInFolder`, `PublishMediaItem`, `ReplaceAssetInRole`, `UpdateMediaItem`, `CancelRegistration`, `InitiateRegistration`, `RejectAmendment`

### P1 — Wrong semantic type (callers cannot distinguish error classes)

**WRONG TYPE: "not found" cases using InvalidOperation → 422 instead of ResourceNotFound → 404**:
- `AssignAssetToRoleHandler`: profile null, asset null, role null
- `PublishMediaItemHandler`: profile null
- `ReplaceAssetInRoleHandler`: asset null, profile null
- `CreateMediaItemHandler`: profile null, folder null
- `AttachRecordTypeHandler`: record type version null
- `UpdateAssetDefinitionHandler`: role null
- `UpdatePinnedRecordTypeVersionHandler`: record type version null
- `PublishMediaProfileHandler`: record type version null
- `SetAssetDefinitionDefaultHandler`: asset null (conflated with wrong-state)
- `InitiateRegistrationHandler`: media item null
- `AttachMediaItemToRegistrationHandler`: media item null
- `RequestAmendmentHandler`: media item null

Fix: replace `InvalidOperation("X not found.")` with `ResourceNotFound("X not found.")` in each case.

**WRONG TYPE: name-conflict cases using InvalidOperation → 422 instead of EntityAlreadyExists → 409**:
- `CreateCollectionHandler` (×2)
- `RenameCollectionHandler` (×2)
- `CreateFolderHandler` (×2)
- `RenameFolderHandler` (×2)
- `MoveFolderHandler` (×1 or ×2)
- `AssignMediaItemToFolderHandler` (×1)
- `MoveMediaItemHandler` (×1)
- `UpdateMediaItemTitleHandler` (×1)
- `CreateMediaItemHandler` (×1)
- `CreateMediaProfileHandler` (×1)
- `PublishMediaProfileHandler` (×2)

Reference: `CreateRecordTypeHandler`, `RenameRecordTypeHandler`, `SetRecordTypeAliasesHandler` in Metadata — all use `EntityAlreadyExists` correctly.

**WRONG TYPE: `BulkCreateFoldersByPathHandler`**: `NameReservationConflictException` mapped to `ExternalServiceUnavailable` → 503. Should be `EntityAlreadyExists` → 409 (or per-item `BulkItemError`).

**WRONG TYPE: metadata parse errors**: `SetFolderMetadataBatch`, `SetFolderMetadataField`, `SetMetadataBatch`, `SetMetadataField` — internal `InvalidOperationException` caught and returned as `InvalidOperation` → 422 instead of `ValidationFailure` → 400.

### P2 — Stale declarations (incorrect OpenAPI documentation)

Remove `ProducesProblem(409)` from: `AbortAssetMultipartUpload`, `CompleteMultipartUpload`, `ConfirmAssetUpload`, `TagAsset`, `ArchiveCollection`, `MoveFolder`, `AssignAssetToRole`, `PublishMediaItem`, `ReplaceAssetInRole`.

Remove `ProducesProblem(413)` from: `BulkInitiateAssetUpload`, `InitiateAssetMultipartUpload`.

Remove `ProducesProblem(404)` from: `CreateCollection` (no entity lookup can fail).

### P3 — Error catalog update (documentation)

Update `docs/spec/shared/error-catalog.md`:
1. `InvalidOperation → 422` (not 409) in the Common table.
2. All state-violation codes in per-module tables: 409 → 422.
3. `StorageQuotaExceeded`: 413 → 422 (no 413 SDK helper exists).
4. `RoleAssignmentNotFound`: mark as WRONG TYPE in handlers — intended 404, currently emits 422.
