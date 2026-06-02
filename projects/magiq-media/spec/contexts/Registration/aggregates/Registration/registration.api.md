# Registration — API

_Context: `Registration`_
_Aggregate: `Registration`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints.
- **Idempotency:** All mutating endpoints (POST, PUT, PATCH, DELETE) accept `IdempotencyKey: <uuid>`. Replaying the same key within the TTL returns the cached response. See [§Idempotency](../../../../shared/api-conventions.md#idempotency).
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457 `ProblemDetails`). See [§Error Contract](../../../../shared/api-conventions.md#error-contract--rfc-9457-problemdetails).

---

## Route Structure

```
POST   /v1/catalog/items/{itemId}/registrations          Initiate (cross-domain creation under catalog)
POST   /v1/registrations/{registrationId}/submit
POST   /v1/registrations/{registrationId}/resubmit
POST   /v1/registrations/{registrationId}/cancel
POST   /v1/registrations/{registrationId}/documents
POST   /v1/registrations/{registrationId}/amendments

POST   /v1/registrations/{registrationId}/submission     [System]
POST   /v1/registrations/{registrationId}/confirm        [System]
POST   /v1/registrations/{registrationId}/reject         [System]
POST   /v1/registrations/{registrationId}/amendments/{amendmentId}/approve  [System]
POST   /v1/registrations/{registrationId}/amendments/{amendmentId}/reject   [System]

GET    /v1/registrations/{registrationId}
GET    /v1/registrations                          ?mediaItemId={id} — by item; omit — by caller
GET    /v1/registrations/search                   ?q={term} — full-text search via OpenSearch
```

---

## Authorization

| Endpoint | Requirement |
|---|---|
| User write endpoints | `actor_type = "User"` and `context.Actor.Id == registration.OwnerId` |
| `[System]` endpoints | `actor_type = "System"` — integration adapter only |
| Read endpoints | User (owner) or System actor |

---

## Write Endpoints (selected)

### `POST /v1/catalog/items/{itemId}/registrations`

Initiates a new registration for a published MediaItem.

**Request:**
```json
{
  "registrationId": "018e4c7a-...",
  "registrationType": "Electronic",
  "registrationAuthority": "US Copyright Office",
  "notes": "Standard copyright filing for film asset."
}
```

**Response `201 Created`:**
```json
{ "id": "018e4c7a-..." }
```

**Errors:** `404` — MediaItem not found · `422` — MediaItem not `Published` · `422` — MediaProfile lacks `Registration` capability.

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity`):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/media-item-not-published",
  "title": "Media item is not published",
  "status": 422,
  "detail": "MediaItem 018e4c7a-... is in status Draft. Only Published media-items can be registered.",
  "extensions": { "errorCode": "MediaItemNotPublished" }
}
```

---

### `POST /v1/registrations/{registrationId}/documents`

Attaches a published "document media-item" before confirmation.

**Request:**
```json
{
  "mediaItemId": "018e4c7b-...",
  "itemType": "ApplicationForm"
}
```

Valid `itemType` values: `"ApplicationForm"`, `"SupportingEvidence"`, `"ConfirmationReceipt"`, `"Other"`

**Response `204 No Content`** — no body.

**Errors:** `409` — `Status = Confirmed` (use amendment endpoint) · `409` — `Status = Cancelled` · `409` — document already attached · `404` — document MediaItem not found · `422` — document MediaItem not `Published` · `422` — document MediaProfile has `Processing` capability.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — use amendment instead):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/registration-confirmed",
  "title": "Registration is confirmed",
  "status": 409,
  "detail": "Registration 018e4c7a-... is Confirmed. Use POST /v1/registrations/{id}/amendments to attach documents post-confirmation.",
  "extensions": { "errorCode": "RegistrationConfirmed" }
}
```

---

### `POST /v1/registrations/{registrationId}/submit`

Transitions `Initiated` or `Resubmitted` → `Submitted`.

**Response `204 No Content`** — no body.

**Errors:** `409` — invalid status · `422` — no documents attached.

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity`):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/no-documents-attached",
  "title": "No documents attached",
  "status": 422,
  "detail": "Registration 018e4c7a-... has no documents attached. At least one document is required before submission.",
  "extensions": { "errorCode": "NoDocumentsAttached" }
}
```

---

### `POST /v1/registrations/{registrationId}/resubmit`

Transitions `Rejected` → `Resubmitted`.

**Response `204 No Content`** — no body.

**Errors:** `409` — `Status ≠ Rejected`.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/invalid-status-transition",
  "title": "Invalid status transition",
  "status": 409,
  "detail": "Registration 018e4c7a-... is in status Submitted and cannot be resubmitted.",
  "extensions": { "errorCode": "InvalidStatusTransition", "currentStatus": "Submitted" }
}
```

---

### `POST /v1/registrations/{registrationId}/cancel`

Cancels from any non-terminal status.

**Response `204 No Content`** — no body.

**Errors:** `409` — `Status = Confirmed` · `409` — `Status = Cancelled`.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — confirmed media-registration):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/registration-confirmed",
  "title": "Registration is confirmed",
  "status": 409,
  "detail": "Registration 018e4c7a-... is Confirmed and represents an external legal record. It cannot be cancelled on the platform.",
  "extensions": { "errorCode": "RegistrationConfirmed" }
}
```

---

### `POST /v1/registrations/{registrationId}/amendments`

Requests a document addition post-confirmation.

**Request:**
```json
{
  "amendmentId": "018e4c7c-...",
  "mediaItemId": "018e4c7d-...",
  "itemType": "ConfirmationReceipt"
}
```

**Response `201 Created`:**
```json
{ "id": "018e4c7c-..." }
```

**Errors:** `409` — `Status ≠ Confirmed` · `409` — duplicate pending amendment for same `mediaItemId` · `404` — document MediaItem not found · `422` — document not `Published` · `422` — document MediaProfile has `Processing` capability.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — duplicate pending amendment):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/duplicate-pending-amendment",
  "title": "Duplicate pending amendment",
  "status": 409,
  "detail": "A pending amendment for MediaItem 018e4c7d-... already exists on Registration 018e4c7a-...",
  "extensions": { "errorCode": "DuplicatePendingAmendment" }
}
```

---

### `POST /v1/registrations/{registrationId}/submission` `[System]`

Records that the owner has dispatched to the external authority (`Submitted → PendingConfirmation`).

**Response `204 No Content`** — no body.

**Errors:** `409` — `Status ≠ Submitted`.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/invalid-status-transition",
  "title": "Invalid status transition",
  "status": 409,
  "detail": "Registration 018e4c7a-... is in status Initiated. It must be Submitted before dispatching to the authority.",
  "extensions": { "errorCode": "InvalidStatusTransition", "currentStatus": "Initiated" }
}
```

---

### `POST /v1/registrations/{registrationId}/confirm` `[System]`

Confirms the media-registration (`PendingConfirmation → Confirmed`).

**Request:**
```json
{ "reference": "1-12345ABC" }
```

**Response `204 No Content`** — no body.

**Errors:** `409` — `Status ≠ PendingConfirmation` · `422` — `reference` empty.

_Accepts `IdempotencyKey` header._

**Error response example (`422 Unprocessable Entity`):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/reference-required",
  "title": "Reference is required",
  "status": 422,
  "detail": "A non-empty authority reference must be provided when confirming a media-registration.",
  "extensions": { "errorCode": "ReferenceRequired" }
}
```

---

### `POST /v1/registrations/{registrationId}/reject` `[System]`

Rejects the media-registration (`PendingConfirmation → Rejected`).

**Request:**
```json
{ "rejectionReason": "Incomplete application form." }
```

**Response `204 No Content`** — no body.

**Errors:** `409` — `Status ≠ PendingConfirmation`.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/invalid-status-transition",
  "title": "Invalid status transition",
  "status": 409,
  "detail": "Registration 018e4c7a-... is in status Rejected. Only PendingConfirmation media-registrations can be rejected.",
  "extensions": { "errorCode": "InvalidStatusTransition", "currentStatus": "Rejected" }
}
```

---

### `POST /v1/registrations/{registrationId}/amendments/{amendmentId}/approve` `[System]`

Approves the amendment and atomically attaches the document.

**Request:**
```json
{ "decisionNotes": "Confirmation receipt accepted." }
```

**Response `200 OK`** — no body.

**Errors:** `404` — amendment not found · `409` — amendment not `Pending`.

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — amendment already resolved):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/amendment-not-pending",
  "title": "Amendment is not pending",
  "status": 409,
  "detail": "Amendment 018e4c7c-... is in status Approved and cannot be approved again.",
  "extensions": { "errorCode": "AmendmentNotPending" }
}
```

---

## Read Endpoints (selected)

### `GET /v1/registrations/{registrationId}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "mediaItemId": "018e4c6f-...",
  "ownerId": "owner_...",
  "registrationType": "Electronic",
  "registrationAuthority": "US Copyright Office",
  "status": "Confirmed",
  "reference": "1-12345ABC",
  "notes": "Standard copyright filing for film asset.",
  "submittedAt": "2026-02-01T10:00:00Z",
  "confirmedAt": "2026-02-15T14:30:00Z",
  "initiatedAt": "2026-01-28T09:00:00Z",
  "documents": [
    {
      "mediaItemId": "018e4c7b-...",
      "itemType": "ApplicationForm",
      "addedAt": "2026-01-29T10:00:00Z",
      "addedViaAmendmentId": null
    },
    {
      "mediaItemId": "018e4c7d-...",
      "itemType": "ConfirmationReceipt",
      "addedAt": "2026-02-16T09:00:00Z",
      "addedViaAmendmentId": "018e4c7c-..."
    }
  ],
  "amendments": [
    {
      "id": "018e4c7c-...",
      "mediaItemId": "018e4c7d-...",
      "itemType": "ConfirmationReceipt",
      "requestedAt": "2026-02-15T16:00:00Z",
      "status": "Approved",
      "resolvedAt": "2026-02-16T09:00:00Z",
      "decisionNotes": "Confirmation receipt accepted."
    }
  ]
}
```

---

### `GET /v1/registrations`

Returns a paginated list of registration summaries. The filter mode is determined by the presence of `mediaItemId`:

| Scenario | Query | Handler |
|---|---|---|
| `?mediaItemId={id}` provided | Registrations for that media item | `ListRegistrationsByMediaItemQuery` |
| `mediaItemId` omitted | Registrations owned by the calling user (`context.Actor.Id`) | `ListRegistrationsByOwnerQuery` |

**Query parameters:** `mediaItemId` (optional), `pageSize` (default `20`), `pageToken` (opaque cursor — omit for first page).

**Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "018e4c7a-...",
      "mediaItemId": "018e4c6f-...",
      "ownerId": "owner_...",
      "registrationType": "Electronic",
      "registrationAuthority": "US Copyright Office",
      "status": "Confirmed",
      "reference": "1-12345ABC",
      "submittedAt": "2026-02-01T10:00:00Z",
      "confirmedAt": "2026-02-15T14:30:00Z",
      "initiatedAt": "2026-01-28T09:00:00Z"
    }
  ],
  "pageSize": 20,
  "nextPageToken": null
}
```

**Errors:** `401` · `403`

> `404` is not returned when `mediaItemId` is not found — the endpoint returns an empty `items` array.

---

### `GET /v1/registrations/search`

Full-text search across the `media-registrations` OpenSearch index. Matches on `registrationType`, `registrationAuthority`, `reference`, and `notes` fields.

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `q` | `string` | Yes | — | Search term. Returns `400` if absent or whitespace-only. |
| `pageSize` | `int` | No | `20` | Results per page. Capped at `100`. |
| `searchAfter` | `string` | No | — | Opaque cursor from the previous response's `nextSearchAfter` field. Omit on the first page. |

**Authorization:** `actor_type = "User"` — results are scoped to the caller's `OwnerId`. `actor_type = "System"` — results are unscoped (all tenants, filtered by `TenantId` from context).

**Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "018e4c7a-...",
      "mediaItemId": "018e4c6f-...",
      "ownerId": "owner_...",
      "registrationType": "Electronic",
      "registrationAuthority": "US Copyright Office",
      "status": "Confirmed",
      "reference": "1-12345ABC",
      "submittedAt": "2026-02-01T10:00:00Z",
      "confirmedAt": "2026-02-15T14:30:00Z",
      "initiatedAt": "2026-01-28T09:00:00Z"
    }
  ],
  "pageSize": 20,
  "nextSearchAfter": null
}
```

**Errors:** `400` — `q` missing or whitespace · `401` · `403`

**Error response example (`400 Bad Request`):**
```json
{
  "type": "https://errors.magiqmedia.com/validation/search-term-required",
  "title": "Search term is required",
  "status": 400,
  "detail": "The 'q' query parameter is required and must not be empty.",
  "extensions": { "errorCode": "SearchTermRequired" }
}
```

**Handler:** `SearchRegistrationsQuery(TenantId, SearchTerm, PageSize, SearchAfter)` → `SearchRegistrationsHandler` (OpenSearch `media-registrations` index, `multi_match` query on `registrationType`, `registrationAuthority`, `reference`, `notes`).

_Does not accept `IdempotencyKey` (read-only)._

---

## Command → Event → Projection Traceability

| API Call                               | Command                               | Domain Event                                                          | Projection                                                                  |
| -------------------------------------- | ------------------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `POST /v1/catalog/items/{id}/registrations` | `InitiateRegistrationCommand`         | `RegistrationInitiated` + `RegistrationRefAdded` (MediaItem stream)   | `RegistrationProjector` → INSERT both tables; `MediaItemProjector` → detail |
| `POST /submit`                         | `SubmitRegistrationCommand`           | `RegistrationSubmitted`                                               | `RegistrationProjector` → UPDATE status                                     |
| `POST /resubmit`                       | `ResubmitRegistrationCommand`         | `RegistrationResubmitted`                                             | `RegistrationProjector` → UPDATE status                                     |
| `POST /cancel`                         | `CancelRegistrationCommand`           | `RegistrationCancelled`                                               | `RegistrationProjector` → UPDATE status                                     |
| `POST /documents`                      | `AttachItemToRegistrationCommand`     | `RegistrationItemAttached`                                            | `RegistrationProjector` → append to `media-items[]`                               |
| `POST /amendments`                     | `RequestAmendmentCommand`             | `RegistrationAmendmentRequested`                                      | `RegistrationProjector` → append to `amendments[]`                          |
| `POST /submission`                     | `RecordRegistrationSubmissionCommand` | `RegistrationSubmissionRecorded`                                      | `RegistrationProjector` → UPDATE status                                     |
| `POST /confirm`                        | `ConfirmRegistrationCommand`          | `RegistrationConfirmed`                                               | `RegistrationProjector` → UPDATE status + reference                         |
| `POST /reject`                         | `RejectRegistrationCommand`           | `RegistrationRejected`                                                | `RegistrationProjector` → UPDATE status                                     |
| `POST /amendments/{id}/approve`        | `ApproveAmendmentCommand`             | `RegistrationAmendmentApproved` + `RegistrationItemAttached` (atomic) | `RegistrationProjector` → UPDATE amendment + append media-item                    |
| `POST /amendments/{id}/reject`         | `RejectAmendmentCommand`              | `RegistrationAmendmentRejected`                                       | `RegistrationProjector` → UPDATE amendment                                  |
| `GET /v1/registrations/{id}`              | `GetRegistrationByIdQuery`            | —                                                                     | reads `media-registration-detail`                                           |
| `GET /v1/registrations?mediaItemId={id}`  | `ListRegistrationsByMediaItemQuery`   | —                                                                     | reads `RegistrationSummaryReadModel` via `MediaItemRegistrationsIndex`      |
| `GET /v1/registrations` (no filter)       | `ListRegistrationsByOwnerQuery`       | —                                                                     | reads `RegistrationSummaryReadModel` filtered by `OwnerId`                  |
| `GET /v1/registrations/search?q={term}`   | `SearchRegistrationsQuery`            | —                                                                     | queries OpenSearch `media-registrations` index                              |

---

## Related

- [Registration Write Model](./media-registration.write-model.md)
- [Registration Read Model](./media-registration.read-model.md)
- [Registration Context Overview](../../context-overview.md)
- [Regist