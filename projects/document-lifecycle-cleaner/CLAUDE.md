# document-lifecycle-cleaner

## Project Overview

Yearly automated process to cull documents and folders from MAGIQ Documents based on a calendar year-end cutoff date. Targets a specific facility identified by folder naming conventions (acronyms). Client: NATA.

**Current status:** As-built. Epic 34120 is implemented and merged — the archival/cleanup pipeline, the React SPA, dual IIS/Docker hosting, and the operator/admin surfaces. The spec (`spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`, aligned to the repo 2026-08-07) describes the system as built. The **Phase 3 — Name Normalization (Step 8)** phase is now implemented in the working tree (`decisions/log.md` [2026-08-05]): SOAP Get/Update Folder+Document ops, `RunPhase.Normalization`, `dbo.CleanupRunRename` + `EnteredNormalization` audit-lock (consolidated into `0001_baseline.sql` — the interim `0002–0004` scripts were folded into the single baseline), the `RenamePlanner` + `ExecuteNormalizationAsync` phase, and confirm→normalization→archival chaining. **Step numbering:** renumbered so nothing collides with Normalization — Normalization = Step 8, Archival = Steps 9–10, Cleanup = Steps 11–12; `RunPhaseExecutor` emits exactly these numbers (`decisions/log.md` [2026-08-05]). Renames address items by their current (raw) path and repath pending descendants after each folder rename. **2026-08-10:** the Step 8 gate was widened from conflicts-only to **any name change** — the run pauses at the Normalization Review whenever the plan changes a name, the operator reviews the **full folder/document change list** (now on `GET …/normalization/plan`) and can **download it before → after (CSV/Excel)** via `GET …/normalization/changes/export`, then **confirms** (`POST …/normalization/confirm`) before 8b runs; only a zero-change plan auto-continues, and the audit lock still trips on the first executed 8b change (`decisions/log.md` [2026-08-10]; plan `normalization-change-review-plan.md`). **2026-08-10:** Step 10 gained an operator **move-failure retry** — a Document move failures panel lists unmovable documents and the operator retries them individually/selected/all (`GET`/`POST …/archival/move-failures[/retry]`); clearing the last failure **pauses after archival** (`AwaitingInput`) so the operator proceeds to cleanup explicitly via `POST …/archival/continue` rather than auto-chaining the irreversible purge (`decisions/log.md` [2026-08-10]; plan `move-failure-retry-plan.md`). Active work is the deferred/post-MVP backlog (`deferred-work-plan.md`) and the **operation audit trail + before/during/after Document Register (CSV)** polish (all `decisions/log.md` [2026-08-05]).

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
- **Name normalization (Step 8, implemented):** the SOAP `Move`/`CreateFolder` can't handle names carrying whitespace variants (double space, non-breaking `U+00A0`, and other Unicode spaces) or invisible format chars (zero-width, BOM, soft hyphen) — all of which the desktop UI allows and which are easily pasted from other documents. A pre-archival phase renames the offending **source** docs/folders in place (any Unicode whitespace → a single regular space, collapsed/trimmed; invisibles stripped — full lists in spec §"Whitespace normalization scope") via `UpdateFolderProperties`/`UpdateDocumentProperties`. The phase runs **8a dry run → conflict gate → 8b execute**: because normalizing can collapse two names onto one, a non-mutating dry run detects name conflicts, the run pauses (`AwaitingInput`) in the **Normalization Review** view for the operator to resolve each (rename / merge folders / keep-one-delete-other; safe rename pre-selected, destructive options confirmed + audited), re-analyses until clean, then executes. Every rename/merge/delete is recorded, and **once 8b executes its first change the run becomes an audit — no longer deletable, only archived** (spec Rules 7 & 8; `decisions/log.md` [2026-08-05, 2026-08-07])

## Blocking Open Questions (all resolved — historical)

Both were resolved long ago; architecture and implementation are complete. Retained for the record:

1. ~~**Who sets the specified date and how?**~~ — ✅ Resolved: the operator picks the cutoff date **and** source library at run creation (per-run inputs on the `CleanupRun`).
2. ~~**Does folder protection extend to the full ancestor hierarchy or immediate parent only?**~~ — ✅ Resolved: full ancestor hierarchy protected (maximum protection).

Full resolution history is in `notes.md` and `decisions/log.md`.

## Scope

Delivered: spec finalised → React UI + .NET API implemented → Epic 34120 shipped (as-built Steps 1–12, including the **Name Normalization** phase at Step 8). Current focus: the deferred/post-MVP backlog (`deferred-work-plan.md`) and audit-trail/register polish.

## File Map

| File | Purpose |
|------|---------|
| `brief.md` | Project summary and constraints |
| `notes.md` | Open question resolutions and session notes |
| `risks.md` | Risk register |
| `tasks.md` | Task tracking |
| `dev-context.md` | Cross-project working context: 3-repo topology, settled architecture, the FastEndpoints→command/query→context pattern, branch/PR protocol |
| `delivery-plan.md` | Epic 34120 ordered branch plan — 17 stories → branches, per-branch scope, dependencies |
| `normalization-conflict-gate-plan.md` | Implementation plan for the Step 8 conflict dry-run + resolution gate (API + SPA): current→target, data model, ordered branches B1–B8, test matrix, DoD |
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

## Spec Alignment — keep the spec in step with the repo

**The spec is the source of truth for *intent*; the repo is the source of truth for *behaviour*. They must not drift.** Whenever work in the `DocumentLifecycleCleaner` product repo changes behaviour that the spec describes — or adds behaviour the spec should describe — **the spec is updated in the same unit of work**, before the change is considered done. Treat a spec update as part of the definition of done, not a follow-up.

**What "the spec" means here:** the business/behaviour spec `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` (source of truth) **and** its developer companion `spec/dev-spec.md` (API catalogue, data model, config schema, SignalR contract, sequence flows, step numbers). A change usually touches one or both; check both. Architecture/design *rationale* still goes to `decisions/log.md` + `references/adrs/` — the spec records *what the system does*, the log records *why*.

**When a repo change lands (or is being designed), check it against the spec and reconcile:**

- **New or changed behaviour** — endpoint, pipeline phase/step, run state, rule, SOAP op, query contract, config/setting, UI flow, audit/log surface: update the matching spec section (and dev-spec section) so it describes the built behaviour. Bump the `_Last updated:_` date and add a one-line note under **History**.
- **Step/phase renumbering or renaming** — update every affected reference in both specs (status banner, phase table, step headings, flow diagrams, endpoint table, `RunPhase`/state tables). Grep for the old numbers so none are left stale.
- **Something the spec still calls "specified / not-yet-built" that has now shipped** — flip it to as-built and remove the not-implemented caveats.
- **A repo change that contradicts a spec rule or a decision** — do **not** silently rewrite the spec to match. Flag the conflict (surface it to Chase, and note it against `decisions/log.md`) and reconcile the intent first; only then update the spec.

**Keep this CLAUDE.md and `MEMORY.md` honest too** — if the status/step summaries above no longer match the repo, correct them as part of the same reconciliation.

If in doubt, a quick pass is: *did this change what the system does? → find the spec section that claims otherwise → fix it (or flag it) now.*

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
