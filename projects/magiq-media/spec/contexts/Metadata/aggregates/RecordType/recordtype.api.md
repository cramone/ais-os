# RecordType — API

_Context: `Metadata`_
_Aggregate: `RecordType`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints.
- **Idempotency:** All mutating endpoints (POST, PUT, PATCH, DELETE) accept `IdempotencyKey: <uuid>`. Replaying the same key within the TTL returns the cached response. See [§Idempotency](../../../../shared/api-conventions.md#idempotency).
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457 `ProblemDetails`). See [§Error Contract](../../../../shared/api-conventions.md#error-contract--rfc-9457-problemdetails).

---

## Route Structure

```
POST   /v1/metadata/record-types                                           Create
POST   /v1/metadata/record-types/{recordTypeId}/draft                      Open draft
POST   /v1/metadata/record-types/{recordTypeId}/fields                     Add field
PATCH  /v1/metadata/record-types/{recordTypeId}/fields/{fieldName}         Update field
PUT    /v1/metadata/record-types/{recordTypeId}/fields/{fieldName}         Replace field (type change)
DELETE /v1/metadata/record-types/{recordTypeId}/fields/{fieldName}         Remove field
POST   /v1/metadata/record-types/{recordTypeId}/fields/reorder             Reorder fields
POST   /v1/metadata/record-types/{recordTypeId}/capabilities               Add capability
DELETE /v1/metadata/record-types/{recordTypeId}/capabilities/{capabilityType}  Remove capability
POST   /v1/metadata/record-types/{recordTypeId}/draft/fields/{fieldName}/deprecate  Deprecate field
DELETE /v1/metadata/record-types/{recordTypeId}/draft                      Discard draft
POST   /v1/metadata/record-types/{recordTypeId}/publish                    Publish
PATCH  /v1/metadata/record-types/{recordTypeId}                            Rename
POST   /v1/metadata/record-types/{recordTypeId}/deprecate                  Deprecate

GET    /v1/metadata/record-types/{recordTypeId}                            Get detail
GET    /v1/metadata/record-types                                           List by owner
GET    /v1/metadata/record-types/{recordTypeId}/versions                   List versions
GET    /v1/metadata/record-types/{recordTypeId}/versions/{version}         Get version detail
```

---

## Authorization

| Endpoint | Requirement |
|---|---|
| All write endpoints | `caller.owner_id == recordType.OwnerId` |
| Read endpoints | Owner or `OwnerId = "owner_system"` |

---

## Write Endpoints (selected)

### `POST /v1/metadata/record-types`

**Request:**
```json
{
  "recordTypeId": "018e4c7a-...",
  "name": "FilmRecord",
  "description": "Schema for cataloguing film entries"
}
```

**Response `201 Created`:**
```json
{ "id": "018e4c7a-..." }
```

**Errors:** `409` — name already exists within owner scope.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/record-type-name-conflict",
  "title": "RecordType name already in use",
  "status": 409,
  "detail": "A RecordType named 'FilmRecord' already exists within this owner scope.",
  "extensions": { "errorCode": "RecordTypeNameConflict" }
}
```

---

### `POST /v1/metadata/record-types/{recordTypeId}/fields`

Adds a field to the current draft.

**Request:**
```json
{
  "fieldName": "release_year",
  "fieldType": "Number",
  "isRequired": true,
  "isSearchable": false,
  "order": 2,
  "description": "Year of original release",
  "minValue": 1888,
  "maxValue": 2100
}
```

**Response `200 OK`** — no body.

**Errors:** `409` — draft does not exist · `409` — `fieldName` already exists in draft.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — duplicate field name):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/field-name-conflict",
  "title": "Field name already exists in draft",
  "status": 409,
  "detail": "A field named 'release_year' already exists in the current draft of RecordType 018e4c7a-...",
  "extensions": { "errorCode": "FieldNameConflict", "fieldName": "release_year" }
}
```

---

### `PUT /v1/metadata/record-types/{recordTypeId}/fields/{fieldName}`

Replaces a field entirely (type change supported). `PUT` semantics — full replacement. `migrationNote` is required. Note: `PUT` and `PATCH` both target `/fields/{fieldName}` — `PATCH` is partial update, `PUT` is full replacement with type-change support. See api-conventions.md §5.2.

**Request:**
```json
{
  "newField": {
    "fieldName": "release_date",
    "fieldType": "Date",
    "isRequired": true,
    "isSearchable": false,
    "order": 2
  },
  "migrationNote": "Migrating from year-only to full date. Existing release_year values orphaned."
}
```

**Response `200 OK`** — no body.

**Errors:** `409` — draft does not exist · `404` — `fieldName` not found in draft · `422` — `migrationNote` is empty.

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity`):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/migration-note-required",
  "title": "Migration note is required",
  "status": 422,
  "detail": "A non-empty migrationNote must be provided when replacing a field type, to document the data impact.",
  "extensions": { "errorCode": "MigrationNoteRequired" }
}
```

---

### `POST /v1/metadata/record-types/{recordTypeId}/capabilities`

Attaches a capability to the current draft. Contributed fields are resolved server-side via `ICapabilityRegistry` — clients only supply the capability type identifier.

**Request:**
```json
{ "capabilityType": "Magiq.Media.Capabilities.DocumentSigning" }
```

**Response `202 Accepted`** — no body.

**Errors:** `409` — no active draft · `409` — capability already attached · `422` — unrecognised capability type · `400` — contributed fields would conflict with existing draft fields or exceed the 100-field limit.

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity` — unrecognised capability):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/unrecognised-capability-type",
  "title": "Unrecognised capability type",
  "status": 422,
  "detail": "Capability type 'Magiq.Media.Capabilities.Unknown' is not registered in ICapabilityRegistry.",
  "extensions": { "errorCode": "UnrecognisedCapabilityType", "capabilityType": "Magiq.Media.Capabilities.Unknown" }
}
```

---

### `DELETE /v1/metadata/record-types/{recordTypeId}/capabilities/{capabilityType}`

Removes a capability from the current draft. All fields contributed by that capability (`SourceCapability == capabilityType`) are also removed.

**Response `204 No Content`** — no body.

**Errors:** `409` — no active draft · `404` — capability not attached · `422` — one or more contributed fields are `IsImmutable = true` (removal blocked).

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity` — immutable fields block removal):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/immutable-fields-block-removal",
  "title": "Immutable fields block capability removal",
  "status": 422,
  "detail": "Capability 'Magiq.Media.Capabilities.DocumentSigning' contributes one or more IsImmutable fields that cannot be removed.",
  "extensions": { "errorCode": "ImmutableFieldsBlockRemoval" }
}
```

---

### `POST /v1/metadata/record-types/{recordTypeId}/draft/fields/{fieldName}/deprecate`

Marks a field in the current draft as deprecated. Deprecated fields remain readable but are excluded from new metadata writes. Useful for schema migrations where immediate removal is unsafe.

**Response `200 OK`** — no body.

**Errors:** `409` — no active draft · `404` — field not found in draft · `422` — field is already deprecated.

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity`):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/field-already-deprecated",
  "title": "Field is already deprecated",
  "status": 422,
  "detail": "Field 'release_year' is already marked as deprecated in the current draft.",
  "extensions": { "errorCode": "FieldAlreadyDeprecated", "fieldName": "release_year" }
}
```

---

### `POST /v1/metadata/record-types/{recordTypeId}/publish`

Publishes the current draft as the next version.

**Response `200 OK`:**
```json
{ "newVersion": 4 }
```

**Errors:** `409` — no draft to publish · `409` — draft is empty.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — no draft):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/no-active-draft",
  "title": "No active draft",
  "status": 409,
  "detail": "RecordType 018e4c7a-... has no active draft to publish. Call POST /v1/metadata/record-types/{id}/draft first.",
  "extensions": { "errorCode": "NoActiveDraft" }
}
```

---

## Read Endpoints (selected)

### `GET /v1/metadata/record-types/{recordTypeId}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "ownerId": "owner_...",
  "name": "FilmRecord",
  "publishedVersion": 3,
  "publishedAt": "2026-01-15T10:00:00Z",
  "hasDraft": true,
  "draftFields": [
    { "fieldName": "director",      "fieldType": "Text",    "isRequired": true,  "order": 1 },
    { "fieldName": "release_date",  "fieldType": "Date",    "isRequired": true,  "order": 2 },
    { "fieldName": "genre",         "fieldType": "MultiEnum","isRequired": false, "order": 3,
      "allowedValues": ["Drama","Thriller","Comedy","Action","Horror"] }
  ],
  "isDeprecated": false,
  "createdAt": "2025-11-01T09:00:00Z"
}
```

---

### `GET /v1/metadata/record-types/{recordTypeId}/versions/{version}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "version": 3,
  "fieldSnapshot": [
    { "fieldName": "director",     "fieldType": "Text",   "isRequired": true, "order": 1 },
    { "fieldName": "release_year", "fieldType": "Number", "isRequired": true, "order": 2,
      "minValue": 1888, "maxValue": 2100 },
    { "fieldName": "genre",        "fieldType": "MultiEnum","isRequired": false,"order": 3 }
  ],
  "publishedAt": "2026-01-15T10:00:00Z"
}
```

---

### `POST /v1/metadata/record-types/{recordTypeId}/deprecate`

Marks the RecordType as `Deprecated`. Existing MediaProfiles already pinned to any version of this type continue to function — deprecation is not breaking for current assignments. No new MediaProfiles may reference any version of a deprecated type.

**Request:** No body.

**Response `202 Accepted`:** No body.

**Auth:** `caller.owner_id == recordType.OwnerId`

_Accepts `IdempotencyKey` header._

**Guards (aggregate):**
- `Version > 0` — must have been published at least once; never-published types cannot be deprecated

**Downstream effects:**
- `RecordTypeDeprecatedIntegrationEvent` published to `media-integration-events`
- Catalog `media-record-types` reference model updated (`IsDeprecated = true` on all version rows) — blocks subsequent `AttachRecordType` and `UpdatePinnedRecordTypeVersion` calls

**Errors:**

```json
// 409 — never published
{
  "type": "https://errors.magiqmedia.com/domain/record-type-not-published",
  "title": "RecordType has not been published",
  "status": 409,
  "detail": "RecordType 018e4c7a-... has never been published and cannot be deprecated.",
  "extensions": { "errorCode": "RecordTypeNotPublished" }
}
```

---

## Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/metadata/record-types` | `CreateRecordTypeCommand` | `RecordTypeCreated` + `RecordTypeDraftCreated` | `RecordTypeProjector` → INSERT |
| `PATCH /v1/metadata/record-types/{id}` | `RenameRecordTypeCommand` | `RecordTypeRenamed` | `RecordTypeProjector` → UPDATE `Name` |
| `POST /v1/metadata/record-types/{id}/draft` | `CreateRecordTypeDraftCommand` | `RecordTypeDraftCreated` | `RecordTypeProjector` → `hasDraft=true` |
| `POST /fields` | `AddFieldToRecordTypeCommand` | `FieldAddedToRecordType` | `RecordTypeProjector` → `draftFields` append |
| `PATCH /fields/{name}` | `UpdateFieldInRecordTypeCommand` | `FieldDefinitionUpdated` | `RecordTypeProjector` → `draftFields` update |
| `PUT /fields/{name}` | `ReplaceFieldInRecordTypeCommand` | `FieldRep