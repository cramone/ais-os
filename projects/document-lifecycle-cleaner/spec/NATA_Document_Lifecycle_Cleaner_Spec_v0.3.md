# NATA — Document Lifecycle Cleaner
### Specification v0.3

_Last updated: 2026-05-05_

> **Status:** Draft — all questions resolved. Ready for architecture.

---

## Goal

Delete documents and folders with a modification date less than or equal to a specified calendar date, and remove empty folders pertaining to a particular facility based on folder naming conventions.

---

## Context

NATA requires a yearly clean culling and deletion of all documents whose modification date falls on or before a specified calendar year-end date, as well as the removal of empty folders associated with a particular facility identified by acronym. This process is intended to be repeatable and automated on an annual basis.

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

This step also captures NATA's decisions about which documents or document categories should be retained regardless of modification date.

**Resolved (display columns):** Implement the minimum recommended column set at launch, with the UI designed to support additional columns in future iterations without a redesign. Minimum columns are to be determined during UI design — candidates include folder path, document count, and date range.

**Resolved (document preservation rules):** No document types, statuses, or categories require unconditional preservation. All documents are subject to the standard date cutoff rule.

---

### Phase 3 — Archival

#### Step 7 — Confirm and execute folder deletes (React UI + .NET API)

The React UI presents a confirmation screen listing all folders selected for deletion. NATA must explicitly approve before the .NET backend API executes any deletions.

The system validates all selected folders against the delete constraint (Rule 4) before any delete is executed. If any folder is in a protected state, the process halts and reports which folders are blocking. Deletion cannot proceed until all blocking folders are resolved or deselected.

#### Step 8 — Create a new archive library in MAGIQ Documents

Create a new, temporary library within MAGIQ Documents to hold the candidate documents during the archival window.

**Resolved:**
- **Library naming convention:** `{LibraryName} - Archive`, where `{LibraryName}` is the name of the source library. For example, a source library named `Facilities` produces `Facilities - Archive`.
- **Existing library:** If a library matching the target name already exists, it is used as-is rather than creating a new one.
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

**Resolved:** This step is performed manually by NATA and is **out of scope** for this system. The verification gate (file count and total size comparison) is also NATA's responsibility.

> The verification gate originally planned to block Step 12 is removed from the automated flow. NATA must confirm Robocopy is complete before proceeding to Step 12.

#### Step 12 — Delete and purge the archive library

Delete the archive library from MAGIQ Documents. The purge — permanent removal from the system — is implemented as a system background process that executes automatically following the delete.

**Resolved:**
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

5. **Archive first** — The archive library must not be deleted (Step 12) until NATA has confirmed that the Robocopy archive is complete (out-of-scope, manual step).

---


## Open Questions

| # | Step / Section | Question | Status |
|---|---|---|---|
| OQ-1 | Step 6 UI | Display columns — minimum set at launch, expandable later | ✅ Resolved |
| OQ-2 | Step 6 | Document types/categories requiring unconditional preservation | ✅ Resolved: none |
| OQ-3 | Rule 2 / Step 4 | Folder protection scope | ✅ Resolved: full ancestor hierarchy |
| OQ-4 | Step 8 | Archive library naming convention | ✅ Resolved: `{LibraryName} - Archive`; reuse if exists |

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
| OQ-1 | Step 6 UI display columns? | Minimum recommended set at launch; UI to be designed for extensibility |
| OQ-2 | Document types requiring unconditional preservation? | None |
