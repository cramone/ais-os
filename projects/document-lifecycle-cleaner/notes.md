# Notes

_Last updated: 2026-07-12_

---

## Remove Retry Animation During Archival
_Captured: 2026-07-12T00:00:00Z_

Remove the animation for "A retry is in progress — this list updates as documents are moved." whilst archival is running.

---

## Add Ignore as Valid Retry Action
_Captured: 2026-07-12T00:00:00Z_

Add ignore as a valid retry action to allow moving past a failed item.

---

## Force Checkout for Checked Out Documents
_Captured: 2026-07-12T00:00:00Z_

Add force checkout handling for the "This document is currently checked out" message.

---

## Remove Duplicate Failure Section Under Progress
_Captured: 2026-07-12T00:00:00Z_

Remove the duplicate failure section that appears under the progress indicator.

---

## Consolidate Snapshot CSV Exports at Document Register
_Captured: 2026-07-12T00:00:00Z_

Keep all snapshot CSV exports in the same location as the Document Register, named as follows:
- Document Register
- Pre Name Normalization
- Post Name Normalization

---

## No Immediate Retry After Archival Progress Completes
_Captured: 2026-07-12T00:00:00Z_

Ensure a retry is not performed immediately after the Archival progress completes on failed items.

---

## Nick is Cool
_Captured: 2026-07-12T00:00:00Z_

Nick is cool.

---

## Show Missing Settings
_Captured: 2026-07-12T00:00:00Z_

Show missing settings to the user.

---

## Wizard Steps Indicator Removed with Notifications
_Captured: 2026-07-12T00:00:00Z_

The wizard steps indicator gets removed when notifications are shown. Notifications need to be added as a step in the wizard steps indicator.

---

## Update dlc-process-walkthrough.html Step 9 Rollback
_Captured: 2026-07-12T00:00:00Z_

Update `dlc-process-walkthrough.html` to show Step 9 as allowing a rollback.

---

## Resolved — 2026-07-21

| Question | Resolution |
|---|---|
| Step 6 display columns | Folder path, document count, folder count, size |
| Step 8 archive library | Operator selects existing or creates new; optional subfolder in either case. No auto-naming convention. |
| Step 12 Robocopy confirmation | UI checkbox; confirming user + timestamp logged. No automated verification. |
| Step 6 document preservation sentence | Removed — contradicted OQ-2. OQ-2 stands: no unconditional preservation rules. |
| Process ticket expiry recovery | App auto-obtains new ticket on behalf of authenticated user if stored ticket has expired. |

---

## Open Questions

### ✅ Previously Blocking — Resolved 2026-05-05

**Folder protection scope**

Q7 and Q17 originally returned conflicting answers. Resolved in favour of maximum protection:

**Decision: A post-cutoff document protects its immediate parent folder AND the full ancestor folder hierarchy.**

Affects: Step 4 folder list logic, Step 5 SQL query, Step 6 UI display, and Rule 2 enforcement.

---

### ✅ Resolved — Step 6 UI (2026-05-05)

**Review UI display columns:** Minimum recommended columns at launch. UI must be designed to support additional columns in future iterations without a redesign.

**Document preservation rules:** No document types, statuses, or categories require unconditional preservation.

**Archive library naming convention (Step 8)**
Format is `{LibraryName} - Archive`, derived from the source library name. If a library with that name already exists, it is reused rather than created fresh.

---

## Resolved Questions — 2026-05-05

Answers provided by team. All incorporated into `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.3.md`.

| Question | Resolution |
|---|---|
| Who sets the specified date? | Records manager / system admin (e.g. Madhuri) |
| Who runs the process? | MAGIQ Documents system admin or power user |
| Additional fields beyond Document Register query? | None — SQL query output only |
| Excel spreadsheet retention period? | No retention period; for viewing purposes only |
| Excel spreadsheet — audit/compliance? | No — no additional fields, no approval required |
| Where is the spreadsheet saved? | Download provided to user; NATA decides where to save it |
| Nested folder handling | If parent becomes empty after child deletion, it can be deleted (criteria permitting) |
| Archive library name | `Facilities - Archive` (second library name TBC) |
| Library permissions | Full control for system admin / power user |
| Library creation audit | Not required |
| Move failure handling | Identify failed docs, continue with remaining, return to failed ones after |
| Robocopy (Step 11) | Out of scope — NATA performs manually |
| Holding period before purge | None — purge proceeds immediately after delete |
| Naming conventions list — final? | Current list is the list; NATA can add or remove acronyms (must be configurable) |
| Naming match — case-sensitive? | Yes, case-sensitive |
| Naming match — rule | Acronym must exist anywhere in the folder name (contains match) |
