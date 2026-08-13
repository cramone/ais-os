# NATA — Document Lifecycle Cleaner
### Specification v0.6

_Last updated: 2026-08-11_

> **Status:** As-built. Epic 34120 is implemented and merged — the archival/cleanup pipeline, the React SPA, dual IIS/Docker hosting, and the operator/admin surfaces — and **Phase 3 — Name Normalization (Step 8)** is now implemented in the working tree as well (`RunPhase.Normalization`, the `RenamePlanner` + `ExecuteNormalizationAsync` phase, the `dbo.CleanupRunRename` store and the `EnteredNormalization` audit-lock, chained confirm→normalization→archival→cleanup). The step numbering reflects the built system throughout: Name Normalization = Step 8, Archival = Steps 9–10, Cleanup = Steps 11–12. This document describes the system as it actually behaves. Architecture rationale lives in `decisions/log.md` and `references/adrs/`, and technical detail (API catalogue, data model, config schema, SignalR contract, sequence flows) lives in `spec/dev-spec.md`.

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
- **Authorisation:** access is restricted to an **admin allowlist of usernames** held in the database-backed settings store (`AdminAllowlist`) and read live, so operators can be added or removed via the admin screen (or first-run setup) with no redeploy. A successfully authenticated user whose username is not on the allowlist is denied. Operators are chosen from a **`GetAllUsers` typeahead** (search by username / first / last name; disabled `Enabled="FALSE"` accounts are hidden), not typed free-hand.

---

## Configuration & Administration

Operational configuration lives in the application database, not `appsettings.json`, so an administrator can change it live through the admin screens without a redeploy. Two stores back this, each seeded on first startup from code defaults and never overwritten once present:

- **Configured queries** (`ConfiguredQuery`) — the four system-configurable MAGIQ Documents SQL queries (Steps 1, 2, 4, 5). Seeded from shipped defaults authored against the real schema, editable on the **Configured Queries** admin screen with optimistic-concurrency and a live "describe result shape" schema check. Parameters (`@specifiedDate`, `@sourceDomainId`, `@folderIds`) are always bound, never concatenated.
- **System settings** (`ConfiguredSetting`) — the deletable-folder acronyms, the MAGIQ SOAP endpoint and transport tuning (timeout, retry count/backoff), the encrypted MAGIQ Documents connection string, the admin allowlist, the query command timeout, and the ticket-heartbeat interval. Edited live on the **System Settings** admin screen.

**First-run setup** is a two-phase wizard for a fresh deployment: it captures the application-database connection (which the migrator then uses to create/upgrade the schema) and the MAGIQ access essentials (SOAP endpoint + allowlist), applied live without a second restart. The MAGIQ access phase runs: **test the SOAP endpoint → bootstrap sign-in → allowlist**. The endpoint field auto-appends `/srv.asmx` if the operator leaves it off. The operator then signs in with a MAGIQ account (authenticated against the candidate endpoint); that account is auto-added to the allowlist as the first operator (pinned, non-removable) and its ticket authorises the `GetAllUsers` typeahead used to add any further operators. This bootstrap sign-in is required because `GetAllUsers` (like the retired anonymous `UserExists` allowlist check) cannot be called anonymously. **Once signed in the endpoint is locked** (shown as a read-only, visually distinct field); changing it requires an explicit **Change** action, which forces a fresh sign-in and resets the allowlist — so an operator can't authenticate against one service and then silently repoint at another. **Completing setup carries the operator straight into the app** (the bootstrap sign-in's shared ticket cookie is adopted — no second login), falling back to the sign-in screen only if that ticket has lapsed. The MAGIQ Documents *database* connection string is set post-login in System Settings.

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
| Existence checks | `UserExists`, `FolderExists`, `DocumentExists` | Steps 8–10 |
| List users (admin-allowlist typeahead) | `GetAllUsers` | Setup bootstrap, System Settings |
| Rename a document / folder (whitespace normalization) | `UpdateDocumentProperties`, `UpdateFolderProperties` | Step 8 |
| Delete a document (to recycle bin) | `DeleteDocument` | Step 8 (keep-one/delete-other conflict resolution) |
| Read a document + its version checksums (duplicate-identity check) | `GetDocument` (`withVersions=true`) | Step 8 (document-conflict analysis) |
| Create archive library / subfolder | `CreateDomain`, `CreateFolder` | Step 9 |
| Read / write a folder's rules | `GetFolderRules`, `SetFolderRules` | Steps 8, 10–11 (delete-rule handling) |
| Move a document | `Move` | Step 8 (folder merge), Step 10 |
| Delete a folder (to recycle bin) | `DeleteFolder` | Step 8 (folder merge), Step 11 |
| Delete the library; list & purge recycle-bin items | `DeleteDomain`, `GetRecycleBinContent`, `PurgeRecycleBinItem` | Step 12 |

### Step 12 — library purge sequence

1. `DeleteDomain` deletes the archive library; its contents scatter into the recycle bin as individual items, each carrying `DeletePath = "\{ArchiveLibraryName}"`.
2. `GetRecycleBinContent` lists the recycle bin.
3. Each item belonging to this run's library (matched by `DeletePath`) is permanently removed with `PurgeRecycleBinItem` — a targeted purge, never a blanket empty-recycle-bin.

### Folder rules and the "Move is copy + delete" constraint

MAGIQ implements `Move` as a copy **followed by a delete**, and folders carry per-folder rules. Both halves of a move can be blocked: the **delete-half** by `DISALLOWDOCUMENTDELETE` (documents in a folder) or `DISALLOWFOLDERDELETE` (child folders of a folder; the **parent** governs a child's deletion), and the **copy-half** by `DISALLOWNEWDOCUMENT` (adding a new document to a folder). So a source folder that disallows document deletes fails a Step 10 move; a parent that disallows folder deletes fails a Step 11 `DeleteFolder`; and — on a **rollback** — a document's original folder that disallows new documents fails the move-back (the copy re-creates the document there).

The pipeline handles all three **reactively at execution time**: when a `Move` or `DeleteFolder` fails, the application reads the governing folder's **live** rules (`GetFolderRules`); only if the relevant rule is actually blocking does it flip that one rule to `allows` (`SetFolderRules`, applied to that folder only), retry the operation, and then restore the exact original rules. The rule and folder depend on the site: `DocumentDeletes` on the source folder (Step 10 move), `FolderDeletes` on the parent (Step 11 delete), and `NewDocuments` on the document's original folder (rollback move-back). Reading the live rule at the moment of failure — rather than a snapshot taken at identification — means a rule an administrator changes mid-run is still honoured. If the rule already permits the action, or the rules cannot be read, or the relax is rejected, nothing is changed and the original error stands. The delete restriction is also surfaced to the operator at review as an informational signal (see Step 6).

The relax/restore is scoped to the **whole set of items that share the one rule-bearing folder**, not to each item: the phase groups its work by that folder (a folder's documents in a Step 10 move, a parent's child folders in a Step 11 delete, a folder's returning documents in a rollback), attempts each item once, and only if some are blocked does it relax that folder's rule **a single time**, retry just the still-blocked items under the relaxed rule, and restore **once**. This replaced an earlier per-item relax/revert that flipped the same folder's rule once per item; against MAGIQ that rapid flip/read churn left the second and later items in a folder failing even though the folder genuinely needed the rule relaxed (`decisions/log.md` [2026-08-09]). See `decisions/log.md` [2026-08-05, 2026-08-09] and the ADR-004/011 amendments.

### Whitespace normalization and the "double-space" bug

The MAGIQ Documents desktop UI allows a document or folder to be **created with whitespace and invisible characters the SOAP web service will not reproduce** — and because operators often paste names in from Word, email, or the web, these characters arrive without anyone noticing. Two classes cause the mismatch:

- **Whitespace variants** — a run of consecutive whitespace (e.g. a double space or a tab), and any of the Unicode space characters that are not the plain `U+0020`: the non-breaking space (`U+00A0`, HTML `&nbsp;`), the narrow and figure no-break spaces (`U+202F`, `U+2007`), the em/en block (`U+2000`–`U+200A`), the ideographic space (`U+3000`), and the rest of the Unicode `White_Space` set (the full list is in [Whitespace normalization scope](#whitespace-normalization-scope) below). The service **collapses and trims regular whitespace and treats these space variants as an ordinary space** — which is how the desktop UI ends up with two folders that look identical (one with a normal space, one with `U+00A0`) that the service regards as the same name.
- **Invisible format characters** — zero-width and formatting code points that render as *nothing* but still change the stored name: the zero-width space (`U+200B`), the zero-width non-joiner/joiner (`U+200C`/`U+200D`), the word joiner (`U+2060`), the byte-order mark / zero-width no-break space (`U+FEFF`), and the soft hyphen (`U+00AD`).

In either case the service cannot create or move an item whose name (or whose folder path at any level) carries one of these characters: the target it would produce never matches the raw source name, and the operation errors (nothing moves). A `MagiqPath.Normalize` helper already folds SQL-derived paths to the service's view (whitespace variants → regular space and collapsed, invisibles stripped) so destinations line up; but the **source** items physically retain the original characters in the repository, so the `Move` still fails.

The fix is a dedicated **Name Normalization** phase (Step 8, below) that renames the offending **source** items *before* the archival move, using `UpdateFolderProperties`(`Path`, `NewFolderName`) for a folder level and `UpdateDocumentProperties`(`Path`, `NewDocumentName`) for a document. It applies two rules so the item becomes web-service-addressable and movable:

1. **Whitespace → a single regular space.** Every character with the Unicode `White_Space` property (equivalently, .NET `char.IsWhiteSpace`) is converted to a regular space (`U+0020`); consecutive whitespace is collapsed to one; leading/trailing whitespace is trimmed — mirroring the service's collapsed/trimmed view.
2. **Invisible format characters → stripped.** The zero-width / formatting code points above (`U+200B`, `U+200C`, `U+200D`, `U+2060`, `U+FEFF`, `U+00AD`) are **removed entirely** rather than converted to a space, so an invisible sitting inside a word does not split it.

Every rename is recorded (see [Run Lifecycle](#run-lifecycle)). The exact path form the rename ops accept for a still-affected source item is confirmed at integration against training (same `xsd:any`/behaviour class as ADR-011 / Story 34525).

#### Whitespace normalization scope

The definitive character set the phase acts on. **Rule 1 — collapse to a single regular space** covers every code point with the Unicode `White_Space` property (25 in total; in .NET, exactly the characters for which `char.IsWhiteSpace` returns `true`), so it need not be hardcoded:

| Range / code point | Characters |
|---|---|
| `U+0009`–`U+000D` | tab, line feed, vertical tab, form feed, carriage return |
| `U+0020` | space (the target character) |
| `U+0085` | next line (NEL) |
| `U+00A0` | no-break space (`&nbsp;`) |
| `U+1680` | ogham space mark |
| `U+2000`–`U+200A` | en quad, em quad, en space, em space, three-/four-/six-per-em space, figure space, punctuation space, thin space, hair space |
| `U+2028` / `U+2029` | line separator / paragraph separator |
| `U+202F` | narrow no-break space |
| `U+205F` | medium mathematical space |
| `U+3000` | ideographic space (full-width) |

**Rule 2 — strip entirely** covers the invisible/zero-width format characters that render as nothing and are therefore *not* in the `White_Space` set (so `char.IsWhiteSpace` never matches them). This is a **fixed, explicit list** — removed, never converted to a space:

| Code point | Character |
|---|---|
| `U+200B` | zero-width space |
| `U+200C` | zero-width non-joiner |
| `U+200D` | zero-width joiner |
| `U+2060` | word joiner |
| `U+FEFF` | zero-width no-break space / byte-order mark |
| `U+00AD` | soft hyphen |

> `U+180E` (Mongolian vowel separator) is a borderline case — a space separator before Unicode 6.3, a format character since — and is **not** in either list today; add it to the strip list if a real case surfaces.

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
| **Phase 3: Name Normalization** | Step 8 (8a dry run · review gate · 8b execute) | Background + interactive review gate |
| **Phase 4: Archival** | Steps 9–10 | Operational (background) |
| **Phase 5: Cleanup** | Steps 11–12 | Automated / background |

> **Phase 3 — Name Normalization** is the first phase that **mutates** the customer's source repository, but only in its **execute** part (Step 8b): it first runs a non-mutating **dry run** and, whenever it would change any name, pauses for the operator to review the planned changes (and resolve any conflicts) and **confirm** before executing. The run becomes an **audit** that can no longer be deleted — only archived — at the **first executed rename/merge/delete**, not merely on entering the phase (see [Run Lifecycle](#run-lifecycle)).

---

## Run Lifecycle

Each execution is a single `CleanupRun` record progressing through a defined set of states. Only one run may be active at a time; terminal runs can be archived out of the active list once resolved.

### Run states

| State | Description |
|---|---|
| `NotStarted` | Run created; Phase 1 not yet triggered |
| `Running` | A background phase is actively executing |
| `AwaitingInput` | Paused at an interactive step (Step 6–7 review, the Step 8 name-change review gate, the post-archival pause after a Step 10 move-failure retry clears every failure, or the Step 12 purge pause); operator action required |
| `Cancelled` | Operator cancelled the run mid-phase |
| `Failed` | An error halted the run; a recovery action is required |
| `Completed` | All phases finished successfully |
| `Abandoned` | Operator wrote off a failed run; a new run may be started |

A terminal run also carries a **rollback status** (`None` / `InProgress` / `Succeeded` / `Failed`) and may be **archived** (moved out of the active list, retained for the record).

**Audit lock (Rule 7).** Once the Name Normalization phase has **executed its first mutation** (Step 8b — a rename, folder merge, or duplicate-document delete) the run has changed the customer's live repository — a change a rollback does **not** undo (rollback returns moved documents and tears down a run-created archive, but does not restore original names or un-merge/un-delete). Such a run is therefore an **audit**: it can never be permanently **deleted**, only **archived** for the record. The recorded rename/merge/delete log is retained with it, and this holds regardless of how far the run then progressed or whether its document moves were later rolled back. A run still in the Step 8 **dry run** or **review gate** (resolving conflicts or reviewing/confirming the change list) has changed nothing and **remains deletable** — the lock trips on the first executed change, not on entering the phase.

### UI structure

- **Jobs Dashboard** — lists all runs, most recent first, with summary state, progress, and success/failure counts; four summary metric cards; a new-run form; and inline lifecycle actions. Progress refreshes on the configurable polling interval (default 30 seconds). This is the landing page.
- **Job Details View** — opened from the dashboard. At the top a **persistent phase stepper** shows where the run is across the whole pipeline — **Identify → Review → Normalize → Archive → Cleanup** — driven by the run's actual phase: completed phases read as done, the current one is highlighted (or marked failed), and a Normalization phase that needed no changes simply shows complete as the run flows on to archival. Below it, it shows full run detail and live progress via SignalR, a final success/failure summary at completion, the register-download control, the run's lifecycle actions, and two logs: the **phase log** (phase-grain: started/completed/failed per phase) and the **operation audit trail** (object-grain: every create, move, delete, purge, rename, merge, folder-rule relax/restore, and operator decision the run made against MAGIQ, with timestamp, outcome, and operator — see below). The audit trail is presented as a compact **live activity** feed of the most recent operations with plain-language descriptions above the **full trail**, which is **server-paged** and **searchable/filterable** by free text, operation, target, outcome and path — so a run with tens of thousands of moves stays responsive instead of loading its whole history at once. The trail shows When, **Source path**, Operation, Target, Outcome, **Destination path** and Detail. All columns are **sortable** (ordered server-side across the whole run, not just the current page); the When, Operation, Target and Outcome columns are **content-sized** (fitted to the widest value they actually hold, with a small buffer). The **Source path** and **Destination path** filters each offer a **typeahead** of the run's recorded values, and every path has a **copy** control. An **Export CSV** button downloads the trail honouring the **current filters** (the whole filtered set, not just the visible page); the file opens with a short summary of the applied filters so it is a self-documenting audit artifact. Both surfaces **refresh automatically while the run is live** (the newest operations land on the first page), so the operator sees activity as it happens without reloading.
- **Normalization Review view** — reached from the Job Details view when a run pauses at the Step 8 name-conflict gate (`AwaitingInput`). A folder-structure view adapted from the Step 6 folder review, it renders the **projected archive outcome** of the normalization plan with each name conflict badged in place. Each conflict shows its issue, a pre-selected safe (non-destructive) suggested resolution, and the applicable options (rename folder, rename document, merge folders, keep-one/delete-other), with an impact summary and a confirm before submitting. Submitting re-runs the dry run and loops until no conflicts remain; resolutions auto-save as a draft.

### Auditability — before, during, and after a run

A run is designed to be fully accountable end to end (`decisions/log.md` [2026-08-05]):

- **Before** — the operator captures a **pre-run Document Register** snapshot (the source library as it stands, ≤ cutoff), retained with the run and exportable to CSV or Excel.
- **During** — every mutating operation the run performs against MAGIQ, and every operator decision that shapes it, is written to an **append-only operation audit trail** (`CleanupRunOperation`): archive-library and folder creates, document moves (recorded **per document** — one entry per move, with its path, destination and outcome), empty-folder deletes, library delete + recycle-bin purge, Name Normalization actions (source renames, folder merges, and duplicate-document deletions) with the operator's conflict resolutions, each reactive folder-rule relax and restore, operator overrides of the acronym pre-select, the purge authorisation (pre-granted at Step 7 or typed at Step 12), and — when a terminal run is **rolled back** — every document **move-back** (recorded **per document**, the reverse of the archival move) and the archive-library **teardown** (folder deletes + recycle-bin purges, tagged as rollback). This is separate from, and complements, the phase log.
- **After** — a **run outcome ledger** (each document's final disposition, each folder's final status, and the rename log) gives the post-run picture, exportable to CSV or Excel. Because the source has been moved/purged by then, "after" is built from the run's own record, not a re-query of the source library.

Together these answer *what the repository looked like before, what the tool did, and what it looked like after*. Both the on-demand register and the pinned snapshots export to **CSV or Excel** (`?format=csv|xlsx`); the pre-run snapshot is captured automatically at confirmation and the post-run outcome ledger when the run completes, both retained with the run in CSV. (Implemented, including the SPA: the Job Details view shows the operation audit trail and a before/after snapshot download panel with an Excel/CSV toggle. Name Normalization now writes `Rename` rows to the operation audit trail. Remaining polish — reviewing-operator attribution for overrides — is tracked in `deferred-work-plan.md`.)

### Navigation rules

- **Review:** the operator reviews and selects folders at Step 6, then confirms at Step 7 (which may return to Step 6 to revise selections). After confirming, the operator lands on the jobs dashboard / details view to monitor the background phases.
- **Name-change review:** whenever the Step 8 dry run would change any name (a rename and/or a conflict), the run pauses and the operator opens the Normalization Review view. Any conflicts are resolved first (submitting re-analyses and re-prompts until the plan is clean); the operator then reviews the **full list of folder and document name changes** — downloadable as a before → after list in CSV or Excel — and **confirms** to proceed. Only a plan that changes nothing skips the gate and executes automatically. A run paused here has mutated nothing and may still be cancelled or deleted.
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
| **Rollback** | For a terminal run: move every archived document back to its original folder and, if this run created the archive library, delete and purge it — returning MAGIQ Documents to its pre-run state. Succeeds only when every document is safely back. A rollback makes the run deletable **unless** Name Normalization had **executed a change** (Step 8b rename/merge/delete): those are not reversed, so such a run stays an audit and is archived, not deleted (Rule 7). A run that only reached the Step 8 dry run / conflict gate mutated nothing and is unaffected |
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

#### Step 8 — Normalize source names (work around the whitespace / invisible-character bug)

_See [Whitespace normalization](#whitespace-normalization-and-the-double-space-bug) for the underlying bug and [Whitespace normalization scope](#whitespace-normalization-scope) for the character lists. Implemented as `RunPhase.Normalization` / `RunPhaseExecutor.ExecuteNormalizationAsync`, planned by `RenamePlanner` and recorded in `dbo.CleanupRunRename`._

Before any document is moved, this phase renames — **in the source repository** — every candidate item whose name (or whose containing folder path, at any level) holds a normalizable character, applying the two rules from [Whitespace normalization scope](#whitespace-normalization-scope): **whitespace → a single regular space (collapsed and trimmed); invisible format characters → stripped**.

Normalizing names can, however, make two previously-distinct items collapse onto the **same** name — e.g. `Report` and `Report ` (trailing space) both become `Report`, or `A B` (regular space) and `A B` (non-breaking space) both become `A B`. The phase therefore runs in three parts: a **dry run** that plans the renames and finds any conflicts without changing anything, an **operator review gate** whenever the plan changes any name (to resolve conflicts and to review + confirm the changes), and the **execution** that actually mutates the repository. These are narrative sub-parts of Step 8 — the phase/step number does not change.

##### Step 8a — Dry run (plan the renames, no mutation)

Working from the run's candidate documents and their resolved paths, the phase computes the normalized name for every affected item — folder path levels (top-down, ancestors before descendants) and documents — and **projects the resulting structure without writing anything to the live repository**. It then detects **name conflicts**: two or more items that would share the same name under the same parent after normalization. The projected plan and any conflicts are persisted against the run.

Conflicts are evaluated against the **whole projected structure**, not just the candidate set — a normalized name that would collide with an existing **non-candidate** sibling is a conflict too, since renaming into it would otherwise silently merge or fail.

##### Name conflicts and how the operator resolves them

Whenever the plan changes any name, the run **pauses in `AwaitingInput`** at the **Normalization Review** view — a folder-structure view adapted from the Step 6 folder review that shows the **projected archive outcome**. If there are conflicts, each is badged in place for the operator to resolve; if there are none, the view goes straight to the change list (below). Only a plan that changes nothing skips the gate. For every conflict the view states the **issue**, offers a **suggested resolution** (a safe, non-destructive default, pre-selected), and lets the operator choose among the applicable options: For every conflict the view states the **issue**, offers a **suggested resolution** (a safe, non-destructive default, pre-selected), and lets the operator choose among the applicable options:

- **Rename folder** — give one of the colliding folders a different, unique name (the suggested default appends a disambiguator, e.g. `… (2)`; the operator may edit it).
- **Rename document** — the same, for colliding documents.
- **Merge the two folders** — fold one folder's contents into the other rather than keeping both. If the merge then produces **document** conflicts inside the combined folder, each is resolved in turn: **rename** one, or **keep one and delete the other**.
- **Keep one / delete the other** — for a duplicate document, retain one and delete the rest (`DeleteDocument`, to the recycle bin).

To inform that last choice, the dry run reads each colliding document's **version checksums** (`GetDocument` with `withVersions=true`) and compares them: when every version's `CheckSum` (and size) matches, the documents are **true duplicates** and the view says so, making keep-one/delete-other a safe collapse; when they differ, the documents hold **genuinely different content**, so the view flags the delete as lossy and keeps a disambiguating rename as the safe default.

Merge and keep-one/delete-other are **destructive** (they remove a source item before archival): they are never the pre-selected default, require a deliberate operator choice with a confirmation, and — like every mutating action — are written to the operation audit trail. Resolutions are auto-saved as a draft so an interrupted session survives a refresh (as at Step 6).

**Protection always wins (Rule 2).** Folder protection overrides every conflict resolution: **no resolution may delete a protected folder or a post-cutoff document.** So each colliding item carries its protection status into the gate, and the options are constrained accordingly — a **merge** is offered only with the protected item as the **survivor** (never the deleted side); **keep-one/delete-other** can never target a protected/post-cutoff document; and when one colliding side is protected the pre-selected default **renames the non-protected side**, leaving the protected item's name unchanged. If **every** colliding item is protected, **rename is the only option offered**. Because a rename deletes nothing, a protection-safe resolution always exists; the run can never be forced into a choice that removes protected content.

**Collisions with a folder outside the cull.** A candidate folder can normalize onto a **non-candidate** sibling — a folder the cull never selected (no candidate documents beneath it). Such a folder is out of scope and is treated like protected content for deletion: it is **never deleted or merged away**. The pre-selected default **renames the candidate side**, leaving the out-of-scope folder untouched. **Merge stays available** for the genuine "these two are really the same folder" case (e.g. a pasted near-duplicate of a live folder), but only with the **non-candidate folder as the survivor** and behind an explicit *"this folder is outside the current cull — its contents will be combined with archived candidates"* warning + confirmation. The out-of-scope side is badged in the Normalization Review view so the operator sees exactly what a merge would combine.

When the operator submits their resolutions, the phase **re-runs the dry run** with those decisions applied — because a chosen rename or merge can itself introduce a new collision — and **repeats until zero conflicts remain**. (This is the "re-run identification until all issues are resolved" loop: it re-analyses the normalization plan, not the Phase 1 candidate identification.)

##### Reviewing and confirming the change list

Once the plan is conflict-free, the Normalization Review view shows the **complete list of folder and document name changes** that Step 8b will apply — each item's current name and its new name, with the offending whitespace/invisible characters made visible and a plain-language reason — plus any resolved folder merges and duplicate-deletes. The operator can **download this before → after list** as **CSV or Excel** to review or keep as a record, then **confirms** to proceed. **Execution does not start until the operator confirms** — the run stays paused (and deletable) at the gate until then. Only a plan that changes nothing bypasses this review and continues automatically.

##### Step 8b — Execute (renames, merges, deletes — mutating)

Once the operator confirms the reviewed plan, the phase applies it against the live repository: **renames** (whitespace/invisible normalization plus any operator disambiguations) via `UpdateFolderProperties`/`UpdateDocumentProperties`; **folder merges** (move children into the surviving folder via `Move`, then delete the emptied folder via `DeleteFolder`); and **duplicate-document deletions** (via the document-delete op). Folder levels are processed top-down so descendant paths stay resolvable. As each rename or merge is applied, the run's **candidate documents are repathed in step** — their recorded source paths are updated to the new folder/document names — so the later archival move (Step 10) addresses each document by its current live path rather than its pre-normalization one (without this a normalized item's move fails *"source folder not found"*). A document **deleted** as a duplicate (keep-one/delete-other) is likewise **excluded from the archival move** — it no longer exists in the source, so it is marked removed and Step 10 skips it (it is not archived and not counted as a move failure). **This is the first part of the run that changes the customer's repository — the point at which the run becomes an audit** (Rule 7, [Run Lifecycle](#run-lifecycle)); the dry run and conflict resolution above change nothing and leave the run deletable.

**Reviewing the rename list and confirming.** Step 8b **never advances on its own**. After it applies the plan, the run **always pauses** in the Normalization phase and the details view shows the **full list of folder and document renames**, each row updating **inline** as it is applied — *Renaming…* → *Renamed*, or the **failure reason** if it could not be applied. This is true whether every rename succeeded or some failed. The operator fixes the cause of any failure in MAGIQ and **retries** it — one at a time or all together (each retry runs inline and stays listed as a record; a folder rename repaths its descendants and the affected candidate documents just as the forward pass did), and every attempt is written to the operation audit trail. **The run cannot advance while any item is still failed or pending.** Only once every rename shows *Renamed* does the **Confirm & continue to archival** button enable; the operator clicks it to proceed, and nothing is archived until they do. (A run paused here has already executed at least one rename, so it is an audit — see Rule 7.)

**Every mutating action is recorded** — for a rename, the item type, its original path/name and the new name; for a merge or delete, the items involved and the operator decision — with the operator/process ticket and a timestamp, persisted against the run and written to the operation audit trail. Actions are batched with per-item status and resume-from-failure, and report progress like Step 10. The phase is idempotent on resume: an item already at its resolved name (or already merged/deleted) is skipped. An action that cannot be completed leaves the item flagged and, as with an unmovable document, blocks the archival move for that item; the run surfaces the failures. Only once execution is complete does the pipeline chain to archival.

The exact path form the rename/merge/delete ops accept for a still-affected source item, and the ordering behaviour, are confirmed at integration against training (same `xsd:any`/behaviour class as ADR-011 / Story 34525).

### Phase 4 — Archival

#### Step 9 — Select or create the archive library

The destination for the candidate documents is either a **new library** (enter a name; a subfolder may be created to organise the archive) or an **existing library** chosen from the live MAGIQ Documents list (also with an optional subfolder). The UI is a modal with a name filter over the library list and on-demand, one-level subfolder browsing. New-library name prefill: `Archive {SourceLibraryName} - {ShortFriendlyDate}` (e.g. `Archive NATA - Dec 2024`), editable before confirming. A library the run **creates** is recorded so a rollback can tear it down; an operator-chosen **existing** library is never torn down wholesale.

#### Step 10 — Move documents to the archive library

The background phase creates the archive library if needed, ensures the destination folder structure exists, and moves each candidate document into the archive, recreating its source-folder hierarchy beneath the destination. Library creation is **idempotent**: before `CreateDomain` the phase lists existing libraries (`GetDomains`) and, if one with the run's name already exists (as happens when a prior attempt created the library but crashed before persisting its id, so a resume re-enters create mode), it **adopts that library and skips creation** rather than failing on *"A library with this name already exists."* An adopted library is **not** flagged as created by this run, so a later rollback/teardown never deletes it — an orphaned empty library from a prior crash is left for the operator to remove. Because Step 8 has already normalized the source names, the source and destination paths are whitespace-clean and the `Move` addresses them cleanly. Moves are batched with per-document status, a single retry pass for failures, and resume-from-failure; progress shows on the dashboard (polling) and in the details view (live via SignalR), with failed documents surfaced as they occur.

If a move fails because the source folder disallows document deletes, the reactive delete-rule handling relaxes that folder's rule, retries the move, and restores the rule (see [Folder rules](#folder-rules-and-the-move-is-copy--delete-constraint)). A document that still cannot be moved after the retry is left `Failed`; there is no rollback of already-moved documents within the run — the phase resumes from the point of failure. If any documents remain unmovable, the run fails with them listed, and the cleanup phase does not proceed.

**Working through move failures (`decisions/log.md` [2026-08-10]).** When a run fails at Step 10 with unmovable documents, the details view shows a **Document move failures** panel listing each failed document with its path, error and attempt count. The operator can fix the underlying cause in MAGIQ and then **retry** the failures — one at a time or all together. Each retry runs **inline**: the row shows *Retrying…* and then, on success, *Moved* in place, and the row **stays in the list** as a record; the main run-progress panel is not disturbed. A retry re-attempts only the chosen documents (reusing the same move machinery, including the reactive delete-rule handling); before attempting, it reconciles each candidate's stored path against the Step 8 rename record, so a document that failed because its source folder was renamed is repaired and then moves cleanly. Any that still fail remain listed with their new error for another attempt (Retry all works through the failed rows one by one, showing progress on each). When a retry clears the **last** failure so every document is archived, the run does **not** auto-continue: it **pauses after archival** (`AwaitingInput`) and the panel offers **Continue to cleanup**, so the operator explicitly proceeds to the folder deletes and the (irreversible) purge. Nothing is deleted until the operator continues.

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

2. **Folder protection** — A folder holding at least one document modified after the cutoff must not be deleted; protection extends to the **full ancestor hierarchy**. Protection overrides the acronym pre-select — a protected folder is never deletable or selectable — **and overrides Name Normalization conflict resolution** (Rule 8): a protected folder is never deleted or merged away, and a post-cutoff document is never deleted as a duplicate.

3. **Empty folders** — Folders left empty after the move are deleted (Step 11).

4. **Delete constraint** — Confirmation (Step 7) cannot proceed while any selected folder is protected. The system validates all selected folders and reports the blockers inline; they must be deselected before proceeding.

5. **Confirm before purge** — The archive library is not deleted/purged (Step 12) until purge is authorised — either pre-granted at Step 7 or granted manually via the typed "permanently delete" confirmation. The confirming user and timestamp are recorded in both cases.

6. **Delete-rule handling** — A folder rule that disallows deletes (which would otherwise fail a Step 10 move or a Step 11 folder delete, since a move is a copy + delete) is worked around reactively: the blocking rule is read live, temporarily relaxed on the one folder, the operation retried, and the original rule restored. The restriction is surfaced at review for visibility but is not a blocker.

7. **Name normalization & audit lock** — Because the MAGIQ web service cannot `Move`/`CreateFolder` an item whose name (or folder-path level) holds a whitespace variant (a doubled space, a non-breaking space `U+00A0`, or any other Unicode whitespace) or an invisible format character (zero-width space, BOM, soft hyphen, etc.) — while the desktop UI allows such names, and they are easily pasted in from other documents — a **Name Normalization** phase (Step 8) renames every affected **source** item in place before the archival move (whitespace → a single regular space; invisibles → stripped; see [Whitespace normalization scope](#whitespace-normalization-scope)), so the move can succeed. Every rename, merge and delete is recorded (item type, original path/name, new name, operator/ticket, timestamp). These changes mutate NATA's live repository and are **not** reversed by a rollback, so **once the phase has executed its first change (Step 8b) the run becomes an audit** and can no longer be permanently deleted — only archived for the record. A run still in the dry run or conflict-resolution gate has changed nothing and stays deletable.

8. **Name-conflict resolution gate** — When normalization would rename two or more items to the same name under the same parent (a folder or document conflict, evaluated against the whole projected structure including non-candidate siblings), the run pauses (`AwaitingInput`) and the operator must resolve every conflict before any change is executed. Options are rename folder, rename document, merge folders, or keep-one/delete-other; the pre-selected default is always a non-destructive rename, and the destructive options (merge, delete-duplicate) require a deliberate choice with confirmation and are audited. **Protection (Rule 2) overrides all of this:** no resolution may delete a protected folder or a post-cutoff document — a merge keeps the protected item as the survivor, keep-one/delete-other never targets protected content, the default renames the non-protected side, and when every colliding item is protected only rename is offered. A colliding folder **outside the cull** (non-candidate) is likewise never deleted or merged away — the default renames the candidate side, and merge is offered only with the non-candidate as the survivor behind an out-of-scope warning. Submitting resolutions re-runs the dry run and repeats until no conflicts remain; only then does Step 8b execute.

---

## History

This document reflects the system as built, including the **Name Normalization** phase (Step 8) added to work around the SOAP double-space bug and now implemented in the working tree (`decisions/log.md` [2026-08-05]). **2026-08-07:** the phase's scope was widened from ASCII whitespace to the **full Unicode `White_Space` set** (all 25 code points — non-breaking, narrow, figure, ideographic and em/en spaces, etc.; equivalently .NET `char.IsWhiteSpace`), each collapsed to a regular space, **plus stripping of invisible format characters** (`U+200B`, `U+200C`, `U+200D`, `U+2060`, `U+FEFF`, `U+00AD`) — because such characters are readily pasted into names from Word, email or the web (see [Whitespace normalization scope](#whitespace-normalization-scope)). **2026-08-07:** Name Normalization gained a **name-conflict dry run + operator resolution gate** — the phase now plans renames without mutating, pauses (`AwaitingInput`) in the new Normalization Review view when renames would collide, lets the operator resolve each conflict (rename / merge / keep-one-delete-other), re-analyses until clean, then executes; the **audit lock (Rule 7) moves to the first executed change** rather than phase entry, and a new **Rule 8** covers the conflict gate (`decisions/log.md` [2026-08-07]). The full history of decisions and resolved questions — protection scope, archive-library selection, purge confirmation, ticket-expiry recovery, the move to database-backed configuration, the overridable acronym pre-select, the folder delete-rule handling, and the name-normalization phase — is recorded in `decisions/log.md` and `references/adrs/`. **2026-08-08:** the first-run setup **admin-allowlist step was reworked** — a MAGIQ update stopped `UserExists` from being callable anonymously, so the wizard no longer validates typed usernames anonymously. Instead the operator does a **bootstrap sign-in** during setup (auto-added to the allowlist, pinned), and the authenticated **`GetAllUsers`** op powers a name/username typeahead (disabled accounts hidden). The same typeahead replaces the plain text allowlist editor in **System Settings**. The anonymous `setup/magiq/validate-user` endpoint was removed; new endpoints `setup/magiq/login`, `setup/magiq/users` and `admin/magiq/users` back the flow (`decisions/log.md` [2026-08-08]). **2026-08-09:** the Step 9/10 archive-library create was made **idempotent** — before `CreateDomain` the phase lists existing libraries (`GetDomains`) and adopts a same-named one if present (skipping creation) instead of failing on *"A library with this name already exists"*; the adopted library is not marked as created by the run, so teardown never deletes it (`decisions/log.md` [2026-08-09]). **2026-08-09:** the reactive delete-rule handling changed from a per-item relax/revert to a **relax-once-per-folder** shape — the phase groups the items sharing a rule-bearing folder, relaxes that folder's rule a single time, retries the blocked items, and restores once; the old per-item flip churned the same folder's rule and left later items in a folder failing during a live cull (`decisions/log.md` [2026-08-09]). **2026-08-09:** the **operation audit trail** in the Job Details view was reworked for scale — the full trail is now **server-paged** (newest first) and **searchable/filterable** by free text, operation, target, outcome and path, above a compact **live activity** feed, and **document moves are recorded per document** (one entry per move, bulk-inserted per batch) rather than one batch-summary entry, so individual moves are visible and searchable (`decisions/log.md` [2026-08-09], reversing the 2026-08-05 batch-summary call). **2026-08-10:** the operation audit trail gained a **CSV export** — an **Export CSV** button in the Job Details view downloads the trail honouring the operator's current filters (the whole filtered set, not just the visible page), streamed from a new `GET /runs/{runId}/operations/export`; the file opens with a `#`-prefixed summary of the applied filters so it is a self-documenting audit artifact (`decisions/log.md` [2026-08-10]). **2026-08-10:** the Step 8 gate was **widened from conflicts-only to any name change** — the run now pauses at the Normalization Review view whenever the plan changes any name, the operator reviews the **full folder/document change list** (surfaced on `GET …/normalization/plan`) and can **download it as a before → after list (CSV/Excel)** via `GET …/normalization/changes/export`, then **confirms** (`POST …/normalization/confirm`) before Step 8b executes; only a zero-change plan still auto-continues, and the audit lock still trips on the first executed 8b change (`decisions/log.md` [2026-08-10]; plan `normalization-change-review-plan.md`). **2026-08-10:** Step 10 gained an operator **move-failure retry** — a Document move failures panel lists each unmovable document and the operator retries them individually, selected, or all (`POST …/archival/move-failures/retry`, list on `GET …/archival/move-failures`); when a retry clears the last failure the run **pauses after archival** (`AwaitingInput`) and the operator explicitly proceeds via `POST …/archival/continue` rather than auto-chaining the irreversible cleanup/purge (`decisions/log.md` [2026-08-10]; plan `move-failure-retry-plan.md`). **2026-08-11:** three normalization/rollback refinements landed together. **(1) Normalization execution gate** — Step 8b now **always pauses** after applying the plan and **never auto-advances**: the details view shows the **full rename list** updating inline (each item *Renamed* or its failure reason), the operator retries failures individually or all (repathing descendants on a folder rename, auditing each attempt), and only once every item is renamed does **Confirm & continue to archival** enable (`GET …/normalization/failures` = full list, `POST …/normalization/failures/retry`, `POST …/normalization/continue`). This also fixed a bug where a failed/paused normalization still ran archival — the phase-runnable guard (`LoadRunnableAsync`) only excluded Cancelled/Completed/Abandoned, so a `Failed`/`AwaitingInput` run's Hangfire-chained archival proceeded; it now no-ops on any non-`Running` state. `RunSummary.EnteredNormalization` distinguishes this post-8b state from the pre-mutation review gate. **(2) Persistent run-phase stepper** — the Job Details view now shows an always-visible Identify → Review → Normalize → Archive → Cleanup stepper driven by the run's phase, with Normalization shown complete/skipped when it needs no changes. **(3) Rollback audit trail** — Tier 2 rollback now writes per-item operation-audit rows: a `MoveBack` per document returned from the archive, and the archive-library teardown (folder deletes + recycle-bin purges) tagged as rollback, so an undo is as traceable as the original archival. Ordered delivery is in `delivery-plan.md`; current status in `tasks.md`.
