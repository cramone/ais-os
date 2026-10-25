---
id: MM-073
type: plan
project: magiq-media
workstream: WS-11-folder-archive-long-running
repo: magiq-media
tags: [magiq-media, folder-archive, saga, api, step-functions]
consumes: []
blocked-by-external: [MM-031]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/folder-locks/INDEX.md#WS-11.
---

# WS-11 — Folder archive / un-archive as long-running (202 + status endpoints + Distributed-Map cascade)

**Target repo:** `magiq-media`
**Depends on:** MM-031 (WS-04 CDK state machines — folder-archive-cascade state machine)
**User policy gate:** no magiq-media change until all external deps ship.

Spec: `202 Accepted` + `Location: /v1/folders/{folderId}/archive-status` (+ `/unarchive-status`), cascade runs in Step Functions Distributed Map. Removes `FolderSubtreeTooLargeToArchive` error, 500-folder cap, API Lambda `DescribeExecution` poll.

## Session invocation

> Picking up WS-11 (plan MM-073). Depends on MM-031 (state machine). Convert archive + unarchive routes to 202 + status endpoint. Dispatch Step Functions execution; return execution id as archive-status route key. Remove `FolderSubtreeTooLargeToArchive` + 500-cap. Status endpoint reports progress.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-031 shipped
- [ ] Current archive endpoint behaviour

## Phase 1 — Route changes
- [ ] `POST /v1/folders/{folderId}/archive` → start execution → 202 + `Location: /v1/folders/{folderId}/archive-status`
- [ ] `POST /v1/folders/{folderId}/unarchive` → analogous + `/unarchive-status`
- [ ] Status endpoints: `GET /v1/folders/{folderId}/archive-status` + `/unarchive-status`

## Phase 2 — Remove old constraints
- [ ] Delete `FolderSubtreeTooLargeToArchive` error code
- [ ] Remove 500-folder cap
- [ ] Remove `DescribeExecution` poll from Api Lambda

## Phase 3 — Status endpoint
- [ ] `DescribeExecution` happens on status endpoint (not archive endpoint)
- [ ] Report progress + per-item errors from Step Functions execution

## Phase 4 — Tests
- [ ] Integration: archive returns 202 + Location
- [ ] Integration: status endpoint reports progress through completion
- [ ] Integration: >500 folder subtree succeeds

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] folder-locks/INDEX.md: WS-11 → § Shipped
- [ ] Remove `Folder archive and un-archive are long-running` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-031 + user policy)
