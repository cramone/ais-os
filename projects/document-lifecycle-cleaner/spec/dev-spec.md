# Document Lifecycle Cleaner — Developer Specification

_Reference: [NATA Document Lifecycle Cleaner Spec v0.6](./NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md) — business rules, process phases, and all resolved questions._

> **Step numbering.** The shipped code now runs the renumbered pipeline (`decisions/log.md` [2026-08-05]): **Phase 3 — Name Normalization = Step 8**, then Archival = **Step 9** (create library) / **Step 10** (move), Cleanup = **Step 11** (delete empty folders) / **Step 12** (purge). `RunPhaseExecutor` emits exactly these numbers. The flows and section headers below use these built numbers; the Name Normalization phase's technical shape is in [Name Normalization Phase](#name-normalization-phase-step-8--implemented) at the end.

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

### First-run setup (anonymous; gated to the setup phase)

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/v1/setup/status` | Where setup stands (database + MAGIQ phases, instance id) |
| `POST` | `/api/v1/setup/test-connection` | Test a candidate app-database connection string |
| `POST` | `/api/v1/setup/app-database` | Save the app-database connection string (encrypted) and restart |
| `POST` | `/api/v1/setup/magiq/test-endpoint` | Test a candidate MAGIQ SOAP endpoint (`ServerInfo`) |
| `POST` | `/api/v1/setup/magiq/login` | Bootstrap sign-in against the candidate endpoint; writes the UI ticket to the shared httpOnly cookie and returns the resolved username to pin as the first allowlisted admin |
| `POST` | `/api/v1/setup/magiq/users` | Enabled MAGIQ users for the allowlist typeahead (`GetAllUsers`, using the cookie ticket) |
| `POST` | `/api/v1/setup/magiq` | Save the SOAP endpoint + admin allowlist to finish setup; re-validates the allowlist against `GetAllUsers` (cookie ticket) |

> `GetAllUsers` is **not anonymous**, so the allowlist can only be populated after the bootstrap sign-in. The
> earlier anonymous `POST /setup/magiq/validate-user` (`UserExists`) endpoint was **removed** (2026-08-08).

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
| `POST` | `/api/runs/{runId}/purge` | Trigger Step 12 purge (Path B — manual confirmation) |
| `GET` | `/api/runs/{runId}/archival/move-failures` | The run's failed Step 10 document moves (id, path, error, attempt count) + `canRetry`/`canContinue` flags |
| `POST` | `/api/runs/{runId}/archival/move-failures/retry` | Retry failed moves **synchronously** — body `{ documentRowIds?: Guid[] }` (empty/omitted = all failed); returns each targeted doc's outcome (`{ runStatus, allCleared, results: [{ id, status, failureReason, attemptCount }] }`). `409 RunNotRetryable` / `409 NoFailuresToRetry` |
| `POST` | `/api/runs/{runId}/archival/continue` | Proceed from the post-archival pause into cleanup (Steps 11–12). `409 RunNotAwaitingCleanup` |
| `GET` | `/api/runs/{runId}/log` | Phase log — the run's `CleanupRunPhaseLog` entries (phase-grain) |
| `GET` | `/api/runs/{runId}/operations` | Operation audit trail — one **page** of the run's `CleanupRunOperation` entries (object-grain: every create/move/delete/purge/rename/rule-relax + operator decision) plus the unpaged `total`. Server-paged, sorted + filtered: `?page=` (default 1), `?pageSize=` (default 50, max 200), `?sort=` (`occurredAt`\|`operationType`\|`targetType`\|`outcome`\|`sourcePath`\|`destinationPath`, default `occurredAt`), `?dir=` (`asc`\|`desc`, default `desc`), `?operationType=`, `?targetType=`, `?outcome=`, `?sourcePath=` (substring), `?destinationPath=` (substring), `?search=` (free text over source/destination/detail/error). Unknown enum/sort values fall back to the default |
| `GET` | `/api/runs/{runId}/operations/paths` | Distinct paths recorded for the run — the SPA source/destination path-filter typeaheads. `?field=` (`source`\|`destination`, default `source`), `?contains=` (case-insensitive substring), `?take=` (default 20, max 50) |
| `GET` | `/api/runs/{runId}/operations/export` | Download the operation audit trail as **CSV**, honouring the operator's current filters — the same `?operationType=`/`?targetType=`/`?outcome=`/`?sourcePath=`/`?destinationPath=`/`?search=`/`?sort=`/`?dir=` as `.../operations`, minus paging (the whole filtered set). Streams `text/csv` (UTF-8 BOM, RFC 4180) opening with a `#`-prefixed filter-summary header; rendered synchronously (no background job). `404 RunNotFound` for an unknown run (`decisions/log.md` [2026-08-10]) |
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

### Name Normalization review gate (Step 8)

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/runs/{runId}/normalization/plan` | Projected archive structure + detected name conflicts **+ the full rename list** (feeds Normalization Review) |
| `POST` | `/api/runs/{runId}/normalization/conflicts/draft` | Autosave draft conflict resolutions |
| `POST` | `/api/runs/{runId}/normalization/resolve` | Submit resolutions → re-run 8a; returns remaining conflicts, or "clean" (re-pauses at the review gate — does **not** auto-execute) |
| `POST` | `/api/runs/{runId}/normalization/confirm` | Confirm the reviewed change list (no conflicts pending) → resume + enqueue 8b execute |
| `GET` | `/api/runs/{runId}/normalization/changes/export?format=xlsx\|csv` | Download the before → after name-change list (renames + resolved merges/deletes) |
| `GET` | `/api/runs/{runId}/normalization/failures` | The run's failed Step 8b renames (id, itemType, path, newName, error) + `canRetry`/`canContinue` flags |
| `POST` | `/api/runs/{runId}/normalization/failures/retry` | Retry failed renames **synchronously** — body `{ renameRowIds?: Guid[] }` (empty/omitted = all failed); returns `{ runStatus, allCleared, items: [still-failed] }`. `409 RunNotRetryable` / `409 NoFailuresToRetry` |
| `POST` | `/api/runs/{runId}/normalization/continue` | Proceed from the post-normalization pause into archival. `409 RunNotAwaitingArchival` / `409 NormalizationFailuresRemain` |

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
| `GET` | `/api/v1/admin/magiq/users` | Enabled MAGIQ users for the System Settings allowlist typeahead (`GetAllUsers`, using the operator's live UI ticket) |

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

Append-only, object-level audit of every mutating primitive a run executes against MAGIQ, plus the operator decisions that shape it — the "during" record between the pre-run and post-run register snapshots (`decisions/log.md` [2026-08-05]). Complements `CleanupRunPhaseLog` (phase-grain) and is never updated, only inserted/read. Written at the SOAP call sites in `RunPhaseExecutor` and `ArchiveLibraryTeardown`, and in the review/confirm/purge handlers for the decision rows. Moves are recorded **per document** — one row per document (its path, destination, outcome and error), bulk-inserted per batch via `AppendManyAsync` so throughput matches the old batch-summary write (`decisions/log.md` [2026-08-09], reversing the 2026-08-05 batch-summary call); creates/deletes/domain/purge/rename/rule-relax+restore and operator decisions are per-op. The trail is read one **newest-first page** at a time with server-side filters (`GetPageByRunAsync`), so a run with tens of thousands of moves no longer loads whole into the SPA. The same filters drive a **CSV export** (`GetAllByRunAsync` — the unpaged form; `RunOperationsCsvWriter`; `GET .../operations/export`): the operator downloads exactly the rows they've filtered to, in a file that opens with a `#`-prefixed summary of the applied filters (`decisions/log.md` [2026-08-10]).

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

Audit record of every source rename made by the Name Normalization phase — the permanent account of the changes the tool made to NATA's live repository. Built alongside a `CleanupRun.EnteredNormalization` bit (in `0001_baseline.sql`) which is the audit-lock signal `DescribeDeletability` consumes. The phase detects what to rename from the **raw** candidate paths (`IMagiqDocumentQueries.GetRawCandidateDocumentPathsAsync`, un-normalized) via the pure `RenamePlanner`, which flags a name needing normalization when it contains **any Unicode whitespace character (`char.IsWhiteSpace`) or any of the invisible format characters** in the strip list, and produces the target by two rules — every whitespace character → a regular space with runs collapsed and ends trimmed; every invisible format character (`U+200B`, `U+200C`, `U+200D`, `U+2060`, `U+FEFF`, `U+00AD`) removed outright (see spec §"Whitespace normalization scope" for the definitive lists). Each rename is a SOAP **Get→Update** pair (re-supplying the read-back `Description`/`UpdateInstructions`; see SOAP-VERIFICATION-34525.md ops 14–17). A rename also writes a `Rename` row to `CleanupRunOperation`.

```sql
CREATE TABLE CleanupRunRename (
    Id            UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId         UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    Seq           BIGINT           NOT NULL,  -- per-run monotonic plan order (folders top-down, then documents); assigned MAX(Seq)+1 in the insert (decisions/log.md [2026-08-11])
    ItemType      NVARCHAR(20)     NOT NULL,  -- Folder|Document
    OriginalPath  NVARCHAR(2000)   NOT NULL,  -- path as addressed, with the original whitespace variant / invisible char
    OriginalName  NVARCHAR(500)    NOT NULL,
    NewName       NVARCHAR(500)    NOT NULL,  -- any whitespace → regular space (collapsed/trimmed); invisibles stripped
    Status        NVARCHAR(20)     NOT NULL DEFAULT 'Pending',  -- Pending|Renamed|Failed
    FailureReason NVARCHAR(1000)   NULL,
    RenamedAt     DATETIME2        NULL,
    RenamedBy     NVARCHAR(100)    NULL       -- operator/process ticket owner
);
-- Read ORDER BY Seq (Id is NEWID/random): Step 8b applies — and the retry reconcile replays — renames in Seq
-- order, so ancestor folders rename before their descendants (decisions/log.md [2026-08-11]).
```

> The audit lock is signalled by `CleanupRun.EnteredNormalization`, **set at the first executed mutation in Step 8b** (not on entering the phase) so a run still in the dry run / conflict gate stays deletable. `DescribeDeletability` consumes it (see the phase section below).

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

## Name Normalization Phase (Step 8) — implemented

Pipeline phase inserted **between operator confirmation (Step 7) and archival**, working around the MAGIQ name-mismatch bug: the desktop UI allows a document/folder name containing whitespace variants (a doubled space, a non-breaking space `U+00A0`, and other Unicode spaces) or invisible format characters, which are easily pasted in from other documents, but the SOAP `Move`/`CreateFolder` ops collapse/trim whitespace and fold those variants, so they cannot create or move such an item and the archival move fails. This phase renames the offending **source** items in place — **every Unicode whitespace character (`char.IsWhiteSpace`) → a regular space, collapsed and trimmed; every invisible format character stripped** — so the move succeeds. See spec §"Whitespace normalization scope" for the definitive character lists. Design → `decisions/log.md` [2026-08-05, 2026-08-07]; spec §"Phase 3 — Name Normalization"; ADR-002 / ADR-004 amendments.

Because normalizing names can collapse two distinct items onto the same name, the phase runs in three parts: **8a dry run** (plan the renames + detect conflicts, no mutation) → **review gate** (`AwaitingInput`; operator resolves any conflicts, then reviews + confirms the full change list — pauses whenever the plan changes any name, per `decisions/log.md` [2026-08-10]) → **8b execute** (apply renames/merges/deletes, mutating). The run is **audit-locked at the first executed mutation in 8b**, not on entering the phase (spec Rule 7, amended 2026-08-07).

### New SOAP operations (Path 1)

| Purpose | SOAP method | Signature (request parts) |
|---|---|---|
| Rename a folder level | `UpdateFolderProperties` | `AuthenticationTicket`, `Path`, `NewFolderName`, `NewDescription` |
| Rename a document | `UpdateDocumentProperties` | `AuthenticationTicket`, `Path`, `NewDocumentName`, `NewDescription`, `NewUpdateInstructions` |
| Delete a document (keep-one/delete-other) | `DeleteDocument` (verified — `SOAP-VERIFICATION-34525.md` op 18) | `AuthenticationTicket`, `Path` (→ recycle bin) |
| Read a document + version checksums (duplicate identity) | `GetDocument` `withVersions=true` (op 16) | `AuthenticationTicket`, `Path`, `withVersions=true` → `<Versions>`/`CheckSum` |
| Folder merge (fold one folder into another) | reuses `Move` (children) + `DeleteFolder` (emptied folder) | — |

Same `<response success="…"/>` contract as the other ops (check `success`, not HTTP status). The exact path form these ops accept to address a **still-affected** source item (one that still carries a whitespace variant or an invisible format character), and their response shapes, are **to confirm at integration** against training (ADR-011 / Story 34525 class).

### Admin-allowlist SOAP operation

| Purpose | SOAP method | Signature (request parts) |
|---|---|---|
| List users for the allowlist typeahead | `GetAllUsers` (verified — `SOAP-VERIFICATION-34525.md` op 19) | `AuthenticationTicket` → `<users><User UserName FirstName LastName Email Enabled …/></users>` |

`GetAllUsers` is **not anonymous** (unlike `UserExists`), so it runs after the first-run bootstrap sign-in or on the operator's live UI ticket. `ParseUserList` reads each `<User>`'s `UserName`/`FirstName`/`LastName`/`Email`/`UserID`/`Enabled`; callers drop `Enabled="FALSE"` accounts. This retires the anonymous `UserExists` allowlist check (2026-08-08).

### Behaviour

- **Phase model.** `RunPhase.Normalization` with two background jobs and an operator gate between them. **8a** `AnalyzeNormalizationAsync` (pure/`RenamePlanner`) builds the plan and conflict set — no SOAP writes. If the plan **changes any name** (a conflict and/or a rename) the run goes `AwaitingInput`; the operator resolves any conflicts and submits (re-runs 8a with resolutions applied — fixpoint loop), then reviews the full change list and **confirms** via `POST …/normalization/confirm`. Only a plan that changes **nothing** skips the gate and enqueues 8b directly. **8b** `ExecuteNormalizationAsync` applies the plan and chains to archival on success — resume-safe and idempotent (an item already at its resolved name / already merged / already deleted is skipped). Batched with per-item status and progress via `IRunProgressNotifier`, like the move.

**Normalization execution gate (Branch A).** Step 8b **never auto-advances** to archival. After applying the plan it **always pauses** the run — `PauseAfterNormalizationExecute` (Running → `AwaitingInput` in Normalization) — regardless of whether every rename succeeded or some failed. (Two things make this reliable: the phase body writes each item's outcome to `dbo.CleanupRunRename`, and — crucially — `LoadRunnableAsync` no-ops on any non-`Running` state, so the archival continuation Hangfire chains after the 8b job does nothing while the run is paused/failed. This closes a bug where a failed/paused normalization still ran archival because the guard only excluded Cancelled/Completed/Abandoned.) The details view shows a **Normalization execution** panel (`GET …/normalization/failures`, which now returns the **full** rename list with per-item status) that updates inline as each item completes (`Renamed`) or fails (with reason); the operator retries failures individually or all (`POST …/normalization/failures/retry`, `INormalizationFailureRetryer.RetryRenamesInlineAsync` — re-attempts in Seq order, repathing descendants + candidate docs after a folder succeeds, audits each as a `Rename` row, run stays paused throughout). The run **cannot advance while any rename is Failed or Pending**; once all are `Renamed` the operator confirms via `POST …/normalization/continue` (`ResumeAfterNormalization` + `StartArchival`, guarded `409 NormalizationChangesIncomplete`). `RunSummary.EnteredNormalization` distinguishes this post-8b execution state from the pre-mutation Normalization Review gate (both present as Normalization-phase pauses).
- **The plan (8a).** From the run's candidate documents and their resolved paths, `RenamePlanner` computes each target name by the two normalization rules — every Unicode whitespace char (`char.IsWhiteSpace`) → a regular space (runs collapsed, ends trimmed); every invisible format char (`U+200B`/`U+200C`/`U+200D`/`U+2060`/`U+FEFF`/`U+00AD`) stripped — and projects the resulting tree. Folder levels are planned top-down (ancestors before descendants). A **conflict** is ≥2 items resolving to the same name under the same parent, evaluated against the **whole projected structure** (including non-candidate siblings), split into `FolderFolder` and `DocumentDocument` kinds.
- **Conflict resolution (gate).** Each conflict gets a suggested resolution — default is a **non-destructive** disambiguating rename (append `" (2)"`, `" (3)"`, …). Operator options: `RenameFolder`, `RenameDocument`, `MergeFolders` (then any resulting inner document conflicts resolve by `RenameDocument` or `KeepOneDeleteOther`), `KeepOneDeleteOther`. Destructive options require an explicit choice + confirmation. Resolutions are draft-saved (like Step 6 selections) and, on submit, fed back into 8a until zero conflicts.
- **Duplicate identity (document conflicts).** For a `DocumentDocument` conflict, 8a reads each colliding document with `GetDocument` `withVersions=true` and compares the `<Version>` `CheckSum` set (+ `VersionSize`). All-match ⇒ flag the group **identical** (the gate may pre-note keep-one/delete-other as a safe collapse); any mismatch ⇒ **distinct content**, so keep-one/delete-other is marked lossy and the rename default stands. Persist the verdict on the conflict row so the SPA renders it without re-fetching.
- **Protection filter (spec Rule 2 wins).** 8a tags each `CleanupRunNameConflictItem` with `Protected` (from the Step 4 protection computation — a folder holding a post-cutoff doc or any ancestor of one; a post-cutoff document itself). The gate then **removes any option that would delete protected content**: a `MergeFolders` must orient so the protected folder is the survivor (never `DeleteFolder`'d); `KeepOneDeleteOther` cannot select a protected/post-cutoff document as the delete target; the default `Rename` targets the non-protected side; and if all members are protected, `RenameFolder`/`RenameDocument` is the only offered `ResolutionType`. `resolve` server-side re-validates this — a client that submits a protection-violating resolution is rejected — so protection can't be bypassed by a crafted request.
- **Non-candidate filter (Gap 2).** 8a also tags `NonCandidate` on any colliding folder the cull didn't select (no candidate docs beneath it). Such a folder is **survivor-only**: `MergeFolders` may keep it but never `DeleteFolder` it, and the default is `RenameFolder` on the candidate side. A merge whose survivor is `NonCandidate` sets an `outOfScope` flag on the response so the SPA shows the "combining with a folder outside this cull" warning + confirm; `resolve` re-validates that no `NonCandidate` (or `Protected`) item is ever the deleted side.
- **Execute (8b).** Apply the resolved plan: renames via `UpdateFolderProperties`/`UpdateDocumentProperties`; merges via `Move` (children) + `DeleteFolder` (emptied folder); duplicate deletes via the document-delete op. Top-down for folders. **First executed action sets `CleanupRun.EnteredNormalization` (the audit-lock bit).** **Candidate documents are repathed in lockstep** — after a folder rename (prefix rewrite of documents beneath it), a document rename (its leaf), or a folder merge (loser → survivor) the `CleanupRunDocument.DocumentPath` rows are updated via `ICleanupRunDocumentStore.UpdatePathsAsync`, mirroring the rename-row repath. Without this Step 10 addresses a moved/renamed source by its stale path and the move fails *"source folder not found"* (decisions/log.md [2026-08-11]). A **keep-one/delete-other** resolution additionally marks the deleted duplicate's candidate row `MoveStatus.Deleted` (matched by its raw path) so it is excluded from the Step 10 move set — `GetMovable`/`HasUnmovedDocuments` select `MoveStatus IN ('Pending','Failed')`, so a `Deleted` candidate is neither moved nor counted as a failure, and the row is retained for the register/audit.
- **Recording (required).** Every executed action writes a `CleanupRunRename` row (renames) or `CleanupRunOperation` row (`Rename`/`FolderMerge`/`DeleteDuplicate`, plus an `OperatorOverride`-style row per resolution decision) and a `CleanupRunPhaseLog` entry. This audit is the phase's purpose, not incidental logging.
- **Failure handling.** An action that can't be completed leaves the item `Failed`; like an unmovable document it blocks the archival move for that item, and the run surfaces the failures. Only once execution is complete does the pipeline chain to archival.

### Conflict data model & endpoints

`RenamePlanner` output persists conflicts so the gate is resumable and the SPA can render them. New table (add to `0001_baseline.sql`; DB is reset pre-release per `decisions/log.md` [2026-08-06]):

```sql
CREATE TABLE CleanupRunNameConflict (
    Id             UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId          UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    Kind           NVARCHAR(20)     NOT NULL,   -- FolderFolder | DocumentDocument
    ParentPath     NVARCHAR(2000)   NOT NULL,   -- normalized parent under which the collision occurs
    CollidingName  NVARCHAR(500)    NOT NULL,   -- the shared normalized name
    Identical      BIT              NULL,       -- DocumentDocument only: all version CheckSums match (GetDocument withVersions)
    ResolutionType NVARCHAR(30)     NULL,       -- RenameFolder|RenameDocument|MergeFolders|KeepOneDeleteOther
    Status         NVARCHAR(20)     NOT NULL DEFAULT 'Pending',  -- Pending|Resolved
    ResolvedBy     NVARCHAR(100)    NULL,
    ResolvedAt     DATETIME2        NULL
);
-- CleanupRunNameConflictItem(ConflictId, ItemType, OriginalPath, OriginalName, NormalizedName,
--   Protected BIT /* Rule 2: protected folder or post-cutoff doc — never deletable/mergeable-away */,
--   NonCandidate BIT /* folder outside the cull — survivor-only, never deleted; merge needs out-of-scope warn */,
--   Action /* Rename|Merge|Keep|Delete */, NewName NULL) lists the members + their per-item action.
```

`CleanupRunOperation.OperationType` gains `FolderMerge` and `DeleteDuplicate` (existing `Rename` covers renames).

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/runs/{runId}/normalization/plan` | Projected structure + conflicts **+ `Renames` (the full change list)** (feeds the Normalization Review tree) |
| `POST` | `/api/runs/{runId}/normalization/conflicts/draft` | Save draft resolutions |
| `POST` | `/api/runs/{runId}/normalization/resolve` | Commit resolutions (server re-validates Rule 2 / Gap 2), resume the run and re-enqueue the 8a dry run; responds `{ runStatus, message }` — the client polls the plan endpoint for the loop outcome |
| `POST` | `/api/runs/{runId}/normalization/confirm` | Confirm the reviewed change list — rejects `409 UnresolvedConflicts` if any conflict is still pending, else `ResumeNormalization` + `StartNormalizationExecute` (8b → archival → cleanup) |
| `GET` | `/api/runs/{runId}/normalization/changes/export?format=xlsx\|csv` | Stream the before → after name-change list (renames + resolved merges/deletes), rendered synchronously via the register CSV/XLSX writers |
| `GET` | `/api/runs/{runId}/normalization/failures` | Failed Step 8b renames + `canRetry` (Failed in Normalization) / `canContinue` (paused post-8b, `EnteredNormalization`, no failures) — feeds the Normalization Failures panel |
| `POST` | `/api/runs/{runId}/normalization/failures/retry` | `INormalizationFailureRetryer.RetryRenamesInlineAsync` — re-attempt failed renames (subset via `renameRowIds`, else all) in Seq order with descendant repathing; on clearing the last failure `AwaitNormalizationContinue` (Failed→AwaitingInput) |
| `POST` | `/api/runs/{runId}/normalization/continue` | Guarded to `AwaitingInput`+Normalization+`EnteredNormalization` with no failed renames → `ResumeAfterNormalization` + `StartArchival` (archival → cleanup) |

`resolve` is asynchronous: it validates every pending conflict is resolved and that no resolution deletes/merges-away a protected or non-candidate item (else `422`), persists the resolutions as `Resolved`, then `ResumeNormalization` + `StartNormalizationAnalysis`. The re-run 8a re-detects (a chosen resolution can create a new collision) and either re-pauses at the gate with the new conflicts **or, when clean, re-pauses at the review gate with the full change list** (it does **not** auto-execute — execution needs an explicit `confirm`). The client polls `GET …/plan` to see remaining conflicts or that the plan is clean and ready to confirm. `confirm` is the only path that starts 8b (except a zero-change plan, which 8a chains directly).

### Audit lock (spec Rule 7, amended 2026-08-07)

Normalization is the **first phase that mutates the customer's source repository**, and a rollback does **not** undo a rename/merge/delete. The lock trips on the **first executed mutation in 8b** — signalled by `CleanupRun.EnteredNormalization` being set — **not** on entering `RunPhase.Normalization`. A run still in the 8a dry run or the review gate (resolving conflicts or reviewing/confirming the change list) has written nothing and stays fully deletable. Once the bit is set:

- `CleanupRun.DescribeDeletability` must **never** return `CanDelete` for it — the tier can be `Reversible`/`Irreversible` but never `NoChanges`, regardless of later progress or a subsequent document rollback.
- The run is disposed of only by **archive** (retained for the record with its `CleanupRunRename` + conflict logs); document moves can still be rolled back, but the run row and audit persist.

> `DescribeDeletability` keys off `EnteredNormalization` (set at first executed change), **not** a `CurrentPhase == Normalization` check — so pre-execution runs remain deletable. (This supersedes the earlier "presence of any `CleanupRunRename` row or `CurrentPhase` reached" note.)

### Sequence — Name Normalization (Step 8)

```
Step 7 confirm succeeds → CleanupRun enters RunPhase.Normalization (NOT yet audit-locked)
  → Enqueue Hangfire job: AnalyzeNormalizationAsync (8a)

8a  Hangfire: AnalyzeNormalizationAsync   [no SOAP writes]
  → RenamePlanner.Plan(rawPaths, resolutions?) → target names + projected tree
  → Detect conflicts (≥2 items → same name under same parent, incl. non-candidate siblings)
  → conflicts.any?          → persist CleanupRunNameConflict rows; Status = AwaitingInput (resolve gate)
     conflicts.none + renames.any? → persist CleanupRunRename rows; Status = AwaitingInput (review gate)
     conflicts.none + renames.none? → enqueue ExecuteNormalizationAsync (8b)   // nothing to review

gate  Operator (Normalization Review view)
  → GET  /normalization/plan            → projected tree + conflicts + full rename list
  → POST /normalization/conflicts/draft → autosave resolutions
  → POST /normalization/resolve         → re-enqueue AnalyzeNormalizationAsync with resolutions
  → loop 8a until conflicts.none (then it re-pauses at the review gate — does NOT auto-execute)
  → GET  /normalization/changes/export  → download before → after list (CSV/XLSX)  [optional]
  → POST /normalization/confirm         → ResumeNormalization + enqueue ExecuteNormalizationAsync (8b)

8b  Hangfire: ExecuteNormalizationAsync   [mutating — first action sets EnteredNormalization]
  → For each folder level, top-down: UpdateFolderProperties(…)  → CleanupRunRename(Renamed)/Failed
  → For each folder merge:  Move(children) + DeleteFolder(emptied) → CleanupRunOperation(FolderMerge)
  → For each document:      UpdateDocumentProperties(…) or DeleteDocument(dup) → Rename/DeleteDuplicate
  → Any Failed → CleanupRun.Status = Failed (surfaced; blocks that item's move)
  → All clean  → Hangfire continuation → archival (Step 9 create library → Step 10 move)
```

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
    │   ├── NormalizationReview          (shown when status = AwaitingInput at Step 8 conflict gate)
    │   │   ├── ProjectedStructureTree   (adapted from FolderTable/tree; renders the planned archive outcome)
    │   │   │   └── ConflictBadge[]      (in-place on colliding nodes)
    │   │   ├── ConflictResolver[]       (issue + suggested default + options: rename folder/doc, merge, keep-one/delete-other; options gated by protection + out-of-scope, with badges)
    │   │   ├── ImpactSummary            (counts of renames/merges/deletes; warns on destructive picks)
    │   │   └── ResolveActions           (Re-check / Continue — autosaves draft; loops until clean)
    │   ├── PurgePanel                   (shown when status = AwaitingInput at Step 12)
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

### 3. Step 9 — Create (or adopt) the archive library

```
Hangfire: ExecuteArchivalAsync (Step 9 — create library)
  → Skip entirely if ArchiveLibraryId already set (operator-chosen existing lib, or a resume that
    persisted the id) — the id is the idempotency marker.
  → Else (create mode): GetDomains → find a library whose name == ArchiveLibraryName (case-insensitive)
      → Match found  → adopt it: SetArchiveLibraryId(match.Id ?? libraryRootPath); DO NOT
                       MarkArchiveLibraryCreated (not owned → teardown never deletes it);
                       CleanupRunOperation(CreateDomain, Ok, Detail="…already existed…creation skipped")
      → No match     → CreateDomain → MarkArchiveLibraryCreated; SetArchiveLibraryId(created.Id);
                       CleanupRunOperation(CreateDomain, Ok)
      → GetDomains/CreateDomain fault → CleanupRunOperation(CreateDomain, Failed) + CleanupRun.Status = Failed
```

This closes the "A library with this name already exists" failure seen when a prior attempt created the
domain but crashed before persisting `ArchiveLibraryId`, so a resume re-enters create mode.

### 4. Step 10 — Move with Retry Loop

```
Hangfire: ExecuteArchivalAsync (Step 10 — move)
  → Load CleanupRunDocument where MoveStatus = Pending
  → Batch documents (ArchivalBatchSize = 25)
  → Within each batch, GROUP BY source folder (ParentPath):
      → For each document in the folder: ensure destination folder, then SOAP Move(source, target)
      → If any of the folder's documents were blocked:
          → RunFolderGroupAsync → guard.WithRuleRelaxedAsync(sourceFolder, DocumentDeletes):
              GetFolderRules once → if DocumentDeletes disallows: SetFolderRules(allows) ONCE
              → retry only the still-failed documents → SetFolderRules(restore) ONCE
          (rule already allows / unreadable / relax rejected → blocked docs stay Failed)
      → Success  → MoveStatus = Moved ; one per-document Move audit row (Ok)
      → Failure  → MoveStatus = Failed, FailureReason ; per-document Move audit row (Failed) ; ItemFailed
  → After full pass: reload all Failed documents
  → Retry pass over the still-Failed set (same per-folder relax-once path)
  → Any still-failed → CleanupRun.Status = Failed
  → All succeeded  → Hangfire continuation → ExecuteCleanupAsync (Steps 11–12)
```

The rule relax/restore is **once per folder**, not once per document (decisions/log.md [2026-08-09]): the
per-document flip churned the same folder's rule and left later documents in the folder failing. The Step
11 folder-delete (group by parent, `FolderDeletes`) and the rollback move-back (group by original folder,
`NewDocuments`) use the same `RunFolderGroupAsync` shape. The per-item audit rows are written from **inside**
the relaxed scope (after the retries, before the restore), so the operation trail reads
`RuleRelax → Move/DeleteFolder rows → RuleRestore` in `Seq` order — faithful to the SOAP order, not
reverted-before-touched (decisions/log.md [2026-08-09]).

**Operator move-failure retry (implemented — decisions/log.md [2026-08-10]).** From the Document move
failures panel, `POST …/archival/move-failures/retry` re-attempts failed moves — a selected subset (`documentRowIds`)
or all failed (empty/omitted). It runs **synchronously and silently** via `IMoveFailureRetryer.RetryDocumentMovesInlineAsync`
(implemented by `RunPhaseExecutor`): it first calls `ReconcileCandidateDocumentPathsAsync` (idempotent — replays
the completed rename log + resolved merges onto the candidate paths, repairing any left stale by a Step 8 that
predates the in-line repath), then moves only the targeted documents through the same per-folder
relax-once machinery **without** flipping the run to Running or emitting run progress (`MoveDocumentsAsync(…,
emitProgress: false)`), and returns each targeted document's post-retry status so the SPA shows the outcome
inline in the row. `AttemptCount` is not reset — history is preserved. It is **never chained to cleanup**: if a
move still fails the run stays `Failed` (for another attempt); when the **last** failure clears
(`HasUnmovedDocumentsAsync` is false) it pauses the run — `CleanupRun.Retry()` then `PauseAfterArchival()` →
`AwaitingInput` in the Archival phase — and the operator explicitly proceeds via `POST …/archival/continue`
(`CleanupRun.ResumeAfterArchival` → `StartCleanup`). The SPA drives Retry-all by calling the endpoint once per
failed row, so each row shows its own inline progress. The endpoint (and `RetryMoveFailuresHandler`) validates
the run is `Failed` in the archival phase (`409 RunNotRetryable`) with at least one failure (`409
NoFailuresToRetry`). This keeps a human checkpoint before the irreversible cleanup/purge (spec §"Working
through move failures").

**Operator Reset:** set all documents to `MoveStatus = Pending`, re-enqueue full job.

### 5. Step 12 — Path B (Manual Purge)

```
Empty-folder delete (Step 11) complete, AutoProceedWithPurge = false
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
