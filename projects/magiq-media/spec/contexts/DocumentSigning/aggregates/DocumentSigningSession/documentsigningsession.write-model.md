# DocumentSigningSession — Write Model

_Context: `DocumentSigning`_
_Aggregate: `DocumentSigningSession`_
_Stream prefix: `signing_`_

---

## Purpose

Tracks the SecuredSigning envelope lifecycle for a single MediaItem signing request. Isolates all SecuredSigning-specific state (envelope ID, signer routing, webhook event sequence) from the core `MediaItem` aggregate. One `DocumentSigningSession` is created per signing request; a new session is required for each retry.

The aggregate is managed by the `DocumentSigningSaga`, which coordinates the checkout lock lifecycle across `DocumentSigningSession` and `MediaItem`.

> **Status:** This aggregate does not yet exist in the codebase. Implementation must follow the TenantId-first convention established in the multi-tenancy plan.

---

## Invariants

| Rule | Error | Command |
|---|---|---|
| MediaItem must be `CheckedOut` by the initiating owner | `MediaItemNotCheckedOut` | `InitiateSigningSession` (handler-side) |
| MediaItem must have no active signing session | `SigningSessionInProgress` | `InitiateSigningSession` (handler-side) |
| MediaProfile must have `DigitalSigning` capability | `CapabilityNotEnabled` | `InitiateSigningSession` (handler-side) |
| `CancelSession` only valid in `Initiated` or `EnvelopeCreated` status | `SigningSessionNotCancellable` | `CancelSession` |
| `CompletionToken` must be valid | `InvalidCompletionToken` | `RecordSigningCompleted` |
| All signers must be `Completed` before signing completion | `SignersNotAllCompleted` | `RecordSigningCompleted` |

---

## Properties

| Property           | Type                    | Notes                                                                                               |
| ------------------ | ----------------------- | --------------------------------------------------------------------------------------------------- |
| `SigningSessionId` | `SigningSessionId`      | UUID v7-based. Caller-generated.                                                                    |
| `TenantId`         | `TenantId`              | Set from `SigningSessionInitiated`. Immutable. First field on creation event.                       |
| `MediaItemId`      | `MediaItemId`           | The MediaItem under checkout. Immutable.                                                            |
| `OwnerId`          | `OwnerId`               |                                                                                                     |
| `InitiatedBy`      | `UserId`                | Acting user identity at session creation. Sourced from JWT `sub` claim, not the resource `OwnerId`. |
| `Status`           | `SigningSessionStatus`  | See lifecycle.                                                                                      |
| `EnvelopeId`       | `string?`               | Set when envelope is created by SecuredSigning.                                                     |
| `Signers`          | `IReadOnlyList<Signer>` | `{ Email, RoutingOrder, Status }`                                                                   |
| `SignedAssetId`    | `AssetId?`              | Set when the signed document Asset is recorded.                                                     |

---

## Status Lifecycle

```
Initiated
    │
    │  RecordEnvelopeCreated (SecuredSigning Adapter)
    ▼
EnvelopeCreated
    │
    │  RecordEnvelopeSent
    ▼
EnvelopeSent
    │
    │  RecordSignerCompleted (per signer — no status change)
    │  RecordSigningCompleted (all signers done)
    ▼
Completed
    │
    │  RecordSignedAsset (Adapter uploads signed PDF)
    ▼
SignedAssetRecorded  ← (saga releases checkout lock)
```

**Terminal failure states (accessible from earlier states):**
- `Voided` — SecuredSigning voided the envelope (e.g., expired, admin void)
- `Cancelled` — Owner cancelled from `Initiated` or `EnvelopeCreated`
- `TimedOut` — System/scheduler expired the session

All failure states trigger `DocumentSigningSaga` compensation: `ForceReleaseCheckout` on the MediaItem.

---

## Value Objects

| Value Object | Description |
|---|---|
| `SigningSessionId` | UUID v7 string, immutable |
| `SignerSpec` | `{ Email, RoutingOrder }` — creation-time input |
| `Signer` | `{ Email, RoutingOrder, Status: SignerStatus }` — tracked state |
| `SignerStatus` | `Pending \| Completed` |
| `SigningSessionStatus` | `Initiated \| EnvelopeCreated \| EnvelopeSent \| Completed \| SignedAssetRecorded \| Voided \| Cancelled \| TimedOut` |

---

## Methods (Commands)

| Method | Description |
|---|---|
| `DocumentSigningSession.Initiate(tenantId, id, mediaItemId, ownerId, initiatedBy: UserId, initialSigners, now)` | Factory. `TenantId` is first parameter. |
| `RecordEnvelopeCreated(envelopeId, now)` | Sets `EnvelopeId`, status → `EnvelopeCreated`. Called by SecuredSigning Adapter. |
| `RecordEnvelopeSent(now)` | Status → `EnvelopeSent`. |
| `RecordSignerCompleted(signerEmail, now)` | Updates individual `Signer.Status = Completed`. No aggregate status change. |
| `RecordSigningCompleted(completionToken, now)` | Validates token; validates all signers completed; status → `Completed`. |
| `RecordSignedAsset(assetId, now)` | Sets `SignedAssetId`, status → `SignedAssetRecorded`. |
| `RecordEnvelopeVoided(reason, now)` | Status → `Voided`. Triggers saga compensation. |
| `CancelSession(cancelledBy, reason, now)` | Only valid in `Initiated` / `EnvelopeCreated`. Status → `Cancelled`. |
| `ExpireSession(now)` | System-only. Status → `TimedOut`. |

---

## Domain Events

| Event | Key Payload Fields | Status Transition |
|---|---|---|
| `SigningSessionInitiated` | `TenantId`†, `SigningSessionId`, `MediaItemId`, `OwnerId`, `InitiatedBy: UserId`, `InitialSigners[]`, `InitiatedAt` | → `Initiated` |
| `SigningEnvelopeCreated` | `SigningSessionId`, `EnvelopeId`, `CreatedAt` | → `EnvelopeCreated` |
| `SigningEnvelopeSent` | `SigningSessionId`, `SentAt` | → `EnvelopeSent` |
| `SignerCompleted` | `SigningSessionId`, `SignerEmail`, `CompletedAt` | — (individual signer state) |
| `SigningCompleted` | `SigningSessionId`, `CompletionToken`, `CompletedAt` | → `Completed` |
| `SignedAssetRecorded` | `SigningSessionId`, `AssetId`, `RecordedAt` | → `SignedAssetRecorded` |
| `SigningEnvelopeVoided` | `SigningSessionId`, `Reason`, `VoidedAt` | → `Voided` |
| `SigningSessionCancelled` | `SigningSessionId`, `CancelledBy`, `Reason`, `CancelledAt` | → `Cancelled` |
| `SigningSessionTimedOut` | `SigningSessionId`, `TimedOutAt` | → `TimedOut` |

† `TenantId` is the **first field** on the creation event.

---

## Commands

| Command | Notes |
|---|---|
| `InitiateSigningSessionCommand(SigningSessionId, MediaItemId, OwnerId, InitiatedBy: UserId, InitialSigners[])` | User-facing. `SigningSessionId` caller-generated (UUID v7). `InitiatedBy` sourced from JWT `sub` claim. |
| `RecordEnvelopeCreatedCommand(SigningSessionId, EnvelopeId)` | System/Adapter only. |
| `RecordEnvelopeSentCommand(SigningSessionId)` | System/Adapter only. |
| `RecordSignerCompletedCommand(SigningSessionId, SignerEmail)` | System/Adapter only. |
| `RecordSigningCompletedCommand(SigningSessionId, CompletionToken)` | System/Adapter only. |
| `RecordSignedAssetCommand(SigningSessionId, AssetId)` | System/Adapter only. |
| `RecordEnvelopeVoidedCommand(SigningSessionId, Reason)` | System/Adapter only. |
| `CancelSigningSessionCommand(SigningSessionId, CancelledBy, Reason)` | User-facing (owner only). |
| `ExpireSigningSessionCommand(SigningSessionId)` | System-only. Dispatched by scheduler Lambda. |

---

## Handler Pre-conditions

| Handler | Pre-condition | Interface | Error |
|---|---|---|---|
| `InitiateSigningSessionHandler` | MediaItem `CheckedOut` by initiating owner | `IMediaItemQueryService.GetCheckoutStateAsync` | `MediaItemNotCheckedOut` |
| `InitiateSigningSessionHandler` | No active signing session on MediaItem | `IMediaItemQueryService.GetCheckoutStateAsync` | `SigningSessionInProgress` |
| `InitiateSigningSessionHandler` | MediaProfile has `Signing` capability | `IMediaProfileQueryService.GetPublishedAsync` | `CapabilityNotEnabled` |
| `RecordSigningCompletedHandler` | `CompletionToken` validated aggregate-side | — | `InvalidCompletionToken` |
| All Adapter commands | `actor_type = "System"` at API Gateway | — | `403` |
| `ExpireSigningSessionHandler` | `actor_type = "System"` at API Gateway | — | `403` |

---

## Write Model Service Interfaces

```csharp
/// <summary>
/// Write-side query service for MediaItem checkout state.
/// Used by InitiateSigningSessionHandler to validate checkout prerequisites
/// without loading the full MediaItem aggregate.
/// </summary>
interface IMediaItemQueryService {
    /// <summary>
    /// Returns a lightweight checkout snapshot for the given MediaItem,
    /// or null if not found.
    /// </summary>
    Task<CheckoutState?> GetCheckoutStateAsync(
        TenantId tenantId, MediaItemId mediaItemId, CancellationToken ct = default);
}

/// <summary>
/// Write-side query service for MediaProfile capabilities.
/// Used by InitiateSigningSessionHandler to verify the Signing
/// capability is active on the media-item's media-profile.
/// </summary>
interface IMediaProfileQueryService {
    /// <summary>
    /// Returns a lightweight media-profile summary for a published media-profile,
    /// or null if not found or not in Published status.
    /// </summary>
    Task<MediaProfileSummary?> GetPublishedAsync(
        TenantId tenantId, MediaProfileId mediaProfileId, CancellationToken ct = default);
}

/// <summary>
/// Lightweight checkout snapshot returned by IMediaItemQueryService.GetCheckoutStateAsync.
/// Carries the fields needed by InitiateSigningSessionHandler to verify:
///   (1) the media-item is checked out by the initiating owner — CheckedOutBy must equal command.InitiatedBy,
///       null means not checked out at all,
///   (2) there is no ActiveSigningSessionId already set,
///   (3) the MediaProfileId for the subsequent media-profile capability check.
/// </summary>
sealed record CheckoutState(
    MediaItemId MediaItemId,
    MediaProfileId MediaProfileId,
    UserId? CheckedOutBy,
    SigningSessionId? ActiveSigningSessionId
);

/// <summary>
/// Lightweight media-profile summary returned by IMediaProfileQueryService.GetPublishedAsync.
/// Carries capabilities as strings — DocumentSigning must not take a hard dependency on
/// Catalog.Domain to perform a single capability check. The Catalog-side implementation
/// maps CapabilitySet to strings via CapabilitySet.AsStringList() before returning.
///
/// NOTE: Signing is a planned Capability value; it does not yet exist in the
/// Catalog.Domain Capability enum. It must be added there before this handler can go live.
/// Current enum values: Registration, CheckInOut, Retention, Review, Processing,
/// Distribution, Governance, VersionControl.
/// </summary>
sealed record MediaProfileSummary(
    MediaProfileId MediaProfileId,
    IReadOnlySet<string> Capabilities
);
```

### `IMediaItemQueryService` — usage

| Handler | Method | Checks performed on result |
|---|---|---|
| `InitiateSigningSessionHandler` | `GetCheckoutStateAsync` | `CheckedOutBy == command.InitiatedBy` — null or different user → `MediaItemNotCheckedOut`; `ActiveSigningSessionId == null` (else `SigningSessionInProgress`); extracts `MediaProfileId` for media-profile query |

### `IMediaProfileQueryService` — usage

| Handler | Method | Checks performed on result |
|---|---|---|
| `InitiateSigningSessionHandler` | `GetPublishedAsync` | `Capabilities.Contains("Signing")` (else `CapabilityNotEnabled`) |

---

## `IExecutionContext` Source by Entry-Point

| Entry-point | Implementation | `TenantId` source |
|---|---|---|
| HTTP (FastEndpoints) | `HttpExecutionContext` | JWT `tenant_id` claim |
| SecuredSigning Adapter Lambda (SQS-triggered) | `SqsExecutionContext` | SNS message attribute `TenantId` |
| Webhook `POST /integrations/secured-signing/webhook` | `SqsExecutionContext` (after lookup) | `media-signing-sessions[EnvelopeId].TenantId` |
| Scheduler / expiry Lambda | `SqsExecutionContext` | SNS message attribute `TenantId` |

---

## Published Integration Events

This context publishes **no integration events** to `media-integration-events`. Signing outcomes are reflected through Catalog — the `DocumentSigningSaga` dispatches `CheckInMediaItem` and `UnlinkSigningSession` commands back to Catalog, whose resulting domain events (`MediaItemCheckedIn`, `MediaItemSigningSessionUnlinked`) then drive downstream state. Final publication or rejection of the media-item, once signed, flows through Catalog's existing `MediaItemApproved` / `MediaItemRejected` integration events.

---

## Consumed Integration Events

This write model consumes **no integration events**. All handler inputs arrive via:

- HTTP API calls (`InitiateSigningSession`, `CancelSigningSession`)
- SecuredSigning webhook (`POST /integrations/secured-signing/webhook`) — HMAC-validated; `TenantId` resolved from `media-signing-sessions[EnvelopeId]` lookup table, not from an integration event
- Intra-context saga command dispatch (`DocumentSigningSaga` drives all subsequent state transitions)

The `IMediaItemQueryService` and `IMediaProfileQueryService` reference models used by `InitiateSigningSessionHandler` are backed by **direct DynamoDB queries** on Catalog's `media-items` and `media-profiles` tables (ACL pattern) — no local projection or event subscription is maintained.

---

## Saga Involved

- **`DocumentSigningSaga`** — triggered on `SigningSessionInitiated`. Manages checkout lock lifecycle: dispatches `LinkSigningSession`, `UnlinkSigningSession`, `CheckInMediaItem`, `ForceReleaseCheckout` (in compensation paths).

See: [System Spec — Saga Coordination](../../../../shared/system-spec.md#saga-coordination-patterns)

---

## Reference Models

Reference models consumed by this write model's command handlers. All are read-only projections; this context never writes to them directly.

---

### `media-items` (DynamoDB — checkout state slice)

**Owned by:** Catalog  
**Consumed via:** `IMediaItemQueryService` (`GetCheckoutStateAsync`)  
**Used by:** `InitiateSigningSessionHandler` — performs a lightweight existence and checkout check before creating the session, avoiding a full aggregate load across context boundaries.

| Field | Type | Purpose |
|---|---|---|
| `MediaItemId` | `string` | Lookup key |
| `MediaProfileId` | `string` | Passed to the subsequent `IMediaProfileQueryService` call to verify `Signing` capability |
| `CheckedOutBy` | `UserId?` | Must equal `command.InitiatedBy` — null or different user → `MediaItemNotCheckedOut` |
| `ActiveSigningSessionId` | `SigningSessionId?` | Must be null — non-null → `SigningSessionInProgress` |

**Subscribed integration events (projector owned by DocumentSigning, consuming Catalog via `media-projector` SQS queue):**

| Event | Source | Write |
|---|---|---|
| `MediaItemCreated` | Catalog | INSERT with `CheckedOutBy = null`, `ActiveSigningSessionId = null`, `MediaProfileId` |
| `MediaItemCheckedOut` | Catalog | UPDATE `CheckedOutBy`, `CheckedOutAt` |
| `MediaItemCheckedIn` / `MediaItemCheckoutAbandoned` / `MediaItemCheckoutForceReleased` | Catalog | UPDATE `CheckedOutBy = null` |
| `MediaItemSigningSessionLinked` | Catalog | UPDATE `ActiveSigningSessionId` |
| `MediaItemSigningSessionUnlinked` | Catalog | UPDATE `ActiveSigningSessionId = null` |

---

### `media-profiles` (DynamoDB — capabilities slice)

**Owned by:** Catalog  
**Consumed via:** `IMediaProfileQueryService` (`GetPublishedAsync`)  
**Used by:** `InitiateSigningSessionHandler` — after resolving `MediaProfileId` from the checkout state, verifies the `Signing` capability is present. DocumentSigning must not take a hard dependency on `Catalog.Domain`, so capabilities are exposed as strings.

| Field | Type | Purpose |
|---|---|---|
| `MediaProfileId` | `string` | Lookup key |
| `Capabilities` | `string[]` | Must contain `"Signing"` — absence → `CapabilityNotEnabled` |

**Subscribed integration events (projector owned by DocumentSigning, consuming Catalog via `media-projector` SQS queue):**

| Event | Source | Write |
|---|---|---|
| `MediaProfilePublished` | Catalog | UPSERT `Capabilities` from `MediaProfilePublishedSnapshot` |
| `MediaProfileDeprecated` | Catalog | UPDATE — mark deprecated; `GetPublishedAsync` returns null for deprecated media-profiles |

---

## Related

- [DocumentSigningSession Read Model](./documentsigningsession.read-model.md)
- [DocumentSigningSession API](./documentsigningsession.api.md)
- [DocumentSigning Business Scenarios](../../business-scenarios.md)
- [MediaItem Write Model](../../../Catalog/aggregates/MediaItem/mediaitem.write-model.md)
