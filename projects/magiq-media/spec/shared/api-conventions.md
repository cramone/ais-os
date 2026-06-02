# API Conventions
_magiq-media · Shared reference for all bounded-context API specs_

All individual API specs (`*.api.md`) reference this document for cross-cutting concerns. No cross-cutting concern should be defined more than once.

---

## Base URL

```
https://api.{env}.magiqmedia.com/v1
```

| Environment | Base URL |
|---|---|
| Local | `http://localhost:5000/v1` |
| Dev | `https://api.dev.magiqmedia.com/v1` |
| Staging | `https://api.staging.magiqmedia.com/v1` |
| Production | `https://api.magiqmedia.com/v1` |

All request URLs in this spec use `{BASE_URL}` as a placeholder. In Postman environments this maps to the `BASE_URL` variable (see [Environment Variables](#environment-variables)).

---

## Authentication

All non-public endpoints require a JWT bearer token.

```
Authorization: Bearer <jwt>
```

### JWT Claim Structure

| Claim | Type | Maps To | Notes |
|---|---|---|---|
| `sub` | `string` | `Actor.Id` | Standard OIDC. Unique, immutable actor identifier. |
| `name` | `string` | `Actor.Name` | Standard OIDC. Full name of the actor. |
| `roles` | `string[]` | `Actor.Roles` | Array of assigned role strings. |
| `actor_type` | `string` | `Actor.ActorType` | Custom claim. `"System"` \| `"User"` \| `"Guest"`. |
| `tenant_id` | `string` | `TenantId` | Custom claim. Tenant boundary — immutable. Never supplied in request body. |
| `exp` | `int` | — | Standard JWT expiry. Rejected unconditionally if expired. |
| `jti` | `string` | — | Standard JWT ID. Required for replay detection. |

**Important:** `TenantId` is sourced exclusively from the `tenant_id` JWT claim (HTTP) or the `TenantId` SNS message attribute (SQS). It must never appear in request bodies or path parameters.

### Actor Types

| Actor | Description |
|---|---|
| **System** | Internal service or automated process. May invoke privileged commands (e.g., `ForceReleaseCheckout`, `ApproveMediaItem` via saga). |
| **User** | Authenticated individual. Primary actor type for all normal domain operations. |
| **Guest** | No JWT present. Read-only access to public endpoints only. Rate-limited by source IP. |

### Token Replay Detection

Every presented JWT is checked against the `media-used-jtis` DynamoDB table. A consumed `jti` returns `401 Unauthorized` on replay. See `system-spec.md §Authentication` for the full enforcement algorithm.

---

## Idempotency

Mutating endpoints (POST, PUT, PATCH, DELETE) accept an optional idempotency key:

```
IdempotencyKey: <caller-generated UUID v4 or v7>
```

The platform middleware (`Magiq.AspNetCore.Idempotency`) stores the first response against the key. Replaying the same key within the TTL window returns the cached response with the original status code — it does not re-execute the command.

**Behaviour:**

| Scenario | Response |
|---|---|
| First call | Normal execution and response |
| Replay with same key (within TTL) | Cached response, same status code |
| Replay after TTL expiry | Normal execution (new response) |

**Postman:** Generate a fresh key per request using the media-collection pre-request script:

```javascript
pm.request.headers.add({ key: 'IdempotencyKey', value: pm.variables.replaceIn('{{$guid}}') });
```

The `IdempotencyKey` is **not** propagated to SNS/SQS. Message-level idempotency is handled by event store conditional writes, projector `ProjectedVersion` guards, and saga status checks.

---

## Error Contract — RFC 9457 ProblemDetails

All error responses use `Content-Type: application/problem+json` and conform to [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457).

### Standard Error Shape

```json
{
  "type": "https://errors.magiqmedia.com/domain/media-item-checked-out",
  "title": "Media item is checked out",
  "status": 409,
  "detail": "MediaItem 018e4c7a-... is currently checked out by user_018e4c7b-...",
  "instance": "/v1/catalog/items/018e4c7a-.../metadata",
  "extensions": {
    "errorCode": "MediaItemCheckedOut",
    "checkedOutBy": "user_018e4c7b-..."
  }
}
```

| Field | Required | Description |
|---|---|---|
| `type` | Yes | URI identifying the error type. Use `https://errors.magiqmedia.com/domain/<code>` for domain errors; `https://errors.magiqmedia.com/validation/<code>` for validation errors. |
| `title` | Yes | Human-readable short description of the error type. Stable — do not vary per instance. |
| `status` | Yes | HTTP status code. Mirrors the response status. |
| `detail` | No | Human-readable instance-specific explanation. May vary per instance. |
| `instance` | No | URI of the specific request that produced the error. |
| `extensions` | No | Domain-specific key-value extensions (e.g., `errorCode`, resource identifiers). |

### Validation Error Shape (422)

For `422 Unprocessable Entity`, the `errors` extension provides field-level detail:

```json
{
  "type": "https://errors.magiqmedia.com/validation/metadata-invalid",
  "title": "Metadata validation failed",
  "status": 422,
  "detail": "One or more metadata fields failed validation for RecordType FilmRecord v4.",
  "instance": "/v1/catalog/items/018e4c7a-.../submit",
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

### Common Status Codes

| Status | Meaning | Common Causes |
|---|---|---|
| `400 Bad Request` | Malformed request / missing required parameter | Invalid JSON, missing path param |
| `401 Unauthorized` | Missing or invalid JWT | Expired token, replayed `jti`, no `Authorization` header |
| `403 Forbidden` | Authenticated but not authorised | Wrong actor type, cross-owner write attempt |
| `404 Not Found` | Resource does not exist for this tenant | Wrong ID, wrong tenant |
| `409 Conflict` | Business rule violation / state conflict | Checkout conflict, duplicate name, invalid state transition |
| `422 Unprocessable Entity` | Validation failure | Schema validation, required field missing |
| `429 Too Many Requests` | Rate limit exceeded | Guest requests, burst limit |
| `500 Internal Server Error` | Unexpected server error | Infrastructure fault |

---

## Pagination

List endpoints that may return large result sets use cursor-based pagination.

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pageSize` | `int` | `20` | Maximum items to return. Capped at `100`. |
| `pageToken` | `string` | — | Continuation token from the previous response. Omit for the first page. |

### Response Fields

```json
{
  "items": [ ... ],
  "nextPageToken": "eyJQSyI6IlRFTkFOVCMuLi4ifQ==",
  "pageSize": 20,
  "totalCount": null
}
```

| Field | Description |
|---|---|
| `items` | Page of results. |
| `nextPageToken` | Token for the next page. `null` when no more pages exist. |
| `pageSize` | Number of items returned in this page. |
| `totalCount` | Not supported on DynamoDB-backed lists. Always `null`. |

### Token Format — DynamoDB-Backed Endpoints

`pageToken` is a **base64url-encoded, JSON-serialised DynamoDB `LastEvaluatedKey`**.

- Treat as opaque — do not decode, re-encode, or construct tokens manually.
- Tokens are **unstable** across projection rebuilds and schema changes. Never persist a token for use beyond the current pagination session.
- A `null` `nextPageToken` means the last page has been reached.

### Pagination — OpenSearch-Backed Endpoints

Endpoints backed by OpenSearch (e.g. `GET /v1/catalog/items/search`, `GET /v1/registrations/search`) use `search_after` pagination instead of `pageToken`. `search_after` is stateless, scalable beyond 10,000 hits, and avoids the deep-pagination performance cliff of `from/size`.

#### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pageSize` | `int` | `20` | Results per page. Capped at `100`. |
| `searchAfter` | `string` | — | Opaque cursor from the previous response's `nextSearchAfter`. Omit for the first page. |

#### Response Fields

```json
{
  "items": [ ... ],
  "nextSearchAfter": "WyIyMDI2LTAxLTAxIiwiMDE4ZTRjN2EiXQ==",
  "pageSize": 20
}
```

| Field | Description |
|---|---|
| `items` | Page of results. |
| `nextSearchAfter` | Base64url-encoded `sort` values from the last hit. Pass as `searchAfter` on the next request. `null` when no more results exist. |
| `pageSize` | Items returned in this page. |

#### Token Format — OpenSearch `search_after`

`nextSearchAfter` is a **base64url-encoded JSON array** of the sort field values from the last document in the page (OpenSearch `sort` values). The server constructs this from the `sort` array on the last `hits.hits` entry.

- Treat as opaque — do not decode or construct manually.
- Tokens are stable as long as the index mapping and sort fields do not change.
- `from/size` pagination is **not permitted** on OpenSearch endpoints — it degrades beyond 10,000 documents and is disabled via index-level `index.max_result_window = 10000`.

#### Consistent Sort Required

`search_after` requires a consistent, unique sort to guarantee stable pagination. All OpenSearch list endpoints sort by `(createdAt desc, {entityId} asc)` where `{entityId}` is a `keyword` field (e.g. `mediaItemId`, `registrationId`). The tiebreaker prevents duplicate or skipped documents when two records share the same `createdAt`.

---

## Sorting

List endpoints that support sorting accept these query parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sortBy` | `string` | endpoint-specific | Field name to sort by. Supported values listed per endpoint. |
| `sortOrder` | `"asc"` \| `"desc"` | `"desc"` | Sort direction. |

**Constraints:** Sort is only supported on DynamoDB GSI-backed sort keys. Endpoints backed by a DynamoDB scan do not support arbitrary `sortBy`. Where the DynamoDB sort key is fixed (e.g., event version), the default sort is documented per endpoint and `sortBy` is not accepted.

### Supported Sort Fields by Endpoint

| Endpoint | Supported `sortBy` Values | Default | Notes |
|---|---|---|---|
| `GET /v1/catalog/collections` | `name`, `createdAt` | `createdAt desc` | Backed by `media-collections` GSI on `createdAt`. |
| `GET /v1/catalog/folders?collectionId=` | `name`, `createdAt` | `createdAt desc` | Backed by `media-folders-by-collection` GSI. |
| `GET /v1/catalog/folders/{folderId}/items` | `name`, `createdAt`, `updatedAt` | `createdAt desc` | Backed by `media-items-by-folder` GSI. |
| `GET /v1/change-requests` | `createdAt`, `resolvedAt` | `createdAt desc` | `resolvedAt` only meaningful when filtering by `status != Open`. |
| `GET /v1/registrations` | `createdAt` | `createdAt desc` | Single GSI sort key — `sortBy` is fixed; `sortOrder` is accepted. |

Endpoints that **do not** accept `sortBy` (scan-based or fixed-key): `GET /v1/catalog/items/unassigned`, `GET /v1/catalog/items/search`, `GET /v1/assets` (filtered by item). Results from these endpoints are returned in DynamoDB scan order, which is not guaranteed to be stable.

---

## Async Operations — 202 Accepted

Endpoints that initiate asynchronous media-sagas return `202 Accepted`.

```
HTTP/1.1 202 Accepted
Location: /v1/catalog/items/018e4c7a-...
Content-Type: application/json

{
  "expectedStatus": "UnderReview",
  "changeRequestId": "018e4c7b-..."
}
```

| Field | Presence | Description |
|---|---|---|
| `Location` header | Always | URL of the resource to poll for status transitions. |
| `expectedStatus` | Always | The status value the resource will transition to on saga completion. |
| `changeRequestId` | Only when `ReviewPolicy = RequiredForPublish` | Pre-allocated MCR ID. Use to fetch the ChangeRequest directly without polling. |

**Polling strategy:** poll the `Location` URL until the resource reaches `expectedStatus` or a terminal error state. See individual scenarios for per-endpoint retry budget and polling interval.

Saga-initiating endpoints:

| Endpoint | Saga Triggered | Poll Field | Terminal Success Status |
|---|---|---|---|
| `POST /v1/catalog/items/{id}/submit` | `MediaItemReviewSaga` | `GET /v1/catalog/items/{id}` → `status` | `Published` or `UnderReview` |
| `POST /v1/catalog/items/{id}/signing-sessions` | `DocumentSigningSaga` | `GET /v1/signing/sessions/{id}` → `status` | `EnvelopeCreated` |

---

## Route Pattern — Nested Creation, Flat Operations

Resources are created under their parent (nested route) and operated on individually (flat route). This is standard REST practice and the inconsistency is intentional.

```
# Create a folder under a collection (nested — parent context required for creation)
POST /v1/catalog/collections/{collectionId}/folders

# Subsequent operations on the folder itself (flat — folder ID is sufficient)
GET    /v1/catalog/folders/{folderId}
PUT    /v1/catalog/folders/{folderId}
DELETE /v1/catalog/folders/{folderId}
```

The nested creation route encodes the mandatory parent relationship at the point of creation. All subsequent individual-resource operations use the flat route because the parent context is already encoded in the resource.

---

## Webhook HMAC Verification

Incoming webhooks from SecuredSigning are signed using HMAC-SHA256.

| | Value |
|---|---|
| Algorithm | `HMAC-SHA256` |
| Header | `X-SecuredSigning-Signature: sha256=<hex-digest>` |
| Secret | Configurable per environment via SSM Parameter Store (`/magiq-media/{env}/secured-signing-webhook-secret`) |
| Test secret | `test-secret-local` (local), `test-secret-dev` (dev) — never committed to source control |

Verification: compute `HMAC-SHA256(secret, raw-request-body)` as hex and compare with the value after `sha256=`. Reject if absent or mismatched.

---

## Test Utilities

The following endpoints are available in non-production environments only. They are gated by `ASPNETCORE_ENVIRONMENT != Production` and return `404` in production.

### Force Saga Expiry

> 🔧 **Requires implementation (R-18 · Phase 5):** This endpoint must be implemented in the test/dev Lambda host. Gate it with `if (env.IsProduction()) return NotFound()`. The handler should locate the saga by `sagaId` and invoke the same timeout handler path as `SagaTimeoutScanner`.

```
POST /v1/test/sagas/{sagaId}/expire
```

Immediately triggers the timeout path for a saga, bypassing the CloudWatch-scheduled `SagaTimeoutScanner`. Use to test compensation flows (e.g., checkout force-release on signing session timeout) without waiting for the real TTL.

| Parameter | Type | Description |
|---|---|---|
| `sagaId` | `string` (path) | ID of the saga instance to expire. |

Response: `204 No Content` on success. `404` if saga not found. `409` if the saga is already in a terminal state (`Complete` or `Failed`).

### Confirm Asset Upload (Upload Bypass)

```
POST /v1/assets/{id}/uploads/confirm
```

Manually advances an asset from `Pending` to `Active`, bypassing the S3 event trigger. Idempotent. Use in test environments to simulate a completed S3 upload without performing the actual PUT to the pre-signed URL.

**Test workflow:**
1. Call `POST /v1/assets/uploads` — capture `assetId` and `uploadUrl`.
2. Skip the actual S3 PUT (or perform it with a fixture file — see below).
3. Call `POST /v1/assets/{id}/uploads/confirm` to advance the asset to `Active`.
4. Poll `GET /v1/assets/{id}` until `status = Active`.

**Test file fixtures** — maintain these in the test repo under `tests/fixtures/`:

| Filename | Size | Content | Purpose |
|---|---|---|---|
| `test-image-small.jpg` | ~100 KB | JPEG image | Standard image upload |
| `test-document.pdf` | ~50 KB | PDF document | Document upload (no Processing capability) |
| `test-video-small.mp4` | ~5 MB | H.264 video | Video upload (triggers full processing pipeline) |
| `test-infected.eicar` | 68 bytes | EICAR test string | Virus scan failure (AM-5) |

**Stub S3 configuration (local):** Set `AWS_S3_ENDPOINT_URL=http://localhost:4566` (LocalStack) in `.env.local`. The pre-signed URL returned by `POST /v1/assets/uploads` will point to the local endpoint. The S3 event notification is also handled by LocalStack and enqueues to the local `media-processing` queue.

See `system-spec.md §Idempotency` for full behaviour.

---

### Processing Worker Simulation

The `ProcessingWorker` Lambda is triggered by messages on the `media-processing` SQS queue. In non-local test environments, asset state cannot advance beyond `Uploading` without either a real S3 PUT triggering the S3 event notification or direct SQS message injection.

**Strategy 1 — Direct SQS injection (integration tests):**

Inject an `AssetValidationPassed` event directly onto the `media-processing` SQS queue using the AWS CLI or a Postman pre-request script:

```bash
aws sqs send-message \
  --queue-url "$PROCESSING_QUEUE_URL" \
  --message-body '{
    "eventType": "AssetValidationPassed",
    "tenantId": "{{TENANT_ID}}",
    "assetId": "{{ASSET_ID}}"
  }'
```

The `PROCESSING_QUEUE_URL` variable must be set per environment (see [Environment Variables](#environment-variables)).

**Strategy 2 — Lambda direct invocation (test environments only):**

Invoke the `ProcessingWorker` Lambda directly with a synthetic event payload. Use the `PROCESSING_WORKER_ARN` environment variable (non-production only). This exercises the full handler logic including idempotency guards and projection writes.

**Polling after injection:** After injecting the SQS message, poll `GET /v1/assets/{id}` until `status = Active`. Recommended: max 12 retries, 5-second interval (60-second total budget).

**Note:** `PROCESSING_QUEUE_URL` and `PROCESSING_WORKER_ARN` must only be set in local and dev Postman environments. Omit them in staging and production.

---

## Environment Variables

Use these variable names in Postman environment files. Secrets must be sourced from SSM Parameter Store and never committed to source control.

| Variable | Local | Dev | Staging | Notes |
|---|---|---|---|---|
| `BASE_URL` | `http://localhost:5000/v1` | `https://api.dev.magiqmedia.com/v1` | `https://api.staging.magiqmedia.com/v1` | No trailing slash. |
| `TENANT_ID` | `test-tenant-local` | `test-tenant-dev` | `test-tenant-staging` | Informational only — not sent in requests. Sourced from JWT. |
| `OWNER_TOKEN` | local dev JWT | long-lived test JWT | short-lived JWT | `actor_type: "User"`. Must include `tenant_id` and `jti`. |
| `SYSTEM_TOKEN` | local system JWT | long-lived system JWT | short-lived JWT | `actor_type: "System"`. Required for privileged endpoints. |
| `SECURED_SIGNING_WEBHOOK_SECRET` | `test-secret-local` | `test-secret-dev` | SSM | HMAC signing secret for webhook tests. |
| `S3_UPLOAD_URL` | set by `POST /v1/assets/uploads` | set by `POST /v1/assets/uploads` | set by `POST /v1/assets/uploads` | Captured dynamically in upload scenarios. |
| `PROCESSING_QUEUE_URL` | LocalStack SQS URL | dev SQS URL | _omit_ | `media-processing` queue. For SQS injection tests only. Never set in staging/production. |
| `PROCESSING_WORKER_ARN` | LocalStack Lambda ARN | dev Lambda ARN | _omit_ | `ProcessingWorker` Lambda ARN. For direct invocation tests only. Never set in staging/production. |

---

## API Versioning

### URL Versioning

All endpoints are versioned via a URL path prefix: `/v{n}/`. The current major version is **v1**.

```
https://api.magiqmedia.com/v1/catalog/items
```

A new major version is introduced only when a breaking change cannot be avoided. Minor and patch changes are made in-place within the current major version — they are always backwards-compatible (see Compatibility Policy below).

### Compatibility Policy

The following changes are **non-breaking** and are made in-place without a version bump:

| Change | Safe? | Notes |
|---|---|---|
| Add a new optional request field | Yes | Ignored by older clients |
| Add a new response field | Yes | Ignored by older clients |
| Add a new endpoint | Yes | Existing clients unaffected |
| Add a new enum value to an extensible field | Yes | Clients must handle unknown enum values gracefully |
| Expand an existing field's maximum length | Yes | Existing clients within the old limit are unaffected |

The following changes are **breaking** and require a new major version:

| Change | Breaking? | Notes |
|---|---|---|
| Remove a request or response field | **Yes** | |
| Rename a field | **Yes** | |
| Change a field's type | **Yes** | |
| Remove or rename an endpoint | **Yes** | |
| Change HTTP method of an endpoint | **Yes** | |
| Remove a previously supported enum value | **Yes** | |
| Change status codes on success | **Yes** | |
| Make a previously optional request field required | **Yes** | |

### Versioning in FastEndpoints

Endpoint versions are registered using `.Version(n)` in `Configure()`. When v2 is introduced, both versions are served simultaneously until v1 is sunset:

```csharp
public override void Configure()
{
    Get("/catalog/items/{id}");
    Version(2);   // served at /v2/catalog/items/{id}
}
```

### Deprecation Policy

When a major version is deprecated:

1. **Deprecation notice** — A `Deprecation` response header is added to all v{n} responses:
   ```
   Deprecation: true
   Sunset: Sat, 01 Jan 2028 00:00:00 GMT
   Link: <https://api.magiqmedia.com/v2/catalog/items/{id}>; rel="successor-version"
   ```
2. **Minimum notice period** — **12 months** from deprecation announcement to sunset date. Enterprise customers may negotiate extended support.
3. **Sunset** — On the sunset date, all v{n} endpoints return `410 Gone` with a `ProblemDetails` body pointing to the successor version.
4. **Communication** — Deprecation announcements are published in the changelog, sent to API key contacts, and documented in this file.

### Current Version Status

| Version | Status | Sunset Date | Notes |
|---|---|---|---|
| v1 | **Active** | — | Current stable version |

