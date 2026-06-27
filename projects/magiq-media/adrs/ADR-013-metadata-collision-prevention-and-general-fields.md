# ADR-013 — Metadata Field-Name Collision Prevention & General Metadata Fields

**Status:** Accepted
**Date:** 2026-06-24
**Author:** Chase Ramone

---

## Context

A `MediaProfile` can pin more than one `RecordType` (`RecordTypeRefs` is a list). Nothing previously detected or prevented two attached `RecordType`s from defining a field with the same `Name` — `MediaProfileDomainService.CompileTemplateAsync` merged fields unconditionally into a dictionary keyed by bare field name, so a collision silently dropped one field's definition in favour of whichever `RecordType` was processed last. A caller writing `"status"` against a profile with two RecordTypes that both define `status` had no way to know, and no way to control, which RecordType's field they were actually setting.

Separately, `MediaItem` had no supported way to carry free-form metadata not governed by any `RecordType` schema. `Folder` has this already (fully unvalidated, free-form); `MediaItem` strictly rejected unknown field names in `SetMetadataField` but inconsistently *accepted* them in `SetMetadataBatch` — a pre-existing implementation asymmetry, not an intentional behaviour, that this ADR also closes.

This decision is scoped to `MediaItem` only. `Folder` metadata remains fully free-form and is explicitly out of scope.

---

## Decision

### 1. Collision resolution happens once, at `MediaProfile` compile time

`MediaProfileDomainService.CompileTemplateAsync` now groups all non-deprecated fields contributed by every attached `RecordType` by bare `Name`:

- **No collision** (exactly one contributing field for that name) → emitted under the bare key only.
- **Collision** (two or more contributing RecordTypes define the same bare name) → the bare key is **never** emitted. Each contributing field is instead re-keyed: if its owning `RecordType` has one or more `Aliases`, the field is emitted once per alias (`{alias}.{bareName}`); if the owning `RecordType` has **no** aliases, it falls back to the guaranteed-unique `{RecordTypeId}.{bareName}` key. The two are **not** both emitted for the same field — a RecordType with aliases is only reachable via its alias-qualified keys, not also via its GUID-qualified key. (An earlier draft of this ADR stated the fallback was "always also" emitted in addition to aliases; that was corrected during implementation review to match what was actually built and already documented in the MediaProfile write-model spec — see Open Question below.)

This is computed once and baked immutably into `MediaProfileSnapshotField`/`MediaItem.SnapshotFields` at compile/publish time — it is never recomputed at write time, so a later `RecordType` alias change cannot retroactively change what an already-created `MediaItem` accepts.

The set of bare names that were suppressed due to collision is tracked alongside the compiled fields (`MediaProfileSnapshot.SuppressedFieldNames`) so that both API clients (via `GET /v1/catalog/profiles/{profileId}`) and the `MetadataFieldAmbiguous` error payload can tell a caller which qualified forms are valid, instead of leaving them to discover it by trial and error.

### 2. `RecordType` gains `Aliases`

`RecordType.Aliases: IReadOnlyList<RecordTypeAlias>` — zero or more short, lowercase, alphanumeric (+ `_`/`-`, no `.`) qualifiers, unique tenant-wide (same scope as `Name`). Replaced wholesale via `SetRecordTypeAliasesCommand` (`PUT /v1/metadata/record-types/{id}/aliases`) — full-list replace, not granular add/remove, mirroring how `RecordTypeRefs` is revised on a profile. Aliases are pinned into the published version snapshot at `Publish()` time; a later alias change only affects future publishes.

### 3. `MetadataFieldOrigin` is required on every metadata write, with no default

`SetMetadataField`, `SetMetadataBatch`, and `BulkSetMetadata` each entry now carries a required `Origin: MetadataFieldOrigin` (`Governed | General`). There is no default value — omitting it is a validation failure at the API boundary, never silently resolved to either value. This was a deliberate, non-negotiable design constraint: silently defaulting to `General` would let a caller bypass schema governance by accident; silently defaulting to `Governed` would reject legitimate general-purpose writes.

Resolution (`MediaItem.ResolveFieldKey`, shared by both `SetMetadataField` and `SetMetadataBatch`):

- **`Governed`** — resolved against `SnapshotFields`: exact match first, then bare-name match. Zero matches → `MetadataFieldUnknown`. Exactly one match → resolved. Two or more matches → `MetadataFieldAmbiguous` (this case is actually unreachable in practice once collision suppression is correctly applied at compile time, since a colliding bare name is never emitted into `SnapshotFields` in the first place — `MetadataFieldAmbiguous` is raised when a caller supplies a *bare* name that was suppressed, not when bare-name lookup itself returns multiple hits).
- **`General`** — rejected with `MetadataFieldNameReserved` if the name matches any key in `SnapshotFields` (bare or qualified); otherwise accepted unconditionally with no `RecordTypeId`/`RecordTypeVersion` attribution on the stored entry.

### 4. General fields live in the same flat `Metadata` dictionary as governed fields

No separate `SetGeneralMetadataField`/`SetGeneralMetadataBatch` commands, and no separate storage structure. Whether a given key is governed or general is always re-derivable by checking `SnapshotFields.ContainsKey(key)` — `Origin` is a per-write input, not a persisted discriminator.

### 5. Bug fix: `SetMetadataBatch`/`SetMetadataField` asymmetry closed

Prior to this change, `SetMetadataBatch` accepted unknown field names silently (the `fieldDef is not null` check only gated the immutability check, not acceptance), while `SetMetadataField` rejected them. Both methods now share the identical `ResolveFieldKey` resolution path. `SetMetadataBatch` validates every entry before raising any event — atomic, no partial application.

---

## Consequences

- **Breaking API change, accepted without a migration path.** `PUT /v1/catalog/items/{itemId}/metadata` and `POST /v1/catalog/items/bulk/metadata` change `fields` from a `fieldName → value` map to an array of `{ fieldName, value, origin }` entries, because a flat map cannot carry a required per-entry `origin`. `PATCH /v1/catalog/items/{itemId}/metadata/{fieldName}` gains a required `origin` field on its request body. Since the platform has no released version yet, no compatibility shim was added — this lands directly on the current branch.
- Clients building a metadata-entry UI can discover valid qualified field names ahead of time via `compiledMetadataFields`/`suppressedFieldNames` on the `MediaProfile` detail response, rather than only learning about a collision from a `MetadataFieldAmbiguous` rejection.
- `RecordType.Aliases` is a new tenant-wide-unique namespace, independent of `RecordType.Name` uniqueness, with its own validation and conflict error (`InvalidRecordTypeAlias`, `RecordTypeAliasNotUnique`).
- **Known implementation gap, not addressed by this ADR:** `MetadataFieldUnknown`, `MetadataFieldAmbiguous`, and `MetadataFieldNameReserved` are distinct named `DomainError` factory methods, but all three currently map to the generic `InvalidOperation` HTTP error kind rather than dedicated `errorCode` values. Clients must currently disambiguate by parsing `detail` (and the `candidates` extension for the ambiguous case), not by `errorCode`. Similarly, the bulk endpoint (`POST /v1/catalog/items/bulk/metadata`) collapses all three resolution failures into a single generic `FieldNotFound` per-item error code, which is a real divergence from the single-item endpoints' error vocabulary, not just a documentation simplification. Both are flagged as follow-up work, tracked in the MediaItem API spec.
- **Pre-existing, unrelated dead-code finding surfaced during this work:** `SetMetadataBatchRequest.RecordTypeId`/`RecordTypeVersion` are documented in the DTO's XML comments as being "validated server-side against the media item's current RecordType," but `SetMetadataBatchEndpoint.HandleAsync` never reads either property. They are accepted on the wire and silently ignored. This predates this ADR's changes and is not fixed here — flagged for a separate follow-up.

---

## Open Question — surfaced during implementation review, not yet decided

Should a colliding field on a RecordType **with** aliases *also* always be reachable via its `{RecordTypeId}.{bareName}` fallback, in addition to its alias-qualified key(s) — or is alias-only access (current behavior) sufficient?

Arguments for "always also": gives every colliding field one qualified key that is guaranteed never to change even if `RecordType.Aliases` is later replaced wholesale via `SetAliases` (recall aliases are a full-list replace, not additive) — useful for tooling, audit trails, or integrations that want a permanently-stable address. Arguments against: doubles (or more) the number of valid write-keys for the same conceptual field with no value synchronization between them (writing via the alias-qualified key and writing via the GUID-qualified key would land in two unrelated `Metadata.Draft` entries, not one) — this duplicate-write-surface characteristic already exists across multiple aliases on the same RecordType today, so "always also" would just extend an existing pattern, not introduce a new one, but it does grow the field surface for every aliased RecordType.

Current code and the MediaProfile write-model spec agree on alias-only (either/or). This ADR's Decision section above has been corrected to match. No code change was made pending your call on this.

---

## Alternatives Considered

**Qualify every field by `RecordTypeId` always, never by alias** — dismissed. `{RecordTypeId}.{fieldName}` is guaranteed-unique and requires no new `RecordType` concept, but GUIDs are not human-writable or human-readable in API requests, UI forms, or support tickets. Aliases give callers a stable, memorable qualifier while the GUID form remains available as a fallback for RecordTypes that never register one.

**Use `RecordTypeName` as the qualifier instead of a new `Aliases` concept** — dismissed. `RecordType.Name` is meant to be a free-form, possibly-changing display name; reusing it as a wire-stable qualifier would either force `Name` to become immutable (an unrelated, unwanted constraint) or break previously-valid qualified field keys whenever a `RecordType` was renamed. A separate, deliberately-immutable-per-publish `Aliases` list avoids coupling the two concerns.

**Separate `SetGeneralMetadataField`/`SetGeneralMetadataBatch` commands instead of an `Origin` parameter** — dismissed. This would have doubled the command surface and the request DTOs for no real benefit, since governed and general fields live in the same flat dictionary and the only behavioural difference is which validation path an entry takes. A required per-entry `Origin` parameter on the existing commands keeps one API surface and lets a single batch legitimately mix both kinds of fields.

**Default `Origin` to `General` when omitted, for backward compatibility with simpler callers** — dismissed outright. A missing `Origin` defaulting to `General` would let any caller silently bypass RecordType-schema governance simply by omitting a field, which is a real security/data-integrity concern for a compliance-grade platform managing regulated records. Defaulting to `Governed` was equally rejected, since it would silently reject what may have been an intentional general-field write. The chosen design — explicit, required, no default — was non-negotiable for this reason.

**Allow `CompileTemplateAsync` to fail outright when an unresolvable collision is detected** — considered via a hypothetical `RecordTypeFieldCollisionUnresolvable` error, but not adopted. The `{RecordTypeId}.{bareName}` fallback is always available regardless of alias configuration, so compilation never actually needs to fail due to a collision — at worst, a RecordType without a registered alias is only reachable via its GUID-qualified key. The error was specified for completeness during design and intentionally left unimplemented.
