# Processing — ProcessingJob Aggregate Architecture Review (Specification vs Repository)

_Context: **Processing** · Aggregate: **`ProcessingJob`** — magiq-media_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API)_
_Date: 2026-07-19_
_Scope: `src/modules/Processing/**` (ProcessingJob slice — Domain, WriteModel{,.Endpoints,.Infrastructure}, ReadModel{,.Endpoints,.Infrastructure}, Contracts, Sagas, Workers, Indexes) vs `docs/spec/contexts/Processing/**` (context-overview, business-scenarios, `aggregates/ProcessingJob/{api,write-model,read-model,scenarios}`) + shared conventions (`api-conventions`, `error-catalog`, `security-scenarios`, `bulk-operations`, `media-types`) + `docs/adrs/**` (esp. `asset-storage-and-processing.md`, ADR-008)_

> Method: 67 production `.cs` files — the full ProcessingJob slice (Domain aggregate + 7 domain events + 6 value objects, 6 commands + 6 handlers, 8 Contracts integration-event/DTO records, the `AssetIngestionSaga` + 5 saga/consumer handlers + 2 workers, the `AssetProcessingJobIndex` reference model + projector, 2 read-model projectors, 2 queries + read models + schemas, and both `ServiceCollectionExtensions`) — were read line-by-line and compared against the ProcessingJob write-model, read-model, API, scenarios and Processing context-overview specs. AssetManagement is referenced only where ProcessingJob directly couples to it (the `Asset*` integration events the saga and workers consume/produce); findings that hinge on AssetManagement or host-project wiring outside this slice are flagged as such. The `SagaTimeoutScanner` and `ProcessingWorker`/`SagaOrchestrator` host projects are outside the module and are called out where a conclusion depends on their wiring.

---

## 1. Module Summary

`ProcessingJob` is the single aggregate of the Processing context. It models one asset's ingestion-pipeline execution as an event-sourced stream (`media.processingjob`): created on upload confirmation, virus-scanned, optionally rendition/metadata-processed, and terminated as **Succeeded**, **Failed**, or **Bypassed**. The context deliberately exposes **no public HTTP endpoints** (correctly — there is no `Processing.Endpoints` project); every interaction is a Lambda-to-Lambda command dispatch or an SQS-driven integration-event handler, and all `TenantId`s flow from the message envelope. Processing communicates with AssetManagement exclusively through integration events on `media-integration-events` SNS — the aggregate itself never touches the `Asset` aggregate.

Structurally the slice is clean and conventional: command-per-folder with thin handlers, a `ProcessingDomainEventMapper` translating domain events to integration events inline, a write-side `AssetProcessingJobIndex` reference model for `AssetId → JobId` resolution, and two DynamoDB read models (`media-processing-jobs` summary, `media-processing-job` detail) fed by dedicated projectors. The aggregate is a well-shaped small state machine with idempotent `Start`/`Bypass`, a genuinely thoughtful `ProcessingTimeout`-only recovery path (`Failed → Succeeded` via `ProcessingJobTimeoutRecovered`), and a two-phase timeout budget in the `AssetIngestionSaga`.

However, the module is **not production-ready**, and — unlike AssetManagement, where the aggregate was the strong part — here the defects cluster in the **projector and orchestration layer** and in a **materially stale write-model spec**. The review surfaced one Critical and a cluster of High issues in four themes:

1. **Read-model projections are wrong or missing.** The summary projector writes `Status = Succeeded` on a **job failure** (a failed job reports as succeeded to ops); the `Bypassed` terminal state is projected **nowhere** (bypassed jobs show `Queued` forever); and the write-side `AssetProcessingJobIndex` records `Running` for **Succeeded and Failed** jobs. The read side silently disagrees with the write side across three surfaces.
2. **The pipeline has no completion driver in the wiring reviewed.** `AssetProcessingWorker.ProcessAsync` — the only code that runs renditions and dispatches `CompleteProcessingJobCommand` — is registered in DI but **never invoked**; the sole `AssetValidationPassed` consumer is the saga, which only dispatches `Start`. As wired, every capable-asset job sits `Running` until the saga timeout forces it `Failed`.
3. **Failures are swallowed with no retry.** All five saga/consumer handlers `catch (Exception) { log "will be retried" }` **without rethrowing** — the message is ACKed and never retried; the reassuring log line is false. Command-dispatch `Result`s are ignored in the same handlers.
4. **Idempotency is asserted but not implemented.** The spec-mandated `GetByAssetIdAsync` create-guard is absent (and missing from the repository interface), a **fresh `JobId` is minted per delivery**, and `Complete`/`Fail` return errors — not no-ops — on terminal re-delivery, contradicting the P-3 idempotency guarantee.

The domain aggregate is the strongest part; the actual virus scan and rendition pipeline are unimplemented TODOs (blocking for a compliance-grade platform), and the `ProcessingJob` write-model spec is behind the code on the entire bypass and timeout-recovery mechanics.

---

## 2. Aggregate Analysis

### `ProcessingJob` (Aggregate Root) — `Processing.Domain/Aggregates/ProcessingJob.cs`

Single aggregate in the context. `EventSourced<ProcessingJob, ProcessingJobId>`, `ITenantScoped`, `[AggregateType("media.processingjob")]`.

**Purpose & responsibilities:** track a single asset's processing lifecycle and enforce the status-transition invariants. It does **not** own final asset state (that is `Asset` in AssetManagement) — it drives the process and publishes integration events.

**Aggregate root:** `ProcessingJob`. **Child entities:** none (correct). **Value objects:** `ProcessingJobId` (UUID v7), `ProcessingAssetId`, `ProcessingJobStatus`, `ProcessingJobFailureCategory`, `RenditionResult`, `ExtractedMetadata`. Healthy VO surface; the aggregate is not anemic.

**Key state:** `Status`, `AssetId`, `StorageKey` (immutable post-creation), `ContentType`, `Renditions`, `Metadata`, `FailureCategory`/`FailureReason`, `CompletedAt`, `CreatedAt`, `TenantId` (first field on the creation event, immutable — convention satisfied, `ProcessingJob.cs:156-164`).

**Invariants enforced in the aggregate (correct):**
- `RecordScanResult` / `Start` require `Status = Queued`; `Complete` / `Fail` require `Status = Running` (`ProcessingJob.cs:103,122,133,139`).
- `Start` and `Bypass` are idempotent (repeat on the same terminal/target state returns success — `ProcessingJob.cs:65-68,133-136`), reflecting the saga/worker race.
- Only `Failed(ProcessingTimeout)` is reversible to `Succeeded` (via `ProcessingJobTimeoutRecovered`); every other failure — including `ProcessingError` — stays terminal (`ProcessingJob.cs:92-96`). This is a genuinely good design.
- `StorageKey`/`TenantId` set once on creation, never mutated.

**Aggregate boundary assessment:** appropriate. The aggregate correctly excludes capability resolution, S3 mechanics, and saga routing. Size is minimal and correct for the lifecycle it governs. No cross-aggregate business logic leaks into it.

**Aggregate-level defects (detailed in §12):**
- **PJ-D1 (Medium, determinism/testability).** `Start()` and `Fail()` stamp `DateTimeOffset.UtcNow` **inside the aggregate** (`ProcessingJob.cs:109,144`) instead of receiving a timestamp, unlike `Create`/`RecordScanResult`/`Complete`/`Bypass` which take one from the handler's `IClock`. Non-deterministic, un-mockable, and inconsistent with its peers.
- **PJ-D2 (Medium, spec drift).** The aggregate implements `Bypass()`, `ProcessingJobBypassed`, the `Bypassed` status, and `ProcessingJobTimeoutRecovered` — **none of which appear** in the write-model spec's methods/events/lifecycle tables (see §11 / PJ-M6).
- **PJ-D3 (Low, VO drift).** `RenditionResult` carries `Width`/`Height` (`RenditionResult.cs:8-9`) that the spec VO omits and that are **dropped** by every downstream mapper (PJ-L1).

---

## 3. Lifecycle Analysis

### State machine (reconstructed from `ProcessingJob.cs` guards + `Apply` handlers)

```text
                         Create (AssetUploadConfirmed)
                                  │
                                  ▼
                               Queued ─────RecordScanResult─────► Queued
                                  │        (no status change)
              ┌───────────────────┼───────────────────────────┐
            Start                Bypass                    (scan Failed / VirusDetected)
              │                    │                             │
              ▼                    ▼                             ▼
           Running            Bypassed [terminal]        Queued  ── ORPHANED ──► (no terminal
        ┌─────┴───────┐    (document fast-exit,           (saga never Start/Bypass;    transition;
    Complete         Fail    P-2 path)                      job stuck Queued forever)   dead-end)
        │             │
        ▼             ▼
    Succeeded      Failed
    [terminal]        │  (ProcessingTimeout only — Complete() re-entry)
                      │  emits ProcessingJobTimeoutRecovered
                      ▼
                  Succeeded [terminal]
```

**Terminal states:** `Succeeded`, `Failed` (non-timeout), `Bypassed`. **Reversible-failure:** `Failed(ProcessingTimeout)` → `Succeeded`.

### Lifecycle issues

- **PJ-L-life1 (Medium/High) — scan-failure and virus jobs are orphaned in `Queued`.** `RecordScanResult` never transitions status; on `Failed`/`VirusDetected`, AssetManagement drives the asset to a terminal state and **never publishes `AssetValidationPassed`**, so the saga never dispatches `Start` or `Bypass`. The `ProcessingJob` remains `Queued` permanently, its read-model rows remain `Queued`, and the only "recovery" (the saga's 15-min validation timeout → `FailAssetProcessingCommand` on the *asset*) is a no-op against the job. There is no terminal transition on the job for a scan failure. (§12 PJ-M2.)
- **PJ-L-life2 (High) — `Running` has no completion driver in the reviewed wiring.** `Start` moves the job to `Running`, but the component that runs the pipeline and dispatches `CompleteProcessingJobCommand` (`AssetProcessingWorker`) is never invoked in-module. As wired, `Running → Succeeded` cannot occur; the job waits for the saga timeout and goes `Running → Failed`. (§12 PJ-C2/PJ-H5.)
- **PJ-L-life3 (Medium) — `Fail`/`Complete` are not idempotent on re-delivery**, so a duplicate timeout/completion returns `InvalidOperation` rather than the no-op the P-3 scenario and the saga's own comment promise (`ProcessingJob.cs:98,105`; `AssetIngestionSaga.cs:164`). (§12 PJ-M1.)
- **PJ-L-life4 (Low) — no `Queued → Failed` path.** `Fail` requires `Running`, so a job stuck in `Queued` (worker crash before `Start`, or the orphan case above) has no domain failure path at all; the spec leans on "SQS DLQ" for this, which does not transition the aggregate.

---

## 4. Commands

6 commands. `⚠` marks a command with at least one finding (detailed in §12).

| Command | Handler | Dispatched by | Notes |
|---|---|---|---|
| CreateProcessingJobCommand | CreateProcessingJobCommandHandler | `AssetUploadConfirmedEventHandler` | ⚠ no `GetByAssetId` idempotency guard; fresh `JobId` per delivery → duplicate jobs (PJ-H1) |
| RecordProcessingJobScanResultCommand | RecordProcessingJobScanResultCommandHandler | `AssetValidationWorker` | ⚠ `outcome` is an unvalidated string; job orphaned on Failed/Virus (PJ-M2) |
| StartProcessingJobCommand | StartProcessingJobCommandHandler | `AssetIngestionSaga` **and** `AssetProcessingWorker` | ⚠ dispatched from two places (PJ-H5); idempotent ✔ |
| BypassProcessingJobCommand | BypassProcessingJobCommandHandler | `AssetIngestionSaga` **and** `AssetProcessingWorker` | ⚠ dual-dispatch (PJ-H5); idempotent ✔ |
| CompleteProcessingJobCommand | CompleteProcessingJobCommandHandler | `AssetProcessingWorker` (unwired) | ⚠ only caller never invoked (PJ-C2); not idempotent on re-delivery (PJ-M1); carries domain VOs (PJ-L4) |
| FailProcessingJobCommand | FailProcessingJobCommandHandler | `AssetProcessingWorker` (catch); saga compensation; `SagaTimeoutScanner` | ⚠ not idempotent on re-delivery (PJ-M1); dispatch result ignored by worker (PJ-M3) |

**Cross-cutting command issues:**
- **Idempotency is inconsistent across the command set.** `Start`/`Bypass` are idempotent; `Create`/`Complete`/`Fail` are not (Create because the handler skips the spec's asset-existence check; Complete/Fail because the guards reject non-`Running`). For at-least-once SQS delivery this is a correctness gap, not a nicety. (PJ-H1/PJ-M1.)
- **All commands are System-dispatched; no authorization is required or present** — this matches `processingjob.api.md §Authorization`. Correct, not a finding.
- **`CompleteProcessingJobCommand` carries domain value objects** (`IReadOnlyList<RenditionResult>`, `ExtractedMetadata?`) directly in its record (`CompleteProcessingJobCommand.cs:7`). Minor CQRS-purity smell — commands ideally carry primitives/DTOs (PJ-L4).
- **No duplicate/redundant commands** in the set itself; the 6 map cleanly to aggregate methods. (The *dispatch* of `Start`/`Bypass` is duplicated across saga and worker — a wiring/design issue, PJ-H5, not a redundant-command issue.)

---

## 5. Queries

2 queries — both internal/system-only (correct per spec; no public HTTP surface).

| Query | Paging | Reachable? | Notes |
|---|---|---|---|
| GetProcessingJobByIdQuery | n/a | ✔ registered | CQRS-clean: returns DTO, 404 on miss (`GetProcessingJobByIdHandler.cs:16-18`). Detail row is stale/wrong for Bypassed jobs (shows Queued — PJ-H3) |
| ListProcessingJobsForAssetIdQuery | index (GSI, cursor) | ✖ **no handler / not registered** | `TenantScopedIndexQuery` defined, but there is **no `ListProcessingJobsForAssetIdHandler`** and it is **not** added in `AddProcessingReadModelQueries` (only `GetProcessingJobById` is — `ReadModel.Infrastructure/ServiceCollectionExtensions.cs:53`). Query is unreachable (PJ-H7) |

**Query issues:**
- **`ListProcessingJobsForAssetIdQuery` is dead** — the read-model spec references a `ListProcessingJobsForAssetIdHandler` that does not exist, and the query is not wired. The `AssetByProcessingJobIndex` GSI it targets is defined (`AssetByProcessingJobIndexSchema.cs`), so this is a missing handler + registration, not a schema gap. (§12 PJ-H7.)
- **CQRS boundary is otherwise clean** — `GetProcessingJobById` returns a read-model DTO; no aggregate or event payload crosses the boundary.
- **`GetProcessingJobByIdQuery` doc-comment claims "Consumed internally by SagaOrchestrator to check job state"** (`GetProcessingJobByIdQuery.cs:11`), but the saga actually resolves job state via `IReferenceLookup<AssetProcessingJobIndex>` (`AssetIngestionSaga.cs:158`). The detail query appears used only by ops tooling — the doc-comment is misleading (PJ-L3).

---

## 6. API Endpoints

**None — and correctly so.** `processingjob.api.md` states the context exposes no public HTTP endpoints and there is no `Processing.Endpoints` project; the repository confirms this (no endpoint project exists in `src/modules/Processing`). This matches the spec exactly and is the right call for a purely event/command-driven context.

The only observations:
- The full internal command/event surface is documented for traceability (api.md §Command → Event → Projection). The **traceability table is stale**: it lists 4 commands (`Create`, `Start`, `Complete`, `Fail`) and omits `RecordProcessingJobScanResult` and `Bypass`, and lists only `media.asset.processing-failed` under "Integration Events Published" while the code publishes six job-level integration events (PJ-M6/PJ-L5).
- Because there is no HTTP surface, RFC 9457 problem-details, versioning, verb, and status-code conventions do not apply. The error-contract findings that dominated the AssetManagement review are **not applicable** here — a genuine strength.

---

## 7. Request DTO Review

No HTTP request DTOs exist (no endpoints). The "request" surface is the six command records. Findings:

| Command record | Findings |
|---|---|
| `CreateProcessingJobCommand` | `JobId` supplied by the caller (`AssetUploadConfirmedEventHandler`), which mints a **new** one per delivery — the root of the duplicate-job idempotency defect (PJ-H1). No validation that `StorageKey`/`ContentType` are non-empty |
| `RecordProcessingJobScanResultCommand` | `Outcome` is a free `string` (`"Passed"`/`"Failed"`/`"VirusDetected"`) with **no validation or enum** — any value is accepted and only `"Passed"` is acted on downstream; a typo silently behaves like non-Passed (PJ-M2) |
| `CompleteProcessingJobCommand` | Carries domain VOs directly (PJ-L4); no null/empty guards on renditions |
| `FailProcessingJobCommand` | `Reason` unbounded/unvalidated; category is a proper enum ✔ |
| `StartProcessingJobCommand` / `BypassProcessingJobCommand` | minimal `(TenantId, JobId[, BypassedAt])` ✔ |

**Cross-cutting:** no FluentValidation anywhere in the slice — acceptable given there is no external input boundary (all inputs originate from trusted internal dispatchers), but `Outcome` deserves a value object or enum since it is a semantic switch.

---

## 8. Response DTO Review

The "response" surface is the two read models and their embedded DTOs.

| DTO | Findings |
|---|---|
| `ProcessingJobDetailReadModel` | Uses domain `ProcessingJobStatus` (incl. `Bypassed`) directly (`ProcessingJobDetailReadModel.cs:18`), so it *can* represent Bypassed — but no projector ever writes it, so bypassed jobs read as `Queued` (PJ-H3). Exposes `StorageKey`/`TenantId` — acceptable for a system-only detail model. Doc-comment cites the wrong table (`media-processing-jobs`) and SK (`JOB#{JobId}`) vs the actual detail table `media-processing-job` / SK `DETAIL` (PJ-L3) |
| `ProcessingJobSummaryReadModel` | `Status`/`StatusText` are plain strings; correctly populated on Created/Started/Succeeded/TimeoutRecovered but **wrong on Failed** (`Status = "Succeeded"` — PJ-C1). No `Bypassed` handling (PJ-H3) |
| `RenditionResultDto` (read + contract) | Field `FileSizeBytes` where the spec DTO says `SizeBytes`; **drops `Width`/`Height`** carried by the domain VO (PJ-L1/PJ-L2) |
| `ExtractedMetadataDto` | Matches the spec (`Width, Height, DurationSeconds, Format, ExifData`) ✔ |

**Cross-cutting:** identifier/size naming is inconsistent with the spec (`FileSizeBytes` vs `SizeBytes`); rendition dimensions are silently lost end-to-end. No `TenantId`-leak-to-clients concern here because there is no client — the read models are system/ops only.

---

## 9. Domain Events

7 domain events, all registered in the aggregate's `When<>` block and all mapped by `ProcessingDomainEventMapper`. Publisher = `ProcessingJob`.

| Domain event | Trigger | Summary proj. | Detail proj. | AssetJobIndex proj. | Integration mapping |
|---|---|---|---|---|---|
| `ProcessingJobCreated` | `Create()` | ✔ | ✔ | ✔ | `ProcessingJobCreatedIntegrationEvent` |
| `ProcessingJobScanResultRecorded` | `RecordScanResult()` | ✖ (no status change) | ✖ | ✖ | `ProcessingJobScanResultIntegrationEvent` |
| `ProcessingJobStarted` | `Start()` | ✔ | ✔ | ✔ | `ProcessingJobStartedIntegrationEvent` |
| `ProcessingJobSucceeded` | `Complete()` | ✔ | ✔ | ⚠ writes `Running` | `ProcessingJobCompletedIntegrationEvent` |
| `ProcessingJobFailed` | `Fail()` | ⚠ writes `Succeeded` | ✔ | ⚠ writes `Running` | `ProcessingJobFailedIntegrationEvent` |
| `ProcessingJobBypassed` | `Bypass()` | ✖ **missing** | ✖ **missing** | ✖ **missing** | `ProcessingJobBypassedIntegrationEvent` |
| `ProcessingJobTimeoutRecovered` | `Complete()` (recovery) | ✔ | ✔ | ✖ missing | `ProcessingJobCompletedIntegrationEvent` (reuses completion contract) |

Notes:
- **Timing correct** for all events; state is set exclusively via `Apply` (no pre-Emit mutation).
- **Payload completeness good** — every event carries `TenantId`, `JobId`, `AssetId`. `ProcessingJobScanResultRecorded` is **not projected** anywhere, so the scan outcome/`FailureReason` never reaches a read model or the summary's `StatusText`; this is acceptable if scan status is purely transient, but it means a "scan failed / virus" state is invisible on the job side (relates to PJ-M2).
- **`ProcessingJobBypassed` is projected nowhere** — the single largest event-projection gap (PJ-H3).
- **`ProcessingJobTimeoutRecovered → ProcessingJobCompletedIntegrationEvent`** cleanly re-uses the completion contract for the internal hop (`ProcessingDomainEventMapper.cs:104-125`) — reasonable, and the distinct domain event preserves the recovery in the audit stream. Good.

---

## 10. Integration Events

### Published (mapper `ProcessingDomainEventMapper.cs`)

Six integration events, all published inline from domain events, each carrying `TenantId` + `EventVersion` (`= AggregateVersion`). No event declares its own message/idempotency id (delegated to the platform `IntegrationEvent` envelope — unverified here).

| Integration event | From | Consumers | Issues |
|---|---|---|---|
| `ProcessingJobCreatedIntegrationEvent` | `ProcessingJobCreated` | Processing self — `ProcessingJobCreatedSagaHandler` (starts saga) | none |
| `ProcessingJobScanResultIntegrationEvent` | `ProcessingJobScanResultRecorded` | AssetManagement | `Outcome` unvalidated string (PJ-M2) |
| `ProcessingJobStartedIntegrationEvent` | `ProcessingJobStarted` | AssetManagement | carries `AssetId`+`EventVersion` not in the context-overview doc shape (PJ-L5) |
| `ProcessingJobCompletedIntegrationEvent` | `ProcessingJobSucceeded` **and** `ProcessingJobTimeoutRecovered` | AssetManagement, Billing | `ProcessingRenditionDto.FileSizeBytes` vs spec `SizeBytes`; `Width/Height` dropped (PJ-L1/PJ-L2) |
| `ProcessingJobFailedIntegrationEvent` | `ProcessingJobFailed` | AssetManagement, Notifications, SagaOrchestrator | `FailureCategory` serialized as string — round-trips via matching enum names ✔ |
| `ProcessingJobBypassedIntegrationEvent` | `ProcessingJobBypassed` | AssetManagement | none (contract fine) — but the write-model spec's "Published Integration Events" table omits Created/Bypassed entirely (PJ-M6) |

Positives: `FailureCategory` names are deliberately aligned with `AssetManagement.FailureCategory` for string round-trip (`ProcessingJobFailureCategory.cs`) — good, explicit contract hygiene. Every published event carries `EventVersion`.

### Consumed (7 handlers)

| Handler | Event | Issue | Severity |
|---|---|---|---|
| `AssetUploadConfirmedEventHandler` | `AssetUploadConfirmedIntegrationEvent` | mints new `JobId` per delivery, no idempotency guard, ignores `Create` dispatch `Result` then runs the scan on a possibly-missing job (PJ-H1/PJ-M3) | High |
| `AssetUploadInitiatedEventHandler` | `AssetUploadInitiatedIntegrationEvent` | intentional no-op; subscription retained pending CDK cleanup — documented, benign | — |
| `ProcessingJobCreatedSagaHandler` | `ProcessingJobCreatedIntegrationEvent` | `catch (Exception){ log "will be retried" }` — **not** rethrown → ACKed, not retried (PJ-H2) | High |
| `AssetValidationPassedSagaHandler` | `AssetValidationPassedIntegrationEvent` | same swallow (PJ-H2); is the **only** consumer of this event → pipeline never runs (PJ-C2) | High |
| `AssetProcessingCompletedSagaHandler` | `AssetProcessingCompletedIntegrationEvent` | same swallow (PJ-H2) | High |
| `AssetProcessingFailedSagaHandler` | `AssetProcessingFailedIntegrationEvent` | same swallow (PJ-H2) | High |
| `AssetProcessingTimeoutRecoveredSagaHandler` | `AssetProcessingTimeoutRecoveredIntegrationEvent` | same swallow (PJ-H2) | High |

**Cross-cutting consumer issues:** the five saga handlers are structurally identical and all swallow (PJ-H2); the upload handler additionally ignores dispatch results (PJ-M3). `TenantId` is taken from the event payload body throughout (`TenantId.From(e.TenantId)`), not from the SQS message attribute the projectors and conventions rely on (CLAUDE.md "never from payload body"); given these are internal system events it is lower-risk than in AssetManagement, but it is the same convention deviation (PJ-M5-adjacent).

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| Summary projector: `ProcessingJobFailed` | `status = Failed`, `statusText = <reason>` (`read-model.md:75`) | Writes `Status = "Succeeded"`, `StatusText = reason` (`ProcessingJobSummaryProjector.cs:67`) | **Critical** | Set `Status = Failed` |
| Bypass projection | (spec omits Bypassed entirely) | `ProcessingJobBypassed` projected by **no** projector → row stuck `Queued` | High | Add Bypassed handlers to both read projectors + index; add to spec |
| `AssetProcessingJobIndex.Status` | "Mirrors current job status" (`write-model.md:229`) | Succeeded/Failed both write `Running`; Bypassed/TimeoutRecovered unhandled (`AssetJobIndexProjector.cs:39-40,49-50`) | High | Write the true terminal status; add missing handlers |
| Create idempotency | Handler calls `GetByAssetIdAsync`; no-op if job exists (`write-model.md:134-137`) | No such call; **new `JobId` per delivery**; repo interface lacks `GetByAssetIdAsync` (`IProcessingJobRepository.cs`) | High | Implement asset-existence guard or deterministic `JobId` |
| Pipeline completion driver | Worker starts job then runs pipeline → `CompleteProcessingJobCommand` (`scenarios.md P-1 §9-10`) | `AssetProcessingWorker.ProcessAsync` registered but **never invoked** in-module | High | Wire the worker (verify host) or remove the redundant saga `Start` |
| `List` query handler | `ListProcessingJobsForAssetIdHandler` exists (`read-model.md:119-120`) | No handler; query unregistered | High | Implement + register the handler |
| Virus scan / renditions | Real scan; renditions per content type | `outcome = "Passed"` hardcoded; pipeline throws `NotImplementedException` | High (deferred) | Implement before production; scan is a compliance control |
| `Fail`/`Complete` idempotency | "`FailProcessingJobCommand` is idempotent — no-op if already succeeded" (`scenarios.md P-3`) | Returns `InvalidOperation` when not `Running` (`ProcessingJob.cs:98,105`) | Medium | Make terminal re-delivery a success no-op |
| Bypass in write-model | Method/event/status **absent** from methods, domain-events, lifecycle, VO tables; only the commands table lists `BypassProcessingJobCommand` | `Bypass()`, `ProcessingJobBypassed`, `Bypassed` status all implemented | Medium | Update the write-model spec to match code |
| Timeout recovery in write-model | `ProcessingJobTimeoutRecovered` absent from spec | Implemented + projected | Medium | Add to spec |
| Saga creation trigger | `write-model.md:203`: created on `AssetValidationPassed`, **not** `ProcessingJobCreated` | Created on `ProcessingJobCreatedIntegrationEvent` (`AssetIngestionSaga.cs:333`), matching `context-overview.md:152` | Medium | Reconcile the two spec docs to the code |
| Timeout-scanner target | `scenarios.md P-3`: scanner dispatches `FailProcessingJobCommand` (job) | Saga status doc says scanner dispatches `FailAssetProcessingCommand` (asset) — a cross-BC command | Medium | Reconcile; state the single source of truth |
| Repository interface | `GetByIdAsync` + `GetByAssetIdAsync` + `SaveAsync` (`write-model.md:158-163`) | Only `GetByIdAsync` + `SaveAsync` (`IProcessingJobRepository.cs`) | Medium | Align interface to actual idempotency design |
| Rendition DTO shape | `RenditionResult { RenditionType, StorageKey, ContentType, SizeBytes }` (`write-model.md:69`) | VO adds `Width/Height`; DTOs rename to `FileSizeBytes`, drop `Width/Height` | Low | Pick one field name; decide whether dimensions are carried |
| Detail table name in comments | Detail = `media-processing-job` (`read-model.md:37`) | Projector/read-model comments say `media-processing-jobs` (summary) | Low | Fix doc-comments |
| `Start`/`Fail` timestamps | (implied deterministic) | `DateTimeOffset.UtcNow` in the aggregate | Low/Med | Inject via `IClock`/parameter |

---

## 12. Bugs

### Critical

**PJ-C1 — Summary projector reports a failed job as `Succeeded`.**
`ProcessingJobSummaryProjector.cs:67`. On `ProcessingJobFailed` the projector writes `current with { Status = nameof(ProcessingJobStatus.Succeeded), StatusText = e.Reason, ... }` — a copy-paste of the `Succeeded` handler. Every genuinely failed job appears in `media-processing-jobs` (the list/status table powering `ListProcessingJobsForAssetIdQuery` and the worker's idempotency-style checks) with `Status = "Succeeded"`, the failure reason hidden in the free-text `StatusText`.
*Why it's a problem:* this is the operator/ops-facing status of the pipeline; a failed transcode/timeout reads as success, defeating the observability the read model exists to provide, and any consumer filtering on `Status == "Failed"` will never find failed jobs. *Impact:* silent misreporting of processing failures for a regulated-records platform. *Recommendation:* set `Status = nameof(ProcessingJobStatus.Failed)`; add a projector unit test asserting the status per event.

### High

**PJ-C2 / PJ-H5 — `Running` has no completion driver; `AssetProcessingWorker` is registered but never invoked; `Start`/`Bypass` are dual-dispatched.**
Verified by reference search: `IAssetProcessingWorker.ProcessAsync` (the only code that runs renditions and dispatches `CompleteProcessingJobCommand`/`FailProcessingJobCommand`) is registered (`WriteModel.Infrastructure/ServiceCollectionExtensions.cs:125`) but **has no caller** in the module. The sole consumer of `AssetValidationPassedIntegrationEvent` is `AssetValidationPassedSagaHandler` → `AssetIngestionSaga.OnAssetValidationPassedAsync`, which dispatches `StartProcessingJobCommand` (or `Bypass`) and updates saga state — but never runs the pipeline. Consequently, for a capable asset the job goes `Queued → Running` and then **waits for the saga timeout** (`ProcessingDispatched` + `TimeoutAt`) → `FailProcessingJobCommand`. Conversely, the worker (if a host project *does* wire it to `AssetValidationPassed`, as its `ProcessAsync(AssetValidationPassedIntegrationEvent)` signature implies) **also** dispatches `Start`/`Bypass` — duplicating the saga and doubling those commands (idempotency saves correctness but not intent).
*Why it's a problem:* the happy path (P-1) cannot complete under the reviewed wiring; and the `Start`/`Bypass` transition has ambiguous ownership between two components reacting to the same event. *Impact:* every image/video/audio job times out and fails, or (if host-wired) redundant command traffic + a race. *Recommendation:* decide the single owner of `Start`/`Bypass` (saga *or* worker, not both); wire `AssetProcessingWorker` to the event that should drive the pipeline and confirm it in the host; add an integration test that carries a capable asset to `Succeeded`.

**PJ-H1 — No create-idempotency guard; a fresh `JobId` is minted per delivery → duplicate jobs.**
`AssetUploadConfirmedEventHandler.cs:33` calls `ProcessingJobId.New()` on every invocation, then dispatches `CreateProcessingJobCommand` and runs the scan — with **no** `GetByAssetIdAsync` check (the spec's idempotency design, `write-model.md:134-137`), which cannot even be performed because `IProcessingJobRepository` lacks the method. On at-least-once redelivery of `AssetUploadConfirmedIntegrationEvent`, a **second `ProcessingJob` with a different `JobId`** is created for the same asset; both emit `ProcessingJobCreated` (starting two sagas keyed by `AssetId` — the second is deduped by the saga, good) and both run a scan cascade; the `AssetProcessingJobIndex` (keyed by `AssetId`) is overwritten to the newer `JobId`, orphaning the first job. *Recommendation:* derive `JobId` deterministically from `AssetId`, or add `GetByAssetIdAsync` and no-op when a job exists; also check the `Create` dispatch `Result` before running the scan.

**PJ-H2 — All five saga/consumer handlers swallow exceptions while logging "message will be retried".**
`ProcessingJobCreatedSagaHandler.cs:23-26`, `AssetValidationPassedSagaHandler.cs:23-26`, `AssetProcessingCompletedSagaHandler.cs:22-25`, `AssetProcessingFailedSagaHandler.cs:22-25`, `AssetProcessingTimeoutRecoveredSagaHandler.cs:24-27`. Each wraps the saga call in `try { … } catch (Exception ex) { logger.LogError(ex, "… message will be retried"); }` and then returns normally. In AWS.Messaging/SQS a handler that returns without throwing is treated as success and the message is **deleted** — it is **not** retried. A transient fault (DynamoDB throttle, optimistic-concurrency conflict, downstream 5xx) therefore silently drops the saga transition: the asset never advances, no retry, no DLQ, and the log line asserts the opposite of what happens.
*Why it's a problem:* this converts every transient infrastructure blip into permanent stuck state, and actively misleads on-call by claiming a retry will occur. *Impact:* stuck-`Queued`/`Running` assets across the pipeline with no automated recovery. *Recommendation:* remove the catch (let the handler throw so SQS retries → DLQ), or catch only to classify: rethrow retryable faults, ACK only genuine idempotent no-ops; add a DLQ + alarm.

**PJ-H3 — `ProcessingJobBypassed` is projected nowhere → bypassed (document) jobs show `Queued` forever.**
Neither `ProcessingJobSummaryProjector` nor `ProcessingJobDetailProjector` implements `IProjectionHandler<ProcessingJobBypassed, …>`, and `AssetJobIndexProjector` doesn't handle it either. `Bypassed` is the terminal state of the entire P-2 document fast-exit path (the common case for PDFs/documents). *Impact:* `GetProcessingJobByIdQuery` and the summary list report every successfully-bypassed document job as `Queued` indefinitely — the read models never reflect a whole category of terminal jobs; the `AssetProcessingJobIndex` likewise stays `Queued`. *Recommendation:* add `ProcessingJobBypassed` handlers to both read projectors (`Status = Bypassed`, `CompletedAt`, `ProjectedVersion`) and to the index projector; add the state to the read-model spec.

**PJ-H4 — `AssetProcessingJobIndex` records `Running` for Succeeded and Failed jobs.**
`AssetJobIndexProjector.cs:39-40` (`ProcessingJobSucceeded` → `Status = Running`) and `:49-50` (`ProcessingJobFailed` → `Status = Running`). The write-side reference index's `Status` never reflects a terminal state after `Start`; `Bypassed`/`TimeoutRecovered` are unhandled entirely. *Why it's a problem:* the index is documented to "mirror current job status" and is the write-side source for `AssetId → job` resolution; any present or future consumer that gates on the index status (e.g. "skip if job already terminal") will misbehave. Today the saga only reads `JobId` from it, limiting blast radius — hence High not Critical — but it is a latent data-integrity bug. *Recommendation:* write the actual event status in each handler; add `Bypassed` handling.

**PJ-H6 — Virus scan and rendition pipeline are unimplemented; scan always returns `Passed`.**
`AssetValidationWorker.cs:36` hardcodes `outcome = "Passed"` (TODO: real ClamAV/scan); `AssetProcessingWorker.cs:113` throws `NotImplementedException` for the whole rendition/metadata pipeline. *Why it's a problem:* for a compliance-grade, government/enterprise records platform, "virus scan always passes" is a security control that does not exist; and every capable-asset job fails processing (compounding PJ-C2). Clearly deferred work, but **blocking for a production-readiness sign-off**. *Recommendation:* implement both before production; until then, treat the context as non-functional for the happy path and gate release on it.

**PJ-H7 — `ListProcessingJobsForAssetIdQuery` has no handler and is unregistered → unreachable.**
The query type exists (`ListProcessingJobsForAssetId/ListProcessingJobsForAssetIdQuery.cs`) but there is no `ListProcessingJobsForAssetIdHandler` file and it is not added in `AddProcessingReadModelQueries` (`ReadModel.Infrastructure/ServiceCollectionExtensions.cs:50-54` registers only `GetProcessingJobById`). The read-model spec references the handler. *Impact:* the documented "list jobs for an asset" capability (used by ops and, per read-model.md, the worker's idempotency check) does not exist. *Recommendation:* implement and register the index-query handler, or remove the query and its spec entry.

### Medium

- **PJ-M1** `Complete()`/`Fail()` are not idempotent on terminal re-delivery — they return `InvalidOperation` when `Status != Running` (`ProcessingJob.cs:98,105`), so a duplicate completion or a timeout-vs-completion race yields a failed `Result`, not the no-op the P-3 scenario and the saga's own compensation comment (`AssetIngestionSaga.cs:164` "FailProcessingJobCommand is a no-op") promise. Combined with PJ-H2 the failed `Result` may be swallowed, masking the race. *Recommendation:* return success when the job is already in the intended terminal state.
- **PJ-M2** Scan-failed / `VirusDetected` orphans the job in `Queued` — `RecordScanResult` records but never transitions, and no downstream ever `Start`/`Bypass`/`Fail`s the job for a failed scan, so the aggregate and its read-model rows sit `Queued` forever (§3 PJ-L-life1). `Outcome` is also an unvalidated string. *Recommendation:* add a terminal job transition for scan failure (e.g. `Fail(ValidationFailure)` or a dedicated `ScanFailed`), and model `Outcome` as an enum/VO.
- **PJ-M3** Command-dispatch `Result`s ignored: `AssetUploadConfirmedEventHandler.cs:35` ignores the `CreateProcessingJobCommand` result then runs the scan against a possibly-uncreated job; `AssetProcessingWorker.cs:97` ignores the `FailProcessingJobCommand` result. Silent loss. *Recommendation:* inspect results; fail loudly (throw) so SQS retries.
- **PJ-M4** Non-deterministic wall-clock in the aggregate: `Start()` and `Fail()` use `DateTimeOffset.UtcNow` (`ProcessingJob.cs:109,144`) instead of an injected clock/parameter, unlike their four peers. Hurts testability and audit-timestamp control. *Recommendation:* pass `startedAt`/`failedAt` from the handler's `IClock`.
- **PJ-M5** Architecture-statement contradiction: the context claims "no cross-BC command dispatch occurs," yet the `AssetIngestionSaga` (embedded in Processing) reacts to AssetManagement events and — per `AssetIngestionSagaStatus.AwaitingValidation` doc — the validation-timeout path dispatches AssetManagement's `FailAssetProcessingCommand` on the `Asset`, while `scenarios.md P-3` says the scanner dispatches `FailProcessingJobCommand` on the job. The two spec docs and the stated rule disagree. *Recommendation:* pick one compensation target and make the docs consistent; if the saga legitimately spans both BCs, state that explicitly and drop the "no cross-BC dispatch" absolute.
- **PJ-M6** The `processingjob.write-model.md` spec is materially behind the code: its Methods table omits `Bypass()`, its Domain-Events table omits `ProcessingJobBypassed` and `ProcessingJobTimeoutRecovered`, its Status Lifecycle and read-model enum omit `Bypassed`, and its "Published Integration Events" table lists 4 of the 6 events — yet the same doc's Commands table *does* list `BypassProcessingJobCommand` (internally inconsistent). *Recommendation:* regenerate the write-model spec from the implemented aggregate before the next wiki publish.
- **PJ-M7** Spec self-contradiction on saga creation trigger (`write-model.md:203` says on `AssetValidationPassed`; `context-overview.md:152` and the code say on `ProcessingJobCreated`). *Recommendation:* fix `write-model.md`.

### Low

- **PJ-L1** `RenditionResult.Width/Height` are dropped by both the integration mapper (`ProcessingRenditionDto`) and the read-model DTO (`RenditionResultDto`) — extracted dimensions never propagate. *Recommendation:* either carry them or remove the VO fields.
- **PJ-L2** Field-name drift: `FileSizeBytes` (code) vs `SizeBytes` (spec DTOs); VO has 6 fields vs the spec VO's 4. *Recommendation:* align on one name.
- **PJ-L3** Doc-comment drift: `ProcessingJobDetailProjector`/`ProcessingJobDetailReadModel` comments cite table `media-processing-jobs` and SK `JOB#{JobId}` for the **detail** model, but the actual detail table is `media-processing-job` with the `DETAIL` discriminator (`ReadModel.Infrastructure/ServiceCollectionExtensions.cs:61`); `GetProcessingJobByIdQuery` comment claims a SagaOrchestrator consumer that uses the reference index instead.
- **PJ-L4** `CompleteProcessingJobCommand` carries domain VOs (`RenditionResult`, `ExtractedMetadata`) directly — minor CQRS-purity smell for an internal command.
- **PJ-L5** Integration-event doc shapes are stale: `ProcessingJobStartedIntegrationEvent` carries `AssetId`+`EventVersion` not shown in the context-overview snippet; the write-model "Published Integration Events" table omits Created/Bypassed (also PJ-M6).

---

## 13. Design Flaws

1. **Read-side/write-side divergence is systemic, not incidental.** Three independent projection surfaces disagree with the aggregate: the summary projector inverts Failed→Succeeded (PJ-C1), the index projector freezes terminal jobs at `Running` (PJ-H4), and `Bypassed` is unprojected everywhere (PJ-H3). Each is individually a small bug; together they mean the read models cannot be trusted for job status — the core value proposition of the read side. A projector test matrix (event × expected status) would have caught all three.

2. **Ownership of the `Start`/`Bypass` transition is split between the saga and the worker.** Both `AssetIngestionSaga.OnAssetValidationPassedAsync` and `AssetProcessingWorker.ProcessAsync` react to `AssetValidationPassedIntegrationEvent` and both dispatch `Start`/`Bypass`, leaning on aggregate idempotency to stay correct. Meanwhile the worker — the piece that actually completes the job — is unwired in the reviewed slice (PJ-C2). The result is simultaneously redundant (two drivers) and incomplete (no completion driver). This is the module's biggest architectural weakness: the pipeline's "who advances the job" is ambiguous.

3. **"Fire-and-forget" consumers mistake swallowing for idempotency.** Catching every exception and logging "will be retried" (PJ-H2) turns transient faults into permanent stuck state and erases the retry/DLQ safety net, exactly as flagged in the AssetManagement review's F-C1/F-C2 — the same anti-pattern, repeated in the Processing consumers.

4. **Idempotency is claimed uniformly but implemented unevenly.** `Start`/`Bypass` are idempotent; `Create`/`Complete`/`Fail` are not (PJ-H1/PJ-M1). At-least-once delivery is a first-class reality here (every handler is SQS-driven), so partial idempotency is a design flaw, not a detail.

5. **A cross-context saga lives inside the Processing write model.** `AssetIngestionSaga` depends on `Magiq.Media.AssetManagement.Events` and orchestrates asset-level compensation. That may be intentional, but it contradicts the context's own "no cross-BC command dispatch" statement (PJ-M5) and couples Processing's deployable to AssetManagement's contract assembly. Ownership of the saga (Processing vs a neutral orchestrator module) should be an explicit, documented decision.

---

## 14. Design Gaps

- **No completion path wired for `Running`** — the pipeline worker is unreferenced (PJ-C2).
- **No terminal transition for scan-failed / virus jobs** — orphaned `Queued` aggregates (PJ-M2).
- **No `Bypassed` projections** on either read model or the index (PJ-H3).
- **No DLQ / dead-letter or retry semantics** around the saga consumers — swallowed failures vanish (PJ-H2).
- **No real virus scan and no rendition/metadata pipeline** — both are TODO stubs (PJ-H6); the scan is a missing security control.
- **No `List`-query handler** — a documented read capability is unreachable (PJ-H7).
- **No optimistic-concurrency-aware retry** in consumers (reload-before-retry) — and, because failures are swallowed, no surface for concurrency conflicts at all.
- **No idempotent create** — duplicate `AssetUploadConfirmed` yields duplicate jobs (PJ-H1).
- **No monitoring/metric** on stuck jobs (jobs `Queued`/`Running` past their budget) beyond the saga's `SagasApproachingTimeout` metric, which does not cover orphaned-`Queued` (scan-failed) jobs.
- **`GetByAssetIdAsync` absent** from the repository interface, so the spec's idempotency design cannot be implemented as written.

---

## 15. Missing Features

- **`ListProcessingJobsForAssetIdHandler`** (query + registration) — specified, not implemented (PJ-H7).
- **Idempotent `CreateProcessingJob`** (asset-existence guard or deterministic `JobId`) — specified in `write-model.md`, absent (PJ-H1).
- **`ProcessingJobBypassed` projector handlers** on summary, detail, and index projectors (PJ-H3).
- **A terminal job transition on scan failure / virus** (`RecordScanResult` currently dead-ends the job) (PJ-M2).
- **Real virus scan** (`AssetValidationWorker`) and **rendition/metadata pipeline** (`AssetProcessingWorker`) (PJ-H6).
- **Wiring that drives `Running → Succeeded`** (invoke the processing worker) and a single owner for `Start`/`Bypass` (PJ-C2).
- **DLQ + retry** for the saga consumers (PJ-H2).
- **Idempotent `Complete`/`Fail`** (no-op on terminal re-delivery) to honour the P-3 guarantee (PJ-M1).
- **Spec updates** bringing `write-model.md` in line with Bypass + timeout-recovery and reconciling the saga-creation-trigger contradiction (PJ-M6/PJ-M7).

---

## 16. Recommendations (prioritised)

### 1 — Correctness
- **R1 (Critical).** Fix `ProcessingJobSummaryProjector` `ProcessingJobFailed` → `Status = Failed` (PJ-C1); add a projector event×status test matrix that also covers PJ-H3/PJ-H4.
- **R2 (High).** Establish a single, working completion driver: wire `AssetProcessingWorker` to the event that should run the pipeline, make the saga the sole owner of `Start`/`Bypass` (or vice-versa), and add an integration test carrying a capable asset to `Succeeded` (PJ-C2/PJ-H5). Confirm the host wiring in `hosts/ProcessingWorker`.
- **R3 (High).** Make consumers observe failures: remove the blanket `catch` (or rethrow retryable faults), add a DLQ + alarm, and inspect command-dispatch `Result`s (PJ-H2/PJ-M3).

### 2 — Data Integrity
- **R4 (High).** Add `ProcessingJobBypassed` handlers to both read projectors and the index projector; write true terminal status in `AssetJobIndexProjector` for Succeeded/Failed and add `TimeoutRecovered` (PJ-H3/PJ-H4).
- **R5 (High).** Implement idempotent create — deterministic `JobId` from `AssetId`, or `GetByAssetIdAsync` + no-op — and add the method to `IProcessingJobRepository` (PJ-H1).
- **R6 (Medium).** Make `Complete`/`Fail` no-op on their intended terminal state so re-delivery and the timeout/completion race are honest no-ops (PJ-M1).

### 3 — Security
- **R7 (High).** Implement the real virus scan before production; treat "always Passed" as a missing compliance control, and add a terminal job transition + read-model surface for `VirusDetected`/scan-failed so infected/failed jobs are visible, not orphaned (PJ-H6/PJ-M2).

### 4 — Domain Modelling
- **R8 (Medium).** Model scan `Outcome` as an enum/value object rather than a raw string (PJ-M2/PJ-P7-DTO); decide whether `RenditionResult.Width/Height` are carried end-to-end or removed (PJ-L1).
- **R9 (Medium).** Inject timestamps into `Start()`/`Fail()` via `IClock` for determinism and testability (PJ-M4).

### 5 — Lifecycle
- **R10 (Medium).** Add a terminal path for `Queued` jobs that can never advance (scan failure, worker crash before `Start`) so they don't accumulate as orphans; add a stuck-job metric covering `Queued` past the validation budget (PJ-M2/§14).

### 6 — API
- **R11 (High).** Implement and register `ListProcessingJobsForAssetIdHandler`, or remove the query and its spec entry (PJ-H7). (No HTTP/error-contract work is needed — the context correctly has no public surface.)

### 7 — Events
- **R12 (Medium).** Reconcile integration-event field naming (`SizeBytes` vs `FileSizeBytes`) and the write-model "Published Integration Events" table with the six events actually published; confirm the platform envelope supplies message/idempotency ids (PJ-L2/PJ-L5).

### 8 — Maintainability
- **R13 (Medium).** Regenerate `processingjob.write-model.md` from the implemented aggregate (Bypass, TimeoutRecovered, Bypassed status, full event/command set) and fix the saga-creation-trigger contradiction across `write-model.md`/`context-overview.md` before the next wiki publish; fix the detail-table doc-comments (PJ-M6/PJ-M7/PJ-L3).

### 9 — Performance
- **R14 (Low).** None material at this scale; the index-query GSI and cursor pagination are appropriate once the `List` handler exists (R11).

### 10 — Scalability
- **R15 (Medium).** Clarify saga ownership (Processing-embedded vs neutral orchestrator) and its cross-BC command dispatch so the deployable coupling and compensation target are intentional and documented (PJ-M5 / §13-5).

---

### Top 5 before production
1. **PJ-C1 / R1** — summary projector reporting **failed jobs as Succeeded** (operators cannot see processing failures).
2. **PJ-C2 / R2** — the `Running` state has **no completion driver wired**; capable-asset jobs only ever time out (happy path is broken).
3. **PJ-H2 / R3** — saga consumers **swallow every failure** and falsely log "will be retried" — no retry, no DLQ, permanent stuck state.
4. **PJ-H3 + PJ-H4 / R4** — **`Bypassed` unprojected** (all document jobs stuck `Queued`) and the index **frozen at `Running`** for terminal jobs.
5. **PJ-H1 / R5** & **PJ-H6 / R7** — **no create-idempotency** (duplicate jobs on redelivery) and **no real virus scan** (missing compliance control on a regulated-records platform).
