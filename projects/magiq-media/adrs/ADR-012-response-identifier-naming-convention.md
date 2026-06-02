# ADR-012 — Response Identifier Naming Convention

**Status:** Accepted  
**Date:** 2026-05-26  
**Author:** Chase Ramone

---

## Context

A review of all API response DTOs, read models, and API contracts across magiq-media identified a system-wide inconsistency in how resource identifiers are named:

- Most read models and API contracts exposed the resource's own primary identifier using a type-qualified name (e.g. `MediaItemId`, `FolderId`, `AssetId`) rather than the conventional `Id`.
- Write responses were split — some used `Id` (e.g. `CreateCollectionResponse`, `CreateMediaItemResponse`), others used type-qualified names (e.g. `CreateMediaProfileResponse.ProfileId`, `InitiateRegistrationResponse.RegistrationId`).
- Sub-item models in bulk responses used ad-hoc abbreviations (`ItemId`, `ProfileId`) that diverged from both conventions.
- One implicit operator (`FolderSummaryModel`) silently swapped `CollectionId` and `FolderId` constructor arguments, causing live data corruption.

The inconsistency creates friction for API clients who cannot rely on a predictable property name for the resource's primary key, and makes generic resource-fetching code (e.g. caching, navigation) impossible to write without per-type special casing.

---

## Decision

### Rule 1 — Own identifier is always `Id`

A resource DTO, read model, or API contract exposes its own primary identifier as `Id`. The type of the resource is already expressed by the class name — the qualification is redundant.

```csharp
// WRONG
public sealed record MediaItemDetailModel(string MediaItemId, ...)

// CORRECT
public sealed record MediaItemDetailModel(string Id, ...)
```

### Rule 2 — References to other resources use explicit names

When a DTO carries an identifier that refers to a *different* resource, the full type-qualified name is used to make the relationship unambiguous.

```csharp
// MediaItem response — MediaProfileId and FolderId are foreign references
public sealed record MediaItemDetailModel(
    string Id,              // own ID
    string MediaProfileId,  // foreign reference ✓
    string? FolderId,       // foreign reference ✓
    string? CollectionId,   // foreign reference ✓
    ...
)
```

### Rule 3 — Version sub-resources use the parent ID as a foreign reference

Version sub-resources are identified by the composite key `(ParentId, VersionNumber)` — they have no opaque own ID. The parent identifier is a foreign reference and uses the explicit qualified name.

```csharp
// MediaItemVersionDetailModel — MediaItemId is a foreign reference to the parent
public record MediaItemVersionDetailModel(
    string MediaItemId,  // foreign reference ✓ — not renamed to Id
    int VersionNumber,
    ...
)
```

### Rule 4 — Bulk result sub-items use explicit names

Sub-item models inside bulk response envelopes (`Succeeded`, `Failed`, `Skipped` lists) exist without wrapping type context, so the type qualifier is required.

```csharp
// BulkCreateCollectionsSucceededModel — CollectionId is correct here
public sealed record BulkCreateCollectionsSucceededModel(int Index, string CollectionId, string Name);
```

### Rule 5 — Integration events and cross-context transport contracts are exempt

Integration events and cross-context contracts published to SNS/SQS must be self-describing. They continue to use explicit qualified names (e.g. `JobId`, `AssetId`) because consumers may not have the enclosing type context.

### Rule 6 — Request body IDs follow the reference convention

Caller-provided IDs in request bodies (e.g. `"assetId"` in `POST /v1/assets/uploads`, `"mediaItemId"` in bulk upload items) refer to resources from the caller's perspective — they are references, not owned IDs. Use the explicit qualified name.

---

## Consequences

- All existing read models, API contracts, and write responses have been updated to follow these rules (tracked in `api-id-naming-remediation-plan.md`).
- The spec `*.api.md` files and Postman collections have been updated to reflect the new property names.
- **DynamoDB migration note:** Renaming C# record properties changes the JSON attribute name written to DynamoDB on new projections. Existing projection records retain old attribute names. At deployment, run a full projection rebuild for all affected tables, or use `[JsonPropertyName("oldName")]` as a temporary shim during the migration window — see the remediation plan for recommended approach.
- API clients consuming the read API must update their deserialisation to use `id` instead of the previous type-qualified names.

---

## Alternatives Considered

**Keep type-qualified names everywhere** — dismissed. Inconsistency between write responses (already using `Id`) and read responses (using `MediaItemId` etc.) is confusing for clients and cannot be fixed by a client-side convention alone.

**Rename write responses to match read responses** — dismissed. Write responses using `Id` are correct REST convention. The read-side should converge to match.
