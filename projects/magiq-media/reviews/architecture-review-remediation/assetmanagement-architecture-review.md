# AssetManagement — Module Architecture Review (Specification vs Repository)

_Module: **AssetManagement** (bounded context) — magiq-media_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API)_
_Date: 2026-07-19_
_Scope: `src/modules/AssetManagement/**` vs `docs/spec/contexts/AssetManagement/**` (+ shared conventions, error catalog, security scenarios, bulk operations)_

> Method: every production `.cs` file in the module (214 files across Domain, WriteModel, WriteModel.Endpoints, WriteModel.Infrastructure, ReadModel, ReadModel.Endpoints, ReadModel.Infrastructure, Contracts) was read and compared against the Asset write-model, read-model, API, scenarios and context-overview specs. The Processing / Catalog / Billing contexts and the `Magiq.Platform` SDK are only referenced where AssetManagement depends on them; findings that hinge on platform-base behaviour that could not be read directly are flagged as such.

---

## 1. Module Summary

AssetManagement owns the `Asset` aggregate — a single uploaded file and its derived renditions — from pre-signed-URL issuance through virus scan, format validation, the processing pipeline, storage-tier lifecycle and final archival/deletion. It is a textbook event-sourced, CQRS module: a rich `Asset` aggregate (`media.asset` stream), a per-module SNS integration-event publisher, two DynamoDB read models (`media-assets` summary, `media-asset-detail`) fed by SQS projectors, and S3 for object storage across `media-source` (originals) and `media-renditions`.

The module is large and, structurally, well organised: command-per-folder, thin FastEndpoints, an integration-event mapper, and a set of write-side reference models (`media-item-capability-refs`, `asset-profile-default-refs`) that let upload-time guards run without cross-BC calls. The domain model is genuinely sophisticated — multipart uploads, document fast-exit, version-artifact promotion, S12 "process-on-assign", and a `ProcessingTimeout`-only recovery path.

However, the module is **not production-ready**. The review surfaced three Critical and a cluster of High issues that fall into four themes:

1. **Authorization is absent.** No endpoint declares an auth policy and no handler performs the PERM-1 owner check. Any authenticated tenant user can read, download, archive, tag or hard-delete any other user's asset.
2. **Handler-orchestrated S3 side effects are mis-ordered and non-transactional.** `DeleteAsset` destroys S3 objects *before* the domain guard runs; multipart complete/abort mutate S3 before the event is persisted; virus-handling deletes before the state guard. These are dual-write bugs on irreversible operations against regulated records.
3. **The read model and integration surface silently diverge from the write model.** Four domain events (`AssetInfectionDetected`, `AssetPromotedToVersionArtifact`, `AssetVersionArtifactReleased`, `AssetReprocessingRequested`) are never projected; integration consumers ignore command `Result`s and swallow failures with no DLQ; the capability reference projector loses archives on reorder.
4. **The error/validation contract is unmet.** Domain guards return generic `InvalidOperation` (422) instead of the catalog's coded 409/422 errors; RFC 9457 `errorCode` is not emitted; there are no request validators, so malformed input yields 500.

The domain aggregate itself is the strongest part of the module; most Critical/High defects live in the **handler / consumer / projector orchestration layer** around it.

---

## 2. Aggregate Analysis

### `Asset` (Aggregate Root) — `AssetManagement.Domain/Aggregates/Asset.cs`

Single aggregate in the context. `EventSourced<Asset, AssetId>`, `ITenantScoped`, `[AggregateType("media.asset")]`.

**Purpose & responsibilities:** own the file's full ingestion/processing/storage lifecycle and all invariants governing state transitions.

**Aggregate root:** `Asset`. **Child entities:** none (correctly — renditions are value objects). **Value objects:** `AssetId`, `FileName`, `StorageKey`, `MediaCategory`, `RoleName`, `Rendition`, `AssetMetadata`, `ArchiveMetadata`, `Tag`, `AssetStatus`, `UploadMode`, `ProcessingStatus`, `FailureCategory`, `MediaItemId`, `UploaderId`, `TenantId`, `ValidationOutcome`. This is a healthy VO surface — the aggregate is not anemic.

**Key state:** `Status`, `UploadMode`, `MultipartUploadId?`, `MediaItemId?`, `RoleName?`, `IsPrimary`, `StorageKey` (immutable post-creation), `Renditions`, `Metadata` (write-once), `Tags`, `LastFailureCategory` (gates timeout recovery), and `_preVersionArtifactStatus` (rebuilt from replay, not persisted).

**Invariants enforced in the aggregate (correct):**
- Multipart/single-part completion paths are mutually exclusive (`ConfirmMultipartUpload` / `ConfirmSinglePartUpload` guard on `UploadMode`).
- `FailProcessing` is stage-aware: `(Pending,UploadExpired)`, `(Validating,ValidationTimeout)`, `(Processing,ProcessingTimeout|ProcessingError)`.
- Only `ProcessingFailed(ProcessingTimeout)` is reversible to `Active` (timeout recovery); every other failure is terminal.
- `Delete` blocks `VersionArtifact`, blocks assigned non-failed assets, and restricts to `{Active, Archived, ValidationFailed, ProcessingFailed}`.
- `PromoteToVersionArtifact` restricted to `{Active, Archived}`; `_preVersionArtifactStatus` captured on `Apply` and restored on release.
- `StorageKey` immutable after the creation event.

**Aggregate boundary assessment:** boundaries are appropriate. The aggregate correctly does **not** own role-assignment policy, capability/quota resolution, or S3 mechanics — those are handler/reference-model/Catalog concerns. Size is reasonable for the lifecycle it governs.

**Aggregate-level defects (detailed in §12–13):**
- **A-D1 (High).** `RoleName` can only be set by `AttachToMediaItem`, which hard-guards `MediaItemId == null`. An asset uploaded *with* a `MediaItemId` (the primary A-1 flow) therefore can never receive a `RoleName`; `IsAssigned()` is `false` forever, silently disabling the delete-lock invariant and diverging from Catalog. (`Asset.cs:205-214, 386-390`.)
- **A-D2 (Low, correctness/determinism).** `RecordValidationResult`'s virus branch emits `AssetInfectionDetected(..., DateTimeOffset.UtcNow)` (`Asset.cs:447`) instead of the passed `recordedAt` — non-deterministic wall-clock inside a domain method; breaks replay reproducibility and skews the published infection timestamp.
- **A-D3 (Medium, spec mismatch).** `FailProcessing` accepts `Pending` (`UploadExpired`), but the write-model invariant table says `FailAssetProcessing` requires `Validating`/`Processing` only. Also `FailureCategory.ValidationError` exists in the enum but no aggregate path ever produces it via `FailProcessing` (validation failure goes through the distinct `AssetValidationFailed`).
- **A-D4 (Medium, generic errors).** Guards return `DomainError.InvalidOperation` (422) rather than the catalog's specific coded errors (`AssetNotActive`, `AssetAlreadyAttached`→409, `AssetNotArchivable`, `AssetNotValidating`→409). Loses the retry-ability signal (409 vs 422) and machine-discriminable `errorCode`.

---

## 3. Lifecycle Analysis

### State machine (reconstructed from `Asset.cs` guards + `Apply` handlers)

```text
                         InitiateUpload (SinglePart)          InitiateMultipartUpload (Multipart)
                                  │                                     │
                                  ▼                                     ▼
                               Pending ───────────────────────────── Pending
                          (SinglePart)                             (Multipart)
                                  │                             ┌───────┴────────┐
                       ConfirmAssetUpload            CompleteMultipartUpload   AbortMultipartUpload
                                  │                             │                │
                                  ▼                             ▼                ▼
                              Validating ◄────────────────── Validating     MultipartAborted [terminal]
                    ┌─────────────┼───────────────┬──────────────────────┐
        RecordValidation:Fail  :Virus        StartProcessing        ActivateDocument
                    │             │               │                      │
                    ▼             ▼               ▼                      ▼
             ValidationFailed  ContainsVirus   Processing              Active  (document fast-exit)
                [terminal*]     [terminal]     ┌───┴─────────┐        (ProcessingStatus=Validated)
                                     CompleteProcessing   FailProcessing
                                               │               │
                                               ▼               ▼
                                             Active        ProcessingFailed
                                                               │  (ProcessingTimeout only)
                                               ┌───────────────┤  CompleteProcessing(success)
                                               │               ▼
                                               │   AssetProcessingTimeoutRecovered → Active
     Active ──RequestReprocessing(no renditions, attached)──► Validating   (S12 re-drive)
     Active | ProcessingFailed ──Archive──► Archived
     Active | Archived ──PromoteToVersionArtifact──► VersionArtifact ──ReleaseVersionArtifact──► Active|Archived
     {Active, Archived, ValidationFailed, ProcessingFailed} ──Delete──► Deleted [soft]
```

`*` `ValidationFailed` is a terminal *processing* state but remains deletable (cleanup).

**Terminal states:** `MultipartAborted`, `ContainsVirus`, `Deleted`. **Reversible-failure:** `ProcessingFailed(ProcessingTimeout)` → `Active`. **Restore:** `VersionArtifact` → prior status.

### Lifecycle issues

- **L-1 (High) — Reprocessing has no timeout/compensation.** `RequestReprocessing` re-enters `Validating` (S12), but the code comment concedes the `AssetIngestionSaga` is terminal per asset and "saga-tracked reprocess timeouts are a documented follow-up" (`Asset.cs:477-480`). If the re-driven validation or processing stalls, there is no `ValidationTimeout`/`ProcessingTimeout` saga to fail it — the asset is stuck in `Validating`/`Processing` indefinitely with no recovery path.
- **L-2 (Medium) — Dead-end read-model rows with no removal path.** `ContainsVirus` and `MultipartAborted` are terminal but are **not** in `Delete`'s allowed set, so their read-model rows can never be removed. (`ContainsVirus` is doubly problematic — see §12 C-3, it is not even projected.)
- **L-3 (Medium) — `Deleted` is a soft state in the domain but the handler hard-deletes S3.** The aggregate/write-model model `Deleted` as "soft; S3 retained," yet `DeleteAssetHandler` and `AssetDeletedIntegrationEvent` perform/trigger hard S3 deletion. The retention guarantee stated in the spec is not real. (See §12 C-1 and §13.)
- **L-4 (Low) — Document fast-exit and full pipeline both terminate at `Active` via the same `AssetProcessingCompleted` event**, discriminated only by `ProcessingStatus` (`Validated` vs `Transcoded`). Acceptable, but it overloads one event across two lifecycles and leaks into the integration surface (§10 F-P3).

---

## 4. Commands

19 commands. `⚠` marks a command with at least one finding (detailed in §12–15).

| Command | Handler | Trigger | Notes |
|---|---|---|---|
| InitiateAssetUpload | InitiateAssetUploadHandler | API | ⚠ standalone max-size guard absent; capability-index race |
| InitiateAssetMultipartUpload | InitiateAssetMultipartUploadHandler | API | ⚠ orphan S3 session on part-url failure; 15-min TTL |
| CompleteMultipartUpload | CompleteMultipartUploadHandler | API | ⚠ S3-before-event → permanent wedge on retry |
| AbortAssetMultipartUpload | AbortAssetMultipartUploadHandler | API | ⚠ S3-before-event retry wedge (lower impact) |
| ConfirmAssetUpload | ConfirmAssetUploadHandler | API | ⚠ no owner check; doc says →Active (actually →Validating) |
| BulkConfirmAssetUpload | BulkConfirmAssetUploadHandler | API | ⚠ 50-cap unenforced; no content-type guard; concurrency catch too narrow |
| RecordValidationResult | RecordValidationResultHandler | System (consumer) | ⚠ S3 delete before guard; hard-delete vs quarantine |
| StartAssetProcessing | StartAssetProcessingHandler | System (consumer) | ⚠ duplicate delivery result swallowed |
| CompleteAssetProcessing | CompleteAssetProcessingHandler | System (consumer) | ⚠ result swallowed; metadata field loss upstream |
| FailAssetProcessing | FailAssetProcessingHandler | System (consumer) | ⚠ actor_type=System not enforced |
| ActivateDocumentAsset | ActivateDocumentAssetHandler | System (consumer) | emits ProcessingCompleted(Validated) |
| TagAsset | TagAssetHandler | API | ⚠ no owner check |
| ArchiveAsset | ArchiveAssetHandler | API | ⚠ no owner check |
| DeleteAsset | DeleteAssetHandler | API | ⚠ **Critical**: S3 deleted before guard |
| AttachAssetToMediaItem | AttachAssetToMediaItemHandler | Internal (Catalog) | ⚠ collides with item-scoped uploads (A-D1) |
| DetachAssetFromMediaItem | DetachAssetFromMediaItemHandler | Internal (Catalog) | ⚠ always fails for item-scoped assets |
| ApplyAssetAssignment | ApplyAssetAssignmentHandler | Internal (Catalog, S12) | ⚠ quota "charged" only checked; Unavailable==Exceeded; IsPrimary hardcoded |
| PromoteAssetToVersionArtifact | (per-asset from MediaItemApproved) | System (consumer) | ⚠ swallowed per-asset failure → unprotected |
| ReleaseVersionArtifact | (per-asset from MediaItemVersionPurged) | System (consumer) | ⚠ swallowed per-asset failure → stuck VersionArtifact |

**Cross-cutting command issues:**
- **No mutating command carries the actor's identity** (`ArchiveAssetCommand`, `TagAssetCommand`, `DeleteAssetCommand` are `(TenantId, AssetId, …)`), so the PERM-1 owner check is impossible downstream even if a handler wanted to run it (§12 C-2).
- **Handlers return generic errors** rather than catalog codes (§2 A-D4).
- **Missing command:** there is no `BulkInitiateAssetUploadCommand` although the spec defines `POST /v1/assets/uploads/bulk` (§15).
- **No duplicate/redundant commands** were found; the command set maps cleanly 1:1 to aggregate methods.

---

## 5. Queries

4 queries — `GetAssetById`, `GetAssetDownloadUrl`, `GetRenditionDownloadUrl`, `ListAssetsByMediaItem`.

| Query | Paging | Auth | Notes |
|---|---|---|---|
| GetAssetByIdQuery | n/a | ⚠ none | returns `Deleted` assets (should 404); leaks `TenantId` |
| ListAssetsByMediaItemQuery | cursor (ADR-014 ✔) | ⚠ none | does not exclude `Deleted`; invalid `status` filter silently ignored |
| GetAssetDownloadUrlQuery | n/a | ⚠ none | not-downloadable → 500 (should 409); cold-storage handled ✔ |
| GetRenditionDownloadUrlQuery | n/a | ⚠ none | no retrievability check (blind presign) |

**Query issues:**
- **CQRS boundary is clean** — handlers return DTOs only, no aggregates/event payloads cross the boundary; cursor-only pagination with no total count is correct per ADR-014. Good.
- **No owner scoping** on any query — cross-owner read/download within a tenant (§12 C-2). The download variants mint working presigned S3 GET URLs to another owner's bytes.
- **Soft-deleted rows leak** into `GetAssetById` (200 + `Deleted`) and unfiltered list results (§12 H-x).
- **`GetRenditionDownloadUrl`** does not consult `IAssetRetrievalInspector`, unlike the original-binary handler, so it can presign an object in cold storage.
- **Missing query capability:** there is no query to list a user's standalone assets (no `mediaItemId`); `ListAssetsByMediaItem` requires `mediaItemId`, so standalone uploads are unlistable via the API. (Design gap — confirm intent.)

---

## 6. API Endpoints

Spec (asset.api.md) vs implementation:

| Spec route | Verb | Impl? | Impl code | Spec code | Note |
|---|---|---|---|---|---|
| /v1/assets/uploads | POST | ✔ | 202 | 202 | ok |
| /v1/assets/uploads/bulk | POST | ✖ **missing** | — | 201/202 | bulk-initiate not implemented |
| /v1/assets/uploads/bulk-confirm | POST | ✔ | 201/202/**422** | 201/202 | extra 422 branch |
| /v1/assets/{id}/uploads/confirm | POST | ✔ | 202 **+body** | 202 no-body | body not in spec |
| /v1/assets/multipart-uploads | POST | ✔ | 202 | 202 | ok |
| /v1/assets/{id}/multipart-upload/complete | POST | ✔ | 204 | 204 | ok |
| /v1/assets/{id}/multipart-upload/abort | POST | ✔ | 202 **+body** | 202 no-body | leaks AssetStatus enum as int |
| /v1/assets/{id}/tags | PUT | ✔ | 200 | 200 | ok |
| /v1/assets/{id}/archive | POST | ✔ | 204 | 204 | ok |
| /v1/assets/{id} | DELETE | ✔ | 204 | 204 | ok |
| /v1/assets/{id} | GET | ✔ | 200 | 200 | leaks tenantId |
| /v1/assets?mediaItemId=&status= | GET | ✔ | 200 | 200 | ok |
| /v1/assets/{id}/download | GET | ✔ | 200/409(/500) | 200/409 | status-guard path returns 500 |
| /v1/assets/{id}/renditions/{type}/download | GET | ✔ | 200/409 | 200/409 | ok |

**Endpoint issues:**
- **No endpoint declares authorization** (grep for `Roles/Policies/Permissions/RequireActorType/AllowAnonymous/PreProcessor` → zero hits). Every endpoint's Swagger advertises a 403 that no code path can emit. (§12 C-2)
- **RFC 9457 `errorCode` not emitted** — both base endpoints send `AddError(message)` + `SendErrorsAsync(status)`; the read-side base additionally flattens all domain errors to `NotFound→404 / Forbidden→403 / _→500`, discarding the domain `errorCode` (this is why the download status-guard returns 500). (§12 H-x)
- **Missing endpoint:** `POST /v1/assets/uploads/bulk` (§15).
- **Verb/route/version:** all *registered* routes match the spec and every endpoint is `Version(1)`. Several XML doc-comments cite stale sub-paths (cosmetic).
- **Status-code drift:** bulk all-failed returns 422 (spec: 202); confirm/abort return a body where spec says none; abort leaks the `AssetStatus` enum serialized as an integer.

---

## 7. Request DTO Review

| DTO | Findings |
|---|---|
| InitiateAssetUploadRequest | field `ItemId` (multipart uses `MediaItemId`); Swagger documents a non-existent `mediaItemId` param; no validation of size/fileName |
| InitiateAssetMultipartUploadRequest | `MediaItemId` (naming diverges from single-part `ItemId`); no size/part validation |
| TagAssetRequest | `_tags = null!` with dereferencing setter → **NRE (500)** if `tags` omitted; tag length/pattern unvalidated |
| BulkConfirmAssetUploadRequest | mutable `class`; only "≥1" enforced, **50-item cap unenforced** |
| DeleteAssetRequest / CompleteAssetMultipartUploadRequest / others | mixed mutable/immutable styles; no id well-formedness validation |

**Cross-cutting:**
- **No FluentValidation validators anywhere** in the module (grep confirms). Consequences: `MediaItemId.From`/`AssetId.From`/`Tag.From` call `Guid.Parse`/VO constructors that **throw on malformed input → unhandled → 500** where the spec expects 400/404/422.
- **`pageSize` cap (100) not enforced locally** — depends on unverified platform `PagerParameters`.
- **Field-naming inconsistency:** same concept `mediaItemId` spelled `ItemId` vs `MediaItemId`; the filtering ADR bans `itemId`.
- No unused request properties found.

---

## 8. Response DTO Review

| DTO | Findings |
|---|---|
| GetAssetByIdResponse | leaks internal `TenantId`; size field named `SizeBytes` |
| AssetSummaryModel | `FileSizeBytes` **always null** (projector never populates it — §12 H-x); size field named `FileSizeBytes` |
| GetAssetDownloadUrlResponse | size field `FileSizeBytes` (spec: `sizeBytes`) |
| AssetRenditionModel / GetRenditionDownloadUrlResponse | `FileSizeBytes` (matches spec here) |
| AbortAssetMultipartUploadResponse | exposes domain `AssetStatus` enum → serialized as int (internal leak) |
| BulkConfirmAssetUploadResponse | missing `skipped` array; per-item failure uses `AssetId` where envelope mandates `name` |
| BulkConfirmAssetUploadSucceededModel | uses `Id` (correct) — inconsistent with sibling failure model's `AssetId` |

**Cross-cutting:**
- **Identifier/size naming is inconsistent** across the surface: `sizeBytes` (detail) vs `fileSizeBytes` (summary, download) — violates ADR-012 response-identifier consistency. Pick one (`sizeBytes` per the detail spec).
- **`TenantId` leakage** in the detail response (multi-tenancy boundary value; should never round-trip to clients).
- Missing metadata: detail response is otherwise complete; no missing timestamps/ids beyond the size-naming issue.

---

## 9. Domain Events

19 domain events, all registered in `Asset`'s `When<>` block. Publisher = `Asset` aggregate.

**Projection coverage gap (verified against both projectors):**

| Domain event | Summary proj. | Detail proj. | Consequence |
|---|---|---|---|
| `AssetInfectionDetected` | ✖ | ✖ | infected+S3-deleted asset shows `Validating` forever (§12 C-3) |
| `AssetReprocessingRequested` | ✖ | ✖ | read model stays `Active` + stale renditions during reprocess |
| `AssetPromotedToVersionArtifact` | ✖ | ✖ | read model shows `Active`/`Archived`, not `VersionArtifact` |
| `AssetVersionArtifactReleased` | ✖ | ✖ | release invisible to read model |
| all other 15 events | ✔ | ✔ | correct |

Other domain-event notes:
- **Timing correct** except `AssetInfectionDetected` (wall-clock, §2 A-D2).
- **Payload completeness:** `AssetProcessingCompleted.Status` is a `ProcessingStatus`, not `AssetStatus` — this becomes a leak when mapped (§10 F-P2). `AssetAttachedToMediaItem` carries `IsPrimary` but the integration event drops it.
- **No duplicate events.** `AssetValidationFailed` intentionally distinct from `AssetProcessingFailed` (mapper unifies them downstream).

---

## 10. Integration Events

### Published (mapper `AssetIntegrationEventMapper.cs`)

All 11 spec-listed mappings are present; `AssetReprocessingRequested → AssetUploadConfirmedIntegrationEvent` is an extra (S12) mapping not in the spec table. Each event carries `TenantId` + `EventVersion`; no event declares its own message/idempotency id (delegated to the platform envelope — unverified).

| Issue | Severity | Detail |
|---|---|---|
| F-P2 | Medium | `AssetProcessingCompletedIntegrationEvent.Status` (and `…TimeoutRecovered.Status`) carry `ProcessingStatus` (`"Transcoded"`/`"Validated"`), while the sibling `…Failed.Status` carries `AssetStatus`. Same-named field, two enums; consumers expecting `"Active"` get `"Transcoded"`. |
| F-P3 | Med/High | Document fast-exit (`ActivateDocumentAsset`) publishes `media.asset.processing-completed`, but context-overview says this event fires "only when Processing capability is present." Billing consumes it → potential mis-billing for documents. |
| F-P4 | Medium | `MediaItemId?` dropped from processing-completed/-failed/-timeout-recovered events (present on the domain events); `Archived`/`Deleted` carry it — inconsistent, forces downstream correlation lookups. |
| F-P5 | Low/Med | No integration event for `AssetDetachedFromMediaItem` or `AssetTagged`, though Search consumes `attached` — stale associations/tags downstream. |
| F-P6 | Low | `AssetInfectionDetectedIntegrationEvent.OccurredAt` inherits the wall-clock timestamp (§2 A-D2). |
| F-P7 | Low | context-overview documents stale event shapes (missing `EventVersion`, wrong field lists) that disagree with both the code and `asset.write-model.md`. |

### Consumed (12 handlers + 2 reference projectors)

| Issue | Severity | Detail |
|---|---|---|
| F-C1 | High | Command-dispatching consumers (`ProcessingJobStarted/Completed/Failed/ScanResult/Bypassed`, `AssetAssignedToRole`) do `return SendAsync(cmd)` **without inspecting the `Result`**. Since commands return failed `Result`s (not throws), an out-of-order or genuinely failed delivery is ACKed and lost — asset stuck, no DLQ, real failures indistinguishable from benign duplicates. |
| F-C2 | High | `MediaItemApprovedEventHandler` / `MediaItemVersionPurgedEventHandler` wrap each asset in `catch (Exception){ log }`. A transient fault (DynamoDB throttle, concurrency) skips promotion/release permanently → an approved-version asset left unprotected is then **deletable** (defeats write-model invariant), or a purge leaves an asset stuck `VersionArtifact`. |
| F-C4 | Med | Every consumer sources `TenantId` from the payload body (`TenantId.From(e.TenantId)`); the `IMessageHandlingContext` (SNS message attribute) is unused — violates the "never from payload body" convention the projectors also rely on. |
| F-C5 | Med | `ProcessingJobCompletedEventHandler` maps only `Width/Height/Duration/Format/ExifData` into `AssetMetadata`, silently dropping `PageCount`, all audio/video fields, `DpiX/Y`, `ColorSpace`, `BitDepth`, `Archive`. Technical metadata is permanently lost. |
| F-C6 | Med | Same handler: `ExifData = e.Metadata.ExifData` not coalesced; a null from Processing violates the `required, never-null` contract → NRE risk in consumers. |
| F-C7 | Low | `ProcessingJobFailedEventHandler` uses unguarded `Enum.Parse<FailureCategory>` (poison on unknown value) where the scan-result handler uses `TryParse` — align. |

### Write-side reference projectors

| Issue | Severity | Detail |
|---|---|---|
| F-R1 | High | `MediaItemCapabilityReferenceProjector`: `MediaItemArchived` before `MediaItemCreated` is dropped (`current is null → MissingCurrent`), then `Created` upserts `IsArchived=false` → **archived MediaItem shows as not-archived forever** → uploads admitted into archived items. |
| F-R2 | High | Same projector mixes version domains: create path watermarks with `EventVersion` (small int), archive path with `ArchivedAt.UtcTicks` (~6e17). The monotonic guard is meaningless across event types; a redelivered `Created` can resurrect a non-archived state. |
| F-R3 | Med/High | `AssetProfileDefaultReferenceProjector` gates a key shared by many profiles `(TenantId, AssetId)` on each profile's own `EventVersion`. Cross-source version comparison can drop a legitimate add/remove → asset wrongly deletable (published default) or wrongly delete-blocked (stale default). |
| F-R5 | Med | Upload-time guards (existence/archive/max-size/capability) read these async reference models → stale-read window; F-R1/F-R2 widen it into permanent inconsistency. Confirm-time re-check recommended. |

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| Delete semantics | Soft delete; "S3 object retained" (`asset.write-model.md:155`) | Hard-deletes original + renditions (`DeleteAssetHandler:56-57`) | High | Decide soft vs hard; align aggregate doc, spec, handler, integration event |
| Delete ordering | AM-7: guard → event → S3 (`asset.scenarios.md:494-497`) | S3 deletion **before** aggregate guard (`DeleteAssetHandler:57-59`) | Critical | Guard first, S3 after success |
| Ownership guard (PERM-1) | All Asset write/read commands enforce `actor.Id == OwnerId` (`security-scenarios.md:67`) | Not enforced anywhere; commands lack ActorId | Critical | Thread ActorId, enforce, emit 403 |
| Infection projection | Both projectors UPDATE → `ContainsVirus` (`asset.read-model.md:73,100`) | Neither projector handles `AssetInfectionDetected` | Critical | Add handlers to both projectors |
| Version-artifact projection | status reflects `VersionArtifact` | Promote/Release not projected | High | Add projector handlers |
| Standalone max size | `StandaloneMaxFileSizeBytes` enforced (`asset.write-model.md:230-232`) | Config key absent; no ceiling for standalone | High | Add option + guard |
| Role assignment | Assigned asset locked from delete; `IsAssigned()` (`asset.write-model.md:28`) | Item-scoped uploads never get RoleName → never "assigned" | High | Allow role-fill when MediaItemId already set |
| Bulk-initiate endpoint | `POST /v1/assets/uploads/bulk` fully specified | Not implemented | High | Implement or formally defer |
| Download not-downloadable | 409 `AssetNotDownloadable` (`asset.api.md:546-556`) | Returns 500 (error mapper flattens) | High | Map to 409 |
| Bulk envelope | `succeeded/failed/skipped`, 201/202, `name` (`bulk-operations.md`) | Missing `skipped`, 422 branch, `AssetId` not `name` | Medium | Align to shared envelope |
| Error contract | RFC 9457 + `errorCode` extension; catalog codes | Generic `AddError(message)`, no `errorCode`; generic `InvalidOperation` | Medium | Emit `errorCode`; use coded errors |
| Multipart part-URL TTL | 1 hour (`asset.scenarios.md:319`) | 15 min (shared single-PUT TTL) | Medium | Separate `MultipartPartUrlExpiryMinutes` |
| FailAssetProcessing states | Validating/Processing only (`asset.write-model.md:23`) | Also accepts Pending (UploadExpired) | Medium | Reconcile spec/code |
| ProcessingCompleted `Status` | Asset status | Carries `ProcessingStatus` | Medium | Publish `AssetStatus`; add explicit ProcessingStatus field |
| ProcessingCompleted event shape | context-overview: `(…, RenditionStorageKeys, CompletedAt)` no `EventVersion` | Richer contract with `EventVersion` | Low (doc) | Reconcile the two spec docs to code |
| ConfirmAssetUpload target | doc-comment "→ Active" | Actually → Validating | Low | Fix doc |
| Validation-passed read status | read-model table "→ Processing or Active" | Aggregate keeps `Validating` (correct) | Low (doc) | Fix spec table |
| Standalone quota (A-2 scenario) | scenario says "quota still applies" | S12: standalone quota-exempt (correct) | Low (doc) | Update stale scenario |

---

## 12. Bugs

### Critical

**C-1 — `DeleteAsset` destroys S3 objects before the domain guard runs (irreversible data loss).**
`DeleteAssetHandler.cs:56-63`. `s3InspectionService.DeleteObjectsAsync(...)` executes at line 57; `asset.Delete(...)` (which holds the `VersionArtifact`/assigned/status guards, `Asset.cs:311-329`) runs at line 59. For any asset whose `Delete()` guard fails — a `VersionArtifact` (approved-version snapshot), an assigned `Active`/`Archived` asset, or any of `Pending/Validating/Processing/ContainsVirus/MultipartAborted` — the original + all renditions are already gone, the command returns an error, and the aggregate is left believing its objects exist.
*Why it's a problem:* destroys regulated, version-pinned binaries with no domain record; the profile-default guard is correctly placed before S3 but the aggregate guard is not. *Impact:* permanent data loss + read/download 403/404 for a still-referenced asset. *Recommendation:* call `asset.Delete(...)` first; perform S3 deletion only on success, before `SaveAsync`.

**C-2 — No ownership authorization on any endpoint or handler (intra-tenant data exfiltration + tampering).**
Verified: zero auth attributes across the module; mutating commands (`ArchiveAssetCommand`, `TagAssetCommand`, `DeleteAssetCommand`) carry no ActorId; read handlers (`GetAssetByIdHandler`, `GetAssetDownloadUrlHandler`, `ListAssetsByMediaItemHandler`) apply no owner scoping. `security-scenarios.md:67` and `asset.api.md` require `actor.Id == asset.OwnerId` on writes and reads. *Impact:* any authenticated tenant user can archive, tag, hard-delete (with C-1, destroy S3), read, list and **download** (working presigned S3 GET) any other owner's asset. *Recommendation:* thread `ActorId` from `IExecutionContext` into every command; enforce `actor.Id == OwnerId` in handlers (System-dispatched commands exempt); return `DomainError.Forbidden` → 403; enforce owner scoping in query handlers before minting URLs.

**C-3 — `AssetInfectionDetected` is never projected (infected assets appear healthy/in-progress).**
Verified: neither `AssetSummaryProjector` nor `AssetDetailProjector` implements `IProjectionHandler<AssetInfectionDetected,…>`, contradicting `asset.read-model.md:73,100`. The event is terminal and the S3 object is hard-deleted. *Impact:* `GET /v1/assets/{id}` and list report a malware-positive, deleted file as `Validating` indefinitely — an audit/compliance-integrity defect for a regulated-records platform. *Recommendation:* add `AssetInfectionDetected` handlers to both projectors (`Status = ContainsVirus`, `UpdatedAt`, `ProjectedVersion`).

### High

**H-1 — Item-scoped uploads can never be assigned a `RoleName`; delete-lock invariant silently disabled.**
Verified across `Asset.cs:205-214`, `AttachAssetToMediaItemHandler:25`, `ApplyAssetAssignmentHandler:61`. `AttachToMediaItem` hard-guards `MediaItemId == null`; `ApplyAssetAssignment` only attaches when `!MediaItemId.HasValue`. An asset uploaded with a `MediaItemId` sets it at creation with `RoleName = null`, so `IsAssigned()` is `false` forever → `Delete()`'s "assigned assets locked" guard never fires and the asset/Catalog role state diverge; `DetachFromMediaItem` (needs `IsAssigned()`) always fails. *Recommendation:* allow role-fill when `MediaItemId` already equals the target, or split "bind MediaItem" from "assign role."

**H-2 — Integration consumers ignore command `Result`s → silent loss, no DLQ (F-C1).** See §10. Out-of-order `ProcessingJobStarted/…` before the aggregate is materialized returns a swallowed `ResourceNotFound`; the asset never advances and the message is ACKed.

**H-3 — Promote/Release consumers swallow per-asset exceptions → version protection not applied (F-C2).** See §10. Under a transient fault an approved-version asset is left unprotected and thus deletable.

**H-4 — Capability reference projector loses archives on reorder / mixes version domains (F-R1, F-R2).** See §10. Uploads admitted into archived MediaItems.

**H-5 — `CompleteMultipartUpload` mutates S3 before appending the event → permanent wedge on retry.**
`CompleteMultipartUploadHandler.cs:46-55`. `CompleteAsync` runs before `SaveAsync`; if `SaveAsync` fails, the object is assembled but the asset stays `Pending`. Retry re-invokes `CompleteAsync` on a consumed `UploadId` → `NoSuchUpload` → throws forever; abort also fails; the single-part auto-confirm fallback can't rescue a `Pending` multipart asset. *Recommendation:* make completion idempotent (treat `NoSuchUpload`/already-completed as success, then append the event), or HEAD-verify object existence before re-completing.

**H-6 — Download "not downloadable" returns 500 instead of 409.**
`GetAssetDownloadUrlHandler.cs:31` / `GetRenditionDownloadUrlHandler.cs:27` return a generic `Failed(...)`; the read base maps everything except NotFound/Forbidden to 500. A download of a `Processing`/`Pending`/`Deleted`/`ProcessingFailed` asset returns 500 where the spec requires 409 `AssetNotDownloadable`. *Recommendation:* dedicated conflict error code → 409.

**H-7 — Standalone uploads have no maximum-size ceiling.**
`InitiateAssetUploadHandler`/`InitiateAssetMultipartUploadHandler` nest the size check inside `if (MediaItemId.HasValue)`. The spec's `StandaloneMaxFileSizeBytes` config key does not exist anywhere. Combined with S12 standalone quota-exemption, there is no upper bound on standalone ingest. *Recommendation:* add the option and enforce it for `MediaItemId == null`.

**H-8 — Soft-deleted assets leak into queries.**
`GetAssetByIdHandler` returns `Deleted` assets (200 + `DeletedAt`); `ListAssetsByMediaItemQuery.Matches` returns `Deleted` rows when no status filter is supplied. Spec: `Deleted` excluded from all queries. *Recommendation:* 404 on `Deleted` in GetById; exclude `Deleted` from list unless explicitly requested.

**H-9 — `AssetSummaryReadModel.FileSizeBytes` is never populated.**
`AssetSummaryProjector` constructs the row with `null` size on both initiate paths and never sets it later. `GET /v1/assets` always returns `fileSizeBytes: null`. *Recommendation:* pass `e.FileSizeBytes` in both INSERTs.

**H-10 — `BillingAcl` quota check does not account for existing usage and mutates the options singleton.**
`BillingAcl.cs:18-23` compares a single file's size against `MaxTotalBytes` (never the owner's accumulated usage) and `Bind`s onto the DI singleton per call. Quota is effectively never enforced until one file exceeds the whole allowance. *Recommendation:* query real per-owner consumption; stop mutating the singleton.

### Medium

- **M-1** `RecordValidationResultHandler:38-41` deletes the S3 object on `VirusDetected` **before** the aggregate's `Validating` guard, and hard-deletes where AM-5 mandates quarantine-bucket move (forensic retention). A spurious/out-of-order `VirusDetected` destroys a live object with no state change.
- **M-2** Bulk confirm omits the content-type guard that single confirm enforces (`BulkConfirmAssetUploadHandler:132-192` vs `ConfirmAssetUploadHandler:65-82`).
- **M-3** Bulk endpoint does not enforce the 50-item `MaxAssetsPerRequest` cap (`BulkOperationsOptions` defined but unreferenced) → unbounded batch → Lambda timeout/throttle risk.
- **M-4** Bulk concurrency retry catches only `DomainException` and re-saves the same in-memory aggregate without reloading — platform concurrency exceptions escape and fail the whole batch; genuine version conflicts can't be resolved by retry.
- **M-5** `ProcessingJobCompletedEventHandler` drops most `AssetMetadata` fields (F-C5) and doesn't coalesce `ExifData` (F-C6).
- **M-6** `ApplyAssetAssignment`: the "charge deferred quota at assign" guarantee isn't implemented (`CheckQuotaAsync` only reads/compares, never charges); `QuotaCheckResult.Unavailable` is treated as `Exceeded` and silently skipped (asset left unprocessed, no retry); `IsPrimary` hardcoded `true`.
- **M-7** No request validators anywhere → malformed ids/tags/omitted fields → 500 instead of 400/422 (`TagAssetRequest` NRE; `MediaItemId.From` FormatException).
- **M-8** `AssetProcessingCompletedIntegrationEvent.Status` leaks `ProcessingStatus`; document fast-exit emits `processing-completed` → mis-billing risk (F-P2/F-P3); `MediaItemId` dropped from processing events (F-P4).
- **M-9** `GetAssetById` response leaks `TenantId`; size-field naming inconsistent across DTOs (`sizeBytes` vs `fileSizeBytes`).
- **M-10** `InitiateMultipartUpload` leaks an orphaned S3 multipart session if `GeneratePartUrlsAsync` throws (compensation only guards `SaveAsync`); 15-minute part-URL TTL too short for multi-GB uploads.
- **M-11** Invalid `status` query filter is silently ignored (returns all) instead of 400; parse is case-sensitive and accepts numeric strings.
- **M-12** `GetRenditionDownloadUrl` does not check retrievability (can presign a cold-storage object).

### Low

- **L-1** `AssetInfectionDetected` uses `DateTimeOffset.UtcNow` (§2 A-D2).
- **L-2** `AbortMultipartUpload` has the same S3-before-event retry wedge as H-5 (lower impact — parts already released).
- **L-3** `ProcessingJobFailedEventHandler` unguarded `Enum.Parse` (poison risk).
- **L-4** `AbortAssetMultipartUploadResponse` leaks the `AssetStatus` enum as an int; confirm/abort return a body where spec says none.
- **L-5** `S3PresignedGetUrlService:27` doesn't forward the `CancellationToken`.
- **L-6** Bulk all-failed returns 422 (spec: 202); response lacks `skipped`; per-item failure uses `AssetId` not `name`.
- **L-7** Endpoint doc-comments cite stale routes; `ConfirmAssetUpload` doc says "→ Active" (actually Validating) and claims idempotent-409 that the code doesn't provide.
- **L-8** No lower/zero-bound validation on `FileSizeBytes` (0-byte multipart → `partCount = 0`); multipart result doesn't return the chosen part size.

---

## 13. Design Flaws

1. **Non-transactional dual writes between the event store and S3 are pervasive and inconsistently ordered.** `DeleteAsset` and virus-handling delete S3 before the guard; multipart complete/abort mutate S3 before the event; multipart initiate emits the event after S3 with partial compensation. There is no outbox/saga to make the object-store side effect atomic with the event append. For a regulated-records system this is the single biggest architectural weakness — every one of these is a partial-failure window. *Recommendation:* adopt a consistent rule (domain guard → event persisted → side effect, with idempotent/compensating object-store operations driven off the event), or an outbox pattern for S3 lifecycle actions.

2. **Integration consumers treat "domain failure" and "duplicate delivery" identically by ignoring the `Result`.** This yields accidental idempotency that also erases genuine failures with no DLQ/observability (F-C1/F-C2). The correct design distinguishes idempotent no-ops (ACK) from retryable failures (throw → SQS retry/DLQ), and reloads the aggregate before concurrency retries.

3. **The write-side role model is split between two representations that can disagree.** `RoleName`/`IsAssigned()` on the aggregate is only reachable via the standalone→assign path; item-scoped uploads live entirely in Catalog's view (H-1). Ownership of "is this asset filling a role" is ambiguous between contexts.

4. **Reference-model watermarks mix version domains and gate multi-source keys on single-source versions** (F-R2/F-R3), defeating the very dedup/monotonicity guarantees they exist to provide.

5. **Overloaded events leak internal phases across the BC boundary.** `AssetProcessingCompleted` serves both pipeline completion and document fast-exit, and its `Status` field carries `ProcessingStatus`; downstream Billing must reverse-engineer intent (F-P2/F-P3).

6. **The error contract is bypassed at the domain layer.** Returning generic `InvalidOperation` (422) throughout collapses the catalog's 409/422 distinction (retry-ability) and prevents machine-discriminable `errorCode`.

---

## 14. Design Gaps

- **No authorization layer** (endpoints or handlers) — the largest gap.
- **No request-validation layer** (no FluentValidation), so the API cannot return 400/422 for malformed input.
- **No RFC 9457 problem-details emission** with `errorCode` from the module's error helpers.
- **No compensation/timeout for S12 reprocessing** (L-1 lifecycle) — stuck-state risk.
- **No DLQ/dead-letter handling or observability** around swallowed consumer failures.
- **No real quota accounting** (usage-aware) — the ACL is a placeholder.
- **No optimistic-concurrency-aware retry** in consumers (reload-before-retry).
- **No confirm-time/assign-time re-validation** of archive/capability drift (reference-model staleness).
- **Missing projections** for infection, promote/release, reprocessing (§9).
- **Missing observability** for the storage-tier lifecycle (acknowledged as derived-on-read, but no metric on restore-required downloads).
- **Missing `StandaloneMaxFileSizeBytes`** configuration and enforcement.
- **No query for standalone assets** (list requires `mediaItemId`).

---

## 15. Missing Features

- **`POST /v1/assets/uploads/bulk` (bulk initiate)** — fully specified in `asset.api.md` (partial-success envelope, aggregate quota, per-item errors); no command/endpoint/request/response exists. Only bulk-confirm is implemented.
- **Ownership enforcement** on every write and read (commands lack ActorId).
- **`AssetInfectionDetected`, `AssetPromotedToVersionArtifact`, `AssetVersionArtifactReleased`, `AssetReprocessingRequested` projector handlers.**
- **Integration events** for `AssetDetachedFromMediaItem` and `AssetTagged` (Search consumes attach but never learns of detach/tag changes).
- **Content-type guard** in the bulk-confirm path.
- **`skipped` array** in the bulk-confirm response envelope.
- **Batch-size (50) enforcement** in the bulk endpoint.
- **Reprocessing timeout saga / compensation.**
- **Quarantine-bucket move** for infected objects (currently hard-deleted).
- **Coded domain errors** (`AssetNotActive`, `AssetAlreadyAttached`→409, `AssetNotArchivable`, `AssetNotValidating`→409, `AssetTooLarge`, `StorageQuotaExceeded`, `S3ObjectNotFound`, `MediaItemArchived`) mapped to catalog status codes.
- **Standalone-asset listing query.**

---

## 16. Recommendations (prioritised)

### 1 — Correctness
- **R1 (Critical).** Reorder `DeleteAssetHandler`: domain guard (`asset.Delete`) → S3 deletion on success → `SaveAsync` (C-1). Apply the same "guard before side effect" rule to the virus path (M-1) and reconcile soft-vs-hard delete semantics (L-3/§11).
- **R2 (High).** Make consumers observe command `Result`s: ACK idempotent no-ops, throw retryable failures to reach SQS retry/DLQ; reload aggregates before concurrency retry (F-C1/F-C2/M-4).
- **R3 (High).** Make multipart complete/abort idempotent (treat `NoSuchUpload`/already-completed as success, then append the event) (H-5/L-2).

### 2 — Data Integrity
- **R4 (Critical).** Add `AssetInfectionDetected`, `AssetPromotedToVersionArtifact`, `AssetVersionArtifactReleased`, `AssetReprocessingRequested` handlers to both projectors; populate `FileSizeBytes` in the summary projector; exclude `Deleted` from queries (C-3/H-8/H-9/§9).
- **R5 (High).** Fix the capability reference projector: single version domain, archive-tombstone that survives reorder, read-and-guard on create; drop cross-source version gating on `asset-profile-default-refs` (F-R1/F-R2/F-R3).
- **R6 (High).** Fix the role model so item-scoped uploads receive a `RoleName` (restore the delete-lock invariant) (H-1).

### 3 — Security
- **R7 (Critical).** Implement PERM-1: thread `ActorId` through all commands; enforce `actor.Id == OwnerId` in write handlers and query handlers; return 403; keep System-dispatched commands exempt (C-2). Enforce `actor_type == System` on `FailAssetProcessing`/`RecordValidationResult` (L-3 §4).
- **R8 (High).** Add the `StandaloneMaxFileSizeBytes` ceiling for standalone uploads (H-7); move infected objects to quarantine rather than deleting (M-1).

### 4 — Domain Modelling
- **R9 (Medium).** Return catalog-coded `DomainError`s (409 vs 422) from aggregate guards; stop emitting `ProcessingStatus` in integration `Status`; add `MediaItemId` to processing integration events; use `recordedAt` in `AssetInfectionDetected` (A-D2/A-D4/F-P2/F-P4).
- **R10 (Medium).** Reconcile `FailProcessing`'s `Pending`/`UploadExpired` acceptance with the invariant table; either use or remove `FailureCategory.ValidationError` (A-D3).

### 5 — Lifecycle
- **R11 (High).** Add a reprocessing timeout/compensation saga so re-driven `Validating`/`Processing` cannot hang forever (L-1).
- **R12 (Low).** Provide a removal/cleanup path for `ContainsVirus`/`MultipartAborted` dead-end rows (L-2).

### 6 — API
- **R13 (High).** Emit RFC 9457 problem-details with `errorCode`; stop flattening domain errors to 500 on the read side; map not-downloadable to 409 (H-6/§6).
- **R14 (High).** Implement (or formally defer) `POST /v1/assets/uploads/bulk` (§15).
- **R15 (Medium).** Add FastEndpoints validators (id well-formedness, tag rules, `pageSize` cap, 50-item batch cap, positive size); normalize `mediaItemId` naming; drop `TenantId` from responses; unify `sizeBytes` naming; align the bulk envelope (`skipped`, 202, `name`) (M-3/M-7/M-9/L-6).

### 7 — Events
- **R16 (Medium).** Map the full `AssetMetadata` field set in `ProcessingJobCompletedEventHandler` and coalesce `ExifData`; add detach/tag integration events if Search needs them (F-C5/F-C6/F-P5).

### 8 — Maintainability
- **R17 (Low).** Reconcile context-overview event shapes with code before the wiki publish; fix stale doc-comments/routes; align the read-model spec's `AssetValidationPassed` row (F-P7/L-7).

### 9 — Performance
- **R18 (Medium).** Separate `MultipartPartUrlExpiryMinutes` (≈60) from the single-PUT TTL; widen the multipart-initiate compensation window to abort orphaned sessions (M-10).

### 10 — Scalability
- **R19 (High).** Replace the placeholder `BillingAcl` with usage-aware quota accounting; stop mutating the options singleton under concurrency (H-10).
- **R20 (Medium).** Add a bounded retry / distinct retryable error for the upload-time capability-index race so legitimate uploads immediately after item creation don't 404 (F-R5/upload M-8).

---

### Top 5 before production
1. **C-2 / R7** — ownership authorization (nothing today prevents cross-owner read/download/mutation within a tenant).
2. **C-1 / R1** — delete-before-guard S3 data loss on regulated records.
3. **C-3 / R4** — infection (and version-artifact/reprocess) projection gaps.
4. **H-2 / R2** & **H-3** — consumers swallowing failures / no DLQ; version-artifact protection not applied.
5. **H-1 / R6** — item-scoped assets never assigned a role → delete-lock bypass.
