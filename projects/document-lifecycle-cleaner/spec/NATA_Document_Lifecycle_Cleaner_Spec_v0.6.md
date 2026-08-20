# NATA — Document Lifecycle Cleaner
### Specification v0.6

_Last updated: 2026-08-19 (rev 44)_

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

**First-run setup** is a two-phase wizard for a fresh deployment: it captures the application-database connection (which the migrator then uses to create/upgrade the schema) and the MAGIQ access essentials (SOAP endpoint + allowlist), applied live without a second restart. The MAGIQ access phase runs: **test the SOAP endpoint → bootstrap sign-in → allowlist**. The endpoint field auto-appends `/srv.asmx` if the operator leaves it off. The operator then signs in with a MAGIQ account (authenticated against the candidate endpoint); that account is auto-added to the allowlist as the first operator (pinned, non-removable) and its ticket authorises the `GetAllUsers` typeahead used to add any further operators. This bootstrap sign-in is required because `GetAllUsers` (like the retired anonymous `UserExists` allowlist check) cannot be called anonymously. **Once signed in the endpoint is locked** (shown as a read-only, visually distinct field); changing it requires an explicit **Change** action, which forces a fresh sign-in and resets the allowlist — so an operator can't authenticate against one service and then silently repoint at another. **Completing setup carries the operator straight into the app** (the bootstrap sign-in's shared ticket cookie is adopted — no second login), falling back to the sign-in screen only if that ticket has lapsed. The MAGIQ Documents **database** connection string is captured in the same step, after sign-in — a **required** field with its own **Test connection** action (`POST /setup/magiq/test-database`), re-validated and actually opened server-side before anything is written, and stored encrypted like any `Secret` setting. It shows the **same worked example** (SQL auth and Windows auth) that System Settings shows under the same setting — one shared string, so the two surfaces cannot drift. It is no longer left to System Settings: without it the first run cannot identify a single candidate, so an install that "finished" setup without it had merely deferred the failure to the first query, with a run already created (rev 25).

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
| List libraries | `GetDomains` | Step 8/9 library picker + new-run source picker (live; a real id/hidden/archive flags are MAGIQ-native facts, decisions/log.md [2026-08-14]) — the folder browser itself no longer calls `GetFolders`; it reads live `FOLDERS`/`FOLDERMAP` rows through three configurable MAGIQ queries instead (rev 11, decisions/log.md [2026-08-14]) |
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

The step runs as **three passes**, each with its own item count and its own name in the Run progress panel (rev 43):

**Pass 1 — delete the archive's contents in chunks** (`DeleteFolder`, *"Deleting the archive contents"*). A folder delete leaves **one recycle-bin entry per folder**, so taking the archive apart before deleting the library is what turns the destruction below into a countable list. The chunks are chosen by depth: the **shallowest depth beneath the archive destination holding at least `ArchivePurgeChunkTarget` folders** (default 25, preferring a shallower level to one that would exceed 1,000 pieces; `0` disables chunking). A `DeleteFolder` takes the folder's whole subtree in one server-side operation, so the only question is how finely to slice — deleting every recorded folder would be twice the folder count in round-trips to say what a few hundred chunks already say. Taking them all at one depth also means no chunk contains another, so the deletes are order-independent. The plan is drawn from the archive folders the run recorded creating (`CleanupRunArchiveFolder`) — no live walk of the tree.

**Pass 2 — purge those chunks** (*"Purging the archive contents"*). `GetRecycleBinContent` is read once, and each entry that reconstructs (parent `DeletePath` + leaf name) to a folder pass 1 just deleted is destroyed with `PurgeRecycleBinItem`.

**Pass 3 — delete the library and purge what is left** (*"Purging the remaining deleted items"*):

1. `DeleteDomain` deletes the (now largely empty) archive library; what it leaves in the recycle bin carries `DeletePath = "\{ArchiveLibraryName}"` (or a path beneath it). **Observed on a real run (rev 24):** the archive library arrives as **one single large entry**, not as the scattered per-item entries the 34525 training verification suggested. The `DeletePath` match handles either shape.
2. `GetRecycleBinContent` lists the recycle bin.
3. Each item belonging to this run's library (matched by `DeletePath`) is permanently removed with `PurgeRecycleBinItem` — a targeted purge, never a blanket empty-recycle-bin.
4. **The source folders Step 11 deleted are purged in the same pass** (rev 23, `decisions/log.md` [2026-08-14]). `DeleteFolder` is a soft delete, so every folder the run removed is also sitting in the recycle bin — matching only the archive library left all of them behind (1,136 on a real NATA run). Each is matched on **both** halves of its bin entry — the leaf name *and* the parent `DeletePath` — so a same-named folder under a different parent, or an unrelated item someone else deleted, is never touched. The match **fails closed**: if MAGIQ describes the entries in a shape the matcher does not recognise, the run purges nothing from the source and logs samples of what it saw rather than guessing.

**Chunking is an optimisation, never the guarantee.** Anything passes 1–2 miss — a folder the run never recorded, a delete MAGIQ rejects, a bin shape the matcher does not recognise, a recycle bin that cannot be read — is still inside the library when `DeleteDomain` runs and is still swept up by the `DeletePath` match behind it. That is what makes it safe to plan from the run's own records. The one thing pass 3 must **not** do is re-attempt a chunk whose purge went **unanswered**: that call may still be running server-side, so such an item is excluded from the final sweep and left in the bin as a recorded failure rather than destroyed twice (see *Timeouts and the unanswered purge*).

**Concurrency.** Every pass runs **one item at a time** by default. `ArchivePurgeConcurrency` (default 1, maximum 8) raises it, but simultaneous destroys against a single MAGIQ Documents instance are unverified — the service was already timing out on one — so it is an operator dial, not the default.

The set of source folders to purge is derived from the **operation audit trail** (`DeleteFolder`/`Ok` rows in the `Cleanup` phase), not from the run's folder rows. The [empty-subtree prune](#step-11--delete-empty-folders) deletes folders the run never evaluated, which therefore have no folder row at all — reading the folder rows alone silently left exactly those empty folders in the bin. Restricting to `Cleanup`-phase rows is what keeps a **rollback** teardown's archive-folder deletes (which are recorded the same way, without a phase) out of the source purge list.

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

**Cutoff date, source library, and an optional starting folder** — When creating a run, the operator picks the **cutoff date** (a calendar year-end date, e.g. 31 December 2024) and the **source library** to cull from, chosen from the live list of MAGIQ Documents libraries. Both are persisted on the `CleanupRun` and bound into the configured queries per run (`@specifiedDate`, `@sourceDomainId`). Documents with a modification date **≤** the cutoff are candidates.

The new-run form asks for the **year-end cutoff first** — it is the decision the run is about, and it frames what the operator is then choosing a source *for* — with a description of what the date does (documents modified on or before it are archived; anything newer is kept and protects every folder above it). Beneath it, the source picker carries its own **required** label (*Library or folder to cull*, asterisked like the cutoff, since a run cannot start without it) and presents the same top-level **Library** / **Folder** choice as the Step 8/9 archive-destination picker, sharing the same browsable library list (filter box, standard/archive/hidden icons). A one-line description sits **directly under the two tabs** stating what each selects — the difference between them decides how much of the repository the run may touch, so it is stated before the operator picks rather than after (rev 33). **Library** culls the whole chosen library. **Folder** additionally browses one level at a time into that library and lets the operator select a folder, scoping identification to **that folder and everything beneath it** rather than the whole library. This is **optional**; leaving it unset keeps the original whole-library scope (`decisions/log.md` [2026-08-13]). Changing the source library resets any chosen starting folder, since it was browsed under the previous library. The starting folder must already exist — there is nothing to scope to if it doesn't, so (unlike the archive-destination Folder picker) there is no "create a new folder here" option. **Known limitation:** the on-demand "before" Document Register export (Step 2) is not narrowed by a starting-folder scope — its columns are entirely operator-defined, with no guaranteed path column to filter on — so a scoped run's downloaded register still reflects the whole source library.

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
- **Job Details View** — opened from the dashboard. At the top a **persistent phase stepper** shows where the run is across the whole pipeline — **Identify → Review → Normalize → Archive → Cleanup** — driven by the run's actual phase: completed phases read as done, the current one is highlighted (or marked failed), and a Normalization phase that needed no changes simply shows complete as the run flows on to archival. The stepper card also owns the **phase log** (phase-grain: started/completed/failed per phase, with timestamps) behind a closed-by-default **Phase timeline** disclosure — it is the same timeline the stepper draws, and as its own card it sat permanently on an active run as a table nobody works with (rev 35). Below the stepper: full run detail and live progress via SignalR, a final success/failure summary at completion, the register-download control, the run's lifecycle actions, and the **operation audit trail** (object-grain: every create, move, delete, purge, rename, merge, folder-rule relax/restore, and operator decision the run made against MAGIQ, with timestamp, outcome, and operator — see below). The audit trail is presented as a compact **live activity** feed of the most recent operations with plain-language descriptions above the **full trail**, which is **server-paged** and **searchable/filterable** by free text, operation, target, outcome and path — so a run with tens of thousands of moves stays responsive instead of loading its whole history at once. The trail shows When, **Source path**, Operation, Target, Outcome, **Destination path** and Detail. All columns are **sortable** (ordered server-side across the whole run, not just the current page); the When, Operation, Target and Outcome columns are **content-sized** (fitted to the widest value they actually hold, with a small buffer). The **Source path** and **Destination path** filters each offer a **typeahead** of the run's recorded values, and every path has a **copy** control. An **Export CSV** button downloads the trail honouring the **current filters** (the whole filtered set, not just the visible page); the file opens with a short summary of the applied filters so it is a self-documenting audit artifact. Both surfaces are **hidden from the Job Details view until the run has reached the Normalization wizard phase** — nothing recorded during Identification or the Step 6/7 review is shown or exported, matching Rule 7 (the audit starts where the run starts mutating the customer's live repository); the underlying `GetRunOperations`/export reads likewise exclude any `Identification`/`ReviewSelection`-phase rows server-side. Once visible, both surfaces **always tail — they never stop polling — and adapt their speed**: every 5s while new rows are arriving, every 15s when nothing is changing. The animated **"Tailing"** chip shows whenever the fast speed is active. This is deliberately **not** conditioned on the run's status: a run's status describes its disposition, not whether work is happening, and a **rollback runs against a `Cancelled` or `Failed` run** while streaming progress the whole time (as do the move-failure and normalization retries, the empty-subtree prune and the Step 12 purge, which run at `AwaitingInput`). The surfaces detect the activity themselves, from the audit trail growing, so no list of "states in which work can occur" has to be maintained or can go stale; the worst case for an unforeseen operation is a single 15s tick before it appears. The live tick refreshes the **rows**, not just the count: with the trail defaulting to oldest-first, new rows land on the last page and nothing the operator is reading moves. The **Run progress** panel's live chip follows the same principle — it appears when the run is `Running` *or* the SignalR hub has pushed a message recently, so a rollback shows as live rather than moving a progress bar with no indication that anything is running (rev 28).
- **Normalization Review view** — reached from the Job Details view when a run pauses at the Step 8 name-conflict gate (`AwaitingInput`). A folder-structure view adapted from the Step 6 folder review, it renders the **projected archive outcome** of the normalization plan with each name conflict badged in place. Each conflict shows its issue, a pre-selected safe (non-destructive) suggested resolution, and the applicable options (rename folder, rename document, merge folders, keep-one/delete-other), with an impact summary and a confirm before submitting. Submitting re-runs the dry run and loops until no conflicts remain; resolutions auto-save as a draft.

### Auditability — before, during, and after a run

A run is designed to be fully accountable end to end (`decisions/log.md` [2026-08-05]):

- **Before** — the operator captures a **pre-run Document Register** snapshot (every document at/before cutoff in the source library — narrowed to the run's starting folder and everything beneath it, if the run was scoped to one — before the Step 6/7 review is even applied), retained with the run and exportable to CSV or Excel.
- **After review, before Normalization** — a **post-review snapshot** captures the run's own outcome ledger (same shape as the "after" ledger below) immediately once Step 7 confirm applies the operator's Step 6/7 folder selections — so a document under an unselected folder already reads `Kept` and each folder shows its `IsSelectedForDeletion`/document/subfolder counts — but before Name Normalization or Archival touch anything. Diffing this against the "before" snapshot shows exactly what the review excluded, without waiting for the run to finish (`decisions/log.md` [2026-08-14]).
- **During** — every mutating operation the run performs against MAGIQ, and every operator decision that shapes it, is written to an **append-only operation audit trail** (`CleanupRunOperation`): archive-library and folder creates, document moves (recorded **per document** — one entry per move, with its path, destination and outcome), empty-folder deletes, library delete + recycle-bin purge, Name Normalization actions (source renames, folder merges, and duplicate-document deletions) with the operator's conflict resolutions, each reactive folder-rule relax and restore, operator overrides of the acronym pre-select, the purge authorisation (pre-granted at Step 7 or typed at Step 12), and — when a terminal run is **rolled back** — every document **move-back** (recorded **per document**, the reverse of the archival move) and the archive-library **teardown** (folder deletes + recycle-bin purges, tagged as rollback). This is separate from, and complements, the phase log.
- **After** — a **run outcome ledger** (each document's final disposition, each folder's final status/selection/counts, and the rename log) gives the post-run picture, exportable to CSV or Excel. Because the source has been moved/purged by then, "after" is built from the run's own record, not a re-query of the source library.
- **Name changes, before and after** — the Step 8 name-change list (every rename plus resolved folder merges/duplicate deletes) is itself pinned twice: once when the plan is clean and shown at the Normalization Review gate, and again once every change is confirmed applied — so the name-normalization step has its own before/after picture, alongside the whole-run one above (rev 14, decisions/log.md [2026-08-14]).

Together these answer *what the repository looked like before, what the operator's review chose, what the tool did, and what it looked like after*. Both the on-demand register and the pinned snapshots export to **CSV or Excel** (`?format=csv|xlsx`); the pre-run and post-review snapshots are captured automatically at confirmation and the post-run outcome ledger when the run completes, all retained with the run in CSV — the name-change snapshots follow the same pattern, pinned automatically at their own two moments rather than downloaded on demand. (Implemented, including the SPA: the Job Details view shows the operation audit trail and a before/after/post-review snapshot download panel with an Excel/CSV toggle. Name Normalization now writes `Rename` rows to the operation audit trail. Remaining polish — reviewing-operator attribution for overrides — is tracked in `deferred-work-plan.md`.)

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
| **Re-run from Step 1** | For a clean-slate terminal run (one that is currently deletable — no un-rolled-back changes in MAGIQ): rewind the whole run to identification and start again on the same cutoff and source library, with a fresh process ticket. The run **keeps its id**, so everything the abandoned attempt derived is cleared first — the **Document Register exports** (every pinned before/after snapshot and the on-demand export), the Step 8 **rename plan** and the **name-conflict** rows — and identification rebuilds the candidate documents and folders from scratch. The register panel therefore starts empty and re-pins its snapshots as the new attempt reaches each point. The **operation audit trail and phase log are kept**: they record what the previous attempt did in MAGIQ and the rollback that made the run re-runnable, and a re-run must not erase that (`decisions/log.md` [2026-08-18]) |

Because the phase bodies are idempotent, Reset and Retry converge behaviourally — neither re-moves a moved document nor recreates the library; they differ in the step marker and the log event recorded. The **failed-document list persists** across Reset and Retry so the operator can compare attempts. The reactive folder delete-rule handling (above) applies on every move/delete attempt, including retries.

---

## The Process

### Phase 1 — Identification

#### Step 1 — Retrieve candidate documents

Run the configured `CandidateDocuments` query to retrieve every document in the source library whose modification date is ≤ the cutoff. If the run has a starting-folder scope, the result is then narrowed in-app to only that folder and its subtree (`decisions/log.md` [2026-08-13]) — the configured query itself is unchanged and still runs whole-library. Candidates are persisted against the run (`Pending`) for the archival move. Each candidate also records whether its source folder disallows document deletes (a review/audit flag).

#### Steps 2–3 — Document register and export (on demand)

The configured `DocumentRegister` query produces a human-readable register of the candidate documents; its column aliases become the Excel headers. NATA had no existing register report, so the application ships a default one, editable via the admin screen. Export runs as a background job (not inside the download request): the operator requests it, a Hangfire job renders the `.xlsx` off the request thread and stashes it, and the SPA polls for progress and then downloads — decoupling generation from any request/proxy/IIS idle timeout.

#### Step 4 — Produce candidate folders

From the candidate documents, the configured `CandidateFolders` query returns each folder that directly holds a candidate document **and its full ancestor chain**, with each folder's direct document/folder counts, size, a "contains a post-cutoff document" bit, and the delete-rule review flags. The application then applies protection and the acronym pre-select in memory:

- **Protection (Rule 2):** a folder that directly holds a document modified **after** the cutoff is protected, and so is its **full ancestor hierarchy**. Protected folders are never deletable.
- **Acronym pre-select:** a folder whose name matches a deletable acronym is pre-selected for deletion (selected by default), unless it is protected — protection always wins.

If the run has a starting-folder scope, protection is computed over the **full, unscoped** ancestor rows first — so an out-of-scope ancestor above the starting folder can still correctly gate protection on folders within scope — and only the final candidate-folder list is then narrowed to the starting folder and its subtree (`decisions/log.md` [2026-08-13]).

#### Step 5 — Resolve folder paths

The configured `FolderPaths` query returns the full resolved path for the candidate folders and their ancestors; these paths are surfaced in the review UI and used as the SOAP move/delete targets.

### Phase 2 — Review & Selection

#### Step 6 — Review and select folders (React UI + .NET API)

A React UI presents the candidate folders (tree or flat list) with their resolved paths and review columns. Folders matching a deletable acronym are **pre-selected** for deletion; the operator can deliberately **override** an individual pre-selected folder to keep it. Protected folders (Rule 2) are never deletable and cannot be selected; since they clutter a list the operator can't act on, they are **hidden from the folder list by default** and only appear when the **Protected** status filter is deliberately applied. Selections are auto-saved as a draft so an interrupted review survives a refresh.

Four bulk actions share one coherent, **filter-scoped** toolbar directly under the path/acronym text filter — every one of them acts only on the folders **currently matching that text filter** (and the status filter), so typing a filter first and then clicking any of them narrows what gets touched, exactly as it narrows what's shown. **Select all matching** / **Deselect all matching** toggle every freely-selectable (not pre-selected, not protected) matching folder. **Select empty folders** and **Select naming-convention folders** are two further independent, self-toggling criteria over the same matching set — deliberately not combined with each other, since "has no documents" and "matches a deletable-acronym rule" are different rules with only partial overlap: **Select empty folders** toggles every unprotected matching folder with no documents (regardless of acronym match); **Select naming-convention folders** toggles every unprotected matching folder matching a configured deletable-acronym rule (regardless of document count). Each of the four reads the current state of its own set — if every matching folder is already selected, clicking deselects them (unlocking any pre-selected ones so they read *Overridden*); otherwise it selects them. A caption below the toolbar names the active filter when one is set, so it's never ambiguous what "matching" means in the moment.

Separately, **Deselect all** is the one action that deliberately ignores the filter — it clears every selection in the whole run, including pre-selected acronym folders (which are then marked overridden so their row reads *Overridden* and stays editable), as a full reset to rebuild the selection from scratch.

In the tree view, a parent/aggregate row's checkbox reflects **every deletable descendant** (freely-selectable and pre-selected alike), not just the freely-selectable subset — showing a **dash** when some, and a **tick** when all, of its descendants are selected, even when those descendants are entirely acronym pre-selected folders. Clicking the parent checkbox still only bulk-toggles the freely-selectable descendants (pre-selected folders still require a deliberate per-row override), so it is disabled — while still showing the correct tick/dash — when a subtree has nothing freely selectable to toggle.

The status filter (**All / Deletable / Protected / Pre-selected / Overridden / Selected / Empty / Has documents / Delete-locked**) carries a short header explaining that it only changes what the list displays, not what is selected.

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

**Reviewing the rename list and confirming.** Step 8b **never advances on its own**. After it applies the plan, the run **always pauses** in the Normalization phase and the details view shows a **summary of the execution** — a progress bar, applied/failed/pending counts, and how far each kind of item has got ("Folders 12/40", "Documents 380/2,104") — with a **Show detail** link expanding the **full list of folder and document renames**, each row updating **inline** as it is applied: *Renaming…* → *Renamed*, or the **failure reason** if it could not be applied. This is true whether every rename succeeded or some failed. The detail starts collapsed, and **opens itself once (and only once) if the phase stops with failures** — there the list is the operator's work queue rather than reference material. The operator fixes the cause of any failure in MAGIQ and **retries** it — one at a time or all together (each retry runs inline and stays listed as a record; a folder rename repaths its descendants and the affected candidate documents just as the forward pass did), and every attempt is written to the operation audit trail. **The run cannot advance while any item is still failed or pending.** Only once every rename shows *Renamed* does the **Confirm & continue to archival** button enable; it sits **after** the phase's content, with a status line stating why it is or isn't available — the same footer shape every other operator gate uses — and nothing is archived until the operator clicks it. (A run paused here has already executed at least one rename, so it is an audit — see Rule 7.)

**Every mutating action is recorded** — for a rename, the item type, its original path/name and the new name; for a merge or delete, the items involved and the operator decision — with the operator/process ticket and a timestamp, persisted against the run and written to the operation audit trail. Actions are batched with per-item status and resume-from-failure, and report progress like Step 10. The phase is idempotent on resume: an item already at its resolved name (or already merged/deleted) is skipped. An action that cannot be completed leaves the item flagged and, as with an unmovable document, blocks the archival move for that item; the run surfaces the failures. Only once execution is complete does the pipeline chain to archival.

The exact path form the rename/merge/delete ops accept for a still-affected source item, and the ordering behaviour, are confirmed at integration against training (same `xsd:any`/behaviour class as ADR-011 / Story 34525).

### Phase 4 — Archival

#### Step 9 — Select or create the archive destination

The destination is one of two mutually exclusive kinds, chosen at the top of the "Archive destination" modal (decisions/log.md [2026-08-13]):

- **Library** — the destination is a library's **root**, nothing more. Either a **new library** (enter a name — prefilled `Archive {SourceLibraryName} - {ShortFriendlyDate}`, e.g. `Archive NATA - Dec 2024`, editable before confirming) or an **existing library** chosen from the live MAGIQ Documents list (name-filterable). There is no subfolder step here — that's what Folder is for.
- **Folder** — the destination is a specific **folder within an existing library**. The operator picks the library (same filterable list as Library/existing), then browses its subfolders one level at a time (on-demand, lazy-loaded); at the current level they can either pick an existing subfolder to drill into, or type a new folder name to append — that folder is created on demand during archival if it doesn't already exist, the same as any candidate folder the run creates. A run can't create a brand-new library and target a folder inside it in one step — Folder always targets an existing library.

A library the run **creates** is recorded so a rollback can tear it down; an operator-chosen **existing** library is never torn down wholesale, and a **Folder** destination never tears down any part of the (necessarily pre-existing) library.

**Destination ancestor name normalization (`decisions/log.md` [2026-08-13]).** A **Folder** destination can pass through one or more pre-existing MAGIQ folders the run did not create — folders that were never candidates for Step 8's source normalization, but can carry the same whitespace/invisible-character problem (they were reached by browsing/typing real MAGIQ folder names). Before the destination path is used, the run checks each pre-existing folder in that chain from the library root down and, if any carries a normalization problem, renames it in place — the same mechanism Rule 7 applies to source items — so the archival move and any later rollback move-back can address it reliably; a not-yet-existing folder the operator types fresh is normalized before it is ever created. This closes the gap symmetrically with source-side normalization: **both ends of a Folder-destination move are now guaranteed whitespace-clean.** A **Library** destination is unaffected — its path is always a library root, so there is no ancestor chain to check. **Known gap, not covered:** when an *existing* library is adopted by id, the library's own name is not checked or corrected — this is a smaller, separate residual risk, noted here rather than silently left undocumented.

#### Step 10 — Move documents to the archive library

Only documents whose **containing folder was actually selected for deletion** at Step 6/7 are moved. Step 1 (identification) scopes candidate documents only by cutoff date and source library — independent of the folder acronym/protection rules Steps 4–5 apply to folders — so the operator's final selection (including any override) is projected onto the candidate document set once, at Step 7 confirm: a document under a folder that was left unchecked or overridden to be kept is marked `Kept` and excluded from this step, the same way a Step 8 duplicate-delete resolution excludes a `Deleted` document (`decisions/log.md` [2026-08-13], fixing a defect where archival moved every candidate document regardless of the operator's folder selection). A `Kept` document stays in its source folder — which is why an unselected folder never becomes empty and so is never a candidate for Step 11's delete.

The background phase creates the archive library if needed, ensures the destination folder structure exists, and moves each remaining candidate document into the archive, recreating its source-folder hierarchy beneath the destination. Library creation is **idempotent**: before `CreateDomain` the phase lists existing libraries (`GetDomains`) and, if one with the run's name already exists (as happens when a prior attempt created the library but crashed before persisting its id, so a resume re-enters create mode), it **adopts that library and skips creation** rather than failing on *"A library with this name already exists."* An adopted library is **not** flagged as created by this run, so a later rollback/teardown never deletes it — an orphaned empty library from a prior crash is left for the operator to remove. Because Step 8 has already normalized the source names, the source and destination paths are whitespace-clean and the `Move` addresses them cleanly. Moves are batched with per-document status, a single retry pass for failures, and resume-from-failure; progress shows on the dashboard (polling) and in the details view (live via SignalR), with failed documents surfaced as they occur.

If a move fails because the source folder disallows document deletes, the reactive delete-rule handling relaxes that folder's rule, retries the move, and restores the rule (see [Folder rules](#folder-rules-and-the-move-is-copy--delete-constraint)). A document that still cannot be moved after the retry is left `Failed`; there is no rollback of already-moved documents within the run — the phase resumes from the point of failure. If any documents remain unmovable, the run fails with them listed, and the cleanup phase does not proceed.

**Working through move failures (`decisions/log.md` [2026-08-10]).** When a run fails at Step 10 with unmovable documents, the details view shows a **Document move failures** panel listing each failed document with its path, error and attempt count. The operator can fix the underlying cause in MAGIQ and then **retry** the failures — one at a time or all together. Each retry runs **inline**: the row shows *Retrying…* and then, on success, *Moved* in place, and the row **stays in the list** as a record; the main run-progress panel is not disturbed. A retry re-attempts only the chosen documents (reusing the same move machinery, including the reactive delete-rule handling); before attempting, it reconciles each candidate's stored path against the Step 8 rename record, so a document that failed because its source folder was renamed is repaired and then moves cleanly. Any that still fail remain listed with their new error for another attempt (Retry all works through the failed rows one by one, showing progress on each). When a retry clears the **last** failure so every document is archived, the run does **not** auto-continue: it **pauses after archival** (`AwaitingInput`) and the panel offers **Continue to cleanup**, so the operator explicitly proceeds to the folder deletes and the (irreversible) purge. Nothing is deleted until the operator continues.

### Phase 5 — Cleanup

#### Step 11 — Delete empty folders

> **What the operator sees it called.** In the run view this step is labelled **"Empty folder cleanup"**, not "Cleanup (step 11)": the phase name covers both this step and Step 12's irreversible purge, which is the last thing that should be ambiguous. The Run progress panel additionally names the **pass** currently running — Step 11 runs two, **"Deleting empty folders"** (the reviewed selection) and then **"Pruning empty subfolders"** (the empty-subtree prune below) — each with its own item count, so the progress bar legitimately fills, resets and fills again. Before rev 29 nothing distinguished the two fills, and a completed step read as a job looping (rev 29).

Once every move is confirmed complete, the selected, non-protected folders (now empty) are deleted to the recycle bin. This is best-effort per folder: a failed delete is recorded against the folder and surfaced, and does not stop the run. If a delete fails because the **parent** folder disallows folder deletes, the reactive delete-rule handling relaxes the parent's rule, retries the delete, and restores it.

Folders are deleted **deepest-first** (child before parent), and — separately — each delete is preceded by a **live check** that the folder currently has no remaining subfolder; if MAGIQ still reports one, the delete is refused rather than attempted (`decisions/log.md` [2026-08-14]). That refusal is audited as **Deferred, not Failed** (rev 30): for a folder whose subtree this run never evaluated it is the *designed* first outcome, and the second pass below prunes the empty children so the delete then succeeds — recording it as a failure filled a healthy run's activity feed with red rows the run itself cleared seconds later. This classification applies **wherever the refusal is reached** (rev 44) — the first pass, the operator's **Retry**, and the inline retry the prune cycle runs automatically on every pass. Rev 30 changed only the first pass, so the retry kept writing the same red rows on every run with a blocked folder; the exemption from the reactive rule handling was already shared, since it lives in the common folder-group runner. The folder row still carries its `Failed` status and blocking reason, which is what hands it to the prune pass and what keeps an unresolved deferral visible in the Folder cleanup failures panel afterwards. A guard refusal also **never triggers the reactive rule handling** — no rule change can make a live subfolder disappear, so the parent's rules are not read, relaxed or restored on its behalf. Both defenses trace to a real incident: MAGIQ's `DeleteFolder` was found to **cascade-remove** a still-present subfolder along with its parent rather than fail, so a parent deleted out of order (or a subfolder this run never independently evaluated — see the note below) could be silently destroyed as collateral damage. The live check is the actual backstop, since ordering alone can only protect a subfolder this run already knows about.

> **Underlying cause, now surfaced at review (`decisions/log.md` [2026-08-14]):** the Step 4 candidate-folder query's ancestor closure only walks *upward* from a folder holding a pre-cutoff document, never *downward*. A subfolder holding only post-cutoff documents can therefore be entirely invisible to a run — no row, no Protected status — unless it independently happens to be an ancestor of some other candidate elsewhere. The live pre-delete check above prevents data loss, and the **"What's in it?"** action on the failure (Rule 9) now names the culprit from the run's own `FolderCount` snapshot plus a live listing, so a blocked delete is explained and resolvable rather than a dead end. The **empty-subtree prune** (below) now resolves the common case outright by closing downward from the blocked folder itself. The Step 4 query is still upward-only: closing it properly needs a **separate** descendant query driven from the selected set rather than a wider `CandidateFolders` closure (closing downward over candidates ∪ ancestors would pull in effectively the whole library, since the ancestor set reaches root level), and that remains deferred — `FOLDERMAP` being a closure table makes the SQL itself trivial, so the open question is scope, not feasibility.

**Working through folder-delete failures (`decisions/log.md` [2026-08-14]).** The details view's **Folder cleanup failures** panel lists every folder Step 11 could not delete, with its error, and offers three distinct actions, because a blocked delete has three distinct causes.

The panel stays **hidden while the run is still working**, and appears once the run settles — parked at Ready for purge, or finished. Step 11 marks a folder failed as soon as its first delete attempt is refused and then resolves most of them itself in its second pass, so showing them live would fill the list with folders the run is about to fix and then drain it again. A panel that means "what still needs your attention" must not show work in progress. Once the run settles, what is left is genuinely blocked, and the panel doubles as the last look before the irreversible purge is authorised.

- **Retry** — one at a time or all together, for a transient cause (a rule flipped, a ticket expired). Unlike the Step 10 move-failure retry this is **not gated on the run's status or phase**: a folder-delete failure never fails the run (it is best-effort), so a stray failure can be retried at any time, including after completion.
- **What's in it?** — lists what MAGIQ currently reports inside the folder, naming any subfolder this run never evaluated. This is what tells the operator whether the blocker is content legitimately retained (settle it) or a subtree the run simply never saw (cull it separately), without leaving the product to go and look.
- **Settle as skipped** — the terminal resolution for a delete that can never succeed. The pre-delete guard is deterministic, so a folder blocked by an unevaluated subfolder fails identically on every retry; settling records the operator's decision with a **mandatory reason** as a `FolderSkipped` audit row, preserves the blocking error on the folder, and moves it to the terminal **`Skipped`** status so it stops being an outstanding failure and is never re-attempted by a resumed pass. It changes nothing in MAGIQ. `Skipped` is deliberately **not** `Protected`: Protected means Rule 2 retained the folder because of known post-cutoff content and its reason says so, and conflating an operator's judgement call with a policy outcome would leave an auditor unable to tell the two apart.

A successful delete is not re-listed in this panel (it is already recorded in the operation audit trail); the panel exists only for what still needs attention, plus the folders settled as skipped, shown muted for the record.

**Clearing the blockage — the empty-subtree prune (`decisions/log.md` [2026-08-14]).** Most blocked folders are blocked by nothing of value: a subfolder that is simply empty, invisible to Step 4 because the identification query only closes *upward* from folders holding pre-cutoff documents. A second, **automatic pass within Step 11** resolves exactly those, so the operator is not handed a list of failures to work through by hand.

It runs unattended by design. The operator already authorised deleting these folders at Step 7; the empty descendants are *inside* what was approved, and deleting the parent was always going to remove them — that is precisely the cascade the guard defends against. Pruning them first is not widening the approved scope, it is achieving it safely and in the right order.

- **Analysis.** For each failed folder the tool reads that folder's **full descendant closure live from the MAGIQ database** (`FOLDERMAP` is a closure table, so this is one join, driven only from the handful of blocked folders) with each descendant's direct document count, and classifies every descendant as **prunable**, **blocking**, or **retained**.
- **The safety rule.** A descendant is prunable only when its **entire subtree holds zero documents** — nothing that can be lost. **Any** document anywhere beneath a folder keeps that folder, and every ancestor of it up to the blocked folder, out of the plan. The document's date is deliberately irrelevant: post-cutoff means Rule 2 should have protected the branch, pre-cutoff means content this run never reviewed. Neither is the prune's to delete.
- **It only ever deletes folders the run never evaluated.** A descendant that has its own candidate row is excluded outright: if it is selected, Step 11's normal pass owns it; if it is not, keeping it was a deliberate operator decision, reported as *retained* rather than quietly overridden.
- **Execution.** Deletes run deepest-first, each still passing the live pre-delete check, and each recorded as a `DeleteFolder` audit row tagged *"Empty-subtree prune"* so an auditor can see the folder was never on the reviewed list. The blocked folders are then re-attempted. The pass **cycles** — resolving one folder can unblock its parent — and stops as soon as a cycle changes nothing.
- **Folder rules that block the prune (Rule 6, subtree form).** A delete is attempted first, as everywhere else in this pipeline; only if MAGIQ rejects it are rules considered. The ordinary reactive handling relaxes the *immediate parent's* `FolderDeletes`, which cannot reach a rule sitting further up or inherited across a branch — so the prune escalates: relax `FolderDeletes` at the **top of the blocked folder's subtree with `ApplyToTree`**, retry the rejected deletes deepest-first, then restore the captured original the same way. Two conditions, both required. Only a rejection **MAGIQ itself returned** counts — a delete the pre-delete check refused is the tool's own judgement, not a rule problem, and must never trigger a tree-wide rule change. And only when **everything beneath the root is being deleted**, because a tree-wide set stamps the root's rules over every descendant, so any folder that survived would be left carrying the root's rules instead of its own. Relax and restore are audited as `RuleRelax`/`RuleRestore` naming the subtree scope; a failed restore is logged as an error and needs manual attention, exactly as for the per-folder form.
- **What it *proves* it cannot fix, it settles.** A folder the prune's own analysis shows is blocked by content — documents somewhere beneath it, or a subfolder that is not being removed — can never be resolved by a retry, so it is set to **`Skipped`** with the reason naming the blocking paths and counts, rather than left as a failure implying someone still has work to do. The original blocking error is preserved alongside the explanation. **The auto-skip is scoped to exactly that proof** (rev 44): a plan that *claimed* it could resolve the folder and then failed to — because a delete it planned was itself refused by the live guard over a descendant the subtree query did not know about — is **left `Failed`, not skipped.** The two are not the same thing: the second folder genuinely becomes deletable once someone deals with the unknown descendant, and `Failed` is what keeps it in the Folder cleanup failures panel with **Retry**, **What's in it?** and the on-demand prune available, where `Skipped` is terminal and takes all three away. An honest failure the operator can act on beats a tidy settlement that closes the door.
- **Operator re-run.** The same operation is available on demand from the Folder cleanup failures panel (dry run + confirm, per folder or in bulk) for a run that finished before this existed, or one where MAGIQ has changed underneath it since.

This is the **downward closure** the Step 4 query deliberately does not do, placed where it is cheap and safe: driven from the few blocked folders at execution time rather than widened across the candidate set, where it would have pulled in effectively the whole library.

**Finishing the work for a skipped folder.** Settling closes the record; it does not cull the subtree that blocked it. The correct follow-up is a **new run scoped to that folder** — by the time a Step 11 failure is being worked, the archive library this run created may already have been deleted and purged (Step 12), so there is no destination left to archive the missed documents into. Scoping the new run at the parent puts the previously-invisible subfolder inside that run's own Step 4 closure, so it is identified, reviewed and archived normally — the invisibility was always relative to where the *previous* run started, not a property of the folder.

#### Step 12 — Delete and purge the archive library

The archive library is deleted and permanently purged as a background process (the `DeleteDomain` → `GetRecycleBinContent` → `PurgeRecycleBinItem` sequence above, targeted to this run's items). Purge behaviour depends on the Step 7 pre-authorisation:

- **Path A — pre-authorised:** purge proceeds automatically; the pre-authorising user and timestamp are on record.
- **Path B — manual (default):** the run pauses at **"Ready for purge"** (`AwaitingInput`); the details view presents a red **Purge** button whose modal requires the operator to type **"permanently delete"** before the purge starts. The confirming user and timestamp are recorded.

There is no holding period between delete and purge — the purge starts immediately once confirmation is recorded. Steps 11 and 12 report progress the same way as Step 10 — Step 12's progress covers every folder it deletes and every recycle-bin item it destroys, across its [three passes](#step-12--library-purge-sequence), and each one is recorded individually in the operation audit trail alongside a summary row carrying the counts (purged, failed, archive items, source folders, chunks and the chunk depth).

**What the operator sees while it runs (rev 43).** The step is labelled **"Purging deleted items"**; the Run progress panel names the pass beneath it — **"Deleting the archive contents"**, then **"Purging the archive contents"**, then **"Purging the remaining deleted items"** — each restarting the count, with the folder or item name on the live activity row. Before rev 43 the archive half was a single `DeleteDomain` and a single purge of the one entry it left, so the most irreversible minutes of a run reported `0/1` and looked, reasonably, like a hung application. Chunking also makes the destruction **resumable in fact**: a pass that stops part-way has already destroyed the chunks it got through, and each is individually recorded.

**What the purge destroys.** Both the archive library's own recycle-bin content **and** the source folders Step 11 deleted (the sequence above). The typed confirmation says so explicitly, because after this there is nothing left in the recycle bin to restore from.

**Timeouts and the unanswered purge (rev 24).** Destroying an archive library's recycle-bin entry is a single call that runs for **minutes**, so the two destructive SOAP operations — `DeleteDomain` and `PurgeRecycleBinItem` — have their own timeout budget (`MagiqPurgeTimeoutSeconds`, default 30 minutes) separate from the ordinary SOAP timeout, and are **never retried** on a transport failure. A timeout there means the outcome is *unknown*, not failed: the service may well be completing the work. Re-issuing it would start a second destroy. Instead the run **re-reads the recycle bin** and checks whether the item has left it — if it has, the purge succeeded and is recorded as such (noting that it was confirmed by inspection rather than by a reply); if it is still there, or the bin cannot be re-read, it stays a failure. On a real run the archive entry outlived the old 100-second budget, was retried four times, and was reported as failed when MAGIQ had in fact completed it (`decisions/log.md` [2026-08-17]).

##### Archived and purged document records

Alongside the structural record above, the run offers two **document** records in the same Document Register list (rev 40, `decisions/log.md` [2026-08-18]):

- **Archived documents** (`GET /runs/{runId}/documents/archived/export`) — every document Step 10 moved into the archive, with the path it came from and the path it landed at. Available as soon as anything has moved. After the purge this is the only record that those documents were ever at those paths.
- **Purged documents** (`GET /runs/{runId}/documents/purged/export`) — every document destroyed when Step 12 removed the archive library. Available once the purge is confirmed.

Both are derived on demand from the operation audit trail — nothing extra is persisted for them.

**The purged record's grain, which the file states plainly.** Deleting a folder or a library puts it in the recycle bin as a *single* entry, so purging that entry destroys everything inside it in one operation. Since rev 43 the run takes the archive apart a folder at a time first, so MAGIQ confirms a purge **per piece** rather than only once for the library — but still never per document. A per-document list of what was destroyed therefore cannot be read out of MAGIQ; it can only be inferred from *this run archived the document* plus *the archive was purged*. The export makes that explicit: its header prints the two library-level confirmations the rows rest on, every row carries a `Basis` column, and the file renders header-only — with the reason — when the purge has not happened, when the run was **rolled back** (a rollback returns the documents and only then destroys an empty archive), or when the only purge in the trail belongs to an earlier re-run attempt.

##### Deleted folder manifest

Because the purge removes the deleted source folders from the recycle bin, the run also offers a **deleted folder manifest** — a CSV listing every folder it removed from the source library, offered as an item in the Job Details view's **Document Register** list from the moment cleanup starts (`GET /runs/{runId}/folders/deleted/export`, rev 23, `decisions/log.md` [2026-08-14]; moved into the register at rev 39, `decisions/log.md` [2026-08-18]). The typed purge confirmation prompts for it by name and points at the register, since that is the last moment the structure still exists anywhere in MAGIQ.

- **Contents.** One row per deleted folder: path, depth, name, parent, origin, the MAGIQ folder id it had, and — where the run evaluated the folder — the document/subfolder counts and size recorded at identification plus its two delete rules. **Origin** distinguishes a `Reviewed` folder (on the operator's list) from a `Pruned` one (removed by the empty-subtree prune); a pruned folder has no identification snapshot, so its metadata columns are deliberately blank rather than zeroed.
- **Order.** Shallowest-first — the order the folders would have to be re-created in, a parent before its children. This is the reverse of the deepest-first order they were deleted in.
- **What it is not.** A structural record, not a backup. It restores paths and the two delete rules; **description, owner and security/permissions are never read by the pipeline and cannot be restored from it.** The file states this in its own header, because a recovery record that overstates itself is worse than none.
- **Availability.** Derived from records the run already holds (the audit trail plus the folder rows), so nothing extra is persisted for it. A run that reached cleanup is irreversible and is therefore never hard-deleted (Rule 7), so the manifest stays downloadable indefinitely.

---

## Deletable Folder Naming Conventions

Folders whose name matches one of the following acronyms are eligible for deletion and are **pre-selected** (selected by default) in the Step 6 review — **along with every folder beneath them**, regardless of that descendant's own name (rev 18, decisions/log.md [2026-08-14]). This matters because a NATA case folder typically matches the convention itself (e.g. `60912 SRV 2016`) while its actual documents live in structural children the convention was never meant to name-match (`1) Preparation`, `2) Report Package`, `3) Response`, `Submission 1`, and similar). Pre-selecting only the case folder's own row left those children unselected, which silently excluded their documents from archival (a document is only archived if its *direct* containing folder is selected) and meant the case folder could never actually become empty at cleanup — a real run showed 92% of its candidate documents left behind this way before the fix. The operator may still deliberately override any individual folder's pre-selection — the case folder, or any one of its descendants — to keep it; a **protected** folder (Rule 2) is never deletable regardless of acronym, and protection does not stop the cascade from continuing to that folder's own non-protected descendants (protection only propagates upward, never down).

```
ADV · ARE · ASS · CEA · CGA · CRE · DCR · DEL · DFS · DRV · DTV · FAS
FES · OLC · OLN · REI · RES · SRE · SRV · STF · STI · VAR
```

- **List:** the current list, held in the system-settings store and editable live on the admin screen — NATA can add or remove acronyms without a redeploy.
- **Matching:** the acronym must appear **anywhere** in the folder name (contains match), **case-sensitive** — checked against a folder's own name only; a descendant's selection comes from the cascade above, not a second name check.

---

## Rules

1. **Date cutoff** — Documents with a modification date ≤ the cutoff (in the chosen source library) are candidates for deletion.

2. **Folder protection** — A folder holding at least one document modified after the cutoff must not be deleted; protection extends to the **full ancestor hierarchy**. Protection overrides the acronym pre-select — a protected folder is never deletable or selectable — **and overrides Name Normalization conflict resolution** (Rule 8): a protected folder is never deleted or merged away, and a post-cutoff document is never deleted as a duplicate.

3. **Empty folders** — Folders left empty after the move are deleted (Step 11).

4. **Delete constraint** — Confirmation (Step 7) cannot proceed while any selected folder is protected. The system validates all selected folders and reports the blockers inline; they must be deselected before proceeding.

5. **Confirm before purge** — The archive library is not deleted/purged (Step 12) until purge is authorised — either pre-granted at Step 7 or granted manually via the typed "permanently delete" confirmation. The confirming user and timestamp are recorded in both cases.

6. **Delete-rule handling** — A folder rule that disallows deletes (which would otherwise fail a Step 10 move or a Step 11 folder delete, since a move is a copy + delete) is worked around reactively: the blocking rule is read live, temporarily relaxed on the one folder, the operation retried, and the original rule restored. The restriction is surfaced at review for visibility but is not a blocker. **Subtree form (Step 11 prune):** where relaxing the immediate parent cannot reach the rule that is actually blocking — one set further up, or inherited across a branch — the prune relaxes `FolderDeletes` from the top of the blocked folder's subtree with `ApplyToTree`, retries, and restores the same way. Gated on the rejection having come from MAGIQ (not from the tool's own pre-delete check) and on the whole subtree being deleted, since a tree-wide set overwrites every descendant's rules.

7. **Name normalization & audit lock** — Because the MAGIQ web service cannot `Move`/`CreateFolder` an item whose name (or folder-path level) holds a whitespace variant (a doubled space, a non-breaking space `U+00A0`, or any other Unicode whitespace) or an invisible format character (zero-width space, BOM, soft hyphen, etc.) — while the desktop UI allows such names, and they are easily pasted in from other documents — a **Name Normalization** phase (Step 8) renames every affected **source** item in place before the archival move (whitespace → a single regular space; invisibles → stripped; see [Whitespace normalization scope](#whitespace-normalization-scope)), so the move can succeed. Every rename, merge and delete is recorded (item type, original path/name, new name, operator/ticket, timestamp). These changes mutate NATA's live repository and are **not** reversed by a rollback, so **once the phase has executed its first change (Step 8b) the run becomes an audit** and can no longer be permanently deleted — only archived for the record. A run still in the dry run or conflict-resolution gate has changed nothing and stays deletable.

8. **Name-conflict resolution gate** — When normalization would rename two or more items to the same name under the same parent (a folder or document conflict, evaluated against the whole projected structure including non-candidate siblings), the run pauses (`AwaitingInput`) and the operator must resolve every conflict before any change is executed. Options are rename folder, rename document, merge folders, or keep-one/delete-other; the pre-selected default is always a non-destructive rename, and the destructive options (merge, delete-duplicate) require a deliberate choice with confirmation and are audited. **Protection (Rule 2) overrides all of this:** no resolution may delete a protected folder or a post-cutoff document — a merge keeps the protected item as the survivor, keep-one/delete-other never targets protected content, the default renames the non-protected side, and when every colliding item is protected only rename is offered. A colliding folder **outside the cull** (non-candidate) is likewise never deleted or merged away — the default renames the candidate side, and merge is offered only with the non-candidate as the survivor behind an out-of-scope warning. Submitting resolutions re-runs the dry run and repeats until no conflicts remain; only then does Step 8b execute.

9. **Completeness invariant** — *Never delete a folder whose contents this run has not fully evaluated.* Deliberately stated as its own rule rather than folded into Rule 2 (`decisions/log.md` [2026-08-14]): Rule 2 is a **retention** rule about *known* post-cutoff content, and its outcome is auditable precisely because the reason can be stated ("contains or descends from a document modified after the cutoff"). This is an **epistemic** guard about content the run cannot see — a different thing, needing a different follow-up, and folding the two together would make Rule 2 unfalsifiable and leave an auditor unable to distinguish *retained by policy* from *skipped through ignorance*. Enforced **at execution** by the Step 11 live pre-delete check, which refuses any folder MAGIQ still reports a subfolder for (and treats an unverifiable listing as "not empty" — fail closed). A folder blocked this way is reported as a Step 11 failure the operator can **retry**, **inspect** ("What's in it?", which names any subfolder the run never evaluated), **clear** (the empty-subtree prune below), or settle as **`Skipped`** with a recorded reason.

The invariant is about *evaluation*, not about never touching an unreviewed folder — so it is satisfied by **extending** the evaluation, which is what the prune does. A folder whose entire subtree provably holds zero documents has been fully evaluated at the moment of the check, and contains nothing that could be lost.

A review-time *prediction* of the same outcome was built and then deliberately withdrawn (`decisions/log.md` [2026-08-14]). Two reasons, either sufficient: at Steps 6–7 the selection being analysed is still only the acronym pre-selection, which the review exists to change — so the warning described a set that was about to stop being true; and the live half **cannot work before Step 8**, because SOAP cannot address a path whose name still carries a whitespace variant, which is the very reason Name Normalization exists. Against a real run it returned *"Target folder not found"* for precisely the folders worth checking. The diagnosis therefore lives where it is both stable and answerable — on the Step 11 failure itself, after normalization. The **post-archival gate** enforces the documents half of the same invariant: the run refuses to proceed from the archival pause into cleanup while any document is still in a failed move state, since the Step 11 check verifies subfolders only and `DeleteFolder` cascades rather than refusing.

---

## History

This document reflects the system as built, including the **Name Normalization** phase (Step 8) added to work around the SOAP double-space bug and now implemented in the working tree (`decisions/log.md` [2026-08-05]). **2026-08-07:** the phase's scope was widened from ASCII whitespace to the **full Unicode `White_Space` set** (all 25 code points — non-breaking, narrow, figure, ideographic and em/en spaces, etc.; equivalently .NET `char.IsWhiteSpace`), each collapsed to a regular space, **plus stripping of invisible format characters** (`U+200B`, `U+200C`, `U+200D`, `U+2060`, `U+FEFF`, `U+00AD`) — because such characters are readily pasted into names from Word, email or the web (see [Whitespace normalization scope](#whitespace-normalization-scope)). **2026-08-07:** Name Normalization gained a **name-conflict dry run + operator resolution gate** — the phase now plans renames without mutating, pauses (`AwaitingInput`) in the new Normalization Review view when renames would collide, lets the operator resolve each conflict (rename / merge / keep-one-delete-other), re-analyses until clean, then executes; the **audit lock (Rule 7) moves to the first executed change** rather than phase entry, and a new **Rule 8** covers the conflict gate (`decisions/log.md` [2026-08-07]). The full history of decisions and resolved questions — protection scope, archive-library selection, purge confirmation, ticket-expiry recovery, the move to database-backed configuration, the overridable acronym pre-select, the folder delete-rule handling, and the name-normalization phase — is recorded in `decisions/log.md` and `references/adrs/`. **2026-08-08:** the first-run setup **admin-allowlist step was reworked** — a MAGIQ update stopped `UserExists` from being callable anonymously, so the wizard no longer validates typed usernames anonymously. Instead the operator does a **bootstrap sign-in** during setup (auto-added to the allowlist, pinned), and the authenticated **`GetAllUsers`** op powers a name/username typeahead (disabled accounts hidden). The same typeahead replaces the plain text allowlist editor in **System Settings**. The anonymous `setup/magiq/validate-user` endpoint was removed; new endpoints `setup/magiq/login`, `setup/magiq/users` and `admin/magiq/users` back the flow (`decisions/log.md` [2026-08-08]). **2026-08-09:** the Step 9/10 archive-library create was made **idempotent** — before `CreateDomain` the phase lists existing libraries (`GetDomains`) and adopts a same-named one if present (skipping creation) instead of failing on *"A library with this name already exists"*; the adopted library is not marked as created by the run, so teardown never deletes it (`decisions/log.md` [2026-08-09]). **2026-08-09:** the reactive delete-rule handling changed from a per-item relax/revert to a **relax-once-per-folder** shape — the phase groups the items sharing a rule-bearing folder, relaxes that folder's rule a single time, retries the blocked items, and restores once; the old per-item flip churned the same folder's rule and left later items in a folder failing during a live cull (`decisions/log.md` [2026-08-09]). **2026-08-09:** the **operation audit trail** in the Job Details view was reworked for scale — the full trail is now **server-paged** (newest first) and **searchable/filterable** by free text, operation, target, outcome and path, above a compact **live activity** feed, and **document moves are recorded per document** (one entry per move, bulk-inserted per batch) rather than one batch-summary entry, so individual moves are visible and searchable (`decisions/log.md` [2026-08-09], reversing the 2026-08-05 batch-summary call). **2026-08-10:** the operation audit trail gained a **CSV export** — an **Export CSV** button in the Job Details view downloads the trail honouring the operator's current filters (the whole filtered set, not just the visible page), streamed from a new `GET /runs/{runId}/operations/export`; the file opens with a `#`-prefixed summary of the applied filters so it is a self-documenting audit artifact (`decisions/log.md` [2026-08-10]). **2026-08-10:** the Step 8 gate was **widened from conflicts-only to any name change** — the run now pauses at the Normalization Review view whenever the plan changes any name, the operator reviews the **full folder/document change list** (surfaced on `GET …/normalization/plan`) and can **download it as a before → after list (CSV/Excel)** via `GET …/normalization/changes/export`, then **confirms** (`POST …/normalization/confirm`) before Step 8b executes; only a zero-change plan still auto-continues, and the audit lock still trips on the first executed 8b change (`decisions/log.md` [2026-08-10]; plan `normalization-change-review-plan.md`). **2026-08-10:** Step 10 gained an operator **move-failure retry** — a Document move failures panel lists each unmovable document and the operator retries them individually, selected, or all (`POST …/archival/move-failures/retry`, list on `GET …/archival/move-failures`); when a retry clears the last failure the run **pauses after archival** (`AwaitingInput`) and the operator explicitly proceeds via `POST …/archival/continue` rather than auto-chaining the irreversible cleanup/purge (`decisions/log.md` [2026-08-10]; plan `move-failure-retry-plan.md`). **2026-08-11:** three normalization/rollback refinements landed together. **(1) Normalization execution gate** — Step 8b now **always pauses** after applying the plan and **never auto-advances**: the details view shows the **full rename list** updating inline (each item *Renamed* or its failure reason), the operator retries failures individually or all (repathing descendants on a folder rename, auditing each attempt), and only once every item is renamed does **Confirm & continue to archival** enable (`GET …/normalization/failures` = full list, `POST …/normalization/failures/retry`, `POST …/normalization/continue`). This also fixed a bug where a failed/paused normalization still ran archival — the phase-runnable guard (`LoadRunnableAsync`) only excluded Cancelled/Completed/Abandoned, so a `Failed`/`AwaitingInput` run's Hangfire-chained archival proceeded; it now no-ops on any non-`Running` state. `RunSummary.EnteredNormalization` distinguishes this post-8b state from the pre-mutation review gate. **(2) Persistent run-phase stepper** — the Job Details view now shows an always-visible Identify → Review → Normalize → Archive → Cleanup stepper driven by the run's phase, with Normalization shown complete/skipped when it needs no changes. **(3) Rollback audit trail** — Tier 2 rollback now writes per-item operation-audit rows: a `MoveBack` per document returned from the archive, and the archive-library teardown (folder deletes + recycle-bin purges) tagged as rollback, so an undo is as traceable as the original archival. Ordered delivery is in `delivery-plan.md`; current status in `tasks.md`. **2026-08-13:** four Job Details/Step 6 refinements landed together. **(1)** The **operation audit trail** (live activity + full trail) is now **hidden until the run reaches the Normalization wizard phase** and excludes any Identification/ReviewSelection-phase rows even if queried directly — the audit starts where the run starts mutating the live repository (Rule 7). **(2)** Both audit-trail surfaces now **poll only while the run is `Running`** (not `AwaitingInput`) and show a **static "Polling…" label** in place of the previous refresh spinner, hidden the rest of the time. **(3)** **Protected folders are hidden by default** in the Step 6 candidate folder list and only shown when the **Protected** status filter is applied. **(4)** Step 6 gained two global bulk actions — **Deselect all** (clears every selection, including pre-selected acronym folders) and **Select empty, naming-convention folders** (selects only acronym-matching folders that are also empty) — alongside the existing filter-scoped select/deselect-matching actions. **2026-08-13 (rev 2):** three corrections to the same day's work. **(1)** The combined "empty, naming-convention" bulk action was wrong — empty (no documents) and naming-convention (acronym match) are different, only partially-overlapping rules — so it was split into two independent, self-toggling actions, **Select empty folders** and **Select naming-convention folders**, each toggling its own criterion on/off based on whether every matching folder is already selected. **(2)** Fixed the tree view's parent/aggregate checkbox: it was computed from only the freely-selectable descendant subset (`TreeNode.selectableIds`), so a subtree made entirely of pre-selected (naming-convention) folders showed no tick/dash at all even when fully selected; it now reads every deletable descendant (`TreeNode.deletableIds`), while bulk-toggle-on-click still only touches the freely-selectable subset. **(3)** Added a header + one-line description above the Step 6 status filter chips clarifying that the filter only changes what the list shows, not what is selected. **2026-08-13 (rev 3):** unified the four Step 6 bulk actions onto one scope — **Select all matching**, **Deselect all matching**, **Select empty folders** and **Select naming-convention folders** all now act on `filteredItems` (the same set narrowed by the path/acronym text filter and the status filter), not two of them silently operating on the whole run; a caption below the toolbar names the active text filter. **Deselect all** remains the sole action that deliberately ignores the filter, as a full-run reset. **2026-08-13 (rev 4):** fixed a defect where Step 10 archived **every** candidate document regardless of the operator's Step 6/7 folder selection — Step 1's candidate-document query and Steps 4–5's candidate-folder query are independent, so nothing previously narrowed the document set to the folders actually selected. `ConfirmDeletionsHandler` (Step 7 confirm) now projects the final folder selections onto the document set: a still-`Pending` document whose containing folder was not selected for deletion is marked `MoveStatus.Kept` (a new terminal status, excluded from Step 10's move set the same way `Deleted` already is) before normalization/archival is enqueued. Step 11's folder delete was unaffected by the defect — it already filtered to `IsSelectedForDeletion = 1` — so only the wasted/incorrect document moves are fixed here, not folder deletion. **2026-08-13 (rev 5):** Step 9's archive destination gained a **Library vs Folder** top-level choice — previously the only granularity was library-root-or-typed-subfolder, conflated inside "create new" vs "choose existing." **Library** now means the root only (create new, or pick existing, from the same filterable list as before). **Folder** is new: pick an existing library, browse its subfolders one level at a time, and either drill into an existing one or type a new name to create it at the current level — the chosen/typed path becomes the destination and is created on demand at archival time if it doesn't already exist. The API's `archiveLibrary.subfolderPath` field was replaced by `destinationType` (`library`|`folder`) + `folderPath`; the underlying `CleanupRun.ArchiveLibraryId`/`ArchiveLibraryName`/`ArchiveSubfolderPath` columns and the Step 9/10 destination-path logic are unchanged — only the request-layer mapping into them changed (decisions/log.md [2026-08-13]). **2026-08-13 (rev 6):** closed a gap in rev 5's Folder destination — a pre-existing MAGIQ folder anywhere in the destination's ancestor chain (browsed/typed via the Step 8 modal) can carry the same whitespace/invisible-character problem Step 8 normalizes for source items, and was not previously checked. The run now walks that chain before archival, renaming any dirty pre-existing ancestor in place (same mechanism as source normalization) and normalizing a not-yet-existing segment before it is created, so both ends of a Folder-destination move are whitespace-clean; a Library destination is unaffected (root only, no ancestor chain). The archive library's own name, when adopted by id, remains a known, separate, uncovered gap (decisions/log.md [2026-08-13]). **2026-08-13 (rev 7):** new-run creation gained an **optional starting-folder scope** — previously the operator could only pick a source *library*, culling the whole thing; now they may additionally browse to a folder within it (same UX as the Step 8/9 Folder destination picker, minus the create-new-folder field) to narrow identification to just that folder and its subtree. Implemented as an in-app path-prefix filter over the existing whole-library query results — not a bound SQL parameter — because MAGIQ's SOAP surface (and the browse UI built on it) addresses folders by path only, never by id, so there is nothing to bind. Folder protection (Rule 2) is still computed over the full unscoped ancestor rows before the final candidate-folder list is narrowed, so propagation stays correct. The on-demand Document Register export is not narrowed by this scope (its operator-defined columns have no reliable path column) — a documented limitation, not an oversight (decisions/log.md [2026-08-13]). **2026-08-13 (rev 8):** the new-run source picker was restructured to match the Step 8/9 archive-destination picker's UI exactly — a top-level Library/Folder toggle sharing one browsable library list (filter box, archive/hidden icons), rather than a plain dropdown with a scope toggle underneath it (decisions/log.md [2026-08-13]). **2026-08-13
(rev 9):** the library/folder browser (both the new-run source picker and the Step 8/9 archive-destination
picker) was switched from live MAGIQ SOAP (`GetDomains`/`GetFolders`) to a **DB-backed catalog** derived
from `dbo.CleanupRunFolder`'s recorded folder paths across all runs, and gained a server-side **name
filter** on the folder level (the library level already had one) plus a **path typeahead** (`GET
/libraries/paths?term=`) letting the operator jump straight to a known path instead of browsing one
level at a time. Consequences: a library/folder with no run history yet won't appear until a run
identifies it, and the archive/hidden icon distinction is lost (those SOAP-only flags are no longer
available). Because the catalog carries no MAGIQ domain id, `POST /runs` now resolves the picked
library's live id itself via a single `GetDomains` call at submit time (`404
SourceLibraryNotFound` if the name no longer resolves); the Step 8/9 archive-destination confirm needed
no equivalent change, since it already addressed the destination by name/path when SOAP exposed no id
(decisions/log.md [2026-08-13]). **2026-08-14 (rev 10):** the library list half of rev 9 was reverted —
`GET /libraries` calls live MAGIQ `GetDomains` again (real id, `IsHidden`/`IsArchive`), since those are
MAGIQ-native facts the DB catalog can't supply; `POST /runs` likewise goes back to trusting a
`sourceDomainId` sent directly from the picker rather than resolving it server-side at submit. The
one-level subfolder browser and the path typeahead **stay** DB-backed (`dbo.CleanupRunFolder`) — that
part of rev 9 is unaffected, since MAGIQ never exposed folder ids anyway and the name filter/typeahead
still work the same way (decisions/log.md [2026-08-14]). **2026-08-14 (rev 11):** the folder browser was
redesigned again, this time discarding the `dbo.CleanupRunFolder` DB catalog entirely in favour of **live
MAGIQ `FOLDERS`/`FOLDERMAP` queries**, addressed by real `FOLDERID`s rather than path strings — closing
the gap rev 9/10 left open (a folder with no run history wouldn't appear, and folders had no id to bind
against). Three new configurable MAGIQ queries back it: `FolderChildren` (one level, by
`domainId`+`parentId`, optional name filter), `FolderSearch` (typeahead across the whole library,
returning id + built path), and `FolderAncestors` (root-to-folder breadcrumb chain via the `FOLDERMAP`
closure table). A root-level folder's `PARENTID` equals its own library's `DOMAINID`, so root browsing
needs no special case — `parentId` simply starts at the domain id. Both pickers (new-run source, Step
8/9 archive destination) now share a single **`FolderBrowser`** React component styled after the
OneDrive "Move to" picker — breadcrumbs, an inline search box that jumps straight to a match via the new
ancestors lookup, the folder list, and (where applicable) an inline new-folder-name field — replacing the
older plain browse-one-level-at-a-time UI. `GET /libraries/folders` moved from a `path=` query parameter
to `domainId=`+`parentId=`+optional `nameFilter=`; two new endpoints, `GET /libraries/folders/search` and
`GET /libraries/folders/ancestors`, back the search box and breadcrumb restoration respectively. The new-run
optional starting-folder scope (rev 7) is unchanged: the picker resolves a trail of real folder ids while
browsing, but `POST /runs` still receives and stores `SourceFolderPath` as a plain slash-joined name path
(`CleanupRun.SourceFolderPath`) — identification still applies it as an in-app path-prefix filter over the
unscoped candidate rows, not a bound folder id (decisions/log.md [2026-08-14]). **2026-08-14 (rev 12):**
the `FolderBrowser`'s "jump to a folder" search was **scoped to the folder currently being browsed**,
rather than matching anywhere in the whole library — `GET /libraries/folders/search` gained a `parentId`
parameter (the same "current location" id `GET /libraries/folders` already takes), and `FolderSearch`
only returns folders with a `FOLDERMAP` row confirming they descend from it. Passing `parentId =
domainId` at the library root still searches the whole library, since the closure table records every
folder's ancestor chain up to its domain. The search box automatically rescopes (and clears any typed
text) as the operator navigates deeper or back up; the Step 8/9 modal's one-shot restore-by-path lookup
deliberately keeps searching the whole library, since it needs to find a previously-picked folder
regardless of where the browser happens to be pointed when it reopens (decisions/log.md [2026-08-14
follow-up]). **2026-08-14 (rev 13):** the new-run source picker's search box was changed from a
subtree-jump search to a **plain client-side name filter** over the folders already listed at the
current location — no API call, and nothing to navigate to, since a match is by definition already
visible in the current list. The Step 8/9 archive-destination picker's search (jump to a match anywhere
in the current subtree) is unchanged; the two pickers now use the shared `FolderBrowser`'s two search
modes (`filter` for new-run, `jump` for Step 8/9) rather than one shared behaviour (decisions/log.md
[2026-08-14 filter-mode follow-up]). **2026-08-14 (rev 14):** the Step 8 name-change list's download
moved off the Normalization Review screen and onto the Document Register. Previously a standalone
"Download changes" button on the review screen hit its own `GET .../normalization/changes/export`
endpoint on demand; now the same before → after content (renames plus resolved folder merges/duplicate
deletes) is captured automatically as two **pinned Document Register snapshots** — `PreNormalization`
(captured the moment the plan is clean and shown at the review gate) and `PostNormalization` (captured
once every rename is confirmed applied and the operator proceeds to archival) — listed and downloadable
from the Document Register section alongside the existing `PreRun`/`PostRun` register snapshots and the
on-demand export. The Normalization Review screen keeps its in-app change table for review, with a note
pointing to the Document Register section for a downloadable copy; the old export endpoint was retired
(decisions/log.md [2026-08-14]). **2026-08-14 (rev 15):** the operation audit trail now defaults to
**oldest-first** ordering so it reads as an append-only log (new rows land on later pages instead of
reshuffling page 1), and its live poll refreshes only the row count/pagination, never the visible rows.
The Step 11 **Folder cleanup outcomes** panel was narrowed to **failures only** (a successful delete is
already an audit-trail row) and renamed **Folder cleanup failures**; it now also supports **retrying** a
failed folder delete, individually or all together (`POST .../folders/delete-failures/retry`), not gated
on run status since a folder-delete failure never fails the run. The `RunProgressPanel`'s own generic
"N failed" list was removed as a fourth, redundant place to see failures (decisions/log.md [2026-08-14]).
**2026-08-14 (rev 16):** a real cull surfaced a Step 11 defect — a parent folder was deleted before its
still-present child, and MAGIQ's `DeleteFolder` was found to **cascade-remove** the child rather than fail,
so the pipeline's own delete attempt for it then failed "Target folder not found." Step 11 now deletes
folders **deepest-first** and, independently, runs a **live pre-delete emptiness check** against MAGIQ before
every delete — refusing it (folder marked failed with a clear reason) if any subfolder still exists, rather
than trusting the run's own candidate-set snapshot. Investigating further surfaced a **known, flagged gap**:
the Step 4 candidate-folder query's ancestor closure only walks upward, so a subfolder holding only
post-cutoff documents can be invisible to a run entirely (no row, no Protected status at Step 6) unless it
independently qualifies as an ancestor of some other candidate. The live check prevents this from causing
data loss, but Step 6 review still won't surface such a folder — closing that is deferred (decisions/log.md
[2026-08-14]). **2026-08-14 (rev 17):** the Document Register's before/after picture gained two fixes,
prompted by the same investigation. **(1)** The pinned "before" (pre-run) snapshot and the on-demand export
were both known to reflect the **whole source library**, ignoring a run's optional starting-folder scope —
they now narrow to that folder (and everything beneath it) by matching a folder-path column in the query's
own results, the same scope logic Steps 1/4/8 already apply; a heavily customized register query with no
recognizable path column is left unscoped (with a warning logged) rather than silently returning nothing.
**(2)** A new pinned **post-review** snapshot captures the run's own outcome ledger immediately once Step 7
confirm applies the operator's Step 6/7 folder selections — before Normalization or Archival touch
anything — so it shows exactly what got `Kept` vs. selected, alongside each folder's document/subfolder
counts, without waiting for the run to finish. The "after" (post-run) ledger gained the same
selection/count columns. See [Auditability](#auditability---before-during-and-after-a-run) above
(decisions/log.md [2026-08-14]). **2026-08-14 (rev 18):** cross-referencing a real run's PreRun/PostReview
exports (the rev 17 feature immediately earning its keep) surfaced the true cause of the Step 11 "still has
subfolders" failures — not a Step 11 bug, but the acronym pre-selection never cascading to a matched
folder's structural children. A NATA case folder matches the convention on its own name (e.g. `60912 SRV
2016`), while its actual documents live in unmatched children (`1) Preparation`, `2) Report Package`,
`3) Response`, `Submission 1`, ...); only the case folder's own row was pre-selected, so those children's
documents were silently excluded from archival (Step 7's Kept-exclusion checks a document's direct parent
only) and the case folder could never truly empty at cleanup. One real run showed **92% of its candidate
documents** left behind this way. Confirmed there was no operator workaround either — the Step 6 tree's
subtree-select cascade only fires from a row that isn't itself pre-selected, and the case folder's row is.
Fixed at the source: selecting an acronym-matched folder now cascades selection to **every** folder beneath
it, matched or not (see [Deletable Folder Naming Conventions](#deletable-folder-naming-conventions) above) —
protection (Rule 2) still always wins for the folder it applies to, and still doesn't block the cascade from
reaching that folder's own non-protected descendants (decisions/log.md [2026-08-14]). **2026-08-14 (rev
19):** the upward-only-closure gap that rev 18's sibling entry flagged rather than fixed stopped being a dead
end for the operator. A second live run hit it again — `.../60912 SRV 2016/3) Response` failed its Step 11
delete because it held a subfolder no candidate row ever covered, leaving it and its parent permanently
`Failed` with retry deterministically futile. Three changes, plus a new **Rule 9** (the completeness
invariant) naming the principle that was previously implicit in the guard: **(1)** a **Step 6/7 completeness
warning** predicts which selected folders Step 11 cannot empty, derived free from the run's own
`FolderCount` snapshot versus the child rows it holds, covering both unevaluated children and deliberately
deselected ones, propagated up the ancestor chain so one root cause reads as one warning; only the
directly-blocked folders are then live-verified against MAGIQ (capped per request) to name the culprits, on
demand via `GET /runs/{runId}/folders/completeness` so it can be re-checked after a fix without re-running
identification. **(2)** A terminal **`Skipped`** folder status plus **Settle as skipped** and **What's in
it?** actions on the failures panel, giving the operator a way to inspect and then close out a delete that
can never succeed — with a mandatory reason recorded as a `FolderSkipped` audit row and the blocking error
preserved. `Skipped` is deliberately distinct from `Protected` so a judgement call is never mistaken for a
policy outcome. **(3)** The **post-archival gate** now refuses to proceed into cleanup while any document is
still in a failed move state (`409 UnresolvedMoveFailures`) — the Step 11 guard checks subfolders only and
there is no verified `GetDocuments` op to check documents with, so blocking at the decision point is what
makes that asymmetry unreachable. The Step 4 query itself is **still upward-only**: closing it needs a
separate descendant query driven from the selected set, since closing downward over candidates ∪ ancestors
would pull in effectively the whole library (`decisions/log.md` [2026-08-14]). **2026-08-14 (rev 20):** the
review-time half of rev 19 was **withdrawn** after its first run against real data. The Step 6/7 completeness
panel was removed outright (API, analyzer and audit surfaces all retained). Two independent reasons: at
Steps 6–7 the selection it analysed was still only the acronym pre-selection, which the review exists to
change, so it warned about a set that was about to stop being true; and the live verification **cannot work
before Step 8**, since SOAP cannot address a path whose name still carries a whitespace variant — it returned
*"Target folder not found"* against precisely the folders worth checking. The same analysis now surfaces only
where it is both stable and answerable: the **"What's in it?"** action on a Step 11 failure, after
normalization (`decisions/log.md` [2026-08-14]). **2026-08-14 (rev 21):** a Step 11 **empty-subtree prune**
was added — a second, operator-gated pass that resolves a blocked folder by deleting the unevaluated
descendants beneath it whose subtrees provably hold **zero documents**, then re-attempting the folder. It
reads the blocked folder's full descendant closure live from the MAGIQ database via a new configurable
`FolderSubtree` query, classifies every descendant as prunable / blocking (holds documents — never touched) /
retained (the run evaluated it and is keeping it), shows the operator the plan, and re-derives it immediately
before executing so a document added during the review cannot be destroyed. This is the **downward closure**
deferred since rev 19, finally placed where it is cheap and safe — driven from the few blocked folders at
execution time rather than widened across the candidate set. Rule 9 gains the corresponding clarification:
the invariant is about *evaluation*, so extending the evaluation satisfies it (`decisions/log.md`
[2026-08-14]). **2026-08-14 (rev 22):** the prune gained a **subtree rule escalation** — where a folder rule
blocks a prune delete and relaxing the immediate parent cannot reach it (the rule sits further up, or is
inherited across the branch), `FolderDeletes` is relaxed from the top of the blocked folder's subtree with
`ApplyToTree`, the rejected deletes retried deepest-first, and the captured original restored the same way.
Delete-first-then-diagnose as everywhere else; gated on the rejection having come from MAGIQ rather than the
tool's own pre-delete check, and on the entire subtree being deleted, since a tree-wide set overwrites every
descendant's rules (`decisions/log.md` [2026-08-14]). **2026-08-17 (rev 23):** Step 12 was completed in three
related ways. **(1) Source folders are purged too** — `DeleteFolder` is a soft delete, so every folder Step 11
removed was still in the recycle bin after a "successful" purge (1,136 on a real NATA run); they are now
matched on both the leaf name and the parent `DeletePath` and purged in the same authorised operation, failing
closed if the bin entries do not have the expected shape. **(2) Purge visibility** — Step 12 now emits progress
for every item it destroys and writes each purge to the operation audit trail, plus a summary row carrying the
counts; previously a multi-minute purge showed nothing at all, which read as a run that had silently stopped.
**(3) Deleted folder manifest** — a new CSV export (`GET /runs/{runId}/folders/deleted/export`) lists every
folder the run removed from the source library, ordered shallowest-first so the structure can be re-created by
hand if it ever absolutely has to be; the typed purge confirmation prompts for it, since afterwards the file is
the only record left. The manifest and the purge list share one definition of "which source folders did this
run delete", derived from the `Cleanup`-phase `DeleteFolder`/`Ok` **audit rows** rather than from folder rows —
the empty-subtree prune's folders have no folder row, and those are precisely the empty folders both callers
were missing (`decisions/log.md` [2026-08-14, 2026-08-17]). **2026-08-17 (rev 24):** the first live purge under
rev 23 exposed two more things. **(1)** `DeleteDomain` leaves the archive library in the recycle bin as **one
large entry**, not the scattered per-item entries the 34525 training verification recorded — corrected above;
the matcher was unaffected, but it means the archive half of the purge is a single operation whose progress
can only read 0 → 1. **(2)** That single call ran for minutes, blew through the 100-second SOAP timeout, was
**retried four times** (each retry starting another destroy), and was then recorded as failed — while MAGIQ had
actually completed it. The two destructive operations now have their own long timeout budget
(`MagiqPurgeTimeoutSeconds`, default 30 minutes), are never retried on a transport failure, and an unanswered
purge is resolved by **re-reading the recycle bin** to see whether the item is gone rather than by guessing
either way (`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 25):** an operator-surface pass over the SPA, plus one setup change with real behaviour behind it.
**(1) Setup captures the MAGIQ Documents connection string** — it is now a required field in the MAGIQ access step
(after sign-in), with its own **Test connection** action (`POST /setup/magiq/test-database`) and a server-side open
before `POST /setup/magiq` writes anything; it is written first, ahead of the endpoint/allowlist pair that
`SetupMagiqState` reads as "configured", so setup can never be observed complete with the connection string still
missing. Previously setup finished without it and the operator was told to set it in System Settings — an install
that looked ready and failed at the first identification query. **(2) Liveness is now shown, not stated** — the run
header's **Running** badge, the phase stepper's current step, the Run progress transport chip and the audit trail's
follow indicator all animate *only while the run is actually `Running`*, and the transport chip is hidden entirely
otherwise (it previously showed "live"/"polling" on finished runs, and the striped "working" bar ran while the run
sat at an operator gate). All motion is decorative, driven from one stylesheet, and disabled under
`prefers-reduced-motion`. **(3) "Polling…" became "Tailing"** on both audit surfaces — polling named the transport
(and, as rev 27 found, only half-truthfully: the tick was refreshing the count, not the rows), where tailing names what
the operator gets. **(4) Recent activity rows** now carry the **full source path** and any error on their own lines
beneath the summary, which named only the leaf — ambiguous in a repository where the same document name recurs
under dozens of folders. **(5) The audit trail's Destination path column shows a full path** — a rename records only
the new name (all `UpdateFolderProperties` takes), so the column showed a bare leaf beside a fully-qualified source;
it is now composed with the source's parent at render time, which also fixes the runs already recorded. **(6) The
Normalization Review's change list is summarised by default** — counts by kind and a tally of *why* (extra spaces
×n, non-breaking space ×n) with a **Show all** toggle for the full table; a real cull changes hundreds of names and
the table buried the Confirm control under a wall of paths, which is the shape that gets confirmed unread. **(7)
Pending name conflicts are grouped by the decision they pose** — identical documents (every version matches, so a
duplicate delete loses nothing), duplicate names with differing content (rename unless certain), and folders
(rename or merge) — rather than listed in plan order, which made the operator re-derive the same question per card.
 **2026-08-17 (rev 26):** the Step 8b **execution** view got the same treatment rev 25 gave the pre-execution review.
It now leads with a **summary** — progress bar, applied/failed/pending counts, and per-kind progress (folders vs
documents, which matter separately because a folder rename repaths its pending descendants) — behind a **Show detail**
link that expands the unchanged per-item table. The detail is collapsed by default and **auto-opens once** if the phase
stops with failures, since there the list is a work queue rather than reference material. **Confirm & continue to
archival** moved from above the table to a footer **after** the content, paired with a status line explaining its
state, matching the Step 6–7 review, the Normalization Review and the purge control; previously the decision to move
on sat above the evidence for it (`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 27):** the audit surfaces were labelled "Tailing" but were not tailing. Two independent causes, both fixed.
**(1)** They polled **only while the run was `Running`** (the 2026-08-13 rule) — written before any of the work that happens
at a *stopped* run. A rollback runs against a `Failed` run; the move-failure retry, the normalization retry, the
empty-subtree prune and the Step 12 purge all run while the run sits at `AwaitingInput` or `Failed`. So the trail was live
in the one state where little was being appended and frozen in the states where the operator was actively causing rows to
be written; the only way to see them was to leave the run and come back. Both surfaces now tail in any non-terminal state,
matching the definition of "live" the Document move failures panel already used. **(2)** The full trail's live tick
refreshed the filtered **count** only, deliberately, to avoid swapping rows mid-read — which lit up a new last page whose
contents never appeared. It now refetches the current page: under the default oldest-first sort a refetch of any page but
the last returns identical rows, so nothing being read moves, and the last page grows as the run works
(`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 28):** rev 27 was still wrong, for the same underlying reason: it inferred "is the run working?" from the run's
status, just from a longer list of statuses. A **rollback runs against a `Cancelled` run** — terminal by status, busy in fact,
streaming per-item progress — so the audit surfaces sat idle while the Run progress bar visibly moved. Liveness is no longer
inferred from status at all. Both audit surfaces **always poll and adapt their speed** (5s while the trail is growing, 15s when
it is not), detecting the work from the trail itself; the "Tailing" chip reflects the fast speed. The status is now only a hint
that biases the initial speed, so getting it wrong costs one 15s tick rather than a frozen view — a bounded, self-correcting
failure, which is what the previous two designs lacked. The **Run progress** panel's live chip likewise now keys off "the hub
pushed a message recently" rather than `status === 'Running'`. The run **status badge deliberately still reads `Cancelled`** and
does not animate: the run's disposition is not a claim about the present moment, and pulsing it would assert the run is running
(`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 29):** the run view named the pipeline's steps the way the pipeline names them — "Cleanup (step 11)" —
which is accurate and nearly useless: **Cleanup** covers deleting the emptied source folders (a soft delete, recoverable) *and*
destroying them and the archive library for good, and nothing on screen said which was running. Two changes. **(1) Steps have
operator-facing labels** (`theme/steps.ts`): Step 11 is **"Empty folder cleanup"**, Step 12 **"Purging deleted items"**, and
similarly across the pipeline; used in the run header, the Run progress panel, and the phase stepper's description for the
current phase. The phase keeps its own name — the stepper is phase-grain — but a phase whose steps do materially different
things now names the step it is actually on. **(2) The progress messages carry an `operation`** — the individual **pass** the
count belongs to (`PhaseStarted`/`ProgressUpdated`, values in `Hubs/Messages/RunOperations.cs`). A step is not one pass: Step 11
runs "Deleting empty folders" and then "Pruning empty subfolders"; Step 12 destroys the archive library and then the source
folders Step 11 deleted; a rollback runs three. Each restarts the item count, so the bar fills more than once per step — which
previously looked like a bug and is now simply two named operations. Optional and additive, so client and server interoperate at
either version (`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 30):** Step 11's pre-delete guard refusal ("still has N subfolder(s)") is no longer recorded as a **failure**.
It is the designed first outcome for any folder whose subtree Step 4 never evaluated — the second pass prunes the empty children
and the delete succeeds — so a completely healthy cleanup was filling the operator's activity feed with red rows that the run
itself cleared seconds later, which is how you train someone to stop reading failures. The attempt is still audited (the sequence
deferred → pruned → deleted is what an auditor wants) under a new outcome **`Deferred`**, with the reason in `Detail` rather than
`ErrorMessage`, and no failed-item push. The folder row keeps its `Failed` status and reason, so the handoff to the prune pass and
the visibility of an *unresolved* deferral are both unchanged. Separately, a guard refusal no longer drags the folder's parent
through the reactive rule handling: relaxing a folder rule cannot make a live subfolder disappear, so what used to be a rule read
plus — where the parent disallowed folder deletes — a relax, a retry the guard refused again, and a restore, is now skipped
outright, removing needless mutations of the customer's folder rules (`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 31):** the library and folder pickers (the new-run source picker, the Step 8/9 archive-destination picker, and the shared folder browser inside both) now show **placeholder rows** while a listing loads, instead of collapsing to a single "Loading…" line and re-expanding. Every navigation — opening a folder, walking back up a breadcrumb, switching library — was resizing the control and moving everything below it, which in the modal means the buttons walk up and down the screen between clicks. The placeholder block is held at the size of the **last listing that loaded**, so moving between sibling folders keeps the control at roughly its current height; the first load uses a middling default. Presentation only — no change to what is fetched or when (`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 32):** the same pickers now also **hold their list height while the filter box is used**. Narrowing thirty folders to two shrank the list by a few hundred pixels, so the controls below it jumped up under the cursor — and back down on a backspace. The list keeps the height it had **unfiltered** (measured, and clamped to its own scroll cap so a long scrolling list can't reserve its whole content height), and the "no matches" message now renders *inside* that reserved box rather than replacing it, so filtering down to nothing holds the height too (`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 33):** the Start-a-run form was reordered and labelled. The **year-end cutoff moved above the source picker** (it was below it, where a long library list pushed it off the bottom of the modal) and gained a description of what the date actually does. The source picker gained a **required label** — *Library or folder to cull*, with the same asterisk the cutoff carries; without one it read as an optional extra rather than the second half of a two-part decision — and a **description under the Library/Folder tabs** saying what each selects, since that choice decides how much of the repository the run is allowed to touch (`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 34):** the shared folder browser's navigation was consolidated. The **filter/search box now sits above the breadcrumb** — the breadcrumb is the browser's address bar and belongs directly above the list it addresses, where previously the search box separated the two — and the separate **"Change library" link became part of the breadcrumb row** as an **up-folder icon button**. That button is one control with two meanings, as in any file manager: up one level while there is a level to go up, and, at the library's root, back out to the library list. It is disabled where neither applies, and its tooltip names the destination ("Up to 2019", "Back to the library list"). Applies to both callers — the new-run source picker and the Step 8/9 archive-destination picker (`decisions/log.md` [2026-08-17]).
 **2026-08-17 (rev 35):** the **phase log moved into the phase stepper's card**, behind a closed-by-default **Phase timeline** disclosure, and its own card at the bottom of the run view was removed. The log is a phase-grain timeline — started / completed / failed, with a timestamp — and the stepper is already the page's timeline widget drawn from the same facts; as a separate card it was a table nobody works with, permanently occupying an active run and pushing the panels that *are* worked with further down. Nothing about it shows on an active run unless asked for: no timings on the face of the stepper, the disclosure closed. A failed phase still surfaces without it — the stepper renders that phase red, and the failure itself appears in the panel that owns it. Its rows now name each step the way the rest of the view does ("Empty folder cleanup", not "Cleanup / 11") (`decisions/log.md` [2026-08-17]).
 **2026-08-18 (rev 36):** **Re-run from Step 1** now clears the previous attempt's derived state before rewinding. The run keeps its id, so the abandoned attempt's **Document Register exports** (every pinned before/after snapshot plus the on-demand export) previously presented as the new attempt's — an operator diffing "before" against "after" would have been comparing two different runs. Found while fixing that: the Step 8 **rename plan** and **name-conflict** rows carried over too, and Step 8a only plans when no rename rows exist, so a re-run skipped planning and re-applied the *previous* plan against the current library — a correctness bug, not a display one. All three are now cleared in one transaction. The **operation audit trail and phase log are deliberately kept**: they record what the previous attempt did in MAGIQ and the rollback that made the run re-runnable, and only re-derivable state is cleared. The clear runs *before* the rewind, so a failure leaves the run terminal and still re-runnable rather than stuck `Running` with stale state (`decisions/log.md` [2026-08-18]).
 **2026-08-18 (spec rev 37):** the Step 8 review card was **re-laid-out onto the same skeleton as the Step 8b execution panel** (rev 26) — header counts beside the title, one description, a bounded summary, the *Show all* disclosure, then the footer — so the two Step 8 screens an operator sees back-to-back share one information architecture. Four specific fixes: the "a downloadable copy is in the Document Register" note was **pinned opposite the headline count** in a `space-between` and wrapped into it at any narrow width (it now sits under *Show all*, with which it shares a purpose); the four counts were **prose, not figures** (`Label N` inline, label-first, at body weight — now number-first `Stat`s on one inset panel, destructive counts coloured only when non-zero); the reason tally's bare "Because of" gained a **real label**; and both states' hand-rolled footers were extracted to one shared **`ReviewFooter`**, with the conflict state's impact tally moved **above** its cards so summary → detail → action holds in both. The per-conflict cards and the full change table are unchanged — those are a working surface, dense because the decision is (`decisions/log.md` [2026-08-18]).
 **2026-08-18 (spec rev 38):** the **Live activity** feed's outcome badge is now sized to the **widest outcome** (`Deferred`) rather than shrink-wrapping its own text, so every row's description starts at the same x. The description carries the item's full path and wraps over two or three lines on a deep folder, with the reason line wrapping beneath it — so a varying badge width made every row wrap at a different column, which a feed of mixed outcomes now hits routinely (a Step 11 guard refusal became `Deferred` at rev 30). The width derives from the outcome enum, so a new or renamed outcome stays covered, and it is a *minimum* width, so an under-estimate widens the badge rather than clipping it. The reason line's indent derives from the same constant. The full audit trail already sized its Outcome column against the whole enum universe and is unchanged (`decisions/log.md` [2026-08-18]).
 **2026-08-18 (spec rev 39):** the **Document Register** became one list of everything a run produces, and its items were renamed and described. **(1)** The **deleted folder manifest** moved out of its own card at the bottom of the run view and into the register list — it is a downloadable record of what the run did to the repository, which is what that card is for, and having it elsewhere meant an operator looking for "the files this run produced" had to know two places. It differs mechanically (a synchronous CSV from its own endpoint, so no row count and never *Generating*), which a shared row model absorbs. **(2)** Every item now carries a **one-line description of what is in the file**, always visible — choosing between five near-identically-shaped CSVs previously meant already knowing the pipeline. **(3)** Titles now **name the artefact rather than the moment**: *Before (pre-run)* → **Starting register**, *After review (pre-normalization)* → **Reviewed plan**, *Name changes — before/after* → **Planned / Applied name changes**, *After (outcome)* → **Final outcome**, *On-demand* → **On-demand export**. The old labels were timestamps to decode — one said the same thing twice, another pinned a single file to two different points in the run — where the before/after pairing survives perfectly well in *planned/applied* and *starting/final*. Order follows the run's timeline, with the manifest between the final outcome and the on-demand export (a different artefact, not a later one), and the purge confirmation now names the Document Register rather than "this page" (`decisions/log.md` [2026-08-18]).
 **2026-08-18 (spec rev 40):** two new records joined the Document Register — **Archived documents** (`GET /runs/{runId}/documents/archived/export`, every document Step 10 moved into the archive with the path it came from and the path it landed at) and **Purged documents** (`GET /runs/{runId}/documents/purged/export`, every document Step 12 destroyed). The register described what the run planned and what the repository looked like, but nothing said what it did to the documents themselves; the deleted folder manifest covered only the structural half. Both derive on demand from the operation audit trail, like the manifest — no new snapshot kind, no schema change, no background job. The purged record is explicit about its grain: `DeleteDomain` bins the archive as a *single* entry, so MAGIQ confirms the destruction once at library level and never per document, making each row an inference the file states in its header alongside the confirmations it rests on. It deliberately lists nothing when the run was **rolled back** — a rollback returns every document and only then destroys the now-empty archive, leaving an audit trail indistinguishable from a real purge — and nothing when the only purge in the trail belongs to an earlier re-run attempt (`decisions/log.md` [2026-08-18]).
 **2026-08-18 (spec rev 41):** the SPA gained **addressable pages** — `/runs`, `/runs/{runId}`, `/queries` and `/settings`, with `/` resolving to the runs list. The shell previously held its current page in React state, so the whole app lived at one URL: a refresh or a bookmark always landed back on the runs list, Back did nothing useful, and a run could not be linked to — "have a look at this run" meant "open the tool, go to Runs, find the row". Implemented as a hand-rolled History-API hook rather than by adding a routing library, since the SPA carries no routing or state library and there are four routes. Nothing was needed server-side: the API already served unmatched paths from the SPA entry point, on both IIS and Docker. Nav items and dashboard run rows are now real links, so middle-click, ⌘/Ctrl-click and "copy link address" work — and the dashboard's rows, previously reachable only by mouse, gained a keyboard tab stop. The page segment matches case-insensitively so a pasted `/Runs/{id}` still opens the run rather than silently redirecting to the list (`decisions/log.md` [2026-08-18]).
 **2026-08-18 (spec rev 42):** the shared folder browser's order became **breadcrumb → filter box → folder list**, reversing the ordering set at rev 34. Top-down that reads *where you are* → *how to narrow it* → *what is here* — the order a file manager leads with, and the order the operator asks the questions in: orient first, then filter. Rev 34's case was adjacency (keep the trail beside the list it addresses), but the filter box is itself about the current location — its placeholder names it — so it sits comfortably between the two, and leading with the address is the stronger convention for a picker used against an unfamiliar library. The up-folder control keeps its place at the head of the breadcrumb row, which rev 34 got right (`decisions/log.md` [2026-08-18]).
 **2026-08-18 (spec rev 43):** **Step 12 now destroys the archive in chunks.** `DeleteDomain` bins the whole library as *one* entry (rev 24), so purging it was a single call that ran for many minutes and could only ever report `0/1` — during the one part of a run that cannot be undone, the tool looked hung. The step now runs three named passes: delete the archive's contents a folder at a time (**"Deleting the archive contents"**), purge those entries (**"Purging the archive contents"**), then `DeleteDomain` the emptied library and sweep up what is left (**"Purging the remaining deleted items"**). Chunks are chosen by **depth** — the shallowest level beneath the archive destination holding at least `ArchivePurgeChunkTarget` folders (default 25, preferring a shallower level over one exceeding 1,000 pieces, `0` disables) — because a `DeleteFolder` already takes a whole subtree in one server-side operation, so the choice is only how finely to slice, and one chunk per recorded folder would be twice the folder count in round-trips to say what a few hundred already say. Taking them all at one depth keeps chunks non-nesting and order-independent. The plan comes from the run's own `CleanupRunArchiveFolder` records, which it can afford to do because **chunking is an optimisation and never the guarantee**: whatever it misses is still inside the library when `DeleteDomain` runs and still swept up behind it. The one exception is a chunk purge that went **unanswered** — it is barred from the final sweep rather than fired at a service that may still be working through it. Deliberately **sequential** by default (`ArchivePurgeConcurrency`, default 1): concurrent destroys against one MAGIQ instance are unverified. The purged-document record's grain improves as a side effect — a confirmation per archive folder rather than one for the library — though still not per document, and the file says so. Found and fixed alongside: the **rollback** teardown compared a recorded archive path (`Archive/2019/Case`) with a reconstructed bin path (`\Archive\2019/Case`), so it matched nothing and left its archive folders in the recycle bin; both sides now fold to one comparison form (`decisions/log.md` [2026-08-18]).
 **2026-08-19 (spec rev 44):** four defects surfaced by a failing test suite, three of them behaviours the spec already claimed. **(1) The acronym pre-select cascade stopped at the wrong place.** Rule 2 protection propagates *upward*, so one post-cutoff document anywhere beneath a matched case folder marked that folder protected too — and the cascade skipped its walk entirely on that basis, so a single recent document in one subfolder silently un-selected the whole case folder. This is the 92%-left-behind defect the cascade was added to fix, reintroduced by the guard meant to keep the protected folder itself out of the selection. The walk now starts from **every** name-matched folder; the protected folder is still never selected (two independent checks already ensured that), it simply no longer stops the walk to its non-protected descendants. **(2) No CSV export carried a UTF-8 BOM**, though every one of them said it did and Excel needs it for the non-ASCII names Step 8 exists to handle: the encoder was configured to emit the BOM but the encoding method used never emits it. All three writers — the operation audit trail, the Document Register, and the deleted-folder/archived/purged records — now prepend it, and it is pinned by test in each. **(3) A pre-delete guard refusal reached through a retry was still audited as a red `Failed` row** (see Step 11 above): rev 30 reclassified only the first pass, and the prune cycle runs the retry automatically, so the failure rows rev 30 removed came straight back on any run with a blocked folder. **(4) The prune's auto-skip was narrower than the spec described**, and stays that way deliberately — see "What it *proves* it cannot fix" above. The remaining failures were stale test expectations, not defects: three had been written against pre-rev-30/pre-2026-08-14 behaviour, and one compared a call record against a mis-shaped tuple (`decisions/log.md` [2026-08-19]).
