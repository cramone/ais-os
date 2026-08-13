# Name Normalization — Conflict Gate: Implementation Plan

_Created 2026-08-07. Owner: Chase. Author of plan: Claude. Status: **spec complete, implementation not started.**_

> **Purpose.** This is the build plan for turning the specced Name Normalization **conflict dry-run + operator
> resolution gate** into working code across the **API** (`DocumentLifecycleCleaner`) and **SPA**
> (`DocumentLifecycleCleaner.Web`). It is written to survive across Claude sessions: a fresh session should be
> able to read this file (plus the sources it points to) and pick up any branch without re-deriving context.

---

## 0. How to use this plan across sessions

**Read order for any session doing this work:**

1. `MEMORY.md` (session bootstrap) and `CLAUDE.md` (project rules, spec-sync rule, cardinal "vanilla stack" rule).
2. `dev-context.md` §5 (endpoint→command/query→context pattern), §7 (branch/PR protocol), §8 (quick-reference rules).
3. This file.
4. Spec **source of truth** for behaviour: `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` — Step 8 (8a/8b + "Name conflicts"), "Whitespace normalization scope", Rules 2, 7, 8, Run Lifecycle (audit lock, run states, Normalization Review, navigation).
5. Spec **technical companion**: `spec/dev-spec.md` — "Name Normalization Phase (Step 8)": phase model, conflict data model & endpoints, protection/non-candidate/identity filters, sequence, component map.
6. Decision log entries (`decisions/log.md`): **[2026-08-07]** ×4 — conflict gate + audit-lock retiming; vendor-permanent + SOAP ops; protection precedence; Gap 2 non-candidate handling. Plus **[2026-08-05]** original phase and **[2026-08-06]** migration consolidation.
7. SOAP contracts: `DocumentLifecycleCleaner/SOAP-VERIFICATION-34525.md` — op 16 `GetDocument` (`withVersions=true` / `CheckSum`), op 18 `DeleteDocument`, addendum-4 findings.

**Working protocol (from `dev-context.md` §7 — do not deviate):**

- **Chase owns git.** Claude designs the branch (name, work items, scope, file list) and implements **inside the working tree**; Claude does **not** commit/push/PR. One story per branch; `feature/{workItemId}-{slug}`.
- **Verification without a .NET SDK on the bridge VM:** Claude validates C# by brace/paren balance, reference/using checks, and reading diffs; validates the SPA with `tsc -b` / `npm run build` where runnable; **Chase runs the real `dotnet build` + tests and `npm run build`.** Unit tests are authored by Claude and run by Chase.
- **Spec-sync (CLAUDE.md rule):** if implementation forces a behaviour change from the spec, update `spec/*.md` **in the same branch** and note it in `decisions/log.md` — do not let code and spec drift. Flag, don't silently rewrite, any contradiction of a rule/decision.

**Cardinal invariants (must hold in every branch):**

- **Vanilla stack only** — no `Magiq.Platform.*`, no DynamoDB/event-sourcing/MediatR. FastEndpoints built-in bus, Dapper, Hangfire, SignalR, SQL Server.
- **Protection (Rule 2) wins** — no resolution ever deletes a protected folder or a post-cutoff document; a non-candidate folder is survivor-only. The deleted party of any merge/duplicate-delete must be an **in-scope, non-protected candidate**.
- **Audit lock (Rule 7) trips on the FIRST EXECUTED mutation in 8b**, never on entering the phase. Dry run + gate mutate nothing and stay deletable.
- **Every endpoint:** omit `api/` (global prefix), full `Configure()` metadata + `Version(1)`, map Results→HTTP via `DlcEndpoint`. Non-GET `{runId}` routes are guarded by the existing `RunOwnerPreProcessor`.
- **SOAP:** check the `success` attribute, not HTTP status.

---

## 1. What we're building (one paragraph)

Name Normalization (Step 8) becomes three parts instead of one: **8a** a non-mutating *dry run* that plans the
renames and detects **name conflicts** (two+ items collapsing onto the same name under one parent); a
**conflict gate** where — if conflicts exist — the run pauses (`AwaitingInput`) and the operator resolves each
in a new **Normalization Review** SPA view (rename / merge folders / keep-one-delete-other), with re-analysis
looping until clean; and **8b** the *execute* pass that applies the resolved plan (renames, merges, duplicate
deletes) and only then locks the run as an audit. Protection and out-of-scope folders constrain the options so
nothing preserved is ever destroyed.

---

## 2. Current state → target (what actually changes)

| Area | Today | Target |
|---|---|---|
| `MagiqPath.Normalize` / `RenamePlanner.Collapse` | collapses ASCII whitespace runs only | full Unicode `White_Space` → single space (collapse+trim) **and** strip invisibles (`U+200B/200C/200D/2060/FEFF/00AD`). Same helper used source + destination. (Implements the spec-only [2026-08-07] scope decisions.) |
| `RenamePlanner.Build` | pure: raw paths → ordered `PendingRename[]` | also returns **conflicts** (folder/document) with `Protected` / `NonCandidate` tags + suggested disambiguations; accepts prior **resolutions** for the re-analysis loop; accepts candidate/protection metadata as inputs (stays pure) |
| `RunPhaseExecutor.ExecuteNormalizationAsync` | single job: plan **and** execute; sets `EnteredNormalization` when the plan is built | split into **`AnalyzeNormalizationAsync` (8a)** and **`ExecuteNormalizationAsync` (8b)**; audit lock moves to the first executed action in 8b |
| Audit lock (`CleanupRun.MarkNormalizationEntered`) | called at plan build | called at **first executed** rename/merge/delete in 8b |
| `RunPipeline` | `confirm → StartNormalization → archival → cleanup` | `confirm → analysis(8a) → [gate loop] → execute(8b) → archival → cleanup` |
| SOAP client | no `DeleteDocument`; `GetDocument` has no versions | add `DeleteDocumentAsync`; `GetDocument` `withVersions=true` → parse `<Versions>`/`CheckSum` |
| Data model | `CleanupRunRename` + `EnteredNormalization` in baseline | add `CleanupRunNameConflict` (+ `…Item`) to `0001_baseline.sql`; `OperationType += FolderMerge, DeleteDuplicate` |
| Endpoints | none for normalization | `GET /runs/{id}/normalization/plan`, `POST …/conflicts/draft`, `POST …/resolve` |
| SPA gating | `JobDetailsView`: `inReview = AwaitingInput && currentStep <= 8` mounts `SetupWizard` | route `AwaitingInput && currentPhase === 'Normalization'` → new **NormalizationReview**; keep review (phase `ReviewSelection`) on the wizard. **This guard is a real collision to fix.** |
| SPA views | `SetupWizard`, `Step6FolderReview`, `Step7ConfirmDeletions`, `PurgeControl` | add `NormalizationReview` + subcomponents; reuse `wizard/folderTree.ts` |

---

## 3. Data model & migrations (into `0001_baseline.sql` — DB reset pre-release, per [2026-08-06])

```sql
CREATE TABLE CleanupRunNameConflict (
    Id             UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId          UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    Kind           NVARCHAR(20)     NOT NULL,   -- FolderFolder | DocumentDocument
    ParentPath     NVARCHAR(2000)   NOT NULL,   -- normalized parent under which the collision occurs
    CollidingName  NVARCHAR(500)    NOT NULL,   -- the shared normalized name
    Identical      BIT              NULL,       -- DocumentDocument only: all version CheckSums match
    ResolutionType NVARCHAR(30)     NULL,       -- RenameFolder|RenameDocument|MergeFolders|KeepOneDeleteOther
    Status         NVARCHAR(20)     NOT NULL DEFAULT 'Pending',  -- Pending | Resolved
    ResolvedBy     NVARCHAR(100)    NULL,
    ResolvedAt     DATETIME2        NULL
);
CREATE INDEX IX_CleanupRunNameConflict_RunId ON CleanupRunNameConflict (RunId);

CREATE TABLE CleanupRunNameConflictItem (
    Id             UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    ConflictId     UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRunNameConflict(Id),
    ItemType       NVARCHAR(20)     NOT NULL,   -- Folder | Document
    OriginalPath   NVARCHAR(2000)   NOT NULL,
    OriginalName   NVARCHAR(500)    NOT NULL,
    NormalizedName NVARCHAR(500)    NOT NULL,
    Protected      BIT              NOT NULL DEFAULT 0,  -- Rule 2: protected folder or post-cutoff doc
    NonCandidate   BIT              NOT NULL DEFAULT 0,  -- folder outside the cull — survivor-only
    Action         NVARCHAR(20)     NULL,       -- Rename | Merge | Keep | Delete
    NewName        NVARCHAR(500)    NULL
);
CREATE INDEX IX_CleanupRunNameConflictItem_ConflictId ON CleanupRunNameConflictItem (ConflictId);
```

- `CleanupRunOperation.OperationType` comment/domain gains `FolderMerge`, `DeleteDuplicate` (the `Rename` type already exists).
- No new journal script — folded into the single baseline (fresh-DB assumption still holds; call it out in the PR).

---

## 4. Domain & enums (API `Domain/`)

- New enums: `NameConflictKind { FolderFolder, DocumentDocument }`, `ConflictResolutionType { RenameFolder, RenameDocument, MergeFolders, KeepOneDeleteOther }`, `ConflictItemAction { Rename, Merge, Keep, Delete }`. Add `FolderMerge`, `DeleteDuplicate` to `RunOperationType`.
- `CleanupRun`:
  - **Retime the audit lock:** stop calling `MarkNormalizationEntered()` at plan build. Call it from 8b at the **first executed** action. `DescribeDeletability` already keys off `EnteredNormalization` — leave it, just set the bit later.
  - Gate helpers: enter `AwaitingInput` in phase `Normalization` at step 8 (mirror the existing review-pause helpers, e.g. the `AwaitingInput`/`AdvanceAwaitingInput` methods), and resume to `Running` when resolutions are clean.
- New models: `NameConflict`, `NameConflictItem` (domain) + `PendingRename` (exists). Planner outputs a `NormalizationPlan { IReadOnlyList<PendingRename> Renames; IReadOnlyList<NameConflict> Conflicts; }`.
- Stores: `ICleanupRunNameConflictStore` + Dapper impl (`Persistence/`), mirroring `ICleanupRunRenameStore`.

---

## 5. SOAP client (API `Integration/Magiq/Soap/`)

- `IMagiqSoapClient`:
  - `Task<MagiqSoapResult<SoapSuccess>> DeleteDocumentAsync(string ticket, string path, CancellationToken ct = default);` — envelope + parse per SOAP-VERIFICATION op 18 (`ParseAck`, `success` only).
  - `GetDocumentAsync` — add `withVersions` (overload or bool param). Extend `DocumentProperties` with `IReadOnlyList<DocumentVersion>` (`Number`, `CheckSum`, `VersionSize`). Parser reads `<Versions><Version …><CheckSum/>…` per op 16. Keep existing `Name`/`Description`/`UpdateInstructions` behaviour unchanged when `withVersions=false`.
- Add a small `DocumentVersion` model. Unit tests parse the exact sample XML in SOAP-VERIFICATION ops 16 & 18 (copy the payloads).

---

## 6. Pipeline (API `Pipeline/`)

**`RunPipeline`:**
- Replace `StartNormalization` with `StartNormalizationAnalysis(runId)` → enqueue `AnalyzeNormalizationAsync`.
- On a clean analysis, enqueue `ExecuteNormalizationAsync`, then chain (continuations) → `ExecuteArchivalAsync` → `ExecuteCleanupAsync` (unchanged tail).
- `resolve` endpoint re-enqueues `AnalyzeNormalizationAsync` (the loop).

**`RunPhaseExecutor`:**
- **`AnalyzeNormalizationAsync` (8a, no SOAP writes):** `StartPhase(Normalization, 8)` if not already; load raw candidate paths (`queries.GetRawCandidateDocumentPathsAsync`) + candidate-folder/protection metadata (from `CleanupRunFolder`); for `DocumentDocument` candidates read version checksums via `GetDocument withVersions=true`; run `RenamePlanner.Analyze(...)` with any persisted resolutions; persist conflicts. **If conflicts → `AwaitingInput`** (step 8). **Else → enqueue 8b.** Do **not** set `EnteredNormalization`.
- **`ExecuteNormalizationAsync` (8b, mutating):** load the resolved plan; apply top-down: renames (existing `ApplyRenameAsync` Get→Update pair), **folder merges** (`Move` each child into survivor → `DeleteFolder` emptied loser; reuse the reactive delete-rule relax/retry/restore already used at archival), **duplicate deletes** (`DeleteDocument`). Set `MarkNormalizationEntered()` + persist on the **first** successful action. Write `CleanupRunRename` / `CleanupRunOperation(FolderMerge|DeleteDuplicate)` rows. Batched, resumable, progress via `IRunProgressNotifier`. On success chain archival.
- Keep the existing repath-pending-descendants logic for folder renames; extend it to account for a merge changing child paths.

**`ConfirmDeletionsHandler`:** call `pipeline.StartNormalizationAnalysis(runId)` instead of `StartNormalization`.

---

## 7. Planner (API `Pipeline/RenamePlanner.cs`)

- Widen `Collapse` to the full scope (or move to `MagiqPath.Normalize` and call it): Unicode `White_Space` → single space (collapse+trim) + strip the six invisibles. Add unit tests for each character class.
- New `Analyze(inputs)` producing `NormalizationPlan`:
  - Inputs: raw candidate doc paths; a set describing which folders are candidates vs non-candidate and which are protected/post-cutoff; document version checksums for potential doc collisions; prior resolutions (list).
  - Detect conflicts: group projected items by (parent, normalized name); ≥2 ⇒ conflict. Evaluate against the **whole projected structure** incl. non-candidate siblings.
  - Tag each `NameConflictItem` with `Protected` / `NonCandidate`; compute `Identical` for doc conflicts from checksums.
  - Suggested default resolution = non-destructive disambiguating rename (`" (2)"`, `" (3)"`…) on the **non-protected / candidate** side.
  - Apply prior resolutions to the projection before re-detecting (fixpoint loop).
- Stays pure/side-effect-free and unit-tested (no SOAP/DB) — the executor feeds it data.

---

## 8. API endpoints (API `Features/Runs/Normalization/`)

All under the global prefix (no `api/`), `Version(1)`, `DlcEndpoint`, owner-guarded (non-GET).

| Verb | Route | Handler responsibility |
|---|---|---|
| `GET` | `/runs/{runId}/normalization/plan` | projected structure + conflicts (+ per-item Protected/NonCandidate/Identical, suggested defaults) for the tree |
| `POST` | `/runs/{runId}/normalization/conflicts/draft` | autosave draft resolutions (no side effects beyond persistence) |
| `POST` | `/runs/{runId}/normalization/resolve` | **validate** resolutions (reject any that would delete a Protected or NonCandidate item, or that leave a conflict unresolved) → persist → re-enqueue 8a → respond `{ remainingConflicts | clean }` |

Server-side protection/non-candidate re-validation lives here (defence in depth — never trust the client).

---

## 9. SPA (`DocumentLifecycleCleaner.Web/src/`)

- **`api/normalization.ts`** — typed client (copy `api/folders.ts` shape; use `api/http.ts`): `getPlan`, `saveDraft`, `resolve`.
- **`pages/JobDetailsView.tsx`** — fix the gate: mount `NormalizationReview` when `run.status === 'AwaitingInput' && run.currentPhase === 'Normalization'`; keep `SetupWizard` for `currentPhase === 'ReviewSelection'`; `PurgeControl` for the Cleanup purge pause. (Replaces the fragile `currentStep <= 8` test.)
- **`wizard/NormalizationReview.tsx`** (+ subcomponents):
  - `ProjectedStructureTree` — reuse/extend `wizard/folderTree.ts`; render planned archive outcome; badge conflicts, protected, out-of-scope, identical/distinct.
  - `ConflictResolver` — per conflict: issue text, suggested default pre-selected, options **gated** (hide/disable merge & delete-duplicate where they'd hit Protected/NonCandidate; destructive picks need a confirm; out-of-scope merge shows the "outside this cull" warning).
  - `ImpactSummary` — counts of renames/merges/deletes; warn on destructive picks.
  - `ResolveActions` — Re-check/Continue; autosave draft (debounced) via `saveDraft`; `resolve` loops until clean, then the run continues automatically.
- **Naming note:** the existing `wizard/Step8ArchiveLibraryModal.tsx` is archive-library selection (spec **Step 9**), a pre-normalization confirm concern — leave it; don't confuse it with the Step 8 conflict gate.

---

## 10. Ordered branch plan (one story per branch; `feature/{workItemId}-{slug}`)

Create ADO stories under **Epic #34120** (tag `document-lifecycle-cleaner` + per-branch tag). IDs TBD by Chase.

| # | Branch (slug) | Scope | Depends on |
|---|---|---|---|
| **B1** | `normalization-scope-and-planner` | Widen `MagiqPath.Normalize` to full `White_Space` + invisible-strip (closes the [2026-08-07] scope decisions); extend `RenamePlanner` → `Analyze` with conflict detection + Protected/NonCandidate/Identical tags + resolutions loop; pure unit tests | — |
| **B2** | `conflict-data-model` | `CleanupRunNameConflict(+Item)` into baseline; new enums; `OperationType += FolderMerge/DeleteDuplicate`; `ICleanupRunNameConflictStore` + Dapper; retime `EnteredNormalization`; gate state helpers on `CleanupRun` | — |
| **B3** | `soap-deletedocument-and-versions` | `DeleteDocumentAsync`; `GetDocument withVersions` + `DocumentVersion`/`CheckSum` parsing; unit tests off SOAP-VERIFICATION ops 16/18 | — |
| **B4** | `normalization-8a-analysis-gate` | `AnalyzeNormalizationAsync`; pipeline `StartNormalizationAnalysis`; pause→`AwaitingInput`; `ConfirmDeletionsHandler` retarget; checksum read for doc conflicts | B1,B2,B3 |
| **B5** | `normalization-8b-execute` | `ExecuteNormalizationAsync` split: renames + merges (`Move`+`DeleteFolder`) + `DeleteDocument`; audit-lock on first action; `FolderMerge`/`DeleteDuplicate` audit rows; reuse delete-rule handling; chain archival | B4 |
| **B6** | `normalization-endpoints` | `GET plan`, `POST conflicts/draft`, `POST resolve` (+ server-side protection/non-candidate validation, re-enqueue loop) | B2,B4 |
| **B7** | `spa-normalization-gate-and-client` | `api/normalization.ts`; `JobDetailsView` routing fix (phase-based gate) | B6 |
| **B8** | `spa-normalization-review-view` | `NormalizationReview` + `ProjectedStructureTree`/`ConflictResolver`/`ImpactSummary`/`ResolveActions`; badges, warnings, destructive confirms, draft autosave, resolve loop | B7 |

**Suggested execution order:** B1 ∥ B2 ∥ B3 (independent) → B4 → B5 → B6 → B7 → B8. B7+B8 may be merged if preferred; B4+B5 are kept separate because 8a (no mutation) and 8b (mutation + audit lock) carry very different risk.

---

## 11. Test matrix (author with each branch; Chase runs)

**Planner / scope (B1):** each whitespace class (double space, tab, `U+00A0`, `U+2007/202F`, `U+3000`, line/para sep) → single space; each invisible (`U+200B/200C/200D/2060/FEFF/00AD`) stripped, not spaced; mid-word invisible does **not** split. Conflicts: folder–folder (trailing space vs none; regular vs nbsp), document–document, collision with a **non-candidate** sibling, cascading (merge → inner doc conflict), resolution re-analysis introducing a **new** conflict (loop terminates). Tagging: Protected, NonCandidate, Identical vs distinct (checksum).
**SOAP (B3):** parse op 16 (versions/checksum) and op 18 (ack) sample payloads; `success="false"` path.
**Pipeline (B4/B5):** 8a with zero conflicts → straight to 8b; 8a with conflicts → `AwaitingInput`, nothing mutated, run still deletable (`DescribeDeletability.CanDelete == true`); 8b first action sets `EnteredNormalization` and flips deletability; merge = Move children + DeleteFolder loser; delete-duplicate = DeleteDocument; resume idempotency; a rename/merge that hits a disallow-delete rule → reactive relax/retry/restore.
**Protection/non-candidate (B4/B6):** `resolve` rejects a resolution deleting a Protected or NonCandidate item; all-protected conflict offers rename only; merge orients survivor = protected/non-candidate.
**SPA (B7/B8):** phase-based gate mounts NormalizationReview (and does **not** mount the folder-review wizard) at `AwaitingInput`+`Normalization`; destructive options gated + confirmed; out-of-scope warning shown; draft autosave; resolve loop then auto-continue; `tsc`/`npm run build` clean.

---

## 12. Verification (bridge VM has no .NET SDK)

- C#: brace/paren/using balance, reference existence, XML-doc well-formedness, and diff review per file. Author xUnit tests; **Chase runs `dotnet build` + `dotnet test`.**
- SPA: `tsc -b` / `npm run build` in `DocumentLifecycleCleaner.Web` where runnable; otherwise Chase builds.
- Each branch ends with a **spec-sync check**: does the built behaviour still match `spec/*.md`? If not, update the spec in the same branch (CLAUDE.md rule).

---

## 13. Open items / integration to-confirm

- **Non-candidate protection status:** a non-candidate folder is survivor-only, so its own protection status is moot for deletion — but confirm 8a can cheaply tell "candidate vs non-candidate" for a colliding sibling (derive from the candidate-folder set / a `FolderExists`-style check on the projected parent).
- **`DeleteDocument` path form:** op 18 sample uses a full slash path with original whitespace; confirm the executor addresses duplicates by their current (post-any-rename) path.
- **Merge child enumeration:** how 8b lists the loser folder's children to `Move` (SQL candidate set vs a SOAP folder listing) — prefer the run's own candidate/rename records; confirm nothing outside the run is moved.
- **SPA `currentPhase` availability:** confirm the run summary DTO already exposes `currentPhase` (it's shown in `JobDetailsView` header) so the gate can key off it.

---

## 14. Definition of done (per branch)

Code matches the spec; unit tests authored (and green on Chase's build); `tsc`/build clean; endpoints carry full `Configure()` + `Version(1)` + owner guard; audit rows written; **spec + decision log reconciled in the same branch**; Chase commits/PRs and links the ADO work items. No `Magiq.Platform.*`. Protection invariant holds. Audit lock only at first 8b mutation.
