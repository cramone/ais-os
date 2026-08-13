# Step 10 Move-Failure Retry — Implementation Plan

_Created 2026-08-10. Owner: Chase. Author of plan: Claude. Status: **implemented in the working tree (uncommitted).**_

> **Purpose.** Let an operator work through Step 10 document-move failures — retrying them individually or
> all together — instead of the only recovery being a whole-phase Retry. When every failure clears, the run
> pauses after archival so the operator explicitly proceeds to cleanup/purge.

> **Refinement (2026-08-10, after first UX review).** Retry is now **synchronous and per-row inline**, not a
> background job: `POST …/archival/move-failures/retry` returns each targeted document's outcome and the panel
> shows *Retrying… → Moved* in the row (resolved rows stay listed), without disturbing the main run-progress
> panel. Per-row Retry no longer needs a checkbox (the selection UI was dropped); Retry-all calls the endpoint
> once per failed row so each shows its own progress. Implementation: `IMoveFailureRetryer.RetryDocumentMovesInlineAsync`
> (on `RunPhaseExecutor`, `MoveDocumentsAsync(…, emitProgress:false)`) — the async `RetryDocumentMovesAsync` /
> `StartMoveFailureRetry` were removed.

**Decisions locked with Chase (2026-08-10):**

- **After a retry clears the last failure:** the run **stops and lets the operator proceed** — it pauses
  (`AwaitingInput`, Archival phase) and the operator triggers cleanup, rather than auto-continuing into the
  (irreversible) purge.
- **UI:** a **Document move failures** panel in the Job Details view (best-practice placement, alongside the
  run progress).

---

## What was built

### API (`DocumentLifecycleCleaner`)

- **Run state — `Domain/CleanupRun.cs`:** `PauseAfterArchival()` (Running → AwaitingInput, Archival, step 10)
  and `ResumeAfterArchival()` (AwaitingInput+Archival → Running).
- **Executor — `Pipeline/RunPhaseExecutor.cs`:** `RetryDocumentMovesAsync(runId, documentRowIds?, ct)` —
  loads the failed set (narrowed to the selection when given), reuses `EnsureArchiveDestinationAsync` +
  `MoveDocumentsAsync` (per-folder relax-once, per-document audit), then: any still failed → `FailArchival`;
  all clear → `PauseAfterArchival` (no cleanup chaining). No library create (the library already exists).
- **Pipeline — `IRunPipeline` / `RunPipeline` / `FakeRunPipeline`:** `StartMoveFailureRetry(runId, ids?)`
  (enqueue only — no continuation).
- **Features — `Features/Runs/Archival/`:**
  - `GET /runs/{runId}/archival/move-failures` → `MoveFailuresResponse` (items + `FailedCount` +
    `CanRetry`/`CanContinue`).
  - `POST /runs/{runId}/archival/move-failures/retry` (`{ documentRowIds? }`) → guards `Failed`+Archival &
    non-empty failures (`409 RunNotRetryable` / `409 NoFailuresToRetry`), `Retry()` + `StartMoveFailureRetry`.
  - `POST /runs/{runId}/archival/continue` → guards AwaitingInput+Archival (`409 RunNotAwaitingCleanup`),
    `ResumeAfterArchival()` + `StartCleanup`.
  - All non-GET routes owner-guarded by the global pre-processor; each endpoint carries full `Configure()` +
    `Version(1)` and maps Results→HTTP via `DlcEndpoint`.

### SPA (`DocumentLifecycleCleaner.Web`)

- **`api/runs.ts`:** `MoveFailure`/`MoveFailures` types; `getMoveFailures`, `retryMoveFailures`,
  `continueToCleanup`.
- **`components/MoveFailuresPanel.tsx`:** lists failures (path, error, attempts) with checkbox multi-select,
  per-row Retry, Retry selected, Retry all; polls while the run is active; when all clear and the run is
  paused post-archival, shows **Continue to cleanup**. Self-hides when there is nothing to show. Owner-only.
- **`pages/JobDetailsView.tsx`:** mounts the panel in the progress branch (covers both `Failed` and the new
  `AwaitingInput`+Archival pause).

### Tests

- `CleanupRunTests` — the two new transitions + guards.
- `MoveFailuresHandlerTests` — list (flags), retry all/selected, retry guards, continue + guard.
- `RunPhaseExecutorArchivalCreateDomainTests` — retry that clears all → pause; retry that still fails → Failed.
- New reusable `Fakes/FakeCleanupRunDocumentStore`.

## Behaviour notes / for the record

- Only the **recovery** path gains the post-archival checkpoint; a clean archival run still auto-chains
  cleanup (which then pauses at the Step 12 purge as before).
- The generic **Retry (resume)** / **Reset** lifecycle actions are unchanged and still available on a failed
  run (whole-phase recovery); the panel is the granular, per-document path.
- Audit lock (Rule 7) is unaffected — moves already tripped it; a paused-after-archival run stays an audit.

## Verification

- SPA `tsc --noEmit` clean. C# validated by reference/pattern checks (no .NET SDK on the bridge VM) — Chase
  runs `dotnet build` + `dotnet test` and `npm run build`, and owns branch/commit/PR.

## Spec-sync (done in step)

`spec/…v0.6.md` (Step 10 "Working through move failures", `AwaitingInput` state, History),
`spec/dev-spec.md` (endpoint table, Step 10 retry-loop note), `decisions/log.md` [2026-08-10], `CLAUDE.md`.
