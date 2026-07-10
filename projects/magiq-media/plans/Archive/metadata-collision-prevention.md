# Metadata Field-Name Collision Prevention & General Metadata — Implementation Plan

**Status:** Design locked. Not yet implemented — no spec or code changes made.
**Repos touched:** `magiq-media` (app code), AIS-OS `spec/contexts/Metadata/aggregates/RecordType/`, `spec/contexts/Catalog/aggregates/MediaProfile/`, `spec/contexts/Catalog/aggregates/MediaItem/`. Possibly a new ADR in `adrs/`.
**Why this exists:** A `MediaProfile` can pin more than one `RecordType` (`RecordTypeRefs` is a list). Nothing today detects or prevents two attached `RecordType`s from defining a field with the same `Name` — `MediaProfileDomainService.CompileTemplateAsync` merges fields unconditionally, so a collision currently silently overwrites one field's value with another's at the `MediaItem` level (last-`RecordTypeId`-wins in the dictionary keyed by bare field name). Separately, `MediaItem` had no supported way to carry free-form metadata not governed by any `RecordType` schema (`Folder` has this; `MediaItem` strictly rejects unknown fields in `SetMetadataField` but inconsistently *accepts* them in `SetMetadataBatch` — see Bug Fix below). This plan resolves both, scoped to `MediaItem` only. `Folder` is explicitly out of scope.

---

## 1. Decision Summary

| # | Decision | Locked |
|---|---|---|
| 1 | Collision-qualification happens **once, at `MediaProfile` publish/compile time** (`CompileTemplateAsync`), baked immutably into `MediaProfileSnapshotField`/`MediaItem.SnapshotFields`. Never recomputed at write time. | ✅ |
| 2 | Qualification only applies to fields that **actually collide** across the profile's attached `RecordTypeRefs`. Unique field names stay bare. | ✅ |
| 3 | `RecordType` gains `Aliases: IReadOnlyList<RecordTypeAlias>` (zero or more), unique tenant-wide. Pinned into the published `FieldSnapshot` at `Publish()` time — never drifts for already-pinned profile versions. | ✅ |
| 4 | When a collision is detected for a given field `Name`, the contributing `RecordType`'s field is addressable under **every alias it has** (`{alias}.{Name}`) **and always also** under `{RecordTypeId}.{Name}` (guaranteed-unique fallback). All keys map to the identical `MediaProfileSnapshotField`. | ✅ |
| 5 | If no collision exists for a `Name`, only the bare key is emitted — never alias- or guid-qualified, even if the contributing `RecordType` has aliases set. | ✅ |
| 6 | General (free-form, ungoverned) metadata lives in the **same flat `Metadata` dictionary** as governed fields, not a separate structure. | ✅ |
| 7 | No separate `SetGeneralMetadataField`/`SetGeneralMetadataBatch` commands. `SetMetadataField`/`SetMetadataBatch` gain a **required, non-defaultable** `MetadataFieldOrigin` (`Governed \| General`) per entry. | ✅ |
| 8 | `Origin` has **no implicit default**. Missing/unspecified `Origin` is a validation failure at the API boundary — never silently resolved to `General` (governance bypass risk) or `Governed` (silent reject of legitimate general writes). | ✅ |
| 9 | Bug fix: `SetMetadataBatch` currently accepts unknown field names silently (no guard), while `SetMetadataField` rejects them. Both must reject unknown `Origin = Governed` field names identically once this lands. | ✅ |
| 10 | Alias mutation: single `SetRecordTypeAliasesCommand(RecordTypeId, Aliases[])` — full-list replace, not granular add/remove. Mirrors how other list-shaped properties are revised wholesale elsewhere in the domain (e.g. `RecordTypeRefs` on profile revision). | ✅ |

---

## 2. Domain Model Changes

### `RecordType` (Metadata context)

- New property: `Aliases: IReadOnlyList<RecordTypeAlias>` — optional, defaults to empty list.
- `RecordTypeAlias` — new value object, same shape/constraints as `FieldName`/`RecordTypeName` (`NonEmptyString`, lowercase, alphanumeric + `_`/`-`, **no `.`** — the qualifier separator must never appear inside an alias or `{alias}.{Name}` becomes ambiguous to read, even though it's never parsed back apart programmatically).
- New invariant: each entry in `Aliases` unique **tenant-wide** (same scope as `Name`, not owner-scoped) — mirrors the existing `Name` uniqueness rationale (large enterprises/government tenants, many uncoordinated `RecordType` authors via `OwnerId`).
- New command: `SetRecordTypeAliasesCommand(RecordTypeId, Aliases: string[])` — full replace. Validates each entry against the format constraint and the tenant-wide uniqueness check before applying. No-op (no event) if the new list is identical to the current one.
- New event: `RecordTypeAliasesUpdated { RecordTypeId, OldAliases[], NewAliases[], UpdatedAt }`.
- `Aliases` (as they exist at the moment of `Publish()`) are copied into `FieldSnapshot` alongside the existing `SourceCapability`-style immutable, per-version data. A later `SetRecordTypeAliasesCommand` only affects *future* publishes — it never rewrites an already-published version's pinned aliases, and therefore never changes the meaning of keys already baked into existing `MediaItem.SnapshotFields`.

### `MediaProfile` / `CompiledMetadataTemplate` (Catalog context)

- `CompiledMetadataField` gains nothing new structurally — `RecordTypeId`/`RecordTypeVersion` already present are sufficient to derive every qualified key. What changes is **how many dictionary entries** `CompileTemplateAsync` emits per field.
- `CompileTemplateAsync` rewrite:
  1. As today, fetch each `RecordTypeVersionReference` detail for every `(RecordTypeId, Version)` in `recordTypeRefs`, including its pinned `Aliases` (new field on the reference projection — see §6).
  2. Group all non-deprecated fields **across every attached RecordType** by bare `Name`.
  3. For each group:
     - **Count == 1** → emit one `CompiledMetadataField` keyed by the bare `Name`.
     - **Count > 1** → for *each* contributing field, emit the same `CompiledMetadataField` once per pinned alias (`{alias}.{Name}`) plus once more under `{RecordTypeId}.{Name}`. Never emit the bare key for this group.
- `CompiledMetadataTemplate.ToSnapshot()` / `MediaProfileSnapshotField` — no structural change. The dictionary just gets more (value-equal, multiply-keyed) entries when collisions occur.
- New `DomainError`: `RecordTypeFieldCollisionUnresolvable` — only needed if we ever *require* qualification success; not needed for the current design since the GUID-qualified key is always available as a guaranteed-unique fallback, so compilation never actually fails due to a collision. (No new blocking error here — flagged for completeness, not adopted.)

### `MediaItem` (Catalog context)

- `MetadataFieldOrigin` enum: `Governed | General`.
- `SetMetadataFieldCommand` / `SetMetadataBatchCommand` — each field entry gains a required `Origin: MetadataFieldOrigin` (not nullable, no default).
- `MediaItem.SetMetadataField` / `SetMetadataBatch` resolution, per entry:
  - `Origin == Governed` → `SnapshotFields.TryGetValue(FieldName, ...)`. Miss → reject (`MetadataFieldUnknown`, see §5). Hit → existing validation path (immutability, type/constraint checks) unchanged.
  - `Origin == General` → skip `SnapshotFields` entirely. No schema validation. Reject only if `FieldName` collides with a **reserved word** — see `MetadataFieldNameReserved` below.
  - **Bug fix**: today `SetMetadataBatch` does not reject unknown `Governed`-shaped entries (`fieldDef is not null` only gates the immutability check, not acceptance). This is closed as part of the `Origin` rewrite — both methods now run through identical resolution logic for `Governed` entries.
- New `DomainError`: `MetadataFieldNameReserved` — a `General` entry's `FieldName` exactly matches a key that exists in `SnapshotFields` (i.e. a caller is trying to use the general-field path to write a governed field's slot, bare or qualified). Rejected outright — `Origin` must match what the field actually is, not be used to bypass schema validation on an existing governed key.
- New `DomainError`: `MetadataFieldAmbiguous` — a `Governed` entry's `FieldName` is a bare name that *would* be valid on one of the profile's `RecordType`s but was suppressed from `SnapshotFields` because it collided and was never qualified. Distinguishes "field doesn't exist at all" from "field exists but you must qualify it" — see §4 Scenario 5. Requires the compile step to also record which bare names were *suppressed* (not just which qualified keys were emitted), so the handler can build a helpful error payload (the listing of valid qualified forms).
- `MetadataChangeset` / `Metadata.Current`/`Draft` — no structural change. Origin is a per-write input, not a persisted discriminator field on the changeset itself; whether a given key is governed or general is always re-derivable by checking `SnapshotFields.ContainsKey(key)`.

---

## 3. Validation Rules

| Rule | Applies to | Error | Enforced where |
|---|---|---|---|
| `Origin` must be explicitly present (not null, not omitted) | Every entry in `SetMetadataFieldCommand`/`SetMetadataBatchCommand` | `MetadataFieldOriginRequired` | FastEndpoints DTO → command mapping (nullable `Origin?` on the DTO, validated non-null before mapping). Never relies on enum default value 0. |
| `Origin == Governed` requires `FieldName` present (bare, alias-qualified, or guid-qualified) in `SnapshotFields` | `SetMetadataField`, `SetMetadataBatch` | `MetadataFieldUnknown` | Aggregate method — existing path, now applied uniformly to both methods (closes the asymmetry bug) |
| Bare `FieldName` that exists *somewhere* on the profile but was suppressed due to collision | `SetMetadataField`, `SetMetadataBatch` (Governed) | `MetadataFieldAmbiguous` | Aggregate method, using a suppressed-names set carried on `MediaProfileSnapshot` (new, see §2) |
| `Origin == General` `FieldName` collides with any key already present in `SnapshotFields` | `SetMetadataField`, `SetMetadataBatch` (General) | `MetadataFieldNameReserved` | Aggregate method |
| `RecordType.Aliases[i]` format: non-empty, lowercase, alphanumeric + `_`/`-`, no `.` | `SetRecordTypeAliasesCommand` | `InvalidRecordTypeAlias` | Handler-side validator, same pattern as `IFieldConstraintValidator` |
| `RecordType.Aliases[i]` unique tenant-wide (across all `RecordType`s, not just within one) | `SetRecordTypeAliasesCommand` | `RecordTypeAliasNotUnique` | New `IRecordTypeUnicityService.AliasExistsAsync`, same scope-key pattern as `NameExistsAsync` |
| `RecordType.Aliases[i]` immutable per published version once baked into `FieldSnapshot` | — (informational) | — | Enforced by construction — `Publish()` copies current `Aliases`, future `SetRecordTypeAliasesCommand` calls only affect later publishes |

---

## 4. Scenarios & Examples

Setup: `MediaProfile "vehicle-shipment"` pins two RecordTypes:
- `ShippingDocs` (`RecordTypeId = RT-A`), `Aliases = ["shipping", "ship"]`, fields: `status`, `carrier`.
- `ComplianceRecord` (`RecordTypeId = RT-B`), `Aliases = []` (never set), fields: `status`, `auditedBy`.

Both define `status` → collision. `carrier` and `auditedBy` are each unique → no collision.

### Scenario 1 — Unique field, no prefix needed

```
SetMetadataField { FieldName: "carrier", Value: "DHL", Origin: Governed }
```
`SnapshotFields["carrier"]` exists (bare key, no collision for this name) → resolves to `ShippingDocs.carrier`. Accepted.

### Scenario 2 — Collision, alias-qualified

```
SetMetadataField { FieldName: "shipping.status", Value: "InTransit", Origin: Governed }
SetMetadataField { FieldName: "compliance.status", ... }   ← rejected, see Scenario 4
```
`SnapshotFields["shipping.status"]` exists (alias-qualified key for `RT-A`) → resolves to `ShippingDocs.status`. Accepted.

### Scenario 3 — Collision, second alias for the same RecordType

```
SetMetadataField { FieldName: "ship.status", Value: "InTransit", Origin: Governed }
```
`SnapshotFields["ship.status"]` — same `CompiledMetadataField` instance as `shipping.status`, just a second alias key. Resolves identically. Accepted. (Both `shipping.status` and `ship.status` are valid spellings of the same write — callers may use either.)

### Scenario 4 — Collision, no alias set → GUID fallback only

```
SetMetadataField { FieldName: "compliance.status", ..., Origin: Governed }   ← rejected, "compliance" is not a registered alias
SetMetadataField { FieldName: $"{RT-B}.status", Value: "Audited", Origin: Governed }  ← accepted
```
`ComplianceRecord` never registered an alias, so the only qualified form that exists in `SnapshotFields` for its `status` field is the raw-GUID key `{RT-B}.status`. `"compliance.status"` was never emitted by `CompileTemplateAsync` — it's just an unrecognized string, rejected as `MetadataFieldUnknown`, not specially detected as "almost right."

### Scenario 5 — Ambiguous bare name

```
SetMetadataField { FieldName: "status", Value: "InTransit", Origin: Governed }
```
`SnapshotFields` has no bare `"status"` key — it was suppressed at compile time because two RecordTypes define it. Rejected with `MetadataFieldAmbiguous`, payload lists the valid qualified forms: `["shipping.status", "ship.status", "{RT-A}.status", "{RT-B}.status"]` (no alias case for `RT-B`, so it shows the GUID form only).

### Scenario 6 — General (free-form) field

```
SetMetadataField { FieldName: "internal_note", Value: "Customer called twice", Origin: General }
```
`internal_note` is not present anywhere in `SnapshotFields` and `Origin = General` → bypasses schema validation entirely, written unconditionally. No `RecordTypeId`/`RecordTypeVersion` attribution on the stored entry.

### Scenario 7 — General field collides with a reserved (governed) key

```
SetMetadataField { FieldName: "carrier", Value: "spoofed", Origin: General }
```
`"carrier"` exists in `SnapshotFields` (it's `ShippingDocs.carrier`). Rejected with `MetadataFieldNameReserved` — a caller cannot use `Origin = General` to write into a slot that's actually governed, even though the value would otherwise be schema-valid by coincidence.

### Scenario 8 — Missing `Origin`

```
SetMetadataField { FieldName: "carrier", Value: "DHL" }   ← Origin omitted from request body
```
Rejected at the API boundary with `MetadataFieldOriginRequired`, before the command ever reaches the aggregate. Never silently treated as `Governed` or `General`.

### Scenario 9 — Batch with mixed Origins (the asymmetry-bug regression case)

```
SetMetadataBatch {
  Fields: [
    { FieldName: "carrier", Value: "DHL", Origin: Governed },
    { FieldName: "internal_note", Value: "expedited", Origin: General },
    { FieldName: "made_up_field", Value: "x", Origin: Governed }   ← must now be rejected
  ]
}
```
Today, `made_up_field` would silently succeed with a null `RecordTypeId`/`RecordTypeVersion` on the stored entry — the exact asymmetry bug. After this change, the whole batch is validated entry-by-entry before any event is raised; `made_up_field` fails `MetadataFieldUnknown` and the entire batch command is rejected (atomic — no partial application), matching `SetMetadataField`'s existing behavior.

---

## 5. New / Changed `DomainError`s

| Error | Trigger | Existed before? |
|---|---|---|
| `MetadataFieldOriginRequired` | `Origin` missing on a command entry | No |
| `MetadataFieldUnknown` | `Governed` entry, `FieldName` not in `SnapshotFields` under any form | Renamed/clarified — today's message is `"Field {fieldName} unknown."` via generic `InvalidOperation`; promoted to a named `DomainError` for consistent API mapping |
| `MetadataFieldAmbiguous` | `Governed` entry, bare `FieldName` suppressed due to a collision | No |
| `MetadataFieldNameReserved` | `General` entry, `FieldName` collides with an existing governed key | No |
| `InvalidRecordTypeAlias` | `SetRecordTypeAliasesCommand`, malformed alias string | No |
| `RecordTypeAliasNotUnique` | `SetRecordTypeAliasesCommand`, alias already used tenant-wide | No |

---

## 6. File-by-File Change List

### Spec (AIS-OS)

- `spec/contexts/Metadata/aggregates/RecordType/recordtype.write-model.md` — add `Aliases` property, `RecordTypeAlias` value object, `SetRecordTypeAliasesCommand`/`RecordTypeAliasesUpdated`, new invariant row, `IRecordTypeUnicityService.AliasExistsAsync` interface addition, note that `Aliases` is pinned into `FieldSnapshot` at `Publish()`.
- `spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md` — rewrite the `CompileTemplateAsync` description to document the group-by-name / collision-qualification behavior; document that `RecordTypeVersionReference` now also carries `Aliases`.
- `spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` — add `MetadataFieldOrigin` to `SetMetadataFieldCommand`/`SetMetadataBatchCommand` rows; add the three new invariants (`MetadataFieldUnknown` promotion, `MetadataFieldAmbiguous`, `MetadataFieldNameReserved`) to the Invariants table; document the suppressed-names tracking on `MediaProfileSnapshot`; note the `SetMetadataBatch` bug fix explicitly so it isn't mistaken for a new behavior in review.
- New ADR: `adrs/ADR-013-metadata-collision-prevention-and-general-fields.md` — captures the alternatives considered (RecordTypeId-only qualifier, RecordTypeName-as-key — rejected, separate `SetGeneralMetadataBatch` — rejected) and the final decision, per the existing ADR convention (Context / Decision / Consequences / Not Chosen).
- `spec/contexts/Metadata/aggregates/RecordType/recordtype.api.md` — new `PUT .../aliases` endpoint, `aliases` field on `GET` detail response, traceability row. See §7.1.
- `spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.api.md` — new `compiledMetadataFields`/`suppressedFieldNames` on `GET /v1/catalog/profiles/{profileId}`. See §7.2.
- `spec/contexts/Catalog/aggregates/MediaItem/mediaitem.api.md` — `origin` added to `PATCH .../metadata/{fieldName}`; breaking shape change (map → array) on `PUT .../metadata` and `POST .../bulk/metadata`; new error response shapes. See §7.3.

### Code (`magiq-media`)

- `Metadata.Domain` — `RecordType` aggregate: `Aliases` property, `RecordTypeAlias` value object, `SetAliases` method, `RecordTypeAliasesUpdated` event, `Apply` handler. `FieldSnapshot` (or wherever per-version data is captured at `Publish()`) gains `Aliases`.
- `Metadata.WriteModel.Infrastructure` — `IRecordTypeUnicityService` gains `AliasExistsAsync`; backing implementation extends the `media-name-reservations` scope-key pattern (e.g. `RECORDTYPE_ALIAS` scope) alongside the existing `RECORDTYPE` name scope.
- `Metadata.Application` (or wherever commands/handlers live) — `SetRecordTypeAliasesCommand`, `SetRecordTypeAliasesHandler` (validates format + uniqueness for each entry, then calls `recordType.SetAliases(...)`).
- `Catalog.Domain` — `CompiledMetadataField` / `CompiledMetadataTemplate` — no structural change. `MediaProfileSnapshot` gains a `SuppressedFieldNames: IReadOnlyList<string>` (or similar) to support `MetadataFieldAmbiguous`.
- `Catalog.WriteModel.Infrastructure.Services.MediaProfiles.MediaProfileDomainService.CompileTemplateAsync` — rewrite per §2 (group-by-name, multi-key emission, suppressed-name tracking). Requires `RecordTypeVersionReference`/`RecordTypeVersionDetail` projection to carry `Aliases` (new field — projector update needed in Metadata's publish-fanout).
- `Catalog.Domain.Aggregates.MediaItems.MediaItem` — `SetMetadataField`/`SetMetadataBatch` rewritten to share one resolution path keyed by `Origin`; new guard clauses for `MetadataFieldAmbiguous`/`MetadataFieldNameReserved`.
- `Catalog.Application` — `SetMetadataFieldCommand`/`SetMetadataBatchCommand` (and their FastEndpoints request DTOs) gain `Origin` per entry; DTO-level validation for `MetadataFieldOriginRequired` (nullable DTO field, validated non-null before mapping to the non-nullable command field).
- Tests: `SetMetadataBatchHandlerTests` (regression test for the bug-fix scenario — Scenario 9), `CompileTemplateAsyncTests` (new — collision/no-collision/alias/guid-fallback/suppressed-name cases), `PublishMediaProfileHandlerTests` (verify multi-key snapshot emission), `SetRecordTypeAliasesHandlerTests` (new), `RecordTypePublishTests` (verify `Aliases` pinned into `FieldSnapshot`).

---

## 7. API Endpoint Changes

Spec files: `spec/contexts/Metadata/aggregates/RecordType/recordtype.api.md`, `spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.api.md`, `spec/contexts/Catalog/aggregates/MediaItem/mediaitem.api.md`.

### 7.1 New — `RecordType` alias endpoint

```
PUT /v1/metadata/record-types/{recordTypeId}/aliases     Replace aliases (full list)
```

Mirrors `SetRecordTypeAliasesCommand` — full replace, not granular add/remove (Decision #10). Not draft-gated — applies regardless of draft state, same as `PATCH /v1/metadata/record-types/{id}` (rename).

**Auth:** `caller.owner_id == recordType.OwnerId`

**Request:**
```json
{ "aliases": ["shipping", "ship"] }
```

**Response `204 No Content`**

**Errors:**
- `422` `InvalidRecordTypeAlias` — malformed entry (empty, uppercase, contains `.`, etc.)
- `409` `RecordTypeAliasNotUnique` — alias already registered tenant-wide by another `RecordType`

```json
// 409 — alias already taken
{
  "type": "https://errors.magiqmedia.com/domain/record-type-alias-conflict",
  "title": "RecordType alias already in use",
  "status": 409,
  "detail": "Alias 'shipping' is already registered tenant-wide by RecordType 018e4c9f-....",
  "extensions": { "errorCode": "RecordTypeAliasNotUnique", "alias": "shipping" }
}
```

_Accepts `IdempotencyKey` header._

**`GET /v1/metadata/record-types/{recordTypeId}` response** gains an `"aliases": ["shipping", "ship"]` field (current, draft-mutable aliases — not yet pinned). **`GET /v1/metadata/record-types/{recordTypeId}/versions/{version}` response** — each `fieldSnapshot` entry's owning RecordType context should expose the aliases that were pinned at that publish (additive — exact placement TBD at spec-edit time, since `fieldSnapshot` today is a flat field list, not grouped by source RecordType).

**Traceability addition:**

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `PUT /v1/metadata/record-types/{id}/aliases` | `SetRecordTypeAliasesCommand` | `RecordTypeAliasesUpdated` | `RecordTypeProjector` → UPDATE `Aliases` |

### 7.2 New — expose compiled, qualified keys on `MediaProfile`

**Gap found while writing this section:** `GET /v1/catalog/profiles/{profileId}` today returns `recordTypeRefs` but never the compiled, qualified key set (`CompiledMetadataTemplate`/`SnapshotFields`). Without this, a client has no way to discover that `status` is suppressed and must be written as `shipping.status` or `{RT-B}.status` — they'd only find out by trial and error via `MetadataFieldAmbiguous`. Add to the `GET` response:

```json
{
  "...": "...",
  "compiledMetadataFields": [
    { "key": "carrier",            "recordTypeId": "RT-A", "fieldType": "Text" },
    { "key": "shipping.status",    "recordTypeId": "RT-A", "fieldType": "Enum" },
    { "key": "ship.status",        "recordTypeId": "RT-A", "fieldType": "Enum" },
    { "key": "018e4c7b-....status","recordTypeId": "RT-A", "fieldType": "Enum" },
    { "key": "018e4c9f-....status","recordTypeId": "RT-B", "fieldType": "Enum" },
    { "key": "auditedBy",          "recordTypeId": "RT-B", "fieldType": "Text" }
  ],
  "suppressedFieldNames": ["status"]
}
```

Without this, `MetadataFieldAmbiguous`'s error payload (§4 Scenario 5) is the *only* place a client ever learns the valid forms — acceptable as a fallback, but a poor discovery experience for building a metadata-entry UI ahead of time. Flagged as required for this plan's API surface, not optional polish.

### 7.3 Breaking — `Origin` required on `MediaItem` metadata-write endpoints

- **`PATCH /v1/catalog/items/{itemId}/metadata/{fieldName}`** — request body gains a required `origin: "Governed" | "General"`. Non-breaking shape (additive field), but a previously-optional-by-omission call now fails closed:

```json
{ "value": "InTransit", "origin": "Governed" }
```

- **`PUT /v1/catalog/items/{itemId}/metadata`** and **`POST /v1/catalog/items/bulk/metadata`** — **breaking shape change**. The current `fields: { "name": value }` map cannot carry a per-entry `origin`. Replace with an array of entries:

```json
{
  "fields": [
    { "fieldName": "shipping.status", "value": "InTransit", "origin": "Governed" },
    { "fieldName": "internal_note",   "value": "Customer called twice", "origin": "General" }
  ],
  "recordTypeId": "018e4c7d-...",
  "recordTypeVersion": 3
}
```

> 🔧 **Breaking change — requires client migration notice**, same convention as the existing R-21/R-23/R-42 flags in `mediaitem.api.md`. Existing callers sending `fields` as an object will fail request validation once this lands; coordinate a version bump or transition window with Akshay (UI/integrations) before deploying.

**New error response shapes:**

```json
// 422 — Origin omitted
{
  "type": "https://errors.magiqmedia.com/validation/metadata-field-origin-required",
  "title": "Metadata field origin is required",
  "status": 422,
  "detail": "Entry 'carrier' is missing a required 'origin' value ('Governed' or 'General').",
  "extensions": { "errorCode": "MetadataFieldOriginRequired", "fieldName": "carrier" }
}

// 422 — unknown governed field
{
  "type": "https://errors.magiqmedia.com/domain/metadata-field-unknown",
  "title": "Metadata field unknown",
  "status": 422,
  "detail": "Field 'made_up_field' is not defined on this MediaItem's compiled metadata schema.",
  "extensions": { "errorCode": "MetadataFieldUnknown", "fieldName": "made_up_field" }
}

// 422 — ambiguous bare name
{
  "type": "https://errors.magiqmedia.com/domain/metadata-field-ambiguous",
  "title": "Metadata field name is ambiguous",
  "status": 422,
  "detail": "Field 'status' is defined by more than one RecordType on this profile and must be qualified.",
  "extensions": {
    "errorCode": "MetadataFieldAmbiguous",
    "fieldName": "status",
    "validForms": ["shipping.status", "ship.status", "018e4c7b-....status", "018e4c9f-....status"]
  }
}

// 422 — general field reserved
{
  "type": "https://errors.magiqmedia.com/domain/metadata-field-name-reserved",
  "title": "Metadata field name is reserved",
  "status": 422,
  "detail": "Field 'carrier' is governed by this MediaItem's RecordType schema and cannot be written with origin 'General'.",
  "extensions": { "errorCode": "MetadataFieldNameReserved", "fieldName": "carrier" }
}
```

`PATCH .../metadata/{fieldName}` and the batch/bulk endpoints share the same error vocabulary — only the per-entry vs. whole-batch framing differs (batch failures reject the entire request atomically, per Decision #1/Scenario 9, so `failed[]` partial-success envelopes do **not** apply to `Governed`/`MetadataFieldUnknown` rejections the way they do for e.g. `DuplicateTitle` in bulk create).

**Traceability table** in `mediaitem.api.md` — existing rows for `SetMetadataBatchCommand`/`MediaItemMetadataSet` and `BulkSetMetadataCommand`/`MediaItemMetadataBatchSet` are unchanged at the command/event/projection level; only the request DTO shape changes.

---

## 8. Explicitly Out of Scope

- `Folder` metadata — remains fully free-form/unvalidated, no `RecordType`/`MediaProfile` relationship. Not touched by this plan.
- Any change to `MediaProfile.RequestPublication`'s required-field gate — it already iterates `SnapshotFields` only, so `General` fields correctly never participate in required-field checks. No change needed.
- Read-model/OpenSearch projection schema for qualified keys (e.g. whether `shipping.status` and `{RT-A}.status` should both be searchable, or only the alias form surfaced in search) — needs a follow-up pass once write-side lands, not blocking this plan.
