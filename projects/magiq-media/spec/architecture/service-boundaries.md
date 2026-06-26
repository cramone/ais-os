# Service Boundary Document — Media Management

_Last updated: 2026-03-11_

---

## Purpose

This document defines the ownership, API surface, and integration contracts for each service in the Media Management bounded context. It is the source of truth for what each service owns, what it exposes, and what it must never do.

---

## Services at a Glance

| Service | Owns | Exposes | Consumes |
|---|---|---|---|
| Ingest API | Upload flow, pre-signed URL issuance, command dispatch | REST (write endpoints) | S3 events via SQS |
| Query API | Read model queries | REST (read endpoints) | DynamoDB, OpenSearch |
| Command Handler | Aggregate lifecycle, event store | Internal (MediatR) | Commands from Ingest API and SQS triggers |
| Projectors | Read model state | None (write to DynamoDB/OpenSearch) | Domain events via SQS |
| Processing Worker | Rendition generation, metadata extraction | None | `AssetValidationPassed` via SQS |
| SecuredSigning Adapter | SecuredSigning envelope lifecycle | Webhook endpoint | `SigningSessionInitiated` via SQS; SecuredSigning webhooks |
| Module `*IntegrationEventPublisher` classes (distributed, ADR-005) | Domain → integration event translation (inline with Command Handler) | SNS topic `media-integration-events` | Domain events via `IDomainEventHandler<T>` in-process |
| Integration Event Consumers | Intra-BC cross-module consumers (capability index, saga triggers) | None (write to module-local read models or dispatch commands) | Integration events via `media-cross-module-events` SQS |

---

## Service Boundaries

---

### Ingest API

**Owns:** The upload initiation flow. Nothing else.

**Responsibilities:**
- Authenticate the request (validate JWT, resolve `IActor` via `IdentityAcl`)
- Validate request metadata (file name, declared content type, declared size)
- Issue pre-signed S3 PUT URL (15-minute TTL)
- Dispatch `UploadAsset` command to Command Handler (synchronous Lambda invoke or in-process MediatR)
- Receive S3 event completion notification via SQS and dispatch `ConfirmAssetUpload` command
- Dispatch all other write commands (`CreateMediaItem`, `AssignMediaItemToFolder`, `CreateCollection`, `CreateFolder`, etc.)

**Does NOT:**
- Write directly to DynamoDB
- Read from DynamoDB or OpenSearch
- Perform any processing or transformation of the asset binary
- Make synchronous calls to Processing Worker

**Contracts:**

`POST /media-assets/upload-url` — standalone asset upload (drag-and-drop; no MediaItem required)
```json
Request:
{
  "fileName": "string",
  "contentType": "image/jpeg | video/mp4 | audio/mpeg | application/pdf",
  "sizeBytes": 1048576,
  "mediaItemId": "018e4c7a-3f10-7b2a-8c4d-1a2b3c4d5e6f"  // optional
}

Response 202:
{
  "assetId": "018e4c7a-3f10-7b2a-8c4d-1a2b3c4d5e6f",
  "uploadUrl": "https://s3.amazonaws.com/...",
  "expiresAt": "2026-03-11T12:15:00Z"
}
```

**Error surface:** 400 (validation), 401 (unauthenticated), 413 (size exceeds quota), 429 (rate limit).

**Quota enforcement:** `UploadAssetHandler` resolves `Processing` capability state via `IMediaItemCapabilityReadModel` (backed by the `media-item-capabilities` reference model, projected from Catalog events). If the media-item lacks the `Processing` capability the handler short-circuits quota evaluation — the asset is a quota-exempt document. Otherwise the handler calls `IBillingAcl.CheckQuotaAsync(OwnerId, SizeBytes)`; a non-`Allowed` result surfaces as 413 at the endpoint.

---

### Query API

**Owns:** All read traffic for media media-assets, media-items, media-collections, media-folders, media-registrations, and configuration within this bounded context.

**Responsibilities:**
- Serve media-item detail, media-folder hierarchies, media-collection detail, asset detail, media-registration detail
- Serve search and filter queries via OpenSearch (`media-items`, `media-registrations` indexes)
- Serve RecordType and MediaProfile configuration reads
- Translate query results into versioned response DTOs

**Does NOT:**
- Accept any write operations
- Load aggregates from the event store
- Call Ingest API or Command Handler
- Return raw domain objects or event payloads

**Contracts (representative):**

```
// Assets
GET /media-assets/{assetId}                          → AssetDetailDto
GET /media-assets?mediaItemId=&status=               → PagedResult<AssetSummaryDto>
POST /media-assets/{assetId}/confirm                 → 202 (dispatches ConfirmAssetUpload)

// Media Items
GET /media-items/{mediaItemId}                 → MediaItemDetailDto
GET /media-items?ownerId=&folderId=&status=    → PagedResult<MediaItemSummaryDto>
GET /media-items?assigned=false                → PagedResult<MediaItemSummaryDto> (unassigned pool)
GET /media-items/{mediaItemId}/versions        → PagedResult<MediaItemVersionSummaryDto>
GET /media-items/{mediaItemId}/versions/{n}    → MediaItemVersionDetailDto

// Collections
GET /media-collections/{collectionId}                → CollectionDetailDto
GET /media-collections?ownerId=                      → PagedResult<CollectionSummaryDto>

// Folders
GET /media-folders/{folderId}                        → FolderDetailDto
GET /media-folders?collectionId=&parentFolderId=     → PagedResult<FolderSummaryDto>

// Registrations
GET /media-registrations/{registrationId}            → RegistrationDetailDto
GET /media-registrations?mediaItemId=&status=        → PagedResult<RegistrationSummaryDto>

// Configuration
GET /media-record-types/{recordTypeId}               → RecordTypeDetailDto
GET /media-record-types/{recordTypeId}/versions      → PagedResult<RecordTypeVersionSummaryDto>
GET /media-profiles/{mediaProfileId}           → MediaProfileDetailDto
GET /media-profiles?ownerId=&status=           → PagedResult<MediaProfileSummaryDto>

// Review
GET /media-change-requests/{mediaChangeRequestId} → MediaChangeRequestDetailDto
GET /media-change-requests?mediaItemId=        → PagedResult<MediaChangeRequestSummaryDto>
```

**Versioning:** All DTOs carry a `schemaVersion` field. Breaking changes produce a new DTO version, served via `Accept: application/vnd.media.v2+json`.

---

### Command Handler

**Owns:** All domain write logic. The event store. Aggregate state.

**Responsibilities:**
- Receive commands (via MediatR, invoked by Ingest API or SQS-triggered Lambda)
- Load aggregate from event store (DynamoDB `media-events` table)
- Apply command via aggregate method
- Persist new events to event store (conditional write, optimistic concurrency)
- Publish resulting events to SQS for downstream fan-out

**Does NOT:**
- Serve any HTTP endpoints directly
- Write to read model tables (`media-items`, `media-item-detail`, `media-assets`, `media-collections`, etc.)
- Call Query API
- Perform any I/O on the asset binary

**Key commands handled (representative):**

| Command | Aggregate | Key Events Raised |
|---|---|---|
| `UploadAsset` | `Asset` (new) | `AssetUploadInitiated` |
| `ConfirmAssetUpload` | `Asset` | `AssetUploadConfirmed` |
| `RecordValidationResult` | `Asset` | `AssetValidationPassed` / `AssetValidationFailed` |
| `StartAssetProcessing` | `Asset` | `AssetProcessingStarted` |
| `CompleteAssetProcessing` | `Asset` | `AssetProcessingCompleted` |
| `FailAssetProcessing` | `Asset` | `AssetProcessingFailed` |
| `TagAsset` | `Asset` | `AssetTagged` |
| `ArchiveAsset` / `DeleteAsset` | `Asset` | `AssetArchived` / `AssetDeleted` |
| `CreateCollection` | `Collection` (new) | `CollectionCreated` |
| `RenameCollection` | `Collection` | `CollectionRenamed` |
| `SetCollectionVisibility` | `Collection` | `CollectionVisibilityChanged` |
| `ArchiveCollection` | `Collection` | `CollectionArchived` |
| `CreateFolder` | `Folder` (new) | `FolderCreated` |
| `RenameFolder` | `Folder` | `FolderRenamed` |
| `MoveFolder` | `Folder` | `FolderMoved` |
| `ArchiveFolder` | `Folder` | `FolderArchived` |
| `CreateMediaItem` | `MediaItem` (new) | `MediaItemCreated`; optionally `MediaItemAssignedToFolder` |
| `AssignMediaItemToFolder` | `MediaItem` | `MediaItemAssignedToFolder` |
| `MoveMediaItem` | `MediaItem` | `MediaItemMoved` |
| `AssignAssetToRole` | `MediaItem` | `AssetAssignedToRole`; optionally `AssetAttachedToMediaItem` (on `Asset`) |
| `SetMetadataField` / `SetMetadataBatch` | `MediaItem` | `MediaItemMetadataFieldSet` / `MediaItemMetadataBatchSet` |
| `RequestPublication` | `MediaItem` | `MediaItemPublicationRequested`; optionally `MediaChangeRequestCreated` + `MediaChangeRequestLinked` |
| `ApproveMediaItem` | `MediaItem` | `MediaItemApproved` |
| `RejectMediaItem` | `MediaItem` | `MediaItemRejected` |
| `CheckOutMediaItem` / `CheckInMediaItem` | `MediaItem` | `MediaItemCheckedOut` / `MediaItemCheckedIn` |
| `InitiateRegistration` | `Registration` (new) | `RegistrationInitiated` |
| `SubmitRegistration` / `ConfirmRegistration` | `Registration` | `RegistrationSubmitted` / `RegistrationConfirmed` |
| `CreateRecordType` | `RecordType` (new) | `RecordTypeCreated` |
| `AddFieldToRecordType` / `ReplaceFieldInRecordType` | `RecordType` | `FieldAddedToRecordType` / `FieldReplacedInRecordType` |
| `CreateMediaProfile` | `MediaProfile` (new) | `MediaProfileCreated` |
| `PublishMediaProfile` / `DeprecateMediaProfile` | `MediaProfile` | `MediaProfilePublished` / `MediaProfileDeprecated` |
| `AssignReviewer` / `ApproveReview` / `RejectReview` | `MediaChangeRequest` | `ReviewerAssigned` / `ReviewApproved` / `MediaChangeRequestApproved` |
| `InitiateSigningSession` | `DocumentSigningSession` (new) | `SigningSessionInitiated` |
| `RecordSigningCompleted` | `DocumentSigningSession` | `SigningCompleted` |

**Return type:** All handlers return `Result<CommandResponse, DomainError>`. No exceptions escape the handler boundary.

---

### Projectors

**Owns:** The read model tables. Their shape. Their consistency guarantees (eventually consistent).

**Responsibilities:**
- Subscribe to domain events from SQS
- Update DynamoDB read models and OpenSearch index
- Be idempotent — replaying an event must produce the same state

**Does NOT:**
- Dispatch commands or raise domain events
- Call external bounded contexts
- Block upstream processing (projectors fail independently; DLQ handles retries)

**Projection map (key events):**

| Projector | Events Consumed | Targets |
|---|---|---|
| `AssetSummaryProjector` | `AssetUploadInitiated`, `AssetMultipartUploadInitiated`, `AssetUploadConfirmed`, `AssetValidationPassed/Failed`, `AssetProcessingStarted/Completed/Failed`, `AssetTagged`, `AssetArchived`, `AssetDeleted`, `AssetAttachedToMediaItem`, `AssetDetachedFromMediaItem`, `AssetStorageTierTransitioned` | `media-assets` |
| `AssetDetailProjector` | Same events as `AssetSummaryProjector` | `media-asset-detail` |
| `CollectionProjector` | `CollectionCreated`, `CollectionRenamed`, `CollectionTagged`, `CollectionVisibilityChanged`, `CollectionDefaultProfileSet`, `CollectionArchived` | `media-collections`, `media-collection-detail`, OpenSearch |
| `FolderProjector` | `FolderCreated`, `FolderRenamed`, `FolderMoved`, `FolderArchived` | `media-folders`, `media-folder-detail` |
| `MediaItemProjector` | `MediaItemCreated`, `MediaItemAssignedToFolder`, `MediaItemMoved`, `MediaItemTitleUpdated`, `MediaItemTagged`, `MediaItemRevertedToDraft`, `MediaItemMetadataFieldSet/BatchSet`, `AssetAssignedToRole`, `AssetUnassignedFromRole`, `MediaItemPublicationRequested`, `MediaItemApproved`, `MediaItemRejected`, `MediaItemArchived`, `MediaChangeRequestLinked/Unlinked` | `media-items` (all GSIs), `media-item-detail`, OpenSearch |
| `MediaItemVersionProjector` | `MediaItemApproved` | `media-item-versions` (full snapshot per publish) |
| `RegistrationProjector` | `RegistrationInitiated`, `RegistrationSubmitted`, `RegistrationConfirmed`, `RegistrationRejected`, `RegistrationCancelled`, `RegistrationDocumentAttached` | `media-registrations`, OpenSearch |
| `RecordTypeProjector` | `RecordTypeCreated`, `FieldAddedToRecordType`, `FieldDefinitionUpdated`, `FieldReplacedInRecordType`, `FieldRemovedFromRecordType`, `FieldsReorderedInRecordType`, `RecordTypeDeprecated`, `RecordTypeRenamed` | `media-record-types` (latest state), `media-record-type-versions` (full snapshot per version) |
| `MediaProfileProjector` | `MediaProfileCreated`, `MediaProfilePublished`, `MediaProfileDeprecated`, `AssetDefinitionAdded/Updated/Removed`, `RecordTypeAttachedToProfile`, `ReviewPolicySet` | `media-profiles` |
| `MediaChangeRequestProjector` | `MediaChangeRequestCreated`, `ReviewerAssigned/Removed`, `ReviewApproved/Rejected`, `ReviewerWithdrawn`, `MediaChangeRequestApproved/Rejected`, `ReviewCommentAdded/Edited/Deleted` | `media-change-requests` |

**Idempotency:** Each projector checks `LastProcessedAggregateVersion` stored on the read model record before applying updates. Duplicate events are detected and skipped.

---

### Processing Worker

**Owns:** The rendition generation pipeline. Nothing else in the domain.

**Responsibilities:**
- Triggered by `AssetValidationPassed` event on SQS
- Download original from S3
- Resolve owning MediaProfile capabilities from `media-items` read model (if `MediaItemId` is set)
- If MediaProfile **lacks `Processing` capability**: fast-exit after virus scan; dispatch `CompleteAssetProcessing` with empty `Renditions[]` and empty `Metadata` — no renditions generated, no metadata extracted
- If `MediaItemId` is null (standalone/drag-and-drop upload): default to full processing pipeline
- Generate renditions per `RenditionProfile` for the asset's `MediaContentType`
- Upload renditions to `media-renditions` bucket
- Extract metadata (dimensions, duration, EXIF)
- Dispatch `CompleteAssetProcessing` or `FailAssetProcessing` command to Command Handler

**Does NOT:**
- Write to any DynamoDB table directly
- Publish events to SQS directly — all state changes go through Command Handler
- Handle commands or domain logic

**Rendition media-profiles (v1):**

| ContentType | Rendition | Spec |
|---|---|---|
| Image | `thumbnail` | 256×256 crop, WebP |
| Image | `preview` | 1280px wide, WebP |
| Image | `original_optimised` | Lossless compression, original format |
| Video | `thumbnail` | Frame at 00:02, 256×256, WebP |
| Video | `hls_720p` | H.264, 720p, HLS manifest (MediaConvert) |
| Audio | `thumbnail` | Waveform PNG, 512×128 |
| Document | `thumbnail` | Page 1 render, 256×256 PNG |

---

### SecuredSigning Adapter

**Owns:** SecuredSigning API integration. Webhook ingestion.

**Responsibilities:**
- Triggered by `SigningSessionInitiated` event on SQS
- Calls SecuredSigning eSign API to create an envelope with the primary document Asset (downloaded from S3 pre-signed URL) and signer routing
- Dispatches `RecordEnvelopeCreated` command on success
- Receives SecuredSigning webhooks via `POST /integrations/secured-signing/webhook` (API Gateway; no auth token — SecuredSigning HMAC signature validated in handler)
- On `envelope-completed`: downloads signed document, uploads to S3 as new Asset, dispatches `RecordSigningCompleted` + `RecordSignedAsset` commands
- On `envelope-voided`: dispatches `RecordEnvelopeVoided` command

**Does NOT:**
- Write to any DynamoDB table directly
- Publish events to SQS directly — all state changes go through Command Handler

**TenantId resolution (Step 25):**

The Adapter has two entry-points with different `TenantId` sources:

- **SQS path** (`SigningSessionInitiated` trigger): `TenantId` extracted from the SNS message attribute. `SqsExecutionContext(tenantId, ownerId, correlationId)` constructed and pushed to DI scope before any processing. Same pattern as Projectors and Processing Worker.

- **Webhook path** (`POST /integrations/secured-signing/webhook`): This endpoint is unauthenticated — SecuredSigning does not send a JWT. `TenantId` cannot be sourced from `HttpExecutionContext`. Resolution path: after HMAC validation, the handler calls `ISigningSessionLookup.GetByEnvelopeIdAsync(payload.EnvelopeId)` against the `media-signing-sessions` lookup table. This table is written by `RecordEnvelopeCreatedHandler` (projector) as a narrow `EnvelopeId → { TenantId, OwnerId, SigningSessionId }` index. `TenantId` from the lookup is then used to construct an `SqsExecutionContext` for the processing scope. This is the only path in the system where `TenantId` is derived from a table lookup rather than from `IExecutionContext` directly.

> **`media-signing-sessions` lookup table:** Write-once, keyed by `EnvelopeId`. Sole purpose is webhook `TenantId` resolution. Not the primary `DocumentSigningSession` aggregate read model. See `code-requirements/document-signing-session.md` §Step 25.

---

## Integration Contracts with External Contexts

### Identity Context (Upstream)
- **Contract:** JWT bearer token. Claims: `sub` (Actor.Id), `name` (Actor.Name), `roles` (Actor.Roles), `actor_type` (Actor.ActorType), `tenant_id` (TenantId).
- **ACL:** `IdentityAcl` in Ingest API + Query API resolves `IActor` from validated JWT claims. No direct calls to identity service at runtime. No `owner_id` claim — `OwnerId` on resources is stamped from `Actor.Id` at creation.

### Billing / Quotas Context (Upstream)
- **Contract:** Synchronous HTTP call from `UploadAssetHandler` to the Billing quota check endpoint before issuing the pre-signed URL. Signature: `CheckQuotaAsync(OwnerId, sizeBytes) → QuotaCheckResult`.
- **Quota exemption:** Resolved inside `UploadAssetHandler` via `IMediaItemCapabilityReadModel.HasProcessingCapabilityAsync`. Items whose `MediaProfile` lacks the `Processing` capability are quota-exempt — the billing call is bypassed entirely.
- **Failure mode:** If quota service is unavailable, fail open with a configurable flag (default: fail closed in prod).

### Notifications Context (Downstream)
- **Contract:** Media Management emits curated `media.*` integration events (e.g. `media.asset.processing-completed`, `media.asset.processing-failed`, `media.registration.confirmed`, `media.registration.rejected`, `media.collection.created`, `media.mediaitem.published`, `media.mediaitem.archived`) to the `media-integration-events` SNS topic via the per-module `*IntegrationEventPublisher` classes (ADR-005). Notifications owns an SQS queue subscribed to that topic with its own filter policy and handles delivery.
- **Coupling:** Zero. Notifications context owns the subscription, filter policy, DLQ, and delivery. Media Management publishes and forgets.

### Search / Discovery Context (Downstream)
- **Contract:** Media Management emits curated `media.*` integration events (e.g. `media.collection.visibility-changed`, `media.folder.created`, `media.mediaitem.created`, `media.mediaitem.assigned-to-folder`, `media.mediaitem.published`, `media.mediaitem.archived`, `media.asset.attached`) to the `media-integration-events` SNS topic. Search/Discovery owns an SQS queue subscribed to that topic and maintains its own index.
- **Coupling:** Zero. Search/Discovery owns subscription, filter policy, and indexing.

### Billing (Downstream integration consumer)
- **Contract:** Media Management emits `media.asset.processing-completed` (pre-filtered on `Processing` capability inline by `AssetIntegrationEventPublisher`), `media.mediaitem.published`, `media.mediaitem.archived`, `media.collection.created`, `media.collection.archived` to the `media-integration-events` SNS topic. Billing owns an SQS queue subscribed to that topic with a filter policy covering those event types.
- **Coupling:** Zero on the integration path. Billing still handles the synchronous quota check for Ingest API on the upstream path — that contract is unchanged.

### Compliance (Downstream integration consumer)
- **Contract:** Media Management emits `media.registration.confirmed` to the `media-integration-events` SNS topic. Compliance owns an SQS queue subscribed with a filter for that event type.
- **Coupling:** Zero.

### SecuredSigning (External)
- **Contract:** REST API (envelope creation, document download). Webhook callbacks for status changes (`envelope-sent`, `envelope-completed`, `envelope-voided`, `recipient-completed`).
- **Adapter:** `SecuredSigning Adapter` Lambda mediates all calls. No other service calls SecuredSigning directly.
- **Auth:** HMAC signature validation on inbound webhooks. No JWT on webhook path — `TenantId` resolved from `media-signing-sessions` lookup table keyed by `EnvelopeId` (see SecuredSigning Adapter §TenantId resolution above).

---

## Cross-Cutting Concerns

### `IExecutionContext`

`IExecutionContext` is the request-scoped service through which command handlers and domain services access the resolved caller identity. It decouples domain code from HTTP and Lambda infrastructure.

```csharp
interface IExecutionContext {
    string   TenantId       // JWT tenant_id claim — drives PK prefix and storage keys
    IActor   Actor          // Resolved actor (User | System | Guest)
    string?  CausationId
    string?  CorrelationId
}

interface IActor {
    string                      ActorType  // "System" | "User" | "Guest"
    string                      Id         // JWT sub claim — unique actor identifier
    string                      Name       // JWT name claim — full name
    IReadOnlyCollection<string> Roles      // JWT roles claim
}
```

**DI media-registration:**

| Host | Implementation | Scope |
|---|---|---|
| `Media.Api` (FastEndpoints) | `HttpExecutionContext` — resolves `IActor` from validated JWT claims via `IHttpContextAccessor` | Scoped (per HTTP request) |
| SQS Lambda entry-points (Projectors, Processing Worker, SecuredSigning Adapter) | `SqsExecutionContext` — constructed per-message from SQS message attributes (`TenantId`, `ActorId`, `CorrelationId`) | Scoped (per SQS message processing unit) |

**Rules:**
- Command handlers never parse JWT claims directly — they read `IExecutionContext` only.
- `TenantId` sourced from `IExecutionContext` is passed explicitly as the first argument to aggregate factory methods and to `IEventStore.LoadAsync`.
- `IEventStore.SaveAsync` does not read from `IExecutionContext` — it reads `TenantId` from `aggregate.TenantId`.
- For SQS Lambdas, `TenantId` comes from the SNS message attribute envelope, never from the event payload body.
- `OwnerId` on a resource equals `context.Actor.Id` at the time the resource was created. Ownership checks use `context.Actor.Id == aggregate.OwnerId` — there is no `owner_id` JWT claim.

---

## Rules

1. **No cross-table direct writes.** Only the service that owns a table writes to it.
2. **No synchronous inter-service calls within the bounded context** except Ingest API → Command Handler (same Lambda, in-process).
3. **All state changes go through Command Handler.** Processing Worker and SecuredSigning Adapter do not write to DynamoDB.
4. **Read models are expendable.** Any read model table can be rebuilt by replaying the event store. Projectors must tolerate full rebuild.
5. **Events are immutable.** Once persisted to the event store, an event record is never updated or deleted.
6. **`OwnerId` on resources equals `context.Actor.Id` at creation time.** Never trusted from the request body. Never a standalone JWT claim.
7. **`TenantId` sourced from `IExecutionContext` only.** Never derived from `OwnerId`, request body, or aggregate content. All DynamoDB PKs are prefixed `TENANT#{TenantId}#` — no write or read may omit this prefix.
