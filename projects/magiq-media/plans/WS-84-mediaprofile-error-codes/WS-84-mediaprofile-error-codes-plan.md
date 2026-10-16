---
id: MM-124
type: plan
project: magiq-media
workstream: WS-84-mediaprofile-error-codes
repo: magiq-media
tags: [magiq-media, catalog, mediaprofile, errors, error-codes, problemdetails, wire-contract]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: MM-100, MM-032, WS-47
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell MediaProfile × error-codes
---

# WS-84 — MediaProfile coded error wiring (11 codes)

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot), MM-032 (`AggregateAlreadyExistsException` → `MediaProfileIdAlreadyExists`), WS-47 (`PlatformProfileImmutable` 403 refusal)

## Problem

`docs/spec/shared/error-catalog.md § MediaProfile` names 11 codes. Code emits every MediaProfile refusal as `DomainError.InvalidOperation(prose)` with no `errorCode`. `MediaProfileErrorCodes` constants class is unbuilt.

11 codes:

| errorCode | HTTP | Condition |
|---|---|---|
| `MediaProfileNotFound` | 404 | Absent / wrong tenant |
| `AttachedRecordTypeDeprecated` | 422 | Attach/re-pin/publish names deprecated version |
| `RecordTypeAlreadyPinned` | 422 | Attach record type draft already pins |
| `PlatformProfileImmutable` | 403 | Tenant write on `Platform`-origin profile |
| `MediaProfileNameConflict` | 409 | Live profile holds name |
| `MediaProfileIdAlreadyExists` | 409 | Duplicate caller id |
| `MediaProfileNotPublished` | 422 | Referenced profile not Published |
| `AssetRoleAlreadyExists` | 409 | Duplicate role name on draft |
| `CapabilityFieldCollision` | 422 | Capability field name collides with pinned RecordType |
| `RevisionBreaksExistingItems` | 422 | Publish removes/renames role or makes required |
| `ProfileSchemaBudgetExceeded` | 422 | Publish would exceed 256 KB SNS budget |

## Code state today

- MediaProfile handlers emit `DomainError.InvalidOperation(prose)` across every refusal site.
- `PlatformProfileImmutable` refusal doesn't exist today — WS-47 covers the 403 refusal path.
- `MediaProfileNameConflict` refusal exists but no coded `errorCode` on wire.
- `AttachedRecordTypeDeprecated` + `RecordTypeAlreadyPinned` + `AssetRoleAlreadyExists` + `RevisionBreaksExistingItems` + `ProfileSchemaBudgetExceeded` + `CapabilityFieldCollision` relate to draft/publish/attach lifecycle — site existence varies by lifecycle flow build state.
- `MediaProfileIdAlreadyExists` depends on F020 / MM-032.

## What the spec requires

- `MediaProfileErrorCodes` constants class with 11 members.
- Every `MediaProfile.*` refusal returns `DomainError.<factory>(errorCode: MediaProfileErrorCodes.<code>, …)`.
- Every `*MediaProfileHandler.cs` reports `errorCode` on refusals.
- `MediaProfileIdAlreadyExists` from `AggregateAlreadyExistsException` (MM-032).
- `PlatformProfileImmutable` from handler-side origin check (WS-47).
- `MediaProfileNameConflict` from name reservation.
- `AssetRoleAlreadyExists` from `MediaProfileDraft` aggregate role-name uniqueness.
- `AttachedRecordTypeDeprecated` + `RecordTypeAlreadyPinned` from attach-record-type handler.
- `MediaProfileNotPublished` from any handler consuming a MediaProfile reference.
- `CapabilityFieldCollision` from publish or attach validation.
- `RevisionBreaksExistingItems` + `ProfileSchemaBudgetExceeded` from publish validation.
- Bulk envelope `BulkItemError.ErrorCode` uses `MediaProfileErrorCodes`.

## Scope boundary

- **MediaProfile only.** Other aggregates handled under their cells.
- Codes gated on partially-built lifecycle flows (capability-field-collision; revision-breaking-detection; schema-budget) ship as constants; call sites land with their owning validation code.
- Does not build `PlatformProfileImmutable` refusal (WS-47 scope); this plan ensures `MediaProfileErrorCodes.PlatformProfileImmutable` is the string that WS-47 cites.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-84 (plan MM-124). MM-100 shipped. Wire 11 MediaProfile error codes to aggregate + handlers. Several codes gated on partially-built lifecycle flows (publish validation, capability-field-collision, schema-budget). Constants ship now; call sites follow owning flow.

## Phase 0 — Scope confirmation

- [ ] MM-100 shipped
- [ ] Grep `DomainError.InvalidOperation` + `ResourceNotFound` sites under `Catalog.Domain/Aggregates/MediaProfiles/` + `Catalog.WriteModel/Commands/MediaProfiles/`
- [ ] Confirm WS-47 reachable (`PlatformProfileImmutable` refusal path)

## Phase 1 — Constants + aggregate

- [ ] `MediaProfileErrorCodes.cs` with 11 const strings
- [ ] `MediaProfile.*` method refusals return `DomainError.<factory>(errorCode: MediaProfileErrorCodes.<code>, message)`
- [ ] `MediaProfileDraft` role-name uniqueness → `AssetRoleAlreadyExists`
- [ ] Snapshot test per factory: `.ErrorCode` set

## Phase 2 — Handlers

- [ ] Aggregate-missing → `MediaProfileNotFound`
- [ ] Name reservation refusal → `MediaProfileNameConflict`
- [ ] `AggregateAlreadyExistsException` (MM-032) → `MediaProfileIdAlreadyExists`
- [ ] Platform-origin refusal → `PlatformProfileImmutable` (WS-47)
- [ ] Attach record type refusals → `AttachedRecordTypeDeprecated`, `RecordTypeAlreadyPinned`
- [ ] Reference-profile refusals → `MediaProfileNotPublished`
- [ ] Bulk envelope `BulkItemError.ErrorCode` uses `MediaProfileErrorCodes`

## Phase 3 — Gated codes

- [ ] `CapabilityFieldCollision` — wired at publish/attach validation site
- [ ] `RevisionBreaksExistingItems` — wired at publish validation site
- [ ] `ProfileSchemaBudgetExceeded` — wired at publish-size validation (coordinate with F008 S3 claim-check: budget check lands before claim-check path triggers)

## Phase 4 — Tests

- [ ] Integration per spec row: HTTP status + `errorCode` + `type`
- [ ] Unit per factory: `ErrorCode` set
- [ ] Platform-origin refusal integration

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: MediaProfile bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-124 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-84 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaProfile × error-codes; status candidate; mirror of MM-101/MM-107/MM-113/MM-118 pattern)
