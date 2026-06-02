# Architecture — magiq-media

**Full spec:** `C:\Users\chase\OneDrive\CoworkOS\development-projects\projects\media-management\architecture\`

---

## Pattern

**DDD + CQRS + Event Sourcing**

- Write side: commands → Command Handler → aggregates → event store (DynamoDB)
- Read side: events → projectors → read models (DynamoDB + OpenSearch) → Query API
- Async: domain events published to SNS → SQS fan-out → downstream consumers

---

## Request Flow

```
Client
  │
  ▼
API Gateway / ALB
  │              │
  ▼              ▼
Ingest API    Query API
(writes)      (reads)
  │              │
  │ MediatR      │ DynamoDB / OpenSearch read models
  ▼              ▼
Command Handler           Read Models
  │
  ① PutItem → media-events (DynamoDB, append-only)
  │
  ② Inline dispatch:
  │   ├── Per-module *IntegrationEventPublisher → SNS: media-integration-events
  │   └── Local projector handlers (read-model writes)
  │
  ③ Publish → SNS: media-domain-events
              │
  ┌───────────┼─────────────┬─────────────┐
  ▼           ▼             ▼             ▼
media-      media-       media-        media-
projector   processing   sagas         signing
  │           │             │             │
Projectors  Processing  SagaOrch      SecuredSigning
Lambda      Worker      estrator      Adapter
```

---

## Multi-Tenancy

- `TenantId` = immutable tenant boundary identifier
- Every DynamoDB PK: `TENANT#{TenantId}#{EntityId}`
- Source: JWT `tenant_id` claim (HTTP) or SNS message attribute (SQS Lambda)
- **Never** from payload body, **never** derived from `OwnerId`
- Every aggregate implements `ITenanted` — `TenantId` set in creation event, immutable

---

## Authentication & Authorization

### JWT Claims

| Claim | Maps to |
|---|---|
| `sub` | `Actor.Id` (OwnerId at creation) |
| `name` | `Actor.Name` |
| `roles` | `Actor.Roles` |
| `actor_type` | `"System"` \| `"User"` \| `"Guest"` |
| `tenant_id` | `TenantId` |

### Actor Types

- **User** — normal domain operations
- **System** — privileged commands (e.g. `ForceReleaseCheckout`, `CreateRecordType`)
- **Guest** — no JWT; read-only public endpoints, rate-limited by IP

### Token Replay Detection

`media-used-jtis` table. Every authenticated request: `GetItem(jti)` → reject if exists → conditional `PutItem` with `attribute_not_exists(PK)`.

### Command Authorization

All write commands on aggregates: `context.Actor.Id == aggregate.OwnerId`
System-only commands: `context.Actor.ActorType == "System"`
Reviewer commands: `context.Actor.Id ∈ ChangeRequest.Reviewers[].ReviewerId`

---

## Event Sourcing

### Event Store Schema (media-events)

```
PK:            TENANT#{TenantId}#{AggregateId}
SK:            AggregateVersion  (0-based integer, monotonic)
EventType:     string
OccurredAt:    ISO8601
Payload:       JSON blob
SchemaVersion: int
PayloadRef:    string? (S3 URI if payload externalized)
```

### Concurrency

Conditional write `attribute_not_exists(AggregateVersion)` — concurrent writes produce `ConditionalCheckFailedException` → retry up to 3× with exponential backoff.

### Rehydration

`LoadAsync(TenantId, AggregateId)` → query all events by PK ordered by `AggregateVersion` → replay `When()` handlers.

---

## Messaging Topology

Two SNS topics:

| Topic | Purpose | Subscribers |
|---|---|---|
| `media-domain-events` | Internal — full domain event shapes | MM-owned queues only |
| `media-integration-events` | Boundary — curated `media.*` envelopes | External BC SQS queues + MM `media-cross-module-events` |

Integration events published **inline** in Command Handler by per-module `*IntegrationEventPublisher` classes — no separate Lambda (ADR-005).

### SQS Queues (MM-owned)

| Queue | Consumer | Source |
|---|---|---|
| `media-projector` | Projectors Lambda | `media-domain-events` |
| `media-processing` | Processing Worker | `media-domain-events` (`AssetValidationPassed` filter) |
| `media-sagas` | SagaOrchestrator | `media-domain-events` |
| `media-signing` | SecuredSigning Adapter | `media-domain-events` |
| `media-cross-module-events` | Integration Event Consumers Lambda | `media-integration-events` |

All queues: standard (not FIFO), max 3 retries, DLQ with CloudWatch alarm on depth > 0.

---

## Name Uniqueness — Two Tiers

**Tier 1 (read-model check):** Command handler queries read model. Rejects early if name taken. Eventually consistent — handles 99% of cases cheaply.

**Tier 2 (atomic reservation):** `TransactWriteItems` writes event + name reservation to `media-name-reservations` atomically. Prevents concurrent writers both passing Tier 1.

Table: `media-name-reservations`
PK: `TENANT#{TenantId}#SCOPE#{ScopeKey}#NAME#{NormalizedName}`

Scopes: `COLLECTION`, `MEDIAPROFILE`, `RECORDTYPE`, `PARENT#{parentId|"ROOT"}`, `FOLDER#{folderId}`

Handler uses `NameReservationIntent` value objects + `INameReservationService` — never constructs DynamoDB types directly.

---

## S3 Upload Patterns

**Single-part (<100MB):** Client `POST /assets/upload-url` → pre-signed PUT URL (15min TTL) → client PUTs to S3 → S3 fires `ObjectCreated` → SQS → `ConfirmAssetUpload`.

**Multipart (≥100MB):** Client `POST /assets/multipart/initiate` → Handler creates S3 multipart upload + pre-signed part URLs → client uploads parts concurrently → client `POST /assets/{id}/multipart/complete` with ETags → `S3.CompleteMultipartUpload`.

S3 key shard: last 4 hex chars of UUID v7 `AssetId` = 65,536 distinct prefixes. Reconstructible from `AssetId` alone. No hashing.

---

## Sagas

| Saga | Trigger | Status |
|---|---|---|
| `AssetIngestionSaga` | `AssetValidationPassed` | ✅ Implemented |
| `MediaItemReviewSaga` | `MediaItemSubmittedForReview` | ⚠️ Partial (missing closing handlers) |
| `DocumentSigningSaga` | `SigningSessionInitiated` | 🔴 Deferred — not registered |

`SagaTimeoutScanner`: CloudWatch scheduled (5-min), scans `media-sagas` for expired `AssetIngestion` sagas → dispatches `FailAssetProcessing`.

---

## Read Models

**DynamoDB** — all detail and summary tables. PK: `TENANT#{TenantId}#{EntityId}`.
**OpenSearch** — two indexes: `media-items` (full-text search), `media-registrations` (faceted filtering).
Index aliases (`media-items-v1` → `media-items`) allow zero-downtime reindex.

All read models are expendable — rebuildable by replaying `media-events`.

---

## Key Invariants

- `TenantId` is never derived from `OwnerId`
- S3 keys use `TenantId` — never `OwnerId` (ownership is mutable; keys must be stable)
- Domain exceptions never escape command handlers — always `Result<T, DomainError>`
- Projectors check `ProjectedVersion` before applying — idempotent under duplicate SQS delivery
- Integration event `EventId` deterministic from `(AggregateId, AggregateVersion, eventType)` — downstream de-dupe
