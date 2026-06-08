# System Specification — Media Management

_Last updated: 2026-04-22_

> Cross-cutting concerns shared across all bounded contexts in the Media Management platform.

---

## Table of Contents

1. [Multi-Tenancy Strategy](#multi-tenancy-strategy)
2. [Authentication & Authorization](#authentication--authorization)
3. [Concurrency Strategy](#concurrency-strategy)
4. [Idempotency Strategy](#idempotency-strategy)
5. [Cross-Aggregate Constraint Enforcement](#cross-aggregate-constraint-enforcement)
6. [Event Sourcing Mechanics](#event-sourcing-mechanics)
7. [Messaging Patterns](#messaging-patterns)
8. [Storage Boundaries](#storage-boundaries)
9. [S3 Upload Patterns](#s3-upload-patterns)
10. [Event Versioning](#event-versioning)
11. [Saga Coordination Patterns](#saga-coordination-patterns)
12. [Cross-Context Relationships](#cross-context-relationships)
13. [Infrastructure Overview](#infrastructure-overview)
14. [Observability](#observability)
15. [Naming Conventions](#naming-conventions)
16. [Ubiquitous Language (Cross-Context)](#ubiquitous-language-cross-context)

---

## Multi-Tenancy Strategy

### TenantId as Primary Isolation Boundary

`TenantId` is the immutable identifier for the tenant (organisation) that owns the deployment scope. It is distinct from `OwnerId` — `OwnerId` identifies a specific owner within a tenant; `TenantId` identifies the tenant boundary itself.

**Sources:**
- HTTP requests: JWT `tenant_id` claim, resolved via `IExecutionContext`
- SQS-triggered Lambdas: SNS message attribute `TenantId` on the event envelope — never from the event payload body

**Rules:**
- `TenantId` is **never** derived from `OwnerId`
- `TenantId` is **never** stored as `OwnerId`
- `OwnerId` S3 keys are forbidden — `TenantId` is used instead (ownership is mutable; storage keys must be stable)

### DynamoDB PK Convention

All DynamoDB tables prefix every PK with `TENANT#{TenantId}#`:

```
PK: TENANT#{TenantId}#{EntityId}
```

This provides hard partition isolation — a correctly constructed key for tenant A cannot address tenant B's rows. `TenantId` is additionally stored as a plain non-key attribute on every record for observability.

### Aggregate Convention

Every aggregate implements `ITenantScoped` (from `Magiq.Platform.WriteModel`, provided by `Magiq.Platform.WriteModel.Domain`):

```csharp
public interface ITenantScoped
{
    TenantId TenantId { get; }
}
```

`TenantId` is:
1. The **first field** on every aggregate creation event
2. The **first parameter** on every aggregate factory method
3. Set once in the creation event's `Apply()` handler; immutable thereafter
4. Read by `IEventStore.SaveAsync` from `aggregate.TenantId` — `IExecutionContext` is not injected into the event store

### IExecutionContext

```csharp
interface IExecutionContext {
    string   TenantId       // JWT tenant_id claim — drives PK prefix and storage keys
    IActor   Actor          // Resolved actor (User | System | Guest)
    string?  CausationId
    string?  CorrelationId
}
```


### IActor

```csharp
interface IActor {
    string                      ActorType  // "System" | "User" | "Guest"
    string                      Id         // JWT sub claim — unique actor identifier
    string                      Name       // JWT name claim — full name
    IReadOnlyCollection<string> Roles      // JWT roles claim
}
```


| Host | Implementation | Scope |
|---|---|---|
| `Media.Api` (FastEndpoints) | `HttpExecutionContext` — from validated JWT claims via `IHttpContextAccessor` | Scoped per HTTP request |
| SQS Lambda entry-points | `SqsExecutionContext` — constructed per-message from SQS message attributes | Scoped per SQS message |

---

## Authentication & Authorization

### JWT Claims

| Claim | Type | Maps To | Notes |
|---|---|---|---|
| `sub` | `string` | `Actor.Id` | Standard OIDC. Unique, immutable actor identifier. |
| `name` | `string` | `Actor.Name` | Standard OIDC. Full name of the actor. |
| `roles` | `string[]` | `Actor.Roles` | Array of assigned role strings. |
| `actor_type` | `string` | `Actor.ActorType` | Custom claim. `"System"` \| `"User"` \| `"Guest"`. |
| `tenant_id` | `string` | `TenantId` | Custom claim. Tenant boundary. Immutable. |
| `exp` | `int` | — | Standard JWT expiry. Rejected unconditionally if expired. |
| `jti` | `string` | — | Standard JWT ID. Required for replay detection. |

`owner_id` is not a JWT claim. Ownership on resources is expressed as `resource.OwnerId = actor.Id` at creation time — `OwnerId` is not a property of the token.

### Actor Types

| Actor | Description |
|---|---|
| **System** | Internal service or automated process. May invoke privileged commands (e.g., `ForceReleaseCheckout`). |
| **User** | Authenticated individual. Primary actor type for all normal domain operations. |
| **Guest** | No JWT present. `HttpExecutionContext` constructs a Guest `IActor` with empty `Roles`. Read-only access to public endpoints only. Rate-limited by source IP. |

### Token Replay Detection

Replay detection uses a dedicated DynamoDB table `media-used-jtis` (`PK: jti`, `TTL: exp`). On every authenticated request, after JWT validation:

1. `GetItem(PK = jti)` — if exists, reject `401`
2. Conditional `PutItem({jti, exp})` with `attribute_not_exists(PK)` — if `ConditionalCheckFailedException`, reject `401`

Full enforcement for all actor types that present a JWT.

### Command-Level Authorization

| Command | Permitted Actor(s) | Rule |
|---|---|---|
| `CreateRecordType` / `PublishRecordType` (system-owned) | System | `context.Actor.ActorType == "System"` |
| `AssignReviewer`, `RemoveReviewer` | User (owner) | `context.Actor.Id == ChangeRequest.OwnerId` |
| `ApproveMediaItem`, `RejectMediaItem` (via CR) | User (reviewer) | `context.Actor.Id ∈ ChangeRequest.Reviewers[].ReviewerId` |
| `ForceReleaseCheckout` | System | `context.Actor.ActorType == "System"` — no `User` or `Guest` may invoke |
| `ArchiveCollection`, `RenameCollection`, `SetCollectionVisibility` | User (owner) | `context.Actor.Id == Collection.OwnerId` |
| All write commands on `MediaItem`, `Asset`, `Registration`, `ChangeRequest` | User (owner) | `context.Actor.Id == aggregate.OwnerId` |

---

## Concurrency Strategy

### Event Store Optimistic Concurrency

All aggregates use event store–level optimistic concurrency enforced by DynamoDB conditional writes:

```
Conditional write: attribute_not_exists(AggregateVersion)
```

Per-aggregate stream linearizability: two concurrent commands at the same `AggregateVersion` produce a `ConditionalCheckFailedException` — only one succeeds. `ConditionalCheckFailedException` → `DomainError.ConcurrencyConflict` → command handler retries up to **3 times** with exponential backoff.

`AggregateVersion`:
- Starts at `0` before any events are persisted
- Incremented by `1` on each event append
- Managed exclusively by the `EventStore` abstraction — never set directly by command handlers

### Aggregate Rehydration

`LoadAsync(TenantId, AggregateId)`:
1. Constructs `PK = TENANT#{TenantId}#{AggregateId}`
2. Queries all events ordered by `AggregateVersion`
3. Replays events via `When()` handlers to reconstruct state
4. `TenantId` is set by the creation event's `When()` handler on every replay — no separate restore call needed

### Folder Hierarchy Concurrency

`Folder` aggregate exposes `Version` and all mutating commands accept `ExpectedVersion` for optimistic concurrency control.

---

## Idempotency Strategy

### Command Idempotency

Conditional write on `attribute_not_exists(AggregateVersion)` makes command handling naturally idempotent — the same command replayed produces a `ConditionalCheckFailedException` on the second attempt, which is treated as success (the event was already written).

**HTTP-level idempotency** for external integrations is handled by the `Magiq.AspNetCore.Idempotency` platform middleware registered in `Media.Api`. The middleware reads the `IdempotencyKey` request header, checks it against a platform-managed DynamoDB backing store, and short-circuits with the cached response on replay. The backing table (`media-idempotency-keys`) is owned and managed by the platform package — it is not an MM-owned infrastructure resource.

**IdempotencyKey is not propagated through SNS/SQS message attributes or integration event payloads.** Message-level idempotency is handled by three independent mechanisms:
- Event store conditional writes (aggregate-level)
- `ProjectedVersion` guards in projectors (projector-level)
- State machine status checks in media-sagas (saga-level)

No additional propagation is required — these mechanisms cover all downstream replay scenarios.

### Projector Idempotency

Every projector checks `ProjectedVersion` (stored on the read model record, implements `IVersionedProjection.ProjectedVersion`) before applying an event:

```
if event.AggregateVersion <= item.ProjectedVersion:
    discard — acknowledge SQS message; return
```

DynamoDB write guards:
- **First write**: `ConditionExpression: attribute_not_exists(PK)`
- **Subsequent writes**: `ConditionExpression: ProjectedVersion < :incomingAggregateVersion`
- **`ConditionalCheckFailedException`** → duplicate delivery → treat as success

### Saga Idempotency

`SagaOrchestrator` media-sagas in `Complete` or `Failed` status discard duplicate events silently.

---

## Cross-Aggregate Constraint Enforcement

Cross-aggregate constraints — uniqueness checks, referential existence, capability guards — cannot be enforced by a single aggregate in isolation. This section defines the standard pattern used across all write models.

### Constraint Categories

| Category | Examples | Enforcement Mechanism |
|---|---|---|
| **Uniqueness** | Collection name per tenant; Folder child name within parent scope; MediaItem title within media-folder; MediaProfile name per tenant; RecordType name per tenant | Tier 1 (read-model check) + Tier 2 (atomic reservation write) |
| **Referential existence / state** | Profile must be Published; Folder must be active; Asset must be Active; MediaItem must be Published for Registration | Read-model check only — eventual consistency accepted |
| **Capability / policy guards** | Registration capability on media-profile; checkout state; signing prerequisites; processing pipeline branching | Read-model check only |

### Application-Level Interface Pattern

All cross-aggregate constraint checks are performed in command handlers via injected service interfaces. Aggregates remain clean of infrastructure dependencies — they enforce only invariants derivable from their own event stream.

Three platform interfaces cover all cross-aggregate constraint categories:

| Interface | Package | Purpose |
|---|---|---|
| `INameReservationService` | `Magiq.Platform.UniquenessRegistry` | Name uniqueness — Tier 1 check + Tier 2 atomic reservation |
| `IUniquenessCounterService` | `Magiq.Platform.UniquenessRegistry` | Counter-based constraints — media-folder depth, child counts, media-registration counts |
| Per-module `I*QueryService` / `I*DomainService` | Module write model | Referential existence and capability/state checks (e.g., `IMediaProfileQueryService`, `IAssetQueryService`) — read-model backed, eventual consistency accepted |

Per-module query services are **not** used for name uniqueness — that is handled entirely by `INameReservationService`. They exist only for referential existence and capability guard checks.

### `IUniquenessCounterService`

```csharp
interface IUniquenessCounterService
{
    Task<long> GetCounterAsync(TenantId tenantId, ScopeKey scopeKey, string counterName, CancellationToken ct);
    Task IncrementCounterAsync(TenantId tenantId, ScopeKey scopeKey, string counterName, CancellationToken ct);
}
```

Used for constraints that require numeric tracking rather than name reservation:

| Constraint | Scope | Counter name | Used by |
|---|---|---|---|
| Folder depth limit | `ScopeKeys.Folder(parentId)` | `"depth"` | `CreateFolderHandler` |
| Child media-folder count | parent media-folder scope | `"child-folders"` | `CreateFolderHandler` |
| MediaItem media-registration count | `ScopeKeys.MediaItemRegistrations(mediaItemId)` | per-reg type | `RegistrationCountIndexProjector` |

### Interface Naming Convention

All constraint interface methods in this system follow this convention:

| Pattern | Semantics | Caller blocks when |
|---|---|---|
| `*IsAvailableAsync(...)` → `bool` | `true` = not in use / safe to proceed | `false` (unavailable) |
| `Get*Async(...)` → `T?` | `null` = not found | `null` (missing dependency) or when returned state fails guard |

**All uniqueness check methods in this system use `*IsAvailableAsync` semantics.** `true` means the name is available (safe to proceed); callers return `InvalidOperation` when `false`.

### Uniqueness Enforcement — Two Tiers

#### Tier 1: Early Rejection (Read-Model Check)

The command handler calls the service interface, which queries the appropriate read model. If the name is in use the command is rejected before the aggregate is loaded or any event is written. This handles the overwhelming majority of cases cheaply.

This check is eventually consistent — two concurrent handlers may both pass the read-model check before either commits. Tier 2 prevents both from succeeding.

#### Tier 2: Atomic Reservation (DynamoDB Conditional Write)

For uniqueness constraints where a collision would produce a visible incorrect state (name uniqueness is externally visible and cannot be silently corrected), the event store `SaveAsync` call is wrapped in a `TransactWriteItems` operation that simultaneously:

1. Appends the domain event to `media-events` (`ConditionExpression: attribute_not_exists(SK)`)
2. Writes a name reservation to `media-name-reservations` (`ConditionExpression: attribute_not_exists(PK)`)

If either condition fails, the entire transaction is rejected — exactly one concurrent writer succeeds.

On **rename**, the transaction additionally deletes the old reservation atomically:

```
TransactWriteItems:
  1. PutItem  → media-events              (attribute_not_exists(SK))
  2. DeleteItem → media-name-reservations (old name key)
  3. PutItem  → media-name-reservations   (new name key, attribute_not_exists(PK))
```

DynamoDB `TransactWriteItems` supports up to 25 media-items per call; the event + reservation pattern uses 2–3 media-items.

### `media-name-reservations` Table

```
Table: media-name-reservations
PK:    TENANT#{TenantId}#SCOPE#{ScopeKey}#NAME#{NormalizedName}
TTL:   none — reservations persist until explicitly released on rename or archive
```

Scope keys are lowercase with colon delimiters, defined in each module's `ScopeKeys.cs`:

| Constraint | ScopeKey value | Released on |
|---|---|---|
| Collection name (per tenant) | `"media-collection"` | `ArchiveCollection` |
| Folder child name within parent | `"parent:{parentFolderId}"` | `ArchiveFolder` |
| Folder child at media-collection root | `"media-collection:{collectionId}"` | `ArchiveFolder` |
| MediaItem title within media-folder | `"media-item:{folderId}"` | `ArchiveMediaItem` or `MoveMediaItem` (old scope) |
| MediaProfile name (per tenant) | `"media-profile"` | `DeprecateMediaProfile` |
| RecordType name (per tenant) | Defined in Metadata `ScopeKeys.cs` | `DeprecateRecordType` |

**Normalisation:** Name values written to this table are trimmed and lowercased. Display-casing is stored only on the read model.

### `INameReservationService` — Handler-Facing Abstraction

The platform provides `INameReservationService` (from `Magiq.Platform.UniquenessRegistry.Abstractions`) as the handler-facing interface for all uniqueness operations. Command handlers never interact with DynamoDB types directly.

```csharp
interface INameReservationService
{
    // Tier 1: availability check (read-model backed, eventually consistent)
    Task<bool> IsNameAvailableAsync(string tenantId, string scopeKey, string name, CancellationToken ct);

    // Tier 2: atomic reservation operations — each is an independent DynamoDB conditional write
    Task ReserveAsync(string tenantId, string scopeKey, string name, CancellationToken ct);
    Task SwapAsync(string tenantId, string scopeKey, string oldName, string newName, CancellationToken ct);
    Task MoveAsync(string tenantId, string oldScopeKey, string newScopeKey, string name, CancellationToken ct);
    Task ReleaseAsync(string tenantId, string scopeKey, string name, CancellationToken ct);
}
```

`ReserveAsync` and `SwapAsync` throw `NameReservationConflictException` if the name was claimed by a concurrent writer between Tier 1 and Tier 2.

**Important:** Steps 5 (Tier 2 reservation) and 6 (event store write) below are **not atomic with each other** — they are two separate DynamoDB writes. If step 5 succeeds and step 6 fails, the reservation exists without a corresponding event (orphaned reservation). This is an accepted trade-off; the name slot stays blocked until cleaned up manually or until the archive/deprecate path releases it.

**Scope keys** are string constants defined in each module's `ScopeKeys.cs` static class. The format is lowercase with colon delimiters — see [1.7 ScopeKey format table below](#media-name-reservations-table).

### Summary — Which Constraints Use Which Tier

| Constraint | Handler | Tier 1 (IsNameAvailableAsync scope) | Tier 2 method |
|---|---|---|---|
| Collection name uniqueness (create) | `CreateCollectionHandler` | `INameReservationService` — media-collection scope | `ReserveAsync` |
| Collection name uniqueness (rename) | `RenameCollectionHandler` | `INameReservationService` — media-collection scope | `SwapAsync` |
| Collection name (archive) | `ArchiveCollectionHandler` | — | `ReleaseAsync` |
| Folder child name uniqueness (create) | `CreateFolderHandler` | `INameReservationService` — parent media-folder scope | `ReserveAsync` |
| Folder child name uniqueness (rename) | `RenameFolderHandler` | `INameReservationService` — parent media-folder scope | `SwapAsync` |
| Folder child name uniqueness (move) | `MoveFolderHandler` | `INameReservationService` — target parent scope | `MoveAsync` |
| Folder name (archive) | `ArchiveFolderHandler` | — | `ReleaseAsync` |
| MediaItem title within media-folder (create) | `CreateMediaItemHandler` | `INameReservationService` — media-folder scope | `ReserveAsync` |
| MediaItem title within media-folder (assign) | `AssignMediaItemToFolderHandler` | `INameReservationService` — media-folder scope | `ReserveAsync` |
| MediaItem title within media-folder (move) | `MoveMediaItemHandler` | `INameReservationService` — target media-folder scope | `MoveAsync` |
| MediaItem title within media-folder (rename) | `UpdateMediaItemTitleHandler` | `INameReservationService` — media-folder scope | `SwapAsync` |
| MediaItem title (archive) | `ArchiveMediaItemHandler` | — | `ReleaseAsync` |
| MediaProfile name uniqueness (create) | `CreateMediaProfileHandler` | `INameReservationService` — media-profile scope | `ReserveAsync` |
| MediaProfile name uniqueness (publish, name changed) | `PublishMediaProfileHandler` | `INameReservationService` — media-profile scope | `SwapAsync` |
| MediaProfile name (deprecate) | `DeprecateMediaProfileHandler` | — | `ReleaseAsync` |
| RecordType name uniqueness (create) | `CreateRecordTypeHandler` | `INameReservationService` — media-record-type scope | `ReserveAsync` |
| RecordType name uniqueness (rename) | `RenameRecordTypeHandler` | `INameReservationService` — media-record-type scope | `SwapAsync` |
| RecordType name (deprecate) | `DeprecateRecordTypeHandler` | — | `ReleaseAsync` |

### Handler Call Sequence

Standard sequence for any command handler enforcing a uniqueness constraint:

1. **Tier 1** — `await _nameReservationService.IsNameAvailableAsync(tenantId, scopeKey, name)` → return `DomainError.InvalidOperation` if `false`
2. *(optional)* — call state/existence interfaces → return `DomainError` if dependency missing or invalid
3. Load aggregate from repository (omit for factory commands)
4. Call aggregate method
5. **Tier 2** — `await _nameReservationService.ReserveAsync(tenantId, scopeKey, name)` — or `SwapAsync` / `MoveAsync` / `ReleaseAsync` depending on the operation
6. `await repository.SaveAsync(aggregate)`
7. Return success

`NameReservationConflictException` (from step 5) and `ConcurrencyConflictException` (from event store write) are both handled by MediatR pipeline behaviors — handlers do not catch them.

For a concrete reference implementation see `CreateCollectionCommandHandler` and `RenameCollectionCommandHandler` in `Catalog.WriteModel/Handlers/`.

---

## Event Sourcing Mechanics

### Event Store Schema

```
Table:    media-events
PK:       TENANT#{TenantId}#{AggregateId}   (e.g., "TENANT#acme#asset_018e4c7a-...")
SK:       AggregateVersion                     (integer, 0-based, monotonic)
TenantId: string                             (plain attribute — redundant with PK prefix; for observability)
EventType: string                            (e.g., "AssetUploaded")
OccurredAt: ISO8601
Payload:  JSON blob
SchemaVersion: int
PayloadRef: string?                          (S3 URI when payload externalized)
```

Externalized payload path: `{tenantId}/events/{aggregateId}/{AggregateVersion}.json`

### Event Versioning

Every event record in the store carries a `SchemaVersion: int` field. All domain events start at `SchemaVersion = 1`. Upcasters are registered per event type and transform older schema versions to the current shape at load time — events are **never mutated in the store**.

### Compatibility Policy

| Change type | `SchemaVersion` bump required? | Notes |
|---|---|---|
| Add a new **nullable** field | **No** — additive-safe | Deserializer treats missing value as `null`. Old readers ignore unknown fields. |
| Add a new **required** field | **Yes** | Old events lack the field; an upcaster must supply a default. |
| Rename a field | **Yes** | Old events have the old name; upcaster maps old → new. |
| Remove a field | **Yes** | Old events carry the field; upcaster drops it. |
| Change a field's type | **Yes** | Old events carry the old type; upcaster converts. |
| Change event semantics (business logic) | **N/A** | Upcasters cannot correct business logic retroactively — requires full projection rebuild. |

**Current baseline:** All domain events in this system are at `SchemaVersion = 1`. No upcasters are currently registered.

### Upcaster Pattern

Upcasters transform an older event schema version into the current version at load time, before the aggregate's `When<T>` handler is invoked. The event store record is never mutated.

**Rules:**
- Upcasters must be composable: an event stored at v1 may need to pass through both a v1→v2 upcaster and a v2→v3 upcaster on load. The chain is applied in ascending version sequence.
- Upcasters may not change event semantics — field renames, field additions, and format normalisation only.
- If event semantics change, a full projection rebuild (replay from event store) is required instead.

**Interface:**

```csharp
// Platform interface — implemented per event type per schema version.
public interface IEventUpcaster<TEvent> where TEvent : IDomainEvent
{
    int FromVersion { get; }        // SchemaVersion this upcaster consumes
    int ToVersion { get; }          // SchemaVersion this upcaster produces
    TEvent Upcast(JsonElement raw); // Deserializes raw JSON → current TEvent shape
}
```

**Registration pattern:**

```csharp
// In each module's DI registration:
services.AddUpcaster<AssetUploaded, AssetUploadedV1Upcaster>();
```

**Example upcaster** (renaming `FileName` → `OriginalFileName` at v2):

```csharp
public class AssetUploadedV1Upcaster : IEventUpcaster<AssetUploaded>
{
    public int FromVersion => 1;
    public int ToVersion   => 2;

    public AssetUploaded Upcast(JsonElement raw)
    {
        // Map old field name to new field name; all other fields deserialize normally.
        var fileName = raw.GetProperty("FileName").GetString();
        return new AssetUploaded(
            ...,
            OriginalFileName: new FileName(fileName!),
            ...
        );
    }
}
```

### Schema Version Sunset Policy

Old `SchemaVersion` values may be retired once all events at that version have been replayed and re-projected. The retirement process:

1. Confirm no records at the old version remain in the event store (scan `media-events` with `FilterExpression: SchemaVersion = :old`).
2. Remove the upcaster registration.
3. Deploy — the event store reader will now fail fast if it encounters the retired version, making stale data immediately visible.

Retirement is **optional** — leaving old upcasters in place is always safe.

### Dual-Write Risk

After a successful `PutItem` to the event store, the `EventPublisher` publishes the event payload to `media-domain-events` SNS topic. Steps ① (PutItem) and ② (SNS publish) are not atomic. Full event store replay is always available for projection rebuilds. This is an accepted design decision — see ADR-002.

---

## Messaging Patterns

### SNS → SQS Fan-Out

All domain events are published to a single SNS topic (`media-domain-events`) after persisting to the event store. Downstream consumers receive events via dedicated SQS queue subscriptions.

### SNS Message Attributes

Every published event carries these message attributes (never parsed from the payload body by consumers):

| Attribute | Type | Source |
|---|---|---|
| `TenantId` | String | `eventRecord.TenantId` — stamped by `EventPublisher` |
| `AggregateId` | String | Aggregate stream identifier |
| `AggregateVersion` | Number | Event sequence position |
| `EventType` | String | Discriminator for filter policies |
| `CorrelationId` | String | Propagated from originating request |

### Queue Topology

Events flow through **two SNS topics** (see ADR-005):

- `media-domain-events` — internal. Carries full domain events in their internal shape. Only Media Management-owned consumers subscribe.
- `media-integration-events` — boundary. Carries the curated `media.*` integration-event subset in published-language envelope form. External bounded contexts subscribe their own SQS queues to this topic.

```
SNS Topic: media-domain-events                       ← internal (domain event shapes)
    │
    ├── SQS: media-projector       → Projectors (cross-aggregate)
    ├── SQS: media-processing      → Processing Worker (AssetUploadConfirmedIntegrationEvent only)
    ├── SQS: media-sagas           → SagaOrchestrator
    └── SQS: media-signing         → SecuredSigning Adapter

SNS Topic: media-integration-events                  ← boundary (media.* envelopes)
    │     populated by per-module *IntegrationEventPublisher classes
    │     running inline with Command Handler (ADR-005 — no separate Lambda)
    │
    ├── SQS: media-cross-module-events  → Integration Event Consumers Lambda
    │                                      (MM-owned intra-BC fan-in; capability
    │                                       index, saga triggers, etc.)
    ├──▶ Notifications-owned SQS       (filter: see catalog)
    ├──▶ Search/Discovery-owned SQS    (filter: see catalog)
    ├──▶ Billing-owned SQS             (filter: see catalog)
    └──▶ Compliance-owned SQS          (filter: see catalog)
```

| Queue                                                            | Owner            | Source Topic               | Filter                                                                 | Visibility Timeout   | Max Receive | DLQ                             | DLQ Retention |
| ---------------------------------------------------------------- | ---------------- | -------------------------- | ---------------------------------------------------------------------- | -------------------- | ----------- | ------------------------------- | ------------- |
| `media-projector`                                                | Media Management | `media-domain-events`      | All events                                                             | 60s                  | 3           | `media-projector-dlq`           | 14 days       |
| `media-processing`                                               | Media Management | `media-integration-events` | `AssetUploadConfirmedIntegrationEvent` only                            | 30 min / 4 h (video) | 3           | `media-processing-dlq`          | 14 days       |
| `media-sagas`                                                    | Media Management | `media-domain-events`      | All events                                                             | 30s                  | 3           | `media-sagas-dlq`               | 14 days       |
| `media-signing`                                                  | Media Management | `media-domain-events`      | `SigningSessionInitiated` + webhook triggers                           | 60s                  | 3           | `media-signing-dlq`             | 14 days       |
| `media-cross-module-events` (renamed from `media-notifications`) | Media Management | `media-integration-events` | `EventType` filter — integration events consumed by intra-BC consumers | 30s                  | 3           | `media-cross-module-events-dlq` | 7 days        |
| External BC consumer queues                                      | External BC      | `media-integration-events` | Per-BC filter policy on `EventType` message attribute                  | BC-defined           | BC-defined  | BC-owned DLQ                    | BC-defined    |

All queues are standard (not FIFO). Per-aggregate event ordering is guaranteed at the event store level by `AggregateVersion`. Projectors and media-sagas are idempotent and tolerate out-of-order SQS delivery.

**CloudWatch alarms:** DLQ depth > 0 triggers P2 alert for `media-processing-dlq` and `media-sagas-dlq`; P3 for all others.

### Integration Events

Integration events are a curated subset of domain events, translated into published-language form inline in the Command Handler by each module's `*IntegrationEventPublisher` class (ADR-005) and emitted directly to the `media-integration-events` SNS topic. External contexts subscribe their own SQS queues to that topic with filter policies; intra-BC consumers share the topic via the MM-owned `media-cross-module-events` queue. Integration events use a dot-separated naming convention:

```json
{
  "eventId":           "018e4c7a-3f10-7b2a-8c4d-1a2b3c4d5e6f",
  "eventType":         "media.mediaitem.published",
  "occurredAt":        "2026-03-26T12:00:00Z",
  "schemaVersion":     1,
  "sourceAggregateId": "mediaitem_018e4c7a-...",
  "ownerId":           "owner_018e4c7b-...",
  "payload":           { }
}
```

| Integration Event                     | Source Domain Event               | Consumers                                                                                                                                                          |
| ------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `media.collection.created`            | `CollectionCreated`               | Notifications, Billing                                                                                                                                             |
| `media.collection.renamed`            | `CollectionRenamed`               | Notifications                                                                                                                                                      |
| `media.collection.tagged`             | `CollectionTagged`                | Notifications                                                                                                                                                      |
| `media.collection.visibility-changed` | `CollectionVisibilityChanged`     | Search/Discovery                                                                                                                                                   |
| `media.collection.archived`           | `CollectionArchived`              | Notifications, Billing                                                                                                                                             |
| `media.folder.created`                | `FolderCreated`                   | Search/Discovery                                                                                                                                                   |
| `media.folder.renamed`                | `FolderRenamed`                   | Notifications                                                                                                                                                      |
| `media.folder.moved`                  | `FolderMoved`                     | Search/Discovery                                                                                                                                                   |
| `media.folder.archived`               | `FolderArchived`                  | Notifications                                                                                                                                                      |
| `media.item.created`                  | `MediaItemCreated`                | Search/Discovery; AssetManagement (capabilities index); Registration (media-registration context)                                                                  |
| `media.item.assigned-to-folder`       | `MediaItemAssignedToFolder`       | Search/Discovery                                                                                                                                                   |
| `media.item.submitted-for-review`     | `MediaItemSubmittedForReview`     | Notifications                                                                                                                                                      |
| `media.item.published`                | `MediaItemApproved`               | Notifications, Search/Discovery, Billing; Registration (media-registration context — sets `IsPublished = true`)                                                    |
| `media.item.rejected`                 | `MediaItemRejected`               | Notifications                                                                                                                                                      |
| `media.item.archived`                 | `MediaItemArchived`               | Billing, Search/Discovery; AssetManagement (capabilities index — sets `IsArchived = true`); Registration (media-registration context — sets `IsPublished = false`) |
| `media.item.signing-session-voided`   | `SigningEnvelopeVoided`           | Notifications _(declared; DocumentSigning module not yet built)_                                                                                                   |
| `media.profile.published`             | `MediaProfilePublished`           | Notifications                                                                                                                                                      |
| `media.profile.deprecated`            | `MediaProfileDeprecated`          | Notifications                                                                                                                                                      |
| `media.asset.uploaded`                | `AssetUploaded`                   | Notifications                                                                                                                                                      |
| `media.asset.attached`                | `AssetAttachedToMediaItem`        | Search/Discovery                                                                                                                                                   |
| `media.asset.processing-completed`    | `AssetProcessingCompleted`        | Notifications, Billing _(filtered: `Processing` capability only)_                                                                                                  |
| `media.asset.processing-failed`       | `AssetProcessingFailed`           | Notifications                                                                                                                                                      |
| `media.asset.archived`                | `AssetArchived`                   | Notifications, Billing                                                                                                                                             |
| `media.asset.deleted`                 | `AssetDeleted`                    | Notifications, Search/Discovery                                                                                                                                    |
| `media.asset.infection-detected`      | `AssetInfectionDetected`          | Notifications; Security audit log                                                                                                                                  |
| `media.changerequest.created`         | `ChangeRequestCreated`            | Notifications                                                                                                                                                      |
| `media.changerequest.approved`        | `ChangeRequestApproved`           | Notifications                                                                                                                                                      |
| `media.changerequest.rejected`        | `ChangeRequestRejected`           | Notifications                                                                                                                                                      |
| `media.changerequest.abandoned`       | `ChangeRequestAbandoned`          | Notifications _(raised when MediaItem archived/withdrawn while review open)_                                                                                       |
| `media.processingjob.scan-result`     | `ProcessingJobScanResultRecorded` | AssetManagement (intra-BC via `media-cross-module-events`) — `ProcessingJobScanResultEventHandler` dispatches `RecordValidationResultCommand`                      |
| `media.processingjob.started`         | `ProcessingJobStarted`            | AssetManagement (intra-BC via `media-cross-module-events`)                                                                                                         |
| `media.processingjob.completed`       | `ProcessingJobSucceeded`          | AssetManagement (intra-BC via `media-cross-module-events`)                                                                                                         |
| `media.processingjob.failed`          | `ProcessingJobFailed`             | AssetManagement (intra-BC via `media-cross-module-events`)                                                                                                         |
| `media.recordtype.published`          | `RecordTypePublished`             | Notifications                                                                                                                                                      |
| `media.recordtype.deprecated`         | `RecordTypeDeprecated`            | Notifications                                                                                                                                                      |
| `media.registration.initiated`        | `RegistrationInitiated`           | Notifications                                                                                                                                                      |
| `media.registration.submitted`        | `RegistrationSubmitted`           | Notifications; SagaOrchestrator (triggers external authority submission)                                                                                           |
| `media.registration.resubmitted`      | `RegistrationResubmitted`         | Notifications; SagaOrchestrator (retries authority submission)                                                                                                     |
| `media.registration.confirmed`        | `RegistrationConfirmed`           | Notifications, Compliance                                                                                                                                          |
| `media.registration.rejected`         | `RegistrationRejected`            | Notifications                                                                                                                                                      |
| `media.registration.cancelled`        | `RegistrationCancelled`           | Notifications                                                                                                                                                      |

**Billing filter:** `media.asset.processing-completed` is only forwarded to the Billing consumer when the owning `MediaItem`'s `MediaProfile` has the `Processing` capability. This filtering is applied inline by the `AssetIntegrationEventPublisher` — Billing applies no filtering of its own.

---

## Storage Boundaries

### DynamoDB Tables

| Table                                | PK                                                      | SK                                                        | Owner Context                                                                                                                  |
| ------------------------------------ | ------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `media-asset`                        | `TENANT#{TenantId}#{AssetId}`                           | `DETAIL`                                                  | AssetManagement.ReadModel (`AssetDetailReadModel`)                                                                             |
| `media-assets`                       | `TENANT#{TenantId}#ASSETS`                              | `{AssetId}`                                               | AssetManagement.ReadModel (`AssetSummaryReadModel`)                                                                            |
| `media-asset-item-ref`               | `TENANT#{TenantId}#MEDIA_ITEM#{MediaItemId}`            | `CAPABILITY`                                              | AssetManagement.ReadModel (`MediaItemCapabilityReference`)                                                                     |
| `media-catalog-asset-ref`            | `TENANT#{TenantId}#ASSET#{AssetId}`                     | `STATE`                                                   | Catalog.WriteModel (cross-module reference; `AssetStateReference`)                                                             |
| `media-catalog-change-request-ref`   | `TENANT#{TenantId}#CHANGE_REQUEST`                      | `{ChangeRequestId}`                                       | Catalog.WriteModel (cross-module reference; `ChangeRequestReference`)                                                          |
| `media-catalog-folder-folders-index` | `TENANT#{TenantId}#FOLDER`                              | `{FolderId\|CollectionId}`                                | Catalog.WriteModel (`FolderFoldersIndex`)                                                                                      |
| `media-catalog-folder-items-index`   | `TENANT#{TenantId}#MEDIA_ITEM`                          | `{MediaItemId}`                                           | Catalog.WriteModel (`MediaItemFolderIndex`)                                                                                    |
| `media-catalog-media-profile-index`  | `TENANT#{TenantId}#MEDIA_PROFILE`                       | `{MediaProfileId}`                                        | Catalog.WriteModel (`MediaProfileIndex`)                                                                                       |
| `media-catalog-record-type-ref`      | `TENANT#{TenantId}#RECORD_TYPE`                         | `{RecordTypeId}#{Version}` \| `{RecordTypeId}#DEPRECATED` | Catalog.WriteModel (cross-module reference; `RecordTypeVersionDetailIndex`)                                                    |
| `media-change-request`               | `TENANT#{TenantId}#{ChangeRequestId}`                   | `DETAIL`                                                  | ChangeRequests.ReadModel (`ChangeRequestDetailReadModel`)                                                                      |
| `media-change-request-comments`      | `TENANT#{TenantId}#CHANGE_REQUEST#{ChangeRequestId}`    | `COMMENT#{CommentId}`                                     | ChangeRequests.ReadModel (`ChangeRequestCommentReadModel`)                                                                     |
| `media-change-requests`              | `TENANT#{TenantId}#CHANGE_REQUESTS`                     | `{ChangeRequestId}`                                       | ChangeRequests.ReadModel (`ChangeRequestSummaryReadModel`)                                                                     |
| `media-collection`                   | `TENANT#{TenantId}#{CollectionId}`                      | `DETAIL`                                                  | Catalog.WriteModel (`CollectionDetailReadModel`)                                                                               |
| `media-collections`                  | `TENANT#{TenantId}#COLLECTIONS`                         | `{CollectionId}`                                          | Catalog.WriteModel (`CollectionSummaryReadModel`)                                                                              |
| `media-events`                       | `TENANT#{TenantId}#{AggregateId}`                       | `AggregateVersion`                                        | Command Handler (write) / all aggregate contexts (read)                                                                        |
| `media-folder`                       | `TENANT#{TenantId}#{FolderId}`                          | `DETAIL`                                                  | Catalog.ReadModel (`FolderDetailReadModel`)                                                                                    |
| `media-folder-children`              | `TENANT#{TenantId}#FOLDER#{FolderId}#CHILDREN`          | `{ChildId}`                                               | Catalog.ReadModel (`FolderChildrenSummaryReadModel`)                                                                           |
| `media-folder-hierarchy`             | `TENANT#{TenantId}#HIERARCHY#{Folder\|CollectionId}`    | `FOLDER#{FolderId}`                                       | Catalog.ReadModel (`FolderHierarchyNodeReadModel`)                                                                             |
| `media-folders`                      | `TENANT#{TenantId}#FOLDERS`                             | `{FolderId}`                                              | Catalog.ReadModel (`FolderSummaryReadModel`)                                                                                   |
| `media-idempotency-keys`             | `TENANT#{TenantId}#{OwnerId}#{IdempotencyKey}`          | —                                                         | API layer (TTL) (Platform plugin)                                                                                              |
| `media-item`                         | `TENANT#{TenantId}#{MediaItemId}`                       | `DETAIL`                                                  | Catalog.ReadModel (`MediaItemDetailReadModel`)                                                                                 |
| `media-items`                        | `TENANT#{TenantId}#ITEMS`                               | `{MediaItemId}`                                           | Catalog.ReadModel (`MediaItemSummaryReadModel`)                                                                                |
| `media-item-versions`                | `TENANT#{TenantId}#ITEM_VERSIONS#{MediaItemId}`         | `{VersionNumber}`                                         | Catalog.ReadModel (`MediaItemVersionReadModel`)                                                                                |
| `media-name-reservations`            | `TENANT#{TenantId}#SCOPE#{ScopeKey}`                    | `NAME#{normalizedName}`                                   | Cross-aggregate uniqueness enforcement — see [Cross-Aggregate Constraint Enforcement](#cross-aggregate-constraint-enforcement) |
| `media-profile`                      | `TENANT#{TenantId}#{MediaProfileId}`                    | `DETAIL`                                                  | Catalog.ReadModel (`MediaProfileDetailReadModel`)                                                                              |
| `media-profile-versions`             | `TENANT#{TenantId}#PROFILE#{MediaProfileId}`            | `{VersionNumber}`                                         | Catalog.ReadModel (`MediaProfileVersionReadModel`)                                                                             |
| `media-profiles`                     | `TENANT#{TenantId}#PROFILES`                            | `{MediaProfileId}`                                        | Catalog.ReadModel (`MediaProfileSummaryReadModel`)                                                                             |
| `media-processing-job`               | `TENANT#{TenantId}#{JobId}`                             | `DETAIL`                                                  | Processing.WriteModel (`JobDetailReadModel`)                                                                                   |
| `media-processing-jobs`              | `TENANT#{TenantId}#PROCESSING_JOBS`                     | `{JobId}`                                                 | Processing.WriteModel (`JobSummaryReadModel`)                                                                                  |
| `media-record-type`                  | `TENANT#{TenantId}#{RecordTypeId}`                      | `DETAIL`                                                  | Metadata.ReadModel (`RecordTypeDetailReadModel`)                                                                               |
| `media-record-type-versions`         | `TENANT#{TenantId}#RECORD_TYPE_VERSIONS#{RecordTypeId}` | `{VersionNumber}`                                         | Metadata.ReadModel (`RecordTypeVersionReadModel`)                                                                              |
| `media-record-types`                 | `TENANT#{TenantId}#RECORD_TYPES`                        | `{RecordTypeId}`                                          | Metadata.ReadModel (`RecordTypeSummaryReadModel`)                                                                              |
| `media-registration`                 | `TENANT#{TenantId}#{RegistrationId}`                    | `DETAIL`                                                  | Registration.ReadModel (`RegistrationDetailReadModel`)                                                                         |
| `media-registration-item-ref`        | `TENANT#{TenantId}#MEDIA_ITEM#{MediaItemId}`            | `STATE`                                                   | Registration.WriteModel (cross-module reference; `MediaItemRegistrationIndex`)                                                 |
| `media-registrations`                | `TENANT#{TenantId}#REGISTRATIONS`                       | `{RegistrationId}`                                        | Registration.ReadModel (`RegistrationSummaryReadModel`)                                                                        |
| `media-sagas`                        | `TENANT#{TenantId}`                                     | `SAGA#{sagaType}#{sagaId}`                                | SagaOrchestrator                                                                                                               |
| `media-signing-sessions`             | `EnvelopeId`                                            | `DETAIL`                                                  | DocumentSigning (lookup table for webhook TenantId resolution)                                                                 |
| `media-signing-session`              | `TENANT#{TenantId}#{SigningSessionId}`                  | `DETAIL`                                                  | DocumentSigning                                                                                                                |
| `media-used-jtis`                    | `jti`                                                   | —                                                         | Auth layer (TTL = `exp`) (Platform plugin)                                                                                     |

### DynamoDB Table GSIs

| Table              | Index Name                        | GSI PK   | GSI PK Example                                              | GSI SK   | GSI SK Example                          | Owner Context                                                    |
| ------------------ | --------------------------------- | -------- | ----------------------------------------------------------- | -------- | --------------------------------------- | ---------------------------------------------------------------- |
| `media-assets`           | `AssetByMediaItemIndex`           | `GSI1PK` | `TENANT#{TenantId}#ITEM#{MediaItemId}#ASSETS`               | —        | —                                       | AssetManagement.ReadModel (`AssetByMediaItemIndexSchema`)        |
| `media-collections`      | `CollectionByNameIndex`           | `GSI1PK` | `TENANT#{TenantId}#COLLECTIONS`                             | `GSI1SK` | `{Name}#{CollectionId}`                 | Catalog.ReadModel (`CollectionByNameIndexSchema`)                |
| `media-collections`      | `PublicCollectionByNameIndex`     | `GSI2PK` | `TENANT#{TenantId}#COLLECTIONS#PUBLIC`                      | `GSI2SK` | `{Name}#{CollectionId}`                 | Catalog.ReadModel (`PublicCollectionByNameIndexSchema`)          |
| `media-folders`          | `FolderByParentAndNameIndex`      | `GSI1PK` | `TENANT#{TenantId}#PARENT#{CollectionId\|FolderId}#FOLDERS` | `GSI1SK` | `{Name}#{FolderId}`                     | Catalog.ReadModel (`FolderByParentAndNameIndexSchema`)           |
| `media-folders`          | `FolderHierarchyIndex`            | `GSI2PK` | `TENANT#{TenantId}#COLLECTION#{CollectionId}#FOLDERS`       | `GSI2SK` | `{Name}#{FolderId}`                     | Catalog.ReadModel (`FolderHierarchyIndexSchema`)                 |
| `media-folder-children`  | `FolderChildByNameIndex`          | `GSI1PK` | `TENANT#{TenantId}#FOLDER#{ParentFolderId}#CHILDREN`        | `GSI1SK` | `{Name}#{ChildId}`                      | Catalog.ReadModel (`FolderChildByNameIndexSchema`)               |
| `media-items`            | `MediaItemByFolderIndex`          | `GSI1PK` | `TENANT#{TenantId}#FOLDER#{FolderId}#ITEMS`                 | `GSI1SK` | `{Name}#{MediaItemId}`                  | Catalog.ReadModel (`MediaItemByFolderIndexSchema`)               |
| `media-items`            | `MediaItemUnassignedByOwnerIndex` | `GSI2PK` | `TENANT#{TenantId}#ITEM#UNASSIGNED`                         | `GSI2SK` | `OWNER#{OwnerId}#{Title}#{MediaItemId}` | Catalog.ReadModel (`MediaItemUnassignedByOwnerIndexSchema`)      |
| `media-profiles`         | `MediaProfileByNameIndex`         | `GSI1PK` | `TENANT#{TenantId}#PROFILES`                                | `GSI1SK` | `{Name}#{MediaProfileId}`               | Catalog.ReadModel (`MediaProfileByNameIndexSchema`)              |
| `media-change-requests`  | `ChangeRequestByMediaItemIndex`   | `GSI1PK` | `TENANT#{TenantId}#ITEM#{MediaItemId}#CHANGE_REQUESTS`      | —        | —                                       | ChangeRequests.ReadModel (`ChangeRequestByMediaItemIndexSchema`) |
| `media-change-requests`  | `ChangeRequestByOwnerIndex`       | `GSI2PK` | `TENANT#{TenantId}#OWNER#{OwnerId}#CHANGE_REQUESTS`         | —        | —                                       | ChangeRequests.ReadModel (`ChangeRequestByOwnerIndexSchema`)     |
| `media-record-types`     | `RecordTypeByNameIndex`           | `GSI1PK` | `TENANT#{TenantId}#RECORD_TYPES`                            | `GSI1SK` | `{Name}#{RecordTypeId}`                 | Metadata.ReadModel (`RecordTypeByNameIndexSchema`)               |
| `media-processing-jobs`  | `AssetByProcessingJobIndex`       | `GSI1PK` | `TENANT#{TenantId}#ASSET#{AssetId}#JOBS`                    | `GSI1SK` | `{UpdatedAt}`                           | Processing.ReadModel (`AssetByProcessingJobIndexSchema`)         |
| `media-registrations`    | `RegistrationByMediaItemIndex`    | `GSI1PK` | `TENANT#{TenantId}#ITEM#{MediaItemId}#REGISTRATIONS`        | `GSI1SK` | `{InitiatedAt}#{RegistrationId}`        | Registrations.ReadModel (`RegistrationByMediaItemIndexSchema`)   |
| `media-registrations`    | `RegistrationByOwnerIndex`        | `GSI2PK` | `TENANT#{TenantId}#OWNER#{OwnerId}#REGISTRATIONS`           | `GSI2SK` | `{InitiatedAt}#{RegistrationId}`        | Registrations.ReadModel (`RegistrationByOwnerIndexSchema`)       |

### S3 Buckets

| Bucket             | Key Pattern                                          | Written By                  | Notes                                                         |
| ------------------ | ---------------------------------------------------- | --------------------------- | ------------------------------------------------------------- |
| `media-source`  | `{tenantId}/{shard}/{assetId}/original.{ext}`        | Ingest API (pre-signed PUT) | MediaProfile has `Processing` capability, or unattached asset |
| `media-renditions` | `{tenantId}/{shard}/{assetId}/{renditionType}.{ext}` | Processing Worker           | Generated renditions                                          |
| `media-documents`       | `{tenantId}/{shard}/{assetId}/document.{ext}`        | Ingest API (pre-signed PUT) | MediaProfile lacks `Processing` capability                    |

`{shard}` = last 4 hex chars of UUID v7 `AssetId` (`assetId.ToString("N")[^4..]`) — 65,536 distinct prefixes from random bits 112–127. No hashing required; reconstructible from `AssetId` alone.

### Table Ownership Notes

**Processing** — owns `AssetProcessingJobIndex` (write-side reference model keyed by `AssetId → ProcessingJobId`, used by `AssetValidationWorker`). The Processing Worker Lambda is otherwise stateless — it publishes integration events to `media-integration-events` SNS; AssetManagement subscribes and applies all `Asset` aggregate state transitions via its own command handlers.

**S3 lifecycle:**
- `media-source`: transition to Glacier Instant Retrieval after 90 days for archived media-assets
- `media-documents`: no lifecycle transition — media-registration documents retained indefinitely

### Rendition Deletion on Asset Soft-Delete

When an asset transitions to `Archived` (soft-delete) or `Deleted` (hard-delete), its renditions stored under `media-renditions` must be cleaned up. The cleanup contract:

**Trigger:** `media.asset.archived` or `media.asset.deleted` integration event, both of which now carry a `StorageKey` field containing the source object's S3 key path (format: `{tenantId}/{shard}/{assetId}/original.ext`). The rendition prefix is derived as `{tenantId}/{shard}/{assetId}/` — all objects under this prefix in `media-renditions` belong to the same asset.

**Mechanism:** The Processing context reacts to these events and deletes rendition objects directly from `media-renditions`. Consumers must handle `StorageKey = null` (events published before this field was introduced) by deriving the prefix from `TenantId` + `AssetId`.

**Backward compatibility:** `StorageKey` is nullable in both the domain event and integration event. Existing events replayed from the event store will have `StorageKeyBucket = null` and `StorageKeyValue = null`; the `Apply(AssetArchived/AssetDeleted)` handlers do not use these fields so replay is safe.

---

## S3 Upload Patterns

Two upload modes are supported. The client selects the mode by calling the appropriate initiation endpoint. Once initiated, a mode cannot be changed.

### Single-Part Upload (PUT)

Used for media-assets below the multipart threshold (typically < 100 MB, or where the client opts for simplicity). Per ADR-004.

**Flow:**
1. Client calls `POST /media-assets/upload-url` → receives `assetId` + pre-signed S3 PUT URL (15-min TTL). Asset is created in `Pending` state.
2. Client PUTs the binary directly to S3. No Lambda proxy.
3. S3 fires `ObjectCreated` event → SQS → Ingest Lambda → `ConfirmAssetUploadCommand` (auto).
4. Client may also call `POST /media-assets/{id}/confirm` manually as a fallback. The command is idempotent.
5. `ConfirmAssetUploadHandler` performs a HEAD check (size + content-type defence-in-depth), then transitions `Pending → Validating`.

### Multipart Upload

Used for large media-assets (≥ platform-configured threshold, default **100 MB**). Leverages S3 Multipart Upload API to allow concurrent, resumable part uploads.

**Flow:**
1. Client calls `POST /media-assets/multipart/initiate` with `assetId`, `fileName`, `contentType`, `sizeBytes`, optional `mediaItemId`.
2. Handler runs the same guards as single-part (existence, archive state, max file size, quota). Then calls `S3.CreateMultipartUpload` to obtain an `uploadId`.
3. Handler computes part count: `ceil(sizeBytes / partSizeBytes)`. `partSizeBytes` is configured per deployment (`AssetManagement:Upload:MultipartPartSizeBytes`, default **50 MB**; minimum 5 MB per S3 requirement).
4. Handler generates a pre-signed URL for each part via `S3.UploadPart` (15-min TTL per URL). Returns `assetId`, `uploadId`, and `[{ partNumber, uploadUrl, expiresAt }]`.
5. Asset is created in `Pending` state with `UploadMode = Multipart` and `MultipartUploadId` stamped on `AssetMultipartUploadInitiated`.
6. Client uploads each part directly to S3 using the part URLs. Parts may be uploaded concurrently.
7. Client calls `POST /media-assets/{assetId}/multipart/complete` with `[{ partNumber, eTag }]` (ETags returned by S3 on each part PUT).
8. Handler calls `S3.CompleteMultipartUpload`. On success S3 assembles the object and fires `ObjectCreated` (which the Ingest Lambda will receive, but the asset will already be `Validating` by then — idempotent no-op).
9. Handler calls `asset.ConfirmUpload()` → `Pending → Validating`. From here the pipeline is identical to single-part.

**Abort:**
- Client (or system timeout) calls `POST /media-assets/{assetId}/multipart/abort`.
- Handler calls `S3.AbortMultipartUpload` to release S3 part storage, then transitions asset to `MultipartAborted` (terminal).
- Aborted media-assets are excluded from all read models.

**Constraints:**
- S3 minimum part size: **5 MB** (except the final part, which may be smaller).
- S3 maximum part count: **10,000**.
- Maximum total multipart asset size: `10,000 × partSizeBytes` (500 GB at default 50 MB part size).
- Pre-signed part URLs expire after **15 minutes**. Clients requiring longer uploads must re-initiate.
- `ConfirmAssetUploadCommand` (single-part path) rejects media-assets whose `UploadMode = Multipart` and `Status = Pending` with `409 Conflict`. It is not the correct completion path for multipart media-assets.

**Configured values (per deployment):**

| Config Key | Default | Notes |
|---|---|---|
| `AssetManagement:Upload:MultipartPartSizeBytes` | 52,428,800 (50 MB) | Minimum 5,242,880 (5 MB) |
| `AssetManagement:Upload:MultipartUrlTtlMinutes` | 15 | Per-part URL TTL |

---

## Saga Coordination Patterns

### Sagas Overview

Sagas coordinate multi-aggregate workflows that cannot be expressed as a single atomic command. The `SagaOrchestrator` Lambda manages saga state in the `media-sagas` DynamoDB table.

| Saga | Trigger | Aggregates Involved | Context | Status |
|---|---|---|---|---|
| `AssetIngestionSaga` | `AssetValidationPassedIntegrationEvent` | Asset | AssetManagement / Processing | ✅ Implemented |
| `MediaItemReviewSaga` | `MediaItemSubmittedForReview` | MediaItem, ChangeRequest | Catalog / ChangeRequests | ⚠️ Partial — missing `MediaItemApproved/Rejected/Withdrawn/Archived` closing handlers |
| `DocumentSigningSaga` | `SigningSessionInitiated` | DocumentSigningSession, MediaItem | DocumentSigning / Catalog | 🔴 Planned/Deferred — not registered in `SagaRegistrations` |

### AssetIngestionSaga

Manages the processing pipeline for a single Asset. Owns the timeout boundary — if the Processing Worker does not complete within the configured TTL, `SagaTimeoutScanner` dispatches `FailAssetProcessing`.

Happy path: `AssetValidationPassedIntegrationEvent` → saga reads `HasProcessingCapability` flag → dispatches `StartProcessingJobCommand` (capable) or `BypassProcessingJobCommand` (bypass) → Processing Worker runs pipeline → `ProcessingJobCompletedIntegrationEvent` → `AssetProcessingCompleted` → saga complete.

Compensation: `ProcessingJobFailedIntegrationEvent` or timeout → saga dispatches `FailAssetProcessing` → closes.

### MediaItemReviewSaga

Manages the review-gated publish workflow. Only created when `MediaProfile.ReviewPolicy = RequiredForPublish`.

Happy path: `MediaItemSubmittedForReview` → `CreateChangeRequest` → `LinkChangeRequest` → awaiting reviewer decisions → `ChangeRequestApproved` → `ApproveMediaItem` → `MediaItemApproved` → saga complete.

Compensation: `ChangeRequestRejected` → `RejectMediaItem` → saga closes.

### DocumentSigningSaga

Manages the full SecuredSigning envelope lifecycle, including checkout lock management on `MediaItem`.

Happy path: `SigningSessionInitiated` → SecuredSigning Adapter creates envelope → `LinkSigningSession` → awaiting signers → `SigningCompleted` + `SignedAssetRecorded` → `UnlinkSigningSession` + `CheckInMediaItem` → saga complete.

Compensation: `SigningEnvelopeVoided` → `UnlinkSigningSession` + `ForceReleaseCheckout` → saga closes.

### SagaTimeoutScanner

Lambda triggered by CloudWatch Events (5-minute schedule). Scans `media-sagas` for timed-out saga instances and dispatches the appropriate compensation command.

| Saga Type | Status Scanned | Condition | Command Dispatched | Status |
|---|---|---|---|---|
| `AssetIngestionSaga` | `ProcessingDispatched` | `Payload.TimeoutAt < now` | `FailAssetProcessingCommand(FailureCategory.ProcessingTimeout)` | ✅ Implemented (`AssetIngestionTimeoutScanner`) |
| `DocumentSigningSaga` | `AwaitingSigners` | `Payload.TimeoutAt < now` | `ExpireSigningSessionCommand(signingSessionId)` | 🔴 Planned/Deferred — `DocumentSigningTimeoutScanner` not yet implemented |

Each saga type has its own configurable TTL — asset processing defaults to 4 hours; document signing defaults to 72 hours to accommodate human signing latency. The scanner is stateless: it reads `media-sagas` and dispatches one command per expired saga. Idempotency is enforced by the aggregate (`ExpireSigningSession` and `FailAssetProcessing` are no-ops on already-terminal aggregates).

---

## Cross-Context Relationships

```
┌─────────────────────────────────────────────────────────────┐
│  UPSTREAM (external)                                         │
│  Identity (JWT)          Billing / Quotas (sync HTTP)        │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│  MEDIA MANAGEMENT (this platform)                            │
│                                                              │
│  AssetManagement ←──────────── Processing                    │
│       │                             │                        │
│  Catalog ───────── ChangeRequests   │                        │
│       │                             │                        │
│       ├───────── DocumentSigning ───┘                        │
│       │                                                      │
│       └───────── Registration                                │
│                                                              │
│  Metadata ──────────────────── (referenced by all above)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ Integration events (SNS → SQS)
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        Notifications    Search/Discovery    SecuredSigning
        (downstream)     (downstream)        (external)
```

### External Context Integrations

| Context | Type | Integration Pattern |
|---|---|---|
| Identity | Upstream | JWT validated at API Gateway; `OwnerId` from `sub` claim via `IdentityAcl`. No runtime calls. |
| Billing / Quotas | Upstream | Sync HTTP from Ingest API before pre-signed URL issuance. `BillingAcl` translates response. Items whose `MediaProfile` lacks `Processing` capability are quota-exempt. |
| Notifications | Downstream | Owns its own SQS queue subscribed to `media-integration-events` SNS with a filter policy for the integration events it consumes. Media Management publishes and forgets. |
| Search / Discovery | Downstream | Owns its own SQS queue subscribed to `media-integration-events` SNS. Maintains its own index from the integration event stream. |
| Billing (integration consumer) | Downstream | Owns its own SQS queue subscribed to `media-integration-events` SNS. Consumes `media.asset.processing-completed` (pre-filtered inline by `AssetIntegrationEventPublisher` on `Processing` capability), `media.mediaitem.published`, `media.mediaitem.archived`, `media.collection.created`, `media.collection.archived`. |
| Compliance (integration consumer) | Downstream | Owns its own SQS queue subscribed to `media-integration-events` SNS. Consumes `media.registration.confirmed`. |
| SecuredSigning | External | `SecuredSigning Adapter` Lambda is the sole integration point. No other service calls SecuredSigning. `TenantId` on webhook path resolved from `media-signing-sessions` lookup table keyed by `EnvelopeId`. |

### Internal Context Dependencies

| Context | Depends On | Dependency Type |
|---|---|---|
| Catalog (MediaItem, MediaProfile) | Metadata (RecordType) | Read — MediaProfile pins RecordType versions; RecordType schema validates MediaItem metadata |
| AssetManagement (Asset) | Catalog (MediaItem) | Optional reference — `MediaItemId` is nullable |
| ChangeRequests (ChangeRequest) | Catalog (MediaItem) | Reference via `MediaItemId` |
| DocumentSigning (DocumentSigningSession) | Catalog (MediaItem) | Reference via `MediaItemId`; checkout managed via events |
| Registration (Registration) | Catalog (MediaItem) | Reference via `MediaItemId` |
| Processing (Worker) | AssetManagement (Asset) | Integration events via SNS → `media-cross-module-events` — Processing publishes `ProcessingJobScanResultIntegrationEvent`; AssetManagement owns all `RecordValidation*` command dispatch |

---

## Infrastructure Overview

### Services

| Service | Runtime | Role |
|---|---|---|
| Ingest API | Lambda / ECS (ASP.NET, FastEndpoints) | Accepts write requests; dispatches commands |
| Query API | Lambda / ECS (ASP.NET, FastEndpoints) | Serves all read traffic |
| Command Handler | Lambda (MediatR) | Aggregate lifecycle, event store writes, SNS publish |
| Projectors (13) | Lambda (SQS-triggered) | Maintain DynamoDB and OpenSearch read models |
| Processing Worker | Lambda (SQS-triggered) | Rendition generation; metadata extraction |
| SagaOrchestrator | Lambda (SQS-triggered) | Cross-aggregate coordination |
| SagaTimeoutScanner | Lambda (CloudWatch scheduled) | Processing timeout enforcement |
| SecuredSigning Adapter | Lambda (SQS + webhook) | SecuredSigning API integration |

### Projector Inventory

All projectors subscribe to the `media-projector` SQS queue and run as a single multi-handler Lambda (`Media.Projectors.Lambda`). Read-model projectors are query-facing; write-side reference index projectors are used by command handlers for constraint enforcement.

**Read-model projectors:**

| Projector | Context | Read Models Maintained |
|---|---|---|
| `AssetDetailProjector` | AssetManagement | `media-asset-detail` |
| `AssetSummaryProjector` | AssetManagement | `media-assets` |
| `CollectionDetailProjector` | Catalog | `media-collection-detail` |
| `CollectionSummaryProjector` | Catalog | `media-collections` |
| `FolderDetailProjector` | Catalog | `media-folder-detail` |
| `FolderSummaryProjector` | Catalog | `media-folders` |
| `MediaItemDetailProjector` | Catalog | `media-item-detail` |
| `MediaItemSummaryProjector` | Catalog | `media-items` (all GSIs) |
| `MediaItemVersionProjector` | Catalog | `media-item-versions` |
| `MediaProfileDetailProjector` | Catalog | `media-profiles` |
| `MediaProfileVersionProjector` | Catalog | `media-profile-versions` |
| `ChangeRequestDetailProjector` | ChangeRequests | `media-change-request-detail` |
| `ChangeRequestSummaryProjector` | ChangeRequests | `media-change-requests` |
| `ChangeRequestCommentProjector` | ChangeRequests | `media-change-request-comments` |
| `SigningSessionDetailProjector` | DocumentSigning | `media-signing-session-detail` |
| `SigningSessionSummaryProjector` | DocumentSigning | `media-signing-sessions` | 🔴 Deferred — `DocumentSigning` module not yet complete |
| `RegistrationDetailProjector` | Registration | `media-registration-detail` |
| `RegistrationSummaryProjector` | Registration | `media-registrations` |
| `RecordTypeDetailProjector` | Metadata | `media-record-types` |
| `RecordTypeSummaryProjector` | Metadata | `media-record-types` |
| `RecordTypeVersionProjector` | Metadata | `media-record-types` |

**Write-side reference index projectors** (see `system-architecture.md` for full table list and gap status):
`FolderChildIndexProjector`, `FolderMediaItemsIndexProjector`, `RegistrationCountIndexProjector`, `FolderActiveItemCountIndexProjector`, `MediaProfileIndexProjector`, `RecordTypeVersionDetailIndexProjector`

### OpenSearch Indexes

**`media-items`** — primary search surface

| Field | Type |
|---|---|
| `tenantId` | keyword |
| `mediaItemId` | keyword |
| `collectionId` | keyword |
| `folderId` | keyword |
| `ownerId` | keyword |
| `title` | text (analyzed) |
| `status` | keyword |
| `isAccessible` | boolean |
| `mediaProfileId` | keyword |
| `tags` | keyword[] |
| `metadata` | object — `IsSearchable = true` fields only; per-`FieldType` mapping |
| `createdAt` / `publishedAt` | date |

**`media-registrations`** — media-registration search / facet filtering

| Field | Type |
|---|---|
| `tenantId` / `registrationId` / `mediaItemId` / `ownerId` | keyword |
| `registrationType` / `registrationAuthority` / `status` | keyword |
| `submittedAt` / `confirmedAt` | date |

Index aliases (`media-items-v1` → alias `media-items`) allow zero-downtime reindexing.

### WAF Web ACL

A WAFv2 Web ACL (`REGIONAL` scope) is associated with every API Gateway stage. It is provisioned alongside the API Gateway in CDK (`waf.construct.ts`) and configured identically across all environments — rule priority and action never vary by environment.

**Managed rule groups (all in `Block` override mode):**

| Priority | Rule Group | Coverage |
|---|---|---|
| 10 | `AWSManagedRulesCommonRuleSet` | OWASP Top 10 core rules (XSS, path traversal, protocol violations, bad bots) |
| 20 | `AWSManagedRulesKnownBadInputsRuleSet` | Known exploitation patterns — Log4j JNDI, Spring4Shell, SSRF probes |
| 30 | `AWSManagedRulesSQLiRuleSet` | SQL injection in query strings, body, URI, and headers |

**Association target:** `arn:aws:apigateway:{region}::/restapis/{restApiId}/stages/{stageName}` — the REST API stage ARN. WAF is evaluated before the request reaches API Gateway throttling or the Lambda integration.

**Default action:** `Allow` — traffic that does not match any managed rule is forwarded to the origin. All matched rule actions are `Block`.

**Scope note:** `REGIONAL` is required for API Gateway v1 (REST API). CloudFront-fronted APIs would additionally require a `CLOUDFRONT`-scoped ACL in `us-east-1`; this is deferred until the CDN layer is introduced (STOR-6).

---

## Observability

- **Structured logs:** Serilog with `TenantId` enriched on every log event (HTTP request or SQS message scope)
- **Distributed tracing:** AWS X-Ray on all Lambda invocations; `TenantId` annotated as first-class dimension
- **Error handling:** Commands return `Result<T, DomainError>` — no domain exceptions escape handlers; Lambda DLQs for infra failures
- **DLQ monitoring:** CloudWatch alarms on DLQ depth for all queues

---

## Naming Conventions

| Artifact | Convention | Example |
|---|---|---|
| Commands | `VerbNoun` (imperative, PascalCase) | `CreateCollection`, `ReplaceFieldInRecordType` |
| Domain Events | `NounPastParticiple` (PascalCase) | `CollectionCreated`, `FieldReplacedInRecordType` |
| Integration Events | `{context}.{noun}.{past-participle}` (dot-separated, lowercase) | `media.collection.created` |
| Aggregates | `PascalCase` noun | `MediaItem`, `RecordType` |
| Value Objects | `PascalCase` noun or noun phrase | `FolderId`, `FieldDefinition` |
| Commands return | `Result<TResponse, DomainError>` | No domain exceptions escape handlers |
| Aggregate IDs | UUID v7-based strongly-typed value objects | `new MediaItemId(Uuid7.NewUuid7())` |
| System owner | Reserved `OwnerId = "owner_system"` | Platform-level RecordTypes and MediaProfiles |
| Tenant key prefix | `TENANT#{TenantId}#` | All DynamoDB PKs |

---

## Ubiquitous Language (Cross-Context)

| Term | Meaning |
|---|---|
| `TenantId` | Immutable tenant boundary identifier. Prefixes all DynamoDB PKs, S3 keys, and event store paths. Sourced from JWT `tenant_id` claim via `IExecutionContext`. |
| `OwnerId` | The `Actor.Id` of the actor who owns a resource, stamped at creation time. Ownership check: `context.Actor.Id == resource.OwnerId`. `"owner_system"` is reserved for platform-level config aggregates. Not a JWT claim. |
| `IActor` | The resolved identity of the calling actor. Sourced from JWT claims (`sub`, `name`, `roles`, `actor_type`) by `HttpExecutionContext`, or constructed from SQS message attributes by `SqsExecutionContext`. |
| Capability | A domain module switch defined on a `MediaProfile`. Activates modules (`Processing`, `Registration`, `Review`, `CheckInOut`, `VersionControl`, `Retention`, `Distribution`, `Governance`) for all `MediaItem`s conforming to that media| `createdAt` | date |
| `publishedAt` | date |

**`media-registrations`** — registration search / facet filtering

| Field | Type |
|---|---|
| `tenantId` | keyword |
| `registrationId` | keyword |
| `mediaItemId` | keyword |
| `ownerId` | keyword |
| `registrationType` | keyword |
| `registrationAuthority` | keyword |
| `status` | keyword |
| `submittedAt` | date |
| `confirmedAt` | date |

Index aliases (`media-items-v1` → alias `media-items`) allow zero-downtime reindexing on schema changes.

---

## CORS Policy

All HTTP origins are rejected by default. Allowed origins are configured per environment as an explicit allowlist — `AllowAnyOrigin` is **never** permitted outside `ASPNETCORE_ENVIRONMENT = Development`.

### Per-Environment Allowed Origins

| Environment | Allowed Origins | Notes |
|---|---|---|
| Development | `http://localhost:*`, `https://localhost:*` | Wildcard port for local dev servers |
| Dev | `https://*.dev.magiqmedia.com` | Dev tenant portals |
| Staging | `https://*.staging.magiqmedia.com` | Staging tenant portals |
| Production | `https://*.magiqmedia.com`, `https://magiqmedia.com` | Production portals only. No wildcards on external domains. |

### Configuration

Allowed origins are sourced from SSM Parameter Store at startup (`/magiq-media/{env}/cors/allowed-origins`, newline-delimited). The CDK stack writes this parameter per environment during deployment.

```csharp
// Startup.cs — correct CORS registration
var allowedOrigins = configuration
    .GetSection("Cors:AllowedOrigins")
    .Get<string[]>() ?? [];

builder.Services.AddCors(options =>
    options.AddDefaultPolicy(policy =>
        policy.WithOrigins(allowedOrigins)
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials()));
```

`AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()` is **prohibited** in staging and production. Any PR introducing this pattern must be rejected at code review. The `media-waf-web-acl` AWS WAF rule set provides a defence-in-depth layer, but it is not a substitute for correct CORS configuration.

### Preflight

CORS preflight (`OPTIONS`) requests are handled by ASP.NET Core middleware. API Gateway is configured to pass `OPTIONS` through to the Lambda — no special API Gateway CORS configuration is used.

---

## Rate Limiting

Rate limiting protects the platform from runaway clients and multi-tenant resource contention. Limits are enforced at the API Gateway throttling layer (quota plans) and at the application layer (per-tenant token bucket).

### Tiers by Actor Type

| Actor Type | Tier | Requests / second | Burst | Notes |
|---|---|---|---|---|
| `Guest` | Guest | 5 req/s per source IP | 10 | Unauthenticated read-only traffic. API Gateway IP-based throttle. |
| `User` | Standard | 50 req/s per `tenant_id` | 200 | Default for all user-authenticated tenants. |
| `User` | Premium | 200 req/s per `tenant_id` | 500 | Enterprise tenants. Configured via API Gateway usage plan assigned to tenant API key. |
| `System` | System | 500 req/s per `tenant_id` | 1000 | Internal service-to-service traffic. Separate usage plan; no burst cap in practice. |

### Write-Side Rate Limiting

Per-tenant write rate limiting is applied at the application layer in the Ingest API, independent of API Gateway throttle. Implemented as a token bucket per `TenantId` with the following defaults:

| Operation category | Sustained rate | Burst |
|---|---|---|
| Asset uploads (initiate) | 20 req/s | 50 |
| All other write commands | 100 req/s | 300 |

Exceeded limits return `429 Too Many Requests` with a `Retry-After` header (seconds until next token replenishment).

### Rate Limit Response

```json
{
  "type": "https://errors.magiqmedia.com/rate-limit/exceeded",
  "title": "Rate limit exceeded",
  "status": 429,
  "detail": "Tenant acme has exceeded the write rate limit for asset uploads. Retry after 2 seconds.",
  "extensions": { "errorCode": "RateLimitExceeded", "retryAfterSeconds": 2 }
}
```

### Configuration

Rate limit thresholds are configurable per environment via SSM Parameter Store (`/magiq-media/{env}/rate-limits/`). Tenant-level overrides are applied via API Gateway usage plans — the CDK stack provisions one usage plan per tier and associates tenant API keys at onboarding.

---

## Disaster Recovery

### RTO / RPO Targets

| Target | Value | Scope |
|---|---|---|
| **RTO** (Recovery Time Objective) | **< 30 minutes** | Time from incident declaration to restored write traffic in the same region |
| **RPO** (Recovery Point Objective) | **< 1 minute** | Maximum data loss. DynamoDB PITR provides continuous backups; SNS/SQS in-flight messages are retained for 14 days in DLQs. |
| Cross-region RTO | < 4 hours | Active-passive cross-region failover (future — see SPEC-19). Not currently implemented. |
| Cross-region RPO | < 15 minutes | DynamoDB global table replication lag (future). Not currently implemented. |

### DR Runbook — Lambda Deployment Rollback

**Trigger:** Lambda function errors exceed 5 % of invocations over 5 minutes, or a P0 incident is declared.

**RTO target:** < 5 minutes from decision to rollback to restored Lambda traffic.

1. **Declare incident.** Page on-call via PagerDuty (or equivalent). Link CloudWatch dashboard.
2. **Identify the bad version.** In AWS Console → Lambda → `Media.Api` → Versions. Identify the version deployed in the last release (check deployment pipeline for the version ARN).
3. **Update alias to previous version.** Run:
   ```bash
   aws lambda update-alias \
     --function-name Media.Api \
     --name live \
     --function-version <previous-version-number>
   ```
   Repeat for `Media.QueryApi`, `Media.Projectors.Lambda`, `Media.SagaOrchestrator.Lambda`, `Media.Processing.Lambda` if affected.
4. **Verify.** Check CloudWatch error rate metrics. Confirm alarm clears within 2 minutes.
5. **Drain in-flight messages.** If projectors or consumers were rolled back, check DLQ depths. Redriving the DLQ after rollback is safe — the projector `ProjectedVersion` guard makes re-processing idempotent.
6. **Post-incident.** File a post-mortem. Do not re-deploy the bad version until root cause is confirmed.

### DR Runbook — DynamoDB Table Recovery

**Trigger:** Accidental data deletion, corruption, or table-level failure.

**RPO target:** < 1 minute (PITR continuous backup).

1. **Stop writes.** Take the affected Lambda(s) out of service by setting reserved concurrency to 0 in the AWS Console (prevents further writes during recovery).
2. **Identify restore point.** Determine the last known-good timestamp from CloudWatch logs or incident timeline.
3. **Restore table to a new table.** In AWS Console → DynamoDB → `{affected-table}` → Backups → Restore. Select point-in-time restore. Name the restored table `{affected-table}-restored-{date}`.
4. **Validate data.** Spot-check key rows in the restored table against expected event log.
5. **Swap table.** Update the SSM Parameter Store key `/magiq-media/{env}/dynamodb/{table-name}` to the restored table name. Restart Lambda functions (update reserved concurrency back to normal).
6. **Rebuild projections if needed.** If a read model table was the victim, run projection rebuild: `dotnet replay --context={context} --from-version=0` (see OBS-5 for tooling spec).
7. **Re-enable writes.** Restore Lambda reserved concurrency.
8. **Post-incident.** File a post-mortem. Delete the old corrupt table only after 7-day observation period.

### DR Runbook — Full Region Failure

Not currently implemented. Cross-region strategy is deferred to SPEC-19. In the event of an AWS region outage:

1. Declare a maintenance window (static error page via CloudFront).
2. Contact AWS support to determine ETA for region recovery.
3. If region ETA > 4 hours, escalate to cross-region failover decision (manual process — see SPEC-19 when implemented).

### Backup Verification Schedule

| Resource | Backup mechanism | Verification cadence |
|---|---|---|
| All DynamoDB read model tables | PITR (continuous) | Monthly restore test to `{table}-verify` table |
| `media-events` event store | PITR (continuous) | Quarterly full restore + projection rebuild test |
| `media-sagas` | PITR (continuous) | Monthly |
| S3 buckets (`media-source`, `media-renditions`, `media-documents`) | S3 Versioning + replication (future) | Quarterly |
