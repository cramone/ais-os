# document-lifecycle-cleaner

## Project Overview

Yearly automated process to cull documents and folders from MAGIQ Documents based on a calendar year-end cutoff date. Targets a specific facility identified by folder naming conventions (acronyms). Client: NATA.

**Current status:** As-built, plus one specified-not-yet-built phase. Epic 34120 is implemented and merged — the archival/cleanup pipeline, the React SPA, dual IIS/Docker hosting, and the operator/admin surfaces. The spec (`spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`, aligned to the repo 2026-08-05) describes the system as built. The **Phase 3 — Name Normalization (Step 8)** phase is now implemented in the working tree (`decisions/log.md` [2026-08-05]): SOAP Get/Update Folder+Document ops, `RunPhase.Normalization`, `dbo.CleanupRunRename` + `EnteredNormalization` audit-lock (migration `0004`), the `RenamePlanner` + `ExecuteNormalizationAsync` phase, and confirm→normalization→archival chaining. **Step numbering:** renumbered so nothing collides with Normalization — Normalization = Step 8, Archival = Steps 9–10, Cleanup = Steps 11–12 (`decisions/log.md` [2026-08-05]). Renames address items by their current (raw) path and repath pending descendants after each folder rename. Active work is the deferred/post-MVP backlog (`deferred-work-plan.md`), the folder delete-rule handling, the name-normalization phase, and the **operation audit trail + before/during/after Document Register (CSV)** (all `decisions/log.md` [2026-08-05]).

## ADO Board
Project: **Documents** (MAGIQSoftware org). Epic **#34120** — *Document Lifecycle Cleaner — NATA* (8 Features, 17 User Stories, 49 Tasks; created 2026-07-13). Repo: `DocumentLifecycleCleaner`. Work items tagged `document-lifecycle-cleaner` and per-branch tags.

## Stack

- **Frontend:** React (review + confirmation UI — Steps 6 & 7)
- **Backend:** .NET API
- **Data:** SQL queries, system-level configurable
- **Integration:** MAGIQ Documents library/folder/document APIs

## Key Constraints

- SQL queries must be configurable at the system level (DB-backed `ConfiguredQuery` store, no hardcoded schema)
- Deletable folder acronyms **pre-select** folders for deletion in the UI; the operator may deliberately override an individual pre-selection. Folder **protection (a post-cutoff document) always wins** — a protected folder is never deletable
- Deletion is blocked until folder validation passes (delete constraint rule)
- Purge is a background system process, not a direct user action
- A folder rule that disallows deletes (a `Move` is a copy + delete) is handled reactively — read the live rule, temporarily relax it on the one folder, retry, then restore it (`decisions/log.md` [2026-08-05])
- **Name normalization (Step 8, specified/not-yet-built):** the SOAP `Move`/`CreateFolder` can't handle names with a double space (which the desktop UI allows), so a pre-archival phase renames the offending **source** docs/folders in place (doubled whitespace → single space) via `UpdateFolderProperties`/`UpdateDocumentProperties`. Every rename is recorded, and **once the phase begins the run becomes an audit — it can no longer be deleted, only archived** (spec Rule 7; `decisions/log.md` [2026-08-05])

## Blocking Open Questions (all resolved — historical)

Both were resolved long ago; architecture and implementation are complete. Retained for the record:

1. ~~**Who sets the specified date and how?**~~ — ✅ Resolved: the operator picks the cutoff date **and** source library at run creation (per-run inputs on the `CleanupRun`).
2. ~~**Does folder protection extend to the full ancestor hierarchy or immediate parent only?**~~ — ✅ Resolved: full ancestor hierarchy protected (maximum protection).

Full resolution history is in `notes.md` and `decisions/log.md`.

## Scope

Delivered: spec finalised → React UI + .NET API implemented → Epic 34120 shipped (as-built Steps 1–11). Current focus: the deferred/post-MVP backlog (`deferred-work-plan.md`), the folder delete-rule handling, and the specified-not-yet-built **Name Normalization** phase (Step 8; renumbers the spec to 12 steps).

## File Map

| File | Purpose |
|------|---------|
| `brief.md` | Project summary and constraints |
| `notes.md` | Open question resolutions and session notes |
| `risks.md` | Risk register |
| `tasks.md` | Task tracking |
| `dev-context.md` | Cross-project working context: 3-repo topology, settled architecture, the FastEndpoints→command/query→context pattern, branch/PR protocol |
| `delivery-plan.md` | Epic 34120 ordered branch plan — 17 stories → branches, per-branch scope, dependencies |
| `decisions/log.md` | Architecture and design decisions (append-only log) |
| `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` | Spec — source of truth (active, markdown) |
| `spec/dev-spec.md` | Developer specification — API catalogue, data model, config schema, SignalR contract, component map, sequence flows, error contracts |
| `references/adrs/ADR-001-hangfire-background-engine.md` | ADR: Hangfire as pipeline engine |
| `references/adrs/ADR-002-cleanup-run-state-machine.md` | ADR: CleanupRun persisted state machine |
| `references/adrs/ADR-003-multi-target-hosting.md` | ADR: IIS default + Docker supported |
| `references/adrs/ADR-004-magiq-integration-soap-dapper.md` | ADR: MAGIQ integration via SOAP + Dapper |
| `references/adrs/ADR-005-single-application-database.md` | ADR: Single dedicated app database |
| `references/adrs/ADR-006-authentication-two-ticket-model.md` | ADR: MAGIQ auth piggybacking + two-ticket model |
| `references/adrs/ADR-007-process-ticket-persistence.md` | ADR: Process ticket persisted in app DB |
| `references/adrs/ADR-008-react-spa-from-wwwroot.md` | ADR: React SPA served from API wwwroot |
| `references/adrs/ADR-009-command-query-dispatch.md` | ADR: Command/query dispatch via FastEndpoints built-in bus |
| `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.3.md` | Spec — previous version (archived, markdown) |
| `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.2.docx` | Spec — previous version (archived) |

## Decisions

All architecture and design decisions go in `decisions/log.md`. Do not duplicate entries in `brief.md` or here.

---

## Memory System

**MEMORY SYSTEM**

This folder contains a file called `MEMORY.md`. It is your external memory for this project — use it to bridge the gap between sessions.

**At the start of every session:** Read `MEMORY.md` before responding. Use what you find to inform your work — don't announce it, just be informed by it.

**Memory is user-triggered only.** Do not automatically write to `MEMORY.md`. Only add entries when the user explicitly asks — using phrases like "remember this," "don't forget," "make a note," "log this," "save this," or "create session notes." When triggered, write the information to `MEMORY.md` immediately and confirm you've done it.

**All memories are persistent.** Entries stay in `MEMORY.md` until the user explicitly asks to remove or change them. Do not auto-delete or expire entries.

**Flag contradictions.** If the user asks you to remember something that conflicts with an existing memory, don't silently overwrite it. Flag the conflict and ask how to reconcile it.

---

> When the user asks to create a new subfolder, use the **subfolders** skill. It handles the full interview, CLAUDE.md and MEMORY.md creation, identity overrides, and memory isolation.
