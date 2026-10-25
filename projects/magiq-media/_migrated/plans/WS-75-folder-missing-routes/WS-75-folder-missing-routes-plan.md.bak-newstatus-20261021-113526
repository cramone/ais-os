---
id: MM-115
type: plan
project: magiq-media
workstream: WS-75-folder-missing-routes
repo: magiq-media
tags: [magiq-media, catalog, folder, http, routes]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
depends-on: 'Folder × write-model plan (future)'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Folder × http-routes
---

# WS-75 — Folder missing routes: `PUT /originator` + `POST /reopen`

**Target repo:** `magiq-media`
**Depends on:** Folder × write-model cell plan (future — provides `SetFolderOriginatorCommand` + `ReopenFolderCommand`)

## Problem

`docs/spec/contexts/Catalog/aggregates/Folder/folder.api.md` names 20 Folder HTTP routes. Code wires 15. 5 missing:

| spec route | status | plan |
|---|---|---|
| `PUT /v1/folders/{folderId}/originator` | **missing** | **this plan** |
| `GET /v1/folders/{folderId}/archive-status` | missing | WS-11 (long-running) |
| `POST /v1/folders/{folderId}/unarchive` | missing | WS-11 |
| `GET /v1/folders/{folderId}/unarchive-status` | missing | WS-11 |
| `POST /v1/folders/{folderId}/reopen` | **missing** | **this plan** |

Also:
- `POST /v1/folders/{folderId}/archive` — code wires it synchronously; spec: `202 Accepted` + `Location: /v1/folders/{folderId}/archive-status`. Shape change covered by WS-11.

This plan covers the 2 routes outside WS-11's long-running scope: `PUT /originator` + `POST /reopen`.

## What the spec requires

- `SetFolderOriginatorEndpoint` at `PUT /v1/folders/{folderId}/originator` → `SetFolderOriginatorCommand`. Spec: records-management "originator" is the submitting agency / department. Payload: `{ OriginatorId, OriginatorName }` (align with `folder.api.md § Request body` for the exact row).
- `ReopenFolderEndpoint` at `POST /v1/folders/{folderId}/reopen` → `ReopenFolderCommand`. Refuses `FolderNotClosed 422` (MM-113) if the folder isn't closed.
- Both routes 204 No Content on success; 404 / 403 / 409 / 422 per guard precedence.

## Wire-visibility

Additive — 2 new routes. Existing clients unaffected.

## Scope boundary

- **Endpoint layer only.** Commands + handlers + aggregate methods (`Folder.SetOriginator`, `Folder.Reopen`) + domain events (`FolderOriginatorChanged`, `FolderReopened`) belong to the Folder × write-model cell plan. This plan dispatches commands that plan implements. Sequence: write-model cell ships first.
- **Not in scope:** archive 202-async conversion + `/archive-status` + unarchive + `/unarchive-status` — all WS-11.
- **Not in scope:** error-code wiring on the new routes — MM-113 constants.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-75 (plan MM-115). Folder × write-model cell plan must ship first (SetFolderOriginator + ReopenFolder commands). Wire PUT /originator + POST /reopen endpoints. 2 new routes, additive.

## Phase 0 — Scope confirmation

- [ ] Folder × write-model plan shipped (`SetFolderOriginatorCommand`, `ReopenFolderCommand`, `Folder.SetOriginator`, `Folder.Reopen` aggregate methods)
- [ ] `folder.api.md § Request body` rows for both routes confirmed
- [ ] Confirm archive 202-async + status endpoints covered by WS-11 (sanity)

## Phase 1 — Endpoints

- [ ] `SetFolderOriginatorEndpoint` at `PUT /v1/folders/{folderId}/originator`
- [ ] `ReopenFolderEndpoint` at `POST /v1/folders/{folderId}/reopen`
- [ ] Each: guard precedence, 204 on success, FastEndpoints `Version(1)`

## Phase 2 — Tests

- [ ] Integration: `PUT /originator` on closed/open/archived folders — correct state refusals (`FolderArchived` / `FolderNotFound`)
- [ ] Integration: `POST /reopen` on closed folder → 204 + state transition; on non-closed → `FolderNotClosed 422`
- [ ] Integration: idempotent repeat `POST /reopen` on reopened folder → `FolderNotClosed 422`

## Phase 3 — Communicate change

- [ ] Breaking-changes.md entry (added in this sweep's Phase 3) — API wire additive
- [ ] Release notes

## Phase 4 — Ship

- [ ] PR to `develop`

## Phase 5 — Close

- [ ] CLAUDE.md § KDPW: Folder-routes bullet updated / removed
- [ ] INTEGRATION-BACKLOG.md: MM-115 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-75 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-15: plan drafted (alignment-sweep-2026-10-15 cell Folder × http-routes; status candidate; depends on Folder × write-model plan)
