# DocumentSigningSession — Read Model

_Context: `DocumentSigning`_
_Aggregate: `DocumentSigningSession`_

---

## Read Models

### `media-signing-sessions` (DynamoDB)

Summary table. Powers list queries and tenant-scoped lookups.

| Field              | Type      | Notes                                       |
| ------------------ | --------- | ------------------------------------------- |
| `PK`               | `string`  | `EnvelopeId` — functionally required for O(1) webhook lookup. Record created on `SigningEnvelopeCreated` (not `SigningSessionInitiated`). |
| `TenantId`         | `string`  | Plain attribute — resolved from this table by webhook adapter |
| `SigningSessionId` | `string`  |                                             |
| `MediaItemId`      | `string`  |                                             |
| `OwnerId`          | `string`  |                                             |
| `Status`           | `string`  | `SigningSessionStatus` enum                 |
| `EnvelopeId`       | `string`  | PK value — always set on insert             |
| `SignedAssetId`    | `string?` | Set when `SignedAssetRecorded` processed    |
| `CreatedAt`        | `string`  |                                             |
| `ResolvedAt`       | `string?` | Set on any terminal state                   |
| `ProjectedVersion` | `long`    |                                             |
| `EventId`          | `string`  |                                             |

**GSIs:**
- `MediaItemIndex` (`MediaItemId + CreatedAt`) — lists all signing sessions for a MediaItem
- `TenantSessionIndex` (`TenantId + SigningSessionId`) — enables `GET /media-signing-sessions/{id}` tenant-scoped lookup

> **Webhook lookup:** When `POST /integrations/secured-signing/webhook` is received (unauthenticated), the `SecuredSigningAdapter` performs a direct `GetItem(PK = EnvelopeId)` to resolve `TenantId` and `SigningSessionId`. O(1) — no GSI scan required. This is a read-only lookup path — no writes from the webhook handler.

### `media-signing-session-detail` (DynamoDB)

Full detail. Powers `GET /media-signing-sessions/{id}`.

All `media-signing-sessions` fields plus:

| Field | Type | Notes |
|---|---|---|
| `InitiatedBy` | `string` | `OwnerId` of the user who initiated the session |
| `Signers` | `object[]` | `[{ email, routingOrder, status, completedAt? }]` |
| `CancellationReason` | `string?` | Set on `SigningSessionCancelled` |
| `VoidReason` | `string?` | Set on `SigningEnvelopeVoided` |

---

## Projection Handlers

### `SigningSessionProjector`

**Trigger:** `media-projector` SQS queue
**Targets:** `media-signing-sessions`, `media-signing-session-detail`

| Event | Write |
|---|---|
| `SigningSessionInitiated` | INSERT both tables; `signers[]` initialized with `status = Pending` |
| `SigningEnvelopeCreated` | UPDATE `EnvelopeId`, `Status = EnvelopeCreated`; populates `EnvelopeIdIndex` (sparse GSI entry written) |
| `SigningEnvelopeSent` | UPDATE `Status = EnvelopeSent` |
| `SignerCompleted` | UPDATE `signers[email].status = Completed`, `completedAt` in detail |
| `SigningCompleted` | UPDATE `Status = Completed` |
| `SignedAssetRecorded` | UPDATE `Status = SignedAssetRecorded`, `SignedAssetId`, `ResolvedAt` |
| `SigningEnvelopeVoided` | UPDATE `Status = Voided`, `ResolvedAt`, `VoidReason` in detail |
| `SigningSessionCancelled` | UPDATE `Status = Cancelled`, `ResolvedAt`, `CancellationReason` in detail |
| `SigningSessionTimedOut` | UPDATE `Status = TimedOut`, `ResolvedAt` |

---

## Queries

| Query | Description |
|---|---|
| `GetSigningSessionByIdQuery(TenantId, SigningSessionId)` | Full detail |
| `ListSigningSessionsByMediaItemQuery(TenantId, MediaItemId, PageToken?)` | All sessions for a MediaItem |
| `GetSigningSessionByEnvelopeIdQuery(EnvelopeId)` | Webhook lookup (internal — resolves `TenantId` + `SigningSessionId`; no TenantId input) |

---

## Query Handlers

When implemented, handlers will extend `QueryHandler<TQuery, TResponse>` (`Magiq.Platform.ReadModel.Queries`) and inject `IReadModelReader<T>` from `Magiq.Platform.ReadModel`. The webhook lookup (`GetSigningSessionByEnvelopeId`) is an exception — it operates without a `TenantId` and resolves tenant context directly from the summary table PK.

> **⚠️ Gap:** Query handlers for `DocumentSigning.ReadModel` are not yet implemented.

---

## Read Model Types

All read models implement `IReadModel` from `Magiq.Platform.ReadModel`.

### `SigningSessionSummaryReadModel`

Targets `media-signing-sessions` (DynamoDB). Powers list queries.

```csharp
record SigningSessionSummaryReadModel(
    string TenantId,
    string SessionId,
    string MediaItemId,
    string OwnerId,
    string Status,
    DateTimeOffset CreatedAt,
    DateTimeOffset? ResolvedAt,
    long ProjectedVersion) : IReadModel;
```

### `SigningSessionDetailReadModel`

Targets `media-signing-session-detail` (DynamoDB). Powers `GetSigningSessionById`.

```csharp
record SigningSessionDetailReadModel(
    string TenantId,
    string SigningSessionId,
    string MediaItemId,
    string OwnerId,
    string InitiatedBy,
    string Status,                  // Initiated | EnvelopeCreated | EnvelopeSent | Completed | SignedAssetRecorded | Voided | Cancelled | TimedOut
    string? EnvelopeId,
    List<SignerDto> Signers,
    string? SignedAssetId,
    string? VoidReason,
    string? CancellationReason,
    DateTimeOffset? ResolvedAt,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion) : IReadModel;
```

### Embedded Types

```csharp
record SignerDto(
    string Email,
    int RoutingOrder,
    string Status);                 // Pending | Completed
 
enum SigningSessionStatus  
{  
    Initiated,  
    EnvelopeCreated,  
    EnvelopeSent,  
    Completed,  
    SignedAssetRecorded,  
    Voided,  
    Cancelled,  
    TimedOut  
}
   
enum SignatureStatus  
{  
    Pending,  
    Completed  
}
    
```

---

## Related

- [DocumentSigningSession Write Model](./documentsigningsession.write-model.md)
- [System Spec — Storage Boundaries](../../../../shared/system-spec.md#storage-boundaries)