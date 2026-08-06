# NATA — Document Lifecycle Cleaner
### Specification v0.6

_Last updated: 2026-08-05_

> **Status:** As-built, plus one specified-not-yet-built phase. Epic 34120 is implemented and merged — the archival/cleanup pipeline, the React SPA, dual IIS/Docker hosting, and the operator/admin surfaces. This document describes the system as it actually behaves, with one exception: **Phase 3 — Name Normalization (Step 8)** is newly specified here and not yet implemented; its addition renumbers the archival/cleanup steps (the as-built code still uses the pre-insertion numbers — Archival at Steps 8–9, Cleanup at 10–11 — until the phase is built). Architecture rationale lives in `decisions/log.md` and `references/adrs/`, and technical detail (API catalogue, data model, config schema, SignalR contract, sequence flows) lives in `spec/dev-spec.md`.

---

## Goal

Delete documents and folders with a modification date on or before a specified calendar date, and remove the resulting empty folders for a particular facility identified by folder-name acronyms. The process is repeatable and operator-run on an annual basis.

---

## Context

NATA requires a yearly cull of every document whose modification date falls on or before a specified calendar year-end date, together with the removal of empty folders associated with a particular facility identified by acronym. Documents are not destroyed outright: they are moved into a dedicated archive library, the emptied folders are removed, and the archive library is then deleted and purged — giving a single, auditable, resumable operation that an operator drives once a year.

---

## Repository

Source code is hosted in **Azure DevOps Git**, MAGIQSoftware organisation, repository **DocumentLifecycleCleaner**, under Epic **#34120**. This planning workspace (`document-lifecycle-cleaner`) holds the spec, ADRs, decision log and delivery plan; the product repo holds the .NET API + React SPA that ships.

---

## Infrastructure & Technology

The application is a long-running, multi-phase pipeline with an interactive operator UI, hosted on-premises. The technology choices follow from that shape; full rationale is in `decisions/log.md` (2026-07-13) and the ADRs.

**Frontend** — React single-page application (Mantine UI), built and published into the API's `wwwroot` and served as static files by the same ASP.NET Core app (`UseDefaultFiles` + `UseStaticFiles` + `MapFallbackToFile("index.html")`). No separate web server and no CORS surface. FastEndpoints uses a global `api` route prefix so the SPA deep-link fallback does not intercept API routes (ADR-008).

**Backend** — C# / .NET 8 with **FastEndpoints**, using the REPR (Request–Endpoint–Response) / vertical-slice pattern. Commands and queries are dispatched through the **FastEndpoints built-in bus** (ADR-009); handlers return `Result` values that a shared endpoint base maps to HTTP, rather than throwing. CQRS is kept lightweight; full event sourcing is deliberately **not** used — the domain is a workflow, not a rich aggregate. The application deliberately does **not** use the team's `Magiq.Platform.*` stack (no DynamoDB, event sourcing, platform dispatcher, MediatR, or multi-tenancy); it is built from vanilla primitives.

**Background pipeline** — **Hangfire** runs the normalization, archival, move, delete, and purge phases, providing persistence, automatic retries, phase chaining via continuations, and a job store. This satisfies the resumability requirement (Step 10 — resume from the point of failure, no rollback of already-moved documents) and the background-purge requirement (Step 12). The Hangfire server runs in-process within the API (ADR-001).

**Run state** — Each execution is a persisted `CleanupRun` state machine (see [Run Lifecycle](#run-lifecycle)). It enforces a single active run at a time, tracks the current phase/step and run state, records per-document move failures for the identify-skip-resume behaviour (Step 10), records the source renames made in normalization (Step 8), and persists the process ticket and archive-library bookkeeping (ADR-002).

**Progress reporting** — Two-tier. The **jobs dashboard** polls the API on a configurable interval (default 30 seconds) for summary progress across all runs. The **job details view** uses **SignalR** for live, full-detail progress while the operator is actively monitoring a run. Server-Sent Events is an acceptable alternative since progress is server→client only.

**Data** — SQL Server. The application uses a **single dedicated application database** holding its own state (the `CleanupRun*` tables, the configurable-query and system-settings stores, and the register-export store) alongside the Hangfire tables, kept separate from the MAGIQ Documents database (ADR-005). App-database access is **Dapper** over thin repositories, with schema managed by **DbUp** — embedded, ordered, forward-only scripts journaled in `SchemaVersions` (ADR-010). The MAGIQ Documents database is queried directly (also via Dapper) for candidate retrieval and folder-path resolution.

**Hosting** — On-premises / customer-hosted. **IIS is the default target**; **Docker** is also supported so the client can switch without code changes (ADR-003). Kestrel is the web server in both cases (IIS reverse-proxies); all environment-specific settings come from the database-backed settings store (see [Configuration & Administration](#configuration--administration)) rather than host-specific code paths. A `Dockerfile` builds the SPA and publishes it into the API image's `wwwroot`, producing the same single self-contained artifact used under IIS. Single-server deployment either way.

**Integration** — MAGIQ Documents is integrated two ways: a **SOAP web service** (`srv.asmx`) for library/folder/document operations, and **direct SQL** via **Dapper** for the configurable candidate-retrieval and folder-path queries (ADR-004). The SOAP client is a hand-built typed `HttpClient` rather than a WCF proxy, because the service's result payloads are `xsd:any` and a generated proxy would surface them untyped anyway (ADR-011). Neither path has Windows-specific dependencies, so a Linux container remains viable. See [SOAP API Contract](#soap-api-contract).

---

## Authentication & Authorisation

The application piggybacks off MAGIQ Documents authentication rather than maintaining its own credential store. The SOAP `AuthenticateUser` action accepts a username and password and, on success, returns an `AuthenticationTicket` (carried as a `ticket` attribute on the response) that must accompany subsequent web-service calls (ADR-006).

- **Login flow:** the operator signs in with their MAGIQ Documents credentials → the app calls `AuthenticateUser` → the returned ticket establishes the app session. A best-effort `isValidTicket` call fetches the operator's display name.
- **Ticket lifecycle:** the ticket has a **sliding 20-minute timeout** — each call resets the window. `AuthenticateUser` returns a **new, independent ticket on every call**.
- **Two tickets per login:** the app obtains two independent tickets — one for the **UI session** (so the operator can log out without affecting a running job) and one dedicated to the **background process**. The two are never crossed: the UI ticket rides on the scoped current-operator context (foreground); the process ticket rides on the `CleanupRun` (background/Hangfire).
- **Keeping the process ticket alive:** a lightweight periodic `isValidTicket` heartbeat keeps the process ticket's sliding window open through lulls between phases, in addition to the incidental calls made during work.
- **Process ticket persisted across recycles:** the process ticket is stored in the application database against the `CleanupRun` (ADR-007), so it survives an IIS recycle / app restart — on startup the app reloads it and resumes the heartbeat. If the stored ticket has expired after a prolonged outage, the application obtains a new one on the authenticated user's behalf; no manual re-authentication is required. The UI ticket is not persisted — after a restart the operator simply re-authenticates for the UI.
- **Authorisation:** access is restricted to an **admin allowlist of usernames** held in the database-backed settings store (`AdminAllowlist`) and read live, so operators can be added or removed via the admin screen (or first-run setup) with no redeploy. A successfully authenticated user whose username is not on the allowlist is denied.

---

## Configuration & Administration

Operational configuration lives in the application database, not `appsettings.json`, so an administrator can change it live through the admin screens without a redeploy. Two stores back this, each seeded on first startup from code defaults and never overwritten once present:

- **Configured queries** (`ConfiguredQuery`) — the four system-configurable MAGIQ Documents SQL queries (Steps 1, 2, 4, 5). Seeded from shipped defaults authored against the real schema, editable on the **Configured Queries** admin screen with optimistic-concurrency and a live "describe result shape" schema check. Parameters (`@specifiedDate`, `@sourceDomainId`, `@folderIds`) are always bound, never concatenated.
- **System settings** (`ConfiguredSetting`) — the deletable-folder acronyms, the MAGIQ SOAP endpoint and transport tuning (timeout, retry count/backoff), the encrypted MAGIQ Documents connection string, the admin allowlist, the query command timeout, and the ticket-heartbeat interval. Edited live on the **System Settings** admin screen.

**First-run setup** is a two-phase wizard for a fresh deployment: it captures the application-database connection (which the migrator then uses to create/upgrade the schema) and the MAGIQ access essentials (SOAP endpoint + allowlist), applied live without a second restart. The MAGIQ Documents *database* connection string is set post-login in System Settings.

A run whose `CandidateDocuments`, `CandidateFolders`, or `FolderPaths` query is unset lands in **Failed**; the register export reports an error until `DocumentRegister` is set.

---

## SOAP API Contract

Base URL: `srv.asmx` (classic ASMX / infoRouter). SOAP 1.1, document/literal, operation namespace `http://tempuri.org/`. Requests are hand-built envelopes posted with a quoted `SOAPAction` header.

### Response format

All operations return HTTP `200`; the real outcome is carried by a `success` attribute on the result payload — **callers check `success`, never the HTTP status** (ADR-004/011). The result element is typed `xsd:any`, so the reader normalises both a nested element and an escaped/CDATA XML string:

```xml
<response success="true"  error="" ... />   <!-- success (may carry a ticket / rules / items) -->
<response success="false" error="optional error message" />  <!-- failure -->
```

The `error` attribute may be empty even on failure. A `success="false"` is an operation error and is **never retried**; only transport faults (network, timeout, HTTP 5xx) are retried, with exponential backoff.

### Operations

| Purpose | SOAP method | Used at |
|---|---|---|
| Authenticate; validate/keep-alive a ticket | `AuthenticateUser`, `isValidTicket` | Login, heartbeat |
| List libraries; list one level of subfolders | `GetDomains`, `GetFolders` | Step 9 browse |
| Existence checks | `UserExists`, `FolderExists`, `DocumentExists` | Setup, Steps 8–10 |
| Rename a document / folder (whitespace normalization) | `UpdateDocumentProperties`, `UpdateFolderProperties` | Step 8 |
| Create archive library / subfolder | `CreateDomain`, `CreateFolder` | Step 9 |
| Read / write a folder's rules | `GetFolderRules`, `SetFolderRules` | Steps 10–11 (delete-rule handling) |
| Move a document | `Move` | Step 10 |
| Delete a folder (to recycle bin) | `DeleteFolder` | Step 11 |
| Delete the library; list & purge recycle-bin items | `DeleteDomain`, `GetRecycleBinContent`, `PurgeRecycleBinItem` | Step 12 |

### Step 12 — library purge sequence

1. `DeleteDomain` deletes the archive library; its contents scatter into the recycle bin as individual items, each carrying `DeletePath = "\{ArchiveLibraryName}"`.
2. `GetRecycleBinContent` lists the recycle bin.
3. Each item belonging to this run's library (matched by `DeletePath`) is permanently removed with `PurgeRecycleBinItem` — a targeted purge, never a blanket empty-recycle-bin.

### Folder rules and the "Move is copy + delete" constraint

MAGIQ implements `Move` as a copy **followed by a delete**, and folders carry per-folder rules. Both halves of a move can be blocked: the **delete-half** by `DISALLOWDOCUMENTDELETE` (documents in a folder) or `DISALLOWFOLDERDELETE` (child folders of a folder; the **parent** governs a child's deletion), and the **copy-half** by `DISALLOWNEWDOCUMENT` (adding a new document to a folder). So a source folder that disallows document deletes fails a Step 10 move; a parent that disallows folder deletes fails a Step 11 `DeleteFolder`; and — on a **rollback** — a document's original folder that disallows new documents fails the move-back (the copy re-creates the document there).

The pipeline handles all three **reactively at execution time**: when a `Move` or `DeleteFolder` fails, the application reads the governing folder's **live** rules (`GetFolderRules`); only if the relevant rule is actually blocking does it flip that one rule to `allows` (`SetFolderRules`, applied to that folder only), retry the operation once, and then restore the exact original rules. The rule and folder depend on the site: `DocumentDeletes` on the source folder (Step 10 move), `FolderDeletes` on the parent (Step 11 delete), and `NewDocuments` on the document's original folder (rollback move-back). Reading the live rule at the moment of failure — rather than a snapshot taken at identification — means a rule an administrator changes mid-run is still honoured. If the rule already permits the action, or the rules cannot be read, or the relax is rejected, nothing is changed and the original error stands. The delete restriction is also surfaced to the operator at review as an informational signal (see Step 6). See `decisions/log.md` [2026-08-05] and the ADR-004/011 amendments.

### Whitespace normalization and the "double-space" bug

The MAGIQ Documents desktop UI allows a document or folder to be **created with a run of consecutive whitespace** in its name (e.g. a double space), but the SOAP web service **collapses and trims whitespace** in names on `CreateFolder`/`Move` — so it cannot create or move an item whose name (or whose folder path at any level) contains a double space: the target it would produce never matches the doubled-whitespace name, and the operation errors (nothing moves). A `MagiqPath.Normalize` helper already collapses SQL-derived paths to the service's single-space view so destinations line up; but the **source** items physically retain their doubled whitespace in the repository, so the `Move` still fails.

The fix is a dedicated **Name Normalization** phase (Step 8, below) that renames the offending **source** items *before* the archival move, using `UpdateFolderProperties`(`Path`, `NewFolderName`) for a folder level and `UpdateDocumentProperties`(`Path`, `NewDocumentName`) for a document — replacing each doubled-whitespace run with a single space so the item becomes web-service-addressable and movable. Every rename is recorded (see [Run Lifecycle](#run-lifecycle)). The exact path form the rename ops accept for a doubled-whitespace source item is confirmed at integration against training (same `xsd:any`/behaviour class as ADR-011 / Story 34525).

---

## MAGIQ Documents queries

Four system-configurable Dapper queries drive the data steps (Steps 1, 2, 4, 5). They are authored against the real MAGIQ Documents schema (`PUBLICATION` / `FOLDERS` / `FOLDERMAP` / `DOMAINS`) and ship as editable defaults:

- **Candidate documents (Step 1)** — every document with modification date ≤ the cutoff, in the chosen source library, with its resolved path. Also flags whether the document's folder disallows document deletes (review signal).
- **Document register (Step 2)** — a human-readable register of the candidate documents; the SELECT's column aliases become the export's Excel headers, so an administrator can add or remove columns without a deploy.
- **Candidate folders (Step 4)** — each folder that directly holds a candidate document, plus its full ancestor chain, with direct document/folder counts, size, a "contains a post-cutoff document" bit, and the two delete-rule review flags (the folder's own document-delete rule and its parent's folder-delete rule).
- **Folder paths (Step 5)** — the full path for a set of folder ids.

Acronym matching and ancestor-protection are applied **in the application**, not in SQL. The delete-rule flags are an informational snapshot for the review only — execution always re-reads the live rules — so they are not part of the queries' required-column contract and default to "not blocked" when a customised query omits them.

---

## Parameters

**Cutoff date and source library** — When creating a run, the operator picks the **cutoff date** (a calendar year-end date, e.g. 31 December 2024) and the **source library** to cull from, chosen from the live list of MAGIQ Documents libraries. Both are persisted on the `CleanupRun` and bound into the configured queries per run (`@specifiedDate`, `@sourceDomainId`). Documents with a modification date **≤** the cutoff are candidates.

**Who runs the process** — A MAGIQ Documents system administrator or power user on the admin allowlist.

---

## Non-Functional Requirements

**Document volume** — A typical NATA run processes **tens of thousands of documents**, which drives:

- Step 10 (document move) runs as a batched background operation with live progress via SignalR; progress events are emitted per-batch, not per-document. Step 8 (name normalization) runs the same way — batched renames with per-batch progress.
- Timeouts (query command timeout, SOAP client timeout) are configurable to accommodate long-running operations.
- The job details view shows a % progress bar, current/total count, current item path (when available), elapsed time, and ETA (when calculable), plus failures as they occur.
- The UI stays responsive while background phases execute.

---

## Process Phases

| Phase | Steps | Type |
|---|---|---|
| **Phase 1: Identification** | Steps 1, 4, 5 (register export 2–3 on demand) | Automated |
| **Phase 2: Review & Selection** | Steps 6–7 | Interactive (React UI + .NET API) |
| **Phase 3: Name Normalization** | Step 8 | Operational (background) |
| **Phase 4: Archival** | Steps 9–10 | Operational (background) |
| **Phase 5: Cleanup** | Steps 11–12 | Automated / background |

> **Phase 3 — Name Normalization** is the first phase that **mutates** the customer's source repository (it renames source documents/folders in place). It is therefore the point at which the run becomes an **audit** that can no longer be deleted — only archived for the record (see [Run Lifecycle](#run-lifecycle)).

---

## Run Lifecycle

Each execution is a single `CleanupRun` record progressing through a defined set of states. Only one run may be active at a time; terminal runs can be archived out of the active list once resolved.

### Run states

| State | Description |
|---|---|
| `NotStarted` | Run created; Phase 1 not yet triggered |
| `Running` | A background phase is actively executing |
| `AwaitingInput` | Paused at an interactive step (review, or the Step 12 purge pause); operator action required |
| `Cancelled` | Operator cancelled the run mid-phase |
| `Failed` | An error halted the run; a recovery action is required |
| `Completed` | All phases finished successfully |
| `Abandoned` | Operator wrote off a failed run; a new run may be started |

A terminal run also carries a **rollback status** (`None` / `InProgress` / `Succeeded` / `Failed`) and may be **archived** (moved out of the active list, retained for the record).

**Audit lock (Rule 7).** Once a run has **entered the Name Normalization phase (Step 8)** it has renamed items in the customer's live repository — a change a rollback does **not** undo (rollback returns moved documents and tears down a run-created archive, but does not restore original names). Such a run is therefore an **audit**: it can never be permanently **deleted**, only **archived** for the record. The recorded rename log is retained with it. This holds regardless of how far the run then progressed or whether its document moves were later rolled back.

### UI structure

- **Jobs Dashboard** — lists all runs, most recent first, with summary state, progress, and success/failure counts; four summary metric cards; a new-run form; and inline lifecycle actions. Progress refreshes on the configurable polling interval (default 30 seconds). This is the landing page.
- **Job Details View** — opened from the dashboard. Shows full run detail and live progress via SignalR, a final success/failure summary at completion, the register-download control, the run's lifecycle actions, and two logs: the **phase log** (phase-grain: started/completed/failed per phase) and the **operation audit trail** (object-grain: every create, move, delete, purge, rename, folder-rule relax/restore, and operator decision the run made against MAGIQ, with timestamp, outcome, and operator — see below).

### Auditability — before, during, and after a run

A run is designed to be fully accountable end to end (`decisions/log.md` [2026-08-05]):

- **Before** — the operator captures a **pre-run Document Register** snapshot (the source library as it stands, ≤ cutoff), retained with the run and exportable to CSV or Excel.
- **During** — every mutating operation the run performs against MAGIQ, and every operator decision that shapes it, is written to an **append-only operation audit trail** (`CleanupRunOperation`): archive-library and folder creates, document moves (recorded per batch), empty-folder deletes, library delete + recycle-bin purge, source renames (Name Normalization), each reactive folder-rule relax and restore, operator overrides of the acronym pre-select, and the purge authorisation (pre-granted at Step 7 or typed at Step 12). This is separate from, and complements, the phase log.
- **After** — a **run outcome ledger** (each document's final disposition, each folder's final status, and the rename log) gives the post-run picture, exportable to CSV or Excel. Because the source has been moved/purged by then, "after" is built from the run's own record, not a re-query of the source library.

Together these answer *what the repository looked like before, what the tool did, and what it looked like after*. Both the on-demand register and the pinned snapshots export to **CSV or Excel** (`?format=csv|xlsx`); the pre-run snapshot is captured automatically at confirmation and the post-run outcome ledger when the run completes, both retained with the run in CSV. (Implemented, including the SPA: the Job Details view shows the operation audit trail and a before/after snapshot download panel with an Excel/CSV toggle. Remaining polish — reviewing-operator attribution for overrides, and `Rename` rows once Name Normalization ships — is tracked in `deferred-work-plan.md`.)

### Navigation rules

- **Review:** the operator reviews and selects folders at Step 6, then confirms at Step 7 (which may return to Step 6 to revise selections). After confirming, the operator lands on the jobs dashboard / details view to monitor the background phases.
- **Cancel:** the operator may cancel an active run; it stops cooperatively at the next guarded checkpoint and enters `Cancelled`. Documents already moved remain in the archive and can be recovered by a rollback.
- **Completed runs:** a `Completed` run is final; a new calendar year requires a new run.

### Error recovery and run actions

A `Failed` run — and, where noted, other states — offers these operator actions from both the dashboard and the details view:

| Action | Behaviour |
|---|---|
| **Reset** | Re-enqueue the current phase from its start (idempotent bodies skip already-completed work) |
| **Retry** | Re-enqueue the current phase to resume from the point of failure |
| **Cancel** | Cooperatively stop an active run (→ `Cancelled`) |
| **Abandon** | Mark a failed run `Abandoned`, unblocking a new run (simple confirm dialog) |
| **Rollback** | For a terminal run: move every archived document back to its original folder and, if this run created the archive library, delete and purge it — returning MAGIQ Documents to its pre-run state. Succeeds only when every document is safely back. A rollback makes the run deletable **unless** the run had entered Name Normalization (Step 8): renames are not reversed, so such a run stays an audit and is archived, not deleted (Rule 7) |
| **Re-run identification** | For a run still paused in review (before confirmation): rebuild the candidate set for the same cutoff and source library (discards current review selections; gated behind a confirmation) |

Because the phase bodies are idempotent, Reset and Retry converge behaviourally — neither re-moves a moved document nor recreates the library; they differ in the step marker and the log event recorded. The **failed-document list persists** across Reset and Retry so the operator can compare attempts. The reactive folder delete-rule handling (above) applies on every move/delete attempt, including retries.

---

## The Process

### Phase 1 — Identification

#### Step 1 — Retrieve candidate documents

Run the configured `CandidateDocuments` query to retrieve every document in the source library whose modification date is ≤ the cutoff. Candidates are persisted against the run (`Pending`) for the archival move. Each candidate also records whether its source folder disallows document deletes (a review/audit flag).

#### Steps 2–3 — Document register and export (on demand)

The configured `DocumentRegister` query produces a human-readable register of the candidate documents; its column aliases become the Excel headers. NATA had no existing register report, so the application ships a default one, editable via the admin screen. Export runs as a background job (not inside the download request): the operator requests it, a Hangfire job renders the `.xlsx` off the request thread and stashes it, and the SPA polls for progress and then downloads — decoupling generation from any request/proxy/IIS idle timeout.

#### Step 4 — Produce candidate folders

From the candidate documents, the configured `CandidateFolders` query returns each folder that directly holds a candidate document **and its full ancestor chain**, with each folder's direct document/folder counts, size, a "contains a post-cutoff document" bit, and the delete-rule review flags. The application then applies protection and the acronym pre-select in memory:

- **Protection (Rule 2):** a folder that directly holds a document modified **after** the cutoff is protected, and so is its **full ancestor hierarchy**. Protected folders are never deletable.
- **Acronym pre-select:** a folder whose name matches a deletable acronym is pre-selected for deletion (selected by default), unless it is protected — protection always wins.

#### Step 5 — Resolve folder paths

The configured `FolderPaths` query returns the full resolved path for the candidate folders and their ancestors; these paths are surfaced in the review UI and used as the SOAP move/delete targets.

### Phase 2 — Review & Selection

#### Step 6 — Review and select folders (React UI + .NET API)

A React UI presents the candidate folders (tree or flat list) with their resolved paths and review columns. Folders matching a deletable acronym are **pre-selected** for deletion; the operator can deliberately **override** an individual pre-selected folder to keep it. Protected folders (Rule 2) are never deletable and cannot be selected. Selections are auto-saved as a draft so an interrupted review survives a refresh.

- **Columns (minimum):** folder path, document count, folder count, size; status; the design supports extra columns without a redesign.
- **Delete-locked signal:** folders sitting under a MAGIQ "disallow delete" rule (their own document-delete rule, or their parent's folder-delete rule) show a **"Delete-locked"** badge and can be filtered. This is informational — the tool lifts the rule reactively during archive/cleanup and restores it, so these folders are still processed; the badge simply makes the restriction visible up front.
- **Interactions:** virtual scroll (no pagination); free-text filter on path/acronym; status filters (deletable, protected, pre-selected, overridden, selected, empty, has-documents, delete-locked); subtree/tri-state selection in tree view; bulk select/deselect over freely-selectable rows (pre-selected rows change only via a deliberate per-row override).
- **Impact summary + confirm:** a live summary of folders/documents/size to be deleted, with a warning when selected folders still contain documents, and a confirm dialog before the irreversible submit.

No document types, statuses, or categories require unconditional preservation — all documents are subject to the date cutoff.

#### Step 7 — Confirm selections, choose the archive, pre-authorise purge

Confirming the review submits the folder selections and captures the archival choices; it does **not** itself delete anything (deletion happens in Step 11). Before advancing, the system validates every selected folder against the delete constraint (Rule 4): any folder still in a protected state is reported **inline on the blocked rows**, and confirmation cannot proceed until the blockers are deselected. At confirmation the operator also:

- **Selects the archive library (Step 9, below)** — create new, or choose existing, with an optional subfolder.
- **Optionally pre-authorises the purge** — a checkbox, "Automatically proceed with purge when ready". If checked, the run proceeds through Step 12 without further input (the confirming user and timestamp are recorded); if unchecked (default), the run pauses for a manual typed confirmation at Step 12.

### Phase 3 — Name Normalization

#### Step 8 — Normalize source names (work around the double-space bug)

_New phase — specified here, not yet implemented. See [Whitespace normalization](#whitespace-normalization-and-the-double-space-bug) for the underlying bug._

Before any document is moved, this background phase renames — **in the source repository** — every candidate item whose name (or whose containing folder path, at any level) holds a run of consecutive whitespace, collapsing each run to a single space so the SOAP `Move`/`CreateFolder` operations can address and move it. Working from the run's candidate documents and their resolved paths:

- **Folder path levels first.** Every distinct folder level, across all candidate document paths, that contains a double space is renamed via `UpdateFolderProperties`(`Path`, `NewFolderName`). Levels are processed **top-down (ancestors before descendants)** so that once a parent is normalized the descendant paths stay resolvable; a level already free of doubled whitespace is skipped.
- **Then documents.** Any candidate document whose own name contains a double space is renamed via `UpdateDocumentProperties`(`Path`, `NewDocumentName`), addressing it by its (now-normalized) folder path.

**Every rename is recorded** — the item type (folder/document), its original path/name and the new normalized name, the operator/process ticket, and a timestamp — persisted against the run and written to the phase audit log. This record is the point of the phase: it is a permanent account of the changes made to NATA's live repository, which is **why entering this phase makes the run an audit that can no longer be deleted, only archived** (Rule 7, [Run Lifecycle](#run-lifecycle)).

Renames are batched with per-item status and resume-from-failure, and report progress like Step 10. The phase is idempotent on resume: an item already normalized (no doubled whitespace remains) is skipped, so a re-invoked job re-scans cleanly. A rename that cannot be completed leaves the item flagged and, as with an unmovable document, blocks the archival move for that item; the run surfaces the failures. Only once normalization is complete does the pipeline chain to archival.

The exact path form the rename ops accept for a still-doubled source item, and the ordering behaviour, are confirmed at integration against training (same `xsd:any`/behaviour class as ADR-011 / Story 34525).

### Phase 4 — Archival

#### Step 9 — Select or create the archive library

The destination for the candidate documents is either a **new library** (enter a name; a subfolder may be created to organise the archive) or an **existing library** chosen from the live MAGIQ Documents list (also with an optional subfolder). The UI is a modal with a name filter over the library list and on-demand, one-level subfolder browsing. New-library name prefill: `Archive {SourceLibraryName} - {ShortFriendlyDate}` (e.g. `Archive NATA - Dec 2024`), editable before confirming. A library the run **creates** is recorded so a rollback can tear it down; an operator-chosen **existing** library is never torn down wholesale.

#### Step 10 — Move documents to the archive library

The background phase creates the archive library if needed, ensures the destination folder structure exists, and moves each candidate document into the archive, recreating its source-folder hierarchy beneath the destination. Because Step 8 has already normalized the source names, the source and destination paths are whitespace-clean and the `Move` addresses them cleanly. Moves are batched with per-document status, a single retry pass for failures, and resume-from-failure; progress shows on the dashboard (polling) and in the details view (live via SignalR), with failed documents surfaced as they occur.

If a move fails because the source folder disallows document deletes, the reactive delete-rule handling relaxes that folder's rule, retries the move, and restores the rule (see [Folder rules](#folder-rules-and-the-move-is-copy--delete-constraint)). A document that still cannot be moved after the retry is left `Failed`; there is no rollback of already-moved documents within the run — the phase resumes from the point of failure. If any documents remain unmovable, the run fails with them listed, and the cleanup phase does not proceed.

### Phase 5 — Cleanup

#### Step 11 — Delete empty folders

Once every move is confirmed complete, the selected, non-protected folders (now empty) are deleted to the recycle bin. This is best-effort per folder: a failed delete is recorded against the folder and surfaced, and does not stop the run. If a delete fails because the **parent** folder disallows folder deletes, the reactive delete-rule handling relaxes the parent's rule, retries the delete, and restores it.

#### Step 12 — Delete and purge the archive library

The archive library is deleted and permanently purged as a background process (the `DeleteDomain` → `GetRecycleBinContent` → `PurgeRecycleBinItem` sequence above, targeted to this run's items). Purge behaviour depends on the Step 7 pre-authorisation:

- **Path A — pre-authorised:** purge proceeds automatically; the pre-authorising user and timestamp are on record.
- **Path B — manual (default):** the run pauses at **"Ready for purge"** (`AwaitingInput`); the details view presents a red **Purge** button whose modal requires the operator to type **"permanently delete"** before the purge starts. The confirming user and timestamp are recorded.

There is no holding period between delete and purge — the purge starts immediately once confirmation is recorded. Steps 11 and 12 report progress the same way as Step 10.

---

## Deletable Folder Naming Conventions

Folders whose name matches one of the following acronyms are eligible for deletion and are **pre-selected** (selected by default) in the Step 6 review. The operator may deliberately override an individual pre-selected folder to keep it; a **protected** folder (Rule 2) is never deletable regardless of acronym.

```
ADV · ARE · ASS · CEA · CGA · CRE · DCR · DEL · DFS · DRV · DTV · FAS
FES · OLC · OLN · REI · RES · SRE · SRV · STF · STI · VAR
```

- **List:** the current list, held in the system-settings store and editable live on the admin screen — NATA can add or remove acronyms without a redeploy.
- **Matching:** the acronym must appear **anywhere** in the folder name (contains match), **case-sensitive**.

---

## Rules

1. **Date cutoff** — Documents with a modification date ≤ the cutoff (in the chosen source library) are candidates for deletion.

2. **Folder protection** — A folder holding at least one document modified after the cutoff must not be deleted; protection extends to the **full ancestor hierarchy**. Protection overrides the acronym pre-select — a protected folder is never deletable or selectable.

3. **Empty folders** — Folders left empty after the move are deleted (Step 11).

4. **Delete constraint** — Confirmation (Step 7) cannot proceed while any selected folder is protected. The system validates all selected folders and reports the blockers inline; they must be deselected before proceeding.

5. **Confirm before purge** — The archive library is not deleted/purged (Step 12) until purge is authorised — either pre-granted at Step 7 or granted manually via the typed "permanently delete" confirmation. The confirming user and timestamp are recorded in both cases.

6. **Delete-rule handling** — A folder rule that disallows deletes (which would otherwise fail a Step 10 move or a Step 11 folder delete, since a move is a copy + delete) is worked around reactively: the blocking rule is read live, temporarily relaxed on the one folder, the operation retried, and the original rule restored. The restriction is surfaced at review for visibility but is not a blocker.

7. **Name normalization & audit lock** — Because the MAGIQ web service cannot `Move`/`CreateFolder` an item whose name (or folder-path level) holds a double space — while the desktop UI allows such names — a **Name Normalization** phase (Step 8) renames every affected **source** item in place (doubled whitespace → single space) before the archival move, so the move can succeed. Every rename is recorded (item type, original path/name, new name, operator/ticket, timestamp). These renames mutate NATA's live repository and are **not** reversed by a rollback, so **once the normalization phase has begun the run becomes an audit** and can no longer be permanently deleted — only archived for the record.

---

## History

This document reflects the system as built, plus the one specified-not-yet-built **Name Normalization** phase (Step 8) added to work around the SOAP double-space bug (`decisions/log.md` [2026-08-05]). The full history of decisions and resolved questions — protection scope, archive-library selection, purge confirmation, ticket-expiry recovery, the move to database-backed configuration, the overridable acronym pre-select, the folder delete-rule handling, and the name-normalization phase — is recorded in `decisions/log.md` and `references/adrs/`. Ordered delivery is in `delivery-plan.md`; current status in `tasks.md`.
