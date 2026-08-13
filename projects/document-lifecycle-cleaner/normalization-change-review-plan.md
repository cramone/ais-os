# Name Normalization — Change Review & Before/After Export: Implementation Plan

_Created 2026-08-10. Owner: Chase. Author of plan: Claude. Status: **implemented in the working tree (uncommitted).**_

> **Fix (2026-08-10).** First run surfaced a loop: after submitting resolutions the resolver re-appeared and the
> rename list never showed. Cause — `GET …/normalization/plan` keeps the **Resolved** conflict rows (they are
> the durable merge/duplicate-delete action log), and the SPA branched on `conflicts.length`, so a clean plan
> (only Resolved rows left) still rendered the resolver. Fixed in `NormalizationReview.tsx`: the resolver,
> submit payload and "conflicts remain" gate now key off **pending** conflicts only, and the change list shows
> the renames **plus** the resolved folder-merges / duplicate-deletes.

> **Purpose.** Extend the Step 8 Name Normalization gate so an operator can (1) **review every folder
> and document name change before it is applied**, not just the conflicts; (2) still resolve name
> conflicts as today; and (3) **download a before → after name-change list** (Excel/CSV). Builds directly
> on the conflict gate shipped from `normalization-conflict-gate-plan.md`.

**Decisions locked with Chase (2026-08-10):**

- **Gate:** the run pauses at Step 8 **whenever normalization would change a name** — with or without
  conflicts. The operator reviews the full change list, resolves any conflicts, then explicitly confirms
  before 8b executes. A run with **zero** renames and zero conflicts still auto-continues (no empty gate).
- **Download:** a **targeted name-change list** (one row per change: type, path, original → new name,
  reason, resolution), reusing the existing Excel/CSV toggle. Not a full pre/post Document Register
  snapshot.

---

## 0. Read order for any session doing this work

1. `MEMORY.md`, `CLAUDE.md` (spec-sync rule; cardinal vanilla-stack rule).
2. `normalization-conflict-gate-plan.md` (the gate this extends) and `dev-context.md` §5/§7/§8.
3. This file.
4. Spec source of truth: `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` — Step 8 (8a/8b, "Name
   conflicts"), Run Lifecycle (audit lock, run states, Normalization Review), Rules 7 & 8.
5. Spec companion: `spec/dev-spec.md` — "Name Normalization Phase (Step 8)" (phase model, endpoints,
   sequence, component map) and the Document Register export section.

**Working protocol (unchanged):** Chase owns git; Claude designs the branch + implements in the working
tree (uncommitted), authors xUnit/`tsc` checks; Chase runs `dotnet build`/`dotnet test`/`npm run build`,
commits, PRs, merges. No `Magiq.Platform.*`. Every endpoint: omit `api/`, full `Configure()` +
`Version(1)`, Results→HTTP via `DlcEndpoint`, non-GET `{runId}` routes owner-guarded.

---

## 1. What we're building (one paragraph)

Today `AnalyzeNormalizationAsync` (8a) either pauses for conflicts **or silently auto-runs 8b** when the
plan is clean, and the `GET normalization/plan` endpoint returns **only conflicts** — the operator never
sees the plain whitespace/invisible renames that will be applied. We change the 8a gate to **pause on any
change**, surface the **full rename set** (plus resolved merges/deletes) through the plan endpoint and the
Normalization Review view, add a **name-change export** (`GET …/normalization/changes/export?format=`)
that reuses the register CSV/XLSX writers, and add an explicit **confirm** step (`POST …/normalization/
confirm`) that starts 8b. The audit lock (Rule 7) still trips only on the first executed 8b mutation, so
a run parked at the review gate has changed nothing and stays deletable.

---

## 2. Current state → target

| Area | Today | Target |
|---|---|---|
| `AnalyzeNormalizationAsync` (8a) | conflicts → pause; **clean → auto `StartNormalizationExecute`** | conflicts **or** renames present → persist both, **pause** (`AwaitingInput`); **only** zero-change plans auto-continue |
| Renames at the gate | persisted **only** on the clean path, right before auto-execute | persisted whenever a plan is produced (conflict **and** clean paths) so the change list is always available at the gate |
| `resolve` loop | clean re-analysis **auto-executes** 8b | clean re-analysis **parks** at the review gate (full change list shown) — execution needs an explicit confirm |
| Proceeding to 8b | implicit (analysis chains it) | explicit **`POST …/normalization/confirm`** → `StartNormalizationExecute` |
| `GET …/normalization/plan` | returns `Conflicts` only | also returns **`Renames`** (type, path, original, new) so the UI can list every change |
| Name-change download | none | **`GET …/normalization/changes/export?format=xlsx\|csv`** — synchronous small file, reuses `RegisterCsvWriter` / `DocumentRegisterExcelWriter` |
| `NormalizationReview.tsx` | conflict resolver only; title "Resolve name conflicts" | adds an **All name changes** table + format toggle + **Download changes** + **Confirm & continue**; handles the no-conflict review case; retitled "Review name changes (Step 8)" |
| `JobDetailsView` gate | already mounts review on `AwaitingInput && Normalization` | unchanged trigger (covers the no-conflict pause too); copy + a confirm callback |
| Spec / dev-spec | Step 8 "clean plan executes automatically" | Step 8 pauses on any change; new confirm step; plan returns renames; new export endpoint |

---

## 3. API changes (`DocumentLifecycleCleaner`)

### 3.1 Gate retiming — `Pipeline/RunPhaseExecutor.cs` `AnalyzeNormalizationAsync`

Replace the tail (current lines ~103–120):

- Always `DeletePendingByRunAsync` then, if `plan.Conflicts.Count > 0`, `AddBatchAsync(conflicts)`.
- **Persist renames whenever `plan.Renames.Count > 0`** (idempotent: keep the existing
  `existing.Count == 0` guard so resumes don't double-insert), on **both** the conflict and clean paths.
- **Pause if `plan.Conflicts.Count > 0 || plan.Renames.Count > 0`** → `run.PauseForNormalizationConflicts()`
  (rename to `PauseForNormalizationReview()` or add a sibling on `CleanupRun`; the run state is still
  `AwaitingInput` + phase `Normalization`, so no SPA-gate change is needed). Return.
- **Only** when there are no conflicts **and** no renames → `pipeline.StartNormalizationExecute(runId)`
  (unchanged no-op tail: 8b finds nothing, chains archival → cleanup).
- Still **never** call `MarkNormalizationEntered()` here (audit lock stays on the first 8b mutation).

### 3.2 New confirm command/endpoint — `Features/Runs/Normalization/Confirm/`

`POST /runs/{runId}/normalization/confirm` (owner-guarded, `Version(1)`, `DlcEndpoint`). Handler:

- 404 `RunNotFound` if missing.
- Guard: reject unless the run is `AwaitingInput` + phase `Normalization` **and** there are **no pending
  conflicts** (`ICleanupRunNameConflictStore.GetByRunAsync` → all `Resolved`). Return a `Result.Conflict`
  ("UnresolvedConflicts") otherwise — defence in depth against a client that skips resolution.
- `run.ResumeFromNormalizationReview()` (→ `Running`) + `pipeline.StartNormalizationExecute(runId)`.
- Return the run status. `StartNormalizationExecute` already chains 8b → archival → cleanup.

### 3.3 Plan response gains renames — `Features/Runs/Normalization/NormalizationPlanResponse.cs`

Add `IReadOnlyList<RenameView> Renames` to `NormalizationPlanResponse`; `RenameView(string ItemType,
string OriginalPath, string OriginalName, string NewName, string Status)`. Populate in
`GetNormalizationPlanHandler` from `ICleanupRunRenameStore.GetByRunAsync` (inject it). Conflicts already
carry their resolved merge/delete actions, so the SPA can render the complete change set from
`Renames` + resolved `Conflicts`.

### 3.4 Name-change export — `Features/Runs/Normalization/ExportChanges/`

`GET /runs/{runId}/normalization/changes/export?format=xlsx|csv`. **Synchronous** (the change set is
bounded by items-being-renamed, not the whole library — no Hangfire job, unlike the register export):

- Handler builds `IReadOnlyList<IReadOnlyDictionary<string, object?>>` rows from the rename store +
  resolved conflicts. Columns (first-appearance order → identical CSV/XLSX layout):
  `Type` (Folder/Document), `Change` (Normalize / Rename / Merge / Delete-duplicate),
  `Parent path`, `Original name`, `New name`, `Reason` (which whitespace/invisible characters — reuse the
  planner's normalization diff logic; mirror the SPA's `describeDifference`), `Resolution` (conflict id /
  chosen action, blank for a plain normalize), `Status`.
- Reuse `IRegisterCsvWriter` / `IDocumentRegisterExcelWriter` (they already take generic dictionary rows).
- Return bytes with content-type + filename (`run-{id}-name-changes.{csv|xlsx}`) via `DlcEndpoint`'s file
  response, same pattern as `DownloadRegisterExportEndpoint`. Owner-guarded.
- Available at the gate **and** afterward (renames persist), so it doubles as the record of what 8b did.

### 3.5 Tests (author; Chase runs)

- `AnalyzeNormalizationAsync`: renames-only (no conflicts) → `AwaitingInput`, renames persisted, nothing
  mutated, run still deletable (`DescribeDeletability.CanDelete == true`); zero-change plan → straight to
  execute; conflicts present → renames **and** conflicts persisted at the gate.
- Confirm handler: rejects with unresolved conflicts; on clean, resumes + enqueues execute; 404 on missing.
- Export handler: rows for each change kind; CSV and XLSX column parity; empty-change readable file.
- `GetNormalizationPlanHandler`: returns renames + conflicts.

---

## 4. SPA changes (`DocumentLifecycleCleaner.Web/src/`)

- **`api/normalization.ts`**: add `renames: RenameView[]` to `NormalizationPlan`; add
  `confirmNormalization(runId, token)` (POST confirm) and `downloadNameChanges(runId, format, token)`
  (GET export → blob download, copy `downloadRegisterExportFile`).
- **`wizard/NormalizationReview.tsx`**:
  - **All name changes** table from `plan.renames` + resolved conflict actions — reuse the `Visible`
    chip renderer so before/after whitespace is visible; searchable/paged for large sets; grouped or
    badged by change kind (Normalize / Rename / Merge / Delete).
  - **Format toggle + Download changes** button (reuse the Job Details Excel/CSV pattern).
  - **No-conflict path:** when `conflicts.length === 0` but `renames.length > 0`, skip the resolver and
    show the change list + **Confirm & continue** (calls `confirmNormalization` → `onResolved()`).
  - **Conflict path:** keep the resolver; "Submit resolutions" re-analyses; a clean re-analysis now
    **parks** (does not auto-run) → the view reloads showing the full change list + **Confirm & continue**.
  - Retitle to "Review name changes (Step 8)"; keep the "nothing changes until you confirm" note.
- **`pages/JobDetailsView.tsx`**: gate trigger unchanged (`AwaitingInput && currentPhase ===
  'Normalization'` already covers the no-conflict pause). Update the read-only alert copy to "review name
  changes"; the register card is untouched.
- Verify with `tsc -b` / `npm run build`.

---

## 5. Spec-sync (same unit of work — CLAUDE.md rule)

- `spec/…v0.6.md` Step 8: 8a now **pauses on any change** (not just conflicts); add the explicit
  **confirm** step before 8b; note the operator can review + export the full change list. Bump
  `_Last updated:_` + a History line.
- `spec/dev-spec.md`: `GET …/normalization/plan` now returns renames; add `POST …/normalization/confirm`
  and `GET …/normalization/changes/export`; update the Step 8 sequence (pause → review/export → confirm →
  8b) and run-state notes.
- `CLAUDE.md` / `MEMORY.md`: correct the Step 8 summary if it implies clean plans auto-execute.
- Decision log: append **[2026-08-10]** — "Step 8 review gate widened to any rename + name-change export".

---

## 6. Ordered branch plan

Cohesive enough for **one story, one branch** (`feature/{storyId}-normalization-change-review`), worked in
this internal order. Split into three PRs (B1 API gate+plan, B2 export, B3 SPA) only if Chase prefers
smaller reviews.

| Step | Scope | Notes |
|---|---|---|
| 1 | Gate retiming + confirm endpoint + plan returns renames (§3.1–3.3) | Behaviour change — pauses on any rename; keeps audit lock on first 8b mutation |
| 2 | Name-change export endpoint (§3.4) | Synchronous; reuses register writers |
| 3 | SPA: change list, download, confirm, no-conflict flow (§4) | Gate trigger unchanged |
| 4 | Spec + dev-spec + decision log reconciliation (§5) | In the same branch |

**ADO:** new Story under Epic #34120, Feature **34126 Review/Selection/Confirmation** (tag
`document-lifecycle-cleaner`). Claude drafts the commit + PR text at the end; Chase creates the branch,
builds, commits, PRs, links the story.

---

## 7. Definition of done

Run pauses at Step 8 whenever a name changes; operator sees the full folder + document change list,
resolves any conflicts, downloads the before→after list (CSV/XLSX), and confirms before 8b runs; a
zero-change plan still auto-continues; audit lock trips only on the first 8b mutation; a parked run is
still deletable; unit tests authored + green on Chase's build; `tsc`/`npm run build` clean; spec +
dev-spec + decision log reconciled in the same branch; no `Magiq.Platform.*`.
