# Spec vs Repo Alignment Report

Generated: 2026-06-11  
Scope: `D:\source\github\magiq-media\src\modules\` (excluding `.claude/worktrees/`)  
Spec root: `C:\Users\chase\OneDrive\Magiq\AIS-OS\projects\magiq-media\spec\contexts\`

---

## Summary

| Context | Mismatches | Spec-not-in-repo | Repo-not-in-spec |
|---|---|---|---|
| AssetManagement | 9 | 1 | 4 |
| Catalog | 2 | 0 | 4 |
| Processing | 3 | 0 | 1 |
| Registration | 0 | 0 | 0 |
| Metadata | 0 | 0 | 1 |
| DocumentSigning | 1 | 4 | 0 |
| ChangeRequests | 1 | 0 | 0 |

**Total findings: 31**

---

## AssetManagement

### Domain Events

#### MISMATCH: Upload domain event renamed without spec update

- **Spec says:** `AssetUploaded` — emitted by `ConfirmUpload()` / `InitiateUpload()`; fields `AssetId`, `ConfirmedAt` only.
- **Repo has:** Two distinct events — `AssetUploadInitiated` (emitted on upload initiation; 13 fields including `TenantId`, `AssetId`, `OwnerId`, `MediaItemId?`, `OriginalFileName`, `ContentType`, `StorageKey`, `BucketName`, `StorageTier`, `Status`, `SizeBytes`, `UploadedAt`) and `AssetUploadConfirmed` (13 fields including `TenantId`, `AssetId`, `OwnerId`, `OriginalFileName`, `ContentType`, `StorageKey`, `BucketName`, `StorageTier`, `Status`, `SizeBytes`, `ConfirmedAt`).
- **Which is correct:** Repo — the two-phase split (initiation then confirmation) aligns with the actual S3 presigned URL flow and is used correctly throughout the codebase.
- **Recommended fix:** Update the write-model spec to replace `AssetUploaded` with `AssetUploadInitiated` (raised by `InitiateUpload`) and `AssetUploadConfirmed` (raised by `ConfirmUpload`), with the full field lists as found in the repo. Also correct the read-model spec which still references the stale `AssetUploaded` name.

---

#### MISMATCH: Spec lists wrong source event for `AssetUploadConfirmedIntegrationEvent`

- **Spec says:** The source domain event for `AssetUploadConfirmedIntegrationEvent` is `AssetConfirmed`.
- **Repo has:** The integration event is mapped from `AssetUploadConfirmed` (the correct domain event name).
- **Which is correct:** Repo — `AssetConfirmed` does not exist; the spec contains a typo.
- **Recommended fix:** Correct the spec's integration-event table to list `AssetUploadConfirmed` as the source domain event.

---

#### MISMATCH: Upload command and handler renamed without spec update

- **Spec says:** `UploadAssetCommand` / `UploadAssetHandler` initiates the upload.
- **Repo has:** `InitiateAssetUploadCommand` / `InitiateAssetUploadHandler`.
- **Which is correct:** Repo — the name change matches the two-phase event naming and is internally consistent.
- **Recommended fix:** Update the spec commands table to use `InitiateAssetUploadCommand` / `InitiateAssetUploadHandler`.

---

#### MISMATCH: `Archive()` allowed-states precondition differs across spec and repo

- **Write-model spec says:** `Status = Active` (only Active may be archived).
- **API spec says:** `Status = Active | ProcessingFailed`.
- **Repo has:** `Status is not (Active or VersionArtifact)` — i.e. any status except Active and VersionArtifact is rejected; `ProcessingFailed` **is** archivable in the repo.
- **Which is correct:** Unclear — write-model and API spec contradict each other, and the repo differs from both. The repo's guard (`Active | VersionArtifact` are the only blocked states) looks too permissive; `Pending` and `Validating` assets probably should not be archivable.
- **Recommended fix:** Align the write-model spec and API spec on a single precondition. Most likely intent is `Status = Active | ProcessingFailed`; update the write-model spec and tighten the repo guard to match.

---

#### MISMATCH: `Archive()` does not emit `AssetStorageTierTransitioned` atomically

- **Spec says:** `ArchiveAsset()` raises `AssetArchived` AND `AssetStorageTierTransitioned` in the same event-store write.
- **Repo has:** `Archive()` raises only `AssetArchived`; `AssetStorageTierTransitioned` is raised separately by `TransitionStorageTier()`.
- **Which is correct:** Unclear — if the tier is changed synchronously on archive, atomic dual-event emission is correct; if it's an async storage operation, a separate command is correct.
- **Recommended fix:** Clarify intent in the spec. If the tier changes immediately on archive, add the `AssetStorageTierTransitioned` emission to the repo's `Archive()` method. If it is deferred, remove the atomic dual-event claim from the spec.

---

#### MISMATCH: `Delete()` allowed-states precondition

- **API spec says:** Only `Archived` assets may be deleted.
- **Write-model spec says:** `Active | Archived`.
- **Repo has:** `Status is not (Active or Archived)` — meaning only Active and Archived are deletable (same as write-model spec).
- **Which is correct:** Write-model spec / Repo — allowing deletion of Active assets before archiving is a reasonable operational escape hatch; the API spec restriction appears overly conservative.
- **Recommended fix:** Update the API spec to allow `Active | Archived`, matching the write-model and repo.

---

### Integration Events

#### MISMATCH: Integration event name diverges from spec

- **Spec says:** `AssetUploadedIntegrationEvent` with `[MessageType("media.asset.uploaded")]`.
- **Repo has:** `AssetUploadInitiatedIntegrationEvent` with `[MessageType("media.asset.upload-initiated")]`.
- **Which is correct:** Repo — consistent with the `AssetUploadInitiated` domain event rename.
- **Recommended fix:** Update the spec integration-event table to `AssetUploadInitiatedIntegrationEvent` / `media.asset.upload-initiated`.

---

### Commands

#### MISMATCH: `DeleteAssetCommand` has undocumented `Reason` field

- **Spec says:** `DeleteAssetCommand(TenantId, AssetId)`.
- **Repo has:** `DeleteAssetCommand(TenantId, AssetId, string? Reason, DateTimeOffset OccurredAt)`.
- **Which is correct:** Repo likely — `Reason` is useful for audit; `OccurredAt` follows the platform convention.
- **Recommended fix:** Add `Reason?` and `OccurredAt` to the spec's command signature.

---

#### MISMATCH: `DeleteAssetHandler` does not perform synchronous S3 deletion

- **Spec says:** `DeleteAsset` is synchronous and clears the S3 object inline.
- **Repo has:** `DeleteAssetHandler` raises `AssetDeleted` and persists the event, but does not call `DeleteObjectsAsync`; S3 cleanup is presumably deferred or not yet implemented.
- **Which is correct:** Unclear — the spec's synchronous delete intent may be aspirational.
- **Recommended fix:** Either implement the S3 `DeleteObjectsAsync` call inline in the handler (before or after event persistence), or update the spec to describe an async/event-driven deletion pattern.

---

### Read Models / Projectors

#### MISMATCH: Spec defines one projector; repo has two

- **Spec says:** Single `AssetProjector` subscribing to both the `media-assets` (summary) and `media-asset-detail` tables.
- **Repo has:** `AssetSummaryProjector` (writes `media-assets`) and `AssetDetailProjector` (writes `media-asset-detail`), each as separate classes.
- **Which is correct:** Repo — two projectors is cleaner separation.
- **Recommended fix:** Update the spec to describe two projectors: `AssetSummaryProjector` and `AssetDetailProjector`.

---

#### MISMATCH: `media-assets` summary table missing `StorageTier` field in spec

- **Spec says:** `media-assets` table columns: `AssetId`, `TenantId`, `OwnerId`, `FileName`, `ContentType`, `Status`, `SizeBytes`, `UploadedAt`.
- **Repo has:** `AssetSummaryProjector` also writes `StorageTier` when handling `AssetStorageTierTransitioned`.
- **Which is correct:** Repo likely — `StorageTier` is useful on list views for cost/retrieval decisions.
- **Recommended fix:** Add `StorageTier` to the `media-assets` table definition in the read-model spec.

---

### Spec-not-in-repo

#### GAP: `AssetMultipartUploadInitiated` not handled by projectors

- **Spec says:** Both `AssetUploadInitiated` (single-part) and `AssetMultipartUploadInitiated` should be handled to create the initial read-model record.
- **Repo has:** `AssetDetailProjector` and `AssetSummaryProjector` only handle `AssetUploadInitiated`; `AssetMultipartUploadInitiated` is ignored by both projectors, meaning multipart-upload assets never appear in read models until a later event updates them (if ever).
- **Which is correct:** Spec.
- **Recommended fix:** Add a handler for `AssetMultipartUploadInitiated` in both projectors that inserts the initial row (mirroring the `AssetUploadInitiated` handler).

---

### Repo-not-in-spec

#### EXTRA: `AssetValidationStarted` referenced in spec comments but does not exist

- **Repo has:** The `ConfirmAssetUploadEndpoint` has a comment referencing `AssetValidationStarted`; this event does not exist in the domain. The correct event is `AssetValidationPassed` / `AssetValidationFailed` / `AssetInfectionDetected`.
- **Recommended fix:** Correct the comment. No spec change needed — this is a stale code comment.

---

#### EXTRA: `AssetSummaryReadModel` — `StorageTier` field (covered above under read-model mismatch)

---

#### EXTRA: `AssetValidationFailed` → `AssetProcessingFailedIntegrationEvent` with hardcoded `"ValidationFailed"` status string

- **Repo has:** The mapper emits `AssetProcessingFailedIntegrationEvent` with `Status = "ValidationFailed"` for `AssetValidationFailed` domain events.
- **Spec:** Does not specify the `Status` field value for this mapping.
- **Recommended fix:** Document the `Status` string values (`"ValidationFailed"`, `"InfectionDetected"`, etc.) in the spec's integration-event table to prevent consumer drift.

---

#### EXTRA: `AssetUploadConfirmedIntegrationEvent` has more fields than spec lists

- **Repo has:** `AssetUploadConfirmedIntegrationEvent` carries `TenantId`, `AssetId`, `OwnerId`, `FileName`, `ContentType`, `StorageKey`, `Status`, `ConfirmedAt`, `EventVersion` (9 fields).
- **Spec says:** The source domain event has only `AssetId`, `ConfirmedAt`.
- **Recommended fix:** Update the spec's integration-event payload description to list the full field set as implemented.

---

## Catalog

### Domain Events

#### MISMATCH: `MediaItemSubmittedForReview` domain event renamed to `MediaItemPublicationRequested`

- **Spec says:** Domain event is `MediaItemSubmittedForReview`.
- **Repo has:** Domain event class is `MediaItemPublicationRequested`; the integration event mapper correctly translates it to `MediaItemSubmittedForReviewIntegrationEvent` for cross-context consumers.
- **Which is correct:** Unclear — the domain event name diverges from the spec, but the integration event name is preserved, shielding consumers. The repo name arguably better describes the action (requesting publication triggers a review).
- **Recommended fix:** Either rename the domain event back to `MediaItemSubmittedForReview` to match the spec, or update the spec to `MediaItemPublicationRequested` and document that the integration event name is a deliberate translation.

---

### Commands

#### MISMATCH: `ApproveMediaItemCommand` is a dead command with no route

- **Spec says:** Single `ApproveReviewCommand(MediaItemId, ReviewerId, DecisionComment?)` for reviewer approval, routed via `POST /catalog/items/{id}/approve`.
- **Repo has:** Both `ApproveReviewCommand` and `ApproveMediaItemCommand` with identical signatures. `ApproveMediaItemEndpoint` dispatches `ApproveReviewCommand` (not `ApproveMediaItemCommand`). `ApproveMediaItemCommand` is registered in the DI container but is never dispatched from any endpoint or handler.
- **Which is correct:** Spec — `ApproveReviewCommand` is the correct command; `ApproveMediaItemCommand` appears to be a leftover from a rename that was not fully completed.
- **Recommended fix:** Delete `ApproveMediaItemCommand` and `ApproveMediaItemHandler`.

---

### Repo-not-in-spec

#### EXTRA: `UpdateMediaItemConformanceStatusCommand` / `MediaItemConformanceStatusChanged`

- **Repo has:** A full command, handler, and domain event for updating conformance status on a `MediaItem`. No coverage in the spec.
- **Recommended fix:** Either write the spec for this operation (preconditions, payload, integration events) or determine whether it is obsolete and remove it.

---

#### EXTRA: `UpdateMediaItemDescriptionCommand` / `MediaItemDescriptionUpdated`

- **Repo has:** A command, handler, and domain event for updating the description field of a `MediaItem`. Not in the spec.
- **Recommended fix:** Add to spec (preconditions, field validation, whether it emits an integration event).

---

#### EXTRA: `RemoveRegistrationRefCommand` / `RegistrationRefRemoved`

- **Repo has:** A command, handler, and domain event for removing a registration reference from a `MediaItem`. Not in the spec (spec only covers `AddRegistrationRef` / `RegistrationRefAdded`).
- **Recommended fix:** Add the reverse operation to the spec, including preconditions (e.g. cannot remove a confirmed registration reference) and whether an integration event is required.

---

#### EXTRA: `MediaItemConformanceStatusChanged` event not in spec

- Covered by the `UpdateMediaItemConformanceStatusCommand` entry above.

---

## Processing

### Commands / Trigger Timing

#### MISMATCH: Processing job created on upload initiation, not upload confirmation

- **Spec says:** `CreateProcessingJobCommand` is dispatched by the handler for `AssetUploadConfirmedIntegrationEvent`.
- **Repo has:** `AssetUploadInitiatedEventHandler` (in `Processing.WriteModel`) dispatches `CreateProcessingJobCommand` immediately on receipt of `AssetUploadInitiatedIntegrationEvent` — before the S3 upload has even occurred. `AssetUploadConfirmedEventHandler` only triggers `IAssetValidationWorker.ValidateAsync` and does not create a job.
- **Which is correct:** Spec — creating a processing job before the file is confirmed uploaded means the job exists in a `Queued` state for an asset that may never complete its upload (e.g. browser closes). This is a functional bug.
- **Recommended fix:** Move `CreateProcessingJobCommand` dispatch to `AssetUploadConfirmedEventHandler`, and have `AssetUploadInitiatedEventHandler` do nothing (or be removed). Ensure `AssetValidationWorker` is invoked after job creation.

---

### Read Models / Projectors

#### MISMATCH: Spec defines one projector; repo has two

- **Spec says:** Single `ProcessingJobProjector` for both list and detail read models.
- **Repo has:** `ProcessingJobSummaryProjector` and `ProcessingJobDetailProjector` as separate classes.
- **Which is correct:** Repo — same rationale as AssetManagement split.
- **Recommended fix:** Update the spec to describe two projectors.

---

#### MISMATCH: Query name differs between spec and repo

- **Spec says:** `GetProcessingJobByAssetIdQuery`.
- **Repo has:** `ListProcessingJobsForAssetIdQuery`.
- **Which is correct:** Repo likely — an asset may have multiple processing jobs over its lifetime; a `List` query is more accurate than `GetBy`.
- **Recommended fix:** Update the spec query name to `ListProcessingJobsForAssetIdQuery`.

---

### Repo-not-in-spec

#### EXTRA: `ProcessingJobFailed` mapper hardcodes `"ProcessingError"` failure category

- **Repo has:** `ProcessingDomainEventMapper` sets `FailureCategory = "ProcessingError"` unconditionally for all `ProcessingJobFailed` events.
- **Spec:** Does not specify `FailureCategory` values or that the field should be hardcoded.
- **Recommended fix:** Document the allowed `FailureCategory` values in the spec. Consider whether the category should be sourced from the domain event payload rather than hardcoded.

---

## Registration

No mismatches found. All commands, domain events (`RegistrationInitiated`, `RegistrationSubmitted`, `RegistrationConfirmed`, `RegistrationRejected`, `RegistrationResubmitted`, `RegistrationCancelled`, `RegistrationItemAttached`, `RegistrationAmendmentRequested`, `RegistrationAmendmentApproved`, `RegistrationAmendmentRejected`), integration events, and API endpoints align with the spec.

---

## Metadata

### Repo-not-in-spec

#### EXTRA: `UpdateRecordTypeDisplayNameCommand` / `RecordTypeDisplayNameUpdated`

- **Repo has:** A full command (`UpdateRecordTypeDisplayNameCommand`), handler, and domain event (`RecordTypeDisplayNameUpdated`) for updating the display name of a RecordType.
- **Spec says:** The spec lists a `DisplayName` property on the RecordType aggregate but defines no corresponding command or domain event. The spec's command list includes `RenameRecordTypeCommand` (for the `Name` field, which drives uniqueness) but nothing for `DisplayName`.
- **Which is correct:** Repo likely — `DisplayName` is a separate human-readable label from the unique `Name`; a dedicated update command is reasonable.
- **Recommended fix:** Add `UpdateRecordTypeDisplayNameCommand` / `RecordTypeDisplayNameUpdated` to the spec's commands and domain-events tables, with precondition (e.g. `Status = Published | Draft`) and payload fields.

---

## DocumentSigning

### Aggregate Existence

#### MISMATCH: Spec marks aggregate as not yet implemented; domain events exist but the rest does not

- **Spec says:** "This aggregate does not yet exist in the codebase."
- **Repo has:**
  - Domain events **are** implemented: `SigningSessionInitiated`, `SigningEnvelopeCreated`, `SigningEnvelopeSent`, `SignerCompleted`, `SigningCompleted`, `SignedAssetRecorded`, `SigningEnvelopeVoided`, `SigningSessionCancelled`, `SigningSessionTimedOut`.
  - `DocumentSigningSession` **aggregate class** — absent.
  - **Commands** — absent (no `InitiateSigningSession`, `RecordSignerCompletion`, etc.).
  - **Write-model handlers** — absent.
  - **API endpoints** — absent.
  - **Partial saga implementation** — `SigningSessionInitiatedHandler` exists in `SagaOrchestrator.DocumentSigning` but is incomplete.
- **Which is correct:** The spec's disclaimer is partially stale — domain events have been added since the spec was written, but the bulk of the implementation is still missing.
- **Recommended fix:** Update the spec disclaimer to reflect that domain events are defined. Track the following as outstanding implementation work:
  1. `DocumentSigningSession` aggregate class with `Apply` methods for all 9 domain events.
  2. Command records and handlers for all operations (`InitiateSigningSession`, `RecordEnvelopeCreated`, `RecordEnvelopeSent`, `RecordSignerCompletion`, `RecordSigningCompleted`, `RecordSignedAsset`, `VoidEnvelope`, `CancelSession`, `TimeOutSession`).
  3. Write-model API endpoints.
  4. Complete the `DocumentSigningSaga` orchestrator.

---

## ChangeRequests

### API Endpoints

#### MISMATCH: `POST /v1/change-requests` endpoint absent from write-model endpoints project

- **Spec says:**
  - Write model: `CreateChangeRequest` is "system-created" via `MediaItemPublicationRequestedEventHandler`; clients do not call it directly.
  - API spec: `POST /v1/change-requests` is listed as an explicit HTTP endpoint with a documented request/response contract (caller-generated `changeRequestId`).
  - These two spec documents contradict each other.
- **Repo has:** No `CreateChangeRequest` HTTP endpoint in `ChangeRequests.WriteModel.Endpoints`. The `CreateChangeRequestCommand` and handler exist, and the command **is** dispatched by `MediaItemPublicationRequestedEventHandler` (system-created path). No public HTTP route is exposed.
- **Which is correct:** Write-model spec / Repo — the system-created flow is implemented and working. The API spec appears to have retained a legacy client-facing route that was superseded by the event-driven approach.
- **Recommended fix:** Remove `POST /v1/change-requests` from the API spec, or add a clear note that the endpoint is intentionally absent and creation is system-triggered only.

---

## Cross-Cutting Observations

1. **`AssetUploadInitiated` vs `AssetUploaded` naming ripple:** The upstream rename of the upload initiation event was fully propagated through domain events, integration events, handlers, and projectors — but the spec was never updated. This is the root cause of ~4 individual findings above. A single spec update pass would close all of them.

2. **Two-projector pattern is consistent but undocumented:** Both AssetManagement and Processing use a `SummaryProjector` + `DetailProjector` split. The spec describes only single projectors for both. This is a documentation gap, not a code problem.

3. **`AssetUploadConfirmedIntegrationEvent` payload richness:** The repo adds `OwnerId`, `FileName`, `ContentType`, `StorageKey`, and `Status` to the integration event beyond what the spec implies. This enrichment is consumed by Processing's `AssetValidationWorker`. The spec should document the full payload to prevent consumers from being surprised.

4. **Processing trigger timing (critical):** The finding that jobs are created on `AssetUploadInitiated` rather than `AssetUploadConfirmed` is the most significant functional bug in the audit. Jobs will accumulate for uploads that were never completed, and the `Queued` → `Running` transition will be triggered for assets with no committed S3 object.
