# NATA — Document Lifecycle Cleaner
### Specification v0.4

_Last updated: 2026-07-21_

> **Status:** Baseline — architecture and infrastructure settled (see [Infrastructure & Technology](#infrastructure--technology) and `decisions/log.md`). All blocking questions resolved. Ready for delivery planning and implementation.

---

## Goal

Delete documents and folders with a modification date less than or equal to a specified calendar date, and remove empty folders pertaining to a particular facility based on folder naming conventions.

---

## Context

NATA requires a yearly clean culling and deletion of all documents whose modification date falls on or before a specified calendar year-end date, as well as the removal of empty folders associated with a particular facility identified by acronym. This process is intended to be repeatable and automated on an annual basis.

---

## Repository

Source code is hosted in **Azure DevOps Git**, in the **MAGIQSoftware** organisation, in a repository named **DocumentLifecycleCleaner**.

---

## Infrastructure & Technology

The application is a long-running, multi-phase pipeline with an interactive operator UI. The technology choices below follow from that shape and from the on-premises hosting constraint. Full rationale is recorded in `decisions/log.md` (2026-07-13).

**Frontend** — React single-page application, chosen for a rich review-and-confirmation experience (Steps 6–7). Built and published into the API's `wwwroot` and served as static files by the same ASP.NET Core app (`UseDefaultFiles` + `UseStaticFiles` + `MapFallbackToFile("index.html")`). No separate web server and no CORS surface. FastEndpoints is given a route prefix (e.g. `api`) so the SPA deep-link fallback does not intercept API routes.

**Backend** — C# / .NET with **FastEndpoints**, using the REPR (Request–Endpoint–Response) / vertical-slice pattern. CQRS is kept lightweight (commands and handlers); full event sourcing is deliberately **not** used — the domain is a workflow, not a rich aggregate.

**Background pipeline** — **Hangfire** runs the archival, move, delete, and purge phases. It provides persistence, automatic retries, phase chaining via continuations, and an operator dashboard. This satisfies the spec's resumability requirement (Step 9 — resume from the point of failure, no rollback) and the background-purge requirement (Step 12). The Hangfire server runs in-process within the API.

**Run state** — Each execution is a persisted `CleanupRun` state machine with a status per phase. This makes the process resumable (restart reads the last completed phase), enforces a single active run at a time, and records per-document move failures for the identify-skip-resume behaviour in Step 9.

**Progress reporting** — **SignalR** pushes live progress for long phases (a document move may span thousands of records) to the operator UI, paired with Hangfire's progress tracking. It degrades to polling automatically. Server-Sent Events is an acceptable one-way alternative since progress is server→client only.

**Data** — SQL Server. The application uses a **single dedicated database** that holds both its own state (the `CleanupRun` records) and the Hangfire tables, kept separate from the MAGIQ Documents database. The MAGIQ Documents database is accessed directly for the pre-configured, system-level queries (Steps 1, 2, 5 — candidate retrieval and folder-path resolution), which remain the source of truth for those steps.

**Hosting** — On-premises / customer-hosted. **IIS is the default target**; **Docker** (containerised) is also supported so the client can switch without code changes. The application stays hosting-agnostic — Kestrel is the web server in both cases (IIS acts as a reverse proxy); all environment-specific settings (connection strings, MAGIQ Documents API endpoints, ports) come from configuration/environment variables, with no host-specific code paths. A `Dockerfile` builds the React SPA and publishes it into the API image's `wwwroot`, producing the same single self-contained artifact used under IIS. Single-server deployment either way; no clustering or distributed job processing required for a once-a-year, operator-triggered run.

**Integration** — MAGIQ Documents is integrated two ways: a **SOAP web service API** (for library/folder/document operations) and **direct SQL Database** access via **Dapper** (for the pre-configured candidate-retrieval and folder-path queries in Steps 1, 2, 5). Dapper suits the system-level, configurable raw-SQL approach — it maps query results without imposing a schema or ORM model. Neither path has Windows-specific dependencies, so a **Linux container** remains viable if Docker is chosen.

**Authentication & authorisation** — The application piggybacks off the MAGIQ Documents authentication system rather than maintaining its own credential store. The SOAP endpoint is `srv.asmx`; its **`AuthenticateUser`** action accepts a username and password and, on success, returns an **`AuthenticationTicket`** that must accompany all subsequent web-service calls.

- **Login flow:** the operator signs in with their MAGIQ Documents credentials → the app calls `AuthenticateUser` → the returned ticket establishes the app session.
- **Ticket lifecycle:** the ticket has a **sliding 20-minute timeout** — each call resets the window. `AuthenticateUser` returns a **new, independent ticket on every call**.
- **Two tickets per login:** at login the app calls `AuthenticateUser` **twice**, obtaining two independent tickets — one for the **UI session** (so the operator can log out without affecting a running job) and one dedicated to the **long-running process**. This decouples the UI session lifecycle from the background pipeline.
- **Keeping the process ticket alive:** the process ticket's sliding window is kept open by a **lightweight periodic keep-alive call** (heartbeat) in addition to the incidental SOAP calls made during work — this guarantees the window never lapses during lulls between phases, not just during high-activity phases like the Step 9 move.
- **Process ticket persisted across recycles:** the process ticket is **stored in the dedicated app database** (associated with the `CleanupRun`). Because it is persisted rather than held only in memory, it **survives an IIS recycle / app restart** — on startup the app reloads the stored ticket and resumes the keep-alive. If the stored ticket has expired (e.g. due to a prolonged outage), the application automatically obtains a new ticket on behalf of the authenticated user — no manual re-authentication is required.
- **Authorisation:** access is restricted to an **admin-only allowlist of usernames**, stored in `appSettings.json` for now (interim — a database-backed or configurable store is a likely future iteration). A successfully authenticated user whose username is not on the allowlist is denied.

The **UI ticket** is not persisted and does not need to survive a recycle — if the app restarts, the operator simply re-authenticates for the UI. Only the process ticket is persisted, because only the background run must survive uninterrupted.

---

## Parameters

**Specified Date** — The cutoff is a calendar year-end date (e.g. 31 December 2024). Documents with a modification date _less than or equal to (≤)_ this date are candidates for deletion.

**Who sets the date:** A records manager or system administrator (e.g. Madhuri) sets the specified date within MAGIQ Documents.

**Who runs the process:** A MAGIQ Documents system administrator or power user.

---

## Process Phases

| Phase | Steps | Type |
|---|---|---|
| **Phase 1: Identification** | Steps 1–3 | Automated |
| **Phase 2: Review & Selection** | Steps 4–6 | Interactive (React UI + .NET API) |
| **Phase 3: Archival** | Steps 7–9 | Operational |
| **Phase 4: Cleanup** | Steps 10–12 | Automated / System |

---

## The Process

### Phase 1 — Identification

#### Step 1 — Retrieve candidate documents

Execute the pre-configured SQL query to retrieve all documents from the database where the modification date is less than or equal to the specified calendar date. The query is defined and maintained at the system configuration level so that schema changes can be accommodated without requiring code changes.

#### Step 2 — Apply Document Register query

Use the existing pre-configured SQL query for the Document Register report as the base. This query is maintained at the system configuration level and can be updated independently when the schema changes.

**Resolved:** No additional fields are required beyond what the standard Document Register SQL query provides. The output is exactly what the query returns.

#### Step 3 — Export results to Excel and provide download

Copy the query results to an Excel spreadsheet and provide it as a download. NATA decides where to save the file — it is not uploaded into MAGIQ Documents by the system.

**Resolved:**
- No retention period is required for the spreadsheet.
- The spreadsheet is for viewing purposes only — it is not an audit or compliance artefact.
- No approval is required before the process can proceed.
- No fields beyond those in the SQL query are required.

---

### Phase 2 — Review & Selection

#### Step 4 — Produce a list of candidate folders

Using the documents identified in Step 1, generate a list of all containing folders. This list is used in Step 6 to determine which folders are candidates for deletion or retention.

**Resolved (protection scope):** A single document with a modification date after the specified date protects its immediate parent folder **and the full ancestor folder hierarchy** — every folder up the tree is protected.

**Resolved (nested folder behaviour):** If a parent folder becomes empty after its child folders and documents are deleted, it may also be deleted — provided all deletion criteria are met. If a parent is not empty, it remains.

#### Step 5 — Generate folder paths via SQL

Using the folder IDs produced in Step 4, execute a SQL query that returns the full resolved folder paths. These paths are surfaced in the review UI in Step 6.

#### Step 6 — Review and select folders to delete or keep (React UI + .NET API)

A React-based UI presents NATA with the full list of candidate folders and their resolved paths. NATA selects which folders to delete or retain. Folders matching the deletable naming conventions (see [Deletable Folder Naming Conventions](#deletable-folder-naming-conventions)) are pre-selected for deletion and cannot be overridden by the user.

**Resolved (display columns):** Minimum column set at launch: **folder path**, **document count**, **folder count**, **size**. UI designed to support additional columns in future iterations without a redesign.

**Resolved (document preservation rules):** No document types, statuses, or categories require unconditional preservation. All documents are subject to the standard date cutoff rule.

---

### Phase 3 — Archival

#### Step 7 — Confirm and execute folder deletes (React UI + .NET API)

The React UI presents a confirmation screen listing all folders selected for deletion. NATA must explicitly approve before the .NET backend API executes any deletions.

The system validates all selected folders against the delete constraint (Rule 4) before any delete is executed. If any folder is in a protected state, the process halts and reports which folders are blocking. Deletion cannot proceed until all blocking folders are resolved or deselected.

#### Step 8 — Select or create an archive library in MAGIQ Documents

The operator selects the destination archive library for the candidate documents. The UI prompts the operator to either:

- **Create a new library** — enter a name; optionally create a subfolder within the new library to organise the archived documents, or
- **Choose an existing library** — select from available MAGIQ Documents libraries; optionally create a new subfolder within the chosen library.

**Resolved:**
- **Permissions:** Full control for the system administrator or power user.
- **Audit logging:** Not required.

#### Step 9 — Move documents to the archive library

Move all candidate documents identified in Step 1 into the library created in Step 8.

**Resolved (move failure handling):** If a document cannot be moved, identify which documents failed and why. Continue moving the remaining documents, then return to the failed documents once the rest are complete. There is no rollback mechanism — the process resumes from the point of failure.

---

### Phase 4 — Cleanup

#### Step 10 — Delete empty folders

Delete all folders that are empty following the document move in Step 9. This step must not execute until all document moves in Step 9 are confirmed complete.

#### Step 11 — Robocopy archive _(Out of Scope)_

~~NATA uses Robocopy to copy the entire archive library to a designated file share for long-term backup.~~

**Resolved:** This step is performed manually by NATA and is **out of scope** for this system. The operator must confirm completion before Step 12 can proceed — see Step 12.

#### Step 12 — Delete and purge the archive library

Before the delete executes, the operator must confirm in the UI that the Robocopy archive (Step 11) is complete. The UI presents a confirmation checkbox; the system records the confirming username and timestamp. No other verification is performed.

Only after this confirmation is recorded does the system delete the archive library. The purge — permanent removal from the system — is implemented as a system background process that executes automatically following the delete.

**Resolved:**
- **Robocopy confirmation:** UI checkbox only; confirming user and timestamp are logged. No automated verification.
- No holding period is required between the delete action and the background purge.
- Once the relevant documents and folders have been deleted, the archive library can be deleted and purged immediately.

---

## Deletable Folder Naming Conventions

Folders matching the following acronyms are always eligible for deletion. In the review UI (Step 6), these folders are pre-selected and NATA cannot override the selection.

```
ADV · ARE · ASS · CEA · CGA · CRE · DCR · DEL · DFS · DRV · DTV · FAS
FES · OLC · OLN · REI · RES · SRE · SRV · STF · STI · VAR
```

**Resolved:**
- **List status:** This is the current complete list. NATA may add or remove acronyms — the list must be configurable.
- **Matching rule:** The acronym must exist _anywhere_ in the folder name (contains match, not prefix or exact match).
- **Case sensitivity:** Matching is case-sensitive.

---

## Rules

1. **Date cutoff** — Documents with a modification date less than or equal to the specified calendar date are candidates for deletion.

2. **Folder protection** — Folders containing at least one document with a modification date after the specified date must not be deleted. Protection extends to the **full ancestor folder hierarchy** — every ancestor folder above the containing folder is also protected.

3. **Empty folders** — Empty folders must be deleted.

4. **Delete constraint** — Deletion cannot proceed while any selected folder is in a protected state. The system must validate all selected folders before executing any deletions. If the constraint is violated, the process halts and reports which folders are blocking. Deletion cannot proceed until all blocking folders are resolved or deselected.

5. **Archive first** — The archive library must not be deleted (Step 12) until the operator has confirmed via UI checkbox that the Robocopy archive (Step 11) is complete. The confirming user and timestamp are recorded.

---


## Open Questions

| # | Step / Section | Question | Status |
|---|---|---|---|
| OQ-1 | Step 6 UI | Display columns — minimum set at launch, expandable later | ✅ Resolved: folder path, document count, folder count, size |
| OQ-2 | Step 6 | Document types/categories requiring unconditional preservation | ✅ Resolved: none |
| OQ-3 | Rule 2 / Step 4 | Folder protection scope | ✅ Resolved: full ancestor hierarchy |
| OQ-4 | Step 8 | Archive library — operator selects or creates, with optional subfolder | ✅ Resolved |
| OQ-5 | Step 12 | Robocopy confirmation mechanism | ✅ Resolved: UI checkbox; user + timestamp logged |
| OQ-6 | Auth | Process ticket expiry recovery | ✅ Resolved: app auto-obtains new ticket on behalf of user |

---

## Resolved Questions Log

| # | Question | Resolution |
|---|---|---|
| Q1 | Who sets the specified date? | Records manager / system admin (e.g. Madhuri) |
| Q2 | Who runs the process? | MAGIQ Documents system admin or power user |
| Q3 | Additional fields beyond Document Register query? | None — SQL query output only |
| Q4 | Excel spreadsheet retention period and owner? | No retention period; viewing only |
| Q5 | Audit/compliance requirement for spreadsheet? | No |
| Q6 | Where is the spreadsheet saved? | Download provided; NATA decides where to save |
| Q7 | Folder protection scope (Step 4)? | Immediate parent AND full ancestor hierarchy |
| Q8 | Nested folder handling? | Empty parents can be deleted once criteria are met |
| Q9 | Archive library name? | `{LibraryName} - Archive` (derived from source library name; reuse if already exists) |
| Q10 | Library permissions? | Full control for system admin / power user |
| Q11 | Library creation audit? | Not required |
| Q12 | Move failure handling? | Identify and skip; resume after rest complete |
| Q13 | Robocopy — manual or automated? Verification? | Out of scope; NATA performs manually |
| Q14 | Holding period before purge? | None — purge immediately after delete |
| Q15 | Naming conventions list — complete? Configurable? | Current list is complete; NATA can add/remove |
| Q16 | Case-sensitive matching? Prefix or contains? | Case-sensitive; acronym must exist anywhere in folder name |
| Q17 | Rule 2 protection scope? | Full ancestor hierarchy (overrides initial answer; resolved 2026-05-05) |
| OQ-1 | Step 6 UI display columns? | Folder path, document count, folder count, size — UI designed for extensibility |
| OQ-2 | Document types requiring unconditional preservation? | None |
| OQ-4 | Archive library — naming or selection? | Operator selects or creates library; optional subfolder in either case |
| OQ-5 | Robocopy confirmation mechanism? | UI checkbox before Step 12; confirming user and timestamp logged |
| OQ-6 | Process ticket expiry recovery? | App auto-obtains new ticket on behalf of authenticated user — no manual re-auth |
