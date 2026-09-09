# Processing — Code Defects and Open Decisions

_magiq-media · 2026-09-08 · Chase Ramone_

**This is a standalone report, not a `review-cycle` review.** It has no `MM-` id and is not indexed in
`reviews/README.md`. If any block of it is taken forward, that block becomes a review in its own
workstream folder and this file becomes its evidence.

---

## What this is

`processing-spec-drift-2026-09-08.md` found 26 items. **The 19 "spec wrong, code right" items are
closed** — the seven files under `docs/spec/contexts/Processing/` were rewritten on 2026-09-08 to the
RecordType layout, with every historical correction block stripped and the tree treated as a first draft.
`shared/error-catalog.md § Processing` was corrected in the same pass.

**This file carries what is left: the places the code is wrong, and the two questions that need an answer
before anything is written.** Every one is marked in the rewritten spec with a `⚠` block, so the spec no
longer overstates the system while these are open. The **Marked in spec** row on each finding is where to
look, and where to delete from once it is fixed.

| | Count |
|---|---:|
| Code defects | 8 |
| Open decisions | 2 |
| **High** | 2 |

Two findings are new — they surfaced during the rewrite rather than in the original sweep, and are
numbered on from the drift report: **PROC-27** and **PROC-28**. **PROC-29** was recorded as "verified
correct" there, because the spec described it accurately; it is carried here because an accurate
description of a gap is still a gap.

---

## 1. Code defects

### 1.1 The pipeline

#### PROC-1 · **High** · `AssetProcessingWorker` has no trigger

`IAssetProcessingWorker.ProcessAsync` has **no caller in the solution**, and no queue delivers
`media.asset.validation-passed` to the `ProcessingWorker` host — `media-processing` allowlists
`media.asset.upload-confirmed` alone, and `ProcessingRegistrations` registers one message handler. So the
rendition and metadata half of the pipeline does not run.

| | |
|---|---|
| **Effect** | `CompleteProcessingJobCommand` is never dispatched. `ProcessingJob` cannot reach `Succeeded` in any environment; `ProcessingJobSucceeded` and `ProcessingJobTimeoutRecovered` are unreachable. Every capable asset stalls at `Running` until the 240-minute budget expires and the scanner fails it — so **the full pipeline currently terminates in a timeout, always**. The bypass path is unaffected: the saga dispatches it |
| **Fix** | Two changes, and doing only the first makes things worse: (a) subscribe the `ProcessingWorker` host to `media.asset.validation-passed` and route it to `ProcessAsync`; (b) implement `RunProcessingPipelineAsync`, which today throws `NotImplementedException`. Wiring (a) alone converts a silent stall into a `ProcessingError` on every asset |
| **Decide first** | Whether `AssetProcessingWorker` is built or deleted. If renditions are not near-term, deleting the worker and its two unreachable command dispatches is honest; the spec would then say the full-pipeline exit is unbuilt rather than describing a path with a hole in it |
| **Code** | `modules/Processing/Processing.WriteModel.Infrastructure/Workers/AssetProcessingWorker.cs:113` (the throw) · `hosts/ProcessingWorker/ProcessingRegistrations.cs:50` · `cdk-magiq-media/lib/constructs/messaging/sqs-queues.ts:178` |
| **Tests** | None. There is no test of `AssetProcessingWorker` at all |
| **Marked in spec** | `context-overview.md:74` (§ Service Boundaries) · `context-overview.md:129`, `:156` · `processingjob.write-model.md:49` (§ Status transitions) · `processingjob.api.md:46` · `processingjob.scenarios.md:70`, `:87`, `:218` |

#### PROC-2 · **High** · The validation-timeout path records `ProcessingTimeout`

`AssetIngestionTimeoutScanner.CompensateValidationTimeoutAsync` makes two dispatches:
`FailAssetProcessingCommand(ValidationTimeout)` against **Asset**, then
`FailProcessingJobCommand(ProcessingTimeout)` against **ProcessingJob**. The second should carry
`ValidationTimeout`.

The saga's own compensation does parse `ValidationTimeout` correctly, but it can only run after the asset
event crosses SNS and `media-sagas`. The scanner's second dispatch is in-process and lands first, so
`Fail` finds the job already `Failed`, returns idempotent success, and **keeps the first category**.

| | |
|---|---|
| **Effect** | `ProcessingJobFailureCategory.ValidationTimeout` is never written to a job. Because `Complete()` treats `ProcessingTimeout` as the one reversible category, a validation-timed-out job is also **wrongly eligible for timeout recovery** — which is verbatim the defect X-11.5 was raised to close. The enum member landed; the writer did not change |
| **Fix** | One line: `ProcessingJobFailureCategory.ValidationTimeout` at `AssetIngestionTimeoutScanner.cs:184`, and the reason string already says "validation TTL" |
| **Sequencing** | **Fix this before PROC-1.** It is masked today only because no late success can arrive; it stops being masked the moment the pipeline runs |
| **Code** | `hosts/TimeoutScanner/Scanner/AssetIngestionTimeoutScanner.cs:184` |
| **Tests** | None cover the validation-timeout path end to end. Add one asserting the job's category after both dispatches settle |
| **Marked in spec** | `processingjob.write-model.md:98` (§ Value Objects) · `assetingestionsaga.md:143` (§ The scanner) · `processingjob.api.md:51` · `processingjob.scenarios.md:216` |

### 1.2 Idempotency

#### PROC-3 · Medium · Job creation is not idempotent

`AssetUploadConfirmedEventHandler` mints a fresh `ProcessingJobId` on every delivery and
`CreateProcessingJobCommandHandler` creates unconditionally. `IProcessingJobRepository` has
`GetByIdAsync` and `SaveAsync` and nothing else.

| | |
|---|---|
| **Effect** | A duplicate SQS delivery of `AssetUploadConfirmedIntegrationEvent` creates a **second `ProcessingJob` for the same asset**, overwrites the `media-processing-asset-index` row so the first job becomes unreachable to compensation, and emits a second saga-creation event that the saga's existence guard absorbs |
| **Fix** | Add `GetByAssetIdAsync(tenantId, assetId, ct)` to `IProcessingJobRepository`, and have the handler return `Result.Success(Unit.Value)` when a job already exists. The `JobId` must stay on the command — it is what lets the handler thread the id into `AssetValidationWorker` without waiting on a projection |
| **Watch** | The lookup wants the write side or the reference model, not a read model, or the guard inherits the projection lag it was added to avoid |
| **Code** | `modules/Processing/Processing.WriteModel/IntegrationEvents/Consuming/Handlers/AssetUploadConfirmedEventHandler.cs:33` · `.../Commands/CreateProcessingJob/CreateProcessingJobCommandHandler.cs` · `.../Repositories/IProcessingJobRepository.cs` |
| **Marked in spec** | `processingjob.write-model.md:233` (§ Handler-side Pre-conditions) · `processingjob.scenarios.md:90` |

### 1.3 Projections

#### PROC-4 · Medium · `ProcessingJobBypassed` is projected by nothing

None of the three projectors handles it — `ProcessingJobSummaryProjector`, `ProcessingJobDetailProjector`
and `AssetJobIndexProjector`. `AssetJobIndexProjector` also omits `ProcessingJobTimeoutRecovered`, and
writes `Running` on both terminal events it *does* handle.

| | |
|---|---|
| **Effect** | A bypassed job reads `Queued` in `media-processing-job`, `media-processing-jobs` and `media-processing-asset-index` **permanently**. `Bypassed` is on the enum and both read models serialise it, so the status is in the published contract and unobservable in practice. On the index, `Status` never reaches a terminal value for any job |
| **Fix** | Add the `ProcessingJobBypassed` handler to all three, and `ProcessingJobTimeoutRecovered` to the index. Separately, decide whether the index's `Status` and `StartedAt` should be correct or removed — nothing reads either today, and a field named `Status`, typed `ProcessingJobStatus` and sitting beside a `JobId` is a trap for the next reader whichever way it goes |
| **Code** | `modules/Processing/Processing.ReadModel/Projectors/*.cs` · `modules/Processing/Processing.WriteModel/Indexes/Projectors/AssetJobIndexProjector.cs` |
| **Marked in spec** | `processingjob.read-model.md:118` (§ Projection Handlers) · `processingjob.write-model.md:309` (§ Write-Side Reference Model) · `processingjob.api.md:93` · `processingjob.scenarios.md:166` |

#### PROC-27 · Medium · Neither read model projects `FailureCategory` **(new)**

`ProcessingJobDetailReadModel` carries `FailureReason` and no category; the summary model carries
`StatusText`, which is set to the reason string on failure.

| | |
|---|---|
| **Effect** | `ProcessingTimeout` is the only reversible failure, so a client polling a job must not treat `Failed` as final without checking the category — **and the read side gives it no way to check.** A client sees `Failed` plus free text and cannot tell a recoverable timeout from a terminal `ProcessingError`. The rule the spec states is unachievable through the API it states it for |
| **Fix** | Project `FailureCategory` onto `ProcessingJobDetailReadModel` at minimum, and onto the summary model if job lists are ever exposed. Both projectors already receive it on `ProcessingJobFailed`; `ProcessingJobTimeoutRecovered` must null it alongside `FailureReason` |
| **Note** | Blocked in practice by PROC-29 — there is no read surface for a client to poll yet. Fix it with the read host rather than before it |
| **Code** | `modules/Processing/Processing.ReadModel/ReadModels/ProcessingJobDetailReadModel.cs` · `.../Projectors/ProcessingJobDetailProjector.cs` |
| **Marked in spec** | `processingjob.read-model.md:221` (§ `Failed` is not final, and the read model cannot say so) |

### 1.4 The read path

#### PROC-29 · Medium · Two read models and a GSI are maintained with no reader

`QueryApi.csproj` does not reference Processing and never calls `AddProcessingReadModelQueries()`.
`GetProcessingJobByIdQuery`'s handler is registered only in the `Api` host, which has no Processing
endpoints to invoke it. `ListProcessingJobsForAssetIdQuery` has **no handler class at all**, while its
`AssetByProcessingJobIndex` GSI is maintained on every job event.

| | |
|---|---|
| **Effect** | `media-processing-job`, `media-processing-jobs` and one GSI are written on every event and read by nothing. Write capacity for no reader, and — worse — it reads as working: the query record exists, the schema is registered, the index fills up |
| **Fix** | Either give Processing a read host (`QueryApi` reference + `AddProcessingReadModelQueries()`) **and** write `ListProcessingJobsForAssetIdHandler`, or delete the query, the GSI schema and both projectors. Half of either is what produced the current state |
| **Decide first** | Whether job status is client-visible at all. It is the most pollable thing this context owns, which argues for exposing it — but see PROC-6, because exposing a list against the current partition shape is the case that hurts |
| **Code** | `hosts/QueryApi/QueryApi.csproj` · `hosts/QueryApi/Startup.cs` · `modules/Processing/Processing.ReadModel/Queries/ListProcessingJobsForAssetId/` · `modules/Processing/Processing.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:53` |
| **Marked in spec** | `processingjob.api.md:67`, `:69` (§ Read Endpoints) · `processingjob.read-model.md:147` (§ Query Handlers) |

### 1.5 Errors

#### PROC-28 · Low · No refusal in Processing carries an `errorCode` **(new)**

`error-catalog.md § Processing` named two codes. Neither string exists in `src/`: not-found is a bare
`ResourceNotFound("Processing job not found.")` and all five status refusals are bare
`DomainError.InvalidOperation` carrying free text.

| | |
|---|---|
| **Effect** | Nothing a caller sees is machine-readable. The catalog's head note already covers this — *"still aspirational: every code in the Processing and DocumentSigning sections"* — so this is tracked, not silent |
| **Fix** | The same one-line change to the endpoint base classes that Catalog has. **Blocked by PROC-29**: with no HTTP surface there is nowhere for a coded error to be returned, so this lands with the read host or not at all |
| **Also done** | The catalog previously listed `ProcessingJobAlreadyComplete` (409) for *"result recorded against an already-terminal job"*. **That condition no longer exists** — repeating a transition the job has already made is idempotent success. Replaced 2026-09-08 with `ProcessingJobStatusInvalid` (422), which describes the five refusals that are real |
| **Code** | `modules/Processing/Processing.Domain/Aggregates/ProcessingJob.cs:72,98,141,155,171` · all six command handlers |
| **Marked in spec** | `shared/error-catalog.md:700` · `processingjob.write-model.md:124` (§ Invariants) |

### 1.6 Comments

#### PROC-5 · Low · Six stale or wrong XML doc comments

Code-side only, and each will mislead the next reader of the file before they reach the spec.

| File | Claim | Reality |
|---|---|---|
| `ProcessingJobDetailReadModel.cs:10-12` | table `media-processing-jobs`, PK `TENANT#{TenantId}`, SK `JOB#{JobId}` | table is `media-processing-job`; the keys are neither of those |
| `ProcessingJobDetailReadModel.cs:20` | `// Queued \| Running \| Succeeded \| Failed` | omits `Bypassed` |
| `AssetUploadInitiatedEventHandler.cs` | *"The SQS subscription … is still active in the Processing Lambda (managed via CDK)"* | `media-processing` allowlists upload-confirmed only; this no-op runs in `EventConsumers` |
| `ProcessingWorker/Function.cs:56-57` | `IMediaItemCapabilityService` *"used by `AssetValidationWorker`"* | that worker takes a dispatcher and a logger only |
| `ProcessingJob.cs:14-18` | *"Only created when the … profile has the Processing capability"* | a job is created for every confirmed upload, before capability is known |
| `StartProcessingJobCommandHandler.cs`, `AssetProcessingWorker.cs:70` | Start is dispatched by the worker | the saga dispatches it |

| | |
|---|---|
| **Fix** | A comment sweep. Rides along with any Processing PR; needs no workstream |
| **Marked in spec** | Not marked, deliberately — the spec is now correct on all six points, so a reader of the spec is unaffected |

---

## 2. Open decisions

Both are places where the code and the spec now agree on *what happens* and nobody has decided whether it
is right. Neither is a defect until the question is answered.

### PROC-6 · **The summary table puts every job in one partition per tenant**

`ProcessingJobSummaryReadModel.CreateProjectionKey(tenantId, jobId)` supplies no group key, so
`DefaultProjectionSchema` builds `PK = TENANT#{TenantId}#PROCESSING_JOBS` for every job the tenant has
ever run. The detail table does not have this shape — it passes the `JobId` as the group key, giving
`TENANT#{TenantId}#PROCESSING_JOB#{JobId}`.

| | |
|---|---|
| **The question** | Is a single partition per tenant acceptable for the most write-heavy, most pollable projection in the platform? A large tenant re-ingesting a collection concentrates the whole burst on one key |
| **Option A** | Leave it. Defensible while PROC-29 stands and nothing reads the table — but it is being *written* today regardless of readers |
| **Option B** | Add a group key. Cheapest is the `AssetId`, which matches the one access pattern the query wants and spreads writes per asset. Requires a rebuild, and there is no rebuild verb (see below) |
| **Option C** | Delete the summary table and its GSI, and serve job history from the detail table. Fewest moving parts if job lists are never exposed |
| **Tied to** | PROC-29 — exposing the list is the case that makes this hurt, so decide them together |
| **Also relevant** | There is **no CLI rebuild verb for `ProcessingJob`**, and `media-processing-asset-index` is registered `schemaVersion: null`, which the replay tooling refuses outright. Option B needs that built first |
| **Marked in spec** | `processingjob.read-model.md:47` (§ `media-processing-jobs`) · `:238` (§ Consistency) |

### PROC-16 · **`RenditionResult` carries dimensions that are dropped at every boundary**

```csharp
public sealed record RenditionResult(
    string RenditionType, string StorageKey, string ContentType,
    long FileSizeBytes, int? Width, int? Height);
```

`ProcessingRenditionDto` (the integration event) and `RenditionResultDto` (the read model) both have the
first four members and neither has the last two.

| | |
|---|---|
| **The question** | Are per-rendition dimensions part of the contract or not? Today they are stored in the event stream and observable by nobody |
| **Option A** | Carry them through both DTOs. A thumbnail's dimensions are the kind of thing a UI asks for, and the data is already there |
| **Option B** | Drop them from the value object. `ExtractedMetadata` already carries the *original's* dimensions, which is the more commonly wanted number |
| **Note** | Nothing populates either field today — PROC-1 means no `RenditionResult` has ever been constructed outside tests — so this is free to change now and expensive later |
| **Marked in spec** | `processingjob.write-model.md:114` (§ Value Objects) · referenced from `processingjob.read-model.md` § Read Model Types |

---

## 3. What was changed in the spec

For the record, so a reviewer can tell rewrite from drift.

| File | Lines (was → now) | Substance |
|---|---:|---|
| `context-overview.md` | 284 → 310 | Merged the duplicate *High-Level Event Flows* / *Pipeline Logic* sections; added `ProcessingJobCreated` and `Bypassed` to the published table; all six contracts now carry `EventVersion` and the `Bypassed` contract exists; failure categories corrected; the worker's index lookup removed |
| `processingjob.write-model.md` | 307 → 334 | Stream **discriminator** replaces a prefix that appears nowhere in `src/`; both wrong command signatures fixed; § Invariants and § Methods rebuilt against the real state machine and `Bypass()` added; the reference model's rationale rewritten around compensation |
| `processingjob.api.md` | 141 → 111 | Three overlapping command tables collapsed to one; dispatchers corrected — the saga owns `Start` and `Bypass`; `Result<Unit, IDomainError>`; source line-number citations dropped as rot-prone |
| `processingjob.read-model.md` | 239 → 254 | Both tables' real PK/SK documented, with the platform key rule stated once; `sizeBytes` → `FileSizeBytes`; the phantom `ListProcessingJobsForAssetIdHandler` row removed |
| `processingjob.scenarios.md` | 260 → 228 | The saga state `Complete` — which does not exist — replaced with the correct terminal state per scenario; P-1's upload payload corrected to the real command shape; two of three mermaid diagrams dropped as duplication |
| `sagas/assetingestionsaga.md` | 271 → 272 | § DLQ rewritten: X-11.6 is fixed, exceptions propagate and the DLQ is reachable; the "no test coverage at all" claim corrected |
| `business-scenarios.md` | 26 → 29 | Index only |
| `shared/error-catalog.md § Processing` | — | `ProcessingJobAlreadyComplete` replaced; the absence of any `errorCode` stated |

Every file was checked with `.github/scripts/check-spec-truncation.py` immediately after writing; the
guard passes on all 89 files under `docs/spec/`.

---

## Suggested next steps

1. **PROC-2 first, alone.** One line, and it must land before PROC-1 or the bug it fixes comes back live.
2. **PROC-1 is a decision before it is a task.** Build the pipeline or delete the worker — and until one
   of those happens, the ⚠ markers are what stop the spec from claiming a path that does not run.
3. **PROC-29, PROC-27, PROC-28 and PROC-6 are one workstream**, in that order. They are all the read path,
   and each of the last three is either blocked by or entangled with the first.
4. **PROC-3 and PROC-4 are independent and small.** Either can go into any Processing PR.
5. **PROC-5 is a comment sweep.** No workstream.
