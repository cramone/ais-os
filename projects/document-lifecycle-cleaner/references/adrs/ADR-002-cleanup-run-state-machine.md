# ADR-002 — CleanupRun as Persisted State Machine

**Date:** 2026-07-13  
**Status:** Accepted

---

## Context

The process spans multiple phases over a potentially long wall-clock time. The spec requires:

- The process must be **resumable** — a restart must not restart from Step 1.
- Only **one active run** may exist at a time.
- Per-document move failures (Step 9) must be tracked individually so the identify-skip-resume behaviour works.
- The process needs an **audit trail** appropriate for a records-management context.

Without explicit state modelling, phase transitions and failure recovery would require ad-hoc logic spread across job handlers.

---

## Decision

Model each execution as a persisted `CleanupRun` record with:

- A `Status` field tracking the overall run state (`NotStarted`, `Running`, `AwaitingInput`, `Cancelled`, `Failed`, `Completed`, `Abandoned`).
- A `CurrentPhase` / `CurrentStep` field so a restart reads the last completed point and resumes from there.
- A `CleanupRunDocument` table recording per-document move status (`Pending`, `Moved`, `Failed`) — enables Step 9 retry to re-process only failed documents.
- A `CleanupRunFolder` table recording per-folder selection state and deletion outcome.
- A `CleanupRunPhaseLog` append-only event log for auditability.

The single-active-run constraint is enforced at the API layer: `POST /api/runs` returns HTTP 409 if any run has a non-terminal status.

---

## Consequences

- Resumability, auditability, and single-run enforcement are structural — not dependent on runtime state.
- Reset and Retry actions (error recovery) are implemented by mutating `MoveStatus` records and re-enqueuing a Hangfire job — no special Hangfire primitives needed.
- The state machine shape means the domain is a **workflow**, not a rich aggregate — full event sourcing is deliberately not applied (see rationale in decisions/log.md 2026-07-13).
- `CleanupRunPhaseLog` doubles as the failure context shown to the operator in the job details view.

---

## Amendment — 2026-08-05: Name Normalization phase + audit lock

Decision detail in `decisions/log.md` [2026-08-05]. Specified, not yet implemented.

A new **Name Normalization** phase is inserted into the pipeline **before archival** (a new `RunPhase.Normalization`, running as its own Hangfire job that chains to archival on success). It works around the SOAP double-space bug (see ADR-004 amendment) by renaming, in the source repository, every candidate document/folder-level whose name holds a run of consecutive whitespace, so the later `Move` can address and move it. This adds a new **Step 8**; the archival/cleanup steps renumber accordingly in the spec (Archival → 9–10, Cleanup → 11–12), though the as-built code keeps the pre-insertion numbers until the phase is built.

Two state-machine consequences, both of which **must not be missed** when the phase is implemented:

1. **Renames are recorded.** Each rename (item type, original path/name, new normalized name, operator/process ticket, timestamp) is persisted against the run — a new `CleanupRunRename`-style store — and written to `CleanupRunPhaseLog`. This is a hard requirement, not incidental logging: the record is the audit of what was changed in NATA's live repository.

2. **Audit lock on deletability.** Normalization is the **first phase that mutates the customer's source repository**, and a rollback does **not** undo a rename (it returns moved documents and tears down a run-created archive only). So once a run has entered the Normalization phase it is permanently an **audit**: `CleanupRun.DescribeDeletability` must never return `CanDelete` for it — it can be **archived** (retained for the record) and its document moves can still be rolled back, but the run row and its rename log are never deleted. Concretely, the deletability tier for a run that reached Normalization can be `Reversible`/`Irreversible` but never `NoChanges`, regardless of how far it then progressed or whether its moves were later rolled back. This is spec Rule 7.

---

## Amendment — 2026-08-05: operation audit trail (`CleanupRunOperation`)

Decision detail in `decisions/log.md` [2026-08-05]. First implementation slice in the product tree.

`CleanupRunPhaseLog` records **phase transitions** (Started/Completed/Failed/Reset/Retried/Cancelled) — it does not record what the run did to each object. The state machine is therefore extended with a second, **object-level append-only log**: `CleanupRunOperation`. Every mutating primitive a run executes against MAGIQ — `CreateDomain`, `CreateFolder`, `Move`, `DeleteFolder`, `DeleteDomain`, `Purge`, `Rename` (when Normalization lands), the reactive `RuleRelax`/`RuleRestore`, and the operator `OperatorOverride` / `PurgeAuthorised` decisions — is written as one immutable row (per-run `Seq`, timestamp, phase/step, outcome, SOAP `success`, error, operator). It is inserted at the SOAP call sites (`RunPhaseExecutor`, `ArchiveLibraryTeardown`) and in the review/confirm/purge handlers, and only ever read back via `GET /api/runs/{runId}/operations`.

Two points that follow from the existing state-machine design:

1. **Move granularity.** Documents are persisted per-batch (accepted edge, 2026-07-28), so moves are audited **batch-summary** — one row per batch carrying moved/failed counts in `Detail` — not one row per document, keeping the 10k-document run's write cost unchanged.

2. **Complements, does not replace.** `CleanupRunPhaseLog` stays (phase-grain failure context in the job view). `CleanupRunRename` (Name Normalization) stays — it doubles as resume state and carries the audit-lock — and a rename also writes a `CleanupRunOperation` row so the object-level trail is complete. Audit rows are cleared by `HardDeleteAsync` along with the other child tables (a run that reached Normalization can't be hard-deleted anyway, per Rule 7).

Schema: migration `0002_operation-audit-and-register-snapshots.sql`; table shape in `spec/dev-spec.md` > Data Model > `CleanupRunOperation`.
