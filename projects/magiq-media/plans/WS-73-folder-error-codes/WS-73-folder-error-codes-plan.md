---
id: MM-113
type: plan
project: magiq-media
workstream: WS-73-folder-error-codes
repo: magiq-media
tags: [magiq-media, catalog, folder, errors, error-codes, problemdetails, wire-contract]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
depends-on: MM-100, MM-032
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Folder × error-codes
---

# WS-73 — Folder coded error wiring (18 codes)

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot on `DomainError` + `ProblemDetails` emission), MM-032 (`AggregateAlreadyExistsException` → `FolderIdAlreadyExists`)

## Problem

`docs/spec/shared/error-catalog.md § Folder` names 18 codes. Code emits every Folder refusal as `DomainError.InvalidOperation(prose)` with no `errorCode` member on the wire. Clients cannot branch on `body.errorCode` for any Folder refusal today.

Codes:

| errorCode | HTTP | Condition |
|---|---|---|
| `FolderNotFound` | 404 | Folder/parent/dest/root absent |
| `FolderAlreadyExists` | 409 | Name taken in scope |
| `FolderIdAlreadyExists` | 409 | Duplicate caller-supplied id |
| `DepthExceeded` | 422 | Nesting > 10 |
| `CircularFolderReference` | 422 | Move/batch creates cycle |
| `FolderAlreadyArchived` | 422 | Archive on archived |
| `FolderNotArchived` | 422 | Un-archive node on non-archived |
| `ArchivedUnderAnotherRoot` | 422 | Un-archive outside root |
| `FolderArchived` | 422 | Mutation on archived folder |
| `FolderCascadeInProgress` | 409 | Archive/unarchive cascade running |
| `FolderAlreadyClosed` | 422 | Close on closed |
| `FolderNotClosed` | 422 | Reopen on non-closed |
| `ClosedDateRequired` | 400 | Close without `closedDate` |
| `ClosedDateOutOfRange` | 400 | `closedDate` out of range |
| `FolderClosed` | 422 | Assign/move item into closed folder |
| `FolderArchiveIncomplete` | — | SQS-only; cascade broke after pre-flight |
| `FolderUnarchiveIncomplete` | — | SQS-only; unarchive cascade broke |
| `ParentCreationFailed` | 422 | Batch parent failed; child skipped (bulk envelope) |

## Code state today

- `Folder.cs` returns `DomainError.InvalidOperation("Folder is already archived.")`, `"Folder is already closed."`, `"Folder is archived."`, `"No pending metadata draft to commit."` — no codes.
- Code comment references `DomainError.FolderNestingDepthExceeded` and `DomainError.FolderHasActiveChildren` as the intended rename targets — neither exists as a factory on `DomainError`; current implementation uses prose only.
- `FolderErrorCodes` constants class is unbuilt.
- `CircularFolderReference` + `DepthExceeded` + close-flow family + archive cascade family all need commands/handlers that may be absent (cascade unarchive + close/reopen specifically).
- `FolderIdAlreadyExists` depends on F020 / MM-032 shipping.
- `FolderArchiveIncomplete` + `FolderUnarchiveIncomplete` are SQS-only codes (HTTP `—`) — surface via the cascade report + status endpoint payload under MM-110 reader.

## What the spec requires

- `FolderErrorCodes` constants class with 18 members.
- Every `Folder.*` refusal returns `DomainError.<factory>(errorCode: FolderErrorCodes.<code>, …)`.
- Every `*FolderHandler.cs` reports `errorCode` on refusals.
- Bulk envelope `BulkItemError.ErrorCode` lookup from `FolderErrorCodes` for batch creation flows.
- Status endpoint (MM-109 Folder parallel; part of WS-11) surfaces `FolderArchiveIncomplete` / `FolderUnarchiveIncomplete` via payload; neither code reaches HTTP root.

## Scope boundary

- **Folder only.** Collection error codes handled under MM-107. MediaItem under its own cell.
- Does not build `UnarchiveFolder`, `CloseFolder`, `ReopenFolder` commands — those are Folder × write-model cell concerns. This plan carries the constants; call sites wire when owning commands land.
- Does not change HTTP status codes for existing refusals — only the shape (`errorCode` added at root).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-73 (plan MM-113). MM-100 shipped. Wire 18 Folder error codes to aggregate + handlers. Several codes gated on cascade/close/unarchive command plans — constants ship now; call sites land when those commands do.

## Phase 0 — Scope confirmation

- [ ] MM-100 shipped
- [ ] Grep every `DomainError.InvalidOperation` + `ResourceNotFound` call site in `Catalog.Domain/Aggregates/Folders/` + `Catalog.WriteModel/Commands/Folders/`
- [ ] Confirm absent commands: `UnarchiveFolder`, `CloseFolder`, `ReopenFolder`, cascade terminators (sanity)

## Phase 1 — Constants + aggregate

- [ ] `FolderErrorCodes.cs` with 18 const strings
- [ ] Every `Folder.*` method refusal returns `DomainError.<factory>(errorCode: FolderErrorCodes.<code>, message)`
- [ ] `Archive` → `FolderAlreadyArchived` (422)
- [ ] `Close` → `FolderAlreadyClosed` (422); missing `ClosedDate` → `ClosedDateRequired` (400); out-of-range → `ClosedDateOutOfRange` (400)
- [ ] Mutations on archived → `FolderArchived` (422)
- [ ] Mutations on closed (assign/move item in) → `FolderClosed` (422)
- [ ] Depth guard → `DepthExceeded` (422)
- [ ] Move cycle → `CircularFolderReference` (422)
- [ ] Snapshot test per factory: shape asserts `.ErrorCode` set

## Phase 2 — Handlers

- [ ] Aggregate-missing → `FolderNotFound`
- [ ] Name-reservation refusal → `FolderAlreadyExists`
- [ ] `AggregateAlreadyExistsException` (MM-032) → `FolderIdAlreadyExists`
- [ ] Bulk envelope `BulkItemError.ErrorCode` uses `FolderErrorCodes`
- [ ] `BulkCreateFoldersByPathHandler` emits `ParentCreationFailed` on skipped child when parent failed

## Phase 3 — SQS-only codes

- [ ] `FolderArchiveIncomplete` constant used by cascade terminator write path (MM-110 shape; owning plan carries wiring)
- [ ] `FolderUnarchiveIncomplete` constant used symmetrically

## Phase 4 — Tests

- [ ] Integration per spec row: HTTP response has correct status + `errorCode` + `type`
- [ ] Unit per factory: `ErrorCode` set
- [ ] Bulk envelope: child-skipped row carries `ParentCreationFailed`

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: Folder line in error-code bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-113 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-73 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-15: plan drafted (alignment-sweep-2026-10-15 cell Folder × error-codes; status candidate; mirrors MM-101 / MM-107 pattern)
