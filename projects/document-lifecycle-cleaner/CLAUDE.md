# document-lifecycle-cleaner

## Project Overview

Yearly automated process to cull documents and folders from MAGIQ Documents based on a calendar year-end cutoff date. Targets a specific facility identified by folder naming conventions (acronyms). Client: NATA.

**Current status:** Spec v0.3 in progress (markdown). All blocking questions resolved 2026-05-05. Ready for architecture. Two non-blocking UI questions remain open (see notes.md).

## ADO Board
_Not yet assigned_

## Stack

- **Frontend:** React (review + confirmation UI — Steps 6 & 7)
- **Backend:** .NET API
- **Data:** SQL queries, system-level configurable
- **Integration:** MAGIQ Documents library/folder/document APIs

## Key Constraints

- SQL queries must be configurable at the system level (no hardcoded schema)
- Deletable folder acronyms are pre-locked in the UI — NATA cannot override them
- Deletion is blocked until folder validation passes (delete constraint rule)
- Robocopy (Step 11) is out of scope — NATA performs manually; verification gate removed from automated flow
- Purge is a background system process, not a direct user action

## Blocking Open Questions

These must be resolved before architecture begins:

1. ~~**Who sets the specified date and how?**~~ — ✅ Resolved: records manager / system admin (e.g. Madhuri)
2. ~~**Does folder protection extend to the full ancestor hierarchy or immediate parent only?**~~ — ✅ Resolved: full ancestor hierarchy protected (maximum protection).

Track all question resolutions in `notes.md`.

## Scope (Q2)

Resolve open questions → finalise spec → design React UI → design .NET API surface → implement.

## File Map

| File | Purpose |
|------|---------|
| `brief.md` | Project summary and constraints |
| `notes.md` | Open question resolutions and session notes |
| `risks.md` | Risk register |
| `tasks.md` | Task tracking |
| `decisions/log.md` | Architecture and design decisions (append-only log) |
| `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.3.md` | Spec — source of truth (active, markdown) |
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
