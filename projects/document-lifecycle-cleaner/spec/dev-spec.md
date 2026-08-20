# Document Lifecycle Cleaner — Developer Specification

_Reference: [NATA Document Lifecycle Cleaner Spec v0.6](./NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md) — business rules, process phases, and all resolved questions._

> **Step numbering.** The shipped code now runs the renumbered pipeline (`decisions/log.md` [2026-08-05]): **Phase 3 — Name Normalization = Step 8**, then Archival = **Step 9** (create library) / **Step 10** (move), Cleanup = **Step 11** (delete empty folders) / **Step 12** (purge). `RunPhaseExecutor` emits exactly these numbers. The flows and section headers below use these built numbers; the Name Normalization phase's technical shape is in [Name Normalization Phase](#name-normalization-phase-step-8--implemented) at the end.

---

## Stack Summary

| Layer | Technology |
|---|---|
| Frontend | React SPA, served from API `wwwroot`; client-side routes (see below) |
| Backend | C# .NET, FastEndpoints (REPR / vertical slice) |
| Background jobs | Hangfire (in-process) |
| Realtime progress | SignalR (`/hubs/run-progress`) |
| App database | SQL Server — `CleanupRun` state + Hangfire tables |
| MAGIQ integration | SOAP (`srv.asmx`) + Dapper (direct SQL) |
| Hosting | IIS (default) or Docker (Linux container) |

### SPA routes

Four addressable client-side routes (rev 41, `decisions/log.md` [2026-08-18]). Before this the shell held its
page in `useState`, so the whole app lived at one URL and a run could not be linked to.

| Route | Page |
|---|---|
| `/runs` | Runs list (jobs dashboard). `/` resolves here |
| `/runs/{runId}` | Run details |
| `/queries` | Configured queries |
| `/settings` | System settings |

Implemented as a hand-rolled `useRoute` hook over the History API (`src/routing/routes.ts`) — a `Route`
union, `parseRoute`, `routePath`, a `popstate` listener and a normalisation effect that rewrites an
unrecognised or bare `/` URL in place. **No routing library**: four routes and one parameter did not justify
adding one to an SPA that otherwise carries no routing or state library.

Nothing was needed server-side — `Program.cs` already registers `MapFallbackToFile("index.html")` last, after
`UseStaticFiles` and `UseFastEndpoints` (all API routes sit under the `api` prefix), so deep links resolve
under IIS (`web.config` sends `path="*"` to ANCMv2 in-process), under Docker (same Kestrel pipeline) and in
Vite's dev server (history fallback by default). Vite's `base` is `/`, so `/assets/*` resolves from a
two-segment URL.

Notes: the page segment is matched **case-insensitively** (the fallback serves `/Runs/{id}` too, and an exact
match would silently drop the id and redirect to the list); the run id is not. Nav items and dashboard run
rows are real anchors, so modifier- and middle-clicks reach the browser. Deep links survive the sign-in gate
because the login screen renders in place and never navigates. **Limitation:** paths are root-absolute, so
the app cannot be hosted under an IIS virtual directory — already true, since `vite base` is `/`.

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
| `POST` | `/api/v1/setup/magiq/test-database` | Test a candidate **MAGIQ Documents** database connection string (separate from `/setup/test-connection`, which tests the *app* database and refuses once that is set — which it always is by this step) |
| `POST` | `/api/v1/setup/magiq` | Save the SOAP endpoint + admin allowlist + **MAGIQ Documents connection string** to finish setup; re-validates the allowlist against `GetAllUsers` (cookie ticket) and opens the database connection before writing anything |

> `GetAllUsers` is **not anonymous**, so the allowlist can only be populated after the bootstrap sign-in. The
> earlier anonymous `POST /setup/magiq/validate-user` (`UserExists`) endpoint was **removed** (2026-08-08).

### Runs

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/runs` | List all runs, most recent first (jobs dashboard) |
| `POST` | `/api/runs` | Create new run (body: `specifiedDate`, `sourceDomainId`, `sourceDomainName`, optional `sourceFolderPath` — decisions/log.md [2026-08-13, 2026-08-14]); triggers Phase 1 (Steps 1–2) immediately |
| `GET` | `/api/runs/{runId}` | Full run detail |
| `POST` | `/api/runs/{runId}/cancel` | Cancel active run |
| `POST` | `/api/runs/{runId}/abandon` | Mark failed run as Abandoned |
| `POST` | `/api/runs/{runId}/reset` | Restart current failed phase from beginning |
| `POST` | `/api/runs/{runId}/retry` | Resume current failed phase from point of failure |
| `POST` | `/api/runs/{runId}/rerun` | Re-run a clean-slate terminal run from Step 1 — rewinds to `Identification`/step 1 with a fresh process ticket and re-enqueues the pipeline. Gated on `RunDeletability.CanDelete` (the same clean-slate test as delete) plus the single-active-run rule. **Clears the previous attempt's re-derivable state first** (`ICleanupRunStore.ClearRerunStateAsync`, one transaction): `RegisterExport`, `CleanupRunRename`, `CleanupRunNameConflict`(+`Item`) — the run keeps its id, so otherwise the register panel showed the old attempt's pinned snapshots as this run's and Step 8a (which only plans when no rename rows exist) re-applied the old plan. `CleanupRunOperation`/`CleanupRunPhaseLog` are deliberately **kept**; `CleanupRunDocument`/`CleanupRunFolder` are cleared and rebuilt by identification itself. The clear runs **before** the rewind, so a failure leaves the run terminal and still re-runnable. `404 RunNotFound`; `409 RunNotRerunnable`; `409 RunAlreadyActive` (`decisions/log.md` [2026-08-18]) |
| `POST` | `/api/runs/{runId}/purge` | Trigger Step 12 purge (Path B — manual confirmation) |
| `GET` | `/api/runs/{runId}/archival/move-failures` | The run's failed Step 10 document moves (id, path, error, attempt count) + `canRetry`/`canContinue` flags |
| `POST` | `/api/runs/{runId}/archival/move-failures/retry` | Retry failed moves **synchronously** — body `{ documentRowIds?: Guid[] }` (empty/omitted = all failed); returns each targeted doc's outcome (`{ runStatus, allCleared, results: [{ id, status, failureReason, attemptCount }] }`). `409 RunNotRetryable` / `409 NoFailuresToRetry` |
| `POST` | `/api/runs/{runId}/archival/continue` | Proceed from the post-archival pause into cleanup (Steps 11–12). `409 RunNotAwaitingCleanup`; `409 UnresolvedMoveFailures` (`{ failedDocuments }`) while any document is still `MoveStatus.Failed` — the documents half of Rule 9, since the Step 11 guard verifies subfolders only and there is no verified `GetDocuments` op. Deliberately `Failed` only, **not** `Pending`: a document under a folder deselected at Step 7 is legitimately left `Pending` by the Kept-exclusion (`decisions/log.md` [2026-08-14]) |
| `GET` | `/api/runs/{runId}/log` | Phase log — the run's `CleanupRunPhaseLog` entries (phase-grain) |
| `GET` | `/api/runs/{runId}/operations` | Operation audit trail — one **page** of the run's `CleanupRunOperation` entries (object-grain: every create/move/delete/purge/rename/rule-relax + operator decision) plus the unpaged `total`. Server-paged, sorted + filtered: `?page=` (default 1), `?pageSize=` (default 50, max 200), `?sort=` (`occurredAt`\|`operationType`\|`targetType`\|`outcome`\|`sourcePath`\|`destinationPath`, default `occurredAt`), `?dir=` (`asc`\|`desc`, default `desc`), `?operationType=`, `?targetType=`, `?outcome=`, `?sourcePath=` (substring), `?destinationPath=` (substring), `?search=` (free text over source/destination/detail/error). Unknown enum/sort values fall back to the default. **Always excludes `Identification`/`ReviewSelection`-phase rows** (a hard `WHERE (Phase IS NULL OR Phase NOT IN (...))`, not an operator filter) — the audit trail starts at Normalization regardless of what a caller requests (`decisions/log.md` [2026-08-13]). The `Phase IS NULL` arm is **load-bearing**: rollback and archive-library-teardown rows carry no phase, and SQL's three-valued logic makes a bare `Phase NOT IN (…)` evaluate to NULL — excluding every one of them (`decisions/log.md` [2026-08-17]) |
| `GET` | `/api/runs/{runId}/operations/paths` | Distinct paths recorded for the run — the SPA source/destination path-filter typeaheads. `?field=` (`source`\|`destination`, default `source`), `?contains=` (case-insensitive substring), `?take=` (default 20, max 50) |
| `GET` | `/api/runs/{runId}/operations/export` | Download the operation audit trail as **CSV**, honouring the operator's current filters — the same `?operationType=`/`?targetType=`/`?outcome=`/`?sourcePath=`/`?destinationPath=`/`?search=`/`?sort=`/`?dir=` as `.../operations`, minus paging (the whole filtered set). Streams `text/csv` (UTF-8 BOM, RFC 4180) opening with a `#`-prefixed filter-summary header; rendered synchronously (no background job). `404 RunNotFound` for an unknown run (`decisions/log.md` [2026-08-10]). Same `Identification`/`ReviewSelection` exclusion as `.../operations` (`decisions/log.md` [2026-08-13]) |
| `POST` | `/api/runs/{runId}/register/export` | Request an on-demand Document Register export (background render); `?format=xlsx\|csv` (default `xlsx`). Bounded to the latest AdHoc export; the pinned Pre/Post snapshots are retained |
| `GET` | `/api/runs/{runId}/register/export/{exportId}` | Poll a register export's status |
| `GET` | `/api/runs/{runId}/register/export/{exportId}/download` | Download a ready register export (content type per format) |
| `GET` | `/api/runs/{runId}/register/exports` | List the run's register exports — pinned PreRun/PostReview/PostRun/PreNormalization/PostNormalization snapshots + latest on-demand — with status, snapshot kind and format. Drives the SPA's Document Register list, which titles them *Starting register*, *Reviewed plan*, *Planned name changes*, *Applied name changes*, *Final outcome* and *On-demand export*, and appends the deleted folder manifest as a further item (rev 39, `decisions/log.md` [2026-08-14, 2026-08-18]) |

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
| `POST` | `/api/runs/{runId}/folders/delete-failures/retry` | Retry failed **Step 11** folder deletes **synchronously** — body `{ folderIds?: string[] }` (the MAGIQ `FolderId`s, empty/omitted = all failed); returns each targeted folder's outcome (`{ results: [{ folderId, status, failureReason }] }`). Not gated on run status — a folder-delete failure never fails the run (Step 11 is best-effort), so this can be retried even after the run has completed. `404 RunNotFound` / `409 NoFailuresToRetry` (`decisions/log.md` [2026-08-14]) |
| `GET` | `/api/runs/{runId}/folders/completeness` | Why a folder could not be emptied (spec Rule 9) — `{ folders: [{ folderId, folderPath, unevaluatedChildCount, remainingChildPaths, blockingDescendantPaths, undiscoveredChildPaths, liveVerifyError }], liveVerified, liveVerifyTruncated }`. Derived from the run's own rows (`FolderCount` vs. child rows held); `?liveVerify=` (default `true`) additionally `GetFolders`-verifies **only the directly-blocked** folders, capped at 50 per request, to name the undiscovered children. Uses the **UI ticket**; no usable ticket degrades to `liveVerified: false` rather than failing. Backs the failures panel's **What's in it?** action and is intended for use **after Step 8** — pre-normalization the live half cannot address a not-yet-normalized path and reports "Target folder not found" (`decisions/log.md` [2026-08-14]). Informational; never changes selection or blocks a submit. `404 RunNotFound` |
| `GET` | `/api/runs/{runId}/folders/prune-plan` | Step 11 empty-subtree prune **dry run** — `{ folders: [{ folderId, folderPath, prunablePaths, blockingPaths, retainedPaths, blockingDocumentCount, resolvesFolder }], totalPrunable, resolvableCount }`. For each currently-`Failed` folder, reads its full descendant closure live from the MAGIQ DB (`FolderSubtree`) and classifies each descendant: **prunable** (entire subtree holds zero documents *and* the run never evaluated it), **blocking** (holds documents — never touched), **retained** (evaluated and being kept). Deletes nothing. `totalPrunable` is de-duplicated across entries (two blocked folders on one chain share descendants). `404 RunNotFound` (`decisions/log.md` [2026-08-14]) |
| `POST` | `/api/runs/{runId}/folders/prune` | Execute the prune — body `{ folderIds: string[] }`, **required** (the SPA drives it one folder at a time). Deletes the prunable set deepest-first, globally de-duplicated across plans, each delete through the live pre-delete guard and the per-parent rule-relax machinery, audited as `DeleteFolder` + `Detail = "Empty-subtree prune"`; then re-attempts the named folders via the ordinary retry. **The plan is re-derived from the live DB immediately before executing**, not taken from the dry run — that re-read is the *only* guard on the document case, since the live pre-delete guard checks **subfolders only** (no verified document-listing SOAP op exists). A narrow read→delete window therefore remains, accepted deliberately. Returns `{ prunedPaths, failures, resolvedFolderIds, stillBlockedFolderIds }`. Not gated on run status. `404 RunNotFound` / `409 NoFoldersRequested` (`decisions/log.md` [2026-08-14]) |
| `GET` | `/api/runs/{runId}/folders/deleted/export` | **Deleted folder manifest** — CSV of every folder the run removed from the source library, for hand re-creation of last resort after Step 12 purges them out of the recycle bin. Surfaced as an item in the SPA's **Document Register** list (rev 39, `decisions/log.md` [2026-08-18]) rather than its own card — it shares the list's row shape but none of its export machinery, so it has no row count and is never `Pending`. Columns `FolderPath,Depth,FolderName,ParentPath,Origin,FolderId,DocumentCountAtIdentification,SubfolderCountAtIdentification,SizeBytesAtIdentification,DisallowFolderDelete,DisallowDocumentDelete`, ordered **shallowest-first** (parent before child — the re-creation order, reverse of the deepest-first delete order). `Origin` is `Reviewed` (a candidate folder row) or `Pruned` (empty-subtree prune, no folder row → metadata columns blank, not zeroed). Set derived via `DeletedSourceFolders.From` (see below), enriched by path from `CleanupRunFolder`. Streams `text/csv` (UTF-8 BOM, RFC 4180) opening with a `#`-prefixed header that states the run, the counts, **and explicitly that description/owner/security are not captured**. No filters, no background job. `404 RunNotFound` (`decisions/log.md` [2026-08-14]) |
| `GET` | `/api/runs/{runId}/documents/archived/export` | **Archived document record** — CSV of every document Step 10 moved into the archive library: `SourcePath,ArchivePath,SourceFolder,DocumentName,MovedAtUtc`. Derived via `ArchivedDocuments.From` over the **audit trail** (`Archival`-phase `Move`/`Document`/`Ok` rows), not `CleanupRunDocument`, because the audit row carries the destination the move actually used — the document row does not store it. Streams `text/csv` (UTF-8 BOM, RFC 4180) opening with a `#`-prefixed preamble; a rolled-back run gets an explicit note that the moves were reversed. No filters, no background job. `404 RunNotFound` (rev 40, `decisions/log.md` [2026-08-18]) |
| `GET` | `/api/runs/{runId}/documents/purged/export` | **Purged document record** — CSV of every document destroyed when Step 12 purged the archive: the archived columns plus `PurgeConfirmedAtUtc,Basis`. **Grain caveat, stated in the file:** `DeleteDomain` bins the archive as *one* entry, so MAGIQ confirms the purge at library level and never per document; each row is inferred (*archived by this run* + *archive purged*) and the preamble prints the two library-level confirmations it rests on. Purge detection is `ArchivePurge.From`, matching the archive's bin item by **`DeletePath`** (from the per-item `Purge` row's `Detail`) — *not* by item name, which the SOAP client may populate from a path. Renders header-only, with the reason, when nothing has been purged, when the run was **rolled back** (any `RollbackStatus` other than `None` — a rollback empties the archive before destroying it), or when the purge predates this attempt's last archival activity (the re-run guard). No filters, no background job. `404 RunNotFound` (rev 40, `decisions/log.md` [2026-08-18]) |
| `POST` | `/api/runs/{runId}/folders/skip` | Settle failed **Step 11** folder deletes as deliberately skipped — body `{ folderIds: string[], reason: string }`, both **required** (never all-by-omission; the reason is the auditable point). Moves each currently-`Failed` folder to the terminal `Skipped` status, **preserving** its `FailureReason`, and writes a `FolderSkipped` operation-audit row with the operator + reason. No SOAP call, no run-state transition, not gated on run status. `404 RunNotFound` / `409 NoFoldersRequested` / `409 ReasonRequired` / `409 NoFailuresToSkip` (`decisions/log.md` [2026-08-14]) |

### Name Normalization review gate (Step 8)

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/runs/{runId}/normalization/plan` | Projected archive structure + detected name conflicts **+ the full rename list** (feeds Normalization Review) |
| `POST` | `/api/runs/{runId}/normalization/conflicts/draft` | Autosave draft conflict resolutions |
| `POST` | `/api/runs/{runId}/normalization/resolve` | Submit resolutions → re-run 8a; returns remaining conflicts, or "clean" (re-pauses at the review gate — does **not** auto-execute) |
| `POST` | `/api/runs/{runId}/normalization/confirm` | Confirm the reviewed change list (no conflicts pending) → resume + enqueue 8b execute; pins the `PreNormalization` Document Register snapshot once the plan settles clean (`decisions/log.md` [2026-08-14]) |
| `GET` | `/api/runs/{runId}/normalization/failures` | The run's failed Step 8b renames (id, itemType, path, newName, error) + `canRetry`/`canContinue` flags |
| `POST` | `/api/runs/{runId}/normalization/failures/retry` | Retry failed renames **synchronously** — body `{ renameRowIds?: Guid[] }` (empty/omitted = all failed); returns `{ runStatus, allCleared, items: [still-failed] }`. `409 RunNotRetryable` / `409 NoFailuresToRetry` |
| `POST` | `/api/runs/{runId}/normalization/continue` | Proceed from the post-normalization pause into archival. `409 RunNotAwaitingArchival` / `409 NormalizationFailuresRemain`; pins the `PostNormalization` Document Register snapshot first (`decisions/log.md` [2026-08-14]) |

> **The Step 8 name-change list is no longer downloaded from a standalone endpoint.** The former
> `GET .../normalization/changes/export?format=xlsx\|csv` was retired — the same content (renames +
> resolved merges/deletes) is now downloadable as two pinned Document Register snapshots,
> `PreNormalization` (captured when the review gate is reached) and `PostNormalization` (captured once
> every rename is confirmed applied), via the existing `.../register/exports` list and
> `.../register/export/{exportId}/download` (`decisions/log.md` [2026-08-14]).

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
  "status": "Pending|Protected|Deleted|Failed|Skipped",
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

**Confirm (POST body — Step 7/8/9):** `archiveLibrary.destinationType` splits into two mutually exclusive
shapes (decisions/log.md [2026-08-13]) — a **library** root, or a specific **folder** within an existing
library:
```json
{
  "autoProceedWithPurge": false,
  "archiveLibrary": {
    "destinationType": "library|folder",
    "mode": "create|existing|null",
    "libraryId": "string|null",
    "libraryName": "string",
    "folderPath": "string|null"
  }
}
```
For `destinationType: "library"`: `mode` is `"create"` (new library named `libraryName`, `libraryId` null)
or `"existing"` (library `libraryId`/`libraryName`); `folderPath` is ignored — the destination is always
that library's root. For `destinationType: "folder"`: `mode` is ignored, `libraryId`/`libraryName`
identify an **existing** library (you can't create a library and target a folder within it in the same
step), and `folderPath` is the destination folder's path within that library (e.g.
`"2024 archive/Q4"`) — created on demand in the archival phase if it doesn't already exist, exactly like
any other `ArchiveSubfolderPath`. `400 InvalidArchiveLibrarySelection` for an unrecognised
`destinationType`, a `library`/`create` with no name, a `library`/`existing` with no id, or a `folder`
missing either the library id/name or a non-empty `folderPath`.

### Archive Libraries (Step 8)

**Library list is live MAGIQ SOAP; folder browsing/search/breadcrumbs are live MAGIQ SQL
(decisions/log.md [2026-08-13, 2026-08-14, 2026-08-14 follow-up]).** `GET /libraries` calls live SOAP `GetDomains` — a
library needs its real MAGIQ id and `IsHidden`/`IsArchive` flags, which only MAGIQ can answer.
Folders are addressed by **id**, not path text — `GET /libraries/folders`, `GET /libraries/folders/
search` and `GET /libraries/folders/ancestors` read three new configured MAGIQ queries
(`FolderChildren`/`FolderSearch`/`FolderAncestors`, `IMagiqFolderBrowseQueries`) directly against
`dbo.FOLDERS`/`dbo.FOLDERMAP` — a live, always-current tree, not a cache (the earlier
`dbo.CleanupRunFolder`-backed browser from 2026-08-13, with its "no run history yet" gap, was deleted).
A root-level folder's `PARENTID` equals its own library's `DOMAINID` (Q4 of
SQL-QUERY-DESIGN-34547.md), so browsing the library root is just `parentId = domainId` — no separate
"root" case anywhere in the stack. The shared `FolderBrowser` React component (OneDrive-style
breadcrumbs + search + folder list, decisions/log.md [2026-08-14]) is what both the new-run source
picker and the Step 8/9 archive-destination picker render for the folder-browsing half. The search box
is **scoped to the current folder's subtree**, not the whole library (decisions/log.md [2026-08-14
follow-up]) — `FolderSearch` filters to folders with a `FOLDERMAP` row under the browser's current
`parentId`, and rescopes automatically (clearing any typed text) as the operator navigates.

| Method | Route | Description |
|---|---|---|
| `GET` | `/libraries?nameFilter=` | List the existing MAGIQ libraries (live `GetDomains`), optionally narrowed by a case-insensitive substring `nameFilter` (applied server-side over the SOAP result) |
| `GET` | `/libraries/folders?domainId=&parentId=&nameFilter=` | The immediate subfolders of a folder (one level), live from `FOLDERS`/`FOLDERMAP`; pass `parentId = domainId` to browse the library's root. `LibraryFolderView` carries `FolderId`/`Name`/`HasChildren`/`DocumentCount` — no path. `nameFilter` is bound as a parameter, never concatenated: `MagiqFolderBrowseQueries.ToLikePattern` wraps it in `%…%` after escaping `\`, `%`, `_` and `[` (escape char first), against the `ESCAPE '\'` on every configured `LIKE`. `]` is **not** escaped — it is special only as the terminator of a bracket expression, and escaping the `[` means none is ever opened. Same treatment for `/libraries/folders/search?term=`. |
| `GET` | `/libraries/folders/search?domainId=&parentId=&term=` | Folder search **scoped to the descendants of `parentId`** (live `FOLDERS`/`FOLDERMAP`, decisions/log.md [2026-08-14 follow-up]) — powers `FolderBrowser`'s `"jump"`-mode search box (Step 8/9 archive destination only; the new-run source picker uses client-side `"filter"` mode and never calls this endpoint), rescoped as the operator navigates; pass `parentId = domainId` to search the whole library from the root. A blank `term` returns no suggestions. |
| `GET` | `/libraries/folders/ancestors?folderId=` | A folder's breadcrumb chain (root first, then the folder itself) — rebuilds the browser's location after a search jump. |

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
    ArchiveSubfolderPath    NVARCHAR(1000)   NULL,
    SourceFolderPath        NVARCHAR(1000)   NULL   -- optional starting-folder scope within the source
                                                      -- library (Steps 1, 4); NULL = whole library
                                                      -- (decisions/log.md [2026-08-13])
);
```

(This snippet is illustrative, not exhaustive — `SourceDomainId`/`SourceDomainName`/`Owner`/`RollbackStatus`/etc. are omitted here for brevity; see `Persistence/Migrations/0001_baseline.sql` for the authoritative schema — `SourceFolderPath` is baked into the baseline, not a separate migration.)

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
    Status                NVARCHAR(20)     NOT NULL DEFAULT 'Pending',  -- Pending|Protected|Deleted|Failed|Skipped
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
    MoveStatus    NVARCHAR(20)     NOT NULL DEFAULT 'Pending',  -- Pending|Moved|Failed|RolledBack|Deleted|Kept
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

The trail is also **read back as data, not just displayed**: `DeletedSourceFolders.From(entries)` is the single definition of *which source folders this run deleted* — `Cleanup`-phase `DeleteFolder`/`Ok`/`Folder` rows, de-duplicated, in deletion order, each tagged `WasPruned` from a `Detail` starting `"Empty-subtree prune"`. Two callers share it: Step 12's recycle-bin purge and the deleted-folder manifest export. It has to be the audit trail rather than `CleanupRunFolder` rows with `Status = Deleted`, because the empty-subtree prune deletes folders the run never evaluated and so never has a row for — reading the folder rows left exactly those empty folders in the recycle bin and off the manifest. The `Cleanup`-phase restriction is load-bearing: the rollback teardown emits `DeleteFolder` rows too, for **archive** folders, with no phase (`decisions/log.md` [2026-08-14]).

```sql
CREATE TABLE CleanupRunOperation (
    Id                   UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    RunId                UNIQUEIDENTIFIER NOT NULL REFERENCES CleanupRun(Id),
    Seq                  BIGINT           NOT NULL,   -- per-run monotonic (append order)
    OccurredAtUtc        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    Phase                NVARCHAR(30)     NULL,       -- RunPhase name, or null (e.g. rollback/teardown)
    Step                 INT              NULL,
    OperationType        NVARCHAR(30)     NOT NULL,   -- CreateDomain|CreateFolder|Move|DeleteFolder|DeleteDomain|Purge|Rename|FolderMerge|DeleteDuplicate|RuleRelax|RuleRestore|OperatorOverride|PurgeAuthorised|MoveBack|FolderSkipped
    Outcome              NVARCHAR(20)     NOT NULL,   -- Ok|Failed|Relaxed|Deferred
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

> **RegisterExport.SnapshotKind** — the `RegisterExport` table (see below / Data Model) has `SnapshotKind NVARCHAR(20) NOT NULL DEFAULT 'AdHoc'`, now `AdHoc|PreRun|PostRun|PreNormalization|PostNormalization` (widened 2026-08-14; no column-width change needed, both new values fit `NVARCHAR(20)`) so a run can retain pinned before/after snapshots — of the candidate register (`PreRun`/`PostRun`) and, separately, of the Step 8 name-change list (`PreNormalization`/`PostNormalization`, decisions/log.md [2026-08-14]); the on-demand export stays `AdHoc` (latest-only). Baked into `0001_baseline.sql` (the interim 0002–0004 scripts were consolidated into the baseline, 2026-08-06).

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

**Optional starting-folder scope (decisions/log.md [2026-08-13]).** A run may carry an optional
`CleanupRun.SourceFolderPath` (raw MAGIQ folder path, relative to the library root; `null` = whole
library) captured on the new-run form by browsing the source library with the shared `FolderBrowser`
(reusing the same `GET /libraries/folders` id-addressed browser the Step 8/9 "Folder" archive-destination
picker uses — live `FOLDERS`/`FOLDERMAP` queries, decisions/log.md [2026-08-14]); the form joins the
browser's final breadcrumb trail's names into the persisted path. The new-run picker's search box is set
to `FolderBrowser`'s `searchMode="filter"` — a plain client-side name filter over the current listing,
no API call — rather than the Step 8/9 picker's default `"jump"` mode (which queries `GET
/libraries/folders/search` and navigates to a match anywhere in the current subtree, decisions/log.md
[2026-08-14 filter-mode follow-up]). This does **not** add a bound query
parameter to the identification queries themselves — `CandidateDocuments`/`CandidateFolders` still bind
only `@specifiedDate`/`@sourceDomainId`. Instead, `RunPhaseExecutor.ExecuteIdentificationAsync` runs `GetCandidateDocumentsAsync`/
`GetCandidateFoldersAsync` exactly as before (still whole-library), then filters the in-memory results by
path prefix (`RunPhaseExecutor.BuildSourceScopePrefix`/`IsWithinSourceScope`, comparing
`MagiqPath.Normalize`d paths against `/{SourceDomainName}/{SourceFolderPath}`) before persisting. Step
4-5's `CandidateFolderBuilder.Build` still runs over the *full* unscoped ancestor rows first (Rule 2
protection propagation needs the complete chain), and only the final `CandidateFolder` list is narrowed
afterward. Step 8's raw-path fetches (`GetScopedRawCandidateDocumentPathsAsync`) apply the same filter, so
a scoped run's normalization plan never touches an item outside the subtree. The Step 2 Document
Register export is **not** scoped — its rows are `IReadOnlyDictionary<string, object?>` with
operator-defined columns and no guaranteed path column to filter on.

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
4. **The pre-lock cascades down the matched folder's full subtree (decisions/log.md [2026-08-14]).**
   Matching is still checked on a folder's **own** `FolderName` only, exactly as above — but once a
   folder matches, **every non-protected descendant folder** (any depth, regardless of that
   descendant's own name) is pre-selected too, not just the matched folder itself.
   `CandidateFolderBuilder.ResolveSelectedIds` builds a `ParentFolderId` → children map from the same
   Step 4 rows the upward Rule 2 walk already uses, then DFS-walks down from **every self-matched
   folder — including a protected one** (the matched folder is still withheld from selection when
   protected, per rule 3; what it must not do is stop the walk, since Rule 2 protection propagates
   *upward*, so one post-cutoff document anywhere in the subtree marks the matched ancestor protected
   too and skipping its walk would un-select the entire case folder — the 92%-left-behind defect this
   cascade exists to fix), marking each visited non-protected id selected (a `visited` set, mirroring
   `ResolveProtectedIds`' cycle guard, ensures a descendant shared by two overlapping matches — or a
   FOLDERMAP cycle — is only walked once). Traversal **continues through** a protected node (Rule 2
   only propagates upward, never down, so a non-protected grandchild beneath a protected child still
   inherits from the matched ancestor further up); only the protected node itself is withheld from
   selection, per rule 3. This was added because NATA's case folders match the convention on their own
   name (e.g. `60912 SRV 2016`) while their actual documents live in structural children the convention
   was never meant to name-match (`1) Preparation`, `2) Report Package`, `3) Response`, `Submission 1`,
   ...) — without the cascade, Step 7's Kept-exclusion (which checks a document's direct parent only)
   silently excluded those documents from archival even though their case folder was selected, and
   Step 11 could then never fully empty the case folder either. One real run showed 92% of its candidate
   documents left behind this way before the fix.

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
| `GET` | `/api/runs/{runId}/normalization/failures` | Failed Step 8b renames + `canRetry` (Failed in Normalization) / `canContinue` (paused post-8b, `EnteredNormalization`, no failures) — feeds the Normalization Failures panel |
| `POST` | `/api/runs/{runId}/normalization/failures/retry` | `INormalizationFailureRetryer.RetryRenamesInlineAsync` — re-attempt failed renames (subset via `renameRowIds`, else all) in Seq order with descendant repathing; on clearing the last failure `AwaitNormalizationContinue` (Failed→AwaitingInput) |
| `POST` | `/api/runs/{runId}/normalization/continue` | Guarded to `AwaitingInput`+Normalization+`EnteredNormalization` with no failed renames → pins the `PostNormalization` Document Register snapshot (best-effort, `IRegisterExportStore`/`RegisterExportJob` via `INameChangeRegisterRows` — decisions/log.md [2026-08-14]), then `ResumeAfterNormalization` + `StartArchival` (archival → cleanup) |

The standalone `GET .../normalization/changes/export?format=xlsx\|csv` endpoint (rendered synchronously
via `ExportNameChangesHandler`) was **retired** (decisions/log.md [2026-08-14]) — its row-building logic
moved into `INameChangeRegisterRows`/`NameChangeRegisterRows` (`Features/Runs/ExportRegister/`), now
shared by `RegisterExportJob` for two new pinned snapshot kinds instead of a bespoke download.
`AnalyzeNormalizationAsync`'s "hasRenames" pause (the point that shows the Normalization Review gate) now also
pins the `PreNormalization` snapshot before returning, replacing any prior one on a re-analysis — the
same "replace on re-capture" rule `PreRun` already followed.

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
                                    → pin RegisterExport(PreNormalization) + enqueue its render
     conflicts.none + renames.none? → enqueue ExecuteNormalizationAsync (8b)   // nothing to review

gate  Operator (Normalization Review view)
  → GET  /normalization/plan            → projected tree + conflicts + full rename list
  → POST /normalization/conflicts/draft → autosave resolutions
  → POST /normalization/resolve         → re-enqueue AnalyzeNormalizationAsync with resolutions
  → loop 8a until conflicts.none (then it re-pauses at the review gate — does NOT auto-execute)
  → GET  /register/exports              → list snapshots incl. PreNormalization → download when Ready  [optional]
  → POST /normalization/confirm         → ResumeNormalization + enqueue ExecuteNormalizationAsync (8b)

8b  Hangfire: ExecuteNormalizationAsync   [mutating — first action sets EnteredNormalization]
  → For each folder level, top-down: UpdateFolderProperties(…)  → CleanupRunRename(Renamed)/Failed
  → For each folder merge:  Move(children) + DeleteFolder(emptied) → CleanupRunOperation(FolderMerge)
  → For each document:      UpdateDocumentProperties(…) or DeleteDocument(dup) → Rename/DeleteDuplicate
  → Any Failed → CleanupRun.Status = Failed (surfaced; blocks that item's move)
  → All clean  → pause (AwaitingInput); operator retries failures / confirms via /normalization/continue
                → continue pins RegisterExport(PostNormalization) + enqueues its render
                → Hangfire continuation → archival (Step 9 create library → Step 10 move)
```

## SignalR Hub Contract

Hub endpoint: `/hubs/run-progress`

Client joins a run-specific group on connect: `run:{runId}`.

### Server → Client Messages

| Message | Payload | When |
|---|---|---|
| `PhaseStarted` | `{ runId, phase, step, totalItems, operation? }` | Phase/step begins |
| `ProgressUpdated` | `{ runId, phase, step, processed, total, currentItemPath, elapsedSeconds, etaSeconds?, operation? }` | Per batch |
| `ItemFailed` | `{ runId, phase, step, itemId, itemPath, reason }` | Per-item failure |
| `PhaseCompleted` | `{ runId, phase, step, successCount, failureCount }` | Phase/step ends |
| `RunStateChanged` | `{ runId, newStatus, phase?, step? }` | Any run state transition |

**Progress granularity:** emit `ProgressUpdated` per batch, not per document. Batch size TBD during implementation — target meaningful operator feedback without hub saturation.

`etaSeconds` is omitted (not null/zero) when insufficient data exists to calculate ETA.

**`operation`** names the individual **pass** the progress belongs to, in operator language — the values are
the constants in `Hubs/Messages/RunOperations.cs` (e.g. `Deleting empty folders`, `Pruning empty subfolders`,
`Deleting the archive contents`, `Purging the archive contents`, `Purging the remaining deleted items`,
`Archiving documents`, `Returning documents to their original folders`). It exists
because **a step is not one pass**: Step 11 runs its reviewed-folder deletes and then, for anything the
pre-delete guard refused, an empty-subtree prune with its own item count; Step 12 runs three (delete the
archive's contents in chunks, purge those chunks, then destroy the library and the source folders Step 11
soft-deleted); a rollback runs three. Each restarts the count, so the
progress bar fills, resets and fills again, and `(phase, step)` alone cannot distinguish that from one job
looping. The SPA shows `operation` as the primary line of the Run progress panel, falling back to a
`(phase, step)` label (`theme/steps.ts`) between messages or for a run loaded over REST. Optional and additive
— a null leaves the SPA on its fallback, so an older client and a newer server interoperate either way
(`decisions/log.md` [2026-08-17]).

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
        └── Step8ArchiveLibraryModal     (modal; "Archive destination")
            ├── DestinationTypeToggle    (Library | Folder — decisions/log.md [2026-08-13])
            ├── Library
            │   ├── LibraryModeToggle    (Create new | Choose existing)
            │   ├── LibraryNameInput     (create; prefilled "Archive {source} - {date}")
            │   └── LibraryPicker        (existing; name filter + list) — targets the library ROOT, no subfolder
            └── Folder
                ├── LibraryPicker        (existing libraries only — shared component with Library/existing)
                ├── FolderBrowser        (shared component, decisions/log.md [2026-08-14] — breadcrumbs +
                │                         search + list; GET /libraries/folders?domainId=&parentId=)
                └── NewFolderNameInput   (optional — appends a not-yet-existing folder at the current level;
                                          rendered by FolderBrowser's newFolderName slot)
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

The CandidateDocuments SQL (Step 1) scopes documents only by cutoff date + source domain — it has **no
knowledge of the acronym/protection rules Steps 4–5 apply to folders**, and `CleanupRunDocument` carries
no folder id/link back to `CleanupRunFolder`. So every document at/before the cutoff in the domain is
inserted as `Pending` here, regardless of whether its folder will end up selected for deletion. That gap
is closed once, at Step 7 confirm — see "Folder-selection projection onto documents" below — **not** here
at Step 1 (decisions/log.md [2026-08-13]).

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

### 3a. Step 9 — Ensure the archive destination folder path (ancestor normalization)

A **folder** destination (spec §"Step 9 — Select or create the archive destination") sets
`ArchiveSubfolderPath` to one or more levels under the library root, some of which may already exist as
real MAGIQ folders this run did not create — captured by browsing/typing in the Step 8 archival-library
modal. Before `EnsureFolderPathAsync` checks/creates that path, `EnsureArchiveDestinationAsync` runs
`RunPhaseExecutor.NormalizeArchiveDestinationAncestorsAsync` (decisions/log.md [2026-08-13]):

```
NormalizeArchiveDestinationAncestorsAsync(run, ticket)
  → Walk ArchiveSubfolderPath's segments top-down from the library root
  → For each segment still found to exist (FolderExistsAsync on the raw composed path so far):
      → Clean (MagiqPath.Normalize(segment) == segment) → leave untouched, descend
      → Dirty → GetFolder → UpdateFolderProperties(rename in place to the normalized name)
              → CleanupRunOperation(Rename, Ok/Failed, TargetType=Folder) — Step 9, same shape as
                Step 8's ApplyRenameAsync
              → Fault → FailArchivalAsync, stop
  → Once a segment is found not to exist, every remaining segment (incl. an operator-typed brand-new
    name) is normalized in memory only — never handed dirty to CreateFolderAsync
  → If anything changed → CleanupRun.SetArchiveSubfolderPath(corrected path) → persist
→ EnsureFolderPathAsync(libraryRoot, BuildDestinationPath(run)) runs against the corrected path
```

This exists because SOAP requires the exact raw stored name to address an existing folder (the same
addressing rule Story 34525/34527 established for Step 8's source renames) — `FolderExistsAsync` checking
the *normalized* composed path would silently miss a dirty pre-existing ancestor, risking a duplicate
"clean" folder alongside it, a hard create failure, or an unresolvable Tier 2 rollback move-back. Both
call sites of `EnsureArchiveDestinationAsync` (the main archival flow and
`RetryDocumentMovesInlineAsync`'s inline retry) get this for free. A **library** destination is unaffected
(its path is always the root, so there's nothing to walk).

**Known residual gap (not covered):** the archive library's own name, when an *existing* library is
adopted by id — `CreateDomain`/adopt-by-name is skipped once `ArchiveLibraryId` is set, a different code
path than the one above. A dirty existing library name is not yet detected or corrected.

### 4. Step 10 — Move with Retry Loop

```
Hangfire: ExecuteArchivalAsync (Step 10 — move)
  → Load CleanupRunDocument where MoveStatus IN (Pending, Failed)   -- Kept/Deleted/Moved/RolledBack excluded
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
  → DeletedFolderManifestPanel offers the deleted-folder manifest (GET .../folders/deleted/export)
    — the modal prompts for it: this is the last point the deleted structure exists in MAGIQ
  → Sees red Purge button
  → Clicks → PurgeConfirmModal
  → Types "permanently delete" → confirms
  → POST /api/runs/{id}/purge { confirmation: "permanently delete" }
  → API validates the confirmation string
  → Records PurgeAuthorisedBy, PurgeAuthorisedAt
  → Enqueues Hangfire job: ExecutePurgeAsync

Hangfire: ExecutePurgeAsync  (RunPhaseExecutor.DeleteAndPurgeArchiveAsync)
  → AdvanceToStep(12) if not already there
  → Read the deleted source folders from the audit trail:
      operations.GetAllByRunAsync(runId, DeletedSourceFolders.Filter, …)
      → DeletedSourceFolders.From(entries)   // Cleanup-phase DeleteFolder/Ok rows,
                                             // incl. the prune's (which have no folder row)
  → Read the archive folders the run created:
      archiveFolders.GetCreatedAsync(runId)           // CleanupRunArchiveFolder — the chunk plan's input
  → Emit PhaseStarted(Cleanup, step 12, total = deleted folder count)
  → ArchiveLibraryTeardown.PurgeAsync(library, ticket, runId, deletedSourceFolders,
                                      archiveFolders, archiveDestinationPath,
                                      onPassStarted, onProgress)

      // ── Pass 1: delete the archive's contents in chunks ───────────────────────────
      → ArchiveChunkPlanner.Plan(destination, archiveFolders, ArchivePurgeChunkTarget)
          → shallowest depth beneath the destination with >= target folders
            (> ArchiveChunkPlanner.MaximumChunks = 1000 → prefer the shallower depth;
             target 0, no records, or < 2 chunks → no plan, straight to pass 3)
      → onPassStarted("Deleting the archive contents", chunkCount)
      → For each chunk folder  [ArchivePurgeConcurrency at a time, default 1]
        → SOAP DeleteFolder(path)                     [standard policy]
        → Audit DeleteFolder row, phase = null, Detail {"archiveChunk":true,"depth":N}
          (phase null keeps it out of DeletedSourceFolders, which is Cleanup-phase only)
        → onProgress → ProgressUpdated via SignalR
        → Failure → warn; the folder is destroyed with the library in pass 3 instead

      // ── Pass 2: purge those chunks ────────────────────────────────────────────────
      → SOAP GetRecycleBinContent (once)
      → Match bin items whose (DeletePath + Name) reconstructs to a folder just deleted
      → onPassStarted("Purging the archive contents", n) → PurgeItemsAsync (below)
      → Bin unreadable / nothing matched → warn; pass 3's DeletePath sweep catches them

      // ── Pass 3: delete the library, purge the remainder ───────────────────────────
      → SOAP DeleteDomain(archiveLibraryName)          [destructive policy: long budget, no retry]
      → SOAP GetRecycleBinContent
      → For each bin item matching EITHER
          the archive library (DeletePath = "\{ArchiveLibraryName}")
          OR a deleted source folder (leaf name AND parent DeletePath both match)
        MINUS any item barred by an unanswered purge in pass 2 (never re-issued)
      → onPassStarted("Purging the remaining deleted items", n) → PurgeItemsAsync

      // ── PurgeItemsAsync — the one place an item is destroyed ──────────────────────
        → SOAP PurgeRecycleBinItem(handle)           [destructive policy: long budget, no retry]
            → Indeterminate (sent, no answer)?
              → GetRecycleBinContent again; handle gone → count as purged
                (audit Outcome=Ok, soapSuccess=false, detail verifiedAgainstRecycleBin)
              → still there, or bin unreadable → stays a failure (fail closed) AND
                the item is barred from any later pass
        → Audit row per item + onProgress → ProgressUpdated via SignalR

      → Audit summary row (TargetType = Selection): purged / failed /
        verifiedAgainstRecycleBin / archiveItems / sourceFolders / sourceFoldersExpected /
        archiveChunks / chunkDepth
      → No source match at all → warn with bin samples, purge nothing from the source (fail closed)
  → CleanupRun.Status = Completed
```

**Why the chunk passes exist (rev 43, `decisions/log.md` [2026-08-18]).** `DeleteDomain` bins the library as **one** entry, so purging it was one call of many minutes reporting `0/1`. `DeleteFolder` bins **one entry per folder**, so deleting the contents first turns the same destruction into a countable, individually-audited, resumable list. Depth-based chunking rather than folder-by-folder because a `DeleteFolder` already takes a whole subtree server-side — the only question is granularity, and one chunk per recorded folder is ~2× folder-count round-trips for the same information. Single-depth chunks never nest, so the deletes are order-independent and concurrency-safe. **The plan is an optimisation, not the guarantee:** it is drawn from the run's own records and every miss is still destroyed by pass 3.

**Settings.** `ArchivePurgeChunkTarget` (default 25, 0–1000; `0` = no chunking; 1000 is a preference, not a ceiling) and `ArchivePurgeConcurrency` (default 1, 1–8) — System Settings → *Archive purge*.

**SOAP operation policies (`SoapOperationPolicy`, decisions/log.md [2026-08-17]).** `HttpClient.Timeout` is `InfiniteTimeSpan`; `MagiqSoapClient` applies the deadline per request via a `CancellationTokenSource` linked to the caller's token, so each operation can have its own budget and retryability:

| Policy | Operations | Timeout | Transport retry |
|---|---|---|---|
| Standard | everything else | `MagiqTimeoutSeconds` (default 100s) | yes — `MagiqMaxRetries` (default 3), exponential backoff |
| Destructive | `DeleteDomain`, `PurgeRecycleBinItem` | `MagiqPurgeTimeoutSeconds` (default 1800s) | **no** |

A transport failure under the destructive policy yields `MagiqSoapErrorKind.Indeterminate` — a new kind meaning *sent, no answer, outcome unknown* — rather than `Protocol`. The distinction exists because the two demand opposite handling: a protocol error means the call did not happen, an indeterminate one means nobody knows, and for a non-idempotent destroy the only safe response is to go and look. `ArchiveLibraryTeardown` does exactly that (`HasLeftRecycleBinAsync`), failing closed if the bin cannot be re-read. Caller cancellation is distinguished from a fired deadline by `ct.IsCancellationRequested`.

**PurgeControl polls throughout**, including while the purge runs — it used to stop the moment the purge was authorised, which froze the panel on "Purge started…" for the several minutes a large purge takes and read as nothing having happened (`decisions/log.md` [2026-08-14]).

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

### Folder-selection projection onto documents (Step 7 confirm)

`ConfirmDeletionsHandler` (`POST .../confirm`) is the **one point in the pipeline** where the operator's
final Step 6/7 folder selections (including overrides) are projected onto the candidate document set,
after the Rule 4 blocked-folder check passes and before `StartNormalizationAnalysis` is enqueued:

1. Build the set of selected folder paths from the just-validated `CleanupRunFolder` rows
   (`IsSelectedForDeletion == true`).
2. Load every still-`Pending` `CleanupRunDocument` row for the run (nothing has moved yet at Step 7).
3. For each, compute its containing folder as `RunPhaseExecutor.ParentPath(document.DocumentPath)` and
   check membership in the selected-path set (`StringComparer.OrdinalIgnoreCase`, matching the folder-path
   comparer used elsewhere in the pipeline).
4. Any document whose containing folder is **not** selected (or whose path is unexpectedly `null`) is set
   to `MoveStatus.Kept` via a dedicated `ICleanupRunDocumentStore.ExcludeAsync(documentRowIds, ct)` — a
   single chunked (1,000 ids/chunk) `UPDATE ... WHERE Id IN (...)`, **not** `UpdateMoveResultsAsync`
   (which Dapper multi-execs one row at a time; fine for a small Step 10 move batch, but this runs
   synchronously inside the Step 7 confirm request against the *whole* candidate set — one round trip per
   document there made a large run's Confirm click hang for minutes, decisions/log.md [2026-08-13]).
   `ExcludeAsync` also leaves `AttemptCount`/`LastAttemptAt` untouched, since an excluded document was
   never attempted. `Kept` is terminal, excluded from `GetMovable`/`HasUnmovedDocuments`
   (`IN ('Pending','Failed')`), left in place in the source repository, and reported as `"Kept"` in the
   before/after Document Register ledger (`Disposition` column, `MoveStatus.ToString()`).

Without this projection, Step 10 archives **every** candidate document for the run — including documents
under a folder the operator explicitly left unchecked or overrode — because Step 1's candidate-document
query and Steps 4–5's candidate-folder query are independent, and nothing before Step 7 ever narrows the
document set to the folders actually selected (decisions/log.md [2026-08-13]; this was a live bug, not a
designed behaviour). Step 11's folder delete was **not** affected — `CleanupRunFolderStore.GetDeletableAsync`
already filters `WHERE IsSelectedForDeletion = 1`, so an unselected folder was never itself deleted, only
needlessly emptied by Step 10 moving its documents out first.

### Step 11 folder-delete ordering + live emptiness guard (decisions/log.md [2026-08-14])

A real cull hit a delete-ordering defect: `GetDeletableAsync`'s SQL is `ORDER BY FolderPath` only (no depth
logic), and since a parent path is always a string-prefix of its child's, this can sort a shorter parent path
before a longer child path. `RunPhaseExecutor.DeleteEmptyFoldersAsync` deleted in that order, and MAGIQ's
`DeleteFolder` — previously verified only against an already-empty leaf path — turned out to
**cascade-remove a still-present child folder** along with a deleted parent rather than fail, so the
pipeline's own later `DeleteFolder` for that child then failed `"Target folder not found."` Two independent
fixes:

1. **Deepest-first re-sort.** `DeleteEmptyFoldersAsync` re-sorts the store's result with
   `OrderByDescending(f => f.FolderPath.Count(c => c == '/'))` before batching — the same pattern
   `RemoveCreatedArchiveFoldersAsync` (rollback teardown) already used. `GetDeletableAsync`'s own SQL
   ordering is unchanged (still `ORDER BY FolderPath`); the depth-safety guarantee lives solely in the
   executor, its only caller.

2. **Live pre-delete emptiness guard — `RunPhaseExecutor.DeleteFolderIfEmptyAsync`.** Wraps every
   `DeleteFolder` call (the main Step 11 pass and `RetryFolderDeletesInlineAsync`) with a
   `IMagiqSoapClient.ListFoldersAsync(ticket, path)` check first. If MAGIQ reports **any** remaining
   subfolder (or the check itself fails to complete), the delete is refused — the folder is marked
   `Failed` with a message describing why, and `DeleteFolderAsync` is never called — rather than trusting the
   run's own candidate-set/`FolderCount` snapshot. This is the actual backstop: ordering alone only protects
   a folder this run already knows about (has a `CleanupRunFolder` row for), and cannot help a folder that's
   invisible to the run entirely or one the operator deliberately deselected (see the flagged gap below).

**Known gap, flagged not fixed:** `ConfiguredQueryDefaults.CandidateFolders`' `FolderSet` CTE closes only
**upward** (`CandidateFolder ∪ ancestors-of-CandidateFolder` via `FOLDERMAP.PARENTID`) — never downward. A
subfolder holding only post-cutoff documents (Rule 2 should protect it) is therefore invisible end-to-end —
no `CleanupRunFolder` row, no `Protected` status, not shown at Step 6 review — unless it independently
happens to be an ancestor of some other candidate folder elsewhere. `CandidateFolderBuilder.ResolveProtectedIds`
only walks `ParentFolderId` within the rows SQL already returned, so there is no app-level mitigation either.
The live emptiness guard above prevents this gap from causing data loss (such a folder can no longer be
deleted out from under an unaware parent), but the SQL/UI-visibility side of the gap is unresolved and
deferred — closing it would need either a recursive/fixed-point downward closure in the configured query or
an equivalent app-level check, which wasn't undertaken this round.

### Document Register: starting-folder scope + PostReview snapshot (decisions/log.md [2026-08-14])

Diagnosing the incident above needed a reliable before/after picture of what a run saw and selected, which
surfaced two gaps in the existing register snapshots.

**1. PreRun/AdHoc narrowed to the run's starting-folder scope.** Previously a known limitation
(decisions/log.md [2026-08-13]): the pinned "before" (`PreRun`) snapshot and the on-demand `AdHoc` export
always queried the whole source library via `IMagiqDocumentQueries.GetDocumentRegisterAsync`, ignoring
`CleanupRun.SourceFolderPath` entirely. Fixed via `RegisterExportJob.BuildScopedRegisterRowsAsync`:

- **`Pipeline/SourceScope.cs`** — `BuildPrefix(run)` / `IsWithinScope(path, prefix)`, extracted from
  `RunPhaseExecutor`'s formerly-private `BuildSourceScopePrefix`/`IsWithinSourceScope` (used by Steps 1/4/8)
  with identical behaviour, now a public static helper both classes share.
- Since the register's SQL is fully operator-configured (no bindable folder id — same reasoning as Steps
  1/4/8), scoping is applied **in-app** after the query returns, matching `SourceScope` against whichever
  of a fixed set of column names (`"Folder Path"`, `FolderPath`, `Document Path`, `DocumentPath`, `Path` —
  tried in order, case-insensitive) the row carries. `ConfiguredQueryDefaults.DocumentRegister`'s default
  SQL already produces a `[Folder Path]` column in exactly this format, so scoping works out of the box.
- **Fails open** if not a single row has a recognized path column (a heavily customized query): every row
  is returned unscoped rather than silently filtered to zero, and a warning is logged. This is a deliberate
  choice — an empty result set here is indistinguishable from "nothing in this folder," which is worse than
  an unscoped result with a logged warning.

**2. New `RegisterSnapshotKind.PostReview`.** Captured in `ConfirmDeletionsHandler` immediately alongside the
existing `PreRun` capture (both created/enqueued back-to-back, replacing any prior snapshot of their own
kind), right after the Kept-exclusion projection (see above) applies the operator's Step 6/7 folder
selections, before `StartNormalizationAnalysis` is enqueued. Routed through the **same**
`RegisterExportJob.BuildOutcomeLedgerAsync` builder `PostRun` uses — reading the run's own
`CleanupRunDocument`/`CleanupRunFolder` tables (already scoped by `SourceScope` at Step 1/4 insert time, so
`PostReview` gets folder-scoping "for free," no column-matching needed) rather than a fresh MAGIQ query. The
switch in `RegisterExportJob.ExecuteAsync` is now:

```csharp
var rows = export.SnapshotKind switch
{
    RegisterSnapshotKind.PostRun or RegisterSnapshotKind.PostReview => await BuildOutcomeLedgerAsync(run.Id, ct),
    RegisterSnapshotKind.PreNormalization or RegisterSnapshotKind.PostNormalization =>
        await nameChangeRows.BuildAsync(run.Id, ct),
    _ => await BuildScopedRegisterRowsAsync(run, ct)  // PreRun / AdHoc
};
```

`BuildOutcomeLedgerAsync`'s folder rows gained three columns (used by both `PostRun` and `PostReview`):
`IsSelectedForDeletion`, `DocumentCount`, `FolderCount` — `Disposition` (`FolderStatus`) alone reads
`Pending` for everything not `Protected` prior to archival, so it can't show what the operator actually
chose; the new columns answer that, and directly answer "does this folder still have subfolders/documents
per this run's own records" — the question the Step 11 incident above raised.

Frontend: `RegisterSnapshotKind` gains `'PostReview'` (`api/runs.ts`); the pinned-snapshot timeline order in
`JobDetailsView.tsx` is PreRun → PostReview → PreNormalization → PostNormalization → PostRun.

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
