# RecordType — Write Model

_Context: `Metadata`_
_Aggregate: `RecordType`_
_Stream prefix: `rt_`_

---

## Purpose

Defines a reusable, versioned metadata schema — a named set of typed field definitions. Referenced by `MediaProfile` to declare what metadata a `MediaItem` must carry. Configuration aggregate; not transactional.

Follows the **Draft → Publish** versioning model: `CreateRecordType` opens an initial draft; structural mutations operate on the draft only; `PublishRecordType` creates an immutable snapshot and increments the version number. Published versions are never modified. MediaProfiles pin a specific published version; they remain pinned until explicitly updated.

Owner-scoped. Use `OwnerId = "owner_system"` for platform-level schemas. Query pattern: `OwnerId IN [ownerId, "owner_system"]`.

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| `Name` unique within tenant scope (enforced handler-side via `IRecordTypeUnicityService`) | `RecordTypeNameNotUnique` | `CreateRecordType`, `RenameRecordType` |
| Draft must be non-null to publish | `NoDraftToPublish` | `PublishRecordType` |
| `FieldName` unique within draft (including capability-contributed fields) | `FieldNameConflict` | `AddFieldToRecordType`, `AddCapabilityToRecordType` |
| `FieldType` is immutable — use `ReplaceFieldInRecordType` for type changes | `FieldTypeImmutable` | `UpdateFieldInRecordType` |
| `ReplaceFieldInRecordType` requires non-empty `MigrationNote` | `MigrationNoteRequired` | `ReplaceFieldInRecordType` |
| `FieldName` to replace must exist in draft | `FieldNotFound` | `ReplaceFieldInRecordType`, `RemoveFieldFromRecordType`, `UpdateFieldInRecordType` |
| Only one draft open at a time | `DraftAlreadyExists` | `CreateRecordTypeDraft` |
| Cannot discard the initial draft (`Version == 0`) — doing so leaves the aggregate permanently inert | `CannotDiscardInitialDraft` | `DiscardRecordTypeDraft` |
| Cannot deprecate before first publish | `RecordTypeNotPublished` | `DeprecateRecordType` |
| Deprecated types cannot be attached to new MediaProfiles | `RecordTypeDeprecated` | (handler-side on `AttachRecordType`) |
| `CapabilityType` must not already be attached to draft | `CapabilityAlreadyAttached` | `AddCapabilityToRecordType` |
| `CapabilityType` must be attached to draft | `CapabilityNotAttached` | `RemoveCapabilityFromRecordType` |
| Capability-contributed fields with `IsImmutable = true` cannot be removed | `CannotRemoveImmutableField` | `RemoveCapabilityFromRecordType` |
| Total field count (draft + contributed) must not exceed 100 | `RecordTypeFieldLimitReached` | `AddFieldToRecordType`, `AddCapabilityToRecordType` |
| `IsImmutable` may only tighten (`false → true`), never relax | `CannotRelaxImmutability` | `UpdateFieldInRecordType` |

---

## Properties

| Property | Type | Notes |
|---|---|---|
| `RecordTypeId` | `RecordTypeId` | UUID v7-based |
| `TenantId` | `TenantId` | Set from `RecordTypeCreated`. Immutable. |
| `Name` | `NonEmptyString` | Unique within owner scope |
| `DisplayName` | `string?` | Human-readable label; separate from the unique `Name`; updated independently via `UpdateRecordTypeDisplayNameCommand` |
| `Description` | `string?` | |
| `OwnerId` | `OwnerId` | Non-nullable |
| `Version` | `int` | Current published version; `0` before first publish |
| `PublishedAt` | `DateTimeOffset?` | Null before first publish |
| `IsDeprecated` | `bool` | No new MediaProfiles may reference a deprecated RecordType |
| `Draft` | `RecordTypeDraft?` | Present when an editing cycle is active |

---

## RecordTypeDraft

| Property | Type | Notes |
|---|---|---|
| `BasedOnVersion` | `int?` | Version the draft was opened from (`null` for initial draft) |
| `Fields` | `IReadOnlyList<FieldDefinition>` | Working set of field definitions — includes both manually-added fields and capability-contributed fields |
| `Capabilities` | `IReadOnlyList<string>` | Fully-qualified capability type names currently attached to this draft |
| `CreatedAt` | `DateTimeOffset` | |

---

## FieldDefinition Value Object

| Property | Type | Notes |
|---|---|---|
| `FieldName` | `NonEmptyString` | Snake-cased; unique within schema |
| `DisplayName` | `string` | Human-readable label |
| `FieldType` | `FieldType` | `Text \| Number \| Date \| Boolean \| Url \| Enum \| MultiEnum`. **Immutable** — use `ReplaceField` for type changes. |
| `IsRequired` | `bool` | |
| `IsSearchable` | `bool` | If `true`, field is indexed in OpenSearch `media-items.metadata` |
| `IsImmutable` | `bool` | If `true`, value cannot be changed after first write; may tighten (`false → true`) but never relax. Capability-contributed fields set this via the registry. |
| `IsDeprecated` | `bool` | Soft-deprecated within a draft; deprecated fields are preserved in published snapshots for migration purposes |
| `SourceCapability` | `string?` | Fully-qualified capability type name if this field was contributed by a capability; `null` for manually-added fields. Used to identify and remove all contributed fields when a capability is detached. |
| `Order` | `int` | Display order; unique within schema; auto-assigned as `max + 1` if omitted |
| `Description` | `string?` | |
| `MinLength` / `MaxLength` | `int?` | Text only |
| `RegexPattern` | `string?` | Text only; validated for syntax and complexity by `IFieldConstraintValidator` |
| `MinValue` / `MaxValue` | `decimal?` | Number only |
| `MinDate` / `MaxDate` | `DateTimeOffset?` | Date only |
| `AllowedValues` | `IReadOnlyList<string>?` | Enum / MultiEnum only |
| `MaxSelections` | `int?` | MultiEnum only; auto-clamped to `AllowedValues.Count` if it exceeds the list size |
| `DefaultValue` | `string?` | Optional default; applied when field is absent on record creation |

---

## Status Lifecycle

```
Draft (Version = 0, no published version)
    │
    │  PublishRecordType
    ▼
Published (Version = 1)
    │
    │  CreateRecordTypeDraft → mutations → PublishRecordType (Version = 2, 3, ...)
    ▼
Published (Version = N)
    │
    │  DeprecateRecordType
    ▼
Deprecated
```

Deprecated RecordTypes remain accessible to MediaProfiles already pinned to their versions. No new MediaProfiles may reference a deprecated type.

---

## Methods (Commands)

| Method | Description |
|---|---|
| `RecordType.Create(tenantId, id, ownerId, name, description?)` | Factory. Opens initial draft. Raises `RecordTypeCreated` + `RecordTypeDraftCreated({basedOnVersion: null})`. |
| `CreateDraft(basedOnVersion)` | Opens a new revision draft from the published version. Guard: no draft open. |
| `AddField(fieldDefinition)` | Adds a field to the draft. Guard: draft non-null; `FieldName` unique in draft. |
| `UpdateField(fieldName, updates)` | Updates field properties (except `FieldType`). Guard: field exists in draft. |
| `ReplaceField(oldFieldName, newFieldDefinition, migrationNote)` | Replaces a field entirely. Guard: non-empty `migrationNote`; `oldFieldName` exists in draft. |
| `RemoveField(fieldName)` | Removes a field from the draft. Guard: field exists. |
| `ReorderFields(orderedFieldNames)` | Sets `Order` on all fields in draft. |
| `AddCapability(capabilityType, contributedFields)` | Attaches a capability to the draft. `contributedFields` are resolved by `ICapabilityRegistry.GetContributedFields` in the handler and appended to `Draft.Fields` with `SourceCapability` set. Guards: draft non-null; not deprecated; capability not already attached (`CapabilityAlreadyAttached`); no field name conflicts (`FieldNameConflict`); total field count ≤ 100 (`RecordTypeFieldLimitReached`). Raises `CapabilityAddedToRecordType`. |
| `RemoveCapability(capabilityType)` | Detaches a capability from the draft and removes all `Draft.Fields` where `SourceCapability == capabilityType`. Guards: draft non-null; not deprecated; capability attached (`CapabilityNotAttached`); no contributed field is `IsImmutable` (`CannotRemoveImmutableField`). Raises `CapabilityRemovedFromRecordType`. |
| `DiscardDraft()` | Discards the current draft without publishing. Guards: draft non-null; `Version > 0` (`CannotDiscardInitialDraft`) — discarding the initial draft would leave the aggregate permanently inert since `CreateDraft`, `Publish`, and `Deprecate` all require `Version > 0`. |
| `Publish()` | Publishes the draft as the next version. Guard: draft non-null and non-empty. Raises `RecordTypePublished({newVersion, fieldSnapshot, capabilities})`. |
| `Rename(newName)` | Renames the RecordType. |
| `UpdateDisplayName(displayName, updatedAt)` | Updates the human-readable display name. Guard: not deprecated. No-op if the new value equals the current value. Applies immediately regardless of draft state. |
| `Deprecate()` | Marks as deprecated. Guard: must be published at least once. |

---

## Domain Events

| Event | Key Payload Fields | Notes |
|---|---|---|
| `RecordTypeCreated` | `TenantId`†, `RecordTypeId`, `OwnerId`, `Name`, `Description?`, `CreatedAt` | → initial state |
| `RecordTypeDraftCreated` | `RecordTypeId`, `BasedOnVersion?`, `InitialFields[]`, `CreatedAt` | `BasedOnVersion` null for initial draft |
| `FieldAddedToRecordType` | `RecordTypeId`, `FieldDefinition`, `AddedAt` | Applied to draft |
| `FieldDefinitionUpdated` | `RecordTypeId`, `FieldName`, `Updates`, `UpdatedAt` | Properties updated (not `FieldType`) |
| `FieldReplacedInRecordType` | `RecordTypeId`, `OldFieldName`, `NewFieldDefinition`, `MigrationNote`, `ReplacedAt` | Type change path |
| `FieldRemovedFromRecordType` | `RecordTypeId`, `FieldName`, `RemovedAt` | |
| `FieldsReorderedInRecordType` | `RecordTypeId`, `OrderedFieldNames[]`, `ReorderedAt` | |
| `CapabilityAddedToRecordType` | `RecordTypeId`, `CapabilityType`, `ContributedFields[]`, `OccurredAt` | Appends capability and its contributed fields to the draft |
| `CapabilityRemovedFromRecordType` | `RecordTypeId`, `CapabilityType`, `OccurredAt` | Removes capability and all fields where `SourceCapability == CapabilityType` from the draft |
| `RecordTypeDraftDiscarded` | `RecordTypeId`, `DiscardedAt` | |
| `RecordTypePublished` | `RecordTypeId`, `NewVersion`, `FieldSnapshot[]`, `Capabilities[]`, `PublishedAt` | Immutable snapshot; increments `Version`; `Capabilities` carries the capability type names active at publish time |
| `RecordTypeDisplayNameUpdated` | `TenantId`, `RecordTypeId`, `DisplayName`, `OccurredAt` | Applies regardless of draft state; not emitted if value unchanged |
| `RecordTypeRenamed` | `RecordTypeId`, `OldName`, `NewName`, `RenamedAt` | |
| `RecordTypeDeprecated` | `RecordTypeId`, `DeprecatedAt` | |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command | Notes |
|---|---|
| `CreateRecordTypeCommand(RecordTypeId, OwnerId, Name, Description?)` | |
| `CreateRecordTypeDraftCommand(RecordTypeId)` | Opens revision from current published version |
| `AddFieldToRecordTypeCommand(RecordTypeId, FieldDefinition)` | |
| `UpdateFieldInRecordTypeCommand(RecordTypeId, FieldName, Updates)` | |
| `ReplaceFieldInRecordTypeCommand(RecordTypeId, OldFieldName, NewFieldDefinition, MigrationNote)` | |
| `RemoveFieldFromRecordTypeCommand(RecordTypeId, FieldName)` | |
| `ReorderFieldsInRecordTypeCommand(RecordTypeId, OrderedFieldNames[])` | |
| `AddCapabilityToRecordTypeCommand(RecordTypeId, CapabilityType)` | `CapabilityType` is a fully-qualified type name; contributed fields resolved by `ICapabilityRegistry` in handler |
| `RemoveCapabilityFromRecordTypeCommand(RecordTypeId, CapabilityType)` | Removes capability and all its contributed fields from the draft |
| `DiscardRecordTypeDraftCommand(RecordTypeId)` | |
| `PublishRecordTypeCommand(RecordTypeId)` | |
| `RenameRecordTypeCommand(RecordTypeId, NewName)` | |
| `UpdateRecordTypeDisplayNameCommand(RecordTypeId, DisplayName)` | Updates the human-readable display name. Precondition: not deprecated (`RecordTypeDeprecated`). No-op if value unchanged. Applies regardless of draft state — no external services required. |
| `DeprecateRecordTypeCommand(RecordTypeId)` | |

---

## Handler-side Pre-conditions

| Handler | Service | Guard type | Condition |
|---|---|---|---|
| `CreateRecordTypeHandler` | `IRecordTypeUnicityService.NameExistsAsync` | Blocking — `EntityAlreadyExists` | Before `RecordType.Create(...)`; blocks if name already in use within tenant scope |
| `CreateRecordTypeHandler` | `IFieldConstraintValidator.Validate` | Blocking — `InvalidRegexPattern` / `RegexPatternTooComplex` | Iterates `command.InitialFields` if non-null; validates each field before creation |
| `AddFieldToRecordTypeHandler` | `IFieldConstraintValidator.Validate` | Blocking — `InvalidRegexPattern` / `RegexPatternTooComplex` | Before loading aggregate; validates `command.Field` regex syntax and complexity budget |
| `ReplaceFieldInRecordTypeHandler` | `IFieldConstraintValidator.Validate` | Blocking — `InvalidRegexPattern` / `RegexPatternTooComplex` | Before loading aggregate; validates `command.NewField` |
| `UpdateFieldInRecordTypeHandler` | `IFieldConstraintValidator.Validate` | Blocking — `InvalidRegexPattern` / `RegexPatternTooComplex` | Before loading aggregate; validates `command.NewField` |
| `RenameRecordTypeHandler` | `IRecordTypeUnicityService.NameExistsAsync` | Blocking — `EntityAlreadyExists` | Before loading aggregate; blocks if new name already in use within tenant scope |
| `AddCapabilityToRecordTypeHandler` | `ICapabilityRegistry.GetContributedFields` | Blocking — delegates from registry `Result` | Before loading aggregate; resolves `IReadOnlyList<FieldDefinition>` contributed by the capability; result passed to `recordType.AddCapability(capabilityType, fields, addedAt)` |

---

## Write Model Service Interfaces

```csharp
/// <summary>
/// Write-side uniqueness check for RecordType names within a tenant.
/// Used by CreateRecordType and RenameRecordType to enforce name uniqueness.
/// Returns true when the name IS ALREADY IN USE — callers block (EntityAlreadyExists) on a true return.
/// Follows *ExistsAsync semantics per the system-wide naming convention.
/// See: System Spec — Cross-Aggregate Constraint Enforcement.
/// </summary>
interface IRecordTypeUnicityService {
    Task<bool> NameExistsAsync(TenantId tenantId, RecordTypeName name, CancellationToken ct = default);
}

/// <summary>
/// Validates FieldDefinition constraint rules before they are applied to the aggregate.
/// Checks regex syntax correctness and complexity budget (100 ms CPU limit).
/// Synchronous — no I/O required.
/// </summary>
interface IFieldConstraintValidator {
    /// <summary>
    /// Returns DomainError.InvalidRegexPattern or DomainError.RegexPatternTooComplex on failure.
    /// Returns Unit on success.
    /// </summary>
    Result<Unit, DomainError> Validate(FieldDefinition field);
}

/// <summary>
/// Registry of FieldDefinitions contributed by platform capabilities.
/// Used by AddCapabilityToRecordType to resolve the field set that a
/// capability injects into the schema.
/// Synchronous — backed by an in-process registry, no I/O.
/// </summary>
interface ICapabilityRegistry {
    /// <summary>
    /// Returns the FieldDefinitions contributed by the given capability type.
    /// Each returned field has SourceCapability set to capabilityType.
    /// Returns DomainError if the capability type is unknown.
    /// </summary>
    Result<IReadOnlyList<FieldDefinition>, DomainError> GetContributedFields(string capabilityType);
}

enum MetadataFieldType {  
    Boolean,  
    Integer,  
    IntegerArray,  
	Number,  
    NumberArray,  
    String,  
    StringArray,  
    Text,  
    Date,  
    DateTime  
}

```

### `IRecordTypeUnicityService` — usage

| Handler | Method | When |
|---|---|---|
| `CreateRecordTypeHandler` | `NameExistsAsync` | Before `RecordType.Create(...)`; `true` return → `EntityAlreadyExists` |
| `RenameRecordTypeHandler` | `NameExistsAsync` | Before loading aggregate; `true` return → `EntityAlreadyExists` |

### `IFieldConstraintValidator` — usage

| Handler | Method | When |
|---|---|---|
| `CreateRecordTypeHandler` | `Validate` | Per each `InitialField` in `command.InitialFields` (if non-null), before `RecordType.Create(...)` |
| `AddFieldToRecordTypeHandler` | `Validate` | Before loading aggregate; validates `command.Field` |
| `UpdateFieldInRecordTypeHandler` | `Validate` | Before loading aggregate; validates `command.NewField` |
| `ReplaceFieldInRecordTypeHandler` | `Validate` | Before loading aggregate; validates `command.NewField` |

### `ICapabilityRegistry` — usage

| Handler | Method | When |
|---|---|---|
| `AddCapabilityToRecordTypeHandler` | `GetContributedFields` | Before loading aggregate; resolved fields passed to `recordType.AddCapability(...)` |

---

## Constraint Enforcement — Implementation Notes

### `IRecordTypeUnicityService` Implementation

Backed by `media-name-reservations` using scope key `RECORDTYPE`. Returns