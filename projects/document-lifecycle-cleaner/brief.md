## Client
NATA

## What this is
A yearly automated process to cull documents and folders from MAGIQ Documents based on a calendar year-end cutoff date. Targets a specific facility identified by folder naming conventions (acronyms).

## Spec
See `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.2.docx`. Current version is draft. Eleven open questions remain — do not begin architecture until the blocking ones are resolved (see risks).

## Stack
- Frontend: React (review + confirmation UI, Steps 6 & 7)
- Backend: .NET API
- Data: SQL queries, system-level configurable
- Integration: MAGIQ Documents library/folder/document APIs

## Q2 scope
Resolve open questions → finalise spec → design React UI → design .NET API surface → implement.

## Key constraints
- SQL queries must be configurable at the system level (no hardcoded schema)
- Deletable folder acronyms are pre-locked in the UI — NATA cannot override them
- Deletion is blocked until folder validation passes (delete constraint rule)
- Archive library must not be purged until Robocopy is verified (verification gate)
- Purge is a background system process, not a direct user action

## Open questions (blocking)
Track resolution in `notes.md`. The two that block everything else:
1. Who sets the specified date and how?
2. Does folder protection extend to the full ancestor hierarchy or immediate parent only?

## Related decisions
Reference `decisions/log.md` — do not duplicate entries here.