---
id: MM-081
type: plan
project: magiq-media
workstream: WS-57b-snapshot-revision-declare
repo: magiq-media
tags: [magiq-media, event-store, snapshots]
consumes: []
blocked-by-external: [MM-079]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-57; origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-57.
---

# WS-57b — Declare snapshot revisions in magiq-media

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.
**Depends on:** MM-079 (WS-57a) released and consumed

**Spec:**
- `changerequest.write-model.md` § Absent-meaning on `ChangeRequestSnapshot`: `ChangeRequestSnapshot` is at **revision 2**. A snapshot without `ResolvedAt` predates the member, so every revision-1 snapshot is discarded on load.
- Every other `ISnapshot` record stays at revision 1 (no attribute) unless its spec says otherwise.

## Session invocation

> Picking up WS-57b (plan MM-081). Add `[Snapshot(Revision = 2)]` to `ChangeRequestSnapshot`. Confirm against the spec that no other snapshot record declares a revision above 1. Add an architecture test that every `ISnapshot` record's declared revision matches its spec.

## Phase 0 — Scope confirmation
- [ ] MM-079 shipped and the platform package referenced
- [ ] Enumerate `ISnapshot` records (`Collection`, `Folder`, `MediaItem`, `MediaProfile`, `ChangeRequest`) and their spec'd revisions

## Phase 1 — Declare
- [ ] `ChangeRequestSnapshot`: `[Snapshot(Revision = 2)]`

## Phase 2 — Tests
- [ ] Architecture test: declared revision per `ISnapshot` record matches the spec table
- [ ] Integration: a stored revision-1 `ChangeRequestSnapshot` → aggregate loads by replay; next snapshot written at revision 2

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] platform-capabilities/INDEX.md: WS-57 → § Shipped; INTEGRATION-BACKLOG: MM-081 → § Shipped
- [ ] Repo `CLAUDE.md`: remove the **Snapshots carry no revision** bullet

## Closing out

The plan's card moves to `done` only after Chase agrees the work is implemented and complete. The closing card comment records every branch the work was committed to.

## Session log
- 2026-10-08: plan drafted with MM-079 (blocked by user policy)
