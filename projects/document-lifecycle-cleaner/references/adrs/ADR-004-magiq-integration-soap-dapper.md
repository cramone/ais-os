# ADR-004 — MAGIQ Documents Integration: SOAP + Dapper

**Date:** 2026-07-13  
**Status:** Accepted

---

## Context

The application integrates with MAGIQ Documents for two distinct purposes:

1. **Library/folder/document operations** (create archive library, move documents, delete folders, purge) — these are domain-level operations that the platform exposes.
2. **Candidate retrieval and folder-path resolution** (Steps 1, 2, 5) — these are reporting-style queries that must be system-level configurable raw SQL, because the MAGIQ Documents schema may change and queries must be updatable without code deployment.

The spec explicitly states: queries for Steps 1, 2, and 5 are stored in `appsettings.json` and can be updated independently of code deployments when the schema changes.

---

## Decision

Integrate MAGIQ Documents via **two paths**:

### Path 1 — SOAP web service (`srv.asmx`)

Used for all library/folder/document operations:
- `AuthenticateUser` — authentication
- `CreateDomain` — create archive library (Step 8)
- `Move` — move document to archive (Step 9)
- `DeleteFolder` — delete empty folders (Step 10)
- `DeleteDomain` — delete archive library (Step 11)
- `GetRecycleBinContent` — retrieve recycle bin items (Step 11)
- `PurgeRecycleBinItem` — permanently remove item (Step 11)

Consumed via a generated SOAP proxy or typed `HttpClient` wrapper. Both SOAP 1.1 and 1.2 are supported by the endpoint.

### Path 2 — Direct SQL via Dapper

Used for the pre-configured queries (Steps 1, 2, 5) against the MAGIQ Documents database. Dapper executes the configured SQL and maps results without imposing an ORM model or schema assumptions.

Connection string for the MAGIQ Documents database is separate from the app database connection string (see ADR-005).

---

## Consequences

- Neither path has Windows-specific dependencies — Linux container remains viable (see ADR-003).
- Dapper suits the raw, configurable-SQL requirement — adding an ORM over a third-party schema would impose model assumptions the spec explicitly avoids.
- SOAP proxy must handle the `<response success="true/false" error="..." />` response contract — callers must check `success`, not just HTTP status (all calls return HTTP 200).
- Direct SQL access requires the app to hold a connection string to the MAGIQ Documents database — treat as a privileged credential in configuration.

---

## Amendment — 2026-08-05: folder delete-rule handling

The SOAP operation set (Path 1) gains two operations, and a new consequence is recorded. Decision detail in `decisions/log.md` [2026-08-05]; the original decision is otherwise unchanged. (The operation list above was the Step-8–11 starting set; later stories also added `CreateFolder`, `FolderExists`, `DocumentExists`, `GetDomains`, `GetFolders`, `UserExists`, and `isValidTicket` — this amendment does not restate those, only the delete-rule additions.)

- **`GetFolderRules`** — read a folder's rules (captured verbatim as a `FolderRuleSet`).
- **`SetFolderRules`** — write a folder's rules (the `<Rules>` fragment as **nested XML**, `ApplyToTree=false`). _(Amended 2026-08-10: originally described as an "escaped `<Rules>` fragment"; verified against training that MAGIQ reads the **child `<Rules>` markup** and silently ignores an escaped string — an escaped payload returned `success="true"` but never relaxed the rule, so the retried `Move` kept failing. Corrected in `MagiqSoapClient.SetFolderRulesAsync`; see `SOAP-VERIFICATION-34525.md` op 21 and `decisions/log.md` [2026-08-10].)_

**New consequence — `Move` is a copy + delete.** MAGIQ implements `Move` as a copy followed by a delete, so a source folder whose `DISALLOWDOCUMENTDELETE` rule is set fails the delete-half and the whole Step 9 move errors; likewise a Step 10 `DeleteFolder` fails when the **parent** folder disallows folder deletes (the parent governs child-folder deletion); and the **copy-half** can be blocked too — a rollback move-back into a document's original folder fails if that folder's `NewDocuments` rule disallows new documents. To keep the pipeline moving, a reactive `IFolderDeleteRuleGuard` sits around each move/delete: on a failure it reads the folder's **live** rules via `GetFolderRules`, and only if the relevant rule is blocking does it flip that one rule to `allows` via `SetFolderRules`, retry once, then restore the exact original in a `finally`. Reading live (not a snapshot from identification) is deliberate — it honours a rule changed mid-run. The rule it relaxes depends on the site: `DocumentDeletes` on the source folder (Step 9), `FolderDeletes` on the parent (Step 10), `NewDocuments` on the destination folder (rollback move-back). The rule set is modelled by the `FolderRule` enum (renamed from `FolderDeleteRule` once it grew to cover the non-delete `NewDocuments` case). The Step 4/1 candidate queries additionally surface the delete restriction as review flags (`DocumentDeleteBlocked`/`FolderDeleteBlocked`), but those are informational only; the guard is the source of truth at execution time.

**Audited (2026-08-05).** A relax/restore mutates the customer's live folder rules, so it is recorded in the operation audit trail (`CleanupRunOperation`, ADR-002 amendment): `RetryWithRuleRelaxedAsync` takes optional `onRelaxed`/`onRestored` hooks that the executor uses to write a `RuleRelax` row when the one rule is actually flipped and a `RuleRestore` row (Ok, or Failed if the folder is left permissive) after the `finally` restore. A restore failure — which already logs an error for manual attention — is now also a durable, queryable audit row.

**Assumption — the archive library has open, unrestricted folder rules (2026-08-05).** The guard is applied only to operations against **NATA's own (source / original) folders**, whose rules the customer controls: the Step 9 move's delete-half (`DocumentDeletes` on the source folder), the Step 10 folder delete (`FolderDeletes` on the parent), and the rollback move-back's copy-half (`NewDocuments` on the document's original folder). Operations against the **archive library** are deliberately **not** guarded — creating the archive folder structure (Step 9) and deleting the run-created archive folders during a rollback (`RemoveCreatedArchiveFoldersAsync`). The archive library is treated as fully open: the run creates it (`CreateDomain`) and its folders take permissive defaults, so no archive-side rule is expected to block a create or delete. If that ever stops holding — an administrator applies restrictive rules to the archive library, or the "choose an existing library" option (Step 8) points at a library that already carries rules — those archive-side operations would need the same guard treatment. Deferred until then rather than pre-emptively guarded.

---

## Amendment — 2026-08-05: name-normalization rename operations (double-space bug)

The SOAP operation set (Path 1) gains two operations to support the new **Name Normalization** phase. Decision detail in `decisions/log.md` [2026-08-05]; the original decision is otherwise unchanged.

- **`UpdateFolderProperties`**(`AuthenticationTicket`, `Path`, `NewFolderName`, `NewDescription`) — rename a folder level.
- **`UpdateDocumentProperties`**(`AuthenticationTicket`, `Path`, `NewDocumentName`, `NewDescription`, `NewUpdateInstructions`) — rename a document.

**Why.** The MAGIQ desktop UI permits a document/folder name containing a run of consecutive whitespace (e.g. a double space), but the SOAP service **collapses and trims whitespace** on `CreateFolder`/`Move`, so it cannot create or move an item whose name (or folder-path level) holds a double space — the whole archival `Move` errors. The workaround is a dedicated pre-move phase that renames the offending **source** items in place (doubled whitespace → single space) using the two ops above, addressing folder levels top-down (ancestors before descendants) then documents. Every rename is recorded as a permanent audit of the change made to NATA's live repository. These ops are used **only** against the customer's own source items during normalization; they are not part of the reactive rule guard. The exact path form the ops accept for a still-doubled source item is confirmed at integration against training (same `xsd:any`/behaviour class as ADR-011 / Story 34525).

> **Step renumber note.** Inserting the Name Normalization phase adds a new **Step 8** and renumbers the spec's archival/cleanup steps: Archival → Steps 9–10 (create library, move), Cleanup → Steps 11–12 (delete folders, purge). **All step numbers in this ADR and its earlier amendments refer to the pre-insertion (as-built code) numbering** — Step 8 create-library, Step 9 move, Step 10 folder-delete, Step 11 purge — which the shipped code still uses until the normalization phase is implemented. See `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`.
