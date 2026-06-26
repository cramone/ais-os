# MediaProfile — API

_Context: `Catalog`_
_Aggregate: `MediaProfile`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints.
- **Idempotency:** All mutating endpoints (POST, PUT, PATCH, DELETE) accept `IdempotencyKey: <uuid>`. Replaying the same key within the TTL returns the cached response. See [§Idempotency](../../../../shared/api-conventions.md#idempotency).
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457 `ProblemDetails`). See [§Error Contract](../../../../shared/api-conventions.md#error-contract--rfc-9457-problemdetails).

---

## Route Structure

```
POST   /v1/catalog/profiles                                              Create
POST   /v1/catalog/profiles/{profileId}/draft                           Open revision draft
POST   /v1/catalog/profiles/{profileId}/asset-definitions               Add asset definition
PATCH  /v1/catalog/profiles/{profileId}/asset-definitions/{roleName}    Update
DELETE /v1/catalog/profiles/{profileId}/asset-definitions/{roleName}    Remove
POST   /v1/catalog/profiles/{profileId}/asset-definitions/reorder       Reorder
PUT    /v1/catalog/profiles/{profileId}/asset-definitions/{roleName}/default  Set default
POST   /v1/catalog/profiles/{profileId}/record-types/{recordTypeId}     Attach RecordType
PUT    /v1/catalog/profiles/{profileId}/record-types/{recordTypeId}/version  Update version
DELETE /v1/catalog/profiles/{profileId}/record-types/{recordTypeId}     Detach RecordType
PUT    /v1/catalog/profiles/{profileId}/review-policy                   Set review policy
PUT    /v1/catalog/profiles/{profileId}/checkout-policy                 Set checkout policy
PUT    /v1/catalog/profiles/{profileId}/capabilities                    Set capabilities
DELETE /v1/catalog/profiles/{profileId}/draft                           Discard draft
POST   /v1/catalog/profiles/{profileId}/publish                         Publish draft
POST   /v1/catalog/profiles/{profileId}/deprecate                       Deprecate

GET    /v1/catalog/profiles/{profileId}                                 Get detail
GET    /v1/catalog/profiles                                             List by owner
GET    /v1/catalog/profiles/{profileId}/versions                        List versions
GET    /v1/catalog/profiles/{profileId}/versions/{version}              Get version detail
```

---

## Authorization

| Endpoint | Requirement |
|---|---|
| All write endpoints | `caller.owner_id == mediaProfile.OwnerId` |
| Read endpoints | Owner or `OwnerId = "owner_system"` |

---

## Write Endpoints (selected)

### `POST /v1/catalog/profiles`

**Request:**
```json
{
  "mediaProfileId": "018e4c7a-...",
  "name": "Film Record Profile",
  "description": "Profile for cataloguing film entries"
}
```

**Response `201 Created`:**
```json
{ "id": "018e4c7a-..." }
```

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/profile-name-conflict",
  "title": "Profile name already in use",
  "status": 409,
  "detail": "A MediaProfile named 'Film Record Profile' already exists for this owner.",
  "extensions": { "errorCode": "ProfileNameConflict" }
}
```

---

### `POST /v1/catalog/profiles/{profileId}/asset-definitions`

**Request:**
```json
{
  "roleName": "primary-image",
  "acceptedContentTypes": ["Image"],
  "isRequired": true,
  "allowMultiple": false,
  "maxFileSizeBytes": null,
  "dimensionConstraints": null
}
```

**Response `204 No Content`** — no body.

**Errors:** `409` — draft does not exist · `409` — `roleName` already exists.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — no draft):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/no-active-draft",
  "title": "No active draft",
  "status": 409,
  "detail": "MediaProfile 018e4c7a-... has no active draft. Call POST /v1/catalog/profiles/{id}/draft first.",
  "extensions": { "errorCode": "NoActiveDraft" }
}
```

---

### `POST /v1/catalog/profiles/{profileId}/record-types/{recordTypeId}`

Attaches a published RecordType version to the draft.

**Request:**
```json
{ "version": 3 }
```

**Response `204 No Content`** — no body.

**Errors:** `409` — draft does not exist · `404` — `{recordTypeId, version}` not found in published versions · `409` — RecordType is deprecated.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — deprecated RecordType):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/record-type-deprecated",
  "title": "RecordType is deprecated",
  "status": 409,
  "detail": "RecordType 018e4c7b-... is deprecated and cannot be attached to a new draft.",
  "extensions": { "errorCode": "RecordTypeDeprecated" }
}
```

---

### `PUT /v1/catalog/profiles/{profileId}/record-types/{recordTypeId}/version`

Updates the pinned version for an already-attached RecordType.

**Request:**
```json
{ "version": 4 }
```

**Response `204 No Content`** — no body.

**Errors:** `409` — RecordType not currently attached · `404` — version does not exist.

_Accepts `IdempotencyKey` header._

**Error response example (`404 Not Found`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/record-type-version-not-found",
  "title": "RecordType version not found",
  "status": 404,
  "detail": "RecordType 018e4c7b-... version 4 does not exist in published versions.",
  "extensions": { "errorCode": "RecordTypeVersionNotFound" }
}
```

---

### `PUT /v1/catalog/profiles/{profileId}/review-policy`

**Request:**
```json
{ "reviewPolicy": "RequiredForPublish" }
```

Valid values: `"None"`, `"RequiredForPublish"`

**Response `204 No Content`** — no body.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — no draft):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/no-active-draft",
  "title": "No active draft",
  "status": 409,
  "detail": "MediaProfile 018e4c7a-... has no active draft. Open a revision draft first.",
  "extensions": { "errorCode": "NoActiveDraft" }
}
```

---

### `PUT /v1/catalog/profiles/{profileId}/capabilities`

**Request:**
```json
{ "capabilities": ["Processing", "VersionControl", "Registration"] }
```

Valid values: `"Processing"`, `"VersionControl"`, `"Registration"`, `"DigitalSigning"`

**Response `204 No Content`** — no body.

_Accepts `IdempotencyKey` header._

**Error response example (`403 Forbidden`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/not-resource-owner",
  "title": "Not the resource owner",
  "status": 403,
  "detail": "Caller owner_B does not own MediaProfile 018e4c7a-...",
  "extensions": { "errorCode": "NotResourceOwner" }
}
```

---

### `POST /v1/catalog/profiles/{profileId}/publish`

Publishes the current draft as the next version.

**Response `200 OK`:**
```json
{ "newVersion": 2 }
```

**Errors:** `409` — no draft to publish · `422` — draft is empty.

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity`):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/draft-empty",
  "title": "Draft is empty",
  "status": 422,
  "detail": "MediaProfile 018e4c7a-... draft has no asset definitions or record types. Add content before publishing.",
  "extensions": { "errorCode": "DraftEmpty" }
}
```

---

## Read Endpoints (selected)

### `GET /v1/catalog/profiles/{profileId}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "ownerId": "owner_...",
  "name": "Film Record Profile",
  "status": "Published",
  "publishedVersion": 2,
  "publishedAt": "2026-02-01T10:00:00Z",
  "assetDefinitions": [
    { "roleName": "primary-image", "acceptedContentTypes": ["Image"], "isRequired": true, "allowMultiple": false },
    { "roleName": "trailer",       "acceptedContentTypes": ["Video"], "isRequired": false, "maxFileSizeBytes": 524288000 }
  ],
  "recordTypeRefs": [
    { "recordTypeId": "018e4c7b-...", "version": 3 }
  ],
  "capabilities": ["Processing", "VersionControl"],
  "reviewPolicy": "RequiredForPublish",
  "checkoutPolicy": "None",
  "compiledMetadataFields": [
    { "name": "director", "bareName": "director", "fieldType": "Text", "isRequired": true, "isImmutable": false,
      "recordTypeId": "018e4c7b-...", "recordTypeVersion": 3 },
    { "name": "invoice.amount", "bareName": "amount", "fieldType": "Number", "isRequired": true, "isImmutable": false,
      "recordTypeId": "018e4c81-...", "recordTypeVersion": 2 },
    { "name": "receipt.amount", "bareName": "amount", "fieldType": "Number", "isRequired": false, "isImmutable": false,
      "recordTypeId": "018e4c82-...", "recordTypeVersion": 1 }
  ],
  "suppressedFieldNames": ["amount"],
  "hasDraft": true,
  "draft": {
    "name": "Film Record Profile",
    "description": null,
    "assetDefinitions": [
      { "roleName": "primary-image", "acceptedContentTypes": ["Image"], "isRequired": true, "allowMultiple": false },
      { "roleName": "trailer",       "acceptedContentTypes": ["Video"], "isRequired": false, "maxFileSizeBytes": 524288000 },
      { "roleName": "poster",        "acceptedContentTypes": ["Image"], "isRequired": false, "allowMultiple": true }
    ],
    "recordTypeRefs": [
      { "recordTypeId": "018e4c7b-...", "version": 3 }
    ],
    "capabilities": ["Processing", "VersionControl"],
    "reviewPolicy": "RequiredForPublish",
    "checkoutPolicy": "None",
    "basedOnVersion": 2,
    "createdAt": "2026-03-15T08:30:00Z"
  },
  "createdAt": "2025-11-01T09:00:00Z"
}
```

`draft` is `null` when `hasDraft` is `false`.

`compiledMetadataFields` and `suppressedFieldNames` are derived from `CompiledTemplate` (set at publish time — see [MediaProfile Write Model — Metadata Field Collision Resolution](./mediaprofile.write-model.md#metadata-field-collision-resolution)). Both are empty arrays on a profile that has never been published. A bare field name appearing in `suppressedFieldNames` means it collided across two or more attached RecordTypes — every contributing field is exposed only under its qualified key (`{alias}.{bareName}` or `{recordTypeId}.{bareName}`) in `compiledMetadataFields`, never under the bare key itself. Clients writing metadata via `SetMetadataField`/`SetMetadataBatch`/`BulkSetMetadata` with `origin: "Governed"` must use the qualified key for any field whose `bareName` appears in `suppressedFieldNames`.

---

### `POST /v1/catalog/profiles/{profileId}/deprecate`

Marks the profile as `Deprecated`. Blocked from assignment to new MediaItems immediately. Existing MediaItems that already reference the profile continue to function unaffected — deprecation is not a breaking change for in-use items.

Name reservation is released on success — the profile name becomes available for a new profile.

**Request:** No body.

**Response `202 Accepted`:** No body.

**Auth:** `caller.owner_id == mediaProfile.OwnerId`

_Accepts `IdempotencyKey` header._

**Guards (aggregate):**
- `Status == Published` — Draft-only profiles (never published) cannot be deprecated
- `Draft == null` — Discard the active draft before deprecating

**Errors:**

```json
// 409 — profile is not published
{
  "type": "https://errors.magiqmedia.com/domain/media-profile-not-published",
  "title": "Media profile is not published",
  "status": 409,
  "detail": "Only Published media profiles can be deprecated.",
  "extensions": { "errorCode": "MediaProfileNotPublished" }
}

// 409 — draft in progress
{
  "type": "https://errors.magiqmedia.com/domain/draft-in-progress",
  "title": "Draft in progress",
  "status": 409,
  "detail": "Media profile 018e4c7a-... has an active draft. Discard the draft before deprecating.",
  "extensions": { "errorCode": "DraftInProgress" }
}
```

---

## Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/profiles` | `CreateMediaProfileCommand` | `MediaProfileCreated` + `MediaProfileDraftCreated` | `MediaProfileProjector` → INSERT |
| `POST /draft` | `CreateMediaProfileRevisionCommand` | `MediaProfileDraftCreated` | `MediaProfileProjector` → `hasDraft=true` |
| `POST /asset-definitions` | `AddAssetDefinitionCommand` | `AssetDefinitionAdded` | `MediaProfileProjector` → draft snapshot |
| `POST /v1/metadata/record-types/{id}` | `AttachRecordTypeToProfileCommand` | `RecordTypeAttachedToProfile` | `MediaProfileProjector` → draft snapshot |
| `PUT /v1/metadata/record-types/{id}/version` | `UpdatePinnedRecordTypeVersionCommand` | `RecordTypeVersionPinnedOnProfile` | `MediaProfileProjector` → draft snapshot |
| `PUT /review-policy` | `SetReviewPolicyCommand` | `ReviewPolicySet` | `MediaProfileProjector` → draft snapshot |
| `PUT /capabilities` | `SetMediaProfileCapabilitiesCommand` | `MediaProfileCapabilitiesSet` | `MediaProfileProjector` → draft snapshot |
| `DELETE /draft` | `DiscardMediaProfileDraftCommand` | `MediaProfileDraftDiscarded` | `MediaProfileProjector` → `hasDraft=false`, clear draft snapshot |
| `POST /publish` | `PublishMediaProfileCommand` | `MediaProfilePublished` | `MediaProfileProjector` → UPDATE summary + INSERT version row |
| `POST /deprecate` | `DeprecateMediaProfileCommand` | `MediaProfileDeprecated` | `MediaProfileProjector` → `status=Deprecated` |
| `GET /v1/catalog/profiles/{id}` | `GetMediaProfileByIdQuery` | — | reads `media-profiles` |
| `GET /versions/{v}` | `GetMediaProfileVersionQuery` | — | reads `media-profiles` |

---

## Related

- [MediaProfile Write Model](./mediaprofile.write-model.md)
- [MediaProfile Read Model](./mediaprofile.read-model.md)
- [RecordType API](../../../Metadata/aggregates/RecordType/recordtype.api.md)
- [Catalog Business 