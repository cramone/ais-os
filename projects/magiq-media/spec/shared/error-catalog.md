# Error Catalog — Media Management

_Last updated: 2026-05-16_

> Exhaustive reference for all `errorCode` values surfaced in RFC 9457 `ProblemDetails` responses. Every error code produced by any endpoint in the platform is listed here with its HTTP status, the condition that produces it, and recommended caller action.

All error responses use `Content-Type: application/problem+json`. The `errorCode` is always in the `extensions` object:

```json
{
  "type": "https://errors.magiqmedia.com/domain/<code>",
  "title": "...",
  "status": 409,
  "extensions": { "errorCode": "MediaItemCheckedOut" }
}
```

Use `https://errors.magiqmedia.com/domain/<code>` for domain/state errors and `https://errors.magiqmedia.com/validation/<code>` for input validation errors.

---

## Common / Cross-Cutting

| `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|
| `Unauthorized` | 401 | Missing, expired, or invalid JWT; replayed `jti` | Re-authenticate and retry with a fresh token |
| `Forbidden` | 403 | Authenticated but not authorised for this operation (wrong `actor_type`, wrong owner) | Do not retry; check actor permissions |
| `NotFound` | 404 | Resource does not exist for this tenant | Verify the ID and tenant context |
| `ConcurrencyConflict` | 409 | Optimistic concurrency violation — another write committed first | Reload the resource and retry the command |
| `InvalidStatusTransition` | 409 | Command rejected because aggregate is in the wrong status | Inspect `currentStatus` in extensions; issue the correct command for that state |
| `InvalidOperation` | 409 | General business rule violation that doesn't map to a more specific code | Read `detail` for specifics |
| `NotResourceOwner` | 403 | Caller's `actor.Id` does not match the resource `OwnerId` | Use the owner's credentials |
| `SystemActorRequired` | 403 | Endpoint requires `actor_type = "System"`; a User or Guest caller was rejected | Use a System token |
| `SearchTermRequired` | 400 | `q` parameter missing or whitespace-only on a search endpoint | Provide a non-empty search term |

---

## AssetManagement

| `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|
| `AssetNotFound` | 404 | Asset does not exist or belongs to a different tenant | Verify `assetId` |
| `AssetNotPending` | 409 | `ConfirmAssetUpload` called but asset is not `Pending` | Asset already progressed; check current status |
| `AssetNotPendingMultipart` | 409 | `CompleteMultipartUpload` / `AbortMultipartUpload` called but `UploadMode ≠ Multipart` or `Status ≠ Pending` | Use the correct completion path for the upload mode |
| `AssetNotValidating` | 409 | Validation result recorded but asset is not `Validating` | Duplicate delivery — idempotent; discard |
| `AssetNotActive` | 409 | Command requires `Status = Active` but asset is in a different status | Check current status; asset may be archived or deleted |
| `AssetNotArchivable` | 409 | `ArchiveAsset` called but asset is not `Active` | Asset is already archived, deleted, or in-flight |
| `AssetNotArchived` | 409 | `DeleteAsset` called from `Archived` path but asset is not archived | Use the `Active → Deleted` path or check current status |
| `AssetAlreadyDeleted` | 409 | `DeleteAsset` called but asset is already `Deleted` | No action required |
| `AssetAlreadyAttached` | 409 | `AttachAssetToMediaItem` called but `MediaItemId` is already set | Asset is already bound; detach first if needed |
| `AssetTooLarge` | 422 | `sizeBytes` exceeds the media-profile's `MaxFileSizeBytes` or the platform standalone limit | Use a smaller file or a media-profile with a higher size limit |
| `StorageQuotaExceeded` | 413 | `IBillingAcl.CheckQuotaAsync` returned non-`Allowed` | Upgrade quota or reduce upload size |
| `MediaItemArchived` | 409 | Asset upload attempted against an archived `MediaItem` | Unarchive the MediaItem or use a different one |
| `MediaItemNotFound` | 404 | Referenced `MediaItemId` does not exist for this tenant | Verify `mediaItemId` |
| `S3ObjectNotFound` | 422 | `ConfirmAssetUpload` HEAD check found no object at the expected S3 key | Client must PUT the file to the pre-signed URL before confirming |
| `MultipartCompleteRejected` | 422 | S3 `CompleteMultipartUpload` rejected the ETags (mismatch, missing parts, etc.) | Verify all part ETags match the values returned by S3; re-upload any missing parts |
| `FileSizeExceeded` | 422 | File exceeds the declared size or media-profile limit (detected at confirmation time) | Re-upload with a compliant file |

---

## Catalog — Collections

| `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|
| `CollectionNotFound` | 404 | Collection does not exist for this tenant | Verify `collectionId` |
| `CollectionAlreadyExists` | 409 | A collection with this name already exists in the tenant | Choose a unique name |
| `CollectionAlreadyArchived` | 409 | Command issued against an already-archived collection | No further mutation allowed; collection is terminal |
| `CollectionArchived` | 409 | Operation not permitted on an archived collection | Unarchive or use a different collection |
| `DuplicateName` | 409 | Name is already reserved within the target scope | Choose a different name |

---

## Catalog — Folders

| `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|
| `FolderNotFound` | 404 | Folder does not exist for this tenant | Verify `folderId` |
| `FolderNotEmpty` | 409 | Archive or delete attempted but folder has active children | Move or archive all children first |
| `CircularFolderReference` | 409 | Move operation would create a cycle in the folder hierarchy | Choose a valid non-descendant target parent |
| `DepthExceeded` | 422 | Folder nesting depth would exceed the platform limit (10) | Restructure the hierarchy |
| `ParentCreationFailed` | 422 | Batch operation: parent folder failed; child was not attempted | Fix the parent creation failure and re-submit |

---

## Catalog — MediaItems

| `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|
| `MediaItemAlreadyExists` | 409 | A MediaItem with this title already exists in the target folder scope | Choose a unique title |
| `DuplicateTitle` | 409 | Title conflicts with an existing MediaItem in the same folder | Choose a unique title |
| `MediaItemCheckedOut` | 409 | Operation not allowed while the MediaItem is checked out | Wait for or force-release the checkout |
| `MediaItemNotCheckedOut` | 409 | `CheckIn` or `ForceReleaseCheckout` called but item is not checked out | No action required |
| `MediaProfileNotPublished` | 422 | Referenced MediaProfile is not in `Published` status | Publish the MediaProfile first |
| `RoleAssignmentNotFound` | 404 | Asset role slot referenced does not exist on the MediaProfile | Verify the role name against the current MediaProfile version |

---

## ChangeRequests

| `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|
| `ChangeRequestNotOpen` | 409 | Operation requires `Status = Open` but the MCR is resolved or abandoned | No further mutation allowed |
| `ReviewerAlreadyAssigned` | 409 | Reviewer is already in the `Reviewers` list for this MCR | No action needed; reviewer is already assigned |
| `ReviewerAlreadyDecided` | 409 | `RemoveReviewer` attempted on a reviewer who has already approved, rejected, or withdrawn | Cannot remove a reviewer who has already decided |
| `ReviewerNotPending` | 409 | Decision command (`Approve`, `Reject`, `Withdraw`) issued but reviewer status is not `Pending` | Reviewer has already decided; no action |
| `ReviewerSelfAssignment` | 422 | Caller attempting to assign themselves as a reviewer on an MCR they initiated | Assign a different reviewer |
| `NotAssignedReviewer` | 403 | Decision command issued by a caller who is not a reviewer on this MCR | Only assigned reviewers may decide |
| `MinimumReviewersRequired` | 422 | `CreateMediaChangeRequest` has no initial reviewers, or `RemoveReviewer` would leave zero decision-capable reviewers | Provide at least one reviewer |
| `NotCommentAuthor` | 403 | Comment edit/delete attempted by a caller who did not author the comment | Only the comment author may modify it |
| `CommentNotFound` | 404 | Comment does not exist on this MCR | Verify `commentId` |

---

## Registration

| `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|
| `MediaItemNotPublished` | 422 | `InitiateRegistration` — MediaItem is not `Published` | Publish the MediaItem first |
| `NoDocumentsAttached` | 422 | `Submit` called with no documents attached | Attach at least one document before submitting |
| `RegistrationConfirmed` | 409 | Mutation attempted on a `Confirmed` registration (use amendment endpoint instead) | Use `POST /registrations/{id}/amendments` for post-confirmation document changes |
| `DuplicatePendingAmendment` | 409 | An open amendment for the same `mediaItemId` already exists | Resolve or cancel the existing amendment first |
| `AmendmentNotPending` | 409 | Amendment approve/reject called but amendment is not `Pending` | Amendment already resolved |
| `ReferenceRequired` | 422 | `ConfirmRegistration` called with an empty `reference` | Provide a non-empty authority reference |
| `SearchTermRequired` | 400 | `GET /registrations/search` called with empty `q` | Provide a non-empty search term |

---

## Processing

| `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|
| `ProcessingJobNotFound` | 404 | Processing job does not exist | Verify `jobId` |
| `ProcessingJobAlreadyComplete` | 409 | Result recorded against an already-terminal job | Duplicate delivery — idempotent; discard |

---

## Batch Operations

These codes appear only in per-item `status` fields inside batch operation responses (not top-level HTTP errors):

| `errorCode` | Condition |
|---|---|
| `FileSizeExceeded` | Item file size exceeds media-profile max |
| `DepthExceeded` | Folder nesting would exceed depth limit |
| `ParentCreationFailed` | Parent item in the same batch failed; this item was not attempted |
| `DuplicateName` / `DuplicateTitle` | Name/title conflicts with an existing record in scope |

---

## Related

- [API Conventions — Error Contract](./api-conventions.md#error-contract--rfc-9457-problemdetails)
- [System Spec — Command Result Contract](./system-spec.md#command-result-contract)
