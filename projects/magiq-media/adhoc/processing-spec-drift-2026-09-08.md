# Processing — Spec ↔ Repo Drift Report

_magiq-media · 2026-09-08 · Chase Ramone_

**This is a standalone report, not a `review-cycle` review.** It has no `MM-` id and is not indexed in
`reviews/README.md`. If any block of it is taken forward, that block becomes a review in its own
workstream folder and this file becomes its evidence.

---

## Scope

| | |
|---|---|
| **Spec** | `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\contexts\Processing\` — 7 files, 1,528 lines |
| **Code** | `src\modules\Processing\` — 6 projects, 70 `.cs` files (excl. `obj`/`bin`) |
| **Also read** | `src\hosts\` (ProcessingWorker, SagaOrchestrator, TimeoutScanner, Api, EventConsumers, QueryApi, Projectors.ReadModel), AssetManagement's five `ProcessingJob*EventHandler`s, `cdk-magiq-media` (`sqs-queues.ts`, `media-buckets.ts`), `aspnetcore-platform` projection/schema internals |
| **Aggregate** | `ProcessingJob` — the only one in this context. `AssetIngestionSaga` is included; it is Processing's. |

**Out of scope:** the Asset aggregate's own state machine (AssetManagement's spec), OpenSearch, and the
`media-quarantine` wiring gap, which the spec already records accurately as X-4.7 and which is unchanged.

**Method.** Code first, spec second; every claim below was checked against the source rather than
against a sibling document. Platform behaviour (`DefaultProjectionSchema`, `ProjectionKey`,
`AddProjectionSchema`) was read in `aspnetcore-platform` rather than assumed. CDK filter policies and
environment variables were read in `cdk-magiq-media`, not inferred.

---

## Headline

**26 findings. 8 High.**

| | Count | What it means |
|---|---:|---|
| **Spec wrong, code right** | 19 | Documentation drift. The system behaves correctly. |
| **Code wrong or unspecified behaviour** | 5 | § 1 — PROC-1 through PROC-5. |
| **Undecided / needs a call** | 2 | PROC-6 (summary-table partition shape), PROC-16 (dropped rendition dimensions). |

**The saga file is the best document in the tree and the scenarios file is the worst — the same split
Catalog and Registration showed.** `sagas/assetingestionsaga.md` was written against the code on
2026-08-27 and is accurate line-for-line: the transition table, the guards, the correlation key, the
two-phase clock, the five statuses, the bypass self-closure, the scanner's three passes, the config
section name and its three uncontrolled defaults, and the "no optimistic concurrency" caution all match
what is in the repo today. The one exception is its DLQ section, which is stale in the *unusual*
direction — see PROC-20. `processingjob.scenarios.md` has not been swept since the P-5/P-7 corrections
landed elsewhere on 2026-08-31 and still closes all three scenarios in a saga state that does not exist.

**Two findings are behavioural and both concern the same hole:**

1. **The rendition pipeline has no trigger at all** (PROC-1). Not "a stub whose queues are not active",
   as `processingjob.api.md` puts it — `IAssetProcessingWorker.ProcessAsync` has **zero callers in the
   solution**, and no queue delivers `media.asset.validation-passed` to the `ProcessingWorker` Lambda.
   `CompleteProcessingJobCommand` is therefore never dispatched from anywhere, and `ProcessingJob` cannot
   reach `Succeeded` in any environment.
2. **The validation-timeout path still records `ProcessingTimeout` on the job** (PROC-2), which is the
   precise defect X-11.5 was raised to close. The `ValidationTimeout` enum member landed; the scanner
   that writes the category did not change.

**The remaining drift clusters in three places:**

1. **Persistence key shapes** (§ 2) — neither read-model table uses the partition key the spec
   documents, and the write-side index's table name appears nowhere in the spec. Same block that misled
   in Catalog and Registration; same root cause (the spec describes a shape `DefaultProjectionSchema`
   does not produce).
2. **`processingjob.write-model.md`'s § Invariants and § Methods** (§ 3) — both still carry the
   pre-X-11.5 `Status = Running` guards and contradict the § Status transitions block a few lines above
   them in the same file.
3. **`context-overview.md`'s integration-event section** (§ 3) — every contract is missing its trailing
   `EventVersion`, one contract is absent entirely, and the failure-category enumeration lists values
   that would throw on parse.

---

# 1. Code-side defects and unspecified behaviour

Five findings where the code, not the spec, is likely what should move.

### PROC-1 · **High** · The rendition pipeline has no trigger — `ProcessAsync` has zero callers

`AssetProcessingWorker` is DI-registered
(`Processing.WriteModel.Infrastructure/ServiceCollectionExtensions.cs`, `AddProcessingWriteModel`), and
its `ProcessAsync` is the only code path that dispatches `CompleteProcessingJobCommand`
(`AssetProcessingWorker.cs:86`). **Nothing calls it.** A solution-wide search for `.ProcessAsync(`
returns no hits outside the interface and its implementation; the only other mentions are comments.

The wiring says the same thing from the other end:

- `ProcessingWorker/ProcessingRegistrations.cs:50` registers exactly one message handler —
  `AssetUploadConfirmedMessageHandler`.
- `cdk-magiq-media/lib/constructs/messaging/sqs-queues.ts:178` allowlists exactly one event type on
  `media-processing`: `media.asset.upload-confirmed`.
- `media.asset.validation-passed` is on `media-sagas` only (`sqs-queues.ts:280`), and was deliberately
  removed from `media-cross-module-events` on 2026-09-01 under X-4.19.

So no `AssetValidationPassedIntegrationEvent` ever reaches the `ProcessingWorker` host, which is the only
host that references `IAssetProcessingWorker`.

**Consequences, none of which the spec states:**

- `ProcessingJob` cannot reach `Succeeded` in any environment. `ProcessingJobSucceeded`,
  `ProcessingJobTimeoutRecovered` and `ProcessingJobCompletedIntegrationEvent` are unreachable code.
- Every capable asset the saga starts sits at `Running` until the 240-minute processing budget expires
  and `AssetIngestionTimeoutScanner` fails it. The full-pipeline path terminates in a timeout, always.
- The bypass path is unaffected — it is dispatched by the saga, not the worker — so document assets
  ingest correctly and only capable assets are stranded.

`processingjob.api.md` calls this out as *"a deliberate pass-through stub whose queues are not active
(X-11.7), so `CompleteProcessingJobCommand` has never been dispatched in any environment"*. That is the
right conclusion from the wrong premise: there is no inactive queue waiting to be switched on, there is
no subscription and no caller. `RunProcessingPipelineAsync` additionally throws
`NotImplementedException` (`AssetProcessingWorker.cs:113`), so wiring the trigger without implementing
the pipeline would convert a silent stall into a `ProcessingError` on every asset.

### PROC-2 · **High** · The validation-timeout path stamps `ProcessingTimeout`, re-opening X-11.5

`AssetIngestionTimeoutScanner.CompensateValidationTimeoutAsync` does two dispatches
(`AssetIngestionTimeoutScanner.cs:172-188`):

1. `FailAssetProcessingCommand(..., FailureCategory.ValidationTimeout, ...)` against the **Asset** — correct.
2. `FailProcessingJobCommand(..., ProcessingJobFailureCategory.ProcessingTimeout, "[saga-timeout] AssetIngestionSaga exceeded validation TTL")`
   against the **ProcessingJob** (`:184`) — **`ProcessingTimeout`, on the validation path.**

The saga's compensating dispatch, which does parse `ValidationTimeout` correctly
(`AssetIngestionSaga.cs:193`), can only run after dispatch (1) reaches the Asset, emits
`AssetProcessingFailed`, publishes to SNS, is delivered on `media-sagas` and invokes the
SagaOrchestrator Lambda. Dispatch (2) is in-process and immediate. It wins, and `ProcessingJob.Fail()`
then returns idempotent success on the already-`Failed` job, **preserving the first category**.

So `ProcessingJobFailureCategory.ValidationTimeout` is, in practice, never written to a ProcessingJob —
and because `ProcessingJob.Complete()` treats `ProcessingTimeout` as the one reversible failure, a
validation-timed-out job remains eligible for timeout recovery. That is verbatim the defect three
documents now claim is fixed: `processingjob.write-model.md § Value Objects`, the
`ProcessingJobFailureCategory` XML doc, and `sagas/assetingestionsaga.md § Compensation` all assert that
a validation timeout is terminal.

Currently masked by PROC-1 — no late success can arrive because no pipeline runs. It stops being masked
the day PROC-1 is fixed. One-line fix at `:184`.

### PROC-3 · Medium · `CreateProcessingJobCommand` is still not idempotent (P-2, confirmed still open)

`AssetUploadConfirmedEventHandler.cs:33` mints `ProcessingJobId.New()` on every delivery, and
`CreateProcessingJobCommandHandler` calls `ProcessingJob.Create(...)` unconditionally.
`GetByAssetIdAsync` is **not** on `IProcessingJobRepository` — the interface has `GetByIdAsync` and
`SaveAsync` and nothing else. A duplicate SQS delivery of `AssetUploadConfirmedIntegrationEvent` creates
a second `ProcessingJob` for the same asset, a second saga-creation event (deduplicated by the saga's
existence guard, so harmless there), and a second row overwrite in `media-processing-asset-index`.

The spec already flags this accurately in a 🚨 block. Recorded here only to confirm it is unchanged as of
2026-09-08, and that the write-model spec's `IProcessingJobRepository` listing still shows a method the
interface does not have.

### PROC-4 · Medium · No projector handles `ProcessingJobBypassed` — including the write-side index

`processingjob.read-model.md` records that neither read-model projector handles the event (P-3), so a
bypassed job reads `Queued` forever in `media-processing-job` and `media-processing-jobs`. **The same is
true of `AssetJobIndexProjector`**, which implements handlers for `Created`, `Started`, `Succeeded` and
`Failed` only, and that is documented nowhere. Nothing currently reads that field (X-4.17 covers why),
so nothing breaks — but the write-model spec's index table should say so alongside the read models
rather than leaving one of the three projectors unmentioned.

`ProcessingJobTimeoutRecovered` is likewise unhandled by `AssetJobIndexProjector`; both spec and code
omit it consistently, so that one is not drift, just a second reason the index's `Status` is not a
status.

### PROC-5 · Low · Six stale or wrong XML doc comments inside Processing

These are code-side; they will mislead the next reader of the file before they ever reach the spec.

| File | Claim | Reality |
|---|---|---|
| `ProcessingJobDetailReadModel.cs:10-12` | table `media-processing-jobs`, PK `TENANT#{TenantId}`, SK `JOB#{JobId}` | table is `media-processing-job`; keys are neither of those (PROC-6) |
| `ProcessingJobDetailReadModel.cs:20` | `// Queued \| Running \| Succeeded \| Failed` | omits `Bypassed` |
| `AssetUploadInitiatedEventHandler.cs` | *"The SQS subscription for `AssetUploadInitiatedIntegrationEvent` is still active in the Processing Lambda (managed via CDK)"* | `media-processing` allowlists `media.asset.upload-confirmed` only. `media.asset.upload-initiated` is on `media-cross-module-events`, so this no-op runs in `EventConsumers`, never in `ProcessingWorker` |
| `ProcessingWorker/Function.cs:56-57` | `AddMediaItemCapabilityLookup()` provides `IMediaItemCapabilityService` *"used by `AssetValidationWorker`"* | `AssetValidationWorker` takes `ICommandDispatcher` and `ILogger` only; capability is resolved in AssetManagement |
| `ProcessingJob.cs:14-18` | *"Only created when the asset's owning MediaItem profile has the Processing capability… This aggregate covers the full-pipeline path"* | a job is created for **every** confirmed upload, before capability is known — that is the whole point of the `Bypassed` state |
| `StartProcessingJobCommandHandler.cs`, `AssetProcessingWorker.cs:70` | Start is *"dispatched by the Processing Worker Lambda as the first step of job execution"* | the saga dispatches it (`AssetIngestionSaga.cs:332`); the worker's copy is unreachable (PROC-1) |

---

# 2. Persistence — key shapes and table names

### PROC-6 · **High** · Neither read-model table uses the documented partition key

Platform behaviour, read in `aspnetcore-platform`:
`DefaultProjectionSchema` builds `PK = TENANT#{tenantId}#{schemaIdentifier}[#{groupKey}]` and
`SK = {discriminator}` (both overridable), and `ProjectionKey`'s constructor is
`(tenantId, discriminator, groupKey = null)` — **discriminator second, group key third**.

**Summary — `media-processing-jobs`.** Registered as
`AddProjectionSchema<ProcessingJobSummaryReadModel, ProcessingJobSummarySchema>("media-processing-jobs", schemaVersion: 1)`;
`ProcessingJobSummarySchema` passes schema identifier `PROCESSING_JOBS` and overrides `BuildSortKey` to
`SUMMARY#{discriminator}`. `CreateProjectionKey(tenantId, jobId)` sets discriminator = `jobId`, group key
= null.

| | Spec | Code |
|---|---|---|
| PK | `TENANT#{TenantId}#{JobId}` | **`TENANT#{TenantId}#PROCESSING_JOBS`** |
| SK | `SUMMARY#{JobId}` | `SUMMARY#{JobId}` ✅ |

**Detail — `media-processing-job`.** Registered as
`AddProjectionSchema<ProcessingJobDetailReadModel>("media-processing-job", "PROCESSING_JOB", schemaVersion: 1)`.
`CreateProjectionKey` is `new ProjectionKey<…>(tenantId, "DETAIL", jobId)` — so discriminator = `DETAIL`,
**group key = `jobId`**.

| | Spec | Code |
|---|---|---|
| PK | `TENANT#{TenantId}#{JobId}` | **`TENANT#{TenantId}#PROCESSING_JOB#{JobId}`** |
| SK | `PROCESSING_JOB#DETAIL#{JobId}` | **`DETAIL`** |

**The summary shape carries a decision, not just a doc fix.** Because the group key is null, *every job
summary for a tenant lands in one partition*. Job status is also the most pollable thing this context
owns, and the GSI that would relieve it (`AssetByProcessingJobIndex`) feeds a query with no handler
(X-11.4 / P-4). A large tenant re-ingesting a collection concentrates the whole write burst on a single
partition key. Worth a call before the doc is simply corrected to match.

### PROC-7 · Medium · The `AssetProcessingJobIndex` table is undocumented

`Processing.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:152` registers it as
`AddProjectionSchema<AssetProcessingJobIndex>("media-processing-asset-index", "ASSET", schemaVersion: null)`
→ PK `TENANT#{TenantId}#ASSET#{AssetId}`, SK the asset id, no schema version (so
`ProjectionReplay`/rebuild tooling will refuse it, consistent with the read-model spec's "no CDK rebuild
verb" note).

`processingjob.write-model.md § Write-Side Reference Models` documents the index's fields, its projector
and its projection key, but never names the table it lives in. The CDK does
(`write-indexes.ts:213`, `ProcessingAssetIndex` → `media-processing-asset-index`), so the name exists in
two repos and neither of them is the spec.

### PROC-8 · Low · The stream prefix in the write-model header does not exist

The file header carries `_Stream prefix: `processing_job_`_`. The string `processing_job_` appears
**nowhere** in `src/`. The aggregate is identified by `[AggregateType("media.processingjob")]`, which is
what the event store keys on. Either state the aggregate type or drop the line.

---

# 3. Write model — commands, invariants, events, contracts

### PROC-9 · **High** · Two command signatures in § Commands are wrong

| Spec | Code |
|---|---|
| `CreateProcessingJobCommand(TenantId, AssetId, StorageKey, ContentType)` | `CreateProcessingJobCommand(TenantId, **JobId**, AssetId, StorageKey, ContentType)` |
| `BypassProcessingJobCommand(TenantId, JobId)` | `BypassProcessingJobCommand(TenantId, JobId, **BypassedAt**)` |

The missing `JobId` is not cosmetic. Pre-generating the id in the handler and threading it forward is
precisely the mechanism that replaced the index lookup (PROC-11) — the spec's omission of the parameter
is why the spec still describes a lookup the code stopped doing.

`processingjob.api.md`'s two command tables have the same gap in a different form: they list command
names only, so they are not wrong, but they are also the only other place a reader would check.

### PROC-10 · **High** · § Invariants and § Methods still carry the pre-X-11.5 guards

The same file's § Status transitions block is correct. Two sections above and below it are not.

**§ Invariants** says *"Status must be `Running` — `Complete()`, `Fail()`"*. In code
(`ProcessingJob.cs`):

- `Fail()` — idempotent success on `Failed`; **transitions from `Queued` or `Running`**; refuses
  `Succeeded`/`Bypassed`.
- `Complete()` — transitions from `Running`; **also accepts `Failed` when `FailureCategory ==
  ProcessingTimeout`**, emitting `ProcessingJobTimeoutRecovered`.

**§ Methods (Commands)** repeats the stale preconditions (`Fail` → "Status = Running", `Complete` →
"Status = Running") and **omits `Bypass(bypassedAt)` entirely** — the method that produces the
`Bypassed` terminal state the rest of the document is built around. `Rehydrate(id)` is also absent,
though that is a repository concern and arguably shouldn't be listed.

This is the one drift in the tree most likely to cause a wrong code change: someone reading § Invariants
would "fix" `Fail()` back to a `Running`-only guard, which is exactly the bug X-11.5 closed.

### PROC-11 · **High** · `AssetValidationWorker` does not resolve the JobId via `AssetProcessingJobIndex`

`AssetUploadConfirmedEventHandler.cs:33-38` mints the `ProcessingJobId`, dispatches
`CreateProcessingJobCommand` with it, and passes it **directly** into
`worker.ValidateAsync(e, jobId, ct)`. `IAssetValidationWorker.ValidateAsync` takes `ProcessingJobId` as
a parameter. The worker never touches the index, and its own XML doc says why ("avoiding a projection
lookup on an index that may not have landed yet") — a correct fix for a real eventual-consistency
window.

The spec asserts the lookup in **five** places:

- `context-overview.md § Service Boundaries` — *"Resolve ProcessingJobId via AssetProcessingJobIndex"*
- `context-overview.md § Pipeline Logic` — the same line in the ASCII diagram
- `processingjob.write-model.md § Write-Side Reference Models` — the entire **"Why it exists"** paragraph
- `processingjob.write-model.md § Consumed Integration Events` — closing paragraph
- `processingjob.scenarios.md` P-1 step 5

The index is still live and still needed — `AssetIngestionSaga.OnAssetProcessingFailedAsync` and both
scanner compensation passes use it to resolve `AssetId → JobId`. But its documented *reason for
existing* is a lookup that no longer happens. Rewrite the rationale around compensation, or someone will
eventually delete the index on the grounds that the worker doesn't need it.

### PROC-12 · Medium · `ProcessingJobStarted`'s documented payload omits `AssetId`

§ Domain Events lists `TenantId`, `JobId`, `StartedAt`. Code:
`ProcessingJobStarted(TenantId, JobId, ProcessingAssetId AssetId, DateTimeOffset StartedAt)` — and
`IProcessingDomainEvent` requires `AssetId` on every event in the family. `ProcessingDomainEventMapper`
reads `e.AssetId` to build `ProcessingJobStartedIntegrationEvent`, so the field is load-bearing, not
incidental.

### PROC-13 · Medium · `ProcessingJobCreatedIntegrationEvent` is absent from both published-event tables

`ProcessingDomainEventMapper` implements `IDomainEventMapper<T>` for all **seven** domain events,
including `ProcessingJobCreated → ProcessingJobCreatedIntegrationEvent` (`media.processingjob.created`).
That event is what creates the saga.

- `context-overview.md § Integration Events › Published` lists four rows — no `Created`, no `Bypassed`.
- `processingjob.write-model.md § Published Integration Events` lists five — adds `Bypassed`, still no
  `Created`.

Both files then rely on the event existing: the context overview's *Consumed › SagaOrchestrator* table
has a `ProcessingJobCreatedIntegrationEvent | Processing (self)` row, and the CDK allowlists
`media.processingjob.created` on `media-sagas`. The publisher tables are simply incomplete.

### PROC-14 · Medium · Every integration-event contract is missing its trailing `EventVersion`

All six Processing integration events end with `long EventVersion`, populated from
`e.AggregateVersion` by the mapper. `context-overview.md § Integration Event Contracts` shows it on
`ProcessingJobScanResultIntegrationEvent` only; `Started`, `Completed` and `Failed` are shown without it,
and **`ProcessingJobBypassedIntegrationEvent` has no contract block at all** despite being the event that
carries the whole document fast-exit path.

Registration's R-19 sweep fixed exactly this class of omission in that context; Processing was not
included.

### PROC-15 · Medium · The documented `FailureCategory` values would throw on parse

`context-overview.md`'s `ProcessingJobFailedIntegrationEvent` block comments the field as
`// e.g. "ProcessingError" | "Timeout" | "ValidationFailure"`. Two of those three are not enum members.

Real values (`ProcessingJobFailureCategory`): `ProcessingError`, `ProcessingTimeout`, `ValidationTimeout`.
`AssetManagement.FailureCategory` has five members and shares those three by name, which is what makes
the round-trip work — and AM parses with `Enum.Parse<FailureCategory>(e.FailureCategory)`
(`ProcessingJobFailedEventHandler.cs:41`), **not** `TryParse`. A category string outside the shared set
is an unhandled exception in the consumer, not a fallback.

`processingjob.write-model.md` has this right. The context overview was not swept with it.

### PROC-16 · Low · `RenditionResult` carries `Width` and `Height`; the spec documents four fields

```csharp
public sealed record RenditionResult(
    string RenditionType, string StorageKey, string ContentType,
    long FileSizeBytes, int? Width, int? Height);   // ← last two undocumented
```

§ Value Objects documents `{ RenditionType, StorageKey, ContentType, FileSizeBytes }`. Both DTOs
(`ProcessingRenditionDto`, `RenditionResultDto`) genuinely have the four fields — so the domain value
object carries per-rendition dimensions that are **dropped at every boundary**: not in the integration
event, not in the read model, not observable by any consumer. Either document them and carry them
through, or delete them. Needs a call rather than a doc edit.

### PROC-17 · Low · Handlers return `Result<Unit, IDomainError>`, not `Result<Unit, DomainError>`

The spec says `Result<T, DomainError>` in § Purpose, § Commands, § Handler-side Pre-conditions and
`processingjob.api.md § API Conventions`. Every handler in the module returns
`Result<Unit, IDomainError>` (the interface). Trivial, but it is stated four times.

### PROC-18 · Low · Five classes named in the spec do not exist

| Named in | Spec name | Actual |
|---|---|---|
| `processingjob.write-model.md § Consumed Integration Events` | `AssetUploadConsumer` | `AssetUploadConfirmedEventHandler` |
| `context-overview.md` (twice, on the `Completed`/`Failed` contracts) | `AssetManagement.ProcessingEventConsumer` | `ProcessingJobCompletedEventHandler` / `ProcessingJobFailedEventHandler` |
| `context-overview.md § Service Boundaries`, `processingjob.api.md § Authorization` | `SagaTimeoutScanner` (as a Lambda/class) | class `AssetIngestionTimeoutScanner` in host `TimeoutScanner`; `SagaTimeoutScanner` is only the CloudWatch metric namespace |
| `processingjob.read-model.md § Query Handlers` | `ListProcessingJobsForAssetIdHandler`, with a reader and a method | **does not exist** — the same file says so two sections earlier (P-4) |
| `processingjob.write-model.md` (truncation note, already annotated) | `ProcessingJobProjector` | correctly annotated as non-existent (X-11.1) — no action |

The `SagaTimeoutScanner` naming is the one worth fixing properly: three different names for one
component across the spec, the host folder and the metric namespace.

---

# 4. Read model

### PROC-19 · Medium · The `media-processing-job` field table still says `sizeBytes`

The `Renditions` row types the array as `[{ renditionType, storageKey, contentType, sizeBytes }]`. It is
`FileSizeBytes` — in the domain VO, in `RenditionResultDto`, and in `ProcessingRenditionDto`. The
**embedded-types block lower in the same file** was corrected under P-9 on 2026-08-31 and carries a note
saying the code has never used `SizeBytes`; the field table above it was missed. Same file, two
spellings, one of them the one P-9 explicitly retired.

Everything else in this document checks out — see § 7.

---

# 5. `AssetIngestionSaga`

### PROC-20 · **High** · The DLQ & Poison Policy section is stale — X-11.6 is fixed

The 🚨 block states that the DLQ is unreachable for any saga-handler exception, that *"both handler
layers swallow exceptions"*, that the inner handler *"catches and logs 'message will be retried' without
rethrowing"*, that `maxReceiveCount: 3` never counts, that the depth alarm can never fire, and that
*"the same pattern is in all five handler pairs"*.

**None of that is true of the code today.** Both layers were rewritten:

- **Inner** — all five of `Processing.WriteModel/IntegrationEvents/Consuming/Handlers/*SagaHandler.cs`
  are now bare one-line delegations to the saga method, each carrying an explicit *"This handler does
  not catch"* doc block citing X-11.6 by name.
- **Outer** — all five of `SagaOrchestrator/AssetIngestion/Handlers/*SagaHandler.cs` catch **only** to
  log and return `MessageProcessStatus.Failed()`, and `Function.FunctionHandler` uses
  `ProcessLambdaEventWithBatchResponseAsync`, so a failure is reported as a batch item failure and the
  message is left on `media-sagas`. `maxReceiveCount: 3` counts; `media-sagas-dlq` is reachable.

This drift runs in the opposite direction to everything else in this report: **the spec understates the
system's reliability.** Someone will either spend a day re-fixing a fixed bug, or — worse — discount the
DLQ during an incident because the spec told them it can't fire.

The § Idempotency bullet 4 and § Compensation are both already correct post-X-11.5; only the DLQ block
was left behind.

### PROC-21 · Medium · "No test coverage of `AssetIngestionSaga` at all" is no longer true

§ Manual Intervention Runbook states *"**no test coverage of `AssetIngestionSaga` at all** (`tests/`
contains nothing matching `*saga*`)"*. There is one file:
`tests/modules/Processing/Processing.WriteModel.Tests/Sagas/AssetIngestionSagaHandlerFailurePropagationTests.cs`.

The spirit of the claim survives — one file covering failure propagation is not coverage of a five-state
machine with a two-phase clock — but the sentence as written is false, and it is the sentence someone
would cite when arguing the saga is untested. Restate it as what is actually missing: no transition
tests, no timeout tests, no idempotency tests.

The rest of the runbook's absence claims still hold: `src/tools/Cli/` has no saga command group, and
`ProjectionsRebuildCommand`'s registry covers no saga.

---

# 6. `processingjob.scenarios.md` — the least-swept file in the tree

### PROC-22 · **High** · All three scenarios close the saga in a state that does not exist

Six occurrences of a saga state called `Complete` — steps and diagrams at lines 54, 113, 132, 185, 205
and 248. `AssetIngestionSagaStatus` has five members and `Complete` is not one of them.

Worse than a typo, because the correct state differs per scenario:

| | Spec says | Actual |
|---|---|---|
| P-1 (full pipeline) | → `Complete` | `Completed` |
| P-2 (bypass) | → `Complete`, on `AssetProcessingCompletedIntegrationEvent` | **`Bypassed`, written synchronously inside the validation-passed handler before the bypass command is dispatched.** The `AssetProcessingCompleted` that P-2 shows closing the saga is in fact *discarded* by the terminal-state guard at `LogDebug` — the saga spec calls this out explicitly as a line that fires once per bypassed asset and is not a duplicate |
| P-3 (timeout) | → `Complete` | `Failed` |

`context-overview.md:143` and `sagas/assetingestionsaga.md` were both corrected on 2026-08-31 under
P-5/P-7 and now say in terms that *"there is no state called `Complete`"*. The scenarios file was not
swept with them.

### PROC-23 · Medium · P-1 and P-3 narrate a pipeline that has no trigger

P-1 steps 9–10 describe `AssetProcessingWorker` generating thumbnails via Sharp/ImageMagick, extracting
EXIF via ExifTool, and dispatching `CompleteProcessingJobCommand`. P-3 step 3 has it submitting a
MediaConvert job. Neither happens — the worker has no caller and its pipeline method throws
`NotImplementedException` (PROC-1). `processingjob.api.md` carries a ⚠ about this; the scenarios carry
nothing, and they are what a new engineer reads first.

At minimum, mark P-1 steps 9–12 and P-3 step 3 as specified-not-implemented, the way
`context-overview.md § S3 Paths` marks the quarantine row.

### PROC-24 · Medium · P-3's key invariant contradicts P-3's own step 1

Step 1 correctly describes the two-phase clock (saga already created on `ProcessingJobCreated`, clock
reset on the transition to `ProcessingDispatched`). The Key invariants block below then says *"The saga
covers only the `StartProcessingJobCommand`–`CompleteProcessingJobCommand` window"* — the pre-P-6
model. The saga covers the validation window too; that is what the 15-minute budget and the scanner's
second pass are for.

### PROC-25 · Low · Four smaller inaccuracies across the three scenarios

- **P-1 step 5** — the `AssetProcessingJobIndex` lookup (PROC-11).
- **P-1 step 4 / P-2 step 4** — `CreateProcessingJobCommand` described as *"(idempotent)"* (PROC-3).
- **P-3 step 5** — `FailProcessingJobCommand({tenantId, jobId, reason: "ProcessingTimeout"})`. That value
  is the `FailureCategory` argument; `Reason` is a separate free-text string
  (`"[saga-timeout] AssetIngestionSaga exceeded processing TTL"`).
- **P-3 step 7** — *"AM `ProcessingJobFailedEventHandler` dispatches `FailAssetProcessingCommand(ProcessingError)`"*.
  The handler passes the category through unchanged, so on this path it is `ProcessingTimeout`.

### PROC-26 · Low · P-3 uses two names for the scanner in consecutive steps

Step 4 says `AssetIngestionTimeoutScanner`, step 5 says `SagaTimeoutScanner`. Same component (PROC-18).

---

# 7. Verified correct — worth recording

Checked against source and found accurate. Recording it so the next pass does not re-derive it.

**`sagas/assetingestionsaga.md` — accurate throughout except § DLQ (PROC-20).** Specifically confirmed:

- Correlation key `AssetId`, `SagaId == AssetId`, SK `SAGA#ASSET_INGESTION#{AssetId}`, projected
  attributes written on every save (`AddProcessingAssetIngestionSaga`).
- The full transition table including the `AwaitingValidation → Failed` row and its
  `Status ∈ {ProcessingDispatched, AwaitingValidation}` guard.
- Five statuses; `Failed` reopenable by `AssetProcessingTimeoutRecovered`; `Bypassed` and `Completed`
  absorbing.
- The bypass branch closing itself synchronously, and the `LogDebug` line that fires for every bypassed
  asset without being a duplicate.
- Clock origins are event timestamps (`e.CreatedAt`, `e.PassedAt`), not `UtcNow`.
- `AssetIngestionTimeoutOptions` section name `Media:Processing:AssetIngestionTimeouts`, defaults 15 /
  240 / 0.2 — **and the ⚠ that no CDK environment variable sets any of them.** Searched
  `cdk-magiq-media` for all four names: no matches. The compiled defaults are the deployed configuration.
- Three scanner passes, the 15-second safety buffer, the `SagaTypeByTimeout` GSI key condition + status
  filter, and both CloudWatch metric names dimensioned by `SagaStatus`.
- `media-sagas` allowlisted to exactly the five event types (`sqs-queues.ts:277-284`), matching
  `SagaRegistrations.AddSagaMessageHandlers`.
- No optimistic concurrency; `Version` written and never read.

**`processingjob.api.md`:**

- No `Processing.WriteModel.Endpoints` project — Processing is the only module without one. Confirmed.
- `Api.csproj` references `Processing.WriteModel.Infrastructure` only. Confirmed.
- `QueryApi.csproj` does not reference Processing at all; `AddProcessingReadModelQueries()` is called
  only from `Api/Startup.cs:190`. X-11.4 holds exactly as written.
- `ListProcessingJobsForAssetIdQuery` has no handler; `AssetByProcessingJobIndexSchema` is registered and
  maintained regardless. P-4 holds.
- **All six line-number citations still resolve to the lines they claim** — `AssetIngestionSaga.cs:193`
  (compensation), `:309` (bypass), `:332` (start); `AssetProcessingWorker.cs:58` (bypass), `:86`
  (complete), `:97` (fail). Rare, and worth saying.

**`processingjob.write-model.md`:**

- The § Status transitions block, including the `Queued → Failed` row, the idempotent-repeat list and the
  refusal set — matches `ProcessingJob.Fail()` / `Start()` / `Bypass()` / `Complete()` case for case.
- `ProcessingJobFailureCategory`'s three members and the "only `ProcessingTimeout` is reversible" rule.
- The `AssetProcessingJobIndex` ⚠ (X-4.17): both terminal events really do write `Status = Running`, so a
  row never reaches `Succeeded` or `Failed`, and both consumers use the index only for `AssetId → JobId`.
  The projection key is `(TenantId, AssetId)` — one row per asset. Exactly right.
- `RecordScanResult` leaving `Status = Queued`.

**`processingjob.read-model.md`:** two tables, two projectors, the per-event write tables (including
`ProcessingJobTimeoutRecovered` on both), the `ProjectedVersion` fence, the `Bypassed`-never-projected
note (P-3), `FileSizeBytes` in the embedded types, and the Consistency section's "no rebuild verb, no
freshness marker" claims — `schemaVersion: null` on the index confirms the rebuild half.

**`context-overview.md`:** the four AssetManagement handler names in § Aggregate List all exist and
dispatch the commands claimed; `media.processingjob.*` are allowlisted on `media-cross-module-events`
(`sqs-queues.ts:257-261`); the `media-quarantine` row's *"provisioned but unwired"* (X-4.7) is still
exactly true — the bucket exists at `media-buckets.ts:173` and no `.cs` file in either repo references
it.

---

# Incidental — not spec drift

`media-processing`'s SQS visibility timeout comment (`sqs-queues.ts:36`, `:170-173`) says 1800 s is
needed because *"virus scan + rendition pipeline can exceed the Lambda function timeout"* and that
*"video jobs extend via `ChangeMessageVisibility` up to 4 h"*. Given PROC-1, that queue currently carries
only job creation and a stub scan that always returns `"Passed"`. The 30-minute visibility timeout is
harmless but is sized for a workload that does not run, and no code calls `ChangeMessageVisibility`.

---

## Suggested next steps

Nothing here is a review yet. If any of it is taken forward:

1. **PROC-1 and PROC-2 are the only two that change behaviour, and they are one workstream.** Both are
   about the pipeline's real terminal states. PROC-2 is a one-line fix that should land *first* — it is
   currently masked by PROC-1 and stops being masked the moment PROC-1 is fixed. Call it
   `processing-pipeline-activation`; it will want a decision on whether the rendition pipeline is
   implemented or the worker deleted, because a stub with a live trigger is worse than a stub with none.
2. **§ 2 (PROC-6…PROC-8) is a documentation fix with one embedded decision** — the single-partition
   summary table. Same shape as Registration's REG-6/REG-7; if `projection-tables` (MM-003) is still
   live, this belongs there rather than in a Processing-specific workstream.
3. **PROC-20 should be corrected on its own, ahead of everything else.** It is a five-minute edit and it
   is the only finding here that would mislead someone during an incident.
4. **§ 3, § 4 and § 6 are a single spec sweep** — roughly half a day, mechanical, best done in one PR
   against `docs/spec/contexts/Processing/` so the files stop disagreeing with each other. PROC-10 and
   PROC-22 are the two that must land; the rest are tidying. PROC-16 needs a call first.
5. **PROC-5 is a code-comment sweep** and can ride along with any Processing PR. It does not need a
   workstream.
