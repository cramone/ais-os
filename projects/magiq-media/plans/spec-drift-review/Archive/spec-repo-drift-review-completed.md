# Spec ↔ Repo Drift Review — completed findings

_magiq-media · original review 2026-08-21 · **archived 2026-08-24**_

This is the closed half of the drift review. Open findings live in
[`../spec-repo-drift-review.md`](../spec-repo-drift-review.md); nothing was deleted in the split, so every
row of the original document is in exactly one of the two files.

**149 findings resolved** (147 fixed, 2 deliberately skipped) of the 208 distinct findings carried. What's
here:

- Every `☑` and `⊘` row, in its original section, with the resolution notes written when it closed.
- The sections that closed **completely** — C.1–C.5 (Catalog cross-cutting, Collection, Folder, MediaItem,
  MediaProfile), D (Metadata), E (Registration), F (ChangeRequests) and I.6 (wiki publish) — kept whole,
  including their intros and "verified aligned" blocks.
- **§J** — where the spec was wrong rather than the code. All 15 resolved.
- **§L** — the original triage order, superseded by the refreshed triage in the live file.
- **§M — the full session log**, 2026-08-21 to 2026-08-24. This is the most useful thing in the file: it
  records not just what was fixed but what each pass got wrong and how the error was caught. Several
  entries are the only written record of why a design is the way it is.

Section letters and finding ids are unchanged, so any reference to `AM-6`, `CR-9`, `X-4.6` etc. still
resolves — check here first, then the live file.

---

### Fix-first list

| ✓ | Rank | Finding | Why it's first |
|---|---|---|---|
| ☑ | 1 | **`ProcessingJobFailed` projects `Status = Succeeded`** (P-1) | Every failed processing job reads back as succeeded. Silent data corruption in an operator-visible read model. |
| ☑ | 2 | **`DeleteAsset` destroys S3 objects before evaluating its guards** (AM-6) | A correctly-rejected delete (422) still permanently deletes the original and every rendition. Unrecoverable data loss on a blocked operation. |
| ☑ | 3 | **`RecordTypeDraftDiscarded` projects `IsDeprecated = true`** (M-6) | Discarding a draft marks the record type deprecated. Copy-paste bug from the neighbouring handler. |
| ☑ | 4 | **`SigningSessionDetailProjector` transposes `TenantId` and `Id`** (DS-4) | Every projected row stores the session id in the tenant field. A tenant-boundary corruption, latent until DocumentSigning ships. |
| ☑ | 5 | **No `publish-wiki.yml` workflow exists** (X-6.1) | Both `CLAUDE.md` files say docs auto-publish and instruct nobody to hand-edit `Media.wiki`. Neither is true — the published wiki has had no update path since the 2026-07-07 move. **Resolved by retiring `Media.wiki` — no workflow built.** |
| ☑ | 7 | **Registration OpenSearch index cannot accept its own documents** (R-6) | `dynamic: "strict"` mapping declares `RegistrationId`; the projected model renamed that field to `Id`. Search indexing and every `nextSearchAfter` cursor are broken. **Fixed, along with the identical defect on the MediaItems index (MI-7).** |
| ☑ | 8 | **A long comment permanently strands a ChangeRequest** (CR-4) | *Added 2026-08-22 on re-verification.* Nothing validates comment length before `Emit`, and `Apply` throws on the stored event. A >255-char body is accepted, persisted, and the aggregate can never be rehydrated again — by event replay or from snapshot. Unrecoverable without editing the stream. **Fixed 2026-08-23 together with CR-10 — bodies left aggregate state, so `Apply` has nothing left to reject.** |

---

## B. AssetManagement

28 findings. Routes and verbs for all 12 implemented endpoints match spec exactly; integration event contracts match 1:1 (11/11).

| ✓ | # | Sev | Area | Spec says | Code does | Spec ref | Code ref |
|---|---|---|---|---|---|---|---|
| ☑ | AM-1 | High | API | `POST /v1/assets/uploads/bulk` — bulk initiate up to 50 uploads | No such endpoint, command or handler. Only `bulk-confirm` exists | `asset.api.md:22,627-713` | absent |
| ☑ | AM-2 | High | Authz | Every asset endpoint requires `caller.owner_id == asset.OwnerId`; 403 otherwise | No owner check anywhere. `Actor.Id` is used only to stamp `UploaderId`. Any tenant user can read/tag/archive/delete any asset | `asset.api.md:43-55` | `Asset.cs` (no guards) |
| ☑ | AM-3 | High | API | Download of non-`Active`/`Archived` asset → 409 `AssetNotDownloadable` | Returns `QueryError.Failed` → **500** | `asset.api.md:525,542-556` | `GetAssetDownloadUrlHandler.cs:31`; mapping `AssetManagementEndpoint.cs:40-45` |
| ☑ | AM-4 | High | Read model | `AssetInfectionDetected` → status `ContainsVirus` in both projectors | Neither projector handles it; event is routed and silently dropped. Infected assets stay `Validating` | `asset.read-model.md:73,100` | `AssetSummaryProjector.cs:17-31`; `Projectors.ReadModel/MessageBusBuilderExtensions.cs:32` |
| ☑ | AM-5 | High | Write model | Standalone upload bounded by `AssetManagement:Upload:StandaloneMaxFileSizeBytes` | No check; the config key does not exist. Standalone uploads are unbounded | `asset.write-model.md:275-278` | `InitiateAssetUploadHandler.cs:39-64` |
| ☑ | **AM-6** | **High** | Write model | Delete guards (status, `IsAssigned()`, `VersionArtifact`) gate the operation; S3 delete then `AssetDeleted` | `DeleteObjectsAsync` runs **before** `asset.Delete()` evaluates guards. A rejected delete still destroys original + renditions, then returns 422 with the aggregate intact | `asset.api.md:389-397` | `DeleteAssetHandler.cs:56-63` ✅*verified* |
| ☑ | AM-7 | High | Write model | Confirm on non-`Pending` asset → 422 `AssetNotPending` | Handler and aggregate treat `Validating`/`Active` as idempotent success → 202 | `asset.api.md:122-136` | `ConfirmAssetUploadHandler.cs:52-56`; `Asset.cs:729-731` |
| ☑ | AM-8 | Med | Read model | `AssetProcessingTimeoutRecovered` → `Active` | Handlers exist but the event is **not registered** on the projector bus — read models stay `ProcessingFailed` | `asset.write-model.md:124-135` | `MessageBusBuilderExtensions.cs:28-42` |
| ☑ | **AM-9** | **High** | Read model | Lifecycle includes `→ VersionArtifact →` | `AssetPromotedToVersionArtifact`, `AssetVersionArtifactReleased`, `AssetReprocessingRequested` have no handlers and no registration. `GET /v1/assets/{id}` can never show `VersionArtifact` | `asset.write-model.md:74-77` | `AssetDetailProjector.cs:16-30` |
| | | | | **Re-scoped 2026-08-23 and raised to High.** Skipped on instruction 2026-08-21 as projector coverage; it is not. Behind the missing projection sat **AM-29**, an unbounded data-loss path — and the projection could not have been added without it, because the release event carried no target status to project | | | |
| ☑ | **AM-29** | **High** | Write model | An asset stays undeletable while any published version snapshots it (`mediaitem.read-model.md:252`) | *Added 2026-08-23 opening AM-9.* **`VersionArtifact` was a single flag over a many-to-one relationship.** `ApprovedAssetSnapshotFactory` serialises *every* current role asset on *every* approval, so an unchanged asset is held by v1, v2 and v3 alike. The old guard refused the second promotion (`Status is not (Active or Archived)`) and `ReleaseVersionArtifact` ignored both of its arguments — so purging **any one** version released an asset the other live versions still referenced, and `DELETE /v1/assets/{id}` would then destroy an S3 object two published version rows pointed at. Zero test coverage on any of it | `mediaitem.read-model.md:252` | `Asset.cs:485,552`; `ApprovedAssetSnapshotFactory.cs:29` |
| ☑ | **AM-30** | **High** | Read model | Purge deletes the version row | *Added 2026-08-23.* `MediaItemVersionDetailProjector` has always declared the handler; `MediaItemVersionPurged` was never registered on the projector bus. A purge released the assets and left the version row live on `GET /items/{id}/versions/{n}`, carrying the storage key of the object AM-29 had just made deletable. The write-side reference row *was* removed — that projector runs off the integration event on the cross-module queue | `mediaitem.read-model.md:250` | `Projectors.ReadModel/MessageBusBuilderExtensions.cs` |
| ☑ | AM-31 | Med | Write model | Consumers log and skip per-asset failures | *Added 2026-08-23.* Both AssetManagement consumers **discarded** the `Result` from `SendAsync`, so only infrastructure faults reached the `catch`. Every domain refusal — AM-29's included — passed in complete silence. The documented "logged and skipped" behaviour did not exist for the common case | — | `MediaItemApprovedEventHandler.cs:36`; `MediaItemVersionPurgedEventHandler.cs:39` |
| ☑ | AM-32 | Med | API | `GET /assets/{id}/renditions/{type}/download` → 409 when not downloadable | *Added 2026-08-23.* Returned `QueryError.Failed` → **500**, on an endpoint whose own OpenAPI description advertised the 409. Its sibling was given a result-variant at AM-3; this one never was | `asset.api.md:660` | `GetRenditionDownloadUrlHandler.cs:27` |
| ☑ | AM-33 | Med | Errors | The AM-14 bulk wire changes are covered by tests and spec | *Added 2026-08-23 from three failing tests.* **AM-14 changed two bulk endpoints' per-item codes and updated neither the tests nor all of the spec.** Three assertions kept pinning the pre-AM-14 strings (`ResourceNotFound` for a missing asset; `FileSizeExceeded` twice for a declared-size overflow that is now `AssetTooLarge` per AM-27) and one test *name* did too. `asset.api.md § bulk pre-flight step 2` and `error-catalog.md § Batch Operations` also still published `FileSizeExceeded` for the declared-size check — the latter for a condition no batch operation raises it for at all. The pass's own log called these out as "two wire changes, called out because they are wire changes" and then shipped tests contradicting them | `error-catalog.md:537`; `asset.api.md:711` | `BulkConfirmAssetUploadHandlerTests.cs:93`; `BulkInitiateAssetUploadHandlerTests.cs:132,150` |
| ☑ | AM-10 | Med | API | List field `originalFileName`; rendition `storageKey`, `sizeBytes` | `fileName`; rendition drops `storageKey`, renames `sizeBytes`→`fileSizeBytes` | `asset.api.md:446,450-458` | `AssetSummaryModel.cs:11`; `AssetRenditionModel.cs:5` |
| ☑ | AM-11 | Med | API | Bulk envelope `{succeeded, failed, skipped}`; ≥1 failure → 202 | `skipped` dropped from the response record (the command result carries it); all-failed returns **422**; failed item serialises as `assetId` not `name` | `bulk-operations.md:15-52` | `BulkConfirmAssetUploadResponse.cs:8`; `...Endpoint.cs:66-76` |
| ☑ | AM-12 | Med | API | Bulk asset batch cap 50, enforced at endpoint, 400 on exceed | Only rejects empty lists. `BulkOperationsOptions.MaxAssetsPerRequest` is never read; deployed config sets **200** | `bulk-operations.md:128-136` | `...Endpoint.cs:48-53`; `hosts/Api/appsettings.json:14` |
| ☑ | AM-13 | Med | API | 202 reserved for two saga endpoints; confirm/abort return no body | Four asset endpoints return 202, two with bodies | `api-conventions.md:360-379` | `InitiateAssetUploadEndpoint.cs:97` + 3 others |
| ☑ | AM-14 | Med | Errors | `AssetNotValidating`, `AssetAlreadyAttached` → 409 | Both `DomainError.InvalidOperation` → **422** | `error-catalog.md:63,68` | `Asset.cs:426,210` |
| ☑ | AM-14b | Med | Errors | Both codes are published client contract | *Added 2026-08-23 reopening AM-14.* Neither code ever reached a client — AssetManagement's endpoint base classes dropped `errorCode` and no raise site was tagged. The 2026-08-21 fix corrected a status nobody could branch on. **Codes now live**; `AssetNotValidating` re-filed as 422 under a stated 409/422 rule | `error-catalog.md § Implementation status` | `AssetManagementEndpoint.cs` |
| ☑ | AM-15 | Med | Write model | `FailProcessing` valid only from `Validating`/`Processing` | Also accepts `Pending` + `UploadExpired`; `ValidationError` category never accepted | `asset.write-model.md:23,195` | `Asset.cs:371-378` |
| ☑ | AM-16 | Med | Write model | `AttachToMediaItem` requires `MediaItemId = null` **and** `Status = Active` | Only the null check runs — a `Pending`/`Archived` asset can be attached | `asset.write-model.md:201` | `Asset.cs:206-215` |
| ☑ | AM-17 | Med | Write model | `DetachFromMediaItem(mediaItemId)` — precondition "id matches" | Signature takes no id (no match check); adds an undocumented `Status == Active` guard, so archived assigned assets can't detach | `asset.write-model.md:202` | `Asset.cs:340-354` |
| ☑ | AM-18 | Med | Write model | Confirm guard 1 = Content-Type must match declared type | Check deliberately removed (documented in-code). `ContentTypeMismatch` is unreachable | `asset.write-model.md:285-288` | `ConfirmAssetUploadHandler.cs:64-68` |
| ☑ | AM-19 | Med | Read model | `AssetSummaryReadModel(AssetId, … ContentType, SizeBytes)`; tables carry `EventId` | Uses `Id`, splits `Category`+`MimeType`, `FileSizeBytes`. Detail adds `BucketName`, has no `LastAssetEventVersion`; neither carries `EventId` | `asset.read-model.md:14-55` | `AssetSummaryReadModel.cs:17-31` |
| ☑ | AM-20 | Med | Read model | `media-assets` summary carries `SizeBytes` | Summary projector writes `null` on both create paths and never sets it. `GET /v1/assets` always returns `fileSizeBytes: null` | `asset.read-model.md:143-156` | `AssetSummaryProjector.cs:46,68,77-82` |
| ☑ | AM-21 | Med | API | `mediaItemId` is the only correct spelling | Single-part upload body field is `itemId`; multipart sibling uses `mediaItemId`. **Spec is self-inconsistent** and code follows the wrong half. **Resolved 2026-08-23 additively** — `mediaItemId` is canonical, `itemId` kept as a deprecated alias to v2 | `api-conventions.md:315-331` vs `asset.api.md:71` | `InitiateAssetUploadRequest.cs:29` |
| ☑ | AM-22 | Low | Read model | `AssetValidationPassed` → status `Processing`/`Active` | Projectors update only timestamps — matches `asset.api.md:601`. The **read-model doc is the stale half** | `asset.read-model.md:71` vs `asset.api.md:601` | `AssetSummaryProjector.cs:85-90` |
| ☑ | AM-23 | Low | Write model | 17 domain events, 11 consumed handlers | `AssetReprocessingRequested` and `AssetAssignedToRoleEventHandler` are real and absent from the spec tables | `asset.write-model.md:208-227` | `Asset.cs:501-511` |
| ☑ | AM-24 | Low | API | Detail response omits `tenantId` | Response exposes `tenantId` to clients | `asset.api.md:438-474` | `GetAssetByIdResponse.cs:8` |
| ☑ | AM-25 | Low | Write model | Event timestamps from command `occurredAt` | `AssetInfectionDetected` uses `DateTimeOffset.UtcNow` instead of `recordedAt` | `asset.write-model.md:191` | `Asset.cs:450` |
| ☑ | AM-26 | Low | Read model | `AssetMetadata` includes `AudioChannels` | Absent from the read-model DTO and API model — never reaches a consumer | `asset.write-model.md:164` | `AssetMetadataDto.cs` |
| ☑ | AM-27 | Low | Errors | `asset.api.md` says size-over-max → 400; `error-catalog.md` says 422 | Code returns 400. **Spec contradicts itself**; code follows the API doc | `asset.api.md:89` vs `error-catalog.md:70` | `InitiateAssetUploadHandler.cs:56-59` |
| ☑ | AM-28 | Low | API | 🔧 "Requires implementation (R-29 · Phase 5)" on archive and delete | Both fully implemented. Banners stale | `asset.api.md:354,385` | `ArchiveAssetEndpoint.cs:24` |

**Verified aligned:** all 12 route paths/verbs; `/v1` correctly wired globally via `Versioning.PrependToRoute` + `Version(1)` (so bare route strings are *not* a finding anywhere in this review); flat URLs; list envelope exactly `{items, pageSize, nextPageToken}`; `mediaItemId` on `GET /v1/assets`; `TenantId` from `IExecutionContext` on every command; 11/11 integration event contracts; aggregate guards for `Archive`/`Delete`/`Promote`/`Release`/`Bypass`/`Tag`; `ProjectedVersion` set on every projector write.

---

## C. Catalog

Largest module, six specced aggregates, four implemented. All 81 routes are flat — the `/catalog` prefix migration is complete.

### C.1 Cross-cutting

| ✓ | # | Sev | Area | Spec says | Code does | Ref |
|---|---|---|---|---|---|---|
| ☑ | C-1 | High | Pagination | `pageSize` capped at 100 on every DynamoDB list | **No clamp anywhere on the Dynamo path** — `pageSize=100000` is honoured. Only the two OpenSearch handlers clamp | `api-conventions.md §Pagination` / `ListCollectionsEndpoint.cs:45` + 5 siblings |
| ⊘ | C-2 | High | Authz | Per-aggregate Authorization tables define owner-scoped rights on every write | No handler except `ForceReleaseCheckoutHandler` checks ownership. Any tenant user can act on any other user's Collection, Folder, MediaItem or MediaProfile | `collection/folder/mediaitem/mediaprofile.api.md §Authorization` |
| ☑ | C-3 | Med | Status codes | 202 reserved "exclusively" for two saga endpoints | Five Catalog endpoints return 202 (4 bulk-create + `publish`). **`bulk-operations.md` mandates the bulk 202** — the two shared specs contradict each other; code follows `bulk-operations.md` | `api-conventions.md §Async` vs `bulk-operations.md §Response Envelope` |
| ☑ | C-4 | Med | Routes | `POST /v1/items/{id}/submit` → status `UnderReview` | Neither exists. Publication is `POST /items/{itemId}/publish`; `MediaItemStatus` has no `UnderReview` (`Draft, PendingApproval, Published, Revising, Archived`) | `api-conventions.md §Async` / `MediaItemStatus.cs:14-19` |
| ☑ | C-5 | Low | Errors | ~30 Catalog error codes | Only MediaItem checkout codes are emitted (22 `WithCode` sites). Matches the catalog's own 2026-08-20 disclaimer — aligned with stated status, not new drift | `error-catalog.md §Implementation status` |
| ☑ | C-6 | Low | Errors | No `ChangeRequestRequired` entry in the catalog | Code emits it on a live checkout path — undocumented code on the wire | `MediaItemErrorCodes.cs:93` |

### C.2 Collection

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | CO-1 | High | `GET /v1/collections?ownerId=` — list for owner | **No `ownerId` parameter exists.** Request is `(PageSize, PageToken)`; returns every collection in the tenant regardless of owner | `collection.api.md §Route Structure` / `ListCollectionsRequest.cs:11` |
| ☑ | CO-3 | Med | `sortBy` = `name`\|`createdAt`, backed by a `createdAt` GSI | No sort params; no `createdAt` GSI exists to sort on | `api-conventions.md §Sort Fields` / `CollectionByNameIndexSchema.cs:15` |
| ☑ | CO-4 | Low | `CollectionId` caller-generated; uses `ICollectionQueryService` + `IMediaProfileReadModel` | Server-generated (matches `collection.api.md` — the two spec files disagree). Neither named service exists; handler uses `INameReservationService` and performs **no** published-profile check | `collection.write-model.md §Properties` / `CreateCollectionCommandHandler.cs:22-45` |
| ☑ | CO-5 | Low | Detail projector maintains `RootFolderIds` | Field absent; both events return `Unchanged()`. Self-documented in-code | `collection.read-model.md` / `CollectionDetailProjector.cs:12-16` |

### C.3 Folder

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | F-1 | High | `MoveFolder`: no circular parent chains → `CircularFolderReference`, enforced by `IFolderHierarchyService` | **`IFolderHierarchyService` does not exist.** Only guard is `newParentFolderId == folderId`. Moving a folder into its own descendant succeeds and detaches the subtree from the collection root | `folder.write-model.md §Invariants` / `MoveFolderHandler.cs:35-47` |
| ☑ | F-2 | High | `CollectionId` immutable — folders cannot move between collections → `FolderCollectionImmutable` | `MoveFolderCommand` carries `CollectionId`, exposes it on the wire, and `Folder.Move` emits `FolderMoved` on change. **Cross-collection move is explicitly supported** | `folder.write-model.md §Invariants` / `Folder.cs:161-169` |
| ☑ | F-3 | High | `GET /v1/collections/{id}/folders/hierarchy` → `{ "folders": [...] }` | Returns `{ "items": [...] }` — top-level envelope key mismatch, client-visible break | `folder.api.md` / `GetFolderHierarchyResponse.cs:6` |
| ☑ | F-4 | Med | `Rename`/`Move` precondition "not archived" | Neither method checks `IsArchived` (metadata methods and `Archive`/`Close` do guard correctly) | `folder.write-model.md §Methods` / `Folder.cs:161,173` |
| ☑ | F-5 | Med | Route list omits `POST /v1/folders/bulk-paths` | A second bulk-path endpoint exists that auto-resolves the collection — public route, no spec entry | `folder.api.md` / `BulkCreateFoldersByPathAutoEndpoint.cs:19` |
| ⊘ | F-6 | Med | `POST /v1/collections/{id}/folders/import` | Not implemented — see BulkFolderImportJob. **Deferred on instruction 2026-08-21** — advanced feature, belongs with §C.6 | `folder.api.md §Large-Volume Imports` |
| ☑ | F-7 | Med | `GET /v1/folders` and `/children` accept `sortBy`/`sortOrder` | Neither request record has them | `folder.api.md` / `ListFoldersRequest.cs:10-14` |
| ☑ | F-8 | Med | One GSI, `CollectionParentIndex` | Three differently-named schemas: `FolderByParentAndNameIndex`, `FolderHierarchyIndex`, `FolderChildByNameIndex`. No `CollectionParentIndex` | `folder.read-model.md §GSI` / `FolderByParentAndNameIndexSchema.cs:15` |
| ☑ | F-9 | Low | Create body `{parentFolderId, name, description, openedDate, closedDate}` | Also accepts/persists `originator`; `GET` surfaces `originator` and `archivedDate` — three undocumented wire fields | `folder.api.md` / `CreateFolderRequest.cs:10` |

**Aligned:** depth ≤ 10 genuinely enforced on all four creation paths via a strongly-consistent counter; archive cascades to descendants and is blocked by active registrations; name reservations swapped/released atomically on move/archive; consolidated `PATCH /v1/folders/{folderId}` matches the 2026-07-08 note.

### C.4 MediaItem

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | MI-1 | High | `GET /v1/items/search` → `{items:[{id,title,status,score}], nextPageToken, pageSize}` + `status`/`folderId`/`collectionId` filters | Returns `nextSearchAfter` (different cursor field); items are **full detail objects**, not summaries, with no `score`; **none of the four filters are accepted** | `mediaitem.api.md` / `SearchMediaItemsRequest.cs:12`, `SearchMediaItemsResponse.cs:7-11` |
| ☑ | MI-2 | Med | `POST /items/{id}/publish` accepts `commentThreadId` | Request has only `itemId` + `reviewerIds`; endpoint passes `null`. The aggregate's parameter is unreachable from HTTP | `mediaitem.api.md` / `PublishMediaItemEndpoint.cs:50-56` |
| ☑ | MI-3 | Med | `POST /items/{itemId}/checkout` body `{collaborators}` | Also accepts `changeRequestId`, which drives the `ChangeRequestRequired`/`ChangeRequestNotOpen` guards — undocumented and behaviourally significant | `mediaitem.api.md` / `CheckOutMediaItemEndpoint.cs:71` |
| ☑ | MI-4 | Med | `GET /v1/folders/{folderId}/items` accepts `status`, `sortBy`, `sortOrder` | None exist. Spec flags this as "R-21 requires implementation" — a known gap, but the published contract is wrong today | `mediaitem.api.md` / `ListMediaItemsRequest.cs:9-12` |
| ☑ | MI-5 | Med | "Exactly one GSI" (`MediaItemByFolderIndex`) | Two more exist and are queried: `MediaItemByLeaseExpiryIndex` (sparse, backs `ListExpiredCheckouts`) and `MediaItemVersionByMediaItemIndex` | `mediaitem.read-model.md §GSIs` / `MediaItemByLeaseExpiryIndexSchema.cs:34-43` |
| ☑ | MI-6 | Low | `Publish` guard: `Status == Draft` | Accepts `Draft` **or** `Revising` — matches the spec's own state diagram. The **prose guard is the stale half** | `mediaitem.write-model.md §Methods` / `MediaItem.cs:857-860` |
| ☑ | **MI-8** | **Med** | `api-conventions.md`: "The version is per-aggregate, not per-field… two callers editing unrelated fields concurrently **will conflict**. That is deliberate for now — see the ADR for the field-level rebase that softens it" | **The rebase shipped.** `MetadataRebase.EvaluateAsync` is wired into both metadata handlers: on a mismatched `If-Match` it replays the tail since the caller's base version and *proceeds* when the write set is disjoint and every field is `AllowsConcurrentEdit`. The spec describes the pre-rebase contract as current and the shipped one as future. A client told "any mismatch is a 409" will not understand a 200 · *Found 2026-08-24* | `MetadataRebase.cs:49`; `SetMetadataFieldHandler.cs:42-53`; `SetMetadataBatchHandler.cs:43-49` |
| ☑ | **MI-9** | Med | `mediaitem.api.md` documents neither `If-Match`, `ETag`, nor `409` on `PUT /items/{itemId}/metadata` or `PATCH /items/{itemId}/metadata/{fieldName}` | These are **the only two endpoints in the platform** that implement optimistic concurrency, and the aggregate's own API contract was silent on it — the mechanism was described only in `api-conventions.md`, which named the wrong verb until 2026-08-22. Both error lists also omitted `409` and the `If-Match`-malformed `400` · *Found 2026-08-24* | `mediaitem.api.md:176,249` |
| ☑ | **MI-10** | Med | `AllowsConcurrentEdit` decides whether a stale write rebases or conflicts | **Not discoverable by any client.** The flag is authored on the RecordType, crosses into Catalog, and is read by the guard — but no read model or endpoint response exposes it. Zero hits for `AllowsConcurrentEdit` in `Catalog.ReadModel*`. A client cannot tell which fields rebase, so cannot predict a `409`. `compiledMetadataFields` on `GET /v1/profiles/{profileId}` is the natural home · *Found 2026-08-24* · **Fixed 2026-08-24** — projected through `CompiledMetadataTemplateMapper` onto both the detail and version-detail rows and emitted on `compiledMetadataFields`; the `api-conventions.md` caveat saying it isn't discoverable is now the discovery instructions | `MediaProfileSnapshotField.cs:31`; `CompiledMetadataFieldDto.cs`; `CompiledMetadataFieldModel.cs` |
| ☑ | **MI-7** | **High** | MediaItem OpenSearch doc; `search_after` tiebreaker sorts on `MediaItemId.keyword` | **Not in the original review — found while fixing R-6.** Identical defect: `MediaItemsIndexMapping` is `dynamic: "strict"` and declares `MediaItemId`, but `MediaItemDetailReadModel` exposes its own identifier as `Id` (ADR-012 rule 1). Strict rejection on every index write; `SearchMediaItems` and `ListAllMediaItems` both sort on a field no document carries | `MediaItemsIndexMapping.cs:46` / `MediaItemDetailReadModel.cs:22` |

**Aligned (notable):** ADR-011 unified assign/move confirmed — `PUT /items/{itemId}/folder` dispatches assign and falls through to move on 422. `GET /v1/items?unassigned=true` exists; the old `/catalog/items/unassigned` route is genuinely gone. **If-Match/ETag is real on both claimed endpoints**, with correct `*` and weak-tag rejection — note `api-conventions.md §Coverage` names the field-level route as `PUT`, but code and `mediaitem.api.md` both use `PATCH`; the shared doc has the wrong verb. `POST /folders/{folderId}/items` correctly returns 201, not 202 (R-42 satisfied). Checkout/checkin/abandon/renew/force-release return documented codes with real `errorCode` extensions — the one place in the codebase where the error contract is fully honoured.

### C.5 MediaProfile

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | MP-1 | High | `GET /v1/profiles/{id}` returns `compiledMetadataFields[]` and `suppressedFieldNames[]`; clients **must** use qualified keys for suppressed bare names | Neither field is on the response or the read model. The compiled template exists on the aggregate but is never projected. **There is no way for a client to discover the qualified field names the metadata API requires** — the ADR-013 discovery path is unimplemented | `mediaprofile.api.md`; `mediaitem.api.md §PATCH .../metadata/{fieldName}` / `GetMediaProfileByIdResponse.cs:6-24` |
| ☑ | MP-2 | Med | 16 write routes | Two more are live and undocumented: `PUT /profiles/{id}/auto-submit-on-complete`, `PUT /profiles/{id}/change-request-policy` — both surfaced on `GET` | `mediaprofile.api.md §Route Structure` / `SetAutoSubmitOnCompleteEndpoint.cs:16` |
| ☑ | MP-3 | Med | `LeaseDurationMinutes` governs checkout expiry | Settable only as an unspecified extra field on `PUT /checkout-policy`; in no request-body spec and absent from the `GET` response example | `mediaitem.api.md §Checkout`; `mediaprofile.defaults.md:156` / `SetCheckoutPolicyEndpoint.cs:16` |
| ☑ | MP-4 | Low | `POST /profiles/{id}/publish` → `{ "newVersion": 2 }` | Returns `{profileId, newVersion, publishedAt}` — additive, non-breaking, undocumented | `mediaprofile.api.md` / `PublishMediaProfileResponse.cs:3` |

### C.6 BulkFolderImportJob / BulkMediaImportJob


> `CLAUDE.md`'s "bulk import **workers** deferred" phrasing materially understates this. The workers aren't the gap; the aggregates are.

---

## D. Metadata (RecordType)

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | M-1 | High | `DELETE /v1/record-types/{id}/draft` → 204 | Returns **202** with a body | `recordtype.api.md §Route Structure` / `DiscardRecordTypeDraftEndpoint.cs:56` |
| ☑ | M-2 | High | `DELETE /v1/record-types/{id}/fields/{fieldName}` → 204 | Returns **202** with a body | `recordtype.api.md:26` / `RemoveFieldFromRecordTypeEndpoint.cs:60` |
| ☑ | M-3 | High | Per-endpoint 409s (no active draft, duplicate field, no draft to publish, capability not attached) and a 404 (field not found) | **Every one** is `DomainError.InvalidOperation` → 422. Only `EntityAlreadyExists` (409) and `ResourceNotFound` (404) are used, and only in Create/Rename/SetAliases | `recordtype.api.md:123,160,211,234,260,388` / `DomainErrors.cs:7-131` |
| ☑ | M-4 | High | `GET /v1/record-types` = list **by owner**; GSI `OwnerIndex (OwnerId + Name)` | Tenant-wide only — no `ownerId` param, no owner predicate. GSI is `RecordTypeByNameIndex` with PK `TENANT#{t}#RECORD_TYPES`. Every tenant record type returned to every caller | `recordtype.read-model.md:14-15,97` / `ListRecordTypesQuery.cs:11-23` |
| ☑ | M-5 | High | `RecordTypeCreated` → `publishedVersion = 0` | Inserts `PublishedVersion = 1` — an unpublished type reports version 1 | `recordtype.read-model.md:76` / `RecordTypeSummaryProjector.cs:28-42` |
| ☑ | **M-6** | **High** | `RecordTypeDraftDiscarded` → `hasDraft = false` | Sets `IsDeprecated = true` — copy-paste from the `RecordTypeDeprecated` handler. **Discarding a draft deprecates the record type** | `recordtype.read-model.md:83` / `RecordTypeSummaryProjector.cs:70-73` ✅*verified* |
| ☑ | M-7 | High | Summary row carries `HasDraft`, toggled on create/discard/publish | Written `false` at create and **never updated by any handler** | `recordtype.read-model.md:30,77,83,84` / `RecordTypeSummaryProjector.cs:28-79` |
| ☑ | M-8 | High | Deprecating a field marks **that** field deprecated | `FieldDeprecatedInRecordType` maps **every** draft field to `IsDeprecated = true` | `recordtype.api.md:228-234` / `RecordTypeDetailProjector.cs:158-165` |
| ☑ | M-9 | High | `GET /v1/record-types/{id}` returns `aliases: []` — the ADR-013 collision qualifier clients must discover | No `Aliases` field on the read model or response; no projector handles `RecordTypeAliasesUpdated`. **Aliases are unreadable via the API** | `recordtype.api.md:334`; ADR-013 Decision 2 / `RecordTypeDetailReadModel.cs:28-43` |
| ☑ | M-10 | Med | `GET /versions/{version}` → `{id, version, aliases, fieldSnapshot, publishedAt}` | `{recordTypeId, name, versionNumber, fieldSnapshot, capabilities, publishedAt}` — `version` renamed, `aliases` absent (`recordTypeId` is correct per ADR-012; the spec is wrong there) | `recordtype.api.md:349-364` / `GetRecordTypeVersionResponse.cs:46-52` |
| ☑ | M-11 | Med | List envelope includes `pageSize` | `ListRecordTypeVersionsResponse` omits it | ADR §Cursor-Only Pagination / `ListRecordTypeVersionsResponse.cs:31-33` |
| ☑ | M-12 | Med | `Deprecate()` guard is `Version > 0` only | Also rejects when a draft is open — an undocumented 422 | `recordtype.api.md:381-382` / `RecordType.cs:185-199` |
| ☑ | M-13 | Med | `RemoveField` removes a field from the draft | `Apply(FieldRemovedFromRecordType)` sets `Draft = null` when the last field goes, **silently discarding the draft** | `recordtype.write-model.md:129` / `RecordType.cs:640-646` |
| ☑ | M-14 | Med | 11 named `errorCode` values | None emitted (no `WithCode` in the module), and `error-catalog.md` has **no Metadata section at all** | `recordtype.api.md` (10 sites) / `DomainErrors.cs` |
| ☑ | M-15 | Med | `IRecordTypeUnicityService` backed by `media-name-reservations`, scope key `RECORDTYPE` | Interface does not exist. Handlers use `INameReservationService` with scope `record-types` | `recordtype.write-model.md:192-216` / `CreateRecordTypeHandler.cs:30` |
| ☑ | M-16 | Med | Invariant table lists no required-field or order-uniqueness guards | Aggregate adds six undocumented rejections (`CannotDeprecateRequiredField`, `FieldOrderConflict`, `FieldAlreadyDeprecated` on update/replace, `CannotRemoveImmutableField`, 1000-char migration note, `NothingToRevise`) | `recordtype.write-model.md:19-41` / `RecordType.cs:142,171,227,335,421,426,533` |
| ☑ | M-17 | Low | Event/command tables | `FieldDeprecatedInRecordType`, `RecordTypeDescriptionUpdated`, `UpdateRecordTypeDescriptionCommand`, `DeprecateField` all exist and are wired but absent from the tables | `recordtype.write-model.md:142-184` |
| ☑ | M-18 | Low | One projector; `RecordTypeVersionSnapshotReadModel` | Four projectors; no such type; `GetRecordTypeVersion` reads a detail model **with** `FieldSnapshot`, contrary to the spec's note | `recordtype.read-model.md:12,69,158-185` |
| ☑ | M-19 | Low | `SetAliases` is a no-op if **set**-equal | Uses `SequenceEqual` — order-sensitive, so reordering emits a spurious event | `recordtype.write-model.md:137` / `RecordType.cs:460-464` |

**Aligned:** all 19 routes exist with correct verb+path; **no `/metadata/` prefix survives anywhere**; 201 with `{id, name, createdAt}` and no `Location`; `PUT /aliases` matches spec end-to-end (regex validation, 409 via reservation scope `record-type-aliases`, 204, `DuplicateAliasInRequest` → 422); `Publish()` pins the active alias set into the event per ADR-013 Decision 2; field limit 100, `FieldTypeImmutable`, `CannotRelaxImmutability`, MaxSelections clamp, capability registry → 422 all enforced as specified.

---

## E. Registration

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | R-1 | High | `Submitted → PendingConfirmation`; confirm/reject require `PendingConfirmation` | **No `PendingConfirmation` member exists.** The state is `SubmissionRecorded`, and that string is returned in `status` on every read | `registration.write-model.md:55-81` / `RegistrationStatus.cs:3-12` |
| ☑ | R-3 | High | User writes require `Actor.Id == registration.OwnerId` | No handler compares caller to `OfficerId` | `registration.api.md:45` / `CancelRegistrationHandler.cs:18-35` |
| ☑ | R-4 | High | Attached document must be `Published` **and its profile must lack `Processing` capability** | Both handlers check `HasRegistrationCapability` on the document instead. `HasProcessingCapability` is loaded into the context record and **never read**. Processed media can be attached; a plain application form is rejected | `registration.write-model.md:26,178-183` / `AttachMediaItemToRegistrationHandler.cs:38` |
| ☑ | R-5 | High | `GET /v1/registrations/{id}` → `reference`, `notes`, `documents[]`, amendment `resolvedAt` | Returns `referenceNumber` + `externalReference` (no `reference`), `items[]` with `attachedAt`, `amendmentId`/`decidedAt`, plus five undocumented fields | `registration.api.md:341-381` / `GetRegistrationByIdResponse.cs:6-26` |
| ☑ | **R-6** | **High** | OpenSearch doc keyed on `registrationId`; `search_after` tiebreaker sorts on `RegistrationId.keyword` | Mapping is `dynamic: "strict"` and declares `RegistrationId`, but the projected model renamed its identifier to `Id` (ADR-012) with no `[JsonPropertyName]` shim. **`Id` isn't in the mapping → strict rejection; `RegistrationId` is never populated → the sort key and every cursor are broken** | `registration.read-model.md:63-80` / `RegistrationsIndexMapping.cs:40-46`; `RegistrationDetailReadModel.cs:33` |
| ☑ | R-7 | High | Search results carry `reference` | Handler indexes the **detail** model but deserialises `_source` into the **summary** record. Detail has `ReferenceNumber`, summary has `Reference` → `reference` is always `null` | `registration.api.md:441-457` / `SearchRegistrationsHandler.cs:93` |
| ☑ | R-8 | High | `actor_type = "User"` → results scoped to caller's `OwnerId` | DSL filters on `TenantId.keyword` only. Any user sees every registration in the tenant | `registration.api.md:436` / `SearchRegistrationsHandler.cs:46-50` |
| ☑ | R-9 | High | `POST /reject` body `{ "rejectionReason": … }` | Binds `{ "reason": … }` | `registration.api.md:287` / `RejectRegistrationRequest.cs` |
| ☑ | R-10 | High | `POST /amendments` body `{amendmentId, mediaItemId, itemType}` | Binds `{itemId, itemType, notes}` — `mediaItemId` renamed to the forbidden `itemId`, `amendmentId` not accepted, undocumented `notes` accepted | `registration.api.md:199-206`; `api-conventions.md:324` / `RequestAmendmentRequest.cs` |
| ☑ | R-11 | Med | `POST /confirm` body `{reference}` | Also accepts `confirmedAt` and uses it verbatim as the event timestamp — **a caller can backdate a confirmed legal record** | `registration.api.md:257-259` / `ConfirmRegistrationEndpoint.cs:49-52` |
| ☑ | R-12 | Med | `POST /submission` takes no body | Accepts `{externalReference, notes}`; the detail projector writes `dispatchDetails` into the read model's `Notes` field | `registration.api.md:230-236` / `RegistrationDetailProjector.cs:72` |
| ☑ | R-13 | Med | 409s for invalid transition / already attached / amendment not pending; 404 for amendment not found; six named codes | All aggregate errors are `InvalidOperation` → 422 with no `errorCode`. A missing amendment returns 422, not 404 | `registration.api.md` (9 sites) / `DomainErrors.cs:10-38` |
| ☑ | R-14 | Med | `GET /v1/registrations` accepts `sortOrder` | Request has only `mediaItemId`, `pageSize`, `pageToken`; the schema never flips scan direction | `api-conventions.md:307` / `ListRegistrationsRequest.cs:12` |
| ☑ | R-15 | Med | GSIs `MediaItemRegistrationsIndex` and `OwnerStatusIndex (OwnerId + Status)` | `RegistrationByMediaItemIndex` and `RegistrationByOwnerIndex`; the owner index sort key is `{InitiatedAt:O}#{Id}`, not `Status` — **status-filtered owner queries are not supported** | `registration.read-model.md:31-33` / `RegistrationByOwnerIndexSchema.cs:45-48` |
| ☑ | R-16 | Med | `RegistrationInitiated` payload includes `Notes?` | Event carries `MediaProfileId` (unspecced) and no `Notes`; the aggregate's `Notes` property is declared but never assigned | `registration.write-model.md:136,156` / `Registration.cs:60,115-128` |
| ☑ | R-17 | Low | Index `media-registrations`, camelCase fields | Index is `registrations`, PascalCase, no `updatedAt`, plus seven fields the spec table omits | `registration.read-model.md:63-88` / `RegistrationsIndexMapping.cs:25` |
| ☑ | R-18 | Low | OpenSearch sorts `(createdAt desc, entityId asc)` | Sorts `InitiatedAt desc` — semantically equivalent. But `registration.read-model.md:149` claims `from`/`size` pagination, contradicting both the API spec and the code | `api-conventions.md:284` |
| ☑ | R-19 | Low | Projector table names statuses `Submitted`, `AmendmentRequested`, `PendingConfirmation`, `Approved` | None of those enum members exist; resubmit projects `Resubmitted` (correct per the aggregate) | `registration.read-model.md:97,234-248` |

**Aligned:** all 14 routes match verb+path; status codes correct throughout (201 body-only, 204 elsewhere, no 202, no `Location`); `mediaItemId` filter correct; both list envelopes correct; search returns 400 on blank `q` and clamps pageSize; `ApproveAmendment` emits both events in one write with `AddedViaAmendmentId` set.

---

## F. ChangeRequests

**Re-verified 2026-08-22** against `feature/change-requests` before starting the fix pass. The original
rows were written 2026-08-21; the module has moved since, and the framing of several findings has moved
with it. Four rows are re-scoped, one is largely stale, and four new findings (CR-14 … CR-17) were
found during the re-read. **Read §F.0 first** — several rows only make sense once the three-aggregate
model is clear.

### F.0 How ChangeRequest, MediaItem and EditSession actually relate

Decision of record: `docs/adrs/editing-lifecycle-and-concurrency.md` in the code repo
(recorded 2026-08-20, corrected 2026-08-21). It **supersedes** the CR-first checkout model that the
`ChangeRequests` spec files still describe. Three separate concerns:

| Concept | Lives in | Answers |
|---|---|---|
| `EditSession` | VO on `MediaItem` | *May you write to this item?* — a membership set plus a lease. Carries a nullable `ChangeRequestId`. |
| `ReviewSession` | VO on `MediaItem` | *What did the reviewers decide?* — roster, `OriginStatus`, `CommentThreadId`, `EditSessionChangeRequestId`, `SessionEditorsOrNull`. |
| `ChangeRequest` | Its own aggregate, own BC | *Why is this change being made?* — `Title`/`Reason`/`Scope`, `Open \| Resolved \| Abandoned`, participants, and the comment thread. |

**Two distinct ChangeRequestIds can be live on one MediaItem at the same time**, and they are the same
aggregate type serving two purposes:

- **Governance CR** — the client calls `POST /change-requests` first, then checks out under it.
  `OpenChangeRequestHandler` writes `ReviewSessionId = ""` and always adds the creator as a participant.
- **Comment-thread CR** — auto-raised at submit: `RequestPublication` → `MediaItemPublicationRequested`
  → `MediaItemSubmittedForReviewIntegrationEvent` → `MediaItemPublicationRequestedEventHandler` →
  `CreateChangeRequestCommand`. Untitled, carries a `ReviewSessionId`, participants = submitter + reviewers.

The enforcement path:

1. `CheckOutMediaItemHandler` reads `profile.ChangeRequestPolicy`. `RequiredForEdit` with no id → 422
   `ChangeRequestRequired`. Any supplied id is validated even when not required.
2. Validation goes through `IChangeRequestQueryService.IsOpenAsync` → `ChangeRequestReference`, a
   **write-side** index in Catalog fed by `ChangeRequestLifecycleEventHandler` from the ChangeRequests
   module's three integration events. It **fails open on absence**, deliberately and documented — a
   client can legitimately outrun the projection.
3. The link survives the review cycle. Submit closes the `EditSession` with reason `Submitted` but
   copies its `ChangeRequestId` onto `ReviewSession.EditSessionChangeRequestId`; `RejectReview` and
   `Withdraw` call `ReopenEditSession(...)` and restore it.
4. `MediaItemApproved` carries `EditSessionChangeRequestId` → `MediaItemApprovedEventHandler` dispatches
   `ResolveChangeRequestCommand` as `MemberId("owner_system")`, which `ChangeRequest.MayClose` exempts.
   An already-terminal result is swallowed so at-least-once redelivery cannot poison-queue a
   publication that succeeded.

**There is no saga.** `MediaItemCheckoutReviewSaga` and its five SNS consumers were explicitly not
built — the lock holds its own membership, the CR holds its own lifecycle, so there is nothing to keep
in step. See CR-17 for the dead references that survive from the superseded design.

### F.1 Findings

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | CR-1 | High | "There is **no public HTTP endpoint** to create them" — 7 routes listed | `POST /change-requests`, `/{id}/resolve`, `/{id}/abandon` all exist. **Re-scoped 2026-08-22:** these are correct per the ADR — the client *must* open the CR before checking out under it. The spec is the stale half; the fix is a spec rewrite, not route removal | `mediachangerequest.api.md §Overview` / `OpenChangeRequestEndpoint.cs:19` |
| ☑ | CR-2 | High | `CommentNotFound` → 404; `NotCommentAuthor` → 403; both with `errorCode` | All three comment guards return `InvalidOperation` → 422 with no code. **Also:** `AddComment`'s parent-not-found is 422 where the spec says 404 | `error-catalog.md §ChangeRequests` / `ChangeRequest.cs:181,197-207,223-233` |
| ☑ | CR-3 | High | `ReviewCommentDeleted` → `isDeleted = true`, **clear body to `"[deleted]"`, clear `authorId`** | Sets `IsDeleted` only. Full body and authorId remain in the table and are returned by `GET /comments`. **Note:** the aggregate retains the body too (CR-10), and the event carries it permanently — decide whether `"[deleted]"` is a redaction requirement or a display concern before fixing | `mediachangerequest.read-model.md:99` / `ChangeRequestCommentProjector.cs:49` |
| ☑ | **CR-4** | **High** | `CommentBody` max **4,000** chars → `InvalidCommentBody` | **Re-scoped 2026-08-22 — this is a poison pill, not a validation gap.** `NonEmptyString.MaxLength = 255`; there is no `AbstractValidator` anywhere in the module; `AddComment` never validates. `Apply(ReviewCommentAdded)` calls `NonEmptyString.Create(e.Body).Value`, which throws on a failed `Result`. A >255-char body is accepted, emitted and **persisted**, after which the aggregate is permanently unrehydratable — same defect in `FromSnapshot`. `AddCommentEndpoint` even documents a 400 for it that nothing raises | `mediachangerequest.write-model.md §Value Objects` / `NonEmptyString.cs:12,30`; `ChangeRequest.cs:185,379,333`; `AddCommentEndpoint.cs:35` ✅*verified* |
| ☑ | CR-5 | High | `GET /v1/change-requests` accepts `sortBy` ∈ {`createdAt`,`resolvedAt`} + `sortOrder` | No sort binding; both GSI schemas return `GetSortKeyCondition => null` and declare no sort key | `api-conventions.md:306` / `ChangeRequestByOwnerIndexSchema.cs:20,29-32` |
| ☑ | CR-6 | Med | Detail returns `createdById` | **Mostly stale 2026-08-22.** `Status`/`Title`/`Reason`/`Scope`/`ResolvedAt` are now on the response and are correct per the ADR — not drift. What survives is `ownerId` vs `createdById`, and the internal split: the aggregate says `CreatedById`, the read model and wire say `OwnerId`. A naming decision, ADR-012 in spirit | `mediachangerequest.api.md` / `GetChangeRequestByIdResponse.cs:5-16`; `ChangeRequest.cs:59` |
| ☑ | CR-7 | Med | `parentCommentId: null` for top-level | Maps to `string.Empty` and is typed non-nullable — clients receive `""` | `mediachangerequest.api.md` / `ChangeRequestCommentSummaryModel.cs:10,22` |
| ☑ | CR-8 | Med | Comments pageSize default 50, max 100, ordered `CreatedAt` asc | Default 20, no cap, ordering unspecified | `mediachangerequest.api.md` / `ListChangeRequestCommentsRequest.cs:3` |
| ☑ | CR-9 | Med | CR "has **no lifecycle status of its own**"; governance lifecycle is "a future increment" | **Confirmed and larger than written.** Beyond `ChangeRequestStatus{Open,Resolved,Abandoned}`, `Resolve()`/`Abandon()` and both events: `Title`, `Reason`, `Scope`, `_participantIds`, `MayClose` with a system-actor exemption, and an `IsOpen` gate on `AddComment`. All four `MediaChangeRequest` spec files **and** `context-overview.md` need rewriting against the ADR | `mediachangerequest.write-model.md:8-18` / `ChangeRequest.cs:39,64-82,117-169,254-257` |
| ☑ | CR-10 | Med | `EditComment` takes `oldBody` from `ICommentReadModel`; bodies "never in aggregate state" (400 KB rationale) | `ICommentReadModel` does not exist. `ReviewComment` carries the full `Body` in aggregate state **and in `ChangeRequestSnapshot`**. **Decide, don't just fix** — this interacts with CR-4: raising the cap 255 → 4,000 multiplies snapshot size ~16×, which is precisely the 400 KB risk the spec's design existed to avoid | `write-model.md:123-135,153` / `ChangeRequest.cs:236,274-283`; `ReviewComment.cs:6` |
| ☑ | CR-11 | Med | `OwnerStatusIndex = OwnerId + Status + CreatedAt`; query takes `Status?` | **Narrowed 2026-08-22.** `Status` *is* now on `ChangeRequestSummaryReadModel` and maintained by the projector — the gap is the index and the query record, not the data. Index is PK-only, no sort key; `ListChangeRequestsByOwnerQuery` has no `Status` parameter | `read-model.md:38` / `ChangeRequestByOwnerIndexSchema.cs:20-32`; `ChangeRequestSummaryReadModel.cs:13` |
| ☑ | CR-12 | Low | `AddCommentHandler` checks caller is owner/participant → `CommentAuthorNotParticipant` | **Partly stale 2026-08-22.** The aggregate now gates `IsOpen` *before* participation (so a closed thread reads as closed to everyone), and `OpenChangeRequestHandler` always adds the creator as a participant. What remains is that the `Forbidden` carries no `errorCode` — fold into CR-2 | `write-model.md:117` / `ChangeRequest.cs:165-174`; `OpenChangeRequestHandler.cs:25-29` |
| ☑ | CR-13 | Low | Catalog declares five reviewer-related codes | **Inverted 2026-08-22.** Reviewers correctly live on `MediaItem.ReviewSession` per the ADR, so the five codes should be **deleted** from the catalog, not implemented. `ChangeRequestNotFound` still has zero call sites — handlers use a bare `ResourceNotFound(...)` | `error-catalog.md §ChangeRequests` / `ChangeRequestErrorCodes.cs:20`; `AddCommentHandler.cs:21` |

### F.2 Found during the 2026-08-22 re-verification

| ✓ | # | Sev | Finding | Ref |
|---|---|---|---|---|
| ☑ | **CR-14** | **High** | `ChangeRequests.ReadModel.Endpoints`'s `SendDomainErrorAsync` calls `AddError(error.ErrorMessage)` with **no code**, while its `WriteModel.Endpoints` twin passes `error.CodeOrNull()`. Every coded error surfaced on a read endpoint silently loses its `errorCode`, independently of X-10.3 — this one drops the code before the configurator ever sees it, so moving `ErrorCodeResponseConfigurator` to `QueryApi` will **not** fix it | `ReadModel.Endpoints/V1/ChangeRequestsEndpoint.cs:23,61` vs `WriteModel.Endpoints/V1/ChangeRequestsEndpoint.cs:24,62` |
| ☑ | CR-15 | Med | **The comment-thread CR raised at submit is never resolved by anything.** `MediaItemApprovedEventHandler` closes only `EditSessionChangeRequestId` — correctly, per the ADR ("publishing under one says nothing about the others"). But nothing closes `ReviewSession.CommentThreadId`, so every published item leaves an `Open` change request behind permanently, visible in `GET /v1/change-requests?mediaItemId=`. Needs a decision, not necessarily a fix | `MediaItemApprovedEventHandler.cs:41-54`; `MediaItem.cs:287,898` |
| ☑ | CR-16 | Med | Nothing on the wire distinguishes a **governance** CR from a **comment-thread** CR. They differ only by `ReviewSessionId` being empty or set, which is on neither read model's public surface. `GET /v1/change-requests?mediaItemId=` returns both flat with no discriminator, and a client cannot tell which id to pass to `POST /items/{id}/checkout` | `ChangeRequestDetailReadModel.cs:17`; `ChangeRequestSummaryReadModel.cs`; `OpenChangeRequestHandler.cs:36-38` |
| ☑ | **CR-18** | Med | *Added 2026-08-23 during the CR-13 prune.* **Two of the "dead" reviewer codes are not dead — they are uncoded.** `MediaItem.cs:271,768` refuses "Reviewer is not part of this review session" and `:276,773` "Reviewer has already made a decision", both as bare `InvalidOperation` 422s. Those are exactly `NotAssignedReviewer` (which the catalog published as **403**, not 422) and `ReviewerNotPending`. The rows were moved to the *Catalog — MediaItems* table marked ⬜; tagging the guards and settling the 403-vs-422 question is a **Catalog** change, in a module whose pass is closed. **Done 2026-08-23 — both questions settled (Chase): the catalog's 403 wins and the code changed to `Forbidden`; `ReviewerAlreadyDecided` wins the name** | `error-catalog.md §Catalog — MediaItems` / `MediaItem.cs:271,276,768,773` |
| ☑ | **CR-20** | **High** | *Added 2026-08-23 opening step 4.* **`GET /v1/change-requests/{id}/comments` threw on every call.** `ListChangeRequestCommentsHandler` called `reader.QueryIndexAsync`, which resolves `IProjectionIndexSchema<ChangeRequestCommentReadModel, ListChangeRequestCommentsQuery>` from DI — a pair never registered. The query was also a `TenantScopedIndexQuery` registered via `AddResultQuery`, so nothing lined up. Fixed by listing the group partition the comments are already stored in; no index was ever needed | `ListChangeRequestCommentsHandler.cs:15` / `ChangeRequests.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:61` |
| ☑ | **CR-21** | Med | *Added 2026-08-23 as the other half of CR-15.* **A withdrawn submission's comment thread stays open forever.** Publication now closes both requests, but withdrawal also ends a review and cannot be observed from this context — `MediaItemWithdrawn` is a **domain-internal** event with no integration counterpart. Closing it needs a new `MediaItemWithdrawnIntegrationEvent`, a new SNS message type, an entry in the `cdk-magiq-media` queue subscription filter, and a consumer. Deliberately not smuggled into the spec-rewrite pass. **Done 2026-08-23, and it was bigger than written — see CR-22** | `MediaItem.cs:1149`; no file in `Catalog.Contracts/Events/MediaItems/` |
| ☑ | **CR-22** | **High** | *Added 2026-08-23 opening CR-21.* **Rejection leaks a comment thread exactly as withdrawal does, and CR-15 had recorded the opposite as a decision.** `Apply(MediaItemRejected)` clears `_activeReview` like the other two outcomes, and `PublishMediaItemHandler:85` mints `ChangeRequestId.New()` on **every** submission — so the thread a rejection abandons is never referenced again. `breaking-changes.md` said the thread was deliberately left open because "the discussion is exactly what is still live"; it was live in a thread the next submission would never look at. One stranded `Open` request per rejection, accumulating across revisions. Cheaper than CR-21 — `media.item.rejected` was already published, though **not** in the CDK allowlist. Reversal sanctioned by Chase | `MediaItem.cs:788`; `PublishMediaItemHandler.cs:85`; `sqs-queues.ts:201-206` |
| ☑ | **CR-23** | **High** | *Added 2026-08-23 during CR-21 verification.* **Every auto-raised comment thread was seeded with participant ids nobody holds.** `Catalog.ValueObjects.MemberId` is a `record struct` with **no `ToString()` override**, so the compiler-generated one renders `MemberId { Value = user-1 }`. `MediaItemDomainEventMapper` used `.ToString()` for `SubmittedBy` and `ReviewerIds`, and `MediaItemPublicationRequestedEventHandler:33,40` rehydrates them with `MemberId.From` — so `AddComment`'s participation guard matched no actor and **nobody could comment on the thread their own review had just opened**. `ChangeRequests.ValueObjects.MemberId` has carried the override, with a comment naming this exact trap, since its own snapshot round-trip hit it | `Catalog.Domain/ValueObjects/MemberId.cs`; `MediaItemDomainEventMapper.cs:133,136` |
| ☑ | **CR-19** | Low | *Added 2026-08-23 during the CR-2 verification.* **Guard order disagrees between commands.** `AddComment` checks `IsOpen` before participation — deliberate and commented, so a closed thread reads as closed to an outsider rather than as "you are not a participant". `Resolve`/`Abandon` check participation first, so the same stranger gets 403 there and 422 from `AddComment`. Either order is defensible; the disagreement is not. Needs a decision, then one comment and one test · **Decided and fixed 2026-08-24 — state-first.** `Resolve`/`Abandon` reordered to match `AddComment`, `EditComment` and `DeleteComment`, which were already 3–2 in favour. Rule written into `MayClose`, the write-model spec, and the error catalog; precedence published per route | `ChangeRequest.cs:139,160,196` |
| ☑ | CR-17 | Low | Dead footprint of the superseded CR-first saga: `SagaOrchestrator.csproj` still references `ChangeRequests.Domain`, `.WriteModel` and `.WriteModel.Infrastructure` under the comment *"ChangeRequests domain events (MCRApproved, MCRRejected) and commands (CreateMCR)"*. None of those types exist, and the ADR records that the saga is not built | `SagaOrchestrator.csproj:38-41` |

> Note: the read-model spec's self-flagged "⚠ Status note — corrected 2026-08-20" (Binding/CheckoutBound/SubmissionBound unimplemented) is **accurate** — verified, not counted as drift. The write-model spec's status note is likewise honest, but `mediachangerequest.api.md` and `context-overview.md` carry **no such caveat** and read as shipped contract — the same documentation problem flagged for DocumentSigning in §H.
>
> Architecture observation, out of scope but worth a ticket: `ChangeRequests.ReadModel.Endpoints` is referenced by **both** `Api` and `QueryApi`, so read routes are served from the write host too.
>
> Confirmed still open from §I.9: **X-9.1** — `EditSessionId.New()` and `ReviewSessionId.New()` are still `Guid.NewGuid()`, while Catalog's own `ChangeRequestId.New()` uses `GuidFactory.CreateVersion7()` two files away.

### F.3 Suggested order for this module

1. ~~**CR-4 alone.**~~ **Done 2026-08-23.** It could not be done alone in the end — the cap question forced CR-10 first, and once CR-10 was decided the poison pill disappeared rather than being patched. See the session log.
2. ~~**CR-11 + CR-6.**~~ **Done 2026-08-23.** CR-6 was cheap as predicted. CR-11 was not — it turned up a platform gap (N.2.4) that changed what could be implemented, and it costs a `schemaVersion` bump and the backlog's tenth rotation.
3. ~~**CR-2 + CR-12 + CR-13 + CR-14.**~~ **Done 2026-08-23.** The error-code pass, same shape as Catalog, Metadata and Registration. Turned up **CR-18** on the way through.
4. ~~**CR-3 + CR-7 + CR-8 + CR-5.**~~ **Done 2026-08-23.** Read-side contract fixes. Turned up **CR-20** before any of them could be tested.
5. ~~**CR-1 + CR-9 + CR-15 + CR-16.**~~ **Done 2026-08-23**, with CR-17 folded in. The spec rewrite, last, so it documents what actually shipped. **Section F is closed** apart from CR-18 (Catalog-owned), CR-19 (a decision) and the withdraw half of CR-15.
6. ~~**CR-18 + CR-21.**~~ **Done 2026-08-23.** The two Catalog-owned leftovers, taken together because both live in `MediaItem`'s review guards. Turned up **CR-22** (rejection leaks the same thread, and CR-15 had recorded the opposite as a decision) and **CR-23** (a missing `ToString()` made every auto-raised thread uncommentable). **Only CR-19 remains in F.**
7. ~~**CR-19.**~~ **Done 2026-08-24.** The decision, resolved to state-before-authorization on the evidence of the other three commands and of `MediaItem`. **Section F is closed.**

---

## G. Processing

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | **P-1** | **High** | `ProcessingJobFailed` → `status = Failed`, `statusText = <reason>` | Sets `Status = nameof(ProcessingJobStatus.Succeeded)`. **Every failed job reads back as Succeeded** | `processingjob.read-model.md` / `ProcessingJobSummaryProjector.cs:67` ✅*verified* |

**Aligned:** no HTTP endpoints (spec is correct); the `Queued→Running→Succeeded|Failed` transitions, the `Bypassed` idempotent no-op, and the timeout-recovery path all match spec exactly; failure taxonomy matches the consolidated ADR.

---

## H. DocumentSigning

**Quantified gap: 27 non-generated `.cs` files across 5 projects — the events-and-value-objects skeleton only.** Present: 9 domain event records, 7 value objects, 2 read models, 1 projector, 2 DI extensions, 4 service interfaces. **Absent: the aggregate, all 9 commands, all 9 handlers, the repository, all 12 endpoints, 2 of 3 projectors, all 3 query handlers, the saga, the timeout scanner, and the webhook implementation.**

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | **DS-4** | **High** | `SigningSessionDetailReadModel(TenantId, Id, MediaItemId, …)` | Projector constructs `(e.SigningSessionId, e.TenantId, e.MediaItemId, …)` — **`TenantId` and `Id` transposed.** Every row stores the session id in the tenant field | `read-model.md` / `SigningSessionDetailProjector.cs:33-47` ✅*verified* |

> **The documentation problem here is sharper than the code gap.** `write-model.md` and `read-model.md` both self-flag that the aggregate doesn't exist. `api.md` and `context-overview.md` carry **no such caveat** and read as shipped contract.

### `CLAUDE.md` deferred-work claims — corrected

| Claim | Reality |
|---|---|
| `DocumentSigningSaga` "not registered in `SagaRegistrations`" | **No such class exists anywhere.** "Not registered" implies it's written but unwired |
| `SigningSessionSummaryProjector`, `DocumentSigningTimeoutScanner` not implemented | ✅ Accurate |
| `MediaItemReviewSaga` "partial — missing closing handlers" | **It does not exist at all.** Repo-wide grep for `MediaItemReviewSaga`/`ReviewSaga` across `src/` and `tests/` → 0 matches. `api-conventions.md:364` lists it as the saga behind `POST /v1/items/{id}/submit` — an endpoint that also doesn't exist (C-4) |
| `POST /v1/test/sagas/{sagaId}/expire` | Confirmed not implemented, consistent with its own R-18 marker. Its sibling `POST /v1/assets/{id}/uploads/confirm` **does** exist but is **not environment-gated** — spec says test utilities must 404 in production |

---

## I. Architecture, hosts & cross-cutting

### I.1 Hosts


### I.2 JWT replay detection

_Removed 2026-08-21 — deferred to the auth plan. Numbering left intact so existing references to X-3.x onward still resolve._

### I.3 Integration event publishing


> X-3.1 is the one hard SDK constraint the application materially breaks. Whether to adopt the outbox or formally amend the platform SDK's stated rule is an architecture decision, not a bug fix — but the current state, where an ADR says one thing and the SDK it depends on forbids exactly that, should not persist undocumented.

### I.4 Tables & infra

| ✓ | # | Sev | Doc says | Reality | Ref |
|---|---|---|---|---|---|
| ☑ | X-4.1 | Med | Three buckets: `media-source`, `media-renditions`, `media-documents` | CDK provisions `magiq-media-originals`, `-renditions`, `-quarantine`. `media-documents` was retired 2026-07-17 — `system-architecture.md:403` records it, but `system-spec.md` and `bounded-context.md` still list it **with a lifecycle rule** | `system-spec.md:692-706` / `media-buckets.ts:89,128,158` |
| ☑ | X-4.2 | Med | — | **`magiq-media-quarantine`** is provisioned (infected assets, no app-role access) and appears in **no** spec S3 table | `media-buckets.ts:43,158` |
| ☑ | X-4.3 | Low | Bucket identifier `media-source` | No such bucket; physical name is `magiq-media-originals-{account}-{region}`. Runtime unaffected (names injected as env vars) but the spec identifier is unresolvable | `system-spec.md:694` |
| ☑ | X-4.6 | ~~Low~~ **Med** | `system-spec.md`'s canonical table list omits `media-folder-locks` and `read-model-metadata` | **Understated — it omits ten.** Also missing: `media-catalog-folder-registration-index`, `media-catalog-item-profile-index`, `media-catalog-asset-item-index`, `media-catalog-version-asset-ref`, `media-catalog-record-type-index`, `media-asset-profile-default-ref`, `media-processing-asset-index`, `media-profile-version`. Plus one table listed under the **wrong name** (`media-catalog-record-type-ref`), one **fictional** (`media-folder-hierarchy` — no CDK resource, no `FolderHierarchyNodeReadModel` in code), and one with the **wrong SK** (`media-catalog-folder-items-index` keys on `{FolderId}`, not `{MediaItemId}`) | `system-spec.md:630-667` / `write-indexes.ts`, `platform-tables.ts`, `projection-tables.manifest.json` |
| ☑ | X-4.8 | **Med** | `system-spec.md`: `media-profile-version` / `media-profile-versions` keyed PK `…#{MediaProfileId}`, SK `{VersionNumber}` | **Reversed in code.** Both call `new ProjectionKey<T>(tenantId, mediaProfileId, version.ToString("D10"))`, and the 3-arg ctor is `(tenantId, discriminator, groupKey)` — discriminator→SK, groupKey→PK suffix. Actual: PK `TENANT#{TenantId}#PROFILE_VERSION[S]#{Version:D10}`, SK `DETAIL#`/`SUMMARY#{MediaProfileId}`. So **every "version 1" row for every profile in a tenant shares one partition**, and a profile's history can't be read with a base-table `Query` — which is why `ListMediaProfileVersions` needs the `MediaProfilesByVersionIndex` GSI. *Found 2026-08-24 verifying X-4.6* | `MediaProfileVersionDetailReadModel.cs:16`; `…SummaryReadModel.cs:15`; `ProjectionKey.cs:20` |
| | | | | **Spec aligned to the repo 2026-08-24.** `system-spec.md` had already been corrected in the X-4.6 pass; four other documents had not, and three of them were worse than the key shape. `system-architecture.md` carried both rows with **no version segment in the PK and a bare `{discriminator}` SK** — wrong on both keys — and its GSI section listed neither `MediaProfileByNameIndex` nor `MediaProfilesByVersionIndex` despite the `media-profile` row saying "see GSI notes below". Its projector table named a `MediaProfileVersionProjector` that does not exist and omitted `MediaProfileSummaryProjector`. `system-spec.md`'s own projector table repeated both errors. **`mediaprofile.read-model.md` was the worst of it**: it described a *single* `media-profiles` table holding current-state and version rows side by side, a `MediaProfileVersionReadModel` type deleted in the Detail/Summary split, an `OwnerStatusIndex` GSI that was never provisioned, a `ListMediaProfilesByOwnerQuery` that never existed, and a `MediaProfileProjector` that never existed — the actual design is 4 tables, 4 read models, 4 projectors, 2 GSIs. All corrected against `ServiceCollectionExtensions.cs:168-174`, the four schema classes and `projection-tables.manifest.json`. **The key shape itself was not changed** — it is documented as-is, with the hot-partition consequence and the constructor trap called out in three places. Whether to re-key remains open; see X-4.10 | |

**Aligned:** `media-events`, `media-sagas` (+ GSI), `media-name-reservations`, `media-idempotency-keys`, `media-tenants`, `media-migrations`, `media-catalog-record-type-index`; both SNS topics; all five SQS pairs with DLQs and depth alarms. Read-model tables are manifest-driven, the two manifest copies are byte-identical, and CI enforces it with a drift gate.

> **Closed 2026-08-24** — X-4.1, X-4.2, X-4.3, X-4.6. X-4.4 and X-4.5 deferred to the queues pass. X-4.7 opened by the same pass. See the session log entry.
>
> After the fix, `system-spec.md`'s inventory and the CDK are a **clean two-way match** — 46 tables, zero on either side that the other doesn't have. The check is scriptable and worth rerunning before anyone trusts the list again: parse `tableId` out of `projection-tables.manifest.json`, plus the `resourceName(config, '…')` / `projected(…)` literals in `write-indexes.ts`, `platform-tables.ts` and `event-store.ts`, and diff against the leading `` `table` `` cell of each row in the spec table.

### I.5 Branching & deployment


### I.6 Wiki publish workflow

| ✓ | # | Sev | Doc says | Reality | Ref |
|---|---|---|---|---|---|
| ☑ | X-6.1 | **High** | Both `CLAUDE.md` files: spec and ADRs "publish to the ADO wiki **automatically** on merge to `develop` via `.github/workflows/publish-wiki.yml`"; "**Don't hand-edit `Media.wiki`** — it's a generated artifact now" | **The workflow does not exist.** `.github/workflows/` contains exactly one file: `build-and-push.yml`. Nothing has ever published `docs/` to the wiki. The ADO wiki has been drifting since 2026-07-07 *and* the no-hand-edit instruction has left it with **no update path at all**. The Z:\ project instructions ("planned but not yet built") are the correct version | both `CLAUDE.md` / `ls .github/workflows/` ✅*verified* |

> Treat the published `Media.wiki` as **untrustworthy** until the workflow is built and run once. Anyone reading module reference pages there is reading pre-migration content.

### I.7 Plans folder


### I.8 Stale references & broken links


### I.9 Platform SDK conventions

| ✓ | # | Sev | Finding | Ref |
|---|---|---|---|---|
| ☑ | X-9.1 | Med | "Do not use `Guid.NewGuid()`" — two violations, both Catalog MediaItem edit-lifecycle VOs. These IDs are not time-sortable, unlike every other ID in the system | `EditSessionId.cs:10`; `ReviewSessionId.cs:7` ✅*verified* |
| ☑ | **X-9.5** | Med | **Both `CLAUDE.md` files, the platform's `CLAUDE.md`, `system-spec.md`, the Z:\ `CLAUDE.md` and `service-boundaries.md` all name MediatR as the mediator** — the platform's even pins "MediatR 13.1.0". **It is not used anywhere.** Zero references across `src/` and `tests/` in *either* repo. Dispatch is `ICommandDispatcher` from `Magiq.Platform.WriteModel.Commands`. Every stack table on the platform is wrong about a first-order architectural component, and a new contributor would go looking for `IRequestHandler` · *Found 2026-08-24* | `Directory.Packages.props` (platform repo) |
| | | | | **Corrected 2026-08-24 across 11 documents.** Fixed: both `CLAUDE.md` files, the platform `CLAUDE.md`, the Z:\ `CLAUDE.md` and `brief.md` (stack tables now read *Command dispatch — `ICommandDispatcher`, not MediatR*); `system-architecture.md` (ASCII topology box, Ingest API and Command Handler service descriptions); `bounded-context.md` (4 sites, incl. the topology diagram and the service table); `system-spec.md` (2 sites); `AssetManagement/context-overview.md`; `mediaprofile.defaults.md`. `service-boundaries.md` already carried a correction note from the X-1.6 rewrite — tightened, see the finding correction below. Where the naming mattered architecturally the replacement says *how* rather than just *what*: cross-cutting concerns are `ICommandMiddleware` implementations composed in registration order by `CommandPipelineFactory`, **not** `IPipelineBehavior`s — that is the thing a contributor arriving from MediatR would get wrong next. **One correction to the finding itself:** "zero references … `Directory.Packages.props` in *either* repo" is wrong. `aspnetcore-platform/Directory.Packages.props:40` still declares `<PackageVersion Include="MediatR" Version="13.1.0" />`. Central version management does not pull a package in and no `.csproj` references it, so nothing consumes it — but the line is where the "MediatR 13.1.0" claim in the platform's stack table came from, and it should be deleted. **Left in place: that is a code change, not a doc change** | |

**Verified compliant, with the checks run:** central package versions — zero `Version=` attributes across every `.csproj` in `src/` and `tests/`. FastEndpoints not MVC — zero `ControllerBase`. No EF/SQL — no `EntityFramework`, `SqlClient`, `DbContext` or `Npgsql` in `Directory.Packages.props`. All 9 implemented aggregates extend `EventSourced<…>` **and** implement `ITenantScoped`, and every per-module domain-event interface is `ITenantScoped` too. `net8.0` throughout; FastEndpoints 6.2.0 as specced.

### I.10 Error catalog


Codes present in both catalog and code (8, all MediaItem checkout / ChangeRequest state): `CheckoutLeaseExpired`, `CheckoutNotLeased`, `CheckoutRequired`, `MediaItemCheckedOut`, `MediaItemNotCheckedOut`, `MediaItemNotCheckoutable`, `TooManyCollaborators`, `ChangeRequestNotOpen`.

---

## J. Where the spec is wrong, not the code

Worth separating, because these are doc-only fixes with no code risk:

| ✓ | Item | Which half is stale |
|---|---|---|
| ☑ | AM-22 | `asset.read-model.md` claims `AssetValidationPassed` changes status; `asset.api.md:601` and the code agree it doesn't |
| ☑ | AM-27 | `asset.api.md` (400) vs `error-catalog.md` (422) for `AssetTooLarge` — code follows the API doc |
| ☑ | AM-21 | `api-conventions.md` mandates `mediaItemId`; `asset.api.md:71` itself says `itemId`. Code follows the wrong half. **Not doc-only after all** — the spec's own error list and guards already said `mediaItemId`, so only the request example was stale; the wire needed a second accepted spelling to converge without a break |
| ☑ | C-3 | `api-conventions.md §Async` and `bulk-operations.md` contradict each other on bulk 202. **Neither half was right** — both docs and the code now say `201`/`200` |
| ☑ | MI-6 | `mediaitem.write-model.md` prose guard says `Draft` only; its own state diagram and the code allow `Revising` |
| ☑ | MediaItem ETag | `api-conventions.md §Coverage` names the field-level route `PUT`; code and `mediaitem.api.md` both use `PATCH`. **Doc-only was the wrong classification** — the verb had already been corrected 2026-08-22 and the box merely never ticked, but auditing it surfaced three live findings (MI-8, MI-9, MI-10), one of which is the spec describing shipped behaviour as future work |
| ☑ | CO-4 | `collection.write-model.md` says caller-generated ID; `collection.api.md` says server-generated. **Resolved as both** — `collectionId` is now optional on the request, server-generated when omitted (AIP-133) |
| ☑ | M-10 | Spec's `id` contradicts ADR-012 rule 3; the code's `recordTypeId` is correct. **Resolved 2026-08-22 in the code's favour** on `recordTypeId` and `versionNumber`; `aliases` was the half the spec had right and is now projected |
| ☑ | R-18 | `registration.read-model.md:149` claims `from`/`size` pagination, contradicting the API spec, the ADR, and the code |
| ☑ | P-10 | `processingjob.read-model.md` status enum is stale against its own write-model file. **Wider:** the projection tables also omitted `ProcessingJobTimeoutRecovered`, which both projectors implement |
| ☑ | CR-9 | The write-model spec is **behind** the code — governance lifecycle is shipped, spec calls it "a future increment". *Widened 2026-08-22:* all four `MediaChangeRequest` spec files plus `context-overview.md` predate `adrs/editing-lifecycle-and-concurrency.md`. **Closed 2026-08-24** — the 2026-08-23 pass had covered three of five files; both scenarios files were still on the superseded model |
| ☑ | CR-1 | *Added 2026-08-22.* `mediachangerequest.api.md` says there is no create endpoint; the ADR makes client-created change requests the design. The spec is the stale half. **Verified fixed 2026-08-24** — corrected in api.md on 2026-08-23, box never ticked |
| ☑ | CR-6 | *Added 2026-08-22.* The six "undocumented fields" on the detail response are the ADR's governance fields — the spec is behind, not the code. Only `ownerId` vs `createdById` is genuine drift. **Verified fixed 2026-08-24** — aggregate renamed to `OwnerId` 2026-08-23; three persisted/published contracts deliberately left, and that residue is now documented on the property |
| ☑ | X-1.1 | Z:\ `CLAUDE.md` "single `Media.Api` host" is wrong; the repo is correct. **Fixed 2026-08-24** — replaced with the real nine-host table; also corrected `ChangeRequest`→`MediaChangeRequest` and flagged DocumentSigning as skeleton-only |
| ☑ | X-1.6 | `service-boundaries.md` (2026-03-11) predates the 9-host split entirely — recommend rewrite or retirement, not patching. **Rewritten 2026-08-24** — topology replaced against the real nine hosts, stale command/projector inventories dropped in favour of pointers, contracts and Rules kept and corrected. 370 → 281 lines |

---

## L. Suggested triage order

1. **Today** — P-1, M-6, DS-4 projector corrections; AM-6 delete ordering.
2. **This week** — X-6.1 build `publish-wiki.yml` (until then the wiki misleads everyone who isn't reading the repo); X-5.1 add the `PROD_ENABLED` guard to the CDK repo's `deploy.yml`; correct the two false `CLAUDE.md` claims (wiki auto-publish, `Media.Api`) since they actively mislead both people and AI assistants.
3. **Next** — owner-scope authorization per module (AM-2, C-2, CO-1, R-3/R-8, M-4); C-1 pageSize clamp; R-6 OpenSearch mapping; the projector coverage gaps (AM-4/8/9, P-3, M-7).
4. **Backlog** — caveat `documentsigningsession.api.md` and both BulkImportJob API specs as unimplemented (or move them to a `proposed/` folder) so published contracts stop describing absent code; X-3.1 outbox decision; retire or rewrite `service-boundaries.md`; the response-shape and error-status corrections.
5. **Doc-only sweep** — everything in §J, which carries no code risk.

---

## M. Session log

### 2026-08-21 — fix-first pass

| Item | Action | Files |
|---|---|---|
| P-1 | **Investigated, then fixed.** Not a workaround — a plain copy-paste bug (see verdict below). `Status` now projects `Failed`; test extended to assert `Status`, which it never did | `ProcessingJobSummaryProjector.cs`, `ProcessingJobSummaryProjectorTests.cs` |
| AM-6 | **Fixed.** `asset.Delete()` guards now run before `DeleteObjectsAsync`. Failure semantics otherwise unchanged (S3 throw ⇒ aggregate unsaved ⇒ 500). Regression test added for an aggregate-rejected delete | `DeleteAssetHandler.cs`, `DeleteAssetHandlerTests.cs` |
| M-6 | **Fixed**, and M-7 with it — the whole `HasDraft` lifecycle: `DraftCreated` → `true`, `DraftDiscarded` → `false`, `Published` → `false`. `IsDeprecated` no longer touched on discard | `RecordTypeSummaryProjector.cs` |
| DS-4 | **Fixed.** Argument order corrected and the call converted to named arguments so two adjacent same-typed `string` parameters can't transpose again | `SigningSessionDetailProjector.cs` |
| X-6.1 | **Resolved by retirement.** `Media.wiki` is obsolete; no `publish-wiki.yml` will be built. All auto-publish claims and "don't hand-edit the wiki" instructions removed from both `CLAUDE.md` files and `docs/README.md` | both `CLAUDE.md`, `docs/README.md`, `asset.write-model.md` |
| X-3.1 | **Deferred** by decision — outbox adoption revisited later | — |
| R-6 | **Fixed.** Mapping renamed `RegistrationId` → `Id` to match the read model (ADR-012 rule 1 makes the model the correct half), sort key updated. **MI-7 fixed at the same time** — the identical defect on the MediaItems index | `RegistrationsIndexMapping.cs`, `SearchRegistrationsHandler.cs`, `MediaItemsIndexMapping.cs`, `SearchMediaItemsHandler.cs`, `ListAllMediaItemsHandler.cs` |

### 2026-08-21 — AssetManagement pass

`☑` done · `⊘` deliberately skipped · `☐` outstanding. Legend applies to §B.

**Done (23):** AM-2 · AM-3 · AM-4 · AM-5 · AM-6 · AM-7 · AM-8 · AM-10 · AM-11 · AM-12 · AM-14 · AM-15 · AM-16 · AM-17 · AM-18 · AM-19 · AM-20 · AM-22 · AM-23 · AM-24 · AM-25 · AM-26 · AM-27 · AM-28

**Skipped on instruction:** AM-9 (VersionArtifact projector coverage — **reopened, re-scoped to High and closed 2026-08-23**; the skip was reasonable given how the row was written and wrong given what was behind it), AM-21 (`itemId` vs `mediaItemId` — **reopened and closed 2026-08-23**, see that pass below).

**Outstanding:** AM-1 and the tail of AM-13 — see below.

#### Determinations that went against the finding

| Item | Determination |
|---|---|
| AM-15 | **Not a code bug.** `FailureCategory.ValidationError` is the label the integration-event mapper stamps on `AssetValidationFailed`; it was never a `FailProcessing` category. `UploadExpired` is valid only from `Pending`. The stage matrix is correct as implemented — the spec's "Validating or Processing" made `UploadExpired` unreachable and would have broken upload-expiry. Guard untouched; `asset.write-model.md` now carries the full matrix. |
| AM-27 | **Keep `400`.** The declared `sizeBytes` is a request field checked against a bound the server already knows, before anything is created — request validation, which this platform maps to `400`. `asset.api.md` and the code already agreed; `error-catalog.md` was the lone dissenter and has been corrected. |
| AM-19 | **Add neither field.** `LastAssetEventVersion` duplicates the platform's `ProjectedVersion` (`IVersionedProjection`), which the dispatcher already uses for dedup and the DynamoDB store for conditional writes — a second copy of the same number is a divergence waiting to happen. `EventId` adds nothing to correctness (dedup is version-based, versions are monotonic per stream) and `DomainEvent` carries no event id to project. Read-model spec updated to say so. |
| AM-11 | **Spec was right, code was wrong** — the reverse of the finding's framing. `asset.api.md` already documented the three-part envelope with `name` and `skipped` and no 422. The endpoint was fixed to match. |

#### Beyond the findings

- **Bulk-confirm had no owner check** (not in the review). Guarding single confirm while leaving bulk open is a straight bypass — a caller could confirm any tenant user's uploads by listing their ids in a batch. Added as a per-item `Forbidden` so one foreign id doesn't discard a legitimate batch.
- **`BulkOperationsOptions` never bound.** AssetManagement declared the root-level section `"BulkOperations"`, which matches nothing in any deployed config — the only bulk block is Catalog's. Its options always fell back to compiled defaults, so the cap was never enforced. Section is now `Media:AssetManagement:BulkOperations`, default 100, with an `appsettings.json` block. The review's "deployed config sets 200" is Catalog's value, which nothing reads.
- **`BillingAcl.CheckQuotaAsync` is not a quota check.** It compares a *single file* against `MaxTotalBytes` and never reads consumed usage — so a tenant with a 1 TB quota can upload unlimited 999 GB files. Unrelated to any AM finding; needs its own ticket.

#### Closed since — AM-1, AM-13, AM-16

| Item | Resolution |
|---|---|
| AM-1 | **Built.** New `POST /v1/assets/uploads/bulk`: command + item/result records, handler, endpoint with request/response models, DI registration, 9 tests. Follows the module's bulk shape (parallel pre-flight → classify → FailFast short-circuit → batched write → ordered output) and mirrors every single-upload guard. Capabilities resolve once per *distinct* media item; the batch persists through one `TransactWriteItems` per chunk. Written fresh — commit `9381b7e9` was **not** reverted, as it calls a removed `Generate` overload and encodes the pre-S12 quota rule. |
| AM-13 | **Complete.** Both initiates → `201`. `confirm` → `202` with **no body** (moved to the body-less base). `abort` → `204` (it is synchronous and complete on return). Two now-orphaned response records remain on disk — see below. The context's status-code convention is now written into `asset.api.md § Authorization Requirements`. |
| AM-16 | **Corrected — the original guard was wrong.** `AssignAssetToRoleHandler:53-54` states outright that assignment carries *no* status constraint ("status only gates presigned GET URL issuance"), and its auto-submit path has an explicit backstop for roles filled before the asset reaches `Active`. Requiring `Active` would have broken drag-and-drop → assign → process and failed `ApplyAssetAssignment` for an assignment Catalog had already committed. The guard is now an allow-list of non-terminal statuses — `Pending`, `Validating`, `Processing`, `Active`, `Archived` — excluding only states that can never become servable. Allow-list, not deny-list, so a status added later must be considered explicitly. |

#### The three off-review findings — all fixed

| Finding | Fix |
|---|---|
| Bulk-confirm had no owner check | Per-item `Forbidden` in the classifier, so one foreign id does not discard a legitimate batch. |
| `BulkOperationsOptions` never bound | Section renamed to `Media:AssetManagement:BulkOperations`, default 100, `appsettings.json` block added, cap enforced at both bulk endpoints. |
| `BillingAcl` was not a quota check | Now enforces `MaxSingleUploadBytes` (default 50 GB) — the only limit decidable from the request. `MaxTotalBytes` is documented as **not enforced**, because consumed-usage accounting lives in Billing and there is no usage read model here. The old code compared the *total allowance* against a *single file*, so a 1.5 TB allowance permitted unlimited 1.4 TB uploads. |

#### Decisions taken while building AM-1

- **Caller-generated UUID v7 ids, required.** No idempotency middleware exists anywhere in this platform (`bulk-operations.md § Idempotency` describes one; a repo-wide search finds nothing), so caller-supplied ids are the only retry-safety mechanism actually available. Server-generated ids would turn one 504 into a hundred duplicate assets. `asset.api.md` updated — it previously specified server-generated.
- **A duplicate id is reported as success, not failure.** The asset exists and the returned pre-signed URL addresses it correctly, because the storage key is derived deterministically from tenant + assetId + extension. A retry therefore hands back a usable URL rather than an error the caller cannot act on.
- **`bulk-operations.md` was wrong about how that works.** It claimed the event store "treats a pre-existing aggregate as a no-op success". It does not — `DynamoDbEventStore` raises `EventConcurrencyException`. Each handler decides what a conflict means, and the two asset endpoints differ deliberately: initiate treats it as success, confirm as `ConcurrencyConflict`. Corrected in the shared doc, including the trap that `EventConcurrencyException` derives from `InvalidOperationException`, **not** `DomainException` — so bulk-confirm's `catch (DomainException)` does not see it.
- **`IAssetRepository.TrySaveNewAsync` added** rather than catching the exception in the handler. `EventConcurrencyException` ships in `Magiq.Platform.EventSourcing.DynamoDb`; catching it in the application layer would drag a persistence technology across the layer boundary. Infrastructure translates it to a boolean; every other failure still throws.

#### Still open

| Item | State |
|---|---|
| Unbounded SNS fan-out | `AwsMessageBusEndpoint.DeliverBatchAsync` uses a bare `Task.WhenAll` with no `MaxDegreeOfParallelism`. It lives in the **platform SDK**, consumed via NuGet, so it cannot be fixed from this repo. In practice the AWS SDK's connection pool (50 per client) bounds it, and a 100-item batch is comfortably inside the 29 s Lambda/APIGW ceiling — but it is the one un-throttled step in the path and deserves a platform ticket. |
| Two orphaned files | `ConfirmAssetUploadResponse.cs` and `AbortAssetMultipartUploadResponse.cs` are now unreferenced. The sandbox cannot delete on that mount — remove them by hand. |
| `bulk-confirm` exception handling | Its `catch (DomainException)` cannot catch `EventConcurrencyException`, so the per-item retry path may never trigger. Not touched; worth its own look. |

### 2026-08-21 — Catalog cross-cutting pass (C.1)

**Done (5):** C-1 · C-3 · C-4 · C-5 · C-6. **Skipped on instruction:** C-2 (owner-scoped authorization).

> ⚠ **Not compiled.** The sandbox has no `dotnet`, so nothing below has been built or tested. Build
> `Catalog.Domain`, `Catalog.WriteModel`, `Catalog.ReadModel(.Endpoints)`, `AssetManagement.WriteModel.Endpoints`
> and run `Catalog.WriteModel.Tests` + `Catalog.ReadModel.Tests` before pushing.

| Item | Resolution |
|---|---|
| C-1 | **Fixed.** New `CatalogPaging` (`Catalog.ReadModel/Queries/Pagination/`) holding `DefaultPageSize = 20`, `MaxPageSize = 100`, `ClampPageSize` and `CursorPager`. All 8 Dynamo-backed list endpoints now build their pager through it (the review said 6; there are 8). The two OpenSearch handlers dropped their inline `Math.Clamp(…, 1, 100)` for the same constants, so the number lives in one place. 11 unit tests. |
| C-3 | **Both spec halves were wrong.** Resolved in favour of neither — see the decision below. Applied to all 6 Catalog bulk endpoints **and** the 2 AssetManagement ones, plus `bulk-operations.md` and `api-conventions.md`. |
| C-4 | **Fixed, and it turned out to be bigger than a rename.** `POST /items/{itemId}/publish` now returns `200 OK` with `{ status, changeRequestId? }` and no `Location` header. |
| C-5 | **Implemented for the whole Catalog context.** 105 raise sites tagged with `.WithCode(...)` across Collections, Folders, MediaItems and MediaProfiles; three new code classes; `error-catalog.md` rewritten with a ✅/⬜ column so a client can tell a live code from an aspirational one. |
| C-6 | **Fixed.** `ChangeRequestRequired` and `ChangeRequestNotOpen` both added to the Catalog — MediaItems table, with a note that the latter has two raise sites in two contexts. |

#### C-3 — partial success is `200`, not `202` (and not `207`)

The two shared docs contradicted each other and the code followed a third convention in one place. The
resolution went against both:

- A bulk endpoint runs its whole batch **inside the request**. Every item has a final outcome by the
  time the response is written. `202 Accepted` means "not finished, come back later" (RFC 9110
  §15.3.3) — it is the signal a client uses to decide *to keep polling*. Returning it for finished
  work tells clients to wait for something that will never happen.
- `207 Multi-Status` (which `POST /items/bulk-metadata` was returning) is a WebDAV code whose body is
  defined to be a `multistatus` **XML** document. It does not describe a JSON envelope, and generic
  clients and proxies treat it as an unrecognised 2xx.
- Rule now: **every item succeeded and the endpoint creates resources → `201`; anything else the batch
  actually processed → `200`; request-level fault → `400`.** All-failed is still `200` — per-item
  failures are domain outcomes in the envelope, not a failure of the request (same reasoning that
  removed the all-failed `422` in AM-11).
- `bulk-paths` keeps its `Failed.Count == 0` test rather than also checking `Skipped`: `Existed` nodes
  are an idempotent success under mkdir -p semantics and ride in `skipped` only for envelope shape.

**AssetManagement was changed too, deliberately.** Leaving its two bulk endpoints on `202` would have
re-created the exact contradiction this finding is about, one day after closing it. It is also not a
reversal of AM-13 but an extension of it — `asset.api.md:54` already states the context's rule as
"`202` only where the request genuinely hands off to a saga or worker", and lines 94, 295 and 403 apply
that reasoning to three single-resource endpoints. The bulk pair were the two places the context did
not follow its own doctrine.

#### C-4 — the saga the spec was describing does not exist

`POST /v1/items/{id}/submit` and `MediaItemStatus.UnderReview` were the visible half. The real finding
is underneath: **there is no `MediaItemReviewSaga` type anywhere in `src/`** — the only saga in the repo
is `AssetIngestionSaga`. `PublishMediaItemHandler` is synchronous on both branches (no reviewers ⇒ the
aggregate auto-approves inline and lands on `Published`; reviewers ⇒ `PendingApproval`), and
`mediaitem.api.md` said so itself two paragraphs above the `202` it documented.

So the `202` + `Location` + `expectedStatus` shape was describing an architecture that was never built,
and pointing clients at a poll loop whose answer was already in the response body. Now `200 OK` with
`status` (a fact) instead of `expectedStatus` (a prediction), no `Location`. The `MediaChangeRequest`
is still created asynchronously by the ChangeRequests module — but that is a *different resource*
reaching its own initial state, not this request finishing.

Knock-on: `202` now has exactly **one live user** in the platform — `POST /v1/assets/{assetId}/confirm`,
which is a genuine hand-off to `AssetIngestionSaga` and was already correct per AM-13. It was missing
from the saga table entirely, so the table has been rewritten as *the complete list of async hand-offs*
rather than a partial one, with `POST /v1/items/{id}/signing-sessions` marked 🔧 unimplemented so the
convention survives for when DocumentSigning ships. Adding a `202` anywhere now means adding a row
with a named asynchronous consumer that actually exists.

#### C-5 — what was tagged, and what deliberately was not

- **Tagged (105 sites, 64 files):** every raise site whose condition the error catalog already
  published, plus the Folder/MediaProfile conditions that were being raised with no documented code at
  all (`FolderArchived`, `FolderAlreadyArchived`, `FolderAlreadyClosed`, `FolderHasActiveRegistrations`,
  `FolderAlreadyExists`, `MediaProfileNotFound`, `MediaItemNotFound`).
- **Not tagged:** MediaProfile's own draft/version refusals (no active draft, nothing to publish,
  capability not attached, asset-definition guards). They have no published codes, and inventing ~15
  would publish a contract ahead of any client need. Called out explicitly in the catalog rather than
  left as a silent gap.
- **Query-side left alone.** `QueryHandler.ResourceNotFound` returns `QueryError`, not `DomainError` —
  `.WithCode` does not apply, and the read-side 404s carry no code. Worth its own decision: the write
  side of `GET`-then-`PUT` now speaks codes and the read side does not.
- **Three catalog rows are now marked ⬜ "not raised"** rather than quietly left as contract:
  `CollectionArchived` (the aggregate reports `CollectionAlreadyArchived`), `DuplicateName` and
  `DuplicateTitle` (superseded by the per-aggregate `*AlreadyExists` codes), `FolderNotEmpty` (archive
  cascades instead of refusing) and `ParentCreationFailed` (a bulk-envelope item error, never a
  response-level code).
- `CircularFolderReference` is tagged at the two cycles the code actually detects — self-move and an
  in-batch `bulk-paths` cycle. **Descendant cycles are still undetected (F-1).** The code is honest
  where it fires; the guard behind it is not finished.

#### Beyond the findings

- **`ListFolderChildren` and `ListMediaItems` documented a `page` query parameter** in their Swagger
  summaries — offset pagination, on a platform where ADR-012 forbids it and the endpoints have never
  accepted it. Removed; both now document `pageSize`/`pageToken` with the cap.
- **`POST /items/{itemId}/reject` does not return the item to `Draft`** as `mediaitem.api.md` claimed —
  it restores `ReviewSession.OriginStatus`, so an item published from `Revising` goes back to
  `Revising`. There is a test asserting exactly this (`MediaItemReviewOriginStatusTests`). Spec
  corrected.
- **`approve`/`reject` documented `422 — media-item not UnderReview`.** Both guards check
  `PendingApproval`. Corrected — same root cause as C-4.
- **Two MediaProfile endpoints returned `202` for fully synchronous work** — `DELETE /profiles/{id}/draft`
  and `DELETE /profiles/{id}/asset-definitions/{roleName}`. Same defect as M-1/M-2 in the Metadata
  module, in a module nobody had looked at for it. Both now `200` with their existing body **unchanged**.
  Trimming to `204` was considered and **rejected (Chase, 2026-08-21)**: `profileId` is what the caller
  needs to fetch the profile by id afterwards, so the body is load-bearing rather than a courtesy echo,
  and dropping it would break clients for no gain. Status code moved, body untouched.

#### Still open after this pass

| Item | State |
|---|---|
| Nothing compiled | No `dotnet` in the sandbox. Build + test before pushing. |
| 16 `.fuse_hidden*` files | Sandbox litter under `Catalog.ReadModel.Endpoints/V1/**` from the first edit pass; the mount refuses to delete them. `git clean -fdx` on that folder, or delete by hand. They are not tracked and not referenced. |
| `DELETE /profiles/{id}/draft` + `.../asset-definitions/{roleName}` | Status code settled at `200`, body kept. Neither route has its own section in `mediaprofile.api.md` — only a line in the route table. Documenting them (and the two undocumented `PUT` routes) is MP-2, for the MediaProfile pass. |
| Clients consuming `POST /items/{itemId}/publish` | `expectedStatus` → `status` is the one wire-shape break in this pass, taken deliberately (Chase, 2026-08-21) rather than aliased, on the grounds that renaming now is cheaper than after more clients bind to it. Needs telling whoever reads that response — the UI most likely. Everything else in this pass changes status codes only, never a body. |
| Read-side error codes | Query 404s carry no `errorCode` because `QueryError` has no extensions bag. Needs a decision, probably at the platform level. |
| `UnderReview` elsewhere | `registration.scenarios.md:246,278` still names a `MediaItemStatus` member that does not exist, and the architecture docs describe `MediaItemReviewSaga` as deferred-but-real. Left for the Registration and architecture passes rather than swept here. |
| The other six modules | Their endpoint base classes still do not forward `errorCode`, so every code outside Catalog remains aspirational. One line each. |

### 2026-08-21 — Catalog Collection pass (C.2)

**Done (4):** CO-1 · CO-3 · CO-4 · CO-5. (CO-2 does not exist — the review numbers Collection findings
CO-1, CO-3, CO-4, CO-5.)

> ⚠ **Still not compiled** — no `dotnet` in the sandbox. This pass changes two command-handler
> constructors, so `Catalog.WriteModel.Tests` will not build until the two updated test files are
> compiled with them.

| Item | Resolution |
|---|---|
| CO-1 | **Removed from the spec.** The owner-scoped variant was never built and is not wanted: it would need an `OwnerId` GSI on `media-collections`, and owner-scoped access belongs with C-2, not bolted on as a query parameter. `collection.api.md` now documents the endpoint as tenant-scoped, with the removal and its reason recorded inline. Added the missing `GET /v1/collections` row to the traceability table while there. |
| CO-3 | **`name` implemented, `createdAt` removed.** `sortBy`/`sortOrder` now exist on `GET /v1/collections` and are resolved by a new `CollectionSort`. `sortOrder=desc` reverses the index walk — verified end to end: `PagerParameters.Descending` → `QueryRequestExtensions.WithPagination` → `ScanIndexForward=false` on the `QueryRequest` the projection store issues. 15 unit tests. |
| CO-4 | **Both spec files were wrong, and there was a live bypass underneath.** See below. |
| CO-5 | **Not needed — do not add it.** See below. |

#### CO-3 — an unsupported sort is a `400`, not a silent fallback

`createdAt` had been advertised on this endpoint for a long time with no `createdAt` index behind it,
so it was never actually sortable. Two ways to resolve that: serve name order anyway, or refuse.

Refusing is right here. A client that asks for `createdAt` and silently receives name-ordered results
gets a correctly-shaped response that is wrong in a way it cannot detect and cannot act on. A `400`
naming the field tells it immediately. The rule is now written into `api-conventions.md § Sorting` as
a general one — and it flags that `GET /v1/items` still falls back silently and should be brought into
line, which is a sibling endpoint's problem, not this one's.

Also caveated in the same place: the `folders` and `items` rows of the supported-sort-fields table
still claim `createdAt` and have **not** been re-verified against their indexes. Same defect shape;
they belong to the Folder and MediaItem passes.

#### CO-4 — the finding understated it: bulk create was a live invariant bypass

The finding reads as a documentation problem. Two of its three parts are; the third is a bug.

**The bug.** `SetDefaultMediaProfileHandler` enforces that a default profile must exist and be
`Published`. `BulkCreateCollectionsHandler` accepted `defaultMediaProfileId` on every item and
validated *nothing* — so a caller could write a default pointing at an unpublished, deprecated or
entirely non-existent profile simply by using the bulk endpoint. Same shape as the bulk-confirm owner
check found in the AssetManagement pass: the single-item path is guarded, the batch path is the way
in. Both create paths now run the same two checks; in bulk it is a per-item failure so one bad
reference does not discard the collections alongside it, and each distinct profile is resolved once
rather than once per item.

`POST /v1/collections` could not set a default profile at all — the command carried the parameter, the
endpoint never populated it. It now accepts `defaultMediaProfileId`, so the single and bulk paths are
symmetric.

**The id question.** `collection.write-model.md` said caller-generated, `collection.api.md` said
server-generated, the code did the latter. Resolved as **optional caller-supplied, server-generated
when omitted** ([AIP-133](https://google.aip.dev/133)) — not as picking a winner.

The reason is recovery, not taste. No idempotency middleware exists anywhere in this platform, so a
caller that lets the server pick the id and then loses the response to a timeout cannot tell "created,
response lost" from "never created": its retry either succeeds or returns `409` naming a collection
whose id it still does not have, and there is no get-by-name endpoint to look it up with. A caller
that supplied the id just calls `GET /v1/collections/{id}`. Same reasoning as AM-1, which made ids
**required** on bulk asset upload; optional here because the tenant-scoped name reservation already
prevents a retry from creating a duplicate — the failure mode is an opaque `409`, not a duplicate row
— and because requiring them would break every existing client. Malformed ids are rejected at the
endpoint with `400` rather than reaching `CollectionId.From` and surfacing as a `500`.

**The fictional services.** `ICollectionQueryService` and `IMediaProfileReadModel` never existed. Worse
than the interface stubs was the 140-line "Constraint Enforcement — Implementation Notes" section
built on them, which this file explicitly billed as *the canonical reference for all
uniqueness-enforcing handlers in the system* — so the fiction was being copied outward. It described
an ambient `ITransactionScope`, a MediatR `TransactionBehavior` committing the event append and the
name reservation atomically, and a `NameReservationConflictBehavior` pipeline step. None of it exists.
Rewritten to describe the real two-tier `INameReservationService` mechanism and the actual handler call
sequences, and the profile check now correctly documents reading the **write-side aggregate** via
`IMediaProfileRepository` rather than an eventually-consistent projection.

**Found while rewriting it — the reservation and the event append are not atomic.** The fiction was
covering a real gap. Each handler makes two independent `await`s, and each leaves a window:

- create — reserve then save: if the save fails the name is **leaked**, permanently unusable with
  nothing to release it;
- rename — swap then save: the reservation points at the new name while the aggregate still holds the
  old one;
- archive — **release then save**: the name goes free while the collection is still live, so another
  collection can take it and a retried archive leaves two live claims on it.

Archive is the sharpest of the three. Documented in `collection.write-model.md` as a known gap rather
than left implied-handled; the outbox that would close it is the same one X-3.1 found missing
platform-wide, and that decision is deferred.

#### CO-5 — `RootFolderIds` is not needed, and would be a regression

First finding: **the spec no longer asks for it.** A repo-wide search turns up `RootFolderIds` in
exactly one place — the projector's own XML comment claiming to diverge from a spec that has since
stopped mentioning it. The finding was written against that stale comment.

Second, and the reason not to add it back: the question it answers is already answered better.
`FolderByParentAndNameIndex` partitions root folders under the **collection id** —
`TENANT#{t}#PARENT#{collectionId}#FOLDERS` — so `GET /v1/folders?collectionId={id}` with no
`parentFolderId` already returns exactly the root folders, paginated, name-sorted, as full summaries
rather than bare ids.

Adding the list would be worse on three counts: it is unbounded, so a collection with thousands of root
folders pushes the detail item toward DynamoDB's 400 KB limit; it makes every folder create, archive
and move a write to one hot item shared by the whole collection; and it couples this projector to
another aggregate's event stream for data that is already indexed. Cross-collection folder moves (F-2)
would add yet another maintenance path. The stale comment is replaced with the decision and its
reasoning, and the same note is in `collection.read-model.md` so it is not re-proposed.

#### Test fallout from AM-2 — two shared constants for one owner

Ten tests across `BulkConfirmAssetUploadHandlerTests` and `ConfirmAssetUploadHandlerTests` failed on
wrong error codes and messages — `S3ObjectNotFound`, `AssetNotPending`, "declared size" — none of which
were actually wrong. **The shared test fixtures carried two different ids for the same concept:**
`AssetFactory.Owner` (`user-1`) and `TestData.Owner1` (`user-owner-1`). `TestCommandHandlingContext`'s
default actor can only match one of them, so every handler test that built assets with the other and
used the default context failed AM-2's owner check *before* reaching the guard it was written to
exercise. The symptom is a wrong error code, which reads as a regression in the thing under test rather
than as an auth failure — the same class of trap as the `MemberId` string-conversion divergence logged
earlier in this file.

Fixed at the source: `TestData.Owner1` now **is** `AssetFactory.Owner`. One id, one default caller.
Nothing depended on them differing — the only test that needs a non-owning caller
(`DeleteAssetHandlerTests.HandleAsync_CallerIsNotOwner_...`) passes an explicit `"someone-else"`, and
`TestData.Owner2` remains for a genuine second member. Patching each affected file's context would have
left the same trap for the next file.

> `AssetFactory.Tenant` (`tenant-1`) and `TestData.Tenant` (`tenant-abc`) diverge the same way. Tenant
> is not part of the owner check so nothing fails on it today, but it is the same defect one guard
> away from mattering.

Worth noting on its own: the owner check AM-2 added to bulk-confirm — the one closing a straight
bypass of the single-confirm guard — **had no test.** Two added: a foreign caller is rejected per item
and never reaches S3, and one foreign id in a batch does not discard the owned items alongside it.

**A second defect was hiding behind the first.** With the owner check passing, one test still failed —
`FailFast_GuardFailure_DiscardsPendingSuccesses` reported *two* `S3ObjectNotFound`s where it expected
one. Cause: the file's local `BuildPendingStandaloneAsset` stamped every asset with
`TestData.StandardStorageKey`, a single fixed value that embeds Asset1's id. Two assets therefore
shared one storage key, so the test's two `HeadObjectAsync` stubs — one returning metadata, one
returning null — collided, the second silently overwrote the first, and *both* assets took the
null branch. The builder now derives the key from the asset id, mirroring `StorageKeyGenerator`.

That failure mode is worth remembering: a colliding Moq setup on a value-equal key does not error, it
just makes one stub disappear, and it surfaces as a duplicated result rather than as a bad stub. Any
multi-asset test using a shared fixed key has the same trap. `ProfileLimitExceeded` was fine only
because it happened to build its two assets inline with different keys.

#### Test fallout from AM-16, fixed

`AttachToMediaItem_WhenTerminalStatus_ReturnsError` is parameterised over the statuses the AM-16
allow-list excludes, but `BuildAssetInStatus` had no arm for `MultipartAborted` and threw
`NotSupportedException`. Added `BuildMultipartAbortedAsset` — it has to start from
`BuildPendingMultipartAsset`, because `AbortMultipartUpload` rejects a single-part asset on
`UploadMode` before it ever looks at status.

#### Gotcha — `INameReservationService` cannot be verified through its named methods

`ReserveAsync`, `SwapAsync`, `ReleaseAsync`, `MoveAsync` and every `*Many*` variant are **extension
methods** on `INameReservationService`; the interface itself carries only `ApplyAsync(NameReservationIntent, ct)`,
which they all funnel into. Moq throws `NotSupportedException: Extension methods may not be used in
setup / verification expressions` on any `Setup`/`Verify` naming one. Assert against `ApplyAsync`
instead — which is also the stronger assertion, since it catches a reservation written by any route.
Reads are fine: `IsNameAvailableAsync`, `GetTakenNamesAsync` and friends are real interface members.

#### Still open after this pass

| Item | State |
|---|---|
| Nothing compiled | Two command-handler constructors gained a parameter; `CreateCollectionHandlerTests` and `BulkCreateCollectionsHandlerTests` were updated to match. Build before pushing. |
| ~~`GET /v1/items` silent sort fallback~~ | **Fixed 2026-08-22 (MediaItem pass).** Now a `400`; the allow-list lives in `MediaItemSort`. |
| ~~Unverified sort rows~~ | **Both verified.** `folders` in the Folder pass (F-7); `items` on 2026-08-22 (MI-4) — `createdAt`/`updatedAt` had no index and are gone. |
| Reservation/event non-atomicity | Newly documented, not fixed. Tied to the deferred X-3.1 outbox decision. Archive's release-before-save ordering is the one worth fixing first even without an outbox. |

### 2026-08-21 — Catalog Folder pass (C.3)

**Done (8):** F-1 · F-2 · F-3 · F-4 · F-5 · F-7 · F-8 · F-9. **Deferred on instruction:** F-6 (async
folder import — an advanced feature that belongs with the BulkFolderImportJob aggregate in §C.6).

> ⚠ **Still not compiled** — no `dotnet` in the sandbox. This pass changes a domain event's shape, an
> integration event contract, three read-model projectors and two command-handler code paths. Build
> `Catalog.Domain`, `Catalog.Contracts`, `Catalog.WriteModel(.Endpoints/.Infrastructure)`,
> `Catalog.ReadModel(.Endpoints)` and run `Catalog.WriteModel.Tests` + `Catalog.ReadModel.Tests` before
> pushing.

| Item | Resolution |
|---|---|
| F-1 | **Implemented — the finding was right and the endpoint was lying about it.** `MoveFolderHandler` now walks the destination's ancestor chain and refuses the move with `CircularFolderReference`. See below. |
| F-2 | **Spec corrected, and the feature it denied turned out to be half-built.** Cross-collection move was accepted on the wire but never actually changed the folder's collection. See below. |
| F-3 | **Spec corrected to `items`.** The code was right: every other list-shaped response in the platform uses `items`, so a per-endpoint `folders` key would have been a special case for clients to remember for nothing. The spec's example also showed a trimmed four-field node; the endpoint returns full `FolderSummaryModel` objects. Both fixed. |
| F-4 | **Guard implemented in the aggregate.** `Folder.Rename` and `Folder.Move` now reject an archived folder with `FolderArchived`, matching the metadata methods. Rename mattered more than it looks — see below. |
| F-5 | **Documented, and the whole bulk-paths section was wrong besides.** See below. |
| F-7 | **Implemented — the indexes support it.** Both folder lists now accept `sortBy`/`sortOrder`; `createdAt` removed from the contract. |
| F-8 | **Spec corrected.** `CollectionParentIndex` does not exist and neither does the `"ROOT"` sentinel it described. |
| F-9 | **Documented, plus three more undocumented fields the finding missed.** |

#### F-1 — the guard the OpenAPI summary already claimed to have

`MoveFolderEndpoint`'s summary told clients "the domain guards against circular references: if the
target parent is itself a descendant of the folder being moved, 409 is returned." Nothing did that, and
the status was wrong too — `CircularFolderReference` is an `InvalidOperation`, which this platform maps
to `422`. So the one place a client could read the rule was wrong twice over.

The guard walks **up** from the destination rather than down from the folder being moved. That choice is
the whole point:

- Up is bounded by the depth limit, so the check costs at most 10 point reads no matter how large the
  subtree is. Down is O(descendants).
- Up reads `IFolderRepository` — the event store, strongly consistent. Down would have to read
  `FolderFoldersIndex`, which is a projection: an invariant enforced against an eventually-consistent
  read is not enforced.
- A chain that fails to terminate within the depth budget is reported as a cycle. It can only come from
  a hierarchy that is already malformed, and refusing is the safe answer.

What the missing guard actually cost: the cycle has no root, so the whole subtree vanished from the
collection hierarchy and from every list that walks down from a collection, while the aggregates stayed
readable by id. No repair path short of a manual re-parent.

**Not fixed, and now written into the spec as a known gap:** the depth check still only validates the
moved folder. Descendants keep their stale depth counters and their heights are never added to the
destination depth, so a 6-deep subtree moved under a folder at depth 7 lands folders at depth 13. That
needs a write-path subtree walk, which is the same thing the cycle check deliberately avoided.

#### F-2 — cross-collection move was accepted, advertised, and did nothing

The finding reads as a spec error. It is, but underneath it the feature was half-built:

- `MoveFolderCommand` carried `CollectionId`, the endpoint required it in the body, and `Folder.Move`
  emitted `FolderMoved` when it changed — so the API accepted the operation.
- `FolderMoved` carried only **one** collection field, populated at emit time with the folder's
  collection *before* the move. `Apply(FolderMoved)` never touched `CollectionId` at all. So the
  aggregate's collection never changed.
- All three read-model projectors wrote `CollectionId = e.CollectionId` on move — i.e. they intended to
  move the row and re-wrote the old value. And `FolderChildIndexMoveAddedProjector` keyed the *new*
  parent's index entry off the *old* collection, so a root-to-root cross-collection move filed the
  child under the wrong collection.

Fixed by adding `NewCollectionId` to `FolderMoved`, `Apply` setting `CollectionId` from it, and every
consumer reading `EffectiveCollectionId`. The field is **optional and null-tolerant**: events written
before this change deserialise to null, which must be read as "same collection" — `EffectiveCollectionId`
is `NewCollectionId ?? CollectionId` and is `[JsonIgnore]`d so it is not persisted back into the payload
as a phantom contract field. Same treatment on `FolderMovedIntegrationEvent`, where an SQS redrive of a
pre-change message would otherwise deserialise null into a non-nullable string.

**The rule that replaces `FolderCollectionImmutable`** is weaker and more useful: a folder lives in
whatever collection its parent lives in. So the destination parent determines the collection, and a
`collectionId` in the body that disagrees with it is a `400` — rejected, not silently corrected, because
a caller sending contradictory values has a bug. `collectionId` is required only for a move to a
collection root, the one case with nothing to derive it from. The endpoint's `collectionId` is now
nullable to match.

**Two real bugs found while wiring it up:**

- **The old name reservation was released from the wrong scope.** `oldScopeKey` was computed from the
  *destination* collection, so moving a root folder from collection A to B released the reservation in
  B — where nothing was reserved — and left A's claim on the name permanently unreleasable. Silent, and
  only reachable on a cross-collection root move, which is exactly the path nobody exercised.
- **`FolderChildSummaryProjector` edited the row in place.** `child-items` is partitioned by parent
  folder, so a row's key *is* the relationship it records; an upsert left the child filed under the
  folder it left while claiming the collection it arrived in. The source kept listing a child it no
  longer had and the destination never gained one. Now uses the platform's `MoveAsync` result, which
  atomically deletes at the source key and inserts at the destination — the primitive exists precisely
  for "key derived from mutable data". `ResolveKey` deliberately still returns the *pre-move* key,
  because that is where the row currently lives.

> `ResolveKey(MediaItemMoved)` on the same projector has the mirror-image defect: it keys on
> `NewFolderId`, so the new row is correct and the old one is orphaned. Not touched — MediaItem pass.

#### F-4 — renaming an archived folder was swapping a reservation that no longer existed

The archived guard on `Move` is the obvious half. `Rename` is the one that mattered: `ArchiveFolder`
**releases** the folder's name reservation, so `RenameFolderHandler` was calling `SwapAsync` against a
scope entry that had already been deleted. Description-only updates are still allowed on an archived
folder — they touch no reservation — so `PATCH /v1/folders/{id}` refuses only when `name` is present.

#### F-5 — the endpoint was undocumented and the documented one was wrong

`POST /v1/folders/bulk-paths` is the same handler as the nested route with one rule changed: the first
path segment is a **collection name**, retrieved by name or created with `Private` visibility. Worth
having for ingest paths that name their own collection; worth keeping separate from the nested route,
which cannot create a collection by accident.

Writing it up surfaced that the nested route's own documentation had drifted on three points:

- `paths[]` is an array of **objects**, not strings — each carrying optional `description`,
  `openedDate`, `closedDate` and `originator` that apply to the **leaf segment only**.
- The response envelope is the shared `{succeeded, failed, skipped}`, not the `{nodes, failed}` with an
  `action` discriminator the doc showed. Pre-existing folders ride in `skipped[]` with
  `reason: "Existed"`.
- `CircularFolderReference` was listed as a per-path error code here. It is raised by
  `POST .../folders/bulk` — a cycle in that batch's in-batch parent links, which rejects the whole batch
  because a cycle has no valid creation order. Moved to the right table.

#### F-7 — `name` implemented, `createdAt` removed, same as CO-3

All three folder-facing indexes (`FolderByParentAndNameIndex`, `FolderHierarchyIndex`,
`FolderChildByNameIndex`) sort on `{name-lowercased}#{id}`. So `name` is free in both directions and
nothing else is sortable without a new GSI and a backfill — the same situation CO-3 found on collections,
resolved the same way: an unsupported sort is a `400`, not a silent fallback.

The rule now lives in **one** place. `CollectionSort` was reduced to a thin wrapper over a new
`NameOnlySort` that takes the resource name for the error message, and `FolderSort` is a second wrapper.
Copying CO-3's implementation a second time would have guaranteed the two drifted; the wrappers exist so
each endpoint still has one obvious place to grow a second sortable field if it ever gets an index.

`GET /folders/{id}/children` is worth a note: it mixes child folders and media items in one partition
ordered by display name, so a page interleaves the two kinds alphabetically rather than grouping by
type. That is a consequence of the index, and it is now documented rather than left to be discovered.

#### F-8 — there is no `CollectionParentIndex`, and no `"ROOT"` sentinel either

The spec described one GSI with `ParentFolderId` as its sort key, plus a note that root folders store a
`"ROOT"` string sentinel to stay queryable. None of that is real. There are two indexes on
`media-folders`, one per access pattern, both sorted by name; the third schema
(`FolderChildByNameIndex`) belongs to `child-items`.

Root folders are not a special case at all: `FolderByParentAndNameIndex`'s partition key uses
`ParentFolderId ?? CollectionId`, so root folders live under the collection's partition and
`GET /v1/folders?collectionId={id}` with no `parentFolderId` returns exactly them. Same mechanism CO-5
cited as the reason `RootFolderIds` on the Collection detail model is unnecessary — the two findings
were describing the same index from opposite sides.

#### F-9 — three fields, not one, and one flat-to-nested change

`originator` (create request, `FolderCreated`, both read models, all three responses) and `archivedDate`
(both read models, detail and summary responses) are the two the finding named. Also undocumented:

- `metadataAttributor` — the read model's flat `MetadataSetBy` / `MetadataAttributedTo` /
  `MetadataAttributedDate` trio was collapsed into a single `Attributor` value object. The spec still
  documented all three flat fields; none exist.
- `tenantId` on all three folder responses. **Removed rather than documented (Chase, 2026-08-21)**, then
  extended to a platform-wide sweep — see below.

#### The `tenantId` sweep — 13 response types, three contexts

Folder was the trigger; leaving it at Folder would have produced a third state of the world on top of
the two AM-24 already left (AssetManagement without the field, everything else with it). So the field
came off every resource response in the platform:

| Context | Types |
|---|---|
| Catalog — Folder | `FolderSummaryModel`, `GetFolderByIdResponse` |
| Catalog — Collection | `CollectionSummaryModel`, `GetCollectionByIdResponse` |
| Catalog — MediaItem | `MediaItemSummaryModel`, `MediaItemVersionSummaryModel`, `GetMediaItemByIdResponse`, `GetMediaItemVersionResponse` |
| Catalog — MediaProfile | `GetMediaProfileByIdResponse` |
| Metadata | `RecordTypeSummaryModel`, `GetRecordTypeByIdResponse` |
| Registration | `RegistrationSummaryModel`, `GetRegistrationByIdResponse` |

The reasoning is AM-24's: a caller's tenant is fixed by the `tenant_id` claim on its own token and is
the only tenant it can address, so echoing it back tells the client nothing it did not send and puts an
internal DynamoDB partitioning key on the wire. **Read models keep `TenantId`** — it is the partition
key; the endpoint contract is where it comes off.

Cheaper than it looks: all 13 are positional records whose only construction site is their own implicit
operator from a read model, so each removal is two edits in one file. Nothing in `tests/` names any of
the 13, and the integration tests deserialise as `JsonElement` and assert on named properties, so none
asserted on the field.

**One exception, kept deliberately:** `GET /auth/whoami` still returns `tenantId`. Echoing the resolved
identity back is that endpoint's entire purpose — it exists so a client can see what the server made of
its token. The convention now states the rule as applying to *resource* responses and names the
exception, rather than being absolute and false.

**Route count is larger than 13** — the list and search endpoints reuse the same summary/detail types as
their by-id siblings, which is how `GET /v1/collections/public`, `GET /v1/profiles` and
`GET /v1/registrations/search` are in scope without appearing in the table above.

Written up in `api-conventions.md § Response Shape` and logged in `docs/breaking-changes/`, which had no
entry despite its own stated criterion covering "an observable API response". ChangeRequests never
exposed the field; Processing and DocumentSigning have no endpoints project at all.

Also corrected while in there: `EventId` is listed in the read-model field table and is not on the
model. Same determination as AM-19 — dedup is version-based and `DomainEvent` carries no event id — so
the row was removed rather than the field added.

#### Beyond the findings

- **`folder.api.md` still documented `202 Accepted` for partial bulk-create results**, a week after C-3
  settled that on `200`. The shared docs and the endpoints were updated in that pass; this aggregate's
  own file was missed. Corrected, with the per-item envelope shapes spelled out.
- **A no-op move returned `409`.** The destination availability check ran unconditionally, so a move to
  the folder's current location found the name taken — by that same folder — and failed.
  `Folder.Move` is deliberately idempotent and `Move_SameParent_IsIdempotentReturnsSuccess` asserts it,
  so the aggregate and the handler disagreed. The check and the Tier-2 reservation move are now both
  skipped when the scope does not change.
- **The depth counter was adjusted one level at a time** — a loop issuing up to nine sequential DynamoDB
  round-trips when both `IncrementCounterAsync` and `DecrementCounterAsync` take an `amount`. One call
  now.
- **`api-conventions.md § Sorting` says the default `sortOrder` is `desc`.** It is `asc` on every
  name-sorted endpoint. The `desc` default predates the name-only resolution and now applies only to the
  two `createdAt`-sorted rows. Caveated in place rather than rewritten, since the MediaItem pass owns
  those rows.

#### Tests

15 added: 6 aggregate (cross-collection move, collection-unchanged move, legacy-event replay,
self-move, archived move, archived rename), 5 move-handler (descendant cycle with a
verify-nothing-was-saved assertion, unrelated-sibling false-positive check, cross-collection adoption,
contradictory `collectionId`, source-scope reservation release), 4 child-summary projector (the move
result, cross-collection, move-to-root keying, missing row). Plus a `FolderSortTests` file mirroring
`CollectionSortTests`, and the two existing `FolderMoved` projector tests rewritten — they passed either
way, because they put the destination collection in the event's *source* field, so they were asserting
the right value for the wrong reason.

#### Still open after this pass

| Item | State |
|---|---|
| Nothing compiled | A domain event gained a field and an integration event contract changed. Build before pushing. |
| Subtree depth on move | Documented as a known gap in `folder.write-model.md`. Needs a write-path descendant walk; the only existing one reads a projection. Own ticket. |
| ~~`tenantId` on responses~~ | **Swept platform-wide (Chase, 2026-08-21)** — see below. |
| ~~`MediaItemMoved` orphan rows~~ | **Fixed 2026-08-22 (MediaItem pass)** — and worse than predicted: the move was lost entirely rather than duplicated. `child-items` needs a replay. |
| `MoveFolder` takes no collection lock | `CreateFolderHandler` acquires `IFolderCreationLockService` before touching root-scope reservations; `MoveFolderHandler` never has, so a move into or out of a collection root can interleave with a bulk create in that collection. The `TransactWriteItems` reservation still keeps names atomic, so this is an inconsistency in approach rather than a hole — but the two paths should agree. |
| Move is still non-atomic | Same shape as the CO-4 finding on Collection: reserve/swap and the event append are separate awaits. Tied to the deferred X-3.1 outbox decision. |

### Also fixed this session — not from this review

| Item | Action | Files |
|---|---|---|
| `MemberId` string-conversion divergence | Found via the failing `Snapshot_RoundTripsParticipantsAndReviewSession` test on `feature/change-requests`. `MemberId` was the only id in the ChangeRequests module without a `ToString()` override, so `memberId.ToString()` rendered `MemberId { Value = user-1 }` while the implicit `string` operator returned `user-1`. `ChangeRequest.TakeSnapshot` projected participants through the former and `FromSnapshot` rehydrated through `MemberId.From`, so participants survived the round-trip in count but not in value — `IsParticipant` false for everyone, every `AddComment` rejected. Added the override and switched the snapshot to `p.Value` | `MemberId.cs`, `ChangeRequest.cs` |

> Same failure shape as DS-4: structurally interchangeable identifiers, caught only because one test happened to assert the right field. A sweep of `IStringId` value objects across the other modules for the same missing override is worth a ticket.

### P-1 verdict — bug, not a deliberate workaround

1. `ProcessingJobDetailProjector` handles the same `ProcessingJobFailed` event and correctly sets `Status = Failed`, `FailureReason = e.Reason`. A deliberate workaround would have had to fake both projectors.
2. The broken handler is character-for-character the neighbouring `ProcessingJobSucceeded` handler with `StatusText` and `UpdatedAt` edited and `Status` left behind.
3. Stashing the failure reason in `StatusText` is the behaviour of code that *intends* to record a failure.
4. Nothing reads the summary `Status` for control flow — `AssetIngestionSaga` is driven by integration events, so no downstream consumer could have been unblocked by a false `Succeeded`.
5. The processing pipeline is implemented and deployed (`ProcessingWorker` is live — see X-1.4), so there was no unimplemented-pipeline block to work around.

**How it survived:** `ApplyAsync_WhenProcessingJobFailed_SetsFailureReason` asserted `StatusText`, `UpdatedAt` and `ProjectedVersion` — every field except the broken one. The test has been renamed and now asserts `Status`.

### Open questions raised by this pass

- **AM-6 / soft delete.** `Asset.Delete`'s own comment says the transition is *"Deleted (soft); S3 object retained"*, but the handler hard-deletes the original and every rendition. The ordering bug is fixed either way; whether S3 objects should be destroyed at all on `DeleteAsset` is a spec decision that is still open.
- **AM-6 / failure window.** S3 deletion still runs before `SaveAsync`, preserving today's semantics. The alternative — persist first, then delete storage best-effort — trades orphaned objects (reapable) for lost bytes (not). Not changed unilaterally.
- **R-6 / MI-7 deployment.** Both mappings are created at `QueryApi` startup and OpenSearch field renames are not in-place. Per X-1.3 neither `Projectors.Search` nor the OpenSearch domain is deployed in any environment, so there is no live index to migrate — but if one is ever created from the old mapping, it needs deleting and rebuilding, not patching.
- **R-7 still open.** With R-6 fixed, registration search will index successfully but `reference` will still come back `null`: the handler indexes `RegistrationDetailReadModel` (`ReferenceNumber`) and deserialises into `RegistrationSummaryReadModel` (`Reference`). R-6 was the blocker; R-7 is now the visible bug.
- **M-5 untouched.** `RecordTypeCreated` still projects `PublishedVersion = 1` where the spec says `0`. Same constructor as M-6/M-7 but a separate finding.

### 2026-08-22 — Catalog MediaItem pass (C.4)

**Done (6):** MI-1 · MI-2 · MI-3 · MI-4 · MI-5 · MI-6. MI-7 was already closed in the R-6 pass.
Also closed the three items earlier passes parked for this one: the `GET /v1/items` silent sort
fallback and the unverified `items` rows in the shared supported-sorts table (both from the Collection
pass), and the `MediaItemMoved` orphan rows (Folder pass).

> ⚠ **Still not compiled** — no `dotnet` in the sandbox. This pass changes a query's response type, a
> read model's JSON contract, an OpenSearch index mapping, two endpoint request records and a shared
> sort helper's signature. Build `Catalog.ReadModel`, `Catalog.ReadModel.Endpoints`,
> `Catalog.WriteModel.Endpoints`, `Catalog.Domain` and `QueryApi`, and run `Catalog.ReadModel.Tests` +
> `Catalog.WriteModel.Tests` before pushing. `Catalog.ReadModel.Tests.csproj` gained a project
> reference to `Catalog.ReadModel.Endpoints` — see the note in the file for why.

| Item | Resolution |
|---|---|
| MI-1 | **Implemented, and the finding understated it.** Three filters added; the endpoint was also ordering a *search* by date, and returning detail objects. See below. |
| MI-2 | **Spec corrected — the code has it the right way round.** `commentThreadId` is server-minted, not caller-supplied. The finding was written against an older tree: the handler does reach the aggregate's parameter, it just mints the value itself. |
| MI-3 | **Documented, plus a status-code correction on the same endpoint.** `changeRequestId` was live, undocumented, and driving two error codes that *were* documented. |
| MI-4 | **Contract trimmed to what the index can serve, and `sortBy` implemented within it.** `status` removed rather than deferred; `createdAt` rejected; `title` sort added. |
| MI-5 | **Spec-only, confirmed against the manifest.** Three GSIs across three tables, not one. |
| MI-6 | **The guard was right; three pieces of prose and one in-code comment were wrong.** No behaviour change. |

#### MI-1 — the search endpoint was a date-ordered filter wearing a search endpoint's name

The finding lists a cursor-field mismatch, a wrong item shape and three missing filters. Underneath
those, the endpoint had a fourth problem that none of them names: it built a scoring `multi_match` with
a `Title^3` boost and then sorted the results on `CreatedAt desc`, discarding the score entirely. Every
relevance signal it computed was thrown away before the response was written. Now sorts
`_score desc, Id.keyword asc` and returns the score.

- **Filters.** `status`, `folderId` and `collectionId` implemented as non-scoring `filter` clauses, so
  they narrow the candidate set without perturbing the ranking of what survives. All three are
  `keyword`-mapped, so they match whole values.
- **Cursor.** The spec's `nextPageToken` was wrong, not the code. `searchAfter`/`nextSearchAfter`
  matches `GET /v1/items`, which reads the same index; `pageToken` would have been a second cursor
  model over one index.
- **Item shape.** Was `GetMediaItemByIdResponse` — metadata changesets, asset arrays, checkout state,
  for every hit. A search result set is the page a caller is most likely to request large and mostly
  discard, so it was the worst place in the API to be sending detail. Now `MediaItemSummaryModel`, the
  same shape both list endpoints return.
- **`score` placement.** On the shared summary as an optional `init` property suppressed when null,
  rather than on a search-only subtype. A parallel 15-field record would have been the flat-on-the-wire
  option, but it drifts the first time someone adds a field to the summary and forgets the copy — which
  is most of what this review has been finding. Two tests pin the suppression, because that is the only
  thing keeping the two list endpoints' wire shape unchanged.

#### The `media-items` index has never been able to accept a document

Found while implementing MI-1's `status` filter, and it makes both OpenSearch-backed endpoints
non-functional today regardless of their contracts. `MediaItemsIndexMapping` is `dynamic: "strict"` and
`MediaItemSearchIndexSchema` indexes `MediaItemDetailReadModel` **whole**, so any property on the record
with no entry in the mapping causes OpenSearch to reject the entire document. Seven did:

`RecordDate` · `Author` · `MetadataAttributor` · `CheckoutLeaseExpiresAt` · `EditSessionId` ·
`EditSessionEditors` · `Assets.Order` — plus `metadata`, mapped in lower case against a `Metadata`
property, which is the same defect a ninth time.

This is MI-7 and R-6 again — both were single-field name mismatches that took a whole index down — but
broader, and it survived those two fixes because both were found by reading the *query* side. The
mapping's doc comment now states the mirror rule explicitly, so the next person adding a read-model
field is told what it costs to forget.

**Verified by set comparison, not by eye:** the mapping's top-level properties and
`MediaItemDetailReadModel`'s constructor parameters are now 32 and 32, with an empty difference in both
directions. The nested `Assets`, `ConformanceGaps` and `MetadataAttributor` objects were checked the
same way against their DTOs. That check is worth wiring into CI the way the projection-table manifest
drift gate already is — it is the same class of app→infra contract, and the same class of silent
failure.

Also removed `ActiveMediaChangeRequestId` from the mapping: it is on no read model, no projector and no
response anywhere in Catalog. It was additionally documented in `mediaitem.read-model.md`'s `media-item`
field table and in the `GET /v1/items/{itemId}` example — all three removed rather than the field built,
because the change request an item is being edited under lives on the **edit session** (MI-3), not as a
projected field. `LastAssetEventVersion` went the same way. Nine fields the record *does* carry were
undocumented and are now listed.

#### `Status` was being indexed as `0`

Separate defect, same area, and the one that would have made MI-1's new `status` filter a lie.
`MediaItemStatus` is a plain enum persisted numerically — the event store depends on that, and the
enum's own doc comment says member ordering is part of the stored contract. `Projectors.Search`
registers a bare `JsonSerializerOptions`, so the document carried `"Status": 0`, OpenSearch coerced it
to the keyword `"0"`, and `?status=Published` matched nothing. Silent in both directions: indexing
succeeded, the filter returned an empty page, and the read model deserialised back correctly.

Fixed with `[property: JsonConverter(typeof(JsonStringEnumConverter))]` on
`MediaItemDetailReadModel.Status` — scoped to the read model rather than the enum type, so the event
store is untouched, and read-compatible in both directions so existing DynamoDB rows still load. The
alternative (registering the converter globally in `Projectors.Search`) would have silently changed
Registration's documents too.

> **`RegistrationDetailReadModel.Status` has the identical defect** — `RegistrationStatus` enum,
> `keyword` mapping, no converter. Not touched: it belongs to Registration's pass, and R-6/R-7 are
> already open there. Flagged the way the Folder pass flagged `MediaItemMoved` for this one.

#### MI-2 — the finding is stale, and the spec is the half that was wrong

`PublishMediaItemHandler` mints a `ChangeRequestId` when reviewers are present and returns it as
`changeRequestId`. So the aggregate's parameter is reachable; what does not exist is a *caller-supplied*
one, and it should not:

- Nothing could validate it. The `MediaChangeRequest` does not exist yet — ChangeRequests creates it
  asynchronously from `MediaItemPublicationRequested` — so a supplied id would be accepted unchecked and
  could bind the review session to another item's thread.
- The legitimate case is already covered. An item checked out under a change request carries that id
  through review on the edit session (MI-3), and `RequestPublication` reads it off the session
  deliberately, so a rejection that reopens the session lands back under the same CR.
- Caller-generated ids for server-owned resources need an idempotency story, and this endpoint already
  has `IdempotencyKey`.

The name difference across the boundary is now documented as deliberate rather than left looking like
drift: the aggregate and its event say `CommentThreadId` (what the id is *for*), the API says
`changeRequestId` (what it *addresses*).

#### MI-3 — a documented error code whose cause was undocumented

`ChangeRequestRequired` and `ChangeRequestNotOpen` were added to `error-catalog.md` in the C-6 pass. The
request field that raises them — `changeRequestId` on checkout — was in no spec file. A client could
read both codes and have no way to learn what produced them. Now documented on the endpoint, in the
`CheckOut` method row, in the command signature, and as two new rows in the handler pre-conditions
table, with the design reason recorded: the gate is at checkout rather than per-write so a user learns
the change is governed *before* doing an hour of work.

Two corrections on the same endpoint while in there:

- **`TooManyCollaborators` is a `400`, not a `422`.** `MediaItem.CheckOut` raises
  `ValidationFailure`, and `error-catalog.md` already said `400`. Only the endpoint's own OpenAPI
  summary said otherwise — i.e. the one place a client reads it from the running service.
- The summary said nothing about `changeRequestId` at all, so the generated OpenAPI document described
  a request body the endpoint does not have.

#### MI-4 — `status` removed rather than deferred

The published contract had `status`, `sortBy=createdAt` and a `desc` default; the request record had
`folderId`, `pageSize`, `pageToken`. The note deferring the gap to "R-21 · Phase 5" has been dropped
along with the two parameters that were never going to be implementable here.

`MediaItemByFolderIndex` is keyed on folder and sorted `{Title}#{MediaItemId}`. So:

- **`title` sort implemented, `asc` default** — free in both directions, via a new `MediaItemSort`
  wrapper over the `NameOnlySort` rule. `NameOnlySort` gained a six-parameter overload taking the
  caller-facing field name, because a media item's display name is its `title`; the four-parameter form
  still delegates with `"name"`, so `CollectionSort` and `FolderSort` are unchanged.
- **`createdAt` rejected with `400`**, not silently served in title order. Third time this exact
  resolution has been applied — CO-3, F-7, now MI-4.
- **`status` removed.** Status is not part of the key. Filtering on it means reading every item in the
  folder at full read cost and discarding most of them, with pages arriving arbitrarily short. Worse to
  offer than to withhold, and `GET /v1/items?status=` does it properly against OpenSearch. The request
  record documents why, so this does not get "fixed" later by someone who only sees the missing
  parameter.

#### MI-5 — one GSI per table, not one per aggregate

The June note ended "`media-items` now has exactly one GSI", which is true of that table and was read as
true of the aggregate. There are three, one per table, and all three are live:

| Table | GSI | Backs |
|---|---|---|
| `media-items` | `MediaItemByFolderIndex` | `GET /v1/folders/{folderId}/items` |
| `media-item` | `MediaItemByLeaseExpiryIndex` | `TimeoutScanner` — the lapsed-checkout reaper |
| `media-item-versions` | `MediaItemVersionByMediaItemIndex` | `GET /v1/items/{itemId}/versions` |

Confirmed against `projection-tables.manifest.json` in `cdk-magiq-media`, which CDK consumes directly
and a CI drift gate keeps honest — so it, not this document, is the authoritative list, and the spec now
says so. `MediaItemByLeaseExpiryIndex` was worth writing up properly rather than just listing: it is
sparse *and* deliberately not tenant-partitioned, which looks like a multi-tenancy violation until you
know the reaper has no tenant in scope.

The read-model spec's Queries and Query Handlers tables were wrong in the same neighbourhood and are
corrected: three of seven queries named records that do not exist (`ListMediaItemsByFolderQuery`,
`ListMediaItemsByOwnerQuery`, `ListUnassignedMediaItemsQuery` — the last two folded into
`ListAllMediaItemsQuery` when `GET /v1/items` gained `?ownerId=` and `?unassigned=`), `ListExpiredCheckoutsQuery`
was live and unlisted, and `SearchMediaItemsHandler` was documented as paginating by `from`/`size`. That
last one mattered: `from`/`size` is the model that caps out at `max_result_window` (10,000), so a reader
would have designed around a limit this index does not have.

#### MI-6 — the prose contradicted the state diagram directly above it

The guard accepts `Draft` or `Revising`. Three pieces of spec prose and one in-code invariant comment
said `Draft` only — while the state transition diagram two sections up has always shown
`Revising ──Publish──► PendingApproval`, `ReviewSession.OriginStatus` exists specifically to distinguish
the two origins, and `RequestPublication_FromRevising_CarriesOriginStatusOnEvent` has been passing all
along. A `Draft`-only guard would make `BeginRevision` a trap: the only exit from `Revising` would be
`DiscardRevision`.

No behaviour change, so no new test — the existing one is the evidence.

The invariants table named `MediaItemNotDraft` as the error code. It exists nowhere in the codebase and
never has; the guard raises a bare `InvalidOperation`. Marked ⬜ per the error catalog's own convention
rather than inventing an emission.

**Correction to `error-catalog.md` found while checking that:** `InvalidStatusTransition` was listed as
`409`. Every status guard in the codebase raises `InvalidOperation`, which the platform maps to `422` —
the row directly below it in the same table already said so. A client branching on `409` for a status
refusal would have been waiting for a response that never arrives. The two concurrency rows above it
keep `409`; those are genuine conflicts, not state-machine refusals.

#### Carried in from earlier passes

- **`MediaItemMoved` orphan rows — fixed, and it was worse than the Folder pass thought.** The write-up
  there predicted "the new row is correct and the old one is orphaned". Neither happened:
  `ResolveKey(MediaItemMoved)` keyed on `NewFolderId`, so the framework loaded `current` from the
  destination — where no row exists — the handler returned `MissingCurrent`, and the projection did
  nothing at all. The source folder kept listing an item it no longer contained and the destination
  never gained it, on every media-item move. Fixed exactly as `FolderMoved` was: `ResolveKey` returns
  the pre-move key, `ApplyAsync` uses `MoveAsync` to delete at the source and insert at the destination
  atomically. `MediaItemAssignedToFolder` stays an in-place upsert — there is no source row to move.
- **`GET /v1/items` silent sort fallback — fixed.** `ListAllMediaItemsHandler` coerced any unrecognised
  `sortBy` to `createdAt`, so `?sortBy=publishedAt` returned a well-formed, date-ordered page with
  nothing to indicate the request had been ignored. Now a `400`. This was the last silent-fallback sort
  path in the platform; the rule in `api-conventions.md § Sorting` is now true everywhere it claims to
  be. The allow-list moved out of the handler into `MediaItemSort`, so the endpoint validates and the
  handler maps — one owner for the rule.
- **Unverified sort rows — verified.** Both `items` rows in the supported-sort-fields table were
  wrong. `GET /v1/folders/{folderId}/items` advertised `name`, `createdAt` and `updatedAt`; it supports
  `title`. `GET /v1/items` was not in the table at all, and `?unassigned=true` was listed among the
  endpoints that take no `sortBy` — it is not a separate endpoint, just `GET /v1/items` with a filter.
  The claim that those endpoints return "DynamoDB scan order" was wrong twice: neither scans, and both
  have a stable total order.
- **`api-conventions.md § Coverage` verb — fixed.** Named the field-level metadata route as `PUT`;
  code and `mediaitem.api.md` both use `PATCH`. Flagged in this section's own "Aligned" notes and never
  actioned.

#### Tests

15 added across three files. `MediaItemSortTests` mirrors `FolderSortTests`/`CollectionSortTests` for the
folder-scoped rule and adds the tenant-wide one, including a case asserting `sortBy=name` is rejected —
`name` is the sortable field on every *other* Catalog list, so it is the most likely thing a client
copies across. `SearchMediaItemsResponseTests` pins the MI-1 wire contract: summaries not detail
(asserted by the absence of `description`, which only exists on detail), score present per hit, score
absent from the JSON when null, cursor preserved. `FolderChildSummaryProjectorTests` gained four
`MediaItemMoved` cases mirroring its `FolderMoved` ones, including an explicit `ResolveKey` assertion —
the two existing `FolderMoved` projector tests passed either way before the F-2 fix, so a `ResolveKey`
test is what would have caught this class of defect on its own.

`Catalog.ReadModel.Tests` now references `Catalog.ReadModel.Endpoints`. Endpoint response records are
read-side wire contracts and there is no Endpoints test project; the alternative was leaving the
`score` suppression — the one subtle thing in this pass — untested.

#### Still open after this pass

| Item | State |
|---|---|
| Nothing compiled | A query's response type, a read model's JSON contract, a projector's key resolution and a shared sort helper's signature all changed. Build before pushing. |
| `child-items` needs a replay | The `MediaItemMoved` fix corrects the projector, not the rows it has already got wrong. Every media item moved between folders to date is still filed under its source folder in `child-items`. `src/tools/ProjectionReplay` is the mechanism; scope is that one table. |
| `RegistrationDetailReadModel.Status` | Same numeric-enum-into-a-keyword-field defect fixed here on MediaItem. Registration pass. |
| MI-2's asymmetry is undocumented in ChangeRequests | Catalog now explains why `CommentThreadId` and `changeRequestId` are the same value under two names. The ChangeRequests spec has not been checked for the mirror statement. |
| `media-item` detail read model has no `ActiveMediaChangeRequestId` | Removed from three spec locations as unimplemented. If a UI needs "which CR is this item being edited under" without opening the edit session, that is a projector to write, not a spec line to restore. |
| C-2 (owner-scoped authz) still ⊘ | Untouched here, as agreed — the MediaItem Authorization table still describes rights no handler checks. |
| MP-1 … MP-4 | MediaProfile is the remaining C.5 block. MP-3 (`LeaseDurationMinutes`) and MP-2 (`change-request-policy`) are both referenced by the MI-3 write-up, so they are the natural next pass. |
| No CI gate on the OpenSearch mapping | The 32/32 check above was run by hand. A `dynamic: strict` mapping is an app→infra contract exactly like `projection-tables.manifest.json`, which already has a drift gate. Worth its own ticket — it would have caught R-6, MI-7 and the nine fields found here, each of which took a whole index down silently. |

### 2026-08-22 — Catalog MediaProfile pass (C.5)

All four findings closed. MP-1 was the only one with a real hole behind it; the other three were
contract-documentation gaps, one of which turned out to hide a small correctness bug.

#### MP-1 — the compiled template existed, was published, and was thrown away four times

The finding said the template "is never projected". That is accurate but understates where the loss
happens. `MediaProfilePublished.PublishedSnapshot.CompiledTemplate` is populated on every publish and
is already consumed correctly by the *write* side — `CreateMediaItemHandler` pins
`CompiledTemplate.ToSnapshot()` onto `MediaItemCreated`, so items validate against the right qualified
names. It is the read side that drops it: `MediaProfileDetailProjector`, `MediaProfileSummaryProjector`
and `MediaProfileVersionDetailProjector` each receive the event, map six or seven fields off the
snapshot, and never touch `CompiledTemplate`.

So the qualified keys were knowable by the server at item-creation time and unknowable by the client at
any time. A UI building a metadata form for a profile with two RecordTypes both defining `amount` had
no way to learn that the writable keys are `invoice.amount` and `receipt.amount` — and fetching the
contributing RecordType versions returns `amount` twice, which is exactly the set of keys
`PATCH /v1/items/{itemId}/metadata/{fieldName}` refuses.

Now projected onto the detail row **and** the version-snapshot row, through one shared
`CompiledMetadataTemplateMapper` so the two cannot drift.

**The version row matters more than the detail row.** A MediaItem pins the profile version it was
created under. An item on v1 of a profile now on v3 must write v1's qualified keys, and the detail row
only ever holds the current version's. Without `GET /versions/{version}` carrying its own compiled
template, every item on a superseded version would have been given the wrong answer — which is worse
than no answer. This was not in the finding.

**Per-field validation constraints were deliberately left off.** `CompiledMetadataField` also carries
`AllowedValues`, `MinLength`/`MaxLength`, `MinValue`/`MaxValue`, `MinDate`/`MaxDate`, `MaxSelections`,
`RegexPattern`, `DefaultValue` and `AllowsConcurrentEdit`. Compilation does not alter any of them, so
they are already readable from `GET /v1/record-types/{recordTypeId}/versions/{version}` — and each entry
carries the `recordTypeId`/`recordTypeVersion` needed to get there. Projecting them would put an
unbounded payload on a row that list queries also read, to duplicate data that is correct elsewhere. The
gap MP-1 names is the *qualified name*, which is knowable from the profile and from nowhere else; that
is what shipped.

**`GET /v1/profiles` does not carry the template**, and that is the one deliberate deviation from the
finding's wording. The list endpoint reuses the by-id response type — noted in the tenantId sweep as the
reason `GET /v1/profiles` was in scope there — so adding the field to the detail response would have put
an unbounded field list on every row of every page. A page of 50 profiles with 30 compiled fields each
is 1,500 field objects to answer "what profiles exist". New `MediaProfileListItemModel` carries every
other field of the detail response, so nothing was removed from the list contract; only the two new
fields were withheld from it, and the by-id route is documented as the discovery path.

#### MP-3 — the finding named the request side; the response side was broken, not just undocumented

`LeaseDurationMinutes` was indeed an undocumented field on `PUT /checkout-policy`. But it was also
missing from the *read* path in a way the finding did not reach: the detail read model **declares**
`LeaseDurationMinutes`, and no projector ever assigned it. `MediaProfileCheckoutPolicySet` set it on the
draft; `MediaProfilePublished` did not carry it forward to the published block, even though
`PublishedSnapshot.LeaseDurationMinutes` was right there. So on a published profile the field read back
`null` regardless of what the tenant had configured — indistinguishable, to a client, from "this lock
never expires".

Nothing broke operationally, because checkout expiry is computed on the write side from
`MediaProfileIndex.LeaseDurationMinutes`, which is populated correctly. The lease worked; it just could
not be seen. That is the kind of gap that gets "discovered" as a support ticket about locks expiring
when the API says they never will.

Fixed in the detail, summary and version-detail projectors, added to the `GET` response and to the list
item, and documented on both the request and the response side.

**Not changed:** `leaseDurationMinutes` remains meaningful under `checkoutPolicy: "None"`, and is not
rejected there. `None` means checkout is not *required*, not that it is unavailable —
`EditSessionGuard` only gates on `RequiredForEdit` — so a voluntary lock still lapses on the profile's
lease. Rejecting the combination would have broken a working configuration.

#### MP-2 — two routes, plus the two the Folder pass left behind

Both `PUT /auto-submit-on-complete` and `PUT /change-request-policy` are now in the route table with
their own sections. Also documented, per the note left open on 2026-08-21: `DELETE /profiles/{id}/draft`
and `DELETE /profiles/{id}/asset-definitions/{roleName}`, both `200`-with-body, with the reasoning for
the status code recorded rather than left to be rediscovered.

Two behaviours were written down for the first time while documenting them:

- **Only a revision draft can be discarded.** `DiscardDraft` guards on `Status == Published`, so the
  initial draft of a never-published profile is refused. That is correct — discarding it would leave a
  profile with no usable state — but nothing said so.
- **Removing a role that is not on the draft is a `422`, not a `404`.** The profile in the path exists;
  the refusal is about the draft's contents. Documented as-is rather than "corrected", since the
  alternative reading is defensible and changing it is a client-visible break for no gain.

#### MP-4 — the undocumented field was also wrong

`{profileId, newVersion, publishedAt}` is what the endpoint returns, as the finding says. What the
finding could not see is that `publishedAt` was a **second** `GetUtcOffsetNow()` call, made after the
command returned. The value in the response was therefore never the value in `MediaProfilePublished`,
and never the `publishedAt` on the version row the caller would fetch next — off by however long the
publish took, which includes a name-reservation swap and a DynamoDB write. Anyone correlating the two
would have found them disagreeing by milliseconds with no explanation.

One clock read now, used for both. `profileId` also comes from `result.Value.MediaProfileId` rather than
being re-echoed from the route, so the body reports what was actually published.

#### Beyond the findings

- **Three OpenAPI descriptions were unwritten TODOs shipped as documentation.** `SetCheckoutPolicy`
  said "Document the checkout policy options (e.g., single-user exclusive lock, multi-user concurrent)
  and their implications"; `SetReviewPolicy` and `DiscardMediaProfileDraft` had the same shape. These are
  not internal comments — they are the endpoint descriptions in the published Swagger. All three
  rewritten to say what the endpoint does.
- **`ListMediaProfilesResponse` and `ListMediaProfileVersionsResponse` omitted `pageSize`**, which every
  other Catalog list envelope carries and which `api-conventions.md` specifies. Same defect as M-11 in
  the Metadata module. Both added — additive, no break.
- **Three broken spec anchors** still carried the `/catalog` route prefix removed in the routing
  migration: `#get-v1catalogprofilesprofileid` (the MP-1 discovery link itself, so the one place a
  client was told to look was a dead link), `#patch-v1catalogitemsitemidmetadatafieldname`, and
  `#post-v1catalogitemsbulkmetadata`.
- **`mediaprofile.read-model.md` was substantially stale** beyond MP-1's reach and was corrected while
  in there: `MediaProfileDetailReadModel.MediaProfileId` is `Id` in code; `AssetDefinitionDto` names its
  categories `AllowedMediaCategories`, not `AcceptedContentTypes`, and has an `IsDefault` the spec never
  listed; `AutoSubmitOnComplete`, `LeaseDurationMinutes` and `ChangeRequestPolicy` were missing from all
  three DTOs; and the current-state row table still listed `EventId`, removed for the same reason as
  AM-19 and the Folder pass.
- **Event names in the write-model spec did not match the code** — `ReviewPolicySet` and
  `CheckoutPolicySet` are `MediaProfileReviewPolicySet` and `MediaProfileCheckoutPolicySet`, and the
  payload columns omitted `TenantId`, the old/new pairs, and the lease. Corrected, and the two new
  events added.

#### Tests

Nine added across two files. `MediaProfileCompiledTemplateProjectionTests` covers the MP-1/MP-3
projections on both the detail and version-detail projectors, including the collision case (two
RecordTypes contributing `amount`, three emitted fields, one suppressed bare name) and the
never-published case asserting `[]` rather than `null` — the latter is what protects rows written before
this projection existed. `MediaProfileResponseContractTests` pins the wire shape: the detail response
carries the documented seven field properties under the documented names, and the list item does **not**
carry `compiledMetadataFields`/`suppressedFieldNames` while still carrying everything else. That
asymmetry is the easiest thing in this pass for someone to "fix" by accident.

#### Still open after this pass

| Item | State |
|---|---|
| Nothing compiled | Still no `dotnet` in the sandbox. A read model gained two init properties, three response records changed shape, and two list envelopes gained `pageSize`. Build and run `Catalog.ReadModel.Tests` before pushing. |
| `media-profiles` needs a replay | The projectors are fixed; the rows they already wrote are not. Every profile published before this change has `compiledMetadataFields: []` and a `null` `leaseDurationMinutes` on its published block. `src/tools/ProjectionReplay`, scoped to `media-profiles`. Same shape as the `child-items` replay the MediaItem pass left open. |
| `MediaProfileSummaryReadModel` is written and never read | Both summary projectors are maintained, `MediaProfileByNameIndexSchema`/`MediaProfileByVersionIndexSchema` exist, and `ListMediaProfiles` reads the **detail** model instead — the only Catalog list that does. Switching it would need new index schemas and a `projection-tables.manifest.json` change with the cross-repo drift gate, so it was left alone. Worth its own ticket; the summary row is currently dead weight being kept warm. |
| Summary projector conflates draft and published policy | `MediaProfileSummaryProjector.ApplyAsync(MediaProfileCheckoutPolicySet)` writes the **draft's** new policy onto the summary's top-level `CheckoutPolicy`, which is supposed to be published state. Latent only because nothing reads the summary (above). Not fixed here — fixing it in isolation would leave the row half-right. |
| `AssetDefinitionDto.DimensionConstraints` is always `null` | Both projectors pass `null` with a "mapping deferred — see completeness report" comment. So `dimensionConstraints` is on the wire, documented, and never populated. Not a C.5 finding; belongs with the projector coverage gaps in §I. |
| MediaProfile draft refusals still carry no `errorCode` | `mediaprofile.api.md` publishes `NoActiveDraft`, `DraftEmpty`, `ProfileNameConflict` and `DraftInProgress` in its error examples; `error-catalog.md` states plainly that MediaProfile's draft/version refusals are untagged. The two documents contradict each other. The new sections were written to the catalog's truth and say so; the older examples were left for the I.10 error-catalog pass rather than half-corrected here. |
| C.6 (BulkImportJob) is what remains of Catalog | BI-1/BI-2/BI-3 — two fully specced aggregates with nothing behind them at any layer. Not a drift fix; a build. |

### 2026-08-22 — Metadata pass, M-1 to M-5 (D)

Five findings closed. Two of them (M-1, M-2) were the same defect twice; M-3 turned out to be a
mixture — the code was wrong in seven places and the spec was wrong in three; M-4 was spec-only as
called; M-5 was a one-character fix on a read model that turned out **not** to be dead weight.

#### M-1 / M-2 — `202` was advertising a process that does not exist

Both routes returned `202 Accepted` with a body. Neither defers anything: the draft discard and the
field removal are both persisted before the response is written, there is no `Location` header, and
there is nothing to poll. `DiscardRecordTypeDraft`'s OpenAPI text went further and told clients "the
record type draft discard process has started" — there is no process, and a client that believed the
description would have polled forever for a completion that had already happened.

**Resolved as `204`, not the `200`-with-body the MediaProfile pass chose for the identical pair.** Four
things pointed the same way and one pointed the other:

- `api-conventions.md § Async Operations` reserves `202` **exclusively** for the saga hand-offs listed in
  its table, and § 204 vs 202 vs 200 makes `204` the default for a mutation with nothing meaningful to
  return, with `200` reserved for a genuinely load-bearing body.
- Eight of the eleven `DELETE` endpoints in the repo are already `204`.
- `DELETE /record-types/{id}/capabilities/{capabilityType}` — same aggregate, same shape as M-2, removing
  a named sub-resource from the same draft — has always been `204`. Leaving M-2 on anything else would
  have had one aggregate answering the same question two ways.
- Neither body carried anything the caller lacked. `recordTypeId` and `fieldName` are path segments, and
  the timestamp was a **second** `GetUtcOffsetNow()` taken after the command returned — the same defect
  MP-4 found on `POST /profiles/{id}/publish`, so the value in the response never matched the timestamp
  on `RecordTypeDraftDiscarded` / `FieldRemovedFromRecordType`. Deleting the body deleted the bug rather
  than fixing it.

The one thing pointing the other way is the MP-2 decision of 2026-08-21, which put
`DELETE /v1/profiles/{profileId}/draft` and `DELETE /v1/profiles/{profileId}/asset-definitions/{roleName}`
on `200` with `{id, timestamp}`, reasoning that the body is load-bearing because the id is what the
caller re-fetches with. That reasoning is circular — the id is in the URL the caller just called — and it
is the argument that would justify a body on every one of the eight `204` routes. **Flagged to Chase
rather than reversed**, and both new spec sections carry an explicit "known divergence" note naming the
two Catalog routes so the next person finds the inconsistency documented instead of rediscovering it.
See *Still open* below.

Both `*Response` records deleted, both endpoints moved to the non-generic
`MetadataEndpointWithoutRequest` base (the shape `ForceReleaseCheckout` and `RenewCheckout` already use),
and both routes gained a spec section — **neither had one**. They existed only as a line in the route
table, which is why M-1 and M-2 could describe a `204` contract that no page ever elaborated.

#### M-3 — the finding said the code was wrong; the spec was wrong too, in the other direction

Accurate as written: every refusal in the module was `DomainError.InvalidOperation` → `422`, and the
only non-422 codes anywhere were `EntityAlreadyExists`/`ResourceNotFound` in Create, Rename and
SetAliases. But "make the code match the spec" was not the right fix, because three of the spec's `409`
claims were themselves wrong.

**The rule adopted**, now written into `recordtype.api.md` § *Refusal status codes* and into the
`DomainErrors` class doc:

| Code | When |
|---|---|
| `404` | A sub-resource **named in the URL path** does not exist — `{fieldName}`, `{capabilityType}` |
| `409` | A **duplicate**, or the **presence/absence of the draft** conflicts with the request |
| `422` | Content-level refusals, and terminal/initial states no retry will clear |

The discriminator is what the caller does next: after a `409` the *identical* request succeeds once one
other thing has been done; after a `422` it never does. That is RFC 9110 §15.5.10's actual definition of
409 — "a situation where the user might be able to resolve the conflict and resubmit" — and it is what
makes the two codes worth distinguishing at all.

**This narrows MI-6 rather than reversing it.** The `InvalidStatusTransition → 422` ruling of 2026-08-22
governs *status-machine* transitions, and every one of those stays on `422` here — including `Deprecate`
while a draft is open, which is deliberately **not** the `409` that `POST /draft` returns for the same
open draft. Draft presence/absence is not a status transition: a Published record type with no open
draft is in a perfectly valid status, and the thing that is missing is the draft.

Seven code changes, all in `DomainErrors`:

| Was | Now | Why |
|---|---|---|
| `NoDraftInProgress` 422 | **409** | 10 call sites. The caller opens a draft and resends the same request |
| `DraftAlreadyInProgress` 422 | **409** | `CreateDraft` only — a duplicate |
| `FieldNameConflict` 422 | **409** | Duplicate name against stored draft state |
| `CapabilityAlreadyAttached` 422 | **409** | Duplicate binding; same code as AssetManagement's `AssetAlreadyAttached` |
| `FieldNotFound` 422 | **404** | `{fieldName}` is a path segment |
| `CapabilityNotAttached` 422 | **404** | `{capabilityType}` is a path segment |
| `DraftInProgress` 422 | 422 *(kept, and split from `DraftAlreadyInProgress`)* | `Deprecate` only — a status-machine refusal |

Three spec corrections in the other direction:

- **`draft is empty` on publish was `409`, is `422`.** The draft exists; its contents are the problem,
  and adding a field is a different request to a different route.
- **`never published` on deprecate was `409`, is `422`.** Same reasoning. In practice the `Draft == null`
  guard fires first anyway, since a never-published record type still has its initial draft open — so
  both paths now return one code for "not in a deprecatable state", which is the only thing a client can
  act on.
- **Contributed-field collision on `POST /capabilities` was `400`, is `409`.** It is a duplicate name
  against stored draft state — the same condition `POST /fields` reports as `409`. A `400` told the
  client its request was malformed when the request was fine.

There is no generic `Conflict` factory in the platform SDK — `EntityAlreadyExists` is the only
409-mapped `Business` error and its "Entity Error" title reads wrong for a state conflict. Routed
through `DomainError.FromErrorCode(409, "Conflict", …)`, mirroring the private helper
`AssetManagement.Asset` already carries for exactly this reason. **That is now the second copy of the
same workaround** — see *Still open*.

#### M-4 — spec-only, as called, but the field itself is real and stays

Confirmed the finding: `GET /v1/record-types` is tenant-wide with no `ownerId` parameter and no owner
predicate, and the GSI is `RecordTypeByNameIndex` (PK `TENANT#{t}#RECORD_TYPES`, SK
`{name-lowercased}#{id}`), not the `OwnerIndex (OwnerId + Name)` the spec described. There is no
`"owner_system"` sentinel anywhere in the codebase and no owner check in any guard.

Removed from the spec: the `OwnerIndex` GSI, `ListRecordTypesByOwnerQuery`,
`ListRecordTypesByOwnerHandler`, "List by owner" in the route table, the Authorization table's
`caller.owner_id == recordType.OwnerId` rules, "unique within owner scope" on `Name`, the
`OwnerId IN [ownerId, "owner_system"]` query pattern, `OwnerId` from the summary-row field table, and
the owner actor line in the deprecation scenario.

**`OwnerId` itself stays**, per Chase's call. It is real — `PublisherId` on the aggregate, on
`RecordTypeCreated`, on the detail read model, and on the `GET /v1/record-types/{id}` response, set from
the JWT `sub` of whoever created the record type. Deleting it would be a breaking API *and* event-schema
change to remove the only record of who created a type. It is now documented as **provenance, not
authorization**, in all three places it appears, with an explicit "do not build a client that treats
this as an access-control input". The example value was also changed from `"owner_..."` to a UUID v7,
since `PublisherId` is an actor id and the old example implied a namespace scheme that does not exist.

Name uniqueness confirmed tenant-wide: `INameReservationService` under scope key `record-types`, no
owner component.

#### M-5 — the wrong number was on the live list endpoint, not a dead row

`RecordTypeSummaryProjector.ApplyAsync(RecordTypeCreated)` wrote `PublishedVersion = 1`.
`RecordTypeDetailProjector` has always written `0` for the same event, `RecordType.Version` is `0` until
the first `RecordTypePublished`, and `RecordTypeDetailReadModel` documents `// 0 before first publish`.
So `GET /v1/record-types` and `GET /v1/record-types/{id}` reported different published versions for the
same record type, and the list endpoint's answer named a version with no version-snapshot row behind it —
a client fetching `GET /v1/record-types/{id}/versions/1` on the strength of it gets a 404.

Kept as `int` with `0` as the documented "never published" sentinel rather than moving to `int?`. The
aggregate, the detail read model and the spec already agree on that representation; the defect was the
value, not the type, and changing the type would be a wire break for no gain.

**The finding could not see that this was live.** `recordtype.read-model.md` carried a note claiming
`RecordTypeSummaryReadModel` "is not currently used by any handler" and that the list handler reads the
detail model. Both halves are false — `ListRecordTypesHandler` injects
`IReadModelReader<RecordTypeSummaryReadModel>` and `RecordTypeSummaryModel` is the wire shape of every
row of `GET /v1/record-types`. That note is corrected. It matters beyond M-5: the MediaItem and
MediaProfile passes both left summary-row defects unfixed on the reasoning that nothing reads the
summary, and that reasoning does not transfer to Metadata.

#### Beyond the findings

- **Ten OpenAPI descriptions were unwritten TODOs shipped as published Swagger** — the same defect the
  MediaProfile pass found on three. `AddField` said "Document supported field types and validation
  rules", `RemoveCapability` said "Document that the change only takes effect on publish", `UpdateField`
  said "Document the fieldKey path param and…", and `Publish`'s ended in a stray `..`. All rewritten to
  say what the endpoint does. These are the endpoint descriptions clients read, not internal comments.
- **Every `summary.Response(422, …)` in the module listed conditions that are no longer 422.** All
  fifteen write endpoints had their `Produces`/`ProducesProblem` sets and response descriptions
  rewritten against the new mapping — ten gained `ProducesProblem(409)`, three gained a missing
  `ProducesProblem(422)`, and several `404` descriptions that said only "field key not found on draft"
  now also cover the missing-record-type case that the command handler raises.
- `CreateRecordType` never declared `422` despite `IFieldConstraintValidator` rejecting over-complex
  regex patterns on `initialFields`; `PatchRecordType` and `SetRecordTypeAliases` never declared it
  despite `RecordTypeDeprecated` being reachable on both.
- **Six `summary.Response` blurbs described guards that do not exist**, found on a verification pass over
  the change set and corrected. `POST /publish` claimed a name-uniqueness re-check at publish time —
  `PublishRecordTypeHandler` does no name check at all, unlike `PublishMediaProfileHandler` in Catalog,
  which does swap a reservation. `PUT /fields/{fieldName}` claimed immutability and order-collision
  refusals — `ReplaceField` checks neither, so **replacing an `IsImmutable` field is currently
  accepted**, which is an aggregate gap rather than a documentation one and is now recorded in the spec.
  `POST /deprecate` claimed attachment to a published MediaProfile blocks deprecation — nothing checks
  that, and it should not, since profiles keep validating against pinned versions. `PUT /aliases`
  claimed a malformed alias is `422`; the endpoint rejects it at `400` before the aggregate sees it.
  `POST /fields/reorder` claimed an unknown field name is `404`; `ReorderFields` compares the payload to
  the draft as a **set**, so an unknown *or* a missing name is one `FieldOrderMismatch` → `422`.
- **Three more orphaned `*Response` records deleted** — `RemoveCapabilityFromRecordTypeResponse`,
  `DeprecateFieldInRecordTypeResponse`, `DeprecateRecordTypeResponse`, the last two already marked
  "DEAD CODE" in their own doc comments since 2026-07-08. `RemoveCapabilityFromRecordTypeEndpoint` also
  still declared a `TResponse` it never sent while returning `204`, which put a phantom schema on a
  No-Content response in the published OpenAPI document; moved to the non-generic base like the two
  converted here. `CreateRecordTypeResponse` and `PublishRecordTypeResponse` are the only two left, and
  both are live.

#### Tests

`RecordTypeRefusalStatusCodeTests` — 22 facts pinning `error.ErrorType.HttpStatusCode` for every refusal
path the rule covers: nine `409`s for the absent draft, three `409`s for duplicates, five `404`s for
missing path sub-resources, and five `422`s for content and terminal-state refusals. These are the wire
contract a client branches on, so the file says in its own doc comment that a failure here is a spec
decision to be made, not an expectation to be updated.

`RecordTypeSummaryProjectorTests.ApplyAsync_WhenRecordTypeCreated_ShouldCreateSummaryReadModel` asserted
`PublishedVersion.Should().Be(1)` — the defect was pinned by a passing test. Flipped to `0` with the
reason inline.

#### Still open after this pass

| Item | State |
|---|---|
| Nothing compiled | Still no `dotnet` in the sandbox. Two endpoints changed base class, two response records were deleted, `DomainErrors` gained a member and changed seven mappings, and a new test file was added. Build and run `Metadata.WriteModel.Tests` and `Metadata.ReadModel.Tests` before pushing. |
| **`media-record-types` needs a replay** | The projector is fixed; the rows it already wrote are not. Every record type created before this change still reads back `publishedVersion: 1` from `GET /v1/record-types` whether or not it has ever been published. `src/tools/ProjectionReplay`, scoped to the summary rows of `media-record-types`. Third such replay left open, after `child-items` (MI) and `media-profiles` (MP) — these are accumulating and should be run together. |
| ~~MediaProfile's two `200` DELETEs are the only outliers~~ | **Closed same day — Chase approved the flip.** Both are now `204`; see the MP-2 reversal entry below. |
| **Second copy of the `Conflict` workaround** | `DomainError.FromErrorCode(409, "Conflict", …)` now exists in both `AssetManagement.Asset` and `Metadata.DomainErrors`, each with the same explanatory comment about the platform having no generic Conflict factory. `ErrorType.Business` has `ResourceExists` (409) but nothing for a state conflict. This belongs in `aspnetcore-platform` as `DomainError.Conflict(...)` / `ErrorType.Business.Conflict`; ChangeRequests and DocumentSigning will both want it. Worth a ticket before a third copy appears. |
| M-14 — no `errorCode` anywhere in the module | Untouched, as scoped. The module emits no `WithCode`, and `error-catalog.md` still has **no Metadata section at all**, so the eleven named codes in `recordtype.api.md`'s examples (`NoActiveDraft`, `FieldNameConflict`, `MigrationNoteRequired`, …) are illustrative only. The status codes are now right and the codes are still absent — that gap is wider after this pass, not narrower, because a client that can branch on 404/409/422 will next want the code. |
| **M-13 is worse than "Med" and is reachable from a route this pass just touched** | `Apply(FieldRemovedFromRecordType)` sets `Draft = null` when the last field goes. On a **never-published** record type that produces `Draft == null && Version == 0` — precisely the permanently-inert state `CannotDiscardInitialDraft` exists to prevent, and which no command can recover: `AddField`/`Publish` → `409`, `CreateDraft` → `422 NothingToRevise`, `Deprecate` → `422 NothingToDeprecate`. So `DELETE /record-types/{id}/fields/{fieldName}` can brick a record type and answer `204`, and the `204` contract written for it this pass says the opposite ("removes the field from the open draft"). One-line fix (`Draft = Draft with { Fields = fields }`), but it is a behaviour change and was left for M-13 rather than smuggled into a status-code pass. **Raise its severity.** |
| ~~M-12 partially fell out of this pass~~ | **Closed below** — the `Draft == null` guard is now in the write-model invariant table too. | The undocumented `Draft == null` guard on `Deprecate()` is now written into `recordtype.api.md` § Deprecate, with its `422` and the reason it is not the `409` that `POST /draft` returns. **Left unticked:** `recordtype.write-model.md`'s invariant table still omits it, and that table is M-16's subject. Close M-12 with M-16. |
| M-6 … M-19 | M-6 and M-7 were already closed. M-8 (field deprecation marking *every* draft field) is the remaining correctness bug in the module and is the natural next one. M-9 (aliases unreadable via the API) is the remaining contract hole. |
| `RecordTypeVersionSnapshotReadModel` still specced, still nonexistent | M-18. `recordtype.read-model.md` describes a type the codebase does not have and one projector where there are four. Not touched here. |

### 2026-08-22 — MP-2 reversed: the last two `200` DELETEs are now `204`

Follow-on from the Metadata pass, at Chase's direction. `DELETE /v1/profiles/{profileId}/draft` and
`DELETE /v1/profiles/{profileId}/asset-definitions/{roleName}` were the only two non-`204` `DELETE`
endpoints in the platform. Both now return `204 No Content`.

**What survived from MP-2 and what did not.** The synchronous half of the original reasoning was right
and is retained in the spec: the work completes inside the request, so `202` would be a lie. The half
that did not survive is "the body is load-bearing: `profileId` is what the caller uses to re-fetch the
profile afterwards". `profileId` is the path segment the caller had just supplied. The argument is
circular, and applied consistently it would put a body on all ten of the other DELETEs.

**The timestamps were an actual bug, not just redundancy.** Both `discardedAt` and `removedAt` were a
*second* `context.GetUtcOffsetNow()` read taken after the command returned, so neither ever equalled the
timestamp on `MediaProfileDraftDiscarded` or `AssetDefinitionRemoved`. This is the third instance of the
same defect — MP-4 found it on `POST /profiles/{id}/publish` and fixed it by collapsing to one clock
read; M-1/M-2 found it on the two Metadata DELETEs. Here, deleting the body deleted the bug outright.

Both endpoints moved to the non-generic `CatalogEndpointWithoutRequest`, both `*Response` records
deleted, `Produces(200)` → `Produces(204)`, `SendOkAsync` → `SendNoContentAsync`. **Eleven of eleven
DELETEs in the platform now answer `204`**, and the "known divergence" notes the Metadata pass had to
write into `recordtype.api.md` a few hours earlier are gone.

`api-conventions.md` gained the missing definition. § *204 No Content vs 202 Accepted vs 200 OK* said
`200` is for "a meaningful body" without saying what meaningful means, which is the gap MP-2 walked into.
It now states the rule: **an identifier echoed back from the request path is not meaningful, and a server
clock read taken after the command returned is not meaningful either** — it is not the timestamp on the
resulting event, so publishing it invites clients to correlate two values that never agree.

**This is a breaking change** for any client reading either response body, and is flagged as such in
`mediaprofile.api.md`. The migration is to stop reading the body: neither carried anything the client
cannot reconstruct from the request it just made, so there is no field to go and source elsewhere.

#### Beyond the change

- **`RemoveAssetDefinition`'s OpenAPI description was an unwritten TODO** — "Document that removing an
  asset definition… Document that removal is not allowed if it would leave existing assets without a
  definition." The second sentence described a guard the aggregate does not have. Rewritten to what the
  endpoint does.
- Its `summary.Response(404, …)` said "media profile **or asset definition** not found", contradicting
  both the aggregate (a role not on the draft is `DomainError.InvalidOperation` → `422`) and the
  endpoint's own description two lines above. Corrected.

#### Still open

| Item | State |
|---|---|
| Nothing compiled | Same as the Metadata pass — no `dotnet` in the sandbox. Two endpoints changed base class and two response records were deleted. No test under `tests/` exercises either route at the HTTP level (verified), so the risk is compile-only. |
| **`{roleName}` is a `422` in Catalog and a `404` in Metadata** | `DELETE /v1/profiles/{profileId}/asset-definitions/{roleName}` refuses an unknown role with `422`, deliberately (MP-2). `DELETE /v1/record-types/{id}/fields/{fieldName}` and `.../capabilities/{capabilityType}` now refuse an unknown one with `404` (M-3), on the rule that a sub-resource named in the URL path gets a `404`. Both are defensible in isolation; together they are two answers to the same question one module apart. **Not touched** — this pass was scoped to the success code. Worth settling before ChangeRequests and DocumentSigning pick a third answer. |
| Nine more endpoints declare a `TResponse` they never send | `ArchiveCollection`, `ArchiveFolder`, `CloseFolder`, `CommitFolderMetadata`, `DetachRecordType`, `DeleteComment`, `CancelRegistration`, `ResubmitRegistration`, `SubmitRegistration` — all return `204` while declaring a response type, which puts a phantom schema on a No-Content response in the published OpenAPI document. Same one-line cleanup applied here and to `RemoveCapabilityFromRecordType`. Cosmetic, but it is the published Swagger. |
| `403` is declared platform-wide and returned nowhere | Noted while verifying both endpoints' declared code sets. Every write endpoint declares `ProducesProblem(403)`; no code path produces `Forbidden`. That is the deferred auth plan's problem, recorded here so it is not rediscovered a fourth time. |
| `MediaProfileId.From` on a malformed id throws → `500`, not `400` | Both endpoints advertise `400` for "the media profile Id is malformed". The value-object parse throws rather than returning a validation failure. Platform-wide, not specific to these routes. |

### 2026-08-22 — Metadata pass, M-8 to M-19 (D, remainder)

Twelve findings, closing the Metadata module. Four were live bugs, three were contract holes, one was a
guard gap that turned out to be exploitable, and four were spec-only. Two things found here were not in
the review at all and are the more serious half of the pass.

#### The four bugs

**M-8 — deprecating one field deprecated the whole schema.** `RecordTypeDetailProjector` mapped
`IsDeprecated = true` across *every* entry in `draftFields`. So `POST /draft/fields/{fieldName}/deprecate`
returned `204` and the next `GET` reported a draft in which nothing was writable. Above it sat a comment
reading "FieldDefinitionDto has no IsDeprecated field — deprecation is a domain-level state that the read
model does not currently surface. No-op." It described neither the DTO, which has carried the field all
along, nor the code, which was very much not a no-op — a stale comment actively arguing against reading
the line below it.

**M-13 — removing a field could brick a record type, and answer `204` doing it.**
`Apply(FieldRemovedFromRecordType)` set `Draft = null` when the last field went. On a **never-published**
record type that produces `Draft == null && Version == 0` — precisely the permanently inert state
`CannotDiscardInitialDraft` exists to prevent, and which no command recovers: `AddField` and `Publish`
return `409 NoActiveDraft`, `CreateDraft` returns `422 NothingToRevise`, `Deprecate` returns
`422 RecordTypeNotPublished`. The finding rated this "Med". It is the most destructive thing in the
module and it is reachable from `DELETE /record-types/{id}/fields/{fieldName}` — the route M-2 had just
finished documenting as a clean `204`.

An empty draft is a legitimate intermediate state; `Publish()` already refuses one with `DraftEmpty`. The
detail projector carried the same defect as `HasDraft = fields.Count > 0` and is fixed with it. **An
existing test asserted the bug** — `RemoveField_MutableField_RemovesFromDraft` ended
`rt.Draft.Should().BeNull(); // removing last field collapses draft to null`. It has been inverted with
the reason recorded, since a passing test is exactly why nobody found this.

**M-5's sibling, M-19 — `SetAliases` emitted events describing no change.** `SequenceEqual` made the
no-op check order-sensitive, so `PUT /aliases` with `["inv","invoice"]` over a stored
`["invoice","inv"]` raised a `RecordTypeAliasesUpdated` whose `OldAliases` and `NewAliases` held identical
members. That event then re-pinned on the next publish and appears in any audit trail as a modification
that never happened. An alias set is a set — nothing anywhere reads position — so the check is now
`SetEquals`, guarded by a count check so a subset cannot read as equal.

**M-11 — `pageSize` missing from the versions envelope.** Same defect the MediaProfile pass found on two
Catalog envelopes. Without it a client cannot distinguish a short final page from a truncated one, which
is the only thing the field is for. Additive.

#### M-9 / M-10 — the ADR-013 qualifier was documented, published, and unobtainable

`recordtype.api.md` told clients to read `aliases` from `GET /v1/record-types/{recordTypeId}` to discover
the collision qualifier. There was no `Aliases` on the read model, no `aliases` on the response, and **no
projector handling `RecordTypeAliasesUpdated` at all**. So `PUT /aliases` returned `204` and the caller
could never read back what it had set. The single documented route to the qualifier was a dead end.

**The version rows matter more than the detail row, and that is the part the findings could not see.**
`RecordTypePublished` has always carried the pinned alias set per ADR-013 Decision 2; both version
projectors received it and dropped it. A MediaProfile pinned to v1 of a record type whose aliases have
since changed must qualify its field names with **v1's** aliases — the current set on the detail row is
the wrong answer for it, and returning the wrong answer is worse than returning none. Now projected onto
the detail row, the version-detail row and the version-summary row. Exactly the shape MP-1 hit on
MediaProfile's compiled template a day earlier.

Carried on the version *summary* row too, deliberately diverging from MP-1's withholding of the compiled
template from list rows: an alias set is a handful of short strings, and that row already carries the
entire `FieldSnapshot`, so there is no payload argument. All three use an **init property with a `[]`
default** rather than a positional parameter, so rows written before this existed read back `[]` rather
than `null` behind a non-nullable type — the pattern `MediaProfileDetailReadModel.CompiledMetadataFields`
established.

**M-10's naming went against the spec on two counts and with it on one.** `recordTypeId` stays, not `id`:
a version is a sub-resource keyed by `(parentId, versionNumber)` with no identifier of its own, so the
parent id is a foreign reference — ADR § Response Identifier Naming, Rule 3, and exactly what
`GetMediaProfileVersionResponse` does. `versionNumber` stays, not `version`, matching Rule 3's worked
example and every other version contract on the platform. But the **list** rows serialised it as
`version` while the by-version route said `versionNumber`, so a client could not reuse a row's own value
to build the follow-up request; the list row is renamed. `name` and `capabilities` are returned and were
simply missing from the spec.

#### M-16 — the missing guards were exploitable, not cosmetic

The finding said the aggregate had six rejections the invariant table did not document. Reviewing the
guards as instructed turned up the opposite problem on `ReplaceField`, which had **none** of the
integrity checks its neighbours had:

- **An `IsImmutable` field could be replaced.** `RemoveField` refuses one. Replace is a remove-and-add
  that retires the old key, so a caller blocked by `RemoveField` replaced the field instead and got the
  same result. **Immutability was decorative** — the guard it advertises was bypassable by using a
  different verb on the same path.
- **The replacement's name was never checked against the rest of the draft.** Replacing `title` with a
  field named `subtitle` while `subtitle` already existed produced a draft holding two fields with the
  same name — a state `AddField` has always refused to create.
- **An explicitly supplied `order` was accepted unchecked**, making replace the one route to two fields
  sharing a display order.
- **The 1000-character migration-note limit reported `MigrationNoteRequired`**, telling a caller who had
  written 1,200 characters that a note was "required". Split into `MigrationNoteTooLong`.

Replacing a field with the *same* name is explicitly still allowed — it is the documented way to change a
field's type, and the collision guard excludes it.

The invariant table went from twelve rows to twenty-one. `RecordTypeNameNotUnique` and `NoDraftToPublish`
were never real codes.

#### M-12 — kept, and documented

`Deprecate()` refuses while a draft is open. That guard is right: every draft command refuses once
`IsDeprecated`, so deprecating with a draft open would strand it unreachable. Kept, and deliberately a
`422` rather than the `409` that `CreateDraft` returns for the same open draft — this is a status-machine
refusal, which is the MI-6 line. Now in the API guards list and the write-model invariant table.

#### M-14 — eleven published codes, none emitted

`recordtype.api.md` named ten `errorCode` values in its error examples and `error-catalog.md` had **no
Metadata section at all**. The module emitted no codes anywhere. After M-3 that gap got worse, not
better: three statuses now cover twenty-eight distinct conditions, and a `422` on
`PUT /fields/{fieldName}` could be five different things.

`RecordTypeErrorCodes` now carries 28 constants, every `DomainErrors` factory and every handler-raised
refusal is tagged, and `MetadataEndpoint`'s four `SendDomainErrorAsync` overloads pass the code through to
`extensions.errorCode`. The catalog gained a Metadata section, split into identity, draft lifecycle,
fields and capabilities.

Two of the published names were wrong and are corrected rather than invented into existence:
`ImmutableFieldsBlockRemoval` is not a code — the condition is real and `CannotRemoveImmutableField` is
what fires, covering the field path and the capability path alike. `EntityAlreadyExists` in the alias
example is the platform `ErrorType` name, not an `errorCode`; alias conflicts carry
`RecordTypeAliasNotUnique`.

`InvalidRecordTypeAlias` was a dead factory for a condition the API answers with `400` at the endpoint,
before a command is ever built. Deleted; the endpoint now emits the documented code on that `400`.

**This is the second copy of `WithCode`/`CodeOrNull`** — a module cannot reference another module's Domain
project, so the alternative was leaving Metadata untagged. See *Still open*.

#### M-15 / M-17 / M-18 — the spec described a system that was not there

- **M-15.** `IRecordTypeUnicityService` does not exist and never did. Name uniqueness uses the
  platform-shared `INameReservationService` under scope key `record-types`, exactly as aliases use it
  under `record-type-aliases`. Worth noting the semantics were **inverted**: the deleted interface was
  documented as `NameExistsAsync` returning `true` when the name is taken; `IsNameAvailableAsync` returns
  `true` when it is free. Anyone coding to the old doc would have had the check backwards.
- **M-17.** `FieldDeprecatedInRecordType`, `RecordTypeDescriptionUpdated`,
  `UpdateRecordTypeDescriptionCommand` and `DeprecateFieldInRecordTypeCommand` all exist, are wired, and
  were absent from the event and command tables. Added.
- **M-18.** There is no `RecordTypeProjector` — there are four projectors, split by row type. There is no
  `RecordTypeVersionSnapshotReadModel`. `GetRecordTypeVersionHandler` reads
  `RecordTypeVersionDetailReadModel`, not the summary. And the version *summary* row is **not**
  lightweight: the spec said it "omits `FieldSnapshot` to keep list reads cheap" and it carries the full
  snapshot, so `GET /versions` returns a complete field schema per row. That is a real cost worth
  revisiting; the spec now says what ships. `FieldDefinitionDto` was also missing `IsDeprecated`,
  `IsImmutable` and `AllowsConcurrentEdit`, and the detail model block still had a `UpdatedAt` that does
  not exist and a `RecordTypeId` that is `Id`.

#### Tests

Two new files, 21 facts. `RecordTypeDraftIntegrityTests` covers M-13 (including the never-published
brick case, asserted by proving the record type is still publishable afterwards), all four new
`ReplaceField` guards plus the same-name case that must **not** be caught, the note limit at exactly 1000
and at 1001, and M-19's reorder-is-not-a-change assertion via `GetUncommittedEvents().Count`.
`RecordTypeAliasAndDeprecationProjectionTests` covers M-8 with three fields in and exactly one deprecated
out — a two-field fixture would pass under the old code by coincidence — plus the alias projection on all
three rows, the clear-to-`[]` case, and the pre-projection default.

#### Still open after this pass

| Item | State |
|---|---|
| Nothing compiled | No `dotnet` in the sandbox, as throughout. An aggregate gained four guards and two constants, 17 handlers changed, three read models gained an init property, four response DTOs changed shape, and three test files were added or amended. Build and run `Metadata.WriteModel.Tests` and `Metadata.ReadModel.Tests` before pushing. |
| **`media-record-types` replay, now for three reasons** | `publishedVersion` (M-5), `aliases` on the detail and both version rows (M-9/M-10), and any draft where a single field deprecation marked every field (M-8). Rows written before today are wrong in all three ways. `src/tools/ProjectionReplay`, scoped to `media-record-types`. Fourth outstanding replay after `child-items` (MI) and `media-profiles` (MP) — these should be run together, and the backlog is now large enough to be its own ticket. |
| **`RecordTypeVersionSummaryReadModel` carries the full `FieldSnapshot`** | Surfaced by M-18. `GET /v1/record-types/{id}/versions` returns a complete field schema for every version on the page. The spec used to claim it omitted the snapshot; it never did. Trimming it is a client-visible change to a list contract, so it was documented rather than done. |
| `VersionNumber` is `long` on the summary row and `int` on the detail row | Same field, same event, two types. Recorded in the spec rather than harmonised in a pass that was not about it. |
| **`WithCode`/`CodeOrNull` is now duplicated per module** | Second verbatim copy, after Catalog's. Together with the `DomainError.Conflict` workaround from M-3, that is two things every module needs and the platform does not provide. `ErrorType.Business` has `ResourceExists` (409) but nothing for a state conflict, and `DomainError` has no code concept at all. Both belong in `aspnetcore-platform`; ChangeRequests and DocumentSigning will want a third copy otherwise. |
| Line-ending churn on this branch | The repo is CRLF with no `.gitattributes`. On a Linux mount `git diff --numstat` reports a whole-file rewrite for every CRLF file, touched or not, which makes the raw diff unreviewable — review with `--ignore-cr-at-eol`. A `.gitattributes` with `*.cs text eol=crlf` would end this permanently and is worth its own small PR. |
| `403` declared everywhere, returned nowhere | Carried forward from the MediaProfile entry. Every Metadata write endpoint declares `ProducesProblem(403)`; no code path produces `Forbidden`. Deferred auth plan. |
| **Metadata is now closed; C.6 is what remains of Catalog** | M-1 to M-19 are all ticked. BI-1/BI-2/BI-3 — two fully specced aggregates with nothing behind them at any layer — are the remaining Catalog work, and are a build rather than a drift fix. |

---

### 2026-08-22 — Registration pass, R-1 to R-19 (E, complete)

Eighteen findings, closing the Registration module. The shape of this one is different from the
Catalog and Metadata passes: fewer projector bugs, far more **contract** drift — six of the eighteen
were request or response bodies that did not match what the spec published, and two were live
authorization holes.

#### What Registration is for, and why the authorization findings are the serious half

A `Registration` tracks the formal filing of a published MediaItem with an **external authority** — a
copyright office, a deposit library, a regulator. The owner initiates it, attaches supporting
documents, and submits; an integration adapter dispatches it and records that dispatch; the authority
confirms or rejects. A `Confirmed` registration is a permanent legal record: it cannot be cancelled,
it is retained for a statutory minimum of ten years, and it survives tenant offboarding into a
compliance archive. Post-confirmation changes go through an amendment workflow that requires explicit
system-actor approval per document.

That is the context for R-3 and R-8. **No handler compared the caller to the registration's owner**,
so any authenticated user in the tenant could cancel, submit or amend another user's filing — and
**search filtered on tenant alone**, so any user could read every registration in the tenant,
including the reference numbers and authorities of other people's filings. The list endpoint scoped
correctly by owner; search was a hole straight around its boundary. The commands have carried a
`RequestingUser` field since they were written and nothing ever read it.

Both are now enforced, reading the caller from the execution context rather than the payload, in the
shape `AssetManagement.AssetOwnership` established (AM-2). Applied to the five owner-driven commands
only — the five `[System]` ones are dispatched by the integration adapter on the authority's behalf,
not the owner's, and gating them would break every automated path. `actor_type` gating on those five
remains edge authorization and stays with the separate auth plan.

#### R-4 — the eligibility check was inverted, and it was the wrong check

The spec has always said an attached supporting document must be `Published` **and its profile must
lack the `Processing` capability**. Both attach handlers checked `HasRegistrationCapability` instead.
That is wrong in both directions, and the direction that matters is the one nobody would notice:

- A **plain application form** — a PDF whose profile carries no `Registration` capability, because the
  form is not the thing being registered — **could not be attached at all**. The primary use case of
  the endpoint was rejected.
- A **processed video** could be attached as "supporting evidence", which is exactly what the
  `Processing` rule exists to prevent.

`HasProcessingCapability` was already on the reference model, already documented in the write-model
spec as "must be `false`", and **never read**. Verified as instructed before changing anything: the
spec is right, and the two checks are deliberately opposite — the item being *registered* must have
`Registration`, the item being *attached* must lack `Processing`. Registering processed media (a film,
a recording) is the ordinary case, which is why no processing check belongs on the initiate path. The
reference-model prose that claimed initiate also required lacking `Processing` was wrong and is
corrected with it.

#### R-1 — the status was named after the event that produced it

One state sits between dispatch and the authority's decision. The spec called it
`PendingConfirmation` in five documents; the enum called it `SubmissionRecorded`. Not two states — one
state, two names, and `status` is published contract.

Resolved in the spec's favour, and the reasoning is not just "the spec said so five times":
`SubmissionRecorded` is an event name used as a status. Every other member of that enum is either a
state (`Initiated`, `Confirmed`, `Cancelled`) or the owner's own action (`Submitted`, `Resubmitted`),
and `MediaItemStatus.PendingApproval` on the neighbouring aggregate is the same shape. The **event
keeps** the name `RegistrationSubmissionRecorded` — events name what happened, statuses name where you
are, and collapsing that distinction is what produced the drift.

**No replay needed.** The rename was in place at ordinal 2, and the enum is persisted numerically
everywhere it is persisted at all — `RegistrationCancelled.PreviousStatus` in the event store, and
both read-model tables. Stored bytes are unchanged.

#### R-13 — and a status-code ruling that went against this module's own spec

The module emitted **no `errorCode` anywhere** while `registration.api.md` published nine of them in
its error examples, and every refusal was a bare `InvalidOperation` → 422. A caller could not tell
"wrong status" from "already attached" from "amendment already decided" without parsing the message.

`RegistrationErrorCodes` now carries 19 constants, every `DomainErrors` factory and every
handler-raised refusal is tagged, and `RegistrationEndpoint`'s three base classes pass the code through
to `extensions.errorCode`.

**The status codes went against `registration.api.md`, deliberately.** That document published `409`
on six invalid-status-transition sites. That contradicts the `InvalidStatusTransition → 422` row in
`error-catalog.md § Common`, the MI-6 ruling that settled the same question for MediaItem on
2026-08-22, and M-3's reaffirmation of it for Metadata the same day. Three modules answering the same
class of refusal with two different statuses is the outcome worth avoiding, so **the spec was
corrected and the code follows the platform rule**. Four buckets now, written up in the write model:

- **404** — a resource named in the path or body: the registration, an `amendmentId`, a media item.
- **409** — duplicates only. Exactly two: `ItemAlreadyAttached` and `DuplicatePendingAmendment`.
- **422** — status-machine refusals and content the target's rules reject.
- **403** — the owner check.

**One refusal was split.** "Amendment does not exist **or** is not Pending" was a single `422`. Those
are different answers: a `404` means the id is wrong, a `422` means the id is right and someone got
there first — idempotent replay versus a bug. `amendmentId` is a path segment, which is what makes the
missing case a 404 under the same rule M-3 applied to `fieldName`.

`DocumentAlreadyAttached` was published in the catalog and is not a code the module ever raised; the
condition is real and fires as `ItemAlreadyAttached`, matching the module's vocabulary — "item"
everywhere except the route segment.

#### R-11 — a caller could backdate a legal record

`POST /confirm` accepted `confirmedAt` and stamped it onto `RegistrationConfirmed` verbatim. The spec
documents the body as `{reference}` and nothing else. Registrations are the one aggregate where a
falsified timestamp has legal weight — a confirmed filing is a public record with a statutory
retention clock that starts at that instant. Removed; the server stamps from the execution context,
as every other write on this aggregate already did. The finding rated this "Med"; it is the most
serious single line in the module after the two authorization holes.

#### R-12 / R-16 — one read-model field was doing two unrelated jobs

`POST /submission` was specced as taking no body. It accepted `{externalReference, notes}`, and the
detail projector wrote that `notes` — the integration adapter's dispatch note — into the read model's
`Notes` field, which the API documents as *the owner's* note ("Standard copyright filing for film
asset"). Two different things, one field, and no way to tell them apart on read.

Worse, the owner's note had **no source at all**: `Notes` was declared on the aggregate, the spec's
event table listed `Notes?` on `RegistrationInitiated`, and the event did not carry one — so nothing
ever assigned it. The property had been inert since the aggregate was written.

Both halves fixed rather than either half deleted. The body is genuinely useful — the adapter has an
acknowledgement reference and dispatch details to record, and the event has always carried both — so
its fields are renamed after the event fields they populate (`submissionReference`, `dispatchDetails`)
and land in their own read-model columns. `RegistrationInitiated` gains `Notes?`, nullable and
appended after the required fields, so events written before it deserialise to `null` and no replay is
needed for that either.

#### R-5 / R-7 — one rename fixed a contract and a bug at the same time

The detail read model called the authority's reference `ReferenceNumber`. The aggregate property, the
event field, the summary read model and the API spec all said `Reference`. That single divergence
produced two separate defects:

- `GET /v1/registrations/{id}` returned no `reference` field at all — the documented one was missing
  and an undocumented `referenceNumber` sat in its place.
- **Every search result came back with `reference: null`**, even for confirmed registrations (R-7).
  The search handler indexes the *detail* model and deserialised `_source` straight into the *summary*
  record; System.Text.Json binds by name and silently defaults what it cannot find. Search now
  deserialises the model that is actually indexed and narrows it in an explicit mapping, so the next
  divergence is a compile error rather than a null.

Six more response fields were reconciled the same way — `externalReference` → `submissionReference`,
`addedAt` → `attachedAt`, `decidedAt` → `resolvedAt`, `amendments[].amendmentId` → `id` (ADR-012 Rule
1) — and six real, populated, undocumented fields were documented rather than removed.

**`expiresAt` was removed rather than deferred.** No event carried it, no projector wrote it, and
registrations have no expiry concept anywhere in the spec. It returned `null` on every response since
the model was written. Same call MI-4 made on `status`.

#### R-17 — the index rename was free, exactly once

The OpenSearch index was `registrations` — the only index on the platform without the `media-` prefix,
against both `MediaItemsIndexMapping` (`media-items`) and the read-model spec. Renaming an index
normally means a reindex and a cutover. This one had **never successfully accepted a single
document**: the mapping is `dynamic: "strict"` and declared `RegistrationId` while the projected model
had renamed its identifier to `Id`, so every indexing request was rejected until R-6 fixed it days
ago. There was nothing to migrate, and the window closes the moment the R-6 fix ships.

The name is now declared in three places that must move together — the mapping (canonical), the search
index schema, and a literal const in the query handler, because a module cannot reference a host. That
duplication is called out in a comment on each.

The same `dynamic: "strict"` property is why the R-5 renames **had** to land in the mapping in the same
change: a rename on one side alone silently stops all indexing with no error anywhere.

#### Beyond the findings

Four things this pass found that the review did not have:

- **`Status` was being indexed as an ordinal.** Neither read model carried a
  `JsonStringEnumConverter`, so the OpenSearch document held `2` where the mapping declares a
  `keyword`, and every status filter or facet would have matched nothing. Identical defect and
  identical fix to the one the MediaItem pass found. Scoped to the property, never the enum type — the
  event store's numeric form must not move.
- **`AddError("q", "Search term is required.")` sent the message "q".** FastEndpoints has no
  `(propertyName, message)` string overload; the two-string form binds to `(message, errorCode)`. A
  Catalog pass already found and fixed this exact line on `SearchMediaItems`; Registration had the
  same bug and nobody swept for it.
- **`pageSize` was uncapped on `GET /v1/registrations`**, despite the spec and the endpoint's own
  OpenAPI summary both claiming a maximum of 100. One caller could pull an entire tenant's
  registrations in a single DynamoDB query. `RegistrationPaging` mirrors `CatalogPaging`.
- **`RegistrationDocumentDto` was dead** — zero references anywhere. Deleted.

Three spec files outside the Registration folder carried the same drift and were corrected with it:
`bounded-context.md` and `service-boundaries.md` both listed a `RegistrationProjector` handling
`RegistrationDocumentAttached` and `RegistrationExpiryRecorded` — none of which exist — and
`adrs/persistence-and-eventing.md` named the same non-existent projector as the owner of the
OpenSearch index.

#### Determinations that went against the finding

- **R-10, `amendmentId`.** The spec published a caller-supplied `amendmentId` in the request body. The
  server generates it and returns it as `id`, which is how every other identifier on this platform
  works, and idempotency is the `IdempotencyKey` header's job — which this endpoint already accepts.
  The spec is wrong; the code stays.
- **R-15, GSI names.** `RegistrationByMediaItemIndex` / `RegistrationByOwnerIndex` follow the
  platform-wide `<Entity>By<Key>Index` convention and match the CDK manifest that the CI drift gate
  enforces across repos. The spec's `MediaItemRegistrationsIndex` / `OwnerStatusIndex` are fiction.
  The `OwnerId + Status` key is fiction too — no endpoint takes a `status` filter, so nothing was
  asking for it, and the spec now records that status-filtered owner queries are not supported.
- **R-17, field casing.** The spec documents camelCase index fields; the mapping, the documents and
  the DSL are all PascalCase and internally consistent. These names never appear on the wire, so
  changing them would mean a serializer policy and a reindex to fix nothing. Spec corrected.
- **R-19, `AmendmentRequested` status.** The spec had the detail projector setting the registration's
  status to `AmendmentRequested`. There is no such status and there must not be: a confirmed
  registration is a permanent external record and does not leave `Confirmed` because someone asked to
  add a receipt. The amendment carries its own `Pending → Approved | Rejected`. The read-model spec's
  twelve-member status enum — which conflated the two — is now the real seven.

#### Tests

Two new files, 21 facts. `RegistrationRefusalTests` pins the R-1 lifecycle and the whole R-13
status/code map, including the 404-vs-422 amendment split and the notes limit at exactly 1000 and
1001. `RegistrationOwnershipAndEligibilityTests` covers R-3 (owner allowed, stranger 403 with the
repository verified never to save, system actor allowed, no actor denied) and R-4 — including the case
that matters most, a plain document whose profile has **no** `Registration` capability being accepted,
which the old check rejected.

**The existing handler tests had to change, and that is the point.** They passed
`new Mock<ICommandHandlingContext>()`, whose `Actor` is null, so every one of them is now denied by
the fail-closed guard. `TestCommandContext` supplies a real actor rather than the guard being relaxed
to accommodate them.

#### Still open after this pass

| Item | State |
|---|---|
| Nothing compiled | No `dotnet` in the sandbox, as throughout. An aggregate gained a parameter and eight new refusals, 11 handlers changed, two read models changed shape, seven request/response DTOs changed, an OpenSearch index was renamed, and three test files were added or amended. A no-compiler review caught four defects that were fixed before this entry was written; build and run `Registration.WriteModel.Tests` and `Registration.ReadModel.Tests` before pushing. |
| **`media-registration` and `media-registrations` replay** | Two new rows on the N.1 backlog, both same-version corruption. Every registration ever confirmed has its authority reference in a `ReferenceNumber` attribute that nothing reads any more, dispatch details sitting in `Notes`, and no `dispatchDetails`. Rows 8 and 9. |
| **The OpenSearch index has to be created before search works** | `media-registrations` is a new index name. `QueryApiOpenSearchStartup` does an idempotent PUT from the constant, so a deploy creates it — but it will be **empty**, and the only thing that populates it is the detail projector on live events. Backfilling it means the same replay as row 8. Nothing is lost: the old `registrations` index never accepted a document. |
| `errorCode` still does not reach the wire on read endpoints | Not new — X-10.3 already records it. `ErrorCodeResponseConfigurator` is registered in `Api` only, so `SearchTermRequired` and every `GET`'s 404 carry a code that `QueryApi` drops. Tagged at the raise site anyway, so it becomes correct the moment the configurator moves. |
| **`WithCode`/`CodeOrNull` is now on its third verbatim copy** | Catalog, Metadata, and now Registration. Together with a third copy of the `DomainError.Conflict` workaround, that is two things every module needs and the platform does not provide. The ready-to-use prompt in § N.2 is unchanged and now has one more consuming-app file to delete when it lands. |
| `403` declared everywhere, returned nowhere — **no longer true here** | Registration's write endpoints declare `ProducesProblem(403)` and now genuinely produce it, from `NotResourceOwner`. It remains true of the other modules. |
| Registration is closed; F (ChangeRequests) is next | R-1 to R-19 are all ticked, and R-18's duplicate row in § J with them. |

---

### 2026-08-22 — ChangeRequests re-verification pass (F, analysis only — no code changed)

Before starting F, the CR rows were re-read against the working tree rather than trusted from the
2026-08-21 sweep. That turned out to be worth doing: the module moved between the sweep and now, and
four rows describe a system that no longer exists in the shape the row assumes.

**What changed under the review.** `docs/adrs/editing-lifecycle-and-concurrency.md` was recorded
2026-08-20 and corrected 2026-08-21 — the same day as the sweep — and the work it specifies has landed
on `feature/change-requests` (`3d50def8` "implemented ground work" through `380ddf06` "added
checkout"). The ADR **supersedes** the CR-first checkout model, which is what every `ChangeRequests`
spec file still describes. So most of §F is not code drifting away from spec; it is spec that was
overtaken by a decision and never rewritten. §F.0 now records the three-aggregate model the rows sit
on, because several of them are unreadable without it.

**Re-scoped, not re-found:**

| Row | Was | Now |
|---|---|---|
| CR-1 | "Three undocumented public routes exist" | The routes are the design. The spec is the stale half — rewrite, don't remove |
| CR-4 | "No validator, max length wrong" | A **poison pill**. Verified: no `AbstractValidator` in the module, `AddComment` never validates, `Apply` throws on the persisted event. Promoted to the fix-first list as rank 8 |
| CR-6 | "Returns `ownerId`, plus six undocumented fields" | The six are the ADR's governance fields. Only `ownerId` vs `createdById` survives |
| CR-11 | "Status filtering is impossible" | `Status` *is* projected now. The gap is the index and the query record, not the data |
| CR-12 | "No handler check" | Aggregate now gates `IsOpen` before participation; opener is always a participant. Reduces to "the `Forbidden` carries no code" — folded into CR-2 |
| CR-13 | "Five reviewer codes unreachable" | Inverted: reviewers correctly live on `MediaItem.ReviewSession`, so the codes should be **deleted** from the catalog |

**Four new rows — CR-14 to CR-17.** The one that matters is **CR-14**: the read-endpoint base class
drops `errorCode` on the floor before the response configurator ever runs, so it is *not* covered by
X-10.3 and moving `ErrorCodeResponseConfigurator` into `QueryApi` will not fix it. CR-15 (nothing ever
closes the comment-thread CR) and CR-16 (no wire discriminator between a governance CR and a
comment-thread CR) are both design questions the ADR left open rather than defects against it.

**Verified by direct inspection, not inferred:** the `NonEmptyString.Create(...).Value` throw path in
both `Apply(ReviewCommentAdded)` and `FromSnapshot`; the absence of any `AbstractValidator` in
`src/modules/ChangeRequests/`; the `AddError` asymmetry between the two `ChangeRequestsEndpoint` base
classes; `ChangeRequestByOwnerIndexSchema.GetSortKeyCondition => null`; both `Guid.NewGuid()` sites on
`EditSessionId`/`ReviewSessionId` (X-9.1, still open); the `SagaOrchestrator.csproj` references to a
saga the ADR says was never built.

**Not yet decided, and blocking step 1 of §F.3:** CR-10 asks whether comment bodies belong in aggregate
state. CR-4's cap depends on the answer — 255 is safe and wrong, 4,000 matches the spec and multiplies
`ChangeRequestSnapshot` by roughly sixteen. Settle CR-10 first or fix CR-4 with the current cap and
revisit.

### 2026-08-23 — ChangeRequests, CR-4 + CR-10 (F.3 step 1)

Started as "CR-4 alone" per §F.3. It did not stay alone, and the reason is worth recording.

**The cap question had no good answer on its own.** F.3 flagged CR-4 as gated on CR-10 only for the
choice of cap, and that gate turned out to be the whole finding. 255 is safe and contradicts both the
spec and the endpoint's own advertised 400. 4,000 matches the spec and puts up to 4 KB of user text per
comment inside one DynamoDB item — and inside every snapshot of it — against a 400 KB limit, which is
exactly the risk the spec's "bodies never in aggregate state" design existed to avoid. Choosing either
one meant knowingly accepting a defect. So CR-10 went first.

**What decided CR-10: `ReviewCommentEdited.OldBody` had no readers.** Not a projector, not a handler,
not a test — nothing anywhere in the repo read it. The spec's entire `ICommentReadModel` interface
existed to populate that one field, and the only two ways to source it were to keep every body in
aggregate state (the 400 KB problem) or to read the eventually-consistent comment projection from
inside a command handler (a lagging read on the write path). Both were being paid for a field with no
reader. Dropping the field made the choice easy.

**Shape now:**

| Type | Change |
|---|---|
| `ReviewComment` → `CommentIndex` | `(CommentId, AuthorId, IsDeleted)`. Exactly what the guards read; the spec's State table already said this |
| `ReviewCommentSnapshot` | Same three fields — `Body`, `ParentCommentId`, `OccurredAt`, `EditedAt` dropped |
| `ReviewCommentEdited` | `OldBody` dropped. Discriminator stays `@1` — removing a record property is backward-compatible under this serializer |
| `NonEmptyString` → `CommentBody` | Spec's VO name and rules: non-empty, ≤ 4,000, control-char regex. Deleted `NonEmptyString`; it was used for nothing else |
| `AddComment` / `EditComment` | Validate before `Emit`, return `InvalidCommentBody` (400), emit the **trimmed** body |
| `Apply` / `FromSnapshot` | Construct no body VO at all |

**The poison pill was removed by construction, not patched.** Chase's call on the replay question was
"rehydrate verbatim, never validate history" — a `FromHistory` escape hatch on the value object. Once
CR-10 landed, that escape hatch had nothing to do: `Apply(ReviewCommentAdded)` records an id, an author
and a flag, and never touches the text, so there is no path on which stored history can be rejected.
The principle still holds and is written into the spec's Design Notes; it just needed no code. Worth
noting that raising the cap alone would *not* have recovered every stranded stream — an empty body
failed `NonEmptyString` exactly as hard as an over-length one, and streams carrying one are recovered
by this change too.

`Apply(ReviewCommentEdited)` is now deliberately empty: an edit changes only the body, and the body is
not state. It stays registered so replay still advances `AggregateVersion`.

**Also landed:** `InvalidCommentBody` (400) added to the error catalog — the spec's invariant table
named it, the catalog never listed it, and nothing raised it. `AddCommentEndpoint` and
`EditCommentEndpoint` have advertised that 400 to clients all along.

**Docs in the same change,** per the repo's co-location rule: `mediachangerequest.write-model.md`
(methods, events, commands, handler pre-conditions, Design Notes, the `ICommentReadModel` section
deleted, the `media-change-request-comments` reference model re-pointed at its actual readers),
`error-catalog.md`, and a `breaking-changes.md` entry covering both shrunken persisted shapes.

**Not built or run — no .NET SDK in this environment.** Compile risk was checked by hand instead: every
call site of the three comment methods is unchanged in signature, and a repo-wide sweep for
`NonEmptyString`, `ReviewComment`, `OldBody` and `ReviewCommentSnapshot(` is clean outside the files
edited. Two existing tests constructed `ReviewCommentEdited` with `OldBody` and were updated.
`dotnet build` + `dotnet test` on `ChangeRequests.WriteModel.Tests` and `.ReadModel.Tests` still needs
to be run locally before this is trusted.

**New test file:** `ChangeRequestCommentBodyTests.cs` — the cap at and over the boundary, empty and
control-character bodies, LF/CR/TAB accepted, trimming, edit rejection emitting nothing, and three
replay tests that are the actual CR-4 regression: an over-length historical body rehydrates, an empty
one rehydrates, and the recovered aggregate's guards still work. Plus one back-compat test that
deserializes a **legacy snapshot JSON document** carrying the four dropped properties, rather than
constructing the current record and proving a tautology.

**Verification pass — three things it caught, all fixed:**

- The regex rejects C0 and DEL, per the spec's published pattern; the doc comment and the catalog entry
  both claimed C1 as well. Wording narrowed rather than the regex widened — the pattern is contract, and
  broadening it would refuse bodies the contract calls valid.
- The remark on the now-empty `Apply(ReviewCommentEdited)` justified keeping the registration by
  version advancement. Wrong reason — `LoadFromHistory` takes the version off the event, not the
  handler. What actually makes it mandatory is that `ApplyEvent` throws for an unregistered type, so
  deleting the line would strand every stream containing an edit: CR-4 again by another route. Corrected
  in place, since the comment exists precisely to stop someone deleting it.
- The trimming change is invisible in the response *shape* but visible in the response *text*. Called
  out explicitly in the breaking-changes entry rather than left under "no API changes".

**Not touched, still open in F:** CR-11, CR-6 (step 2), the error-code pass (step 3), read-side
contracts (step 4), the spec rewrite (step 5). CR-3's `"[deleted]"` question is unaffected by this
change — the body is still in the event and still in the projection, which is where CR-3 has to deal
with it.

### 2026-08-23 — ChangeRequests, CR-6 + CR-11 (F.3 step 2)

Two rows the review called "one design decision each, cheap once decided". One of them was.

**CR-6 was cheap.** `OwnerId` is the name on every aggregate, read model, response and integration
event in the other six modules; `ChangeRequest.CreatedById` was the sole outlier while its own read
models and wire already said `OwnerId`. Renamed the aggregate property and both commands — all
internal, no persisted or published contract touched, and both command construction sites are
positional so nothing broke. The spec's `createdById` became `ownerId`.

Three contracts deliberately keep the old names, and the aggregate now documents why:
`ChangeRequestCreated.InitiatedBy` and `ChangeRequestSnapshot.InitiatedBy` are stored JSON property
names, `ChangeRequestCreatedIntegrationEvent.CreatedById` is a published wire contract. Renaming any
of them buys consistency in exchange for a shim or a consumer break. Recorded as known residue in the
write-model spec's Design Notes rather than left for someone to rediscover.

**CR-11 was not cheap, because the spec's design turned out to be unimplementable as written.**

The spec asked for `OwnerStatusIndex (OwnerId + Status + CreatedAt)`. Two things came out of trying to
build it:

1. **A composite `{Status}#{CreatedAt}` sort key is worse than it looks.** It buys a `begins_with`
   status filter, but it orders an unfiltered listing by status *name* before date — Abandoned, then
   Open, then Resolved — so "my most recent change requests" becomes unanswerable. That is the common
   case, and it collides directly with CR-5's `sortBy`/`sortOrder` in step 4.
2. **The platform cannot filter an index query at all.** `DynamoDbProjectionStore.QueryIndexAsync`
   builds a `QueryRequest` from the partition key and the optional sort-key condition, sets no
   `FilterExpression`, and never calls the query's `Matches` predicate. `Matches` runs only against
   `InMemoryProjectionStore`. So every `Matches` in this repo is dead in production — harmless today
   only because each one restates what the partition key already guarantees. Written up as **N.2.4**;
   it is the first platform gap on that list with no local workaround.

So the sort key is `{CreatedAt:O}#{Id}` — the `RegistrationByOwnerIndex` arrangement exactly — and
status filtering is deferred to the platform rather than faked. The spec row is re-scoped, not ticked
as built.

**Beyond the findings: `ChangeRequestByMediaItemIndex` got the same sort key.** Not a CR-11 row, but
the identical defect on the same table, and its Registration sibling has had the sort key since it was
written. A GSI key schema cannot be altered in place, so fixing it later would mean a second
`schemaVersion` bump and a second full-history replay of the same table. One rebuild instead of two.

**This is the repo's first `schemaVersion` bump, and it has a deploy hazard.**
`media-change-requests` goes to v2. `ProjectionTableNameResolver` falls through to the *deployed*
version when a table has no rotation metadata row — and this table has never been rotated — so the
instant the bump deploys, reads and writes both point at an empty `-v2` and
`GET /v1/change-requests` returns empty pages. Empty, not an error, which is worse: a client cannot
tell it from "you have no change requests". Added as **row 10** of the §N.1 backlog with that caveat,
and written into `breaking-changes.md` with the deploy ordering. Unlike rows 1–9, this row's replay is
not a correction — it is what makes the table usable at all, which is why it is the one row that
cannot wait for the backlog session unless the deploy waits too.

**The bump also exposed that the rollback mechanism had never worked, and fixing it was the larger
half of this pass.** `ReadModelTables` takes a `retainedPreviousVersions` prop whose whole documented
purpose is keeping the outgoing table alive during a rotation. It had never been passed — this is the
first bump, so the path had never run — and passing it would not have helped: `createTable(table,
version)` built *every* version from the current manifest entry, so retaining v1 meant asking DynamoDB
to add sort keys to the live v1 GSIs. Left alone, the deploy would have deleted the live v1 table
(`removalPolicy` is `DESTROY` outside prod) leaving an empty v2 and PITR as the only recovery.

The fix is three pieces, and it is reusable — **every one of the §N.1 rotations needs it**:

| Where | Change |
|---|---|
| `ProjectionManifest` | Optional `previousVersions` per table. The committed manifest is now an **input** as well as an output: the generator carries existing history forward and records the outgoing shape when it detects a bump — the only moment that shape still exists anywhere. Idempotent, so the drift gate stays stable |
| `read-models.ts` | `createTable` resolves a version's shape from the history rather than the current entry, and throws with a pointed message if a retained version has no record |
| `magiq-media-stack.ts` | Actually passes `retainedPreviousVersions: { 'media-change-requests': [1] }` |

The manifest generator cannot reflect history out of code — nothing running declares a shape it has
stopped using — so the operational consequence is worth repeating where people will trip on it: **run
the generator on the commit that performs the bump.** That is the only moment the outgoing shape is
still in the file. It is written into the tool's README.

**Files:** the two index schemas, the `schemaVersion` in `ChangeRequests.ReadModel.Infrastructure`,
`projection-tables.manifest.json` in **both** repos (byte-identical, CI drift gate), the aggregate and
two commands for CR-6, `ProjectionManifest` (`TableEntry`, new `PreviousVersionEntry`,
`ManifestGenerator`, `Program`, README) and its drift-gate test, `read-models.ts` and
`magiq-media-stack.ts` in `cdk-magiq-media`, `mediachangerequest.read-model.md` (GSI section + the
by-owner query row), `mediachangerequest.write-model.md` (state, methods, events, commands, a naming
Design Note), `mediachangerequest.api.md`, `breaking-changes.md`, and §N.1/§N.2 here.

**Build status.** The CDK side **was** type-checked — `tsc --noEmit` passes, and the version-shape
lookup was exercised against the real manifest in node (v1 resolves to the PK-only GSIs, v2 to the
sort-keyed ones). `jest` could not run: `ts-jest` is missing from the installed `node_modules`.

The .NET side is **still unbuilt** — no SDK in this environment, same as the CR-4 pass. Needs locally:
`dotnet build`, `dotnet test`, and `dotnet run --project src/tools/ProjectionManifest` to confirm the
generator reproduces the hand-edited manifest. Note the drift gate compares *semantically*, not
byte-for-byte (`ManifestDriftCheck` parses both sides to a `JsonNode` DOM), so formatting differences
cannot fail it — but the `previousVersions` data must match, and that is new code.

Worth knowing while you are in there: the committed manifest has **never** matched generator output
byte-for-byte. The generator writes `WriteIndented = true` — every property on its own line — while the
committed file is hand-compacted to one line per entry. Running the generator reformats the whole file.
Harmless, but it makes for a noisy diff that has nothing to do with this change.

**Deliberately not touched:** the rest of `mediachangerequest.read-model.md` is still the superseded
CR-first model — `Binding`, `Reviewers`, `RejectionReason`, a `media-change-request-detail` table that
does not exist. That is CR-9's rewrite in step 5, and editing around it now would only make the
eventual rewrite harder to review.

### 2026-08-23 — ChangeRequests, CR-2 + CR-12 + CR-13 + CR-14 (F.3 step 3)

The error-code pass, fourth of its kind after Catalog, Metadata and Registration, and the first where
the module started from **zero** codes rather than a partial set.

**What was actually wrong.** All three comment guards returned a bare `InvalidOperation` — so "comment
not found", "comment already deleted" and "you are not the author" reached the client as one 422
distinguishable only by its message prose, which is presentation, not contract. `AddComment`'s parent
check merged not-found with deleted into a single 422 where the spec published 404. And
`ChangeRequestNotFound` had been sitting in the codes file with zero call sites while all five handlers
returned an untagged `ResourceNotFound`.

**Shape now.** A `DomainErrors` factory next to the aggregate, matching Registration's, carrying the
module's four-bucket status rule in its own remarks so the next person adding a refusal has to pick a
bucket:

| Bucket | Codes |
|---|---|
| 404 — named, not there | `ChangeRequestNotFound` (handlers), `CommentNotFound` (path id *and* `parentCommentId`) |
| 403 — there, not for you | `NotChangeRequestParticipant`, `NotCommentAuthor` |
| 422 — there, wrong state | `ChangeRequestNotOpen`, `CommentDeleted` |
| 400 — malformed content | `InvalidCommentBody` (from the CR-4 pass) |

**Two decisions worth recording:**

- **One participant code, not two.** `AddComment`'s participation guard and `Resolve`/`Abandon`'s
  `MayClose` refuse for the same reason, and the aggregate says so itself — "whoever may discuss the
  change may close it". The spec's `CommentAuthorNotParticipant` named the caller rather than the rule
  and covered only one of the two sites, so `NotChangeRequestParticipant` replaced it. Nothing was on
  the wire under either name, so this cost nothing.
- **`CommentDeleted` (422) is separate from `CommentNotFound` (404).** The spec's invariant table
  already implied the pair; the code had collapsed them. 404 means the id is not a comment on this
  request; 422 means it is, and it has been withdrawn. Collapsing them tells someone who just deleted
  their own comment that it never existed.

**CR-14 was the quiet one.** The read host's endpoint base class called `AddError(error.ErrorMessage)`
while its write-host twin passed `error.CodeOrNull()`. That drop happens before the response
configurator runs, so every coded error on a read route lost its `errorCode` silently — and moving
`ErrorCodeResponseConfigurator` to `QueryApi` under X-10.3 would **not** have fixed it. One argument,
both overloads, and the reason is now in the XML doc so nobody "simplifies" it back.

**CR-13 was not what it said, and the difference matters.** The finding called for deleting five
reviewer codes from the catalog. Five of the eight do have no raise site anywhere and were deleted. But
two — `NotAssignedReviewer` and `ReviewerNotPending` — describe conditions `MediaItem` genuinely refuses
today, at four sites, as uncoded 422s. Deleting those would have thrown away names for rules the system
enforces. They moved to the *Catalog — MediaItems* table marked ⬜, and tagging the guards is logged as
**CR-18** rather than done here: `MediaItem.cs` belongs to a pass that is closed, and the catalog
published `NotAssignedReviewer` as a **403** against the code's 422 — a question that deserves the same
deliberation MI-6 got, not a drive-by edit.

**Spec:** the write-model invariants table gained HTTP columns and lost `CommentAuthorMismatch`, a code
that never existed; the handler pre-conditions table now says what the handlers actually check
(existence, and only existence — participation and authorship are aggregate invariants and a second
copy in a handler is a copy that can drift); `error-catalog.md § ChangeRequests` was rewritten;
`mediachangerequest.scenarios.md` had its dangling `CommentAuthorMismatch` corrected.

**One stale doc deliberately marked rather than fixed:** `security-scenarios.md § PERM-3` is built
entirely on the superseded CR-first model — an approve route that does not exist, a saga never built, a
`SubmittedBy` field the aggregate lacks — and it cited `ReviewerSelfApproval`, which this pass deleted.
It now carries a stale banner saying the rule is still wanted and the mechanism described is not real.
Deleting it would lose the intent; rewriting it belongs with the step-5 spec rewrite.

**Tests:** `ChangeRequestErrorCodeTests.cs` — thirteen cases, one per coded refusal plus two pinning
guard *order*: closed-beats-not-a-participant, and deleted-beats-authorship. Order is contract too; it
decides which of two true statements the client is told.

**Still not built** — no .NET SDK here, same as the previous two passes.

#### What the verification pass corrected

Five things, and two of them mattered:

- **"Live on both hosts" was wrong, and I wrote it.** `ErrorCodeResponseConfigurator` is registered in
  `Api` and not in `QueryApi` — the catalog's own banner has said so since R-13 — so ChangeRequests is
  live on the *write* host like every other context. Header corrected, and the catalog's "still
  aspirational" list, "Live" list, codes-file list and `_Last updated_` were all brought with it.
- **CR-14's fix is real but changes nothing observable today, and the first draft of its comment
  oversold that.** `SendDomainErrorAsync` on the read base class has **zero call sites** — read
  endpoints fail through `SendQueryErrorAsync`, and `IQueryError` carries no error-code concept at all,
  just a five-value enum. So there are *two* independent reasons a `GET` returns no code, and moving the
  configurator only fixes one of them. The symmetry fix stands (the day a read endpoint does dispatch a
  command-shaped error it must not swallow the code) but the XML doc now says plainly that nothing calls
  it. The catalog gained the second reason next to X-10.3.
- **`mediachangerequest.api.md` had not been touched and now contradicted the split.** It published
  "`404` — not found **or** already deleted" on all three comment routes with a worked example titled
  "parent comment deleted" returning `CommentNotFound` — precisely the collapse this pass separated.
  Rewritten: every route now lists all its outcomes by code, and the deleted cases are 422. Its
  authorization table also still said "owner or assigned reviewer of the linked MediaItem", which has
  not been true since the ADR.
- **`ReviewerAlreadyDecided` was orphaned.** CR-13 moved two reviewer codes to the MediaItems table but
  this third one was deleted outright, while `mediaitem.api.md` and `mediaitem.scenarios.md` still
  publish it. It names the same guard as `ReviewerNotPending`, so it moved too, marked ⬜ and flagged as
  a duplicate name to settle. Folded into **CR-18**.
- **The write-model spec asserted a guard order that only one of three commands follows,** and omitted
  the owner/system-actor bypass in `MayClose` — which `MediaItemApprovedEventHandler` depends on. Both
  corrected; the order disagreement is logged as **CR-19** rather than resolved, because picking an
  order is a decision about what a stranger is allowed to learn.

One finding was considered and rejected: `DomainErrors.cs` sits in `Aggregates/Media/` while
`ChangeRequestErrorCodes.cs` sits in `Errors/`, and the simple name shadows the platform's public
`DomainErrors` for anything in that namespace or below. That is exactly how Registration and Metadata
are laid out, and matching two sibling modules is worth more than avoiding a shadow nothing currently
hits.

### 2026-08-23 — ChangeRequests, CR-3 + CR-5 + CR-7 + CR-8 (F.3 step 4)

The read-side contract pass. It opened with a finding rather than a fix.

**CR-20: the comments endpoint threw on every call.** `ListChangeRequestCommentsHandler` called
`reader.QueryIndexAsync`, which resolves `IProjectionIndexSchema<TProjection, TQuery>` out of DI — and
no schema was ever registered for that pair. The query derived from `TenantScopedIndexQuery` while
being registered with `AddResultQuery`; nothing about it lined up. `GET /change-requests/{id}/comments`
had never worked. There was no point fixing its page size (CR-8) or its `parentCommentId` (CR-7)
without fixing that first.

The fix needed no index. Comments are already stored one-partition-per-thread —
`PK = TENANT#{t}#CHANGE_REQUEST#{crId}`, `SK = COMMENT#{commentId}` — because the projector passes
`changeRequestId` as the projection key's `groupKey`. `IProjectionStore.ListAsync(tenantId, groupKey,
pager)` reads exactly that. **And it answers CR-8's ordering requirement for free**: comment ids are
UUID v7, so ascending sort-key order *is* creation order. Both the query record and the spec now say
so, along with the warning that the guarantee evaporates silently if ids ever stop being v7.

That fix costs one thing worth recording: the handler injects `IProjectionStore<T>` rather than
`IReadModelReader<T>`, which no other handler does and which the reader's own doc comment discourages.
The group-scoped `ListAsync` simply is not on `IReadModelReader`. Logged as **N.2.5** — a four-line
platform change that removes the only reason to reach past the reader.

**I got CR-5 wrong first, and Chase's answer was made on a bad premise.** I reported that descending
order needed a platform change because `DynamoDbProjectionStore` never sets `ScanIndexForward`. It
doesn't — `QueryRequestExtensions.WithPagination` does, from `PagerParameters.Descending`, and the
Registration pass shipped exactly this pattern two days earlier. Corrected before building anything on
it. `ChangeRequestSort` and `ChangeRequestPaging` are now near-copies of `RegistrationSort` and
`RegistrationPaging`, down to the 400-not-fallback rule from CO-3.

`sortBy=resolvedAt` stays unimplemented, and now says so with a reason rather than by omission: it
needs a third GSI keyed on `{ResolvedAt}#{id}`, that index is sparse because open requests have no
`resolvedAt`, and somebody has to decide whether an unresolved request drops out of the ordering or
sorts to one end. That is a design question, not a missing line of code.

**CR-3 turned out to matter more than the row suggested.** The finding reads as a cosmetic projector
gap. It is not: `ListChangeRequestCommentsQuery.Matches` filters `!IsDeleted`, and per N.2.4 `Matches`
never runs against DynamoDB — so deleted comments come back from `GET /comments` with their full text.
The read model is the only place a client can reach a comment's body. Setting a flag and leaving the
text meant "delete" removed nothing.

The projector now writes `Body = "[deleted]"`. `AuthorId` is **kept**, against the spec's original
wording: the thread still shows that someone withdrew a comment and moderation needs to know who;
anonymising the tombstone hides the one fact that makes it actionable. The spec is corrected on that
point rather than the code bent to match it, and both places now say plainly that this is *read-model*
redaction — `ReviewCommentAdded` carries the body and the event stream keeps it forever, so a real
erasure requirement has to be answered there.

**CR-7** was two words: `readModel.ParentCommentId ?? string.Empty` became `readModel.ParentCommentId`,
and the two response records took `string?`. A top-level comment has no parent; `""` is not a way of
saying that.

**CR-8** gave the module its own `ChangeRequestPaging`, third copy of the helper after Catalog's and
Registration's. It carries a second default — 50 for a comment thread, 20 for a change-request list —
because a review thread is usually read whole. The cap is shared at 100. Before this the comments
endpoint had no cap at all: a caller could pull an entire thread in one query by asking for it.

**Tests:** `ChangeRequestSortAndPagingTests` covers the sort contract and the clamp including the
comments default; the comment projector gained two cases pinning that delete withdraws the body and
keeps the author.

**Files:** the comments query, handler and registration; the comment projector and read model; both
comment response contracts; the two list requests and endpoints; new `ChangeRequestSort` and
`ChangeRequestPaging`; `mediachangerequest.api.md` and `mediachangerequest.read-model.md`; §N.2 here.

**Not built or run** — no .NET SDK in this environment.

#### What the verification pass corrected

- **The comments endpoint advertised a `404` it can no longer return.** The new handler is a bare
  partition read with no existence check, so an unknown `changeRequestId` yields `200` and an empty
  list. `ProducesProblem(404)` and its summary were removed and both spec files now say so — matching
  `GET /change-requests?mediaItemId=`, which already documented the same behaviour.
- **`sortOrder` is not carried in the page token, and that is a real client trap.** A `pageToken` is a
  serialised `LastEvaluatedKey`; the direction is re-derived from the query string each request and
  defaults to `desc`. Paging an `asc` listing with a bare token resumes from an ascending cursor while
  walking backwards, re-serving rows. **`ListRegistrations` has the identical flaw** — it is inherited
  from `PagerParameters`, so folding direction into the token belongs in the platform. Documented in
  `ChangeRequestSort`'s remarks and in `mediachangerequest.api.md` for now.
- **A `PageSize = 0` sentinel would have shipped in the OpenAPI schema** advertising a default of zero
  next to summary text saying 50. Replaced with `= ChangeRequestPaging.CommentsDefaultPageSize`, so the
  published default is the real one and the clamp still catches an explicit `0`.
- **Two in-code key descriptions were stale and now contradicted the new ones two files away** — the
  comment read model and projector both still described `SK = {ChangeRequestId}#{CommentId}`. Corrected
  to the actual `PK = TENANT#{t}#CHANGE_REQUEST#{crId}` / `SK = COMMENT#{commentId}`.
- **The two spec files read as a contradiction** — the read-model file said both indexes are "oldest
  first" while the API file published `sortOrder` defaulting to `desc`. Both were true of different
  things; the read-model file now says which is the index order and which is the endpoint default.

**Step 5 is all that remains in F**: CR-1, CR-9, CR-15, CR-16 — the spec rewrite, which the module's
read-model file still badly needs (`Binding`, `Reviewers`, `RejectionReason` and a
`media-change-request-detail` table that does not exist). Four passes of targeted edits have kept it
honest around the edges without touching the middle.

### 2026-08-23 — ChangeRequests, CR-1 + CR-9 + CR-15 + CR-16 + CR-17 (F.3 step 5) — **section F closed**

The spec rewrite, deliberately last so it documents what shipped rather than what was planned.

**CR-9 was the big one, and "rewrite" is the right word.** `context-overview.md` and
`mediachangerequest.read-model.md` were not drifting — they described a *different system*: reviewer
rosters with assign/remove/withdraw, approve/reject resolution events, `CheckoutBound`/
`SubmissionBound` bindings, `ChangeRequestActivatedForReview`, eight integration events where three
exist, a `MediaChangeRequestProjector` where three projectors exist, and a
`media-change-request-detail` table that has never existed under that name. None of it was ever built.
Both files are rewritten from the code; the write-model file's "future increment" banner is gone
because the increment shipped.

**CR-1 was the inverse of what it looked like.** `mediachangerequest.api.md` claimed "there is no
public HTTP endpoint to create them". Under the ADR a client *must* open a governance request before
checking out under one, and three routes have shipped — `POST /change-requests`, `/{id}/resolve`,
`/{id}/abandon` — none of which the page documented at all. They now have full entries.

**CR-16 rides the rebuild, which is why it was worth doing now.** `ReviewSessionId` is projected onto
the summary read model and the endpoint layer derives a `kind` discriminator — `governance` or
`commentThread` — from it. Deriving rather than storing keeps one source of truth, and exposing `kind`
rather than the raw `reviewSessionId` answers the client's real question ("which id can I check out
under?") without putting an internal identifier on the wire. Adding a projected field to a table
already queued for a full rebuild costs nothing; doing it next month would cost a second rotation.

**CR-15 landed half, and the half is the honest one.** Publication now closes both change requests —
the governance container because the change landed, the comment thread because the review is over —
via a trailing nullable `CommentThreadId` on `MediaItemApproved` and its integration event. The two
resolutions are dispatched **independently**: sequencing them would let a governance request closed by
hand leave the thread open, which is the original bug in miniature.

Withdrawal also ends a review, and the plan was to close the thread there too. It cannot be done
cheaply: **`MediaItemWithdrawn` has no integration event at all.** Closing it needs a new published
Catalog contract, a new SNS message type, a new entry in the CDK queue's subscription filter, and a
consumer — real infra work that has no business hiding inside a spec-rewrite pass. Logged as
**CR-21** with that cost stated.

**CR-17** was folded in: `SagaOrchestrator.csproj` carried three ChangeRequests references for "domain
events (MCRApproved, MCRRejected) and commands (CreateMCR)", none of which exist, plus a matching
`AddChangeRequestWriteModel()` call in `Function.cs`. The only saga in that host is
`AssetIngestionSaga`. All four removed.

**Tests:** `ChangeRequestKindTests` pins the discriminator including the three ways "no review session"
can arrive (null, empty, whitespace — the handler writes `string.Empty`, old rows carry null).
`MediaItemApprovedEventHandlerTests` covers both-closed, thread-only, neither, system-actor
attribution, and the independence case above.

**Files:** `context-overview.md` and `mediachangerequest.read-model.md` rewritten;
`mediachangerequest.api.md` and `mediachangerequest.write-model.md` substantially extended;
`MediaItemApproved` and its integration event, the Catalog mapper, both `MediaItem` emit sites, the
ChangeRequests handler; the summary read model and its projector; new `ChangeRequestKind`; both
response contracts; `SagaOrchestrator`; `breaking-changes.md`.

**Not built or run** — no .NET SDK in this environment.

#### What the verification pass corrected

One of these would have failed the build:

- **`ChangeRequestKindTests` could not compile.** `ChangeRequestKind` lives in
  `ChangeRequests.ReadModel.Endpoints`, and the ReadModel test project referenced only `.ReadModel` and
  `.Domain` — Endpoints references ReadModel, not the reverse, so nothing pulled it in. Project
  reference added.
- **The `POST /v1/change-requests` response example was invented.** `OpenChangeRequestResponse` is
  `record(string ChangeRequestId)` — one field, named `changeRequestId`, no `createdAt`. Also worth a
  note in the spec, since every *read* response uses `id`: this one predates ADR-012 and renaming it
  would break clients.
- **"Stream prefix `mcr_`" is fiction**, carried forward from the old write-model header into the
  rewrite. There is no stream-prefix concept — the event store keys on `TENANT#{TenantId}#{AggregateId}`
  and stores the aggregate type as an attribute. Replaced with `media.changerequest` in both files.
- **The comments field table was three-way self-contradictory** — it survived the rewrite unedited and
  still named `MediaChangeRequestId`, `CommentId` and an `EventId` that does not exist, while the C#
  block and the note below it both had the real shape.
- **A stale "no read model field changed" claim** in the CR-11 breaking-changes entry, which CR-16
  falsified the same day by adding `ReviewSessionId`.
- **My own CR-11 code comment was wrong about the platform** — it claimed the store never sets
  `ScanIndexForward`. It does, via `PagerParameters.Descending`. That is the same mistake I made
  verbally in step 4 and it had been sitting in a source file since; corrected at the source.

---

### 2026-08-23 — AssetManagement, AM-9 — **the skipped row was hiding a data-loss path**

AM-9 was filed as "three events have no projector handler" and skipped on instruction on 2026-08-21 as
projector coverage. Both halves of that were true and the conclusion was wrong.

#### What VersionArtifact is actually for

An asset is promoted to `VersionArtifact` when a MediaItem version snapshots it, and the status has
one job: **make the asset undeletable while a published version's row still carries its S3 key.**
`mediaitem.read-model.md:252` leans on it explicitly — it is why retroactive `AssetDeleted` patching
of version rows was removed.

The relationship is **many-to-one and always was**. `ApprovedAssetSnapshotFactory` serialises every
current role asset on every approval, not just the changed ones, so an unchanged asset appears in v1,
v2 and v3 alike. The aggregate modelled it as a single flag on `Status`.

#### AM-29 — the defect that produced

1. **v1 approved.** Promote succeeds. `_preVersionArtifactStatus = Active`, `Status = VersionArtifact`.
2. **v2 approved**, same asset. `Status is not (Active or Archived)` → **`Result.Failure`**. The
   consumer discarded the result, so: no log line, no metric, no event (**AM-31**). The write-side
   reference row `{item}#2` was written anyway — a different projector, driven off the integration
   event.
3. **v3 approved.** Same silence.
4. **`DELETE /items/{id}/versions/1`.** `ReleaseVersionArtifact` **ignored both of its arguments** and
   released unconditionally. `Status = Active`.
5. Asset is now deletable while v2 and v3 rows still point at its storage key. And those rows were
   still *visible*, because `MediaItemVersionPurged` was never registered on the projector bus
   (**AM-30**) — so the purge deleted nothing it was supposed to delete and released what it was
   supposed to protect.

None of it had a single test. `grep` for `PromoteToVersionArtifact|ReleaseVersionArtifact|PurgeVersion`
across `tests/` returned one hit, and that was an error-code setup.

#### The fix: a set, not a counter (Chase)

`Asset` now holds `HashSet<(MediaItemId, VersionNumber)>`. Promote adds a holder and accepts
`VersionArtifact` as an input status; release removes one and restores the pre-promotion status only
when the set empties.

**A set rather than a reference count, deliberately.** There is no inbox or dedup store anywhere in
this repo and SQS is at-least-once, so a redelivered `MediaItemApproved` would inflate a counter and
the asset would never release. Membership is idempotent by construction — which also let both
"already done" paths become silent successes rather than failures, now that the consumer actually
reports failures.

**No migration, with one gap that needs a backfill.** Both events have carried
`(MediaItemId, VersionNumber)` since they were written, so historical streams rebuild the set exactly.
What they cannot rebuild are the promotions the old guard *refused* — those emitted nothing. The data
to repair it exists in `media-item-version-asset-refs`; re-dispatching promote per row is idempotent
under the new aggregate. Written up in `breaking-changes.md`.

#### Why the projection could not have been "just a registration line"

`AssetVersionArtifactReleased` carried no target status. The restored value lived in a `private` field
rebuilt by replay, so no projector, consumer or operator reading the stream could tell what the asset
became. Adding `RestoredStatus` and `StillHeld` to the event was a prerequisite, not a nicety — and
`StillHeld` only exists because of AM-29. The row as originally written was unimplementable.

`RestoredStatus` is **nullable**, which the verification pass forced and which matters:
`default(AssetStatus)` is `Pending`, not `Active`. A non-nullable field defaulted to `Active` would
have projected a live published asset as awaiting upload on any pre-AM-9 payload, if the deserialiser
falls back to `default(T)` rather than honouring the declared parameter default. `null` is the same
value either way. The aggregate still ignores the field on replay and uses its own state, because
`?? Active` is wrong for an asset that was `Archived` before promotion — the read model cannot know
that and the aggregate always does.

#### The decision that had to be made before any of this could ship

Projecting the status **breaks downloads**, because both download handlers read status from the read
model and their allow-list was `{Active, Archived}`. Published-version assets were downloadable purely
by accident — via a stale projection.

Chase's call: **allow**. `VersionArtifact` means "this backs a published version", which is exactly
what people download, and `AssetStatus` had said downloads were issuable for it all along. Both
allow-lists widened, both spec passages corrected. **AM-32** came with it: the rendition endpoint
returned `500` for a non-downloadable asset on an endpoint already advertising `409` — the same
result-variant shape AM-3 gave its sibling, never applied here.

#### Tests

`AssetVersionArtifactHolderTests` — 13 facts. The three that matter: purging one of three versions
leaves the asset `VersionArtifact` **and** undeletable; a second promotion does not overwrite
`_preVersionArtifactStatus` (which would restore the asset *to* `VersionArtifact` and strand it
there); replay reconstructs the holder set from the stream.

`AssetVersionArtifactProjectionTests` — 7 facts over both projectors, including the `StillHeld` branch
in each direction and the `RestoredStatus == null` fallback. The verification pass called that ternary
the riskiest new line on the read side with zero coverage, and it was right.

#### Not built or run

No .NET SDK — eighth pass. Needs `dotnet build`, then `AssetManagement.WriteModel.Tests` and
`AssetManagement.ReadModel.Tests`.

#### What the verification pass caught

The nullable-`RestoredStatus` problem above, which would have shipped. Also that
`RenditionDownloadUrlResult.NotDownloadable` fabricates a `ContentType` and `FileSizeBytes` its
sibling carries for real — the handler returns before the rendition lookup, so it cannot fill them.
Documented on the factory rather than faked.

#### Still open here, and deliberately

`PurgeMediaItemVersion` documents an `actor_type == "System"` / admin precondition in **three** places
and implements it in none: any authenticated tenant user can purge a version and release its assets.
That is edge authorization, which this review excludes by its own scope note on line 11 — it belongs
to the auth plan, and it is now considerably more interesting than when that note was written.

---

### 2026-08-23 — Catalog, CR-18 + CR-21 (F.3 step 6) — **section F is down to CR-19**

The two Catalog-owned leftovers, taken together because both live in `MediaItem`'s review guards and
both turn on the same question: what does it mean for a review to end?

#### CR-18 — two guards, four published names, two decisions

Nothing here was in dispute about *behaviour*: `ApproveReview` and `RejectReview` have always refused
a non-reviewer and a repeat voter. They refused both as **uncoded `InvalidOperation` 422s**, so a
client could tell "you are not on this review" from "you already voted" from "this item is not under
review" only by parsing prose. Meanwhile the specs published four names for the two conditions —
`NotAssignedReviewer`/`ReviewerNotFound` and `ReviewerNotPending`/`ReviewerAlreadyDecided`.

Both questions went to Chase rather than being decided in passing, and both went the way the *less*
authoritative document had them:

- **403 for membership; the code changed, not the catalog.** This is the split `MediaItemCheckedOut`
  already carries — "may you act here?" is a 403, "can this be done at all right now?" is a 422 — and
  `MediaItem` already answers the structurally identical edit-session question with
  `DomainError.Forbidden` three times over. The already-decided guard stays 422: the caller *is* a
  reviewer.
- **`ReviewerAlreadyDecided` over `ReviewerNotPending`**, though the error catalog is the canonical
  registry and had the other name. Neither had ever reached a client, so the choice cost nothing, and
  `ReviewerDecision.Pending` appears on no read model and in no response body — "NotPending" named a
  state the caller cannot observe. `ReviewerNotFound` was retired for the opposite reason: it reads
  like a 404 for what is an authorization refusal.

Four raise sites tagged, both endpoints' `403` summary text now names the rule rather than saying
"does not have permission", and one `reviewerStatus` extension was deleted from an example rather
than added to the X-10.7 backlog — nothing attaches it and the value is unobservable anyway.

#### CR-21 — and the half of it that was not in the finding

The finding was written as "withdrawal strands its comment thread". It is, and the fix is the one the
row predicted: a new `MediaItemWithdrawnIntegrationEvent` (`media.item.withdrawn`), a trailing
nullable `CommentThreadId` on the domain event, a mapper case, publisher and consumer registrations,
and a CDK filter entry.

**But rejection does the same thing, and CR-15 had written down the opposite as a decision.**
`breaking-changes.md` said the thread is deliberately left open on rejection because "rejection
reopens the edit session and the discussion is exactly what is still live". The premise is false:
`PublishMediaItemHandler:85` calls `ChangeRequestId.New()` on **every** submission with reviewers, so
the still-live discussion was live in a thread the next submission would never reference. One
stranded `Open` request per rejection, accumulating across revisions — and rejection is the more
common path of the two. Logged as **CR-22** and fixed in the same pass with Chase's sign-off; the old
entry in `breaking-changes.md` was annotated rather than edited, because what changed is the
reasoning.

So the rule the code now states in three places: **a review ends in exactly three ways and all three
close the thread it was held in; only publication also closes the governance request.** The
governance request spans the reject → revise → resubmit cycle by design — `ReopenEditSession`
restores it — and is deliberately not carried on the rejected or withdrawn events at all, so no
future handler can close it by accident.

`ReviewChangeRequestCloser` was extracted from `MediaItemApprovedEventHandler` — the tolerant-resolve
logic verbatim, including why already-terminal must not fail the message — now that it has three
callers instead of one.

#### CR-23, which is the reason to keep verifying after the change and not only before it

`Catalog.ValueObjects.MemberId` is a `record struct` with **no `ToString()` override**, so the
compiler-generated one renders `MemberId { Value = user-1 }`. `MediaItemDomainEventMapper` used
`.ToString()` for `SubmittedBy` and `ReviewerIds`, and
`MediaItemPublicationRequestedEventHandler:33,40` rehydrates those with `MemberId.From`. Every
auto-raised comment thread was therefore seeded with participant ids matching no actor — so
`AddComment`'s participation guard refused everyone and **nobody could comment on the thread their
own review had just opened.**

`ChangeRequests.ValueObjects.MemberId` has carried exactly this override, with a comment naming
exactly this trap, since its own snapshot round-trip hit it. Catalog's never got one. Fixed at the
root (the override) *and* at the call sites (`.Value`), because the next person writing a mapper will
reach for `.ToString()` again.

It was found by a verification sweep of a change that had nothing to do with it — the sweep asked
"does `e.WithdrawnBy.ToString()` produce what the consumer expects?" about a line **this pass wrote**,
and the answer implicated two lines it did not.

#### Tests

`MediaItemReviewerGuardTests` — six cases pinning both codes, both statuses, that a refused decision
writes no event, and guard *order* (the status guard runs before membership, so a stranger learns the
item is not under review rather than that they are not on a roster). The roster is deliberately two
reviewers: with one, the first approval publishes the item and the second call would trip the status
guard instead of the guard under test — which is how the first draft of these tests was wrong.

`MediaItemReviewThreadCarriageTests` — five cases: reject and withdraw carry the thread, both carry
null when there was none, an unpublish from `Published` carries none, and approve carries the same
one.

`ReviewEndedEventHandlerTests` — six cases across the two new handlers, including that a null thread
is a no-op (which is how every pre-CR-21 event deserialises) and that an already-closed thread does
not throw.

#### Not built or run

No .NET SDK in this environment — seventh pass in a row. Needs locally: `dotnet build`, then
`Catalog.WriteModel.Tests` and `ChangeRequests.WriteModel.Tests`. On the CDK side `tsc --noEmit`.

#### Before this reaches an environment

**The CDK change must deploy, and it is the whole point.** `media.item.rejected` was already published
to SNS but was **not** in the `media-cross-module-events` subscription filter, and `media.item.withdrawn`
is new. Both handlers are registered in `ConsumerRegistrations`, so an app-only deploy leaves the code
live and silently receiving nothing — the same failure shape as CR-20, which is worth saying out loud
twice in one review.

Threads stranded before this change stay `Open`; no replay closes them, because the events that would
carry the id were written without it. They can be resolved by hand if a tenant cares.

---

## Section F — closing state

Twenty-one rows, five passes, one day. **Section F is closed.**

~~**CR-18**~~ and ~~**CR-21**~~ closed 2026-08-23 in a sixth pass; ~~**CR-19**~~ closed 2026-08-24 in a
seventh — see the session log. Nothing is outstanding in F.

CR-19 was the last row and the only one that was a decision rather than a defect. It resolved to
**state before authorization**, which is what `AddComment`, `EditComment` and `DeleteComment` already
did and what every guard pair in `MediaItem` does. Worth recording that the decision was mostly a matter
of *noticing* — the review framed it as an open question about disclosure, and the answer was already
sitting in the module (3 of 5 commands) and in a test written the following day under CR-18.

**Seven findings were added by the passes rather than found by the review** — CR-18 through CR-23 —
and three of those were Highs: CR-20, an endpoint that had never worked; CR-22, the rejection half of
the thread leak, which CR-15 had recorded as a *deliberate decision* and which was simply wrong; and
CR-23, a `ToString()` on a record struct that made every auto-raised comment thread uncommentable.
That is the argument for the re-verification step at the start of each pass — and now also for the
step *after* it, since CR-23 was caught by verification of a change that had nothing to do with it.
The original sweep read the code correctly and still could not see a DI registration that was never
made, a `ToString()` that was never overridden, or a decision whose premise was false.

**Three things the module now depends on that the platform does not provide:** N.2.4 (index queries
cannot filter — `Matches` is dead against DynamoDB), N.2.5 (`IReadModelReader` cannot list one
parent's children), and the cursor/`sortOrder` gap noted in step 4, which `ListRegistrations` shares.
None is a ChangeRequests defect and all three shaped what this module could ship.

**Before any of this reaches an environment:** `media-change-requests` is at `schemaVersion 2` and its
rotation is row 10 of §N.1 — the only row where the deploy itself creates the problem rather than
correcting one. It is also what makes CR-16's `kind` correct for historical rows.

---

### 2026-08-23 — AM-21, `itemId` → `mediaItemId` on `POST /v1/assets/uploads`

**Done (1):** AM-21 — closed in both §B and §J. Reopened from the 2026-08-21 skip.

> ⚠ **Not compiled.** No `dotnet` in the sandbox. Build `AssetManagement.WriteModel.Endpoints` and run
> `AssetManagement.WriteModel.Tests` — that project gained a `ProjectReference` to the Endpoints project,
> which it did not have before (precedent: `Catalog.ReadModel.Tests`, `ChangeRequests.ReadModel.Tests`).

#### The finding was half right

The review framed this as "the spec is self-inconsistent and the code follows the wrong half". Only the
first clause held. `asset.api.md` was inconsistent **with itself in one place** — the request example on
line 77 and the sentence under it. Its error list (`404`/`422`), its upload-guard steps and the entire
rest of the file already said `mediaItemId`, as did the multipart endpoint 130 lines down and the bulk
endpoint added under AM-1. The odd one out was a single JSON example and a single C# property.

So this was never a doc-only fix, which is where §J had it filed. `itemId` is **live on the wire** —
whatever the docs say, a client that has been sending `itemId` since this endpoint shipped is sending it
today.

#### Resolved additively, because a rename is breaking by the platform's own rule

`api-conventions.md § Compatibility Policy` lists "rename a field" as breaking and requiring a new major
version. Correcting the spelling by renaming the property would have broken every existing caller to fix
a naming inconsistency — a bad trade, and one the conventions document forbids in the same file that
mandates the spelling.

| | Behaviour |
|---|---|
| `mediaItemId` only | Canonical. Documented, used in every example. |
| `itemId` only | Accepted, identical behaviour. `[Obsolete]`, so it renders as deprecated in the OpenAPI document. |
| Both, same value | Accepted — this is what a client mid-migration sends. |
| Both, different values | **`400`.** The server will not guess which media item the asset belongs to. |
| Neither | Standalone (drag-and-drop) upload, unchanged. |

The conflict case is the one real decision here (Chase, 2026-08-23). Silent precedence was the
alternative: `mediaItemId` wins, legacy value ignored, request succeeds. Rejected — the failure it
produces is an asset attached to the wrong media item, with a `201` telling the caller everything worked.
A `400` naming both fields is a bug the client can see and fix in one sitting.

Resolution lives on the request record (`TryResolveMediaItemId`), not in the endpoint, so the precedence
rule is testable without a host and cannot drift from the two properties it reconciles. Both setters trim
before comparison, so a padded alias does not read as a conflict.

| File | Change |
|---|---|
| `InitiateAssetUploadRequest.cs` | Added `MediaItemId`; `ItemId` kept, `[Obsolete]`, XML-documented as an alias with its removal version. `TryResolveMediaItemId(out string?)` added. |
| `InitiateAssetUploadEndpoint.cs` | Resolves before doing any work; `400` with a message naming both fields on conflict. Swagger documents both, the alias as deprecated. |
| `InitiateAssetUploadRequestTests.cs` | New — 6 tests: canonical only, alias only, both-equal, both-equal-with-whitespace, both-differing, neither. |
| `AssetManagement.WriteModel.Tests.csproj` | Added the Endpoints `ProjectReference`. |
| `asset.api.md` | Example and prose now `mediaItemId`; a note documents the alias, its `400`, and its removal at v2; the `400` bullet lists the conflict. |
| `api-conventions.md` | § Filtering now states the rule covers request bodies, and that path params like `{itemId}` are unaffected — an own-identifier in its own route, not a foreign reference. New **Deprecated Fields Within v1** table under Current Version Status. |

`WarningsNotAsErrors` already carries `612,618`, so `[Obsolete]` does not break the build. Tests
`#pragma`-suppress at each use rather than file-wide, so a genuinely unintended use still warns.

#### Beyond the finding

- **`POST /v1/items/bulk/metadata` takes `itemIds` in its body** (`BulkSetMetadataRequest.cs:10`,
  `mediaitem.api.md:1024`). Spec and code agree, so it is not drift and not AM-21 — but it is the same
  convention violation on a different endpoint, and closing AM-21 leaves it as the last one. Needs its
  own row and the same alias treatment; not touched here.
- **`UnassignAssetFromRoleResponse` exposes `itemId`** on a *response*, where ADR rule 2 asks for
  `mediaItemId`. Response-field renames are equally breaking; same follow-up.
- **`AssetFlowTests` still asserts `HttpStatusCode.Accepted`** on this endpoint, which has returned `201`
  since AM-13 landed on 2026-08-21. Seven call sites in that file. Either the integration suite is not
  running in CI or it is running red — worth knowing which before trusting it as a gate.
- The endpoint's class-level XML comment still says "Response: 202 Accepted", also stale from AM-13. Left
  alone to keep this diff to one finding.

---

### 2026-08-23 — AM-14 reopened: the 409/422 rule, and AssetManagement error codes

**Done (1):** AM-14b. AM-14 itself was already ☑ from 2026-08-21 — this pass finishes what that one
could not, because the thing it fixed was invisible.

> ⚠ **Not compiled.** No `dotnet` in the sandbox. Build `AssetManagement.Domain`,
> `AssetManagement.WriteModel`, both `.Endpoints` projects, and run `AssetManagement.WriteModel.Tests`.
> 24 files changed across the module.

#### What was actually wrong

AM-14 as filed said the catalog wanted `409` and the code returned `422`. That was fixed on 2026-08-21
with a private `Conflict()` helper on `Asset`. Both halves agreed afterwards, which is why it was
ticked. Two things were still true and neither was in the finding:

1. **Neither code could reach a client.** `AssetManagementEndpoint`'s four `SendDomainErrorAsync`
   overloads called `AddError(error.ErrorMessage)` — no code argument — and no raise site in the module
   was tagged. `error-catalog.md` said so itself, listing AssetManagement under "still aspirational".
   So the 2026-08-21 pass corrected a status code attached to a code nobody could branch on.
2. **All three `Conflict()` sites are on worker-only paths.** `RecordValidationResult` is dispatched
   from `ProcessingJobScanResultEventHandler` over SQS; `AttachToMediaItem` and `DetachFromMediaItem`
   have no endpoint at all — the live attach path is `ApplyAssetAssignment`, also SQS, from Catalog's
   `AssetAssignedToRole`. The HTTP surface is 12 endpoints and none of them can produce those statuses.

#### The rule, because there wasn't one

AM-14 moved two status guards to `409` on 2026-08-21. MI-6 ruled status guards `422` on 2026-08-22.
Both are in the same catalog, one day apart, pointing opposite ways — not because either was wrong
about its own case, but because nothing said how to tell the cases apart.

> **`409` when the caller can act — change the resource's state, wait for it to change, or re-read a
> stale precondition — and resubmit the *identical* request. `422` when the refusal is terminal for
> that request.**

That is RFC 9110 §15.5.10's own wording ("situations where the user might be able to resolve the
conflict and resubmit the request") read as a test rather than as a description. It is now written into
`api-conventions.md § 409 vs 422` with a worked table, so the next person does not have to re-derive it
from two contradicting precedents.

Under it, **`AssetNotValidating` is `422`** — its own caller action in the catalog reads "duplicate
delivery — idempotent; discard", which is the definition of nothing-to-resolve. **`AssetAlreadyAttached`
keeps `409`** — detach, resubmit the same command. The detach id-mismatch also keeps `409` but for the
second limb: it is the `VersionMismatch` family, a caller precondition gone stale, resolved by
re-reading.

Useful corollary, now in the doc: **a refusal whose remedy is a *different* request — different id,
different endpoint — is `422`, not `409`.** The conflict is not resolvable; the request was wrong.

#### What was built

| Area | Change |
|---|---|
| Plumbing | `AssetManagement.Domain/Errors/DomainErrorCodes.cs` (`WithCode`/`CodeOrNull`) and `AssetErrorCodes.cs` (21 constants), mirroring Catalog. Fourth copy of the same extension pair — all four die when § N.2.2 lands in the platform |
| Base classes | All four `AssetManagementEndpoint` variants now `AddError(error.ErrorMessage, error.CodeOrNull())`. This is the line that makes every code below reach the wire |
| Aggregate | 14 raise sites tagged; `RecordValidationResult` moved 409 → 422 |
| Handlers | 16 `ResourceNotFound("Asset not found")` sites → `AssetNotFound`; the initiate/confirm/multipart/delete/ownership guards tagged with their published codes |
| Read side | The two download `409`s tagged, though `QueryApi` does not serialise codes yet (X-10.3) — tagging now means they go live with that fix rather than needing a second pass |
| Tests | `AssetErrorCodeTests` — 10 tests over the reclassified status, each new delete code, and `WithCode`/`CodeOrNull` semantics |

#### Three new codes, and why inventing them was justified here

`DELETE /v1/assets/{assetId}` is a live endpoint whose four refusals were **one indistinguishable
`422` carrying `errorCode: "InvalidOperation"`**. A client could not tell "purge the owning version"
from "unassign the role" from "wait for ingestion" without parsing the message. So:
`AssetIsVersionArtifact`, `AssetAssignedToMediaItem`, `AssetIsProfileDefault`, plus `AssetNotDeletable`
for the residual status refusal, and `AssetAlreadyDeleted` given a raise site of its own (it was
published but folded into the generic status check).

This is the opposite call to C-5's on MediaProfile, deliberately. There, ~15 codes would have been
invented for conditions no client had asked to distinguish. Here the endpoint is live, the refusals
demand different client behaviour, and adding codes to an unchanged status is additive.

**Not tagged, deliberately:** every refusal reachable only from a saga or SQS consumer —
`CompleteProcessing`, `FailProcessing`, `PromoteToVersionArtifact`, `ReleaseVersionArtifact`,
`RequestReprocessing`, the attach status guard, both detach guards. A code there is published contract
nobody can receive. They get one when an endpoint does.

#### Two wire changes, called out because they are wire changes

Both bulk endpoints carried their per-item codes as **string literals**, and two contradicted the
catalog they were supposed to implement:

| Endpoint | Was | Now | Why |
|---|---|---|---|
| `uploads/bulk` | `ResourceNotFound` | `MediaItemNotFound` | The catalog's name for a missing media item |
| `uploads/bulk` | `FileSizeExceeded` | `AssetTooLarge` | `FileSizeExceeded` is the *actual* size at confirm; a declared size checked against a known bound is `AssetTooLarge` (AM-27) |
| `bulk-confirm` | `ResourceNotFound` | `AssetNotFound` | Same, for a missing asset |

Taken on the grounds that the old values were never published contract — they appear in no version of
`error-catalog.md`. All four now come from constants, which is what stops this recurring.

#### The two ⬜ rows — both closed the same day

They were left ⬜ in the first pass and picked up immediately after. Neither turned out to be the
paperwork exercise it looked like.

**`MultipartCompleteRejected` — a real defect, not a missing tag.** `IMultipartUploadService.CompleteAsync`
let `AmazonS3Exception` propagate, so a client that sent a mismatched ETag or an undersized part was
told its own mistake was a **`500`** — and, because 5xx means "try again, it's us", told to retry a
request that could never succeed. Now:

- `CompleteAsync` returns a `MultipartCompletionResult` (`Completed` / `Rejected(reason)`).
- Infrastructure translates a **fixed allow-list** of five S3 error codes — `InvalidPart`,
  `InvalidPartOrder`, `EntityTooSmall`, `NoSuchUpload`, `MalformedXML` — into a rejection. Everything
  else still throws and still becomes a `500`. Allow-list, so a new S3 error is never silently
  reclassified as the caller's fault.
- The translation is in infrastructure, not the handler, so `AmazonS3Exception` stays out of the
  application layer — the `IAssetRepository.TrySaveNewAsync` precedent from AM-1.
- The handler returns before touching the aggregate, so a refused completion leaves the asset `Pending`
  and the caller can re-upload the bad part and retry. Same ordering lesson as AM-6.
- Three handler tests, including one asserting `SaveAsync` is never called on the rejection path.

**`AssetNotArchived` — not a stale row, a guard that was specced and never built.** The row was the
last trace of a **two-step archive-then-delete policy**: `asset.scenarios.md:505` stated "hard delete
is only permitted on `Archived` assets… the two-step pattern prevents accidental permanent deletion"
as an invariant, and the route table described `DELETE` as "hard-delete an archived asset". `Asset.Delete`
has always accepted `Active`, `Archived`, `ValidationFailed` and `ProcessingFailed`. So this was a
genuine spec-vs-code divergence with a compliance-flavoured rationale behind it, sitting unnoticed
under a row that read like dead contract.

**Resolved in the code's favour (Chase, 2026-08-23.)** Deletion is owner-scoped and already refuses
assigned assets, version artifacts and profile defaults, so the accident-prevention argument was not
worth a breaking change on a live endpoint to enforce a rule nothing has relied on. `AssetNotArchived`
is retired from the catalog; the scenarios file's invariant list, its domain-flow steps, its error
example and the route description were all rewritten to the real four-status rule. The scenarios file
also gained the two facts the guard-order bug turned up: `AssetDeleted` does not clear
`MediaItemId`/`RoleName`, and a failed asset can still be assigned.

> Worth noting for the remaining modules: **a ⬜ row is worth opening, not just annotating.** Both of
> these looked like documentation cleanup from the outside. One was a live `500` on a client error, the
> other a policy the spec asserted and the code had never implemented.

#### The verification pass on *these two*, which found four more things

| Finding | Resolution |
|---|---|
| **`NoSuchUpload` had the wrong caller action.** It was in the same allow-list as the part faults, so it inherited `MultipartCompleteRejected`'s advice — "re-upload the parts and complete again". That can never succeed once the session is gone: the parts have nowhere to go. A client following the documented action would loop on a `422` forever, with the asset stranded `Pending`. | Split into its own code, **`MultipartUploadNotFound`**, with its own action: do not retry, initiate a new multipart upload. `MultipartCompletionResult` grew a three-value `Outcome` instead of a bool. Fourth test added. |
| **`ex.Message` was going back to the client verbatim.** AWS exception text is not a stable contract and can carry bucket, key and request context. | Only S3's `ErrorCode` reaches the wire now, inside a fixed sentence. The full exception is logged — `MultipartUploadService` took an `ILogger<T>`, which it did not have. |
| **A dead knob in the integration fixture.** `TestMultipartUploadService.RejectCompletionWithReason` had no caller, because every multipart integration test in `AssetFlowTests` is commented out. | Removed. The rejection branches are covered by the unit tests; an unused public setter is the kind of thing these passes keep finding. |
| **X-10.4 — every error example in the spec is in a shape nothing emits.** See below. This is the big one and it is not an AM-14 finding. | Authoritative shape documented in `error-catalog.md`; the examples this pass touched corrected; the rest filed. |

#### X-10.4 — the documented error shape is fiction, platform-wide

Chasing whether S3's error code really reached `detail` turned up something wider. The actual response
for a domain refusal on a write endpoint goes `SendDomainErrorAsync` → `AddError(message, code)` →
`ErrorCodeResponseConfigurator` → `DefaultProblemDetailsFactory.CreateValidationProblem`, which
produces:

```json
{
  "type": "https://httpstatuses.com/422",
  "title": "Validation failed",
  "status": 422,
  "errors": { "GeneralErrors": ["<the message>"] },
  "errorCode": "AssetNotDeletable"
}
```

Against that, **every error example in every per-aggregate API spec is wrong in four ways at once**:

| Spec examples say | Reality |
|---|---|
| `"type": "https://errors.magiqmedia.com/domain/<code>"` | `https://httpstatuses.com/{status}` — nothing emits the magiqmedia URIs |
| `"title": "Asset is not archived"` (specific) | Always the literal `"Validation failed"` |
| `"detail": "<the message>"` | **Never populated.** The message is in `errors.GeneralErrors[0]` |
| `"extensions": { "errorCode": … }` | `errorCode` is at the **root** — `Extensions` is `[JsonExtensionData]`, so it serialises inline |

These examples predate any response carrying a code at all and have never been checked against a real
one. A client written from them fails on all four fields. Note this also means the C-5, M-14, R-13 and
CR-2 passes each certified `errorCode` as "live" without ever confirming where in the body it lands —
it does arrive, just not where every example says.

**X-10.4 — closed 2026-08-23, in the spec's favour.** The choice was to rewrite 78 examples down to the
code's shape, or to lift the code to the shape the specs had been describing all along. **The specs were
the better design** (Chase, 2026-08-23) — an RFC 9457 body with a per-type `type` URI, a real `title` and
a populated `detail` is what the standard asks for, and "every 404 titled *Validation failed*" is not
something to enshrine. So the code moved.

**Except on one point, where the code was right and all 78 examples were wrong:** extension members are
**root-level**. `ProblemDetails.Extensions` is `[JsonExtensionData]`, and RFC 9457 § 3.2 has no nested
`extensions` object. Every example showing one has been corrected.

| | Before | Now |
|---|---|---|
| `type` | `https://httpstatuses.com/422` | `https://errors.magiqmedia.com/domain/asset-not-deletable` — derived from the code |
| `title` | `"Validation failed"`, always | `"Asset not deletable"` — derived from the code, stable per type (RFC 9457 § 3.1.3) |
| `detail` | never populated | the occurrence message |
| `errorCode` | root (correct) | root, unchanged |
| `WithMetadata` members | **all dropped** | copied to the root — `currentStatus`, `requestedBytes`, `renditionType` … |
| `errors.GeneralErrors` | the only channel | kept, duplicating `detail` |

**How the error reaches the builder.** `config.Errors.ResponseBuilder` only ever received
`ValidationFailure`s — message and code, nothing else — which is why `title` could not be specific and
`detail` could not exist. The fix is one line in each module base class: after `AddError(...)`, stash the
`IDomainError` on `ValidationFailures[^1].CustomState`. FluentValidation's `CustomState` is an
`object?` that travels with the failure, so there is no ambient state, no `HttpContext.Items` key, and
no new shared project. The builder reads it back with `OfType<IDomainError>()`.

**A failure with no domain error attached is untouched**, so ordinary FastEndpoints request-validation
responses — the field-grouped `errors` dictionary — behave exactly as before. That is what bounds the
blast radius of a change that otherwise touches every error response on the platform.

`WithMetadata` copying was free once the error was in hand, and it closes the second half of § N.2.3 in
this repo. `traceId`, `correlationId` and `timestamp` are reserved: a domain error carrying one of those
keys cannot overwrite the platform's value.

**Scope:** `ErrorCodeResponseConfigurator` rewritten; `ProblemTypeNaming` extracted (the `type`/`title`
derivations are published contract, so they are tested rather than buried in a lambda); 20 base-class
sites across 5 modules; 78 example blocks unnested and 56 of them re-derived so their `type` and `title`
match byte-for-byte what the builder emits; `api-conventions.md § Standard Error Shape` and
`error-catalog.md`'s opening block rewritten. New `tests/hosts/Api.Tests` project — the `Api` host had
none — with 8 naming tests including a slug round-trip over every published AssetManagement code.

**Still the platform's job.** § N.2.3 remains the right end state: an `IProblemDetailsFactory` overload
that takes an `IDomainError`. This is the host-side version so the contract works now; delete it when
the SDK grows one.

### X-10.5 — `recordtype.api.md` was truncated, and invisible to every grep

Found while sweeping the examples: `grep` reported `contexts/Metadata/aggregates/RecordType/recordtype.api.md`
as **a binary file**. It carried 34 NUL bytes, introduced in `8e84c45c` and untouched since.

Two consequences, the second worse than the first:

1. **The file's last table was truncated mid-row** — the *Command → Event → Projection Traceability*
   table ended at `` | `PUT /fields/{name}` | `ReplaceFieldInRecordTypeCommand` | `FieldRep `` and nine
   rows were simply missing. This is not recoverable from history: the file has ended that way since
   `6fc139ee` created it, so it was *born* truncated and the NULs arrived later.
2. **Every grep-based sweep of the spec has silently skipped this file.** Including the Metadata pass of
   this review, and every pass since. Any finding that depended on grepping the spec has a hole in it
   exactly the size of RecordType's API doc.

Fixed: NULs stripped, the nine missing rows reconstructed from `RecordType.cs`'s `Emit` sites and the
route list at the top of the same file, and the reconstruction labelled as such so nobody mistakes it
for original text. Also corrected while in there: `PATCH /v1/record-types/{id}` dispatches **three**
commands (rename, description, display name), and the table listed only the rename.

**A second file had the same problem.** `docs/spec/architecture/domain-model.md` carried **293** NUL
bytes, from the same commit. That one is *not* truncated — its last line matches the pre-corruption
version exactly, so it was only padded — but it was equally invisible to grep, and it was skipped by
the X-10.4 sweep in this very pass until the verification agent caught it. Stripped; a repo-wide scan
of `docs/`, `src/`, `tests/` and `.github/` now finds **zero** NUL-carrying text files.

**Worth a habit change:** a `grep -r` over `docs/` is not proof of absence. `grep -rI` skips binary
files silently by design; `grep -ra` would have read them. Anything that claims "no occurrences in the
spec" from this review predates that knowledge — and two of the spec's own files were in the blind spot
the whole time.

A `.gitattributes` rule marking `docs/**/*.md` as `text` would have caught both at commit time. Worth
adding alongside the § N.3 renormalisation, which is already outstanding and already touches that file.

### X-10.6 — R-13's "read endpoints carry no codes" is not what the wiring does

Found while correcting a comment that repeated it. R-13 reasoned: `ErrorCodeResponseConfigurator` is
registered in `Api` and not in `QueryApi`, therefore no read endpoint carries an `errorCode`. The
premise is right and the conclusion does not follow.

**`src/hosts/Api/Api.csproj` references all five `*.ReadModel.Endpoints` projects** (lines 53, 59, 65,
71, 80) and the host applies no assembly or route filter to FastEndpoints discovery. So `Api` serves
the `GET` routes too — and there, they do carry codes. Only a read route reached through `QueryApi`
loses them.

Which means **both deployables expose the same read routes with different error bodies.** That is the
finding, and it is bigger than the code question: it is a routing and deployment question about which
host a client actually reaches, and whether the duplication is deliberate. Not resolved here.

The claim had been copied into four places — `error-catalog.md`, `asset.api.md`,
`AssetErrorCodes.cs` and two comments I wrote in this pass — all corrected. A separate, *real* limit
survives: an endpoint failing through `IQueryError` has no code to give the builder regardless of host,
so those `404`s stay bare either way.

### X-10.7 — the spec publishes extension fields no raise site attaches

X-10.4 made `WithMetadata` members reach the wire. That surfaced how few there are: the whole repo
attaches **four** keys — `alias`, `candidates`, `capabilityType`, `fieldName`.

The spec's examples show `currentStatus` (10 occurrences), `requestedBytes`, `renditionType`,
`checkedOutBy`, `reviewerStatus`, `retryAfterSeconds`. **None of these is attached anywhere.** The
plumbing now exists; the calls do not, so a client branching on `currentStatus` still gets nothing.

Two ways to close it, and it needs a decision rather than a sweep: attach them at the raise sites (they
are genuinely useful — `currentStatus` on a status refusal saves a round trip), or delete them from the
examples. `registration.api.md:224` already chose deletion for its aggregate while the AssetManagement
examples kept them, so the treatment is currently inconsistent. Flagged in `error-catalog.md`; not
decided.

#### Found by the verification pass, not by the work

A review agent read the whole diff before it was called done. Three things it caught:

- **A live bug in the new `DELETE` guard order.** The `AssetAlreadyDeleted` branch went in *after* the
  assigned-to-media-item check, and it is shadowed on a reachable path. An asset can be attached while
  `Pending`/`Validating`/`Processing`, then fail validation; `AssetDeleted` does not clear `MediaItemId`
  or `RoleName`, so after a successful delete the asset is `Deleted` **and** still `IsAssigned()`. On the
  second delete `isFailedState` is now false (status is `Deleted`, not a failed state), so the assigned
  guard fires and tells the caller to unassign an asset that no longer exists. Already-deleted is now the
  first guard in the method, ahead of everything — an idempotent no-op must never be shadowed by a guard
  that demands action. Regression test added. The aggregate comment claiming failed-state assets "can
  never be assigned" was simply wrong and is corrected: they cannot be *newly attached*, which is a
  different statement.
- **`S3ObjectNotFound` and `FileSizeExceeded` returned `400`, not the `422` the catalog publishes.**
  Both went through the handler's `ValidationFailure(...)` helper, which maps to `400`. Neither is
  request validation — one is a HEAD check against S3, the other measures the uploaded object. Both moved
  to `InvalidOperation`. This was pre-existing drift the review never filed, and the AM-14 pass came
  within one commit of certifying it as verified by putting a ✅ next to both rows.
- **Two files had `System.*` usings sorted last**, against `.editorconfig`'s
  `dotnet_sort_system_directives_first`. Scripted-edit churn; fixed, and the whole module re-checked.

**Left open deliberately:** `S3ObjectNotFound` may belong at `409` under the new rule — the caller can
PUT the file and resubmit the identical confirm. It stays `422` because that is the published value and
the code now matches it. Moving it is a contract decision, not a drift fix.

#### Still open

| Item | State |
|---|---|
| Nothing compiled | Build + test before pushing. `IMultipartUploadService.CompleteAsync` changed signature — the integration fixture's `TestMultipartUploadService` was updated with it; no other implementor exists. |
| `S3ObjectNotFound` at `422` vs `409` | See above — a decision, not a defect. |
| `QueryApi` drops all codes | X-10.3, unchanged by this pass. The two download `409`s are tagged and inert until it lands. |
| Other S3 client-fault codes | The allow-list is four part-fault codes plus `NoSuchUpload` handled separately. If a fifth shows up as a `500` in CloudWatch, it belongs on the list — that is the intended way to extend it. |
| **X-10.4** | **Closed** — the code was lifted to the documented RFC 9457 shape and all 78 examples corrected. See above. Wire change: `type`, `title` and `detail` on every error response across all five live modules. Worth telling whoever consumes them. |
| **X-10.5** | **Closed** — `recordtype.api.md` was truncated and NUL-padded, which made grep treat it as binary and skip it. Rows reconstructed. The habit note matters more than the fix: this review's grep-based findings have a blind spot the size of that file. |
| `Api.Tests` is new | The `Api` host had no test project. One was added and registered in `magiq-media.sln`; CI globs test projects, so it should be picked up — worth confirming on the first run. |
| **X-10.6** | Both `Api` and `QueryApi` serve the same read routes, with different error bodies. A routing/deployment decision, not a code fix. |
| **X-10.7** | Six extension fields published in examples that no raise site attaches. Attach them or delete them — currently inconsistent between contexts. |
| Verification found bugs in this pass | Three rounds of review caught, in my own work: a shadowed delete guard, two wrong test assertions, a corrupted doc value, a code-dropping regression in the response builder, and four false claims in comments. Every one was mechanical to fix and none would have been caught by the build. Worth keeping the review step. |
| Multipart integration tests | All of `AssetFlowTests`' multipart cases are commented out, so the `422` paths have unit coverage only. Worth knowing before trusting that suite as a gate — it also still asserts `202` where AM-13 moved the endpoint to `201`. |
| Processing, DocumentSigning | The last two write-side modules with no `errorCode`. Same one-line base-class change; AssetManagement is now the worked example. |
| Four copies of `WithCode`/`CodeOrNull` | Five, now. § N.2.2 remains the fix. |

### 2026-08-24 — I.4 Tables & infra, X-4.1 + X-4.2 + X-4.3 + X-4.6

Doc-only pass — no code changed. X-4.4 and X-4.5 deliberately skipped; they're queue topology and belong
with the queues work.

#### X-4.1 — the retired bucket had spread further than the finding said

The finding named two files. `media-documents` was actually alive in **eleven**: `bounded-context.md`
(the DocumentSigning integration table still had the signed document being *written* to it),
both AssetManagement and Catalog `context-overview.md`, `mediaprofile.defaults.md` in four places,
`processingjob.scenarios.md` in three including a Mermaid sequence arrow,
`documentsigningsession.scenarios.md`, `Registration/context-overview.md`, and `system-spec.md`.

Every one of them was making the same substantive claim: that a MediaItem whose profile lacks
`Processing` gets its original stored in a *different bucket*. That is the thing S12 removed. Capability
is now a mutable `tier-policy` object tag on one shared bucket, which is why reassigning a profile is a
`PutObjectTagging` call instead of a cross-bucket copy. Each site was rewritten to say tag, not bucket —
not find-and-replaced, since the sentence "stored in `media-documents` (not `media-source`)" doesn't
survive a rename intact.

Left deliberately: the four places that say "`media-documents` was retired" (`domain-model.md:216,446`,
`system-architecture.md:403`, and the ADR). Those are the historical record and are correct as written.

#### X-4.3 — renamed to the identifier the app actually binds

`media-source` appears nowhere outside the spec. The application's config default is `media-originals`
(`S3AssetStorageOptions.OriginalsBucketName`), which CDK overrides at deploy with
`magiq-media-originals-{account}-{region}`. So there were two names in play, spec had a third, and none
of them agreed.

Swept `media-source` → `media-originals` across all 13 files, including the live ADR
`asset-storage-and-processing.md` — leaving that stale would have reintroduced the drift on the next
read, since `system-architecture.md` links to it as the current authority on storage tiering.
Example URLs became `magiq-media-originals.s3.amazonaws.com` (physical form, minus the
account/region suffix, which would make the samples unreadable). `system-spec.md`'s S3 table now carries
logical *and* physical columns plus a short note explaining which one code binds to and why the suffix
exists — the point being that a reader who greps AWS for `media-originals` and finds nothing should be
able to work out why from the spec alone.

`media-renditions` needed no rename: logical name and config default already matched.

#### X-4.2 — writing this one up turned into X-4.7

The finding is "quarantine is provisioned and appears in no spec table," which reads like a one-row
addition. It isn't, and the reason only surfaced because the task was to *explain its usage*.

`asset.scenarios.md` has always described the quarantine flow — infected object moved, not deleted,
forensics preserved, bucket unreachable from app roles. Checking that against the repo before
documenting it:

- `grep -ri quarantine src/` → **nothing**. No code references the bucket.
- In CDK, the Processing Worker gets `buckets.originals.grantRead(...)` and
  `buckets.renditions.grantReadWrite(...)`. **No role in the stack is granted anything on quarantine** —
  not the worker, not anyone.

So the worker can't write to quarantine (no `PutObject`) and can't remove the source object from
originals (no `DeleteObject`, on a read-only grant). The specced move isn't merely unimplemented, it's
unauthorized — the bucket is a correctly-configured, correctly-locked-down, completely unused resource.
An infected upload today sits in `media-originals` next to the clean ones, readable by `Api` and
`QueryApi`, and the only thing that happened is a domain event saying validation failed.

Documented the bucket properly in `system-spec.md` (why a separate bucket rather than a prefix or a
tag — bucket-level IAM is the only boundary that holds when the application roles themselves are what
you're excluding), with a status banner separating specced from deployed. Same banner added at
`asset.scenarios.md` and `Processing/context-overview.md`, so nobody reads the flow and assumes it runs.
Opened as **X-4.7**.

#### X-4.6 — the finding said two tables; it was ten

Rather than eyeball it, the inventory was diffed mechanically: `tableId` out of
`projection-tables.manifest.json`, the `resourceName()` / `projected()` literals out of `write-indexes.ts`,
`platform-tables.ts` and `event-store.ts`, against the spec table's first column. That found:

- **Ten missing**, not two. Beyond `media-folder-locks` and `read-model-metadata`:
  `media-catalog-folder-registration-index`, `media-catalog-item-profile-index`,
  `media-catalog-asset-item-index`, `media-catalog-version-asset-ref`, `media-catalog-record-type-index`,
  `media-asset-profile-default-ref`, `media-processing-asset-index`, `media-profile-version`.
  The pattern is that write-side reference indexes were largely absent — they'd been documented in
  `system-architecture.md` and never backfilled into the canonical list.
- **One under the wrong name** — the spec's `media-catalog-record-type-ref` is
  `media-catalog-record-type-index` in CDK. Its two-partition-strategy layout was undocumented here too.
- **One fictional** — `media-folder-hierarchy` / `FolderHierarchyNodeReadModel`. No CDK resource, no
  manifest entry, and no such type anywhere in `src/`. Row deleted.
- **One with the wrong key** — `media-catalog-folder-items-index` was listed with SK `{MediaItemId}`.
  `FolderMediaItemsIndex.CreateProjectionKey(tenantId, folderId)` keys it on the **folder**; the row holds
  that folder's item ids as a list. `system-architecture.md` had it right. Corrected, with a note, since
  the wrong version is the plausible-looking one.
- **Three not provisioned** — the `media-signing-*` tables, listed with no indication that
  DocumentSigning has no implementation. Marked, consistent with section H.

PK/SK for the added rows were taken from each type's `CreateProjectionKey` and cross-checked against
`system-architecture.md`'s write-index table. `media-folder-locks` earned a call-out: its PK is
`LOCK#{TenantId}#{CollectionId}` — the one table in the system that doesn't lead with `TENANT#`.

The table now has a preamble stating it's authoritative, naming the four CDK files it reconciles against,
and explaining the two suffix rules (`-v{n}` on versioned read models, no environment segment ever) that
make physical names differ from the ids listed. Spec and CDK are now a clean 46-for-46 match.

#### Not fixed, noticed in passing

`asset-storage-and-processing.md:29` claims an S3 bucket policy condition (`s3:content-length-range`) on
the originals bucket as upload-size defence layer 2 of 3. `media-buckets.ts` attaches no bucket policy at
all. Not folded into this pass — it's an upload-validation claim, not a table-or-bucket-inventory one —
but it means the "layered" size enforcement is two layers, both application-side.

#### The verification pass caught three of my own errors

Worth recording, because two of them were the same mistake and it is an easy one to repeat.

**`ProjectionKey`'s 3-argument constructor is `(tenantId, discriminator, groupKey)`** — not
`(tenantId, groupKey, discriminator)`. Discriminator becomes the **SK**; groupKey becomes the **PK**
suffix. Reading `new ProjectionKey<T>(tenantId, mediaProfileId, version)` left-to-right suggests
"partition by profile, sort by version"; it means the opposite. I had written the two MediaProfile
version rows the intuitive way round and both were wrong — and one of them (`media-profile-versions`)
was a row that had been sitting wrong in the spec all along, which I'd copied rather than checked.
Opened as **X-4.8**, because the resulting key shape is a genuine hot-partition risk, not just a doc
error. Every other row I added uses the constructor the same way and verified clean, so the two profile
tables really are the outliers.

**`bucketName()` in the CDK's `config.ts` is dead code.** I cited it as the physical-naming mechanism.
Nothing calls it. Real naming is `bucketNamePrefix` + `bucketNamespace: ACCOUNT_REGIONAL`, where
**CloudFormation** appends the suffix — and it appends `-{account}-{region}-an`, with a trailing `-an`
for the account-regional namespace that the dead helper omits. So the helper is both unused and
incorrect. Rolled into **X-4.9** with two stale CDK comments found the same way.

**`RecordTypeVersionDetailIndex` doesn't exist.** The registered projection type is
`RecordTypeVersionReference`; `RecordTypeVersionDetailIndexProjector` is the projector. I'd carried the
name over from the spec row I was rewriting instead of confirming it. The key shapes in that row were
right.

The lesson for the remaining sections: PK/SK claims can't be lifted from `system-architecture.md` or from
an existing spec row — they have to come from the `CreateProjectionKey` call plus the schema class, read
together, with the constructor's argument order in front of you.

### 2026-08-24 — I.9, X-9.1 — the obvious tidy-up next to it would have broken event replay

Two-line fix, and then a third change that looked equally obvious and would have been a serious mistake.

#### The fix

`EditSessionId.New()` and `ReviewSessionId.New()` called `Guid.NewGuid()`. Both now call
`GuidFactory.CreateVersion7()`, the same platform factory every other ID in the system uses (Medo.Uuid7
today, native `Guid.CreateVersion7()` once the codebase moves to .NET 10). Two files, one line each,
plus a `using Magiq.Platform;`.

No migration needed. Existing v4 session ids stay valid — nothing sorts or range-scans on either type
(`EditSessionId` is a `keyword` in the OpenSearch mapping and a plain string on the read model), so the
mixed old/new population is harmless. That is luck rather than design: had these been aggregate ids,
the same bug would have meant a stream of non-sortable keys sitting in a sort position.

#### The trap: do **not** give these `IEntityId`

Every other ID in Catalog.Domain is declared `readonly record struct XId(Guid Value) : IEntityId`. These
two aren't, and the natural instinct is to "finish the job" and add the interface — the platform's own
XML docs on `IEntityId` even say implementors *should* look exactly like this.

Adding it would corrupt the event store.

`EventSourcingJOptions.Default` — the options the DynamoDB event store serializes with — registers
`EntityIdJsonConverterFactory`, whose `CanConvert` is `t.IsValueType && typeof(IEntityId).IsAssignableFrom(t)`.
So the interface isn't a marker; it's a **serialization switch**. Types that have it persist as a bare
string; types that don't persist as `{"Value":"…"}`. These two IDs are carried on nine already-persisted
domain events — `EditSessionOpened`, `EditSessionClosed`, `EditSessionRenewed`, `EditSessionReopened`,
`MediaItemPublicationRequested`, `MediaItemApproved`, `MediaItemRejected`, `ReviewerApproved`,
`ReviewerRejected`. Adding the interface flips the wire shape for all of them, and every stored event
carrying one fails to deserialize on replay. A checked-out or under-review MediaItem would stop
rehydrating.

Nothing in either file recorded this. Both now carry a remarks block saying the omission is deliberate
and why, because the next person to notice the inconsistency will reach for the same fix.

Worth knowing generally: **`IEntityId` cannot be added to an ID type that already appears in persisted
events without migrating the streams first.** That applies beyond these two.

#### The guard

`CLAUDE.md` has said "never raw `Guid`" since the beginning and it didn't stop this — a convention only
binds the people who read it before writing the code. Added `IdVersionCoverageTests`, modelled on the
existing `CheckoutEnforcementCoverageTests` (same idea: make the rule structural rather than remembered).

It reflects over Catalog.Domain for value types named `*Id` with a public static parameterless `New()`
and a `Guid Value`, calls each factory, and asserts the generated value is v7 — so it covers ID types
that don't exist yet, and can't be fooled by a helper wrapping `Guid.NewGuid()` under a friendlier name.
The scan is shape-based rather than `IEntityId`-based *because* of the trap above: an interface-based
scan would have skipped precisely the two types that were broken. A second fact checks two ids generated
2ms apart actually sort in creation order, since the version nibble alone doesn't prove monotonicity —
which is the property the convention exists for. A third pins the scan itself so it can't pass vacuously.

**Not run.** No .NET toolchain was available. Logged as X-9.4. The failure messages distinguish
"this type is v4" from "every type reports the same odd version", because the second case would point at
`GuidFactory`'s Medo→`Guid` conversion rather than at any ID type — and would mean IDs system-wide are
not sortable, which is a much larger problem than the one this pass set out to fix.

#### Scope

The two files were the only `Guid.NewGuid()` uses in `src/`. The remaining hits are all in `tests/` —
unique names in integration fixtures, correlation ids in a test double, one commented-out line. All
legitimate; none touched. The guard test currently covers Catalog.Domain only; extending it to the other
six modules' domain assemblies is a one-line change per test project and worth doing when one is next
open.

### 2026-08-24 — J, MediaItem ETag — the tracked item was already fixed; the audit wasn't wasted

The row said `api-conventions.md §Coverage` names the field-level route `PUT` where code and
`mediaitem.api.md` use `PATCH`. That had already been corrected on 2026-08-22, with a dated note left in
place; only the checkbox was outstanding. Ticked.

Reading the surrounding section to confirm turned up three things the review had not recorded. All are
about the same two endpoints — `PUT /v1/items/{itemId}/metadata` and
`PATCH /v1/items/{itemId}/metadata/{fieldName}` — which are, verified, the **only** two endpoints in the
platform that implement `If-Match`/`ETag`. `ConcurrencyHeaders` lives on the shared Catalog endpoint base
and is called from exactly four places, all inside those two files.

#### MI-8 — the spec calls shipped behaviour "future"

`api-conventions.md` said, in bold: *"The version is per-aggregate, not per-field. Any committed change
to the item moves it, so two callers editing unrelated fields concurrently **will conflict**. That is
deliberate for now — see the ADR for the field-level rebase that softens it."*

The rebase is not future work. `MetadataRebase.EvaluateAsync` is wired into both handlers: on a
mismatched `If-Match` it replays the event tail since the caller's base version and lets the write
*proceed* when the write set is disjoint from what changed **and** every field written is marked
`AllowsConcurrentEdit`. The conflict error even names the clashing fields rather than just the versions.

This is the worst shape a doc error can take — not a stale detail, but a stated contract that is the
opposite of the behaviour. A client built against "any mismatch is a 409" has no branch for the success
it will sometimes get. Rewritten to describe the two rebase conditions and, importantly, *why the second
one is not redundant with the first*: a disjoint write set doesn't imply a safe one, because a caller who
read `startDate` and computed `endDate` from it has a disjoint write set and a wrong value. That is the
reasoning the flag exists for, and it was only in the ADR.

Softening detail worth keeping: `AllowsConcurrentEdit` defaults to `false`, so on a tenant that has never
set it the observable behaviour still *is* "any mismatch is a 409". The old text wasn't wrong for
today's tenants — it was wrong about why, and it will become wrong outright the first time someone sets
the flag.

#### MI-9 — the aggregate's own API contract never mentioned any of it

`mediaitem.api.md` has zero occurrences of `If-Match` or `ETag`. The two endpoints that implement
optimistic concurrency documented `204` and a `422`, and both error lists omitted `409` entirely — even
though the endpoints' own FastEndpoints summaries in code declare `ProducesProblem(409)` with the text
"The media item has changed since the version supplied in 'If-Match'".

So the only description of the mechanism lived in `api-conventions.md`, a shared document that named the
wrong verb for it until two days ago. Anyone reading the MediaItem contract — the obvious place to look —
would not have known the feature existed. Added a concurrency block to both endpoint sections: the
header pair with a worked `204`/`ETag` exchange, the rebase rule in two sentences, a `409` body example,
and the `400` cases (`*`, weak tags, malformed) that were also undocumented.

#### MI-10 — the flag that decides the outcome is invisible to clients

`AllowsConcurrentEdit` determines whether a stale write rebases or conflicts. It is authored on the
RecordType's `FieldDefinition` and travels through the integration event, the profile compile, the
MediaProfile snapshot and finally `MediaProfileSnapshotField`, where the guard reads it.

It stops there. Zero hits for `AllowsConcurrentEdit` anywhere in `Catalog.ReadModel*` — no read model,
no endpoint response, nothing on `compiledMetadataFields`. A client cannot discover which fields rebase,
so cannot predict whether a concurrent edit will succeed. Left open; `compiledMetadataFields` on
`GET /v1/profiles/{profileId}` is the natural carrier, and the spec now carries an explicit caveat
saying the flag isn't discoverable rather than leaving readers to infer it. **Closed later the same day
— see below.**

### 2026-08-24 — MI-10 — the flag is now on the wire

Taken as its own pass. The finding held exactly as written: the compile path populates
`CompiledMetadataField.AllowsConcurrentEdit` from the RecordType and `MediaProfileSnapshot` carries it
per field, but `CompiledMetadataTemplateMapper` — the single point where the template is flattened onto
the read side — dropped it, so neither `CompiledMetadataFieldDto` nor `CompiledMetadataFieldModel` had
the property at all.

#### What made it a three-line fix rather than a projector-by-projector one

MP-1 left a genuinely good seam behind. `MediaProfileDetailProjector` and
`MediaProfileVersionDetailProjector` both call `CompiledMetadataTemplateMapper.ToFieldDtos`, and its own
doc comment says the shared mapper exists so the current-state row and the version-snapshot row *cannot*
drift. Adding one argument there fixed both rows at once, and the version row is the one that actually
matters: `MetadataRebase` reads the flag off the snapshot pinned at item creation, not off the profile's
current template, so an item on v1 of a profile now on v3 needs v1's answer.

#### The argument that had to be answered

`CompiledMetadataFieldDto` carries a deliberate exclusion: per-field validation constraints
(`allowedValues`, min/max, regex, …) are *not* projected, because compilation doesn't alter them and
duplicating them puts an unbounded payload on a row list queries also read. `AllowsConcurrentEdit` sits
on that same source record and is unchanged by compilation, so on a first reading it belongs on the
excluded side.

It doesn't, and the distinction is worth having written down: the excluded properties describe what a
*value* may be, and a client that skips them gets a `422` it can read. This one describes what the
*transport* will do — whether an `If-Match` mismatch is a `409` or a silent rebase — and a client that
can't see it has no way to interpret the status code it gets back. It's also one `bool` per field, which
is bounded, so the payload argument doesn't carry. Both the DTO's remarks and
`mediaprofile.read-model.md` now state it as the single exception and why, rather than leaving the next
reader to re-derive it and possibly delete the field.

#### Default direction, and what it means for un-replayed rows

The DTO parameter defaults to `false`, matching the write side. That is what makes the backlog row
tolerable rather than urgent: a profile row written between MP-1 and today has the property absent, it
deserialises to `false`, and the client is told a field will conflict when it may in fact rebase. A
spurious `409` the client already has to handle — the failure mode is a wasted retry, not a bad write.
The reverse default would have promised rebases the server refuses. N.1 rows 2 and 4 widened
accordingly; no new rows.

The response emits the flag on every entry including `false`, deliberately. An omit-when-default
serialisation would make "this field conflicts" and "this server predates the field" the same bytes, and
those mean opposite things to a client deciding whether to bother with `If-Match` at all.

#### Spec

`api-conventions.md` carried a blockquote — added the same day, at MI-8 — stating the flag was not
discoverable and to treat every `409` as expected. That's now the discovery instructions instead, and it
was the one thing in the spec that would have been actively wrong after this change. `mediaprofile.api.md`
gained an `allowsConcurrentEdit` subsection stating the two mismatch branches in the order the server
evaluates them (any `false` field short-circuits before the tail is even read — worth stating, because it
means a mixed write set never rebases no matter what changed), and both metadata endpoint sections in
`mediaitem.api.md` now point at the profile route rather than describing a flag with no address.

#### Tests

Four added: the flag survives the detail projector and the version-detail projector separately (they're
the same mapper today, and a future divergence should break something), it reaches the wire under
`allowsConcurrentEdit` with `false` emitted rather than omitted, and the DTO defaults closed. The
existing colliding-template fixture gained `AllowsConcurrentEdit = true` on its one non-colliding field,
so every assertion in that file now runs against a template with a mixed answer rather than a uniform one.

**Not run here** — no .NET SDK in this session. `Catalog.ReadModel.Tests` needs a local run before this
lands.

### 2026-08-24 — CR-19 — the decision had already been made, twice, elsewhere

The last row in Section F, and the only one logged as a decision rather than a defect: `AddComment`
checks `IsOpen` before participation; `Resolve`/`Abandon` checked the caller first. The review framed it
as a genuine trade-off — *"both orders are defensible, the second leaks less to a stranger, the first is
kinder to a participant"* — and left it for someone to choose.

**Resolved to state-first.** `Resolve` and `Abandon` reordered to check `Status == Open` before
`MayClose`.

#### The framing was the mistake, not the order

Two things the row didn't record, both of which made the choice one-sided.

**The module was already 3–2, not 1–2.** `EditComment` and `DeleteComment` check `IsDeleted` (422)
before `AuthorId` (403). Same shape, same direction as `AddComment` — nobody had written it down, so the
review counted only the command that had a comment on it. Reading the aggregate top to bottom rather
than the two named methods makes it a majority the outliers should join, not a tie needing a casting
vote.

**`MediaItem` had settled the same question the day after CR-19 was filed.** It is the only other
aggregate in the codebase that authorizes inside the domain — every other module puts authorization in
the handler — and all five of its guard pairs are state-first. It also has an explicit ordering test,
added under CR-18 on 2026-08-23:

> `ApproveReview_WhenNotUnderReview_RefusesOnStatusBeforeMembership` — *"the status guard runs first and
> is untagged — a stranger learns the item is not under review rather than that they are not on a roster
> that no longer exists"*

That is `AddComment`'s comment in different words. So the decision CR-19 was waiting on had been taken
in a neighbouring aggregate, by the same hand, one day later, and the two never met.

#### The disclosure argument, weighed rather than asserted

The row's case for authz-first was that it leaks less. It does, but far less than it sounds: a request
the caller cannot name is a `404` from the handler before the aggregate is loaded, so existence is
disclosed either way. The entire marginal disclosure is *the terminal status of a request whose id the
caller already holds* — and ids are UUID v7, so holding one means having been sent it.

Against that, the population that sees any difference at all is non-participants acting on already
closed requests. The most plausible member of that population is a **former** participant, for whom
"this was resolved" is both true and more actionable than "you may not". Participants see no difference
under either order; that half of the review's framing — "kinder to a participant" — was not accurate
either.

#### What the fix actually cost

Two guard reorders. **No test broke** — every existing `Resolve`/`Abandon` test builds an *open*
request, so none of them pinned order; the only order-pinning test in the module pinned state-first. Two
tests added for the closed-request path, and `Resolve_ByANonParticipant_IsForbidden` strengthened to
assert the code, since it is now the other half of a documented order rather than a standalone authority
check.

#### One thing found while verifying, fixed as a comment

`MayClose`'s doc said *"Matches `AddComment`: whoever may discuss the change may close it."* It does
not. `MayClose` is `SystemActor || OwnerId || IsParticipant`; `AddComment` is `IsParticipant` alone. The
system actor arm is intended and load-bearing. The `OwnerId` arm is not a live difference — both
creation paths write the opener into `ParticipantIds` (`OpenChangeRequestHandler` explicitly, the
review-cycle handler by prepending the submitter), so an owner who is not a participant cannot currently
be constructed. Left as behaviour, corrected as documentation: the comment now states what the predicate
actually admits and that the `OwnerId` arm is defence in depth. Chase's call, taken as the smaller of
the two options.

#### Where the rule now lives

`MayClose`'s remarks are the primary statement — it is the method both outliers call, so it is where
someone reordering them would look. Then `mediachangerequest.write-model.md § Guard order` (new section,
replacing the "not yet decided" blockquote) with the per-command table and the reasoning;
`mediachangerequest.api.md` with an explicit precedence line on `resolve`, `abandon`, `POST /comments`,
`PATCH` and `DELETE`; `error-catalog.md § ChangeRequests` with the one line a client integrator most
needs — **a 403 here is not evidence the resource is otherwise actionable, it is evidence every state
guard already passed**; and `mediachangerequest.scenarios.md`, whose two existing notes about
`AddComment` both pointed at CR-19 as unfinished.

A `breaking-changes.md` entry, because one status code moves on the wire: a non-participant naming a
closed request gets `422 ChangeRequestNotOpen` where they got `403 NotChangeRequestParticipant`. Both
codes were already published on both routes, so a client handling the documented set needs no change.

#### CR-24 — the two close endpoints never declared the 403 they return

*Added and fixed 2026-08-24, found verifying the above.* `ResolveChangeRequestEndpoint` and
`AbandonChangeRequestEndpoint` declare `ProducesProblem` for 401/404/422 and omit **403** — in the
`Description` block and again in `Summary`. The aggregate has always returned it for a non-participant,
`ChangeRequestsEndpoint.SendDomainErrorAsync` puts `error.ErrorType.HttpStatusCode` straight on the
wire, and `mediachangerequest.api.md` publishes it. All four comment endpoints declare it. So the
generated OpenAPI has been missing a documented response on exactly these two routes.

Pre-existing and unrelated to the order, but CR-19 makes it worse rather than better: 403 is now the
*narrower* path — reachable only once the status guard has passed — so a client generating from the
document sees the broad case and not the specific one. Declared on both, with the 422 description
amended to say it is checked first. This is the third instance of the pattern X-10.5 names: runtime
behaviour that never reached the machine-readable contract.

**Not run here** — no .NET SDK in this session. `ChangeRequests.WriteModel.Tests` needs a local run.

**Section F is closed.**

#### X-10.5 — no headers at all in the generated OpenAPI

Following MI-9 to its end: the two endpoints read `If-Match` and write `ETag` at runtime, but neither
appears in any `Summary`/`Description` block, so neither reaches the generated OpenAPI document. A client
generated from that document has no knowledge of either header.

Not a concurrency problem — a systemic one. `IdempotencyKey` is accepted on many endpoints and declared
on none of them; the spec markdown says "_Accepts `IdempotencyKey` header._" and the machine-readable
contract doesn't. Logged rather than fixed: it's a pass over every endpoint in the codebase, not a
MediaItem change.

#### Verified along the way

`If-Match` handling itself is correct and needed no change: `*` and weak tags rejected `400` rather than
silently ignored, absent header means unconditional write, the tag is a strong quoted decimal of the
aggregate version, and the `ETag` returned after a rebase is the new version. The Folder metadata routes
(`PUT /folders/{folderId}/metadata`, `PATCH /folders/{folderId}/metadata/{fieldName}`) are the same shape
and implement none of it — now stated explicitly in the Coverage paragraph, which previously implied a
rollout in progress.

### 2026-08-24 — J, the rest: P-10 · CR-1/CR-6/CR-9 · X-1.1 · X-1.6

Six rows. Three were already fixed and untickable only because nobody ticked them; two were larger than
written; one was a rewrite. The verification pass found more in what I wrote than in what was there.

#### P-10 — the enum was the small half

`Bypassed` was missing from the read-model status enum and from both status column descriptions. Added.

But the projection tables in the same file omitted an event **both projectors implement**:
`ProcessingJobTimeoutRecovered`. It matters more than a missing row, because of what it does — a job that
timed out is `Failed` with `FailureCategory = ProcessingTimeout`, and if the worker then returns a late
success, `Complete()` emits recovery rather than refusing. The detail projector nulls `failureReason`;
the summary projector overwrites `statusText`. **`ProcessingTimeout` is the only reversible failure** —
every other category stays terminal. So a polling client can legitimately see `Failed → Succeeded` and
must not treat `Failed` as final without reading the category. That was in no spec file. Documented.

`Bypassed` itself needed a caveat rather than a plain entry: it is reachable in the domain and
serialisable by both read models, but **no projector handles `ProcessingJobBypassed`** (P-3, still open),
so a bypassed job sits at `Queued` forever and a client will never observe the value the enum now
publishes. Saying "the enum has five values" without that would have been true and misleading.

#### CR-1, CR-6 — already done, never ticked

Both were fixed on 2026-08-23 and verified here. CR-6's residue is worth noting: the aggregate property
is `OwnerId` now, but the same person is still `InitiatedBy` on `ChangeRequestCreated` and on
`ChangeRequestSnapshot`, and `CreatedById` on `ChangeRequestCreatedIntegrationEvent`. Those three are
persisted or published contracts — renaming them rewrites stored JSON or breaks a consumer — so they
were deliberately left, and the reasoning is recorded on the property itself.

#### CR-9 — the 2026-08-23 pass covered three files of five

`write-model.md`, `read-model.md` and `context-overview.md` all carry "Rewritten 2026-08-23 (CR-9)"
banners. **Both scenarios files do not**, and both were still describing the superseded CR-first model:

- "carries no lifecycle status and has no reviewer roster" — half right in the worst way. There is no
  reviewer roster, but there *is* a lifecycle: `Open | Resolved | Abandoned`, plus `Title`, `Reason`,
  `Scope`, participants and `MayClose`.
- CRC-1 had the client pre-minting `changeRequestId`, passing it to `POST /change-requests`, then
  passing a `commentThreadId` into publish and getting `202`. Verified against code: the id is
  **server-minted**, `title` is required, publish returns **`200`**, and `commentThreadId` was
  deliberately removed from the publish request — the change request does not exist at that point, so a
  caller-supplied value could not be validated and could bind the review to another item's thread.
- Comment ids were caller-supplied in every example. They are server-minted; the response carries them.
- The edit example used `body`; the field is `newBody`.
- CRC-3 had the handler reading the old body through `ICommentReadModel` — a type that has never existed
  — and `ReviewCommentEdited` carrying `OldBody`. It carries only `NewBody` (CR-10).
- The participant rule was stated as "owner or an assigned reviewer of the linked MediaItem". The guard
  is on the **change request's own** `ParticipantIds`, and terminality is checked first, so a closed
  thread returns `422` to everyone rather than leaking participation status.
- CRC-4 said the projector clears `authorId`. It deliberately doesn't — moderation needs to know who
  withdrew a comment; the body blanking *is* the deletion.

CRC-1 was rewritten around the governance flow it should always have described (open → check out under
it → submit → approval auto-resolves it), and a new CRC-1b covers the comment thread the system raises
at submit — the two kinds of change request were never distinguished in scenarios at all.

#### X-1.1 — and two more errors in the same table

Replaced the `Media.Api` single-host line with the real nine-host table. While there: the module table
said `ChangeRequests | ChangeRequest` (the aggregate is `MediaChangeRequest`) and listed
`DocumentSigningSession` flatly alongside implemented aggregates. Both corrected, with a pointer saying
the repo's own `CLAUDE.md` is authoritative for host layout because it is code-reviewed and this file
isn't.

#### X-1.6 — rewritten, not patched

`service-boundaries.md` described a "Command Handler" Lambda, a single "Projectors" service and a
"SecuredSigning Adapter" service. None exist. It also carried a ~35-row command table and a projection
map that had drifted comprehensively and that duplicate `system-architecture.md` and the per-aggregate
spec files.

Rewrote the topology half against the nine real hosts and **deleted both inventories**, replacing them
with a short "where the inventories live" table. That is the substantive decision here: this document's
only unique content is ownership and negative space — what each host must never do — and every list it
carried was a second copy of something maintained better elsewhere. Keeping them was what let it rot.
370 → 281 lines. The external-context contracts, `IExecutionContext` and the seven Rules were kept and
corrected.

#### Then verification found five things I had got wrong

Worth recording in full, because four of the five came from trusting a comment instead of the code.

**MediatR is not used anywhere.** I wrote "in-process MediatR" in four places, from the stack tables.
Zero references across `src/`, `tests/` and `Directory.Packages.props` in **either** repo. Dispatch is
`ICommandDispatcher` from `Magiq.Platform.WriteModel.Commands`. Both `CLAUDE.md` files say MediatR, the
platform's says "MediatR 13.1.0", and `system-spec.md` agrees — every stack table on the platform is
wrong about a first-order component. Opened as **X-9.5**.

**The S3 → SQS upload-confirmation flow was never built.** I wrote that `Api` receives the S3 completion
notification via SQS, from `asset-storage-and-processing.md:31`. `apiFn` has no `addEventSource` and the
stack declares no bucket notification. `ConfirmAssetUpload` is an ordinary client-called endpoint — the
upload is confirmed because the *client* says so, not because S3 did. That is a materially weaker
guarantee than the ADR describes and needs a decision, not a doc edit. Opened as **X-1.10**.

**Rendition deletion doesn't exist either.** I wrote that `ProcessingWorker` deletes renditions on
archive/delete, from `system-spec.md` and a CDK comment saying the same. The host registers exactly one
message handler, `AssetUploadConfirmedIntegrationEvent`, and has no delete path. Renditions of archived
and deleted assets are never cleaned up. **X-1.9**.

**And the one that matters most: storage-tier tagging never runs.** I wrote that the `AssetAssignedToRole`
consumer applies `tier-policy=managed`. The handler exists, is DI-registered, reaches `PutObjectTagging`,
and has its IAM grant provisioned — but `AssetAssignedToRoleIntegrationEvent` is **not among the ~25
event types the bus subscribes**, so nothing routes to it. Nothing is ever tagged. The originals
lifecycle rule is tag-filtered, so it matches nothing, and **every original stays in S3 Standard
forever**. The entire S12 cost design — the thing the whole `media-documents` retirement was built
around, and which I documented in detail three sessions ago — is inert. Opened as **X-1.8**, High.

**CRC-1b's invariant was backwards.** I wrote that publication does not close the comment thread, citing
CR-15. `MediaItemApprovedEventHandler` calls the closer **twice**, for the edit-session request and the
comment thread — and CR-15 is the change that *added* the second call. I cited it as authority for the
opposite of what it did, in a document that contradicted itself two scenarios earlier. Corrected, with
rejection and withdrawal (CR-21/CR-22) noted as the leaks that genuinely remain.

The pattern in four of five: I was reading a comment — in the ADR, in the CDK, in `system-spec.md` — and
treating it as the code. Every one of those comments was itself the drift.

### 2026-08-24 — X-4.8 and X-9.5 — two doc-alignment items, and what was sitting under each

Both closed as spec-alignment work. Neither turned out to be the size the finding row implied, and in
both cases the interesting part was the thing next to it.

#### X-4.8 — the key shape was the smallest problem

The row read as "one spec row disagrees with the code, and `system-spec.md` has already been fixed."
`system-spec.md` had indeed been corrected in the X-4.6 pass. Four other documents had not, and three
were wrong in larger ways than the key:

- **`system-architecture.md`** carried both version tables with **no version segment in the PK and a bare
  `{discriminator}` SK** — wrong on both halves, not just transposed. Its GSI section listed neither
  `MediaProfileByNameIndex` nor `MediaProfilesByVersionIndex`, even though the `media-profile` row said
  "see GSI notes below" and there were no notes. Its projector table named a `MediaProfileVersionProjector`
  that has never existed and omitted `MediaProfileSummaryProjector` entirely.
- **`system-spec.md`'s** projector table (a second, separate table from the one X-4.6 fixed) repeated both
  projector errors.
- **`mediaprofile.read-model.md` was a document about a different system.** One `media-profiles` table
  holding current-state and version rows together, isolated by a "type-qualified platform key"; a
  `MediaProfileVersionReadModel` type; an `OwnerStatusIndex` GSI; a `ListMediaProfilesByOwnerQuery`; a
  `MediaProfileProjector`. **None of those exist.** The shipped design is four tables, four read models,
  four projectors and two GSIs. Two of the fictions were load-bearing for other findings: the
  owner-scoped list query is the CO-1/M-4 authorization gap in disguise, and the "type-qualified key"
  sentence is the exact misreading of `ProjectionKey` that produced X-4.8.
- **`mediaprofile.api.md`** pointed both version reads at `media-profiles` and omitted the two list routes.

Rewritten against `ServiceCollectionExtensions.cs:168-174`, the four schema classes, and
`projection-tables.manifest.json` — not against each other, which is how the four had drifted apart.

**The key itself was deliberately not changed.** Documented as-is in three places, each carrying the
constructor trap — `(tenantId, discriminator, groupKey)`, discriminator→SK, groupKey→PK suffix — because
that is what made every reader before me get it wrong, including me in the X-4.6 pass. Whether to re-key
is a judgement call with a real hot-partition argument on one side and a replay on the other; opened as
**X-4.10** for Chase rather than decided here. The `media-record-types` Version Detail anomaly needs the
same call and is flagged in the same place.

#### X-9.5 — the naming fix was trivial; the sentence it lived in was not

Eleven documents named MediatR; all corrected. Where it mattered the replacement says *how*, not just
*what* — `ICommandMiddleware` composed in registration order by `CommandPipelineFactory`, **not**
`IPipelineBehavior` — since that is the next thing someone arriving from MediatR would get wrong.

Two things worth recording:

**The finding was itself slightly wrong.** It claimed zero references including `Directory.Packages.props`
in either repo. `aspnetcore-platform/Directory.Packages.props:40` still declares `MediatR 13.1.0`. Nothing
consumes it — central version management doesn't pull a package in without a `.csproj` reference — but
that line is *where the platform's stack table got the version number from*. Left in place: deleting it is
a code change, not a doc change.

**Underneath it was X-9.6, which is not a doc problem.** In three documents the MediatR claim sat inside a
sentence asserting that name reservation and event append "are committed atomically" via an ambient
`ITransactionScope` and a `TransactionBehavior`, with `NameReservationConflictException` handled by a
`NameReservationConflictBehavior` so "handlers never catch it directly." **None of those four types exist**,
and neither does `ConcurrencyConflictException`, named alongside them. Handlers do the opposite of all of
it: `ReserveAsync` then `SaveAsync` as two separate writes, with an inline `try`/`catch` on the conflict.
So **a failure between the two leaves an orphaned reservation that nothing releases** — the name is
permanently burned in that scope. The docs now describe the real flow; the hole does not close by
describing it. **X-9.6.**

CO-4 found this same fiction in `collection.write-model.md` on 2026-08-21 and corrected that one file
without checking whether it appeared elsewhere. It appeared in two more, nearly verbatim — copied outward
from the file CO-4 itself described as "billed as the canonical reference," which is precisely the
mechanism that note warned about. **When a finding is that a canonical document was fiction, the fix isn't
done until the copies are found.**

---


---

## Reclassified during the 2026-08-24 archive split

Five rows carried an unticked `☐` but were not open work. Recorded here rather than left in the live file:

| ✓ | # | Why it was not open |
|---|---|---|
| ☑ | X-1.1 | Fixed 2026-08-24 — the Z:\ `CLAUDE.md` now carries the real nine-host table. §J recorded the fix; the §I.1 box was never ticked |
| ☑ | X-1.6 | Rewritten 2026-08-24 — `service-boundaries.md` rebuilt against the nine real hosts, 370 → 281 lines. §J recorded it; the §I.1 box was never ticked |
| ☑ | X-7.1 | Never a finding — the row records a **✅ Aligned** result (the plans stub is exactly what `CLAUDE.md` describes). The open item in §I.7 is X-7.2 |
| ☑ | X-8.4 | Never a finding — the row records a **✅ Aligned** result (`archive/` is intentional). The open items in §I.8 are X-8.1/2/3/5 |
| ☑ | P-10 | Fixed — `processingjob.read-model.md` now carries the five-value enum including `Bypassed`, and documents `ProcessingJobTimeoutRecovered` on both projectors. §J recorded the fix; the §G box was never ticked. **P-3 remains open** and is the reason `Bypassed` still never reaches a read model |

The §G row as it stood:

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☑ | P-10 | Low | Read-model status enum has four values | Domain enum also has `Bypassed`, which the read models serialise. The read-model spec is stale against its own write-model file | `read-model.md §Embedded Types` |
