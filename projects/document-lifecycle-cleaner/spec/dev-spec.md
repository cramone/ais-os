# Document Lifecycle Cleaner — Developer Specification

_Reference: [NATA Document Lifecycle Cleaner Spec v0.6](./NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md) — business rules, process phases, and all resolved questions._

> **Step numbering.** This developer spec uses the **as-built** step numbers (Archival: Step 9 move, Cleanup: Step 11 purge) that the shipped code uses. The spec inserts a new **Phase 3 — Name Normalization (Step 8)** ahead of archival (`decisions/log.md` [2026-08-05]) and renumbers the later steps (move → 10, delete-empty → 11, purge → 12). Until that phase is implemented, the flows below keep the pre-insertion numbers; the new phase's technical shape is in [Name Normalization Phase](#name-normalization-phase-step-8--specified-not-yet-built) at the end.

---

## Stack Summary

| Layer | Technology |
|---|---|
| Frontend | React SPA, served from API `wwwroot` |
| Backend | C# .NET, FastEndpoints (REPR / vertical slice) |
| Background jobs | Hangfire (in-process) |
| Realtime progress | SignalR (`/hubs/run-progress`) |
| App database | SQL Server — `CleanupRun` state + Hangfire tables |
| MAGIQ integration | SOAP (`srv.asmx`) + Dapper (direct SQL) |
| Hosting | IIS (default) or Docker (Linux container) |

---

## API Endpoint Catalogue

Route prefix: `/api`. FastEndpoints REPR pattern — each endpoint is a self-contained vertical slice.

### Authentication

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Authenticate operator; calls `AuthenticateUser` ×2; returns session token |
| `POST` | `/api/auth/logout` | Invalidates UI session ticket |

**Login request:**
```json
{ "username": "string", "password": "string" }
```

**Login response:**
```json
{ "sessionToken": "string", "username": "string" }
```

### Runs

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/runs` | List all runs, most recent first (jobs dashboard) |
| `POST` | `/api/runs` | Create new run; triggers Phase 1 (Steps 1–2) immediately |
| `GET` | `/api/runs/{runId}` | Full run detail |
| `POST` | `/api/runs/{runId}/cancel` | Cancel active run |
| `POST` | `/api/runs/{runId}/abandon` | Mark failed run as Abandoned |
| `POST` | `/api/runs/{runId}/reset` | Restart current failed phase from beginning |
| `POST` | `/api/runs/{runId}/retry` | Resume current failed phase from point of failure |
| `POST` | `/api/runs/{runId}/purge` | Trigger Step 11 purge (Path B — manual confirmation) |
| `GET` | `/api/runs/{runId}/log` | Phase log — the run's `CleanupRunPhaseLog` entries (phase-grain) |
| `GET` | `/api/runs/{runId}/operations` | Operation audit trail — the run's `CleanupRunOperation` entries (object-grain: every create/move/delete/purge/rename/rule-relax + operator decision) |
| `POST` | `/api/runs/{runId}/register/export` | Request an on-demand Document Register export (background render); `?format=xlsx\|csv` (default `xlsx`). Bounded to the latest AdHoc export; the pinned Pre/Post snapshots are retained |
| `GET` | `/api/runs/{runId}/register/export/{exportId}` | Poll a register export's status |
| `GET` | `/api/runs/{runId}/register/export/{exportId}/download` | Download a ready register export (content type per format) |
| `GET` | `/api/runs/{runId}/register/exports` | List the run's register exports — pinned Pre/Post snapshots + latest on-demand — with status, snapshot kind and format (drives the SPA before/after download controls) |

**Create run request:**
```json
{ "specifiedDate": "2024-12-31" }
```

**Run summary (GET /api/runs item):**
```json
{
  "id": "guid",
  "specifiedDate": "2024-12-31",
  "status": "Running|AwaitingInput|Completed|Failed|Cancelled|Abandoned",
  "currentPhase": "Identification|ReviewSelection|Normalization|Archival|Cleanup",
  "currentStep": 9,
  "createdAt": "iso8601",
  "createdBy": "username",
  "owner": "username",
  "successCount": 0,
  "failureCount": 0
}
```

> **Run ownership (decisions/log.md [2026-08-05]).** `owner` is initially the creator (distinct from the
> immutable `createdBy` so it can be transferred later). A run is **read-only to any operator other than its
> owner**: a global pre-processor (`RunOwnerPreProcessor`) short-circuits any **non-GET** request on a
> `/runs/{runId}/…` route with **`403 RunNotOwned`** unless the caller is the owner. GET/view requests
> (run, `/log`, `/operations`, `/folders`, register status/list/download) are unrestricted.

**Purge request (Path B — typed confirmation):**
```json
{ "confirmation": "permanently delete" }
```
API rejects if value ≠ `"permanently delete"` (case-sensitive).

### Folders (Steps 6 & 7)

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/runs/{runId}/folders` | Candidate folder list with path, counts, lock status |
| `PUT` | `/api/runs/{runId}/folders` | Submit folder selections; transitions run to Step 7 |
| `POST` | `/api/runs/{runId}/confirm` | Confirm deletions + archive library; initiates Phase 3 |

**Folder item (GET response):**
```json
{
  "folderId": "string",
  "folderPath": "string",
  "documentCount": 0,
  "folderCount": 0,
  "sizeBytes": 0,
  "isLocked": false,
  "isSelectedForDeletion": true,
  "status": "Pending|Protected|Deleted|Failed",
  "protectionReason": "string|null"
}
```

**Folder selection (PUT body):**
```json
{
  "selections": [
    { "folderId": "string", "selectedForDeletion": true }
  ]
}
```
Locked folders cannot be deselected — API rejects any `selectedForDeletion: false` for a locked folder (HTTP 422).

**Confirm (POST body — Step 7/8):**
```json
{
  "autoProceedWithPurge": false,
  "archiveLibrary": {
    "mode": "create|existing",
    "libraryId": "string|null",
    "libraryName": "string",
    "subfolderPath": "string|null"
  }
}
```

### Archive Libraries (Step 8)

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/libraries` | List available MAGIQ Documents libraries |
| `GET` | `/api/libraries/{libraryId}/folders` | Lazy-load child folders (one level) |

### Admin (allowlisted operators)

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/v1/admin/queries` | List the configurable MAGIQ queries + audit metadata (Story 34550) |
| `GET` | `/api/v1/admin/queries/{key}` | Get one configured query |
| `PUT` | `/api/v1/admin/queries/{key}` | Replace a query's SQL (optimistic-concurrency checked) |
| `POST` | `/api/v1/admin/schema/verify` | Verify the configured queries against the live MAGIQ schema (Story 34575) — see contract below |

---

## Data Model

### CleanupRun

```sql
CREATE TABLE CleanupRun (
    Id                      UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    SpecifiedDate           DATE             NOT NULL,
    Status                  NVARCHAR(20)     NOT NULL,  -- NotStarted|Running|AwaitingInput|Cancelled|Failed|Completed|Abandoned
    CurrentPhase            NVARCHAR(30)     NULL,
    CurrentStep             INT              NULL,
    CreatedAt               DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    UpdatedAt               DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    CreatedBy               NVARCHAR(100)    NOT NULL,
    ProcessTicket           NVARCHAR(500)    NULL,      -- persisted SOAP auth ticket (see ADR-007)
    ProcessTicketObtainedAt DATETIME2        NULL,
    AutoProceedWithPurge    BIT              NOT NULL DEFAULT 0,
    PurgeAuthorisedBy       NVARCHAR(100)    NULL,
    PurgeAuthorisedAt       DATETIME2        NULL,
    ArchiveLibraryId        NVARCHAR(200)    NULL,
    ArchiveLibraryName      NVARCHAR(500)    NULL,
    ArchiveSubfolderPath    NVARCHAR(1000)   NULL
);
```

### CleanupRunFolder

```sql
CREATE TABLE CleanupRunFolder (
    Id                    UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId                 UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    FolderId              NVARCHAR(200)    NOT NULL,
    FolderPath            NVARCHAR(2000)   NOT NULL,
    DocumentCount         INT              NOT NULL DEFAULT 0,
    FolderCount           INT              NOT NULL DEFAULT 0,
    SizeBytes             BIGINT           NOT NULL DEFAULT 0,
    IsLocked              BIT              NOT NULL DEFAULT 0,
    IsSelectedForDeletion BIT              NOT NULL DEFAULT 0,
    Status                NVARCHAR(20)     NOT NULL DEFAULT 'Pending',  -- Pending|Protected|Deleted|Failed
    ProtectionReason      NVARCHAR(500)    NULL
);
```

### CleanupRunDocument

```sql
CREATE TABLE CleanupRunDocument (
    Id            UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId         UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    DocumentId    NVARCHAR(200)    NOT NULL,
    DocumentPath  NVARCHAR(2000)   NULL,
    MoveStatus    NVARCHAR(20)     NOT NULL DEFAULT 'Pending',  -- Pending|Moved|Failed
    FailureReason NVARCHAR(1000)   NULL,
    AttemptCount  INT              NOT NULL DEFAULT 0,
    LastAttemptAt DATETIME2        NULL
);
```

### CleanupRunPhaseLog

```sql
CREATE TABLE CleanupRunPhaseLog (
    Id           UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId        UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    Phase        NVARCHAR(30)     NOT NULL,
    Step         INT              NULL,
    EventType    NVARCHAR(20)     NOT NULL,  -- Started|Completed|Failed|Reset|Retried
    OccurredAt   DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    ErrorMessage NVARCHAR(MAX)    NULL
);
```

### CleanupRunOperation

Append-only, object-level audit of every mutating primitive a run executes against MAGIQ, plus the operator decisions that shape it — the "during" record between the pre-run and post-run register snapshots (`decisions/log.md` [2026-08-05]). Complements `CleanupRunPhaseLog` (phase-grain) and is never updated, only inserted/read. Written at the SOAP call sites in `RunPhaseExecutor` and `ArchiveLibraryTeardown`, and in the review/confirm/purge handlers for the decision rows. Moves are recorded **batch-summary** (one row per batch, counts in `Detail`) to preserve the per-batch move-persistence decision (2026-07-28); creates/deletes/domain/purge/rename/rule-relax+restore and operator decisions are per-op.

```sql
CREATE TABLE CleanupRunOperation (
    Id                   UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId                UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    Seq                  BIGINT           NOT NULL,   -- per-run monotonic (append order)
    OccurredAtUtc        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    Phase                NVARCHAR(30)     NULL,       -- RunPhase name, or null (e.g. rollback/teardown)
    Step                 INT              NULL,
    OperationType        NVARCHAR(30)     NOT NULL,   -- CreateDomain|CreateFolder|Move|DeleteFolder|DeleteDomain|Purge|Rename|RuleRelax|RuleRestore|OperatorOverride|PurgeAuthorised
    Outcome              NVARCHAR(20)     NOT NULL,   -- Ok|Failed|Relaxed
    TargetType           NVARCHAR(20)     NOT NULL,   -- Domain|Folder|Document|Rule|RecycleBinItem|Selection
    SourcePath           NVARCHAR(2000)   NULL,
    DestinationOrNewName NVARCHAR(2000)   NULL,
    SoapSuccess          BIT              NULL,       -- the SOAP `success` attribute (null for non-SOAP rows)
    Detail               NVARCHAR(MAX)    NULL,       -- optional JSON (e.g. batch counts)
    ErrorMessage         NVARCHAR(MAX)    NULL,
    [Operator]           NVARCHAR(100)    NULL
);
-- IX_CleanupRunOperation_RunId_Seq (RunId, Seq)
```

> **RegisterExport.SnapshotKind** — the `RegisterExport` table (see below / Data Model) gains `SnapshotKind NVARCHAR(20) NOT NULL DEFAULT 'AdHoc'` (`AdHoc|PreRun|PostRun`) so a run can retain a pinned Pre-run and Post-run register snapshot for the before/after view; the on-demand export stays `AdHoc` (latest-only). Baked into `0001_baseline.sql` (the interim 0002–0004 scripts were consolidated into the baseline, 2026-08-06).

### CleanupRunRename _(Step 8 — implemented 2026-08-05)_

Audit record of every source rename made by the Name Normalization phase — the permanent account of the changes the tool made to NATA's live repository. Built alongside a `CleanupRun.EnteredNormalization` bit (in `0001_baseline.sql`) which is the audit-lock signal `DescribeDeletability` consumes. The phase detects what to rename from the **raw** candidate paths (`IMagiqDocumentQueries.GetRawCandidateDocumentPathsAsync`, un-normalized) via the pure `RenamePlanner`, and each rename is a SOAP **Get→Update** pair (re-supplying the read-back `Description`/`UpdateInstructions`; see SOAP-VERIFICATION-34525.md ops 14–17). A rename also writes a `Rename` row to `CleanupRunOperation`.

```sql
CREATE TABLE CleanupRunRename (
    Id            UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId         UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    ItemType      NVARCHAR(20)     NOT NULL,  -- Folder|Document
    OriginalPath  NVARCHAR(2000)   NOT NULL,  -- path as addressed, with the doubled whitespace
    OriginalName  NVARCHAR(500)    NOT NULL,
    NewName       NVARCHAR(500)    NOT NULL,  -- whitespace collapsed to single spaces
    Status        NVARCHAR(20)     NOT NULL DEFAULT 'Pending',  -- Pending|Renamed|Failed
    FailureReason NVARCHAR(1000)   NULL,
    RenamedAt     DATETIME2        NULL,
    RenamedBy     NVARCHAR(100)    NULL       -- operator/process ticket owner
);
```

> A run also needs a persisted "reached normalization" signal for the audit lock — either the presence of any `CleanupRunRename` row, or a `CurrentPhase`/high-water-mark check (`RunPhase.Normalization` reached). `DescribeDeletability` consumes it (see the phase section below).

---

## Configuration Schema

Full annotated `appsettings.json`:

```json
{
  "ConnectionStrings": {
    "AppDatabase": "Server=.;Database=DocumentLifecycleCleaner;Trusted_Connection=True;",
    "MagiqDocumentsDatabase": "Server=.;Database=MAGIQDocuments;Trusted_Connection=True;"
  },
  "MagiqDocuments": {
    "SoapEndpoint": "http://server/srv.asmx",
    "AdminAllowlist": [ "madhuri", "admin" ]
  },
  "MagiqSource": {
    "LibraryDomainId": 0
  },
  "Queries": {
    "CommandTimeoutSeconds": 120
  },
  "DeletableFolderAcronyms": [
    "ADV", "ARE", "ASS", "CEA", "CGA", "CRE", "DCR", "DEL",
    "DFS", "DRV", "DTV", "FAS", "FES", "OLC", "OLN", "REI",
    "RES", "SRE", "SRV", "STF", "STI", "VAR"
  ],
  "Hangfire": {
    "DashboardPath": "/hangfire",
    "WorkerCount": 1
  },
  "TicketHeartbeat": {
    "IntervalSeconds": 300
  },
  "RunProgress": {
    "DashboardPollIntervalSeconds": 30
  }
}
```

**Notes:**
- **Configurable query storage (Story 34550).** The four MAGIQ SQL queries are **no longer in
  `appsettings.json`** — they live in the app-DB table `dbo.ConfiguredQuery`, seeded with authored
  defaults at startup and edited via the admin **Configured Queries** screen (`/admin/queries`). This
  keeps them system-configurable without a code deploy (ADR-004) while giving a readable editor and an
  audit trail (`UpdatedBy`/`UpdatedAtUtc`). `Queries` retains only `CommandTimeoutSeconds`.
- **Bound parameters (no concatenation).** Queries reference `@specifiedDate` (cutoff), `@sourceDomainId`
  (the source library `DOMAINID`, from `MagiqSource:LibraryDomainId`), and `@folderIds` (Dapper `IN`
  list). The source id is bound, never interpolated — no injection surface.
- `MagiqSource:LibraryDomainId` scopes the cull to one source library; `0` (unset) matches nothing.
- `CandidateFolders` (Step 4) must return each candidate folder **and its full ancestor chain** so
  `ParentFolderId` links resolve within the result set; see the contract below. Modification date =
  `PUBLICATION.LASTUPDATED`; ancestor expansion + path building use the `FOLDERMAP` closure table.
- `DeletableFolderAcronyms` — case-sensitive contains match against folder name. NATA can add/remove entries.
- `AdminAllowlist` — interim; a database-backed or configurable store is a planned future iteration.
- `TicketHeartbeat.IntervalSeconds` — must be well under 1200 (20 min × 60 sec). 300 (5 min) recommended.
- `Hangfire.WorkerCount` — 1 is appropriate for a single-server annual run; not a throughput-critical system.

---

## Folder Identification (Steps 4-5) — Query & Rules Contract

Phase 1's folder pass (Story 34140) derives the candidate folder set, applies protection and the
acronym pre-lock, resolves paths, and populates `CleanupRunFolder`. It runs **in the same
identification job**, after Step 1, before the run pauses at Step 6.

### `Queries:CandidateFolders` (Step 4)

Parameter: `@specifiedDate`. Returns one row per **candidate folder and every one of its ancestor
folders** (so the tree can be walked in-app from `ParentFolderId`). Required columns:

| Column | Type | Meaning |
|---|---|---|
| `FolderId` | string | MAGIQ folder id (used later for SOAP `DeleteFolder`). |
| `ParentFolderId` | string \| null | Immediate parent; `null` for a root folder. |
| `FolderName` | string | Folder name — matched against the acronym list (case-sensitive contains). |
| `DocumentCount` | int | Documents directly in the folder (review column). |
| `FolderCount` | int | Immediate child folders (review column). |
| `SizeBytes` | long | Folder size (review column). |
| `ContainsPostCutoffDocument` | bit | `1` if the folder **directly** holds >=1 document with modification date **> @specifiedDate** (Rule 2 trigger). |

`Queries:FolderPaths` (Step 5, existing) then resolves `FolderId` -> `FolderPath` for the same set.

### In-app rules (not in SQL — applied over the query result)

1. **Full-ancestor protection (Rule 2, Task 34181).** Seed the protected set with every folder where
   `ContainsPostCutoffDocument = 1`, then propagate **up** the `ParentFolderId` chain — every ancestor
   of a protecting folder is protected too. Protected folders get `Status = Protected` and a
   `ProtectionReason`.
2. **Acronym pre-lock (Step 6 input).** A folder whose `FolderName` contains any configured
   `DeletableFolderAcronyms` entry (case-sensitive) is locked: `IsLocked = 1`,
   `IsSelectedForDeletion = 1`, non-deselectable in the review UI.
3. **Protection overrides the lock (resolved 2026-07-27).** If a folder is **both** acronym-matched
   **and** protected, protection wins: it is **not** pre-locked or pre-selected
   (`IsLocked = 0`, `IsSelectedForDeletion = 0`, `Status = Protected`). Rule 2 ("must not be deleted")
   is a hard safety rule and outranks the acronym convenience pre-selection; this also avoids a
   dead-end where a force-selected locked row is blocked by the Step 7 delete-constraint (Rule 4) with
   no way to deselect it. Non-protected acronym folders are locked as normal.

`CleanupRunFolder` is then populated from the merged result (path, counts, size, `IsLocked`,
`IsSelectedForDeletion`, `Status`, `ProtectionReason`). Progress is emitted per batch via
`IRunProgressNotifier`, and the run transitions to `AwaitingInput` at Step 6.

---

## Schema Verification — Contract (Story 34575)

`POST /api/v1/admin/schema/verify` (admin-only) checks that the configured MAGIQ queries still produce
the output shape the pipeline's mapping code depends on, against the **live** MAGIQ Documents schema.
The app never references MAGIQ tables directly (ADR-004) — its only schema dependency is mediated by
the four configurable queries — so this verifies each query's **result contract**, not MAGIQ's tables.
It is an on-demand pre-flight (no run-creation gate): run it before an annual cull and after any MAGIQ
version upgrade or query edit.

**Mechanism.** For each query the SQL is described with `CommandBehavior.SchemaOnly` (via
`GetSchemaTable`) against the MAGIQ DB — the statement is prepared and its column shape returned, but
**no rows are produced and no data is touched**. Standard parameters are declared for the probe
(`@specifiedDate`, `@sourceDomainId`; the Dapper `IN @folderIds` list in `FolderPaths` is rewritten to
`IN (@folderIds)` with a single placeholder). A SQL fault (missing table/column, syntax, undeclared
parameter) is reported as a `QueryError`.

**Required-column contracts** are code constants derived from the Dapper-mapped result records (the
queries are operator-editable; the columns the code consumes are fixed):

| Query | Required columns (logical type) |
|---|---|
| `CandidateDocuments` | `DocumentId` (string), `DocumentPath` (string) |
| `CandidateFolders` | `FolderId` (string), `ParentFolderId` (string), `FolderName` (string), `DocumentCount` (int), `FolderCount` (int), `SizeBytes` (long), `ContainsPostCutoffDocument` (bool) |
| `FolderPaths` | `FolderId` (string), `FolderPath` (string) |
| `DocumentRegister` | *none* — operator-defined columns; checked only for executability |

**Matching rules.** Required column **names must be present** (case-insensitive); each present column's
SQL type must be **compatible** with the logical type (string ← char family; int ← tinyint/smallint/int;
long ← tinyint/smallint/int/bigint; bool ← bit; datetime ← date family — widening only, so e.g. a
`bigint` where an `int` is required is flagged). **Extra columns are ignored**; column **nullability is
not checked** (SchemaOnly cannot know whether live rows contain nulls, and computed columns over-report
nullability).

**Response (`SchemaVerificationView`).** `passed` (true only when every query is `Ok`), `verifiedAtUtc`,
and `queries[]`, each `{ queryKey, status, error?, discrepancies[] }` where `status` ∈
`Ok | ContractViolation | QueryError | NotConfigured` and each discrepancy is
`{ column, kind: Missing | TypeMismatch, expected, actual? }`. A failing verification is a normal `200`
with `passed: false` — not an HTTP error. Enum values are serialised as their names (per the
`RunSummary` convention).

---

## Name Normalization Phase (Step 8) — specified, not yet built

New pipeline phase inserted **between operator confirmation (Step 7) and archival**, working around the MAGIQ double-space bug: the desktop UI allows a document/folder name containing a run of consecutive whitespace, but the SOAP `Move`/`CreateFolder` ops collapse whitespace and cannot create or move such an item, so the archival move fails. This phase renames the offending **source** items in place so the move succeeds. Design → `decisions/log.md` [2026-08-05]; spec §"Phase 3 — Name Normalization"; ADR-002 / ADR-004 amendments.

### New SOAP operations (Path 1)

| Purpose | SOAP method | Signature (request parts) |
|---|---|---|
| Rename a folder level | `UpdateFolderProperties` | `AuthenticationTicket`, `Path`, `NewFolderName`, `NewDescription` |
| Rename a document | `UpdateDocumentProperties` | `AuthenticationTicket`, `Path`, `NewDocumentName`, `NewDescription`, `NewUpdateInstructions` |

Same `<response success="…"/>` contract as the other ops (check `success`, not HTTP status). The exact path form these ops accept to address a **still-doubled** source item, and their response shapes, are **to confirm at integration** against training (ADR-011 / Story 34525 class).

### Behaviour

- **Phase model.** New `RunPhase.Normalization`; its own Hangfire job (`ExecuteNormalizationAsync`) that chains to archival on success — resume-safe and idempotent (an item with no doubled whitespace left is skipped). Batched with per-item status and progress via `IRunProgressNotifier`, like the move.
- **What is renamed.** From the run's candidate documents and their resolved paths, collapse each run of consecutive whitespace to a single space:
  1. **Folder path levels first, top-down (ancestors before descendants)** so descendant paths stay resolvable, via `UpdateFolderProperties`.
  2. **Then documents** whose own name contains a double space, via `UpdateDocumentProperties`, addressed by the now-normalized folder path.
- **Recording (required).** Each rename writes a `CleanupRunRename` row (`Renamed`/`Failed`) and a `CleanupRunPhaseLog` entry. This is the phase's purpose, not incidental logging.
- **Failure handling.** A rename that can't be completed leaves the item `Failed`; like an unmovable document it blocks the archival move for that item, and the run surfaces the failures. Only once normalization is complete does the pipeline chain to archival.

### Audit lock (spec Rule 7)

Normalization is the **first phase that mutates the customer's source repository**, and a rollback does **not** undo a rename. So once a run has entered `RunPhase.Normalization`:

- `CleanupRun.DescribeDeletability` must **never** return `CanDelete` for it — the tier can be `Reversible`/`Irreversible` but never `NoChanges`, regardless of later progress or a subsequent document rollback.
- The run is disposed of only by **archive** (retained for the record with its `CleanupRunRename` log); document moves can still be rolled back, but the run row and rename audit persist.

### Sequence — Name Normalization (Step 8)

```
Step 7 confirm succeeds
  → CleanupRun enters RunPhase.Normalization (new Step 8)  [run is now audit-locked]
  → Enqueue Hangfire job: ExecuteNormalizationAsync

Hangfire: ExecuteNormalizationAsync
  → Build the set of folder levels + documents (from candidate docs + resolved paths)
      that contain a run of consecutive whitespace
  → For each folder level, top-down:
      → UpdateFolderProperties(ticket, path, collapsedName, …)
      → success → record CleanupRunRename(Renamed);  failure → Failed + ItemFailed
  → For each document with a doubled name:
      → UpdateDocumentProperties(ticket, path, collapsedName, …)
      → success → record CleanupRunRename(Renamed);  failure → Failed + ItemFailed
  → Any Failed → CleanupRun.Status = Failed (surfaced; blocks that item's move)
  → All clean  → Hangfire continuation → archival (Step 9 create library → Step 10 move)
```

> **Renumber note:** with this phase in place the archival/cleanup flows above shift by one — the "Step 9 Move" flow becomes Step 10, "Step 11 Path B purge" becomes Step 12, etc. The existing flow headers keep the as-built numbers until the phase is implemented.

## SignalR Hub Contract

Hub endpoint: `/hubs/run-progress`

Client joins a run-specific group on connect: `run:{runId}`.

### Server → Client Messages

| Message | Payload | When |
|---|---|---|
| `PhaseStarted` | `{ runId, phase, step, totalItems }` | Phase/step begins |
| `ProgressUpdated` | `{ runId, phase, step, processed, total, currentItemPath, elapsedSeconds, etaSeconds? }` | Per batch |
| `ItemFailed` | `{ runId, phase, step, itemId, itemPath, reason }` | Per-item failure |
| `PhaseCompleted` | `{ runId, phase, step, successCount, failureCount }` | Phase/step ends |
| `RunStateChanged` | `{ runId, newStatus, phase?, step? }` | Any run state transition |

**Progress granularity:** emit `ProgressUpdated` per batch, not per document. Batch size TBD during implementation — target meaningful operator feedback without hub saturation.

`etaSeconds` is omitted (not null/zero) when insufficient data exists to calculate ETA.

---

## React Component Map

```
AppShell
├── LoginPage
└── AuthenticatedApp
    ├── JobsDashboard                    (polling: configurable interval, default 30s)
    │   └── RunCard[]
    │       ├── RunSummary               (status, phase, counts, elapsed)
    │       └── RunActions               (Reset | Retry | Abandon — shown on Failed runs)
    │
    ├── JobDetailsView                   (SignalR: /hubs/run-progress)
    │   ├── RunHeader                    (status badge, specifiedDate, createdBy)
    │   ├── PhaseTimeline                (visual step progress)
    │   ├── ProgressPanel                (progress bar, processed/total, currentItemPath, elapsed, ETA)
    │   ├── FailedItemsList              (live-updated; persists across Reset/Retry)
    │   ├── PurgePanel                   (shown when status = AwaitingInput at Step 11)
    │   │   └── PurgeConfirmModal        (typed "permanently delete" required)
    │   └── RunActions                   (Reset | Retry | Abandon — shown on Failed)
    │
    └── SetupWizard                      (mounts when run status = AwaitingInput at Step 6)
        ├── Step6FolderReview
        │   ├── FolderFilterBar          (free-text: path + acronym)
        │   ├── FolderTable              (virtual scroll — no pagination)
        │   │   └── FolderRow[]
        │   │       ├── LockedRow        (disabled checkbox + lock icon + tooltip)
        │   │       └── SelectableRow    (checkbox toggle)
        │   └── SelectionControls        (select all | deselect all — excludes locked rows)
        │
        ├── Step7ConfirmDeletions
        │   ├── FolderTable              (read-only; status column; sortable + filterable by status)
        │   │   └── FolderRow[]
        │   │       └── BlockedIndicator (inline on protected rows)
        │   ├── ValidationBanner         (shown when blocked folders exist; disables confirm)
        │   ├── AutoProceedCheckbox      ("Automatically proceed with purge when ready")
        │   └── BackToStep6Button
        │
        └── Step8ArchiveLibraryModal     (modal)
            ├── LibraryModeToggle        (Create new | Choose existing)
            ├── NewLibraryForm
            │   ├── LibraryNameInput     (prefilled: "Archive {source} - {date}")
            │   └── SubfolderInput       (optional)
            ├── ExistingLibrarySelector
            │   ├── LibraryFilterInput   (name filter)
            │   ├── LibraryList
            │   └── SubfolderBrowser     (lazy-load tree — children load on expand)
            └── ConfirmButton
```

---

## Key Sequence Flows

### 1. Login — Two-Ticket

```
Operator submits credentials
  → POST /api/auth/login
  → API calls AuthenticateUser × 2 in parallel
      Ticket A → UI session (in-memory, not persisted)
      Ticket B → process ticket (persisted to app DB on run create)
  → Heartbeat timer starts (TicketHeartbeat.IntervalSeconds)
  → Returns sessionToken to client
```

Heartbeat: lightweight SOAP operation on Ticket B every N seconds — resets 20-minute sliding window.

### 2. Phase 1 — Auto-trigger on Run Create

```
POST /api/runs { specifiedDate }
  → Create CleanupRun (status: NotStarted)
  → Persist Ticket B to CleanupRun.ProcessTicket
  → Enqueue Hangfire job: ExecutePhase1
  → Return 201 with runId

Hangfire: ExecutePhase1
  → Step 1: execute CandidateDocuments SQL
  → Step 2: execute DocumentRegister SQL
  → Step 4: derive candidate folder list from results
  → Step 5: execute FolderPaths SQL
  → Populate CleanupRunDocument records (MoveStatus: Pending)
  → Populate CleanupRunFolder records (IsLocked per acronym match)
  → CleanupRun.Status = AwaitingInput, CurrentStep = 6
  → Emit RunStateChanged via SignalR
```

### 3. Step 9 — Move with Retry Loop

```
Hangfire: ExecuteStep9
  → Load CleanupRunDocument where MoveStatus = Pending
  → Batch documents (batch size TBD)
  → For each document:
      → Call SOAP Move(documentId, archiveLibraryId)
      → Success  → MoveStatus = Moved
      → Failure  → MoveStatus = Failed, FailureReason, AttemptCount++
      → Emit ItemFailed / ProgressUpdated via SignalR
  → After full pass: reload all Failed documents
  → Retry each Failed document once more (AttemptCount++)
  → Any still-failed → CleanupRun.Status = Failed
  → All succeeded  → Hangfire continuation → ExecuteStep10
```

**Operator Retry:** re-enqueue only documents where `MoveStatus = Failed`. Does not reset `AttemptCount` — history preserved.

**Operator Reset:** set all documents to `MoveStatus = Pending`, re-enqueue full job.

### 4. Step 11 — Path B (Manual Purge)

```
Phase 3 complete, AutoProceedWithPurge = false
  → CleanupRun.Status = AwaitingInput
  → Jobs dashboard: "Ready for purge" badge

Operator opens JobDetailsView
  → Sees red Purge button
  → Clicks → PurgeConfirmModal
  → Types "permanently delete" → confirms
  → POST /api/runs/{id}/purge { confirmation: "permanently delete" }
  → API validates exact string (case-sensitive)
  → Records PurgeAuthorisedBy, PurgeAuthorisedAt
  → Enqueues Hangfire job: ExecuteStep11

Hangfire: ExecuteStep11
  → Call SOAP DeleteDomain(archiveLibraryId)
  → Call SOAP GetRecycleBinContent
  → For each recycle bin item: call SOAP PurgeRecycleBinItem(itemId)
  → Emit ProgressUpdated via SignalR
  → CleanupRun.Status = Completed
```

---

## Error Contracts

### SOAP call failure

```json
{
  "error": "SoapOperationFailed",
  "operation": "Move",
  "detail": "error attribute from SOAP response (may be empty string)"
}
```

### Blocked folder validation (Step 7 confirm)

HTTP 422. Deletion does not proceed.

```json
{
  "error": "FolderValidationFailed",
  "blockedFolders": [
    {
      "folderId": "string",
      "folderPath": "string",
      "reason": "Contains document modified after cutoff date"
    }
  ]
}
```

### Locked folder deselect attempt

HTTP 422.

```json
{ "error": "FolderIsLocked", "folderId": "string" }
```

### Purge confirmation mismatch

HTTP 422.

```json
{ "error": "ConfirmationRequired", "expected": "permanently delete" }
```

### Single active run constraint

HTTP 409. Returned when `POST /api/runs` attempted while a non-terminal run exists.

```json
{ "error": "RunAlreadyActive", "activeRunId": "guid" }
```

### Expired process ticket (mid-run)

On startup or when a SOAP call returns auth failure against the process ticket:
- If operator session is active: app calls `AuthenticateUser` automatically, replaces stored ticket, resumes heartbeat.
- If operator session has ended: run enters `Failed` state with `ErrorMessage: "Process ticket expired; re-authentication required"`. Operator logs in and triggers Retry.
