# MediaItem — API

_Context: `Catalog`_
_Aggregate: `MediaItem`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints.
- **Idempotency:** All mutating endpoints (POST, PUT, PATCH, DELETE) accept `IdempotencyKey: <uuid>`. Replaying the same key within the TTL returns the cached response. See [§Idempotency](../../../../shared/api-conventions.md#idempotency).
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457 `ProblemDetails`). See [§Error Contract](../../../../shared/api-conventions.md#error-contract--rfc-9457-problemdetails).

---

## Route Structure

```
POST   /v1/catalog/items                                     Create (unscoped)
POST   /v1/catalog/items/bulk                               Bulk create
POST   /v1/catalog/folders/{folderId}/items                  Create in folder
PATCH  /v1/catalog/items/{itemId}                            Update title and/or description
PUT    /v1/catalog/items/{itemId}/folder                     Assign to folder or move (see ADR-014)
PATCH  /v1/catalog/items/{itemId}/metadata/{fieldName}       Set metadata field
PUT    /v1/catalog/items/{itemId}/metadata                   Set metadata batch (full replace)
POST   /v1/catalog/items/{itemId}/roles/{roleName}/assets    Assign asset to role
DELETE /v1/catalog/items/{itemId}/roles/{roleName}/assets/{assetId}  Unassign asset from role
POST   /v1/catalog/items/{itemId}/tags                       Replace tags
POST   /v1/catalog/items/{itemId}/publish                    Publish (immediate if no reviewers; pending approval if reviewers assigned)
POST   /v1/catalog/items/{itemId}/withdraw                   Withdraw
POST   /v1/catalog/items/{itemId}/begin-revision             Begin revision (Published → Revising)
POST   /v1/catalog/items/{itemId}/discard-revision           Discard revision (Revising → Published)
POST   /v1/catalog/items/{itemId}/archive                    Archive
DELETE /v1/catalog/items/{itemId}                            Hard-delete (Archived only)
POST   /v1/catalog/items/{itemId}/approve                    Approve review (reviewer action)
POST   /v1/catalog/items/{itemId}/reject                     Reject review (reviewer action)

GET    /v1/catalog/items/{itemId}                            Get detail
GET    /v1/catalog/folders/{folderId}/items                  List by folder
GET    /v1/catalog/items                                     List by owner / status / unassigned
GET    /v1/catalog/items/search                              Full-text search
GET    /v1/catalog/items/{itemId}/versions                   List versions
GET    /v1/catalog/items/{itemId}/versions/{n}               Get version detail
```

---

## Authorization

| Endpoint | Requirement |
|---|---|
| All write endpoints | `caller.owner_id == mediaItem.OwnerId` |
| `POST /v1/catalog/items/{id}/approve`, `POST /v1/catalog/items/{id}/reject` | Caller must be an assigned reviewer in the active `ReviewSession` |
| Read endpoints | Owner or public Collection visibility |

---

## Write Endpoints (selected)

### `POST /v1/catalog/items`

Creates a MediaItem without immediately assigning it to a media-folder. The media-item lands in the unassigned pool and can be assigned later.

**Request:**
```json
{
  "mediaItemId": "018e4c7a-...",
  "mediaProfileId": "018e4c7b-...",
  "title": "Hero Campaign Image"
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
  "type": "https://errors.magiqmedia.com/domain/media-item-already-exists",
  "title": "Media item already exists",
  "status": 409,
  "detail": "A MediaItem with id 018e4c7a-... already exists for this owner.",
  "extensions": { "errorCode": "MediaItemAlreadyExists" }
}
```

---

### `POST /v1/catalog/folders/{folderId}/items`

Creates a MediaItem pre-assigned to the specified media-folder. Equivalent to `POST /v1/catalog/items` followed by folder assignment, but atomic.

**Request:**
```json
{
  "mediaProfileId": "018e4c7b-...",
  "title": "Hero Campaign Image",
  "description": "Q1 hero banner"
}
```

**Response `201 Created`:**
```json
{ "id": "018e4c7a-...", "title": "Hero Campaign Image", "createdAt": "2026-05-08T10:00:00Z" }
```

> 🔧 **Requires implementation (R-42 · Phase 5):** The implementation must return `201 Created`. The operation is synchronous — a new MediaItem resource is created atomically. Do **not** return `202 Accepted`. This is a breaking change for clients that check status codes; notify callers before deploying.

**Errors:** `400`, `401`, `403`, `404` (media-folder or media-profile not found)

_Accepts `IdempotencyKey` header._

**Error response example (`404 Not Found`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/folder-not-found",
  "title": "Folder not found",
  "status": 404,
  "detail": "Folder 018e4c7c-... does not exist for this tenant.",
  "extensions": { "errorCode": "FolderNotFound" }
}
```

---

### `PATCH /v1/catalog/items/{itemId}`

Partially updates mutable fields on a media item. Supply any combination of `title` and/or `description`. At least one field (or `clearDescription: true`) must be present. Omitting a field leaves it unchanged.

**Preconditions:** `Status == Draft | Revising`, `!IsArchived`. Both guards are enforced by the aggregate — violations return `409`.

**Request:**
```json
{
  "title": "Updated Campaign Image",
  "description": "Q2 hero banner — revised copy",
  "clearDescription": false
}
```

| Field | Type | Notes |
|---|---|---|
| `title` | `string?` | New title. Max 512 chars. Omit to leave unchanged. |
| `description` | `string?` | New description. Max 4000 chars. Omit to leave unchanged. |
| `clearDescription` | `bool` | When `true`, sets description to `null` regardless of the `description` field. Use this to distinguish "no change" from "clear". |

At least one of `title`, `description`, or `clearDescription: true` must be present — an empty body returns `400`.

If both `title` and `description` are supplied, two commands are dispatched sequentially (`UpdateMediaItemTitleCommand` then `UpdateMediaItemDescriptionCommand`). A failure on the second command does not roll back the first.

**Response `204 No Content`**

**Errors:**
- `400` — no fields supplied; or `title` fails validation (empty string, exceeds 512 chars)
- `401` — unauthenticated
- `403` — caller does not own the media item
- `404` — media item not found
- `409` — media item is not in `Draft` or `Revising` status, or is archived

_Accepts `IdempotencyKey` header._

---

### `PATCH /v1/catalog/items/{itemId}/metadata/{fieldName}`

Sets a single metadata field on the media-item.

> 🔧 **`origin` is required (ADR-013).** Every metadata write must declare `origin: "Governed" | "General"`. There is no default — omitting it is a `400`, never silently treated as either value. `"Governed"` resolves `fieldName` against the media item's compiled RecordType schema (`SnapshotFields`); a bare name that collides across two or more RecordTypes contributed to the profile must be qualified (e.g. `invoice.amount`, or the RecordTypeId-qualified fallback) — see [MediaProfile API — `compiledMetadataFields`](../MediaProfile/mediaprofile.api.md#get-v1catalogprofilesprofileid) for how to discover the valid qualified forms. `"General"` is a caller-defined field with no schema backing and must not collide with a Governed field name (bare or qualified).

**Request:**
```json
{
  "value": "Q1 2026 hero banner",
  "origin": "Governed"
}
```

**Response `200 OK`** — no body.

**Errors:**
- `400` — `origin` missing or not one of `Governed`/`General`
- `401` / `403` / `404` — standard auth/ownership/not-found
- `422` — value fails schema validation, or field-name resolution fails (`MetadataFieldUnknown`, `MetadataFieldAmbiguous`, `MetadataFieldNameReserved`) — see error shapes below

_Accepts `IdempotencyKey` header._

**Error response example (`403 Forbidden`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/not-resource-owner",
  "title": "Not the resource owner",
  "status": 403,
  "detail": "Caller owner_B does not own MediaItem 018e4c7a-...",
  "extensions": { "errorCode": "NotResourceOwner" }
}
```

**Metadata field origin/resolution error shapes** (shared across `PATCH .../metadata/{fieldName}` and `PUT .../metadata` — see [§Metadata Field Origin Error Shapes](#metadata-field-origin-error-shapes) below):

```json
// 422 — unknown governed field
{
  "type": "https://errors.magiqmedia.com/domain/invalid-operation",
  "title": "Invalid operation",
  "status": 422,
  "detail": "Field 'made_up_field' is not defined on this media item's record type.",
  "extensions": { "errorCode": "InvalidOperation", "fieldName": "made_up_field" }
}

// 422 — ambiguous bare name
{
  "type": "https://errors.magiqmedia.com/domain/invalid-operation",
  "title": "Invalid operation",
  "status": 422,
  "detail": "Field name 'status' is ambiguous — it is defined by more than one record type contributing to this media item's profile. Use one of the qualified field names instead: shipping.status, 018e4c9f-....status.",
  "extensions": { "errorCode": "InvalidOperation", "fieldName": "status", "candidates": ["shipping.status", "018e4c9f-....status"] }
}

// 422 — general field reserved
{
  "type": "https://errors.magiqmedia.com/domain/invalid-operation",
  "title": "Invalid operation",
  "status": 422,
  "detail": "Field name 'carrier' is reserved by this media item's record type schema and cannot be used as a general field.",
  "extensions": { "errorCode": "InvalidOperation", "fieldName": "carrier" }
}
```

Note: as implemented today, `MetadataFieldUnknown`/`MetadataFieldAmbiguous`/`MetadataFieldNameReserved` are distinct named-error *helper methods* in `MediaItemDomainErrors`, but all three currently map onto the generic `DomainError.InvalidOperation` kind (`errorCode: "InvalidOperation"`) rather than dedicated error codes — the plan's originally proposed distinct `errorCode` values (`MetadataFieldUnknown`, `MetadataFieldAmbiguous`, `MetadataFieldNameReserved`) were not adopted at the HTTP-mapping layer. Clients must currently disambiguate by parsing `detail` / the `candidates` extension, not by `errorCode`. Flagged as a candidate follow-up, not a blocker for this plan.

---

### `PUT /v1/catalog/items/{itemId}/metadata`

Full replacement of the media-item's metadata payload in a single atomic operation. Every entry is resolved against `SnapshotFields` (per [Metadata Field Origin Resolution](./mediaitem.write-model.md#metadata-field-origin-resolution)) and validated before any event is raised — any single entry's resolution or validation failure rejects the entire batch with `422` and no changes are persisted. Prefer this over multiple `PATCH` calls when updating several fields together.

> 🔧 **Breaking shape change (ADR-013):** `fields` is now an **array of entries**, not a `fieldName → value` map. This was required because every entry now carries its own required `origin` and must be independently resolvable (a `Governed` entry resolves against the schema; a `General` entry is rejected if it collides with a reserved name) — a flat map can't carry that per-entry metadata. There is no migration path or compatibility shim; the platform has no released version yet, so this is a straight breaking change.

> ⚠️ **Full replace semantics (R-23):** This is a **complete replacement** of `Metadata.Draft`. Entries omitted from the `fields` array are **cleared** — they will no longer appear in the draft. If you intend to preserve existing field values, read the current draft first and include all fields you wish to retain. There is no merge or partial-update behaviour.

**Request:**
```json
{
  "fields": [
    { "fieldName": "description", "value": "Q1 2026 hero banner", "origin": "General" },
    { "fieldName": "release_year", "value": 2026, "origin": "Governed" },
    { "fieldName": "invoice.amount", "value": 199.99, "origin": "Governed" }
  ],
  "recordTypeId": "018e4c7d-...",
  "recordTypeVersion": 3
}
```

| Field | Type | Notes |
|---|---|---|
| `fields` | `array` | Each entry: `{ fieldName: string, value: <any JSON>, origin: "Governed" \| "General" }`. `origin` is required per entry — there is no batch-level default. |
| `recordTypeId` / `recordTypeVersion` | `string?` / `int?` | **Currently dead.** The DTO carries these (doc comment claims "validated server-side against the media item's current RecordType — mismatches return 422"), but `SetMetadataBatchEndpoint.HandleAsync` never reads `req.RecordTypeId`/`req.RecordTypeVersion` — no such validation is actually wired up. Accepted on the wire but silently ignored. Flagged as a bug (dead validated-looking field, misleading doc comment) — not introduced by this plan, pre-existing, surfaced during this review. |

**Response `204 No Content`**

**Errors:**
- `400`, `401`, `403`, `404` — standard
- `422` — schema validation failure, or origin/resolution failure (`MetadataFieldUnknown`, `MetadataFieldAmbiguous`, `MetadataFieldNameReserved` — see [error shapes under `PATCH .../metadata/{fieldName}`](#patch-v1catalogitemsitemidmetadatafieldname) above; same shapes apply here)

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity` — schema validation failure):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/metadata-invalid",
  "title": "Metadata validation failed",
  "status": 422,
  "detail": "One or more metadata fields failed validation for RecordType FilmRecord v4.",
  "instance": "/v1/catalog/items/018e4c7a-.../metadata",
  "errors": [
    {
      "fieldName": "release_date",
      "code": "required",
      "message": "release_date is required by RecordType FilmRecord v4."
    },
    {
      "fieldName": "runtime_minutes",
      "code": "out_of_range",
      "message": "runtime_minutes must be between 1 and 99999."
    }
  ]
}
```

---

### `POST /v1/catalog/items/{itemId}/roles/{roleName}/assets`

Assigns an existing Asset to the named role on this MediaItem.

**No asset status constraint.** An asset may be assigned at any status — `Pending`, `Validating`, `Processing`, `Active`, etc. Asset status only gates **download** (presigned GET URL issuance): only `Active` and `Archived` assets can be downloaded.

**Request:**
```json
{
  "assetId": "018e4c7e-..."
}
```

**Response `204 No Content`**

**Note:** This command also raises `AssetAttachedToMediaItem` on the Asset aggregate, permanently binding `Asset.MediaItemId`.

_Accepts `IdempotencyKey` header._

**Errors:** `404` (asset or media item not found) · `404` (role name not defined in profile) · `409` (role already filled and `allowMultiple = false`) · `422` (asset content type not accepted by role definition)

**Error response example (`404 Not Found`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/asset-not-found",
  "title": "Asset not found",
  "status": 404,
  "detail": "Asset 018e4c7e-... does not exist or is not accessible to this owner.",
  "extensions": { "errorCode": "AssetNotFound" }
}
```

---

### `DELETE /v1/catalog/items/{itemId}/roles/{roleName}/assets/{assetId}`

Removes the asset assignment from the named role.

**Response `204 No Content`**

**Errors:** `404` — no asset with that id assigned to that role.

_Accepts `IdempotencyKey` header._

**Error response example (`404 Not Found`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/role-assignment-not-found",
  "title": "Role assignment not found",
  "status": 404,
  "detail": "Asset 018e4c7e-... is not assigned to role hero-image on MediaItem 018e4c7a-...",
  "extensions": { "errorCode": "RoleAssignmentNotFound" }
}
```

---

### `POST /v1/catalog/items/{itemId}/publish`

Publishes the media-item. User intent is to publish.

- `reviewerIds` empty → publishes immediately; item transitions directly to `Published` and `MediaItemApproved` is raised synchronously.
- `reviewerIds` non-empty → item transitions to `PendingApproval`; a `ReviewSession` is created on the aggregate. Reviewers cast decisions via `/approve` and `/reject`.
- `commentThreadId` (optional) — links a `MediaChangeRequest` comment thread for this review cycle.

**Request:**
```json
{
  "reviewerIds": ["user_018e4c7b-...", "user_018e4c7c-..."],
  "commentThreadId": "018e4c7d-..."
}
```

Both fields are optional. Omit `reviewerIds` (or send empty array) for auto-approve.

**Response `200 OK`** — auto-approve path (no reviewers):
```json
{ "status": "Published", "versionNumber": 1 }
```

**Response `202 Accepted`** — pending approval path (reviewers assigned):
```
HTTP/1.1 202 Accepted
Location: /v1/catalog/items/018e4c7a-...
Content-Type: application/json

{ "expectedStatus": "PendingApproval" }
```

**Errors:**
- `409` — media-item not in `Draft` status
- `409` — signing session in progress
- `422` — caller appears in `reviewerIds` (`ReviewerIsInitiator`)
- `422` — metadata validation failure (required fields missing per RecordType schema)
- `422` — one or more assigned assets not `Active`

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — invalid status):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/invalid-status-transition",
  "title": "Invalid status transition",
  "status": 409,
  "detail": "MediaItem 018e4c7a-... cannot be published from status Published.",
  "extensions": { "errorCode": "InvalidStatusTransition", "currentStatus": "Published" }
}
```

**Error response example (`422 Unprocessable Entity` — validation failure):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/metadata-invalid",
  "title": "Metadata validation failed",
  "status": 422,
  "detail": "One or more required metadata fields are missing for RecordType FilmRecord v4.",
  "instance": "/v1/catalog/items/018e4c7a-.../publish",
  "errors": [
    {
      "fieldName": "release_date",
      "code": "required",
      "message": "release_date is required by RecordType FilmRecord v4."
    }
  ]
}
```

---

### `DELETE /v1/catalog/items/{itemId}`

Permanently hard-deletes an archived media item. Removes the item from all read models (`media-items`, `media-item-detail`, `child-items`). Publishes `MediaItemDeletedMessage` to `media-integration-events`.

> **Two-step pattern:** The item must already be in `Archived` status. Call `POST /v1/catalog/items/{id}/archive` first. This matches the Asset two-step lifecycle (AM-7). Name reservation and folder counter are already released at archive time — this step only purges read model records and emits the downstream integration event.

**Response `204 No Content`**

**Errors:** `404` (item not found), `409` (item is not `Archived`)

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — not archived):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/invalid-operation",
  "title": "Invalid operation",
  "status": 409,
  "detail": "Media item 018e4c7a-... must be archived before it can be deleted.",
  "extensions": { "errorCode": "InvalidOperation" }
}
```

---

### `POST /v1/catalog/items/{itemId}/begin-revision`

Starts a new revision on a published item. The item transitions to `Revising`. The published version remains live and readable while the owner prepares updates.

`Metadata.Draft` is initialised from `Metadata.Current` — edits begin from the published content.

**Request:** `{ }` (route param `itemId` only)

**Response `204 No Content`**

**Errors:**
- `401` — unauthenticated
- `403` — forbidden (caller is not the owner)
- `404` — item not found
- `409` — item is not in `Published` state

_Accepts `IdempotencyKey` header._

---

### `POST /v1/catalog/items/{itemId}/discard-revision`

Discards all draft changes on a `Revising` item and returns it to `Published`. The published version and version number are unchanged.

**Request:** `{ }` (route param `itemId` only)

**Response `204 No Content`**

**Errors:**
- `401` — unauthenticated
- `403` — forbidden (caller is not the owner)
- `404` — item not found
- `409` — item is not in `Revising` state

_Accepts `IdempotencyKey` header._

---

## Read Endpoints (selected)

### `GET /v1/catalog/items/{itemId}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "folderId": "018e4c7c-...",
  "collectionId": "018e4c7d-...",
  "ownerId": "owner_...",
  "mediaProfileId": "018e4c7b-...",
  "title": "Hero Campaign Image",
  "status": "Draft",
  "metadata": {
    "current": {},
    "draft": { "description": "Q1 2026 hero banner" }
  },
  "media-assets": [
    { "assetId": "018e4c7e-...", "roleName": "hero-image" }
  ],
  "registrationIds": [],
  "tags": [],
  "checkoutStatus": "Available",
  "activeMediaChangeRequestId": null,
  "activeSigningSessionId": null,
  "currentVersionNumber": 0,
  "createdAt": "2026-03-26T10:00:00Z"
}
```

---

### `GET /v1/catalog/folders/{folderId}/items`

Returns paginated MediaItems belonging to the specified media-folder.

> 🔧 **Requires implementation (R-21 · Phase 5):** Sort parameters must be implemented. Default sort is `createdAt desc` (DynamoDB GSI ordering). `title` sort requires a secondary scan — implement only if a GSI covers it.

**Query parameters:**

| Param | Type | Notes |
|---|---|---|
| `status` | `string?` | Filter by `MediaItemStatus` |
| `sortBy` | `string?` | `createdAt` (default) \| `title` |
| `sortOrder` | `string?` | `asc` \| `desc` (default: `desc`) |
| `pageToken` | `string?` | Pagination cursor |
| `pageSize` | `int?` | Default 20, max 100 |

**Response `200 OK`:**
```json
{
  "items": [
    { "id": "...", "title": "...", "status": "Draft", "currentVersionNumber": 0, "createdAt": "..." }
  ],
  "nextPageToken": null
}
```

---

~~`GET /v1/catalog/items/unassigned`~~ — **Removed.** Use `GET /v1/catalog/items?unassigned=true` instead. See `GET /v1/catalog/items` below.

---

### `GET /v1/catalog/items`

Lists MediaItems for the tenant, with optional filtering by owner and status.

**Backed by OpenSearch** — eventual consistency applies. Uses `search_after` cursor pagination (not the DynamoDB `pageToken` model). For exact-item lookup use `GET /catalog/items/{itemId}`; for full-text search use `GET /catalog/items/search`.

**Query parameters:**

| Param | Type | Notes |
|---|---|---|
| `ownerId` | `string?` | Filter by owner member ID |
| `status` | `string?` | Filter by `MediaItemStatus` (e.g. `Draft`, `Published`) |
| `unassigned` | `bool?` | When `true`, returns only items not assigned to any folder. Replaces the former `/catalog/items/unassigned` endpoint. |
| `sortBy` | `string?` | `createdAt` (default) \| `title` |
| `sortOrder` | `string?` | `asc` \| `desc` (default: `desc`) |
| `searchAfter` | `string?` | Opaque cursor from the previous response's `nextSearchAfter`. Omit on the first page. |
| `pageSize` | `int?` | Default 20, max 100 |

**Response `200 OK`:**
```json
{
  "items": [
    { "id": "...", "title": "...", "status": "Draft", "currentVersionNumber": 0, "createdAt": "..." }
  ],
  "pageSize": 20,
  "nextSearchAfter": "WyIyMDI2LTAxLTAxIiwiMDE4ZTRjN2EiXQ=="
}
```

---

### `GET /v1/catalog/items/search`

Full-text search backed by OpenSearch `media-items` index. Accepts `?q=` (query string) plus optional `?status=&folderId=&collectionId=&pageToken=&pageSize=` filters.

**Response `200 OK`:**
```json
{
  "items": [
    { "id": "...", "title": "...", "status": "Draft", "score": 0.94 }
  ],
  "nextPageToken": null
}
```

---

### `POST /v1/catalog/items/{itemId}/approve`

Reviewer casts an approval vote. When all non-withdrawn reviewers have approved, the item transitions to `Published` and `MediaItemApproved` is raised.

**Request:**
```json
{ "decisionComment": "Looks good — metadata is complete." }
```

`decisionComment` is optional.

**Response `204 No Content`** — no body (or `200 OK` with `{ "status": "Published", "versionNumber": N }` when approval triggered publish).

**Errors:**
- `403` — caller is not an assigned reviewer in the active `ReviewSession`
- `409` — caller has already decided
- `409` — media-item not `UnderReview`

_Accepts `IdempotencyKey` header._

**Error response example (`403 Forbidden`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/not-assigned-reviewer",
  "title": "Not an assigned reviewer",
  "status": 403,
  "detail": "User user_bob is not an assigned reviewer on the active review session for MediaItem 018e4c7a-...",
  "extensions": { "errorCode": "NotAssignedReviewer" }
}
```

---

### `POST /v1/catalog/items/{itemId}/reject`

Reviewer casts a rejection vote. The item immediately transitions back to `Draft`. The `ReviewSession` is cleared. Draft metadata is preserved for revision.

**Request:**
```json
{ "reason": "Image resolution does not meet minimum requirements." }
```

`reason` is required.

**Response `204 No Content`** — no body.

**Errors:**
- `403` — caller is not an assigned reviewer in the active `ReviewSession`
- `409` — caller has already decided
- `409` — media-item not `UnderReview`
- `422` — `reason` is empty

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — already decided):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/reviewer-already-decided",
  "title": "Reviewer has already decided",
  "status": 409,
  "detail": "Reviewer user_alice has already submitted a decision (Approved) for this review session.",
  "extensions": { "errorCode": "ReviewerAlreadyDecided", "reviewerStatus": "Approved" }
}
```

---

### `GET /v1/catalog/items/{itemId}/versions`

```json
{
  "versions": [
    { "id": "...", "versionNumber": 1, "approvedAt": "2026-03-26T11:00:00Z" }
  ],
  "nextPageToken": null
}
```

---

## Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/items` | `CreateMediaItemCommand` | `MediaItemCreated` | `MediaItemProjector` → INSERT |
| `POST /v1/catalog/folders/{folderId}/items` | `CreateMediaItemCommand` | `MediaItemCreated` | `MediaItemProjector` → INSERT (media-folder pre-assigned) |
| `PUT /v1/catalog/items/{id}/metadata` | `SetMetadataBatchCommand` | `MediaItemMetadataBatchSet` | `MediaItemProjector` → UPDATE metadata |
| `PATCH /v1/catalog/items/{id}/metadata/{fieldName}` | `SetMetadataFieldCommand` | `MediaItemMetadataFieldSet` | `MediaItemProjector` → UPDATE metadata |
| `PATCH /v1/catalog/items/{id}` | `UpdateMediaItemTitleCommand`, `UpdateMediaItemDescriptionCommand` (per field present) | `MediaItemTitleUpdated`, `MediaItemDescriptionUpdated` | `MediaItemProjector` → UPDATE `Title` / `Description` |
| `PUT /v1/catalog/items/{id}/folder` | `AssignMediaItemToFolderCommand` or `MoveMediaItemCommand` (if already assigned) | `MediaItemAssignedToFolder` or `MediaItemMoved` | `MediaItemProjector` → UPDATE folder/collection, remove `UnassignedIndex` on first assign |
| `POST /v1/catalog/items/{id}/tags` | `TagMediaItemCommand` | `MediaItemTagged` | `MediaItemProjector` → UPDATE `Tags` |
| `POST /v1/catalog/items/{id}/roles/{role}/assets` | `AssignAssetToRoleCommand` | `AssetAssignedToRole` | `MediaItemProjector` → UPDATE roles |
| `DELETE /v1/catalog/items/{id}/roles/{role}/assets/{assetId}` | `UnassignAssetFromRoleCommand` | `AssetUnassignedFromRole` | `MediaItemProjector` → UPDATE roles |
| `POST /v1/catalog/items/{id}/publish` (no reviewers) | `PublishMediaItemCommand` | `MediaItemApproved` | `MediaItemProjector` → status UPDATE + version; `MediaItemVersionProjector` → INSERT snapshot |
| `POST /v1/catalog/items/{id}/publish` (with reviewers) | `PublishMediaItemCommand` | `MediaItemPublicationRequested` | `MediaItemProjector` → status UPDATE → PendingApproval, ReviewSession |
| `POST /v1/catalog/items/{id}/approve` | `ApproveReviewCommand` | `MediaItemApproved` (when all approved) | `MediaItemProjector` → status + version; `MediaItemVersionProjector` → INSERT snapshot |
| `POST /v1/catalog/items/{id}/reject` | `RejectReviewCommand` | `MediaItemRejected` | `MediaItemProjector` → status UPDATE (→ Draft), ReviewSession cleared |
| `POST /v1/catalog/items/{id}/withdraw` | `WithdrawMediaItemCommand` | `MediaItemWithdrawn` | `MediaItemProjector` → status UPDATE (→ Draft) |
| `POST /v1/catalog/items/{id}/begin-revision` | `BeginRevisionCommand` | `MediaItemRevisionStarted` | `MediaItemProjector` → status UPDATE (→ Revising), Metadata.Draft seeded from Current |
| `POST /v1/catalog/items/{id}/discard-revision` | `DiscardRevisionCommand` | `MediaItemRevisionDiscarded` | `MediaItemProjector` → status UPDATE (→ Published), Metadata.Draft cleared |
| `POST /v1/catalog/items/{id}/archive` | `ArchiveMediaItemCommand` | `MediaItemArchived` | `MediaItemProjector` → status UPDATE |
| `DELETE /v1/catalog/items/{id}` | `DeleteMediaItemCommand` | `MediaItemDeleted` | `MediaItemProjector` → DELETE; `FolderChildSummaryProjector` → DELETE |
| `GET /v1/catalog/items/{id}` | `GetMediaItemByIdQuery` | — | reads `media-item-detail` |
| Search | `SearchMediaItemsQuery` | — | reads OpenSearch `media-items` |

---

## Related

- [MediaItem Write Model](./mediaitem.write-model.md)
- [MediaItem Read Model](./mediaitem.read-model.md)
- [Catalog Business Scenarios](../../business-scenarios.md)
- [ChangeRequests context](../../../ChangeRequests/context-overview.md)

---

## Bulk Write Endpoints

> Bulk operations follow the shared partial-success envelope. See [`spec/shared/bulk-operations.md`](../../../../shared/bulk-operations.md) for full conventions: `onError`, `onDuplicate`, `BulkItemError`, retry behaviour, and idempotency.

### `POST /v1/catalog/items/bulk`

Creates up to 200 media media-items in a single request. All media-items must target an existing, non-archived media-folder. Title uniqueness is checked per media-folder scope using a single `BatchGetItem` call (Tier 1) before any writes.

**Pre-flight per media-item:**
1. `folderId` must reference an existing, non-archived media-folder.
2. `mediaProfileId` must reference a `Published` media media-profile.
3. Title uniqueness is checked within the media-folder scope — subject to `onDuplicate` strategy.

**Profile caching:** The handler caches each resolved media-profile snapshot by `mediaProfileId` within the request — media-profiles shared across multiple media-items incur only one DynamoDB read.

**Request:**
```json
{
  "media-items": [
    {
      "mediaItemId": "018f...",
      "mediaProfileId": "018e...",
      "title": "Chinatown — Director's Cut",
      "description": "4K restoration",
      "folderId": "018d..."
    },
    {
      "mediaItemId": "018g...",
      "mediaProfileId": "018e...",
      "title": "Vertigo — Restored Edition",
      "folderId": "018d..."
    }
  ],
  "onError": "ContinueOnError",
  "onDuplicate": "Reject"
}
```

`mediaItemId` is caller-generated (UUID v7). If omitted, the server generates one.

**Response `201 Created`** — all media-items succeeded:
```json
{
  "succeeded": [
    { "index": 0, "id": "018f...", "title": "Chinatown — Director's Cut" },
    { "index": 1, "id": "018g...", "title": "Vertigo — Restored Edition" }
  ],
  "failed": [],
  "skipped": []
}
```

**Response `202 Accepted`** — partial results:
```json
{
  "succeeded": [
    { "index": 0, "id": "018f...", "title": "Chinatown — Director's Cut" }
  ],
  "failed": [
    {
      "index": 1,
      "name": "Vertigo — Restored Edition",
      "errorCode": "DuplicateTitle",
      "message": "A media media-item with this title already exists in the media-folder.",
      "suggestedName": "Vertigo — Restored Edition (1)"
    }
  ],
  "skipped": []
}
```

**Errors (request-level):**
- `400` — batch exceeds 200 media-items, or required fields missing/malformed
- `401` — unauthenticated
- `403` — permission denied

**Per-item error codes:**

| `errorCode` | Cause | Caller action |
|---|---|---|
| `FolderNotFound` | `folderId` does not exist | Verify the media-folder ID |
| `FolderArchived` | Target media-folder is archived | Choose a different media-folder |
| `ProfileNotPublished` | `mediaProfileId` not found or not in `Published` status | Ensure media-profile is published first |
| `DuplicateTitle` | Title already taken in this media-folder (when `onDuplicate = Reject`) | Use `suggestedName` or choose a different title |
| `AutoSuffixExhausted` | 99 suffix attempts all taken | Manual rename required |
| `TitleReservationFailed` | Concurrent write conflict; retries exhausted | Re-submit |

_Accepts `IdempotencyKey` header._

---

### `POST /v1/catalog/items/bulk/metadata`

Applies a shared set of metadata fields to multiple MediaItems in a single request. Each item is resolved independently against its own `SnapshotFields` (per [Metadata Field Origin Resolution](./mediaitem.write-model.md#metadata-field-origin-resolution)) — items with different profiles are supported as long as every entry resolves on each item's schema.

Per-item failures do not affect other items (`ContinueOnError` default). Use `FailFast` to abort on first failure — note that with `FailFast`, if *any* item fails, the response returns **zero** succeeded items even if other items resolved cleanly (the handler discards the `succeeded` bag entirely rather than returning a partial commit list), since the per-item writes already happened by the time the failure is observed and a `FailFast` caller is signalling they want an all-or-nothing read on the result.

> 🔧 **Breaking shape change (ADR-013):** `fields` is now an **array of entries**, not a `fieldName → value` map — same change and same reason as `PUT .../metadata` above: each entry now carries its own required `origin`.

**Request:**
```json
{
  "itemIds": ["mi-01", "mi-02", "mi-03"],
  "fields": [
    { "fieldName": "campaign", "value": "Q1-2026", "origin": "General" },
    { "fieldName": "status", "value": "Ready for Distribution", "origin": "Governed" }
  ],
  "onError": "ContinueOnError"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `itemIds` | `string[]` | ✅ | 1–100 items (configurable via `BulkOperations:MaxMediaItemsPerRequest`) |
| `fields` | `array` | ✅ | Each entry: `{ fieldName: string, value: <any JSON>, origin: "Governed" \| "General" }`. Full-replace semantics per item — entries not present are cleared on each item. `origin` is required per entry. |
| `onError` | `"ContinueOnError" \| "FailFast"` | ❌ | Default `ContinueOnError` |

**Response `200 OK`** — all items succeeded:
```json
{
  "succeeded": [
    { "index": 0, "itemId": "mi-01" },
    { "index": 1, "itemId": "mi-02" }
  ],
  "failed": []
}
```

**Response `207 Multi-Status`** — partial failure:
```json
{
  "succeeded": [{ "index": 0, "itemId": "mi-01" }],
  "failed": [
    { "index": 1, "itemId": "mi-02", "errorCode": "FieldNotFound", "message": "Field 'campaign' is not defined on MediaItem mi-02's record type." }
  ]
}
```

**Per-item error codes:**

| `errorCode` | Cause |
|---|---|
| `MediaItemNotFound` | Item does not exist in tenant |
| `MediaItemArchived` | Item is archived — writes blocked |
| `MediaItemNotCheckedOut` | Profile `CheckoutPolicy = RequiredForEdit` and item not checked out by caller |
| `FieldNotFound` | Origin/field-name resolution failed — covers what the single-item endpoints split into `MetadataFieldUnknown`, `MetadataFieldAmbiguous`, and `MetadataFieldNameReserved`. The bulk path does not currently distinguish these three cases at the `errorCode` level; callers must parse `message` for the specific reason. **This is a real divergence from the single-item endpoints, not just a doc simplification — flagged as a follow-up to align bulk and single-item error vocabularies.** |
| `RequiredFieldNull` | Field is `IsRequired` on the schema but value is `null` |
| `UnknownFieldType` | Field type in schema is unrecognised |
| `FieldTypeMismatch` | JSON value incompatible with schema field type |
| `DomainError` | Aggregate rejected the batch (e.g. item status guard) — message is the raw `DomainError.ErrorMessage` |
| `DomainError` | Aggregate rejected the batch (e.g. item status guard) |

**Request-level errors:**
- `400` — `itemIds` empty or exceeds limit
- `401` — unauthenticated
- `403` — caller does not own all items

_Accepts `IdempotencyKey` header._

---

## Updated Command → Event → Projection Traceability

_(Existing table entries unchanged — appended below)_

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/items/bulk` | `BulkCreateMediaItemsCommand` | `MediaItemCreated` (×N) | `MediaItemProjector` → INSERT (×N), `active-items` counter per media-folder |
| `POST /v1/catalog/items/bulk/metadata` | `BulkSetMetadataCommand` | `MediaItemMetadataBatchSet` (×N) | `MediaItemProjector` → UPDATE metadata (×N) |
                                                                                                                                                                                