# Metadata — Context Overview

_Context: `Metadata`_

---

## Purpose

Provides reusable, versioned metadata schemas via the `RecordType` aggregate. RecordType definitions are consumed by `MediaProfile` (owned by the `Catalog` context) to validate metadata fields on MediaItems.

---

## Responsibilities

- Define and version metadata schemas (`RecordType` with typed field definitions)
- Enforce the Draft → Publish versioning model for `RecordType`
- Provide schema validation service (`IMetadataValidator`) consumed by Catalog on `RequestPublication`

---

## Aggregates

| Aggregate | Description |
|---|---|
| `RecordType` | Named, versioned metadata schema. Defines typed field definitions. |

> `MediaProfile` has moved to the **Catalog** context. See [Catalog — Context Overview](../Catalog/context-overview.md).

---

## Service Boundaries

- **Owns:** `media-record-types`, `media-record-types` DynamoDB tables
- **Event stream prefixes:** `rt_` (RecordType)
- **Configuration aggregate** — not transactional; no saga involvement

---

## External Dependencies

| Dependency | Type | Usage |
|---|---|---|
| `Catalog` context | Consumer | `media-record-types` read by `MediaProfile` handlers to validate pinned versions |
| `AssetManagement` context | None direct | `AssetDefinition.AcceptedContentTypes` influences `AssignAssetToRole` validation (Catalog-side) |

---

## Event Flows

### Outbound (consumed by other contexts)

| Event | Consumer |
|---|---|
| `RecordTypePublished` | `RecordTypeProjector` → `media-record-types` (schema validation source for `MediaProfile` and `RequestPublication`) |

---

## Integration Events

### Published

Published inline by `RecordTypeIntegrationEventPublisher` (`Metadata.WriteModel`) immediately after the corresponding domain event is persisted. All events target the `media-integration-events` SNS topic.

| C# Record Type | Trigger Domain Event |
|---|---|
| `RecordTypePublishedMessage` | `RecordTypePublished` |
| `RecordTypeDeprecatedMessage` | `RecordTypeDeprecated` |

### Consumed

This context consumes no integration events. `MediaProfile` (in Catalog) reads the `media-record-types` DynamoDB table directly at command time to validate pinned schema versions.

## Integration Event Contracts

### Published

#### `RecordTypePublishedMessage`

**Publisher:** `RecordTypeIntegrationEventPublisher` — triggered by `RecordTypePublished`

```csharp
record RecordTypePublishedMessage(
    string TenantId,
    string RecordTypeId,
    string Name,
    int Version,
    IReadOnlyList<RecordTypeFieldSummary> Fields,
    IReadOnlyList<string> Capabilities,    // Capability tags on the schema (e.g. ["Processing"])
    DateTimeOffset PublishedAt
);

record RecordTypeFieldSummary(
    string FieldName,
    string FieldType,          // "Text" | "Number" | "Date" | "Boolean"
    bool IsRequired,
    bool IsDeprecated,
    string? SourceCapability   // Capability that contributed this field, if any
);
```

> `Capabilities` on a `RecordType` are metadata-schema-level tags, distinct from `MediaProfile` capabilities. They indicate which domain module contributed a field group.

#### `RecordTypeDeprecatedMessage`

```csharp
record RecordTypeDeprecatedMessage(
    string TenantId,
    string RecordTypeId,
    string Name,
    DateTimeOffset DeprecatedAt
);
```

> Consumers (e.g. Notifications) are alerted that this schema version is superseded. Existing `MediaProfile` pins referencing this `RecordTypeId` and version remain valid — deprecation is advisory, not a hard invalidation.

---

## Ubiquitous Language

| Term | Definition |
|---|---|
| `RecordType` | A named, versioned set of typed field definitions. The schema for metadata. |
| `FieldDefinition` | A single metadata field: `{ FieldName, FieldType, IsRequired, ValidationRules }`. `FieldType` is immutable — use `ReplaceFieldInRecordType` for type changes. |
| `RecordTypeVersion` | A pinned reference: `{ RecordTypeId, Version }`. MediaProfiles (in Catalog) pin specific published versions. |
| `Draft → Publish` | `RecordType` follows this versioning model. Mutations operate on a draft; `PublishRecordType` creates an immutable snapshot and increments the version number. |
| `MigrationNote` | Required on `ReplaceFieldInRecordType` — documents the migration rationale. |

---

## Related

- [RecordType Write Model](./aggregates/RecordType/recordtype.write-model.md)
- [RecordType Read Model](./aggregates/RecordType/recordtype.read-model.md)
- [RecordType API](./aggregates/RecordType/recordtype.api.md)
- [Metadata Business Scenarios](./business-scenarios.md)
- [Catalog Context Overview](../Catalog/context-overview.md) — MediaProfile is owned here
- [MediaItem Write Model](../Catalog/aggregates/MediaItem/mediaitem.write-model.md)
