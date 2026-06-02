# DocumentSigning — Context Overview

_Context: `DocumentSigning`_

---

## Purpose

Manages the full SecuredSigning envelope lifecycle for a single `MediaItem` checkout. The `DocumentSigningSession` aggregate tracks envelope creation, signer completions, the signed asset, and all terminal states (completion, void, cancellation, timeout). It isolates SecuredSigning-specific state (envelope IDs, signer routing orders, webhook events) from the core Catalog domain.

---

## Responsibilities

- Create and track `DocumentSigningSession` instances (one per signing request on a checked-out MediaItem)
- Record SecuredSigning adapter callbacks: envelope created, envelope sent, signer completions, signing completed, signed asset recorded, envelope voided
- Handle cancellation (owner-initiated) and expiry (system/scheduler-initiated)
- Maintain the `media-signing-sessions` lookup table for `EnvelopeId → TenantId` resolution on unauthenticated webhook calls
- Work with `DocumentSigningSaga` (in SagaOrchestrator Lambda) to coordinate `LinkSigningSession` / `UnlinkSigningSession` / `CheckInMediaItem` on the linked MediaItem

**Out of scope:** Direct mutation of MediaItem state. The `DocumentSigningSaga` dispatches all cross-aggregate commands (`LinkSigningSession`, `UnlinkSigningSession`, `CheckInMediaItem`, `ForceReleaseCheckout`).

---

## Aggregates

| Aggregate | Description |
|---|---|
| `DocumentSigningSession` | Envelope lifecycle for a single signing request |

---

## Service Boundaries

- **Owns:** `media-signing-sessions` (both the projector read model and the `EnvelopeId` lookup table), `media-signing-session-detail` DynamoDB tables
- **Event stream prefix:** `signing_`
- **External integration:** SecuredSigning via `SecuredSigningAdapter` Lambda — the sole adapter for DocuSign-style electronic signing

---

## External Dependencies

| Dependency | Type | Usage |
|---|---|---|
| `SecuredSigning` | External service | Envelope creation, signer routing, completion webhooks |
| `SecuredSigningAdapter` Lambda | Internal Lambda | Translates SecuredSigning webhooks into domain commands |
| `Catalog` context | Shared lifecycle | `DocumentSigningSaga` coordinates `MediaItem` checkout lock via `LinkSigningSession`, `UnlinkSigningSession`, `CheckInMediaItem`, `ForceReleaseCheckout` |
| `AssetManagement` context | Output | Adapter creates a new `Asset` record (signed document) via `UploadAsset` after signing completes |

---

## Event Flows

### Inbound (triggers)

| Event | Source | Handling |
|---|---|---|
| `SigningSessionInitiated` | HTTP `POST /media-items/{id}/media-signing-sessions` | Creates `DocumentSigningSession`; `DocumentSigningSaga` created; adapter triggered |
| SecuredSigning webhook | `POST /integrations/secured-signing/webhook` | Validated by HMAC; `TenantId` resolved via `media-signing-sessions[EnvelopeId]` |

### Outbound (emitted by this context)

| Event | Consumer |
|---|---|
| `SigningSessionInitiated` | `DocumentSigningSaga` → dispatch `LinkSigningSession`; `SecuredSigningAdapter` → create envelope |
| `SigningEnvelopeCreated` | `DocumentSigningSaga` → transition; `SigningSessionProjector` → write `EnvelopeId` to lookup table |
| `SigningCompleted` | `DocumentSigningSaga` → dispatch `UnlinkSigningSession`, then `CheckInMediaItem` |
| `SignedAssetRecorded` | `DocumentSigningSaga` → transition to `ReleasingLock` |
| `SigningEnvelopeVoided` | `DocumentSigningSaga` → compensation path: dispatch `ForceReleaseCheckout` |
| `SigningSessionCancelled` | `DocumentSigningSaga` → compensation path |
| `SigningSessionTimedOut` | `DocumentSigningSaga` → compensation path |

---

## SecuredSigning Adapter

The `SecuredSigningAdapter` Lambda is the sole integration point for the SecuredSigning external service. It:

1. Listens on `signing-requests` SQS queue for `SigningSessionInitiated` events
2. Calls SecuredSigning API to create an envelope → dispatches `RecordEnvelopeCreated`
3. Receives webhooks at `POST /integrations/secured-signing/webhook` (unauthenticated, HMAC-validated)
4. Dispatches `RecordEnvelopeSent`, `RecordSignerCompleted`, `RecordSigningCompleted` as events arrive
5. On `SigningCompleted`: downloads signed PDF from SecuredSigning, uploads to S3 as new Asset, dispatches `RecordSignedAsset`

**Webhook TenantId resolution:** `POST /integrations/secured-signing/webhook` carries no JWT. `TenantId` is resolved from the `media-signing-sessions` lookup table keyed by `EnvelopeId`. This lookup row is written by `SigningSessionProjector` when `SigningEnvelopeCreated` is processed.

---

## Integration Events

This context publishes no integration events directly to `media-integration-events`. Outcomes are reflected through Catalog's `media.mediaitem.published` or `media.mediaitem.rejected` events.

---

## Ubiquitous Language

| Term | Definition |
|---|---|
| `DocumentSigningSession` | An aggregate tracking the full lifecycle of a SecuredSigning envelope for one MediaItem signing request |
| `SigningSessionStatus` | `Initiated → EnvelopeCreated → EnvelopeSent → Completed → SignedAssetRecorded` (happy path); also `Voided`, `Cancelled`, `TimedOut` (terminal failure states) |
| `Signer` | `{ Email, RoutingOrder, Status }` — a party in the signing envelope |
| `EnvelopeId` | The external SecuredSigning envelope identifier. Written to the `media-signing-sessions` lookup table keyed by `EnvelopeId` for webhook `TenantId` resolution |
| `SignerSpec` | Value type used at creation: `{ Email, RoutingOrder }` |
| `CompletionToken` | Validated by `RecordSigningCompleted` aggregate guard |
| `DocumentSigningSaga` | Orchestrates MediaItem checkout lock linkage and release across the signing lifecycle |

---

## Related

- [DocumentSigningSession Write Model](./aggregates/DocumentSigningSession/documentsigningsession.write-model.md)
- [DocumentSigningSession Read Model](./aggregates/DocumentSigningSession/documentsigningsession.read-model.md)
- [DocumentSigningSession API](./aggregates/DocumentSigningSession/documentsigningsession.api.md)
- [DocumentSigning Business Scenarios](./business-scenarios.md)
- [MediaItem Write Model](../Catalog/aggregates/MediaItem/mediaitem.write-model.md)
- [System Spec — Saga Coordination](../../shared/system-spec.md#saga-coordination-patterns)
