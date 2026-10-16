---
id: MM-101
type: plan
project: magiq-media
workstream: WS-61-asset-error-codes
repo: magiq-media
tags: [magiq-media, asset-management, error-codes, api-wire]
consumes: [MM-100]
blocked-by-external: [MM-100]
status: active
branches: []
created: 2026-10-15
depends-on: MM-100
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Asset×error-codes
---

# WS-61 — AssetManagement: `AssetErrorCodes` + handler wiring (29 codes)

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot on `DomainError` + `ProblemDetails` emission)

## Problem

Spec [`error-catalog.md § AssetManagement`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/error-catalog.md#assetmanagement) specifies 29 errorCode constants Asset write endpoints emit. Each has a specified HTTP status, condition and caller-action.

Code today:
- `Asset.cs` emits `DomainError.InvalidOperation("prose message")` for every refusal. No typed codes.
- No `AssetErrorCodes` constants class exists in the module (grep returns zero).
- One quoted string literal `"AssetNotConfirmable"` in `BulkConfirmAssetUploadHandler` for the bulk envelope's `BulkItemError.ErrorCode` — the only coded refusal in the module.
- Endpoints have no error mapper; refusals surface via SDK default `ProblemDetails` with status + title + no root `errorCode`.

Every HTTP consumer of Asset routes cannot branch on `body.errorCode` for any of the 29 codes.

## Scope

29 codes from spec:

`AssetNotFound` · `AssetNotPending` · `AssetNotPendingMultipart` · `AssetPipelineStageNotReached` · `AssetPipelineOutcomeConflict` · `AssetNotDownloadable` · `AssetNotActive` · `AssetNotArchivable` · `AssetAlreadyDeleted` · `AssetNotDeletable` · `AssetIsVersionArtifact` · `AssetAssignedToMediaItem` · `AssetIsProfileDefault` · `AssetAlreadyAttached` · `AssetIdAlreadyExists` · `AssetInColdStorage` · `AssetTooLarge` · `AssetFormatConstraintNotMet` · `PdfARenditionFailed` · `InvalidContentType` · `StorageQuotaExceeded` · `MediaItemArchived` · `MediaItemNotFound` · `S3ObjectNotFound` · `MultipartCompleteRejected` · `MultipartUploadNotFound` · `FileSizeExceeded` · `AssetNotConfirmable` · `RenditionNotFound` · `QuarantineMoveAlreadyConfirmed`

Plus bulk codes already partially present:
- `AssetTooLarge` · `DeclaredSizeExceeded` · `ProfileLimitExceeded` · `DuplicateAssetId` (bulk envelope — spec `catalog-error-codes.md § Batch operations`)

**`AssetPipelineStageNotReached` + `AssetPipelineOutcomeConflict` have `—` HTTP status** — pipeline/SQS-only, no client contract. Still coded for observability per spec.

## Phase 0 — Prereq verify
- [ ] MM-100 shipped — `DomainError.ErrorCode` + `ProblemDetails` emission present in SDK

## Phase 1 — Constants
- [ ] `AssetErrorCodes` static class in `AssetManagement.Domain` (constants are the contract — code lives beside aggregate)
- [ ] 29 `public const string X = nameof(X)` entries

## Phase 2 — Aggregate refusals
- [ ] `Asset.cs` — rewrite each `DomainError.InvalidOperation("prose")` return to carry the specific code:
  - `WithErrorCode(AssetErrorCodes.AssetNotPending)` on status guards
  - `WithErrorCode(AssetErrorCodes.AssetAlreadyAttached)` on attach guard
  - `AssetNotDownloadable` on download refusal
  - `AssetNotActive` / `AssetNotArchivable` / `AssetAlreadyDeleted` / `AssetNotDeletable` on respective transitions
  - `AssetNotActive` on reprocess + attach-to-approved variants
  - `AssetValidationFailed`-shaped refusals carry the specified code per confirm/validate path
- [ ] Pipeline refusals (`AssetPipelineStageNotReached`, `AssetPipelineOutcomeConflict`) codedbut `ErrorType` keeps them non-HTTP; SQS consumer logs the code

## Phase 3 — Handler refusals
- [ ] `InitiateAssetUpload` + bulk variant: `AssetTooLarge` (declared vs profile cap), `AssetIdAlreadyExists` (duplicate caller id), `InvalidContentType`, `MediaItemArchived`, `MediaItemNotFound`, `StorageQuotaExceeded`
- [ ] `ConfirmAssetUpload`: `AssetNotPending`, `S3ObjectNotFound`, `FileSizeExceeded`
- [ ] `CompleteMultipart`: `AssetNotPendingMultipart`, `MultipartCompleteRejected`, `MultipartUploadNotFound`
- [ ] `AbortMultipart`: `AssetNotPendingMultipart`
- [ ] `AttachAssetToMediaItem`: `AssetAlreadyAttached`
- [ ] `ArchiveAsset`: `AssetNotArchivable`
- [ ] `DeleteAsset`: `AssetNotDeletable`, `AssetIsVersionArtifact`, `AssetAssignedToMediaItem`, `AssetIsProfileDefault`
- [ ] `GetDownloadUrl` (read side): `AssetNotFound`, `AssetNotDownloadable`, `AssetInColdStorage`
- [ ] `GetRenditionDownloadUrl`: `RenditionNotFound`
- [ ] `RequestReprocessing`: `AssetNotActive` (code only when invoked via HTTP; SQS path raises `InvalidOperation`)
- [ ] `RetryQuarantineMove`: `QuarantineMoveAlreadyConfirmed`
- [ ] Export preflight: `AssetFormatConstraintNotMet`, `PdfARenditionFailed`
- [ ] `BulkConfirmAssetUploadHandler`: already uses `"AssetNotConfirmable"` string literal — switch to `AssetErrorCodes.AssetNotConfirmable`
- [ ] S3 adapter error mapping — only the allow-listed codes translate per spec (`NoSuchUpload` → `MultipartUploadNotFound`, `InvalidPart` family → `MultipartCompleteRejected`, 403/404 on object → `S3ObjectNotFound`). Unlisted → `Unexpected` → `500`

## Phase 4 — Extension members
- [ ] `AssetTooLarge` carries no extension (declared size vs cap)
- [ ] `StorageQuotaExceeded` — none
- [ ] `MultipartCompleteRejected` carries `detail` with S3 error code wrapped in stable sentence (AWS exception text never reaches wire)
- [ ] `FileSizeExceeded` — spec declares no extension; prose carries actual vs declared

## Phase 5 — Endpoint error mapper (reused SDK Phase 3 of MM-100)
- [ ] No per-endpoint code — SDK middleware from MM-100 handles mapping
- [ ] Verify every Asset write endpoint route emits `errorCode` at ProblemDetails root under integration test

## Phase 6 — Tests
- [ ] Integration test per code: issue the condition, assert `body.errorCode == "<code>"` + HTTP status
- [ ] 29 happy-path refusals + bulk envelope `BulkItemError.ErrorCode` for 4 bulk codes

## Phase 7 — Ship
- [ ] PR to `develop`
- [ ] magiq-media CLAUDE.md: drop any related bullet; add § Known deferred/partial work note if other modules not yet done

## Acceptance criteria

- 29 Asset codes carry the specified HTTP status + root `errorCode` + per-row extension members
- `BulkConfirmAssetUploadHandler` emits `AssetErrorCodes.AssetNotConfirmable` constant, not a literal
- S3 translation is an allow-list; unlisted codes `500`

## Breaking-change note

Wire-visible: client that today sees `errorCode: null` on every Asset refusal will begin receiving coded values. `type` URI moves from `httpstatuses.com` to `errors.magiqmedia.com/domain/<kebab-code>`.

## Session log

- 2026-10-15: plan drafted by alignment sweep (Asset×error-codes cell). `status: candidate` pending triage. Depends on MM-100.
