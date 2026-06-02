# Cross-Session Notes
_magiq-media · Remediation loose ends and deferred fixes_

Add entries here when a change in one session has a known spillover into a file outside that session's scope.
Review and resolve after all sessions are complete.

---

## Pending

_(none)_

---

## Resolved

### [Session 1 → ChangeRequests] R-03: `submit-for-review` → `submit` in CR-1
**Source:** Session 1 — R-03 scope includes "CR-1 refs" but ChangeRequests `business-scenarios.md` is outside Session 1's file scope.
**Action:** In `spec/contexts/ChangeRequests/business-scenarios.md`, find all occurrences of `POST /items/{id}/submit-for-review` and replace with `POST /items/{id}/submit`. Check step text and sequence diagrams.
**Status:** Resolved — SPEC-2 (2026-05-16). All occurrences replaced in step text and sequence diagrams.

---

### [Session 8 → MediaItem projector] Cascade behaviour on AssetArchived / AssetDeleted
**Source:** Session 8 — R-29 cascade decision: archiving or hard-deleting an asset does NOT auto-unassign it from its MediaItem role. The MediaItem is left with an orphaned `assetId` reference.
**Action:** When implementing the MediaItem read model projector, it must handle `AssetArchived` and `AssetDeleted` events from the Asset stream and update the MediaItem role slot to surface an inaccessible-asset state (e.g. `assetStatus: "Archived"` or `"Deleted"` on the role entry). Confirm this is the intended UX before the projector is built — if the UI needs to warn on orphaned role slots, the read model must carry enough state to do so.
**Status:** Resolved — PROJ-5 / PROJ-6 (2026-05-16). `AssetDetailProjector` updated to handle `AssetArchived` and `AssetDeleted`; `hasAccessibleAssets` flag defined on MediaItem read model. Cascade does NOT auto-unassign; role slot carries `assetStatus` to surface inaccessible-asset state to UI.
