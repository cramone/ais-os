# Decision Log — Repo House Keeping

## D-001 — Destination repo prefix `mgq-` (2026-10-01)
**Decision:** Every repo created in the springbrooksoftware enterprise must be named `mgq-<name>`.
**By:** Chase Ramone
**Notes:** Rename happens at migration time (target repo name), not at source. A missing prefix alone doesn't trigger `update-then-migrate`. The rest of the naming convention (casing, separators) is still TBD.

## D-002 — Project team (2026-10-01)
**Decision:** The team is Chase Ramone (lead) and Karen Barton.

## D-003 — Karen Barton advisory only (2026-10-01)
**Decision:** Karen Barton is an advisor only. She gets no access to source or destination repos and no GitHub Enterprise seat at this stage. This refines D-002.
**Impact:** Chase is the only person who runs migrations and holds enterprise admin rights.

## D-004 — Add magiq.visualstudio.com as a source (2026-10-01)
**Decision:** Add https://magiq.visualstudio.com as a fourth source, a legacy ADO org. Its register `source` value is `magiq-vs-ado`.
**Notes:** This org is separate from dev.azure.com/MAGIQSoftware (`magiq-ado`). If magiq.visualstudio.com turns out to redirect to dev.azure.com/magiq, it's still a separate org from MAGIQSoftware.

## D-005 — Extensions (magiq-vs-ado): archive locally, hold, delete if unused (2026-10-01)
**Decision:** Don't migrate the `Extensions` repo (register id 1, 9 MAGIQ.Extensions.* packages) for now. Mirror it to `archive/magiq-vs-ado/Extensions/` and set disposition to `hold`.
**Exit:** If no consumers are found once inventory is complete, change disposition to `decommission`. Delete only after Chase confirms in writing. If consumers are found, move the code for the affected area into a new `mgq-` repo.
**Tracking:** `spec/package-dependencies.csv` (one row per package) and `archive/magiq-vs-ado/Extensions/ARCHIVE.md`.

## D-006 — Extensions archived as a zip snapshot (2026-10-01)
**Decision:** Archive `Extensions` as a zip of `master` (its only branch), downloaded from the ADO UI, instead of a full git mirror.
**Context:** The magiq org has no package feeds. The repo has a single branch.
**Trade-off:** Git history is lost (R-004). Accepted because the repo is legacy and history has no expected value.

## D-007 — Extensions deleted at source (2026-10-01)
**Decision:** Chase deleted the Extensions project from magiq.visualstudio.com. Register id 1 is now `disposition=decommission`, `migration_status=decommissioned`.
**By:** Chase Ramone. Deleting it himself is his written confirmation.
**Deviation from D-005:** the source was deleted before the consumer scan. Accepted because the code is in `Extensions.zip` (verified hash), and any consumers restore from the infoxpert feed, not this repo. The package checks continue under R-001.

## D-008 — 30-day hold on magiq.visualstudio.com org (2026-10-01)
**Decision:** Keep the now-empty magiq.visualstudio.com org open until 2026-10-31. Delete it after that if no issues come up.
**Reminder:** one-time scheduled task `delete-magiq-visualstudio-org` fires 2026-10-31. Deleting still needs Chase's written confirmation.

## D-009 — Disposition vocabulary change + 2-location backup flag (2026-10-02)
**Decision:** (1) Remove disposition `migrate-then-archive`. (2) Rename `hold` to `pending`; all 82 existing `hold` rows were converted. (3) Add register column `backup_2loc` (`yes` / `no` / blank) for rows that are `decommission`, `archive-in-place` or `decommissioned`: records whether a 2-location backup has been done. (4) Triage board column order: pending, update-then-migrate, archive-in-place, migrate, decommission.
**By:** Chase Ramone
**Notes:** `tbd` remains valid and shows in the pending column on the board. Extensions (id 1) set to `backup_2loc=yes` because T-01 (copy zip to second location) is marked done. Historic entries (D-005 etc.) still say "hold" — they're append-only. Cowork project instructions (system prompt) still list `hold`; update them to match.

## D-010 — `backup_2loc` gains `not-required` (2026-10-02)
**Decision:** Add value `not-required` to register column `backup_2loc` for decommission / archive-in-place rows where the repo is empty or completely obsolete, so no 2-location backup is needed. It counts as satisfying the backup gate. Put the reason in notes.
**By:** Chase Ramone

## D-011 — Dedicated confirmation fields `confirmed_by` / `confirmed_date` (2026-10-02)
**Decision:** Add register columns `confirmed_by` (default `Chase Ramone`, overridable) and `confirmed_date` (YYYY-MM-DD) on every repo row. They replace the dashboard's "Record written confirmation" note-append. A decommission counts as confirmed only when `confirmed_date` is set. Changing a repo's disposition clears both fields, because a confirmation belongs to a specific decision.
**By:** Chase Ramone
**Notes:** Extensions (id 1) back-filled as confirmed by Chase Ramone on 2026-10-01 (D-007: he deleted the project himself). No other rows were back-filled.
