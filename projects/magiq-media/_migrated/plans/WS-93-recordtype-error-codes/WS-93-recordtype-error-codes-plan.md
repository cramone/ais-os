---
id: MM-133
type: plan
project: magiq-media
workstream: WS-93-recordtype-error-codes
repo: magiq-media
tags: [magiq-media, metadata, recordtype, errors, error-codes, problemdetails, wire-contract]
consumes: [MM-100]
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: MM-100, MM-032, WS-51
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell RecordType × error-codes
---

# WS-93 — RecordType coded error wiring (69 codes)

**Target repo:** `magiq-media`
**Depends on:** MM-100 (SDK `errorCode` slot), MM-032 (`AggregateAlreadyExistsException` → `RecordTypeIdAlreadyExists`), WS-51 (`conflictingRecordTypeId` extension on name/alias conflicts)

## Problem

`docs/spec/shared/error-catalog.md § Metadata — RecordType` names 69 codes — split into "identity + lifecycle" (29) and "fields" (40). Code emits every RecordType refusal as `DomainError.InvalidOperation(prose)` with no `errorCode`. `RecordTypeErrorCodes` constants class unbuilt.

Largest aggregate code set in the catalog by a wide margin — RecordType's draft/publish/field-schema lifecycle generates a large validation surface.

## Code sets

### Identity + lifecycle (29)

**Identity + name:** `RecordTypeNotFound`, `NoPublishedVersion`, `RecordTypeNameConflict`, `RecordTypeIdAlreadyExists`, `RecordTypeAliasNotUnique`, `InvalidRecordTypeAlias`, `DuplicateAliasInRequest`, `TooManyAliases`, `InvalidRecordTypeName`.

**Draft lifecycle:** `NoActiveDraft`, `DraftAlreadyInProgress`, `DraftEmpty`, `CannotDiscardInitialDraft`.

**Publish lifecycle:** `RecordTypeAlreadyPublished`, `RecordTypeAlreadyAbandoned`, `NothingToRevise`, `RecordTypeNotPublished`, `RecordTypeAlreadyDeprecated`, `CannotDeprecateLastVersion`.

**Schema limits:** `SchemaPayloadTooLarge` (256 KB SNS), `SchemaBudgetExceeded` (160 KB sub-cap).

**Deprecation / supersession:** `RecordTypeDeprecated`, `InvalidSupersededByRecordType`, `RecordTypeVersionNotFound`, `RecordTypeVersionAlreadyDeprecated`, `RecordTypeNotDeprecated`, `RecordTypeVersionNotDeprecated`, `SupersessionAlreadyRecorded`.

### Fields (40)

**Field identity:** `FieldNotFound`, `FieldNameConflict`, `InvalidFieldName`.

**Field deprecation:** `CannotDeprecateUnpublishedField`, `UnknownFieldInReorder`, `DuplicateFieldInReorder`, `FieldAlreadyDeprecated`, `FieldDeprecationNotSettable`.

**Field type + removal:** `FieldTypeImmutable`, `CannotRemoveImmutableField`, `CannotRemoveRequiredField`.

**Migration notes:** `MigrationNoteRequired`, `MigrationNoteTooLong`.

**Field limits:** `RecordTypeFieldLimitReached` (100), `TooManyFieldGroups` (20), `TooManyRetiredFieldNames` (500), `RetiredFieldPayloadTooLarge` (512 KB), `TooManyVersions` (500), `TooManyRetainedNames` (100), `TooManyRetainedAliases` (200).

**Constraint validation:** `ConstraintNotApplicableToFieldType`, `AllowedValuesRequired`, `MaxSelectionsExceedsAllowedValues`, `ConstraintRangeInvalid`, `DefaultValueViolatesConstraints`.

**Label / description:** `InvalidLabel`, `InvalidFieldGroup`, `LabelTooLong` (512), `DefaultValueTooLong` (512).

**Allowed values:** `TooManyAllowedValues` (100), `AllowedValueTooLong` (100), `DuplicateAllowedValue`, `InvalidAllowedValue`.

**Regex:** `RegexPatternTooLong` (500), `InvalidRegexPattern`, `RegexPatternTooComplex` (100 ms).

**Internationalisation + accessibility:** `InvalidLanguageTag` (BCP 47), `UnknownAutocompleteToken` (HTML `autocomplete`).

**Publish-schema cohesion:** `UnreconciledPublishedField`, `SchemaIncoherent`.

## Code state today

- RecordType handlers emit `DomainError.InvalidOperation(prose)` across every refusal site.
- `RecordTypeErrorCodes` constants class unbuilt.
- Name/alias conflicts do not carry `conflictingRecordTypeId` extension today — covered by WS-51.
- `RecordTypeIdAlreadyExists` depends on F020 / MM-032.
- Field validation covers draft lifecycle (adds, updates, deprecations, reorders) — large surface.

## What the spec requires

- `RecordTypeErrorCodes` constants class with 69 members.
- Every `RecordType.*` refusal returns `DomainError.<factory>(errorCode: RecordTypeErrorCodes.<code>, …)`.
- Every `*RecordTypeHandler.cs` reports `errorCode` on refusals.
- `RecordTypeIdAlreadyExists` from `AggregateAlreadyExistsException` (MM-032).
- Name/alias conflicts carry `conflictingRecordTypeId` extension payload (WS-51).
- Field validation refusals wire into `AddField` / `UpdateField` / `DeprecateField` / `ReorderFields` / publish-time schema cohesion handlers.
- Bulk envelope `BulkItemError.ErrorCode` lookup from `RecordTypeErrorCodes` for batch flows (if RecordType has bulk).

## Scope boundary

- **RecordType only.**
- Does not build missing commands/handlers — RecordType × write-model cell plan.
- `conflictingRecordTypeId` extension payload wiring = WS-51 scope; this plan ensures `RecordTypeErrorCodes.RecordTypeNameConflict` + `RecordTypeAliasNotUnique` are the strings WS-51 cites.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-93 (plan MM-133). MM-100 shipped. Wire 69 RecordType error codes to aggregate + handlers. Largest aggregate code set in the catalog.

## Phase 0 — Scope confirmation

- [ ] MM-100 shipped
- [ ] Grep `DomainError.InvalidOperation` sites in `Metadata.Domain/Aggregates/RecordTypes/` + `Metadata.WriteModel/Commands/RecordTypes/`
- [ ] Enumerate which draft/publish/field flows are built vs partially built

## Phase 1 — Constants + aggregate (identity + lifecycle)

- [ ] `RecordTypeErrorCodes.cs` with 69 const strings (split into regions matching spec categories for readability)
- [ ] Identity + name refusals wired per spec row
- [ ] Draft lifecycle refusals wired
- [ ] Publish lifecycle refusals wired
- [ ] Deprecation / supersession refusals wired

## Phase 2 — Field validation refusals

- [ ] `AddField` / `UpdateField` handlers: field identity + constraint + label refusals
- [ ] `DeprecateField` handler: field deprecation refusals
- [ ] `ReorderFields` handler: `UnknownFieldInReorder`, `DuplicateFieldInReorder`
- [ ] Publish-schema cohesion handler: `UnreconciledPublishedField`, `SchemaIncoherent`
- [ ] Schema size caps (`SchemaPayloadTooLarge`, `SchemaBudgetExceeded`) + field limits (100, 20, 500, 512 KB, 500 versions, 100 retained names, 200 retained aliases)

## Phase 3 — Handlers

- [ ] Aggregate-missing → `RecordTypeNotFound`
- [ ] Name reservation refusal → `RecordTypeNameConflict` (+ `conflictingRecordTypeId` per WS-51)
- [ ] Alias uniqueness refusal → `RecordTypeAliasNotUnique` (+ `conflictingRecordTypeId` per WS-51)
- [ ] `AggregateAlreadyExistsException` (MM-032) → `RecordTypeIdAlreadyExists`
- [ ] Version-specific refusals → `RecordTypeVersionNotFound`, `RecordTypeVersionAlreadyDeprecated`, `RecordTypeVersionNotDeprecated`

## Phase 4 — Tests

- [ ] Integration per spec row: HTTP status + `errorCode` + `type`
- [ ] Unit per factory: `ErrorCode` set
- [ ] Integration: name conflict carries `conflictingRecordTypeId` (coordinate with WS-51)

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: RecordType bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-133 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-93 close row
- [ ] breaking-changes.md: entry moves on release cut

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RecordType × error-codes; status candidate; mirror of MM-101/107/113/118/124/128 pattern — largest aggregate code set with 69 codes split identity-lifecycle 29 + fields 40)
