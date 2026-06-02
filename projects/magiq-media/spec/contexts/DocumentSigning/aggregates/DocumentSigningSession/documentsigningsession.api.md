# DocumentSigningSession — API

_Context: `DocumentSigning`_
_Aggregate: `DocumentSigningSession`_

---

## API Conventions

Cross-cutting concerns follow [`spec/shared/api-conventions.md`](../../../../shared/api-conventions.md).

- **Authentication:** `Authorization: Bearer <jwt>` required on all endpoints except `POST /v1/integrations/secured-signing/webhooks` (HMAC-validated, unauthenticated).
- **Idempotency:** All mutating endpoints (POST, PUT, PATCH, DELETE) accept `IdempotencyKey: <uuid>`. Replaying the same key within the TTL returns the cached response. See [§Idempotency](../../../../shared/api-conventions.md#idempotency).
- **Errors:** All error responses use `Content-Type: application/problem+json` (RFC 9457 `ProblemDetails`). See [§Error Contract](../../../../shared/api-conventions.md#error-contract--rfc-9457-problemdetails).
- **Webhook HMAC:** See [§Webhook HMAC Verification](../../../../shared/api-conventions.md#webhook-hmac-verification).

---

## Route Structure

```
POST   /v1/catalog/items/{itemId}/signing-sessions       Initiate signing session
POST   /v1/signing/sessions/{sessionId}/cancel           Cancel session (owner)

GET    /v1/signing/sessions/{sessionId}                  Get session detail
GET    /v1/signing/sessions?itemId=                      List by MediaItem

# Internal / System adapter endpoints (actor_type = "System" only):
POST   /v1/signing/sessions/{sessionId}/envelope/created
POST   /v1/signing/sessions/{sessionId}/envelope/sent
POST   /v1/signing/sessions/{sessionId}/signers/{email}/completed
POST   /v1/signing/sessions/{sessionId}/completed
POST   /v1/signing/sessions/{sessionId}/signed-asset
POST   /v1/signing/sessions/{sessionId}/envelope/voided
POST   /v1/signing/sessions/{sessionId}/expire

# Unauthenticated webhook (HMAC-validated):
POST   /v1/integrations/secured-signing/webhooks         (pluralised, /v1/ prefix)
```

---

## Authorization

| Endpoint | Requirement |
|---|---|
| `POST /v1/catalog/items/{id}/signing-sessions` | `caller.owner_id == mediaItem.OwnerId` + MediaItem `CheckedOut` by caller |
| `POST /v1/signing/sessions/{id}/cancel` | `caller.owner_id == session.OwnerId` + `Status ∈ {Initiated, EnvelopeCreated}` |
| All `/envelope/*`, `/signers/*`, `/completed`, `/signed-asset`, `/expire` | `actor_type = "System"` only |
| `POST /v1/integrations/secured-signing/webhooks` | Unauthenticated — HMAC signature validation only |
| Read endpoints | `caller.owner_id == session.OwnerId` |

---

## Write Endpoints

### `POST /v1/catalog/items/{itemId}/signing-sessions`

Initiates a signing session. MediaItem must be checked out by the caller.

**Request:**
```json
{
  "signingSessionId": "018e4c7a-...",
  "signers": [
    { "email": "alice@example.com", "routingOrder": 1 },
    { "email": "bob@example.com",   "routingOrder": 2 }
  ]
}
```

`signingSessionId` is caller-generated (UUID v7).

**Response `202 Accepted`:**
```
HTTP/1.1 202 Accepted
Location: /v1/signing/sessions/018e4c7a-...
```
```json
{
  "id": "018e4c7a-...",
  "expectedStatus": "EnvelopeCreated"
}
```

`expectedStatus` reflects the next state after the SecuredSigning envelope is created asynchronously.

**Errors:**
- `403` — caller is not the MediaItem owner
- `409` — MediaItem not checked out
- `409` — active signing session already in progress
- `422` — MediaProfile does not have `DigitalSigning` capability

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — not checked out):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/media-item-not-checked-out",
  "title": "Media item is not checked out",
  "status": 409,
  "detail": "MediaItem 018e4c7b-... must be checked out by the caller before initiating a signing session.",
  "extensions": { "errorCode": "MediaItemNotCheckedOut" }
}
```

---

### `POST /v1/signing/sessions/{sessionId}/cancel`

Owner cancels the session. Only valid in `Initiated` or `EnvelopeCreated` status.

**Request:**
```json
{ "reason": "Signer list needs to be updated." }
```

**Response `200 OK`** — no body.

**Errors:**
- `403` — caller is not the session owner
- `409` — session status is not `Initiated` or `EnvelopeCreated`

_Accepts `IdempotencyKey` header._

**Error response example (`409 Conflict` — invalid status):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/invalid-status-transition",
  "title": "Invalid status transition",
  "status": 409,
  "detail": "SigningSession 018e4c7a-... is in status Completed and cannot be cancelled.",
  "extensions": { "errorCode": "InvalidStatusTransition", "currentStatus": "Completed" }
}
```

---

### System / Adapter Endpoints

All the following require `actor_type = "System"`. They are dispatched by the `SecuredSigningAdapter` Lambda and are not user-facing.

#### `POST /v1/signing/sessions/{sessionId}/envelope/created`
```json
{ "envelopeId": "env_abc123" }
```

#### `POST /v1/signing/sessions/{sessionId}/envelope/sent`
No body.

#### `POST /v1/signing/sessions/{sessionId}/signers/{email}/completed`
No body.

#### `POST /v1/signing/sessions/{sessionId}/completed`
```json
{ "completionToken": "tok_..." }
```

#### `POST /v1/signing/sessions/{sessionId}/signed-asset`
```json
{ "assetId": "018e4c7e-..." }
```

#### `POST /v1/signing/sessions/{sessionId}/envelope/voided`
```json
{ "reason": "Envelope voided by SecuredSigning admin." }
```

#### `POST /v1/signing/sessions/{sessionId}/expire`
No body.

All return `200 OK` — no body on success, `403` if actor is not System, `404` if session not found.

_All system/adapter endpoints accept `IdempotencyKey` header._

**Error response example (`403 Forbidden`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/system-actor-required",
  "title": "System actor required",
  "status": 403,
  "detail": "This endpoint requires actor_type = System.",
  "extensions": { "errorCode": "SystemActorRequired" }
}
```

---

### `POST /v1/integrations/secured-signing/webhooks`

Unauthenticated entry point for SecuredSigning callbacks. HMAC signature is validated before any processing. `TenantId` resolved from `signing-sessions[EnvelopeId]` lookup.

This endpoint dispatches the appropriate internal System command based on `event_type` in the payload.

**Response `200 OK`** — always returns 200 to acknowledge receipt (failed lookups are silently dropped or sent to DLQ).

**Error response example (`401 Unauthorized` — HMAC mismatch):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/hmac-signature-invalid",
  "title": "HMAC signature invalid",
  "status": 401,
  "detail": "X-SecuredSigning-Signature header is absent or does not match the computed HMAC-SHA256 digest.",
  "extensions": { "errorCode": "HmacSignatureInvalid" }
}
```

---

## Read Endpoints

### `GET /v1/signing/sessions/{sessionId}`

**Response `200 OK`:**
```json
{
  "id": "018e4c7a-...",
  "mediaItemId": "018e4c7b-...",
  "ownerId": "owner_...",
  "initiatedBy": "owner_...",
  "status": "EnvelopeSent",
  "envelopeId": "env_abc123",
  "signers": [
    { "email": "alice@example.com", "routingOrder": 1, "status": "Completed", "completedAt": "2026-03-26T11:00:00Z" },
    { "email": "bob@example.com",   "routingOrder": 2, "status": "Pending",   "completedAt": null }
  ],
  "signedAssetId": null,
  "createdAt": "2026-03-26T10:00:00Z",
  "resolvedAt": null
}
```

---

### `GET /v1/signing/sessions?itemId={id}`

```json
{
  "sessions": [
    { "id": "...", "mediaItemId": "...", "status": "SignedAssetRecorded", "createdAt": "...", "resolvedAt": "..." }
  ],
  "nextPageToken": null
}
```

---

## Command → Event → Projection Traceability

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `POST /v1/catalog/items/{id}/signing-sessions` | `InitiateSigningSessionCommand` | `SigningSessionInitiated` | `SigningSessionProjector` → INSERT |
| `POST /v1/signing/sessions/{id}/cancel` | `CancelSigningSessionCommand` | `SigningSessionCancelled` | `SigningSessionProjector` → Status=Cancelled |
| `POST /envelope/created` | `RecordEnvelopeCreatedCommand` | `SigningEnvelopeCreated` | `SigningSessionProjector` → EnvelopeId, EnvelopeIdIndex |
| `POST /envelope/sent` | `RecordEnvelopeSentCommand` | `SigningEnvelopeSent` | `SigningSessionProjector` → Status=EnvelopeSent |
| `POST /signers/{email}/completed` | `RecordSignerCompletedCommand` | `SignerCompleted` | `SigningSessionProjector` → signer status |
| `POST /completed` | `RecordSigningCompletedCommand` | `SigningCompleted` | `SigningSessionProjector` → Status=Completed |
| `POST /signed-asset` | `RecordSignedAssetCommand` | `SignedAssetRecorded` | `SigningSessionProjector` → SignedAssetId, Status=SignedAssetRecorded |
| `POST /envelope/voided` | `RecordEnvelopeVoidedCommand` | `SigningEnvelopeVoided` | `SigningSessionProjector` → Status=Voided |
| `POST /expire` | `ExpireSigningSessionCommand` | `SigningSessionTimedOut` | `SigningSessionProjector` → Status=TimedOut |
| `GET /v1/signing/sessions/{id}` | `GetSigningSessionByIdQuery` | — | reads `media-signing-session-detail` |

---

## Related

- [DocumentSigningSession Write Model](./documentsigningsession.write-model.md)
- [DocumentSigningSession Read Model](./documentsigningsession.read-model.md)
- [DocumentSigning Business Scenarios](../../business-scenarios.md)
- [MediaItem API](../../../Catalog/aggregates/MediaItem/mediaitem.api.md)
