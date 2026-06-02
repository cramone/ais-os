z# Bounded Context Map & Event Flow Specification — Media Management

_Last updated: 2026-03-11_

---

## Table of Contents

1. [Bounded Context Map](#bounded-context-map)
2. [Bounded Context Registry](#bounded-context-registry)
3. [Internal Services](#internal-services)
4. [Event Flow Specification](#event-flow-specification)
   - [Transport Topology](#transport-topology)
   - [Domain Event Catalog](#domain-event-catalog)
   - [Integration Event Catalog](#integration-event-catalog)
   - [Per-Service Event Contracts](#per-service-event-contracts)
   - [Saga Event Flows](#saga-event-flows)
5. [Queue Topology](#queue-topology)

---

## Bounded Context Map

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  UPSTREAM CONTEXTS                                                              │
│                                                                                 │
│  ┌───────────────────────┐      ┌───────────────────────────────────────────┐   │
│  │  Identity             │      │  Billing / Quotas                         │   │
│  │                       │      │                                           │   │
│  │  JWT issuance         │      │  Storage quota enforcement                │   │
│  │  OwnerId resolution   │      │  Usage metering                           │   │
│  │                       │      │  Quota-exempt: no-Processing media-items        │   │
│  └───────────┬───────────┘      └──────────────────┬────────────────────────┘   │
│              │ JWT (ACL)                            │ Sync HTTP (quota check)    │
└──────────────┼──────────────────────────────────────┼────────────────────────────┘
               │                                      │
               ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  MEDIA MANAGEMENT  (this bounded context)                                        │
│                                                                                  │
│  Core Domain: Media Asset Lifecycle                                              │
│  ─────────────────────────────────────────────────────────────────────────────   │
│                                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  ┌──────────────────────────┐ │
│  │ Ingest   │  │ Query    │  │ Command Handler  │  │ Projectors               │ │
│  │ API      │  │ API      │  │ (write side)     │  │ (read model builders)    │ │
│  └──────────┘  └──────────┘  └─────────────────┘  └──────────────────────────┘ │
│                                                                                  │
│  ┌──────────────────────┐  ┌─────────────────────┐  ┌────────────────────────┐  │
│  │ Processing Worker    │  │ SagaOrchestrator    │  │ SecuredSigning Adapter │  │
│  └──────────────────────┘  └─────────────────────┘  └────────────────────────┘  │
│                                                                                  │
│  Aggregates: RecordType · MediaProfile · Collection · Folder                     │
│              MediaItem · Asset · Registration · MediaChangeRequest               │
│              DocumentSigningSession                                              │
│                                                                                  │
└───────────────────────────┬──────────────────────────────────────────────────────┘
                            │ Integration events (media-integration-events SNS → BC-owned SQS)
          ┌─────────────────┼──────────────────┬──────────────────┬──────────────────┐
          ▼                 ▼                  ▼                  ▼                  ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐
│  Notifications  │  │ Search/Discovery │  │  Billing    │  │ Compliance  │  │  SecuredSigning     │
│  (downstream)   │  │ (downstream)     │  │ (downstream)│  │ (downstream)│  │  (external service) │
│                 │  │                  │  │             │  │             │  │                     │
│  Delivery of    │  │ Public catalogue │  │ Usage       │  │ Registration│  │  Envelope API       │
│  alerts to      │  │ indexing and     │  │ metering    │  │ reporting   │  │  Webhook callbacks  │
│  owners/users   │  │ discovery feeds  │  │             │  │             │  │                     │
└─────────────────┘  └──────────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘
```

### Context Relationship Types

| Relationship | Type | Pattern |
|---|---|---|
| Identity → Media Management | Upstream / ACL | JWT validated at API Gateway; `IdentityAcl` resolves `IActor` from JWT claims (`sub`, `name`, `roles`, `actor_type`, `tenant_id`). No runtime calls to Identity. |
| Billing → Media Management | Upstream / ACL | Synchronous HTTP call from Ingest API before issuing upload URL. `BillingAcl` translates quota check response. Items whose MediaProfile lacks the `Processing` capability bypass the quota check entirely. |
| Media Management → Notifications | Downstream / Published Language | Integration events published to the `media-integration-events` SNS topic. Notifications owns an SQS queue subscribed to that topic with its own filter policy; Media Management publishes and forgets. |
| Media Management → Search/Discovery | Downstream / Published Language | Integration events published to the `media-integration-events` SNS topic. Search/Discovery owns an SQS queue subscribed to that topic and maintains its own index from the integration event stream. |
| Media Management → Billing (integration consumer) | Downstream / Published Language | Integration events published to the `media-integration-events` SNS topic. Billing owns an SQS queue subscribed with a filter for the integration events relevant to metering. The `Processing`-capability filter for `media.asset.processing-completed` is applied inline by the `AssetIntegrationEventPublisher` in the AssetManagement module before publication — Billing performs no filtering of its own. |
| Media Management → Compliance (integration consumer) | Downstream / Published Language | Integration events published to the `media-integration-events` SNS topic. Compliance owns an SQS queue subscribed with a filter for `media.registration.confirmed`. |
| Media Management → SecuredSigning | External / Anticorruption Layer | `SecuredSigning Adapter` Lambda mediates all API calls and webhook ingestion. No other service calls SecuredSigning directly. |

---

## Bounded Context Registry

### Media Management (this context)
- **Role:** Core domain. Owns the full lifecycle of media media-assets — ingestion, processing, cataloguing, media-registration, and retrieval.
- **Owns:** All aggregates listed in `domain-model.md`. All read models in `media-*` DynamoDB tables. All S3 buckets (`media-source`, `media-renditions`, `media-documents`).
- **Does not own:** User identity. Storage billing. Downstream search indexes. SecuredSigning envelopes (owns only the `DocumentSigningSession` aggregate that models the lifecycle).

### Identity (upstream, external)
- **Role:** Issues JWT tokens. Claims carried: `sub` (Actor.Id), `name` (Actor.Name), `roles` (Actor.Roles), `actor_type` (Actor.ActorType), `tenant_id` (TenantId).
- **Integration point:** JWT validated at API Gateway level. `IdentityAcl` in Ingest and Query APIs resolves `IActor` from JWT claims. No runtime calls beyond token validation.
- **Reserved constant:** `OwnerId = "owner_system"` is a platform-level sentinel for `RecordType` and `MediaProfile` configuration aggregates. Not issued by Identity; no actor will have `Actor.Id = "owner_system"`.

### Billing / Quotas (upstream, external)
- **Role:** Tracks storage usage per owner. Enforces upload quotas. Receives usage events.
- **Integration point:** Synchronous HTTP check from Ingest API before pre-signed URL issuance. Receives `media.asset.processing-completed` filtered to media-items whose MediaProfile has the `Processing` capability only — media-items lacking `Processing` are quota-exempt and the event is suppressed inline by `AssetIntegrationEventPublisher` before publication to the `media-integration-events` topic.
- **Failure mode:** Configurable — default fail-closed in production.

### Notifications (downstream, external)
- **Role:** Delivers alerts to owners and users on significant events.
- **Integration point:** Owns an SQS queue subscribed to the `media-integration-events` SNS topic with a filter policy for the integration events it needs. Zero coupling — Media Management publishes, Notifications owns subscription, DLQ, and delivery.

### Search / Discovery (downstream, external)
- **Role:** Public discovery layer. May maintain its own search index from Media Management events.
- **Integration point:** Owns an SQS queue subscribed to the `media-integration-events` SNS topic. Consumes `media.collection.visibility-changed`, `media.mediaitem.published`, `media.mediaitem.archived`, `media.folder.*`, `media.mediaitem.created`, `media.mediaitem.assigned-to-folder`, `media.asset.attached`.

### Billing (downstream integration consumer)
- **Role:** Usage metering driven off integration events (in addition to upstream quota enforcement).
- **Integration point:** Owns an SQS queue subscribed to `media-integration-events` with a filter for `media.asset.processing-completed`, `media.mediaitem.published`, `media.mediaitem.archived`, `media.collection.created`, `media.collection.archived`. The `Processing`-capability filter is applied inline by the `AssetIntegrationEventPublisher` in Media Management — Billing does not filter on its own.

### Compliance (downstream integration consumer)
- **Role:** Regulatory reporting for media-registration events.
- **Integration point:** Owns an SQS queue subscribed to `media-integration-events` with a filter for `media.registration.confirmed`.

### SecuredSigning (external service)
- **Role:** Provides digital envelope signing (eSign) via REST API and webhooks.
- **Integration point:** `SecuredSigning Adapter` Lambda is the sole integration point. Handles envelope creation, signer routing, and webhook ingestion. All state changes are written back to Command Handler as commands — SecuredSigning never writes to domain state directly.

---

## Internal Services

### Overview

All services within the Media Management bounded context communicate via the `media-domain-events` SNS topic and its subscriber SQS queues. Synchronous command dispatch (Ingest API → Command Handler) is in-process via MediatR.

| Service | Runtime | Owns | Role |
|---|---|---|---|
| Ingest API | Lambda / ECS (ASP.NET, FastEndpoints) | Upload flow, pre-signed URL issuance | Accepts write requests; dispatches commands |
| Query API | Lambda / ECS (ASP.NET, FastEndpoints) | Read model queries | Serves all read traffic |
| Command Handler | Lambda (MediatR) | Event store; aggregate lifecycle | Processes all commands; persists events; publishes to both `media-domain-events` and (via per-module `*IntegrationEventPublisher` handlers) `media-integration-events` |
| Projectors | Lambda (SQS-triggered) | Read model tables | Maintain DynamoDB and OpenSearch read models |
| Processing Worker | Lambda (SQS-triggered) | Rendition generation pipeline | Generates renditions; extracts metadata; dispatches result commands |
| SagaOrchestrator | Lambda (SQS-triggered) | Saga state (`media-sagas` table) | Manages cross-aggregate processes; dispatches compensating commands |
| SagaTimeoutScanner | Lambda (CloudWatch scheduled) | — | Scans for timed-out saga instances; dispatches timeout compensation |
| SecuredSigning Adapter | Lambda (SQS-triggered + API Gateway webhook) | Signing envelope mediation | Calls SecuredSigning API; ingests webhooks; dispatches result commands |
| Integration Event Consumers | Lambda (SQS-triggered by `media-cross-module-events`) | Intra-BC consumers that react to other modules' integration events (e.g. AssetManagement maintaining capability index from Catalog's `MediaItemCreatedMessage`) | Consumes integration events from the intra-BC fan-in queue and dispatches follow-up commands or writes module-local read models. See ADR-005. |

**Note on integration event publishing:** There is no separate Integration Event Publisher Lambda. Each module owns an `*IntegrationEventPublisher` class in its WriteModel that implements `IDomainEventHandler<T>` for its published events, translates them inline into `media.*` integration events, and publishes to `media-integration-events` via `IMessageBus`. Publishing runs in-process with the Command Handler. See ADR-005.

### Command Handler — Aggregates Owned

| Aggregate | Stream prefix | New command |
|---|---|---|
| `RecordType` | `recordtype_` | `CreateRecordType` |
| `MediaProfile` | `mediaprofile_` | `CreateMediaProfile` |
| `Collection` | `media-collection_` | `CreateCollection` |
| `Folder` | `media-folder_` | `CreateFolder` |
| `MediaItem` | `mediaitem_` | `CreateMediaItem` |
| `Asset` | `asset_` | `UploadAsset` |
| `Registration` | `media-registration_` | `InitiateRegistration` |
| `MediaChangeRequest` | `mediachangerequest_` | `CreateMediaChangeRequest` _(system only)_ |
| `DocumentSigningSession` | `signingsession_` | `InitiateSigningSession` |

### Projectors — Read Models Owned

| Projector | Read models owned |
|---|---|
| `AssetProjector` | `media-assets`, `media-asset-detail` |
| `CollectionProjector` | `media-collections`, `media-collection-detail` |
| `FolderProjector` | `media-folders`, `media-folder-detail` |
| `MediaItemProjector` | `media-items` (+ all GSIs), `media-item-detail`, OpenSearch `media-items` |
| `MediaItemVersionProjector` | `media-item-versions` |
| `RegistrationProjector` | `media-registrations`, OpenSearch `media-registrations` |
| `RecordTypeProjector` | `media-record-types`, `media-record-type-versions` |
| `MediaProfileProjector` | `media-profiles` |
| `MediaChangeRequestProjector` | `media-change-requests` |

---

## Event Flow Specification

### Transport Topology

Events flow in two distinct layers:

**Layer 1 — Domain events (write-side internal):**
Command Handler writes domain events to the `media-events` DynamoDB table (append-only, per-aggregate partition). These events are the source of truth for aggregate state. They are never directly consumed by anything outside Command Handler's own aggregate rehydration.

**Layer 2 — Domain event bus (internal):**
After a successful write to the event store, Command Handler publishes the same event payload to the `media-domain-events` SNS topic. Internal Media Management consumers (Projectors, Processing Worker, SagaOrchestrator, SecuredSigning Adapter) receive events via their dedicated SQS queue subscriptions. External bounded contexts do **not** subscribe to `media-domain-events`.

**Layer 3 — Integration event bus (boundary):**
Translation from domain event to integration event happens inline in the Command Handler, via per-module `*IntegrationEventPublisher` classes registered as `IDomainEventHandler<T>` (see ADR-005). Each publisher constructs the published-language `media.*` envelope, applies any catalog-declared filter (e.g. `Processing` capability gate on `media.asset.processing-completed`), and publishes directly to the `media-integration-events` SNS topic via `IMessageBus`. External bounded contexts (Notifications, Search/Discovery, Billing, Compliance) each own an SQS queue subscribed to `media-integration-events` with their own filter policy, DLQ, and retry configuration. Intra-BC consumers (e.g. AssetManagement reacting to Catalog's `MediaItemCreatedMessage`) subscribe via the MM-owned `media-cross-module-events` queue.

```
Client Request
      │
      ▼
Ingest API ──(MediatR)──▶ Command Handler
                                │
                       ①  PutItem (conditional)
                                │
                                ▼
                         media-events (DynamoDB)
                         AggregateId | AggregateVersion | EventType | Payload | SchemaVersion
                                │
                       ②  Dispatch domain event handlers (in-process)
                                │
                  ┌─────────────┼──────────────────────────┐
                  ▼                                        ▼
           Projector handlers             Module *IntegrationEventPublisher
           (local read-model                    │
            writes inline)                      │  build media.* envelope
                                                │  apply catalog filters
                                                │
                                                ▼
                                      SNS: media-integration-events

                       ③  Publish domain event (outbound)
                                │
                                ▼
                      SNS: media-domain-events
                                │
              ┌─────────────┬───┴─────────┬─────────────┐
              ▼             ▼             ▼             ▼
     SQS: media-projector  media-processing  media-sagas  media-signing
              │             │             │             │
              ▼             ▼             ▼             ▼
     Cross-aggregate   Processing    SagaOrchestrator  SecuredSigning
     projectors        Worker                          Adapter
              │             │             │             │
              │  Dispatch commands back to Command Handler (cycle)
              └─────────────┴─────────────┘

  SNS: media-integration-events
              │
  ┌───────────┼───────────────┬───────────────┬───────────────┐
  ▼           ▼               ▼               ▼               ▼
media-cross-   Notifications  Search/         Billing        Compliance
module-events  -owned SQS     Discovery-      -owned SQS     -owned SQS
(intra-BC                     owned SQS
 fan-in)
  │
  ▼
Integration Event Consumers
(MM-internal cross-module)
```

**Key invariants:**
- Step ① and ② are not atomic. This is the accepted dual-write risk (ADR-002). Full event store replay is always available for projection rebuilds.
- All SQS queues have a DLQ (max 3 retries). CloudWatch alarms on DLQ depth for each queue.
- SagaOrchestrator is idempotent: media-sagas in `Complete` or `Failed` status discard duplicate events.
- Projectors are idempotent: each checks `LastProcessedAggregateVersion` before applying.

---

### Domain Event Catalog

All events persisted to `media-events`. Grouped by aggregate.

#### RecordType

| Event | Key Payload Fields | Version Increment |
|---|---|---|
| `RecordTypeCreated` | `RecordTypeId`, `OwnerId`, `Name`, `Fields[]` | No |
| `FieldAddedToRecordType` | `RecordTypeId`, `FieldDefinition`, `Version` | Yes |
| `FieldDefinitionUpdated` | `RecordTypeId`, `FieldName`, changed fields, `Version` | Yes |
| `FieldReplacedInRecordType` | `RecordTypeId`, `OldField`, `NewField`, `MigrationNote`, `Version` | Yes |
| `FieldRemovedFromRecordType` | `RecordTypeId`, `FieldName`, `Version` | Yes |
| `FieldsReorderedInRecordType` | `RecordTypeId`, `FieldOrders[]`, `Version` | Yes |
| `RecordTypeDeprecated` | `RecordTypeId`, `DeprecatedAt` | No |
| `RecordTypeRenamed` | `RecordTypeId`, `OldName`, `NewName` | No |

#### MediaProfile

| Event | Key Payload Fields | Version Increment |
|---|---|---|
| `MediaProfileCreated` | `MediaProfileId`, `OwnerId`, `Name`, `CreatedAt` | No |
| `AssetDefinitionAdded` | `MediaProfileId`, `AssetDefinition` (full), `Version` | Yes |
| `AssetDefinitionUpdated` | `MediaProfileId`, `RoleName`, changed fields, `Version` | Yes |
| `AssetDefinitionRemoved` | `MediaProfileId`, `RoleName`, `Version` | Yes |
| `AssetDefinitionsReordered` | `MediaProfileId`, `[{RoleName, DisplayOrder}]`, `Version` | Yes |
| `AssetDefinitionDefaultSet` | `MediaProfileId`, `RoleName`, `DefaultAssetId?`, `Version` | Yes |
| `RecordTypeAttachedToProfile` | `MediaProfileId`, `RecordTypeId`, `Version` | Yes |
| `RecordTypeVersionPinnedOnProfile` | `MediaProfileId`, `RecordTypeId`, `OldVersion`, `NewVersion` | Yes |
| `RecordTypeDetachedFromProfile` | `MediaProfileId`, `RecordTypeId` | Yes |
| `ReviewPolicySet` | `MediaProfileId`, `OldPolicy`, `NewPolicy` | No |
| `MediaProfilePublished` | `MediaProfileId`, `PublishedAt` | No |
| `MediaProfileDeprecated` | `MediaProfileId`, `DeprecatedAt` | No |

#### Collection

| Event | Key Payload Fields |
|---|---|
| `CollectionCreated` | `CollectionId`, `OwnerId`, `Name`, `Visibility` |
| `CollectionRenamed` | `CollectionId`, `OldName`, `NewName` |
| `CollectionTagged` | `CollectionId`, `Tags[]` |
| `CollectionVisibilityChanged` | `CollectionId`, `OldVisibility`, `NewVisibility` |
| `CollectionDefaultProfileSet` | `CollectionId`, `MediaProfileId` |
| `RootFolderAddedToCollection` | `CollectionId`, `FolderId` |
| `RootFolderRemovedFromCollection` | `CollectionId`, `FolderId` |
| `CollectionArchived` | `CollectionId`, `ArchivedAt` |

#### Folder

| Event | Key Payload Fields |
|---|---|
| `FolderCreated` | `FolderId`, `CollectionId`, `ParentFolderId?`, `Name`, `OwnerId` |
| `FolderRenamed` | `FolderId`, `OldName`, `NewName` |
| `FolderMoved` | `FolderId`, `OldParentFolderId?`, `NewParentFolderId?` |
| `FolderArchived` | `FolderId`, `ArchivedAt` |

#### MediaItem

| Event | Key Payload Fields | Status Transition |
|---|---|---|
| `MediaItemCreated` | `MediaItemId`, `FolderId?`, `CollectionId?`, `OwnerId`, `MediaProfileId`, `Title` | → Draft |
| `MediaItemAssignedToFolder` | `MediaItemId`, `FolderId`, `CollectionId` | — |
| `MediaItemTitleUpdated` | `MediaItemId`, `OldTitle`, `NewTitle` | — |
| `MediaItemMoved` | `MediaItemId`, `OldFolderId`, `NewFolderId`, `OldCollectionId`, `NewCollectionId` | — |
| `MediaItemRevertedToDraft` | `MediaItemId`, `RevertedAt`, `Trigger` | Published → Draft |
| `MediaItemMetadataFieldSet` | `MediaItemId`, `FieldName`, `Value`, `RecordTypeId`, `RecordTypeVersion` | — |
| `MediaItemMetadataBatchSet` | `MediaItemId`, `Fields[]` | — |
| `AssetAssignedToRole` | `MediaItemId`, `AssetId`, `RoleName` | — |
| `AssetUnassignedFromRole` | `MediaItemId`, `AssetId`, `RoleName` | — |
| `MediaItemSubmittedForReview` | `MediaItemId`, `SubmittedAt` | Draft → PendingApproval |
| `MediaItemApproved` | `MediaItemId`, `ApprovedAt`, `NewVersionNumber`, `ApprovedMetadataSnapshot` | PendingApproval → Published (or Draft → Published on immediate publish) |
| `MediaItemRejected` | `MediaItemId`, `Reason`, `RejectedAt` | PendingApproval → Draft |
| `MediaItemWithdrawn` | `MediaItemId`, `WithdrawnAt` | Published → Withdrawn |
| `MediaItemArchived` | `MediaItemId`, `ArchivedAt` | → Archived |
| `MediaItemTagged` | `MediaItemId`, `Tags[]` | — |
| `RegistrationRefAdded` | `MediaItemId`, `RegistrationId` | — |
| `MediaItemCheckedOut` | `MediaItemId`, `CheckedOutBy`, `CheckedOutAt` | — |
| `MediaItemCheckedIn` | `MediaItemId`, `CheckedInBy`, `CheckedInAt` | — |
| `MediaItemCheckoutAbandoned` | `MediaItemId`, `AbandonedBy`, `AbandonedAt` | — |
| `MediaItemCheckoutForceReleased` | `MediaItemId`, `ReleasedBy`, `Reason`, `ReleasedAt` | — |
| `MediaItemSigningSessionLinked` | `MediaItemId`, `SigningSessionId` | — |
| `MediaItemSigningSessionUnlinked` | `MediaItemId`, `SigningSessionId` | — |
| `MediaChangeRequestLinked` | `MediaItemId`, `MediaChangeRequestId` | — |
| `MediaChangeRequestUnlinked` | `MediaItemId`, `MediaChangeRequestId` | — |

#### Asset

| Event | Key Payload Fields | Status Transition |
|---|---|---|
| `AssetUploaded` | `AssetId`, `MediaItemId?`, `OwnerId`, `StorageKey`, `ContentType`, `OriginalFileName` | → Pending |
| `AssetUploadConfirmed` | `AssetId`, `ConfirmedAt` | Pending → Validating |
| `AssetValidationPassed` | `AssetId`, `MediaItemId?`, `JobId`, `StorageKey`, `ContentType`, `PassedAt` | Validating → (Processing or Active) |
| `AssetValidationFailed` | `AssetId`, `Reason` | Validating → ValidationFailed |
| `AssetProcessingStarted` | `AssetId` | → Processing |
| `AssetProcessingCompleted` | `AssetId`, `Renditions[]`, `Metadata` | Processing → Active |
| `AssetProcessingFailed` | `AssetId`, `Reason` | Processing → ProcessingFailed |
| `AssetTagged` | `AssetId`, `Tags[]` | — |
| `AssetArchived` | `AssetId`, `ArchivedAt` | Active → Archived |
| `AssetDeleted` | `AssetId`, `DeletedAt` | → Deleted |
| `AssetAttachedToMediaItem` | `AssetId`, `MediaItemId`, `RoleName?` | — |
| `AssetDetachedFromMediaItem` | `AssetId`, `MediaItemId`, `DetachedAt` | — |

#### Registration

| Event | Key Payload Fields | Status Transition |
|---|---|---|
| `RegistrationInitiated` | `RegistrationId`, `MediaItemId`, `OwnerId`, `RegistrationType`, `RegistrationAuthority` | → Initiated |
| `RegistrationSubmitted` | `RegistrationId`, `SubmittedAt` | Initiated → Submitted |
| `RegistrationConfirmed` | `RegistrationId`, `Reference`, `ConfirmedAt` | → Confirmed |
| `RegistrationRejected` | `RegistrationId`, `Reason`, `RejectedAt` | → Rejected |
| `RegistrationResubmitted` | `RegistrationId`, `ResubmittedAt` | Rejected → Resubmitted |
| `RegistrationCancelled` | `RegistrationId`, `CancelledAt` | → Cancelled |
| `RegistrationDocumentAttached` | `RegistrationId`, `MediaItemId`, `DocumentType` | — |
| `RegistrationExpiryRecorded` | `RegistrationId`, `ExpiresAt` | — |

#### MediaChangeRequest

| Event | Key Payload Fields | Status Transition |
|---|---|---|
| `MediaChangeRequestCreated` | `MediaChangeRequestId`, `MediaItemId`, `OwnerId`, `CreatedAt` | → Open |
| `ReviewerAssigned` | `MediaChangeRequestId`, `ReviewerId`, `AssignedAt` | — |
| `ReviewerRemoved` | `MediaChangeRequestId`, `ReviewerId` | — |
| `ReviewApproved` | `MediaChangeRequestId`, `ReviewerId`, `DecisionComment?`, `ApprovedAt` | — |
| `ReviewRejected` | `MediaChangeRequestId`, `ReviewerId`, `Reason`, `RejectedAt` | — |
| `ReviewerWithdrawn` | `MediaChangeRequestId`, `ReviewerId`, `DecisionComment?`, `WithdrawnAt` | — |
| `MediaChangeRequestApproved` | `MediaChangeRequestId`, `MediaItemId`, `ApprovedAt` | Open → Approved |
| `MediaChangeRequestRejected` | `MediaChangeRequestId`, `MediaItemId`, `RejectedBy`, `RejectedAt` | Open → Rejected |
| `ReviewCommentAdded` | `MediaChangeRequestId`, `CommentId`, `AuthorId`, `Body`, `ParentCommentId?` | — |
| `ReviewCommentEdited` | `MediaChangeRequestId`, `CommentId`, `OldBody`, `NewBody`, `EditedAt` | — |
| `ReviewCommentDeleted` | `MediaChangeRequestId`, `CommentId`, `DeletedAt` | — |

#### DocumentSigningSession

| Event | Key Payload Fields | Status Transition |
|---|---|---|
| `SigningSessionInitiated` | `SigningSessionId`, `MediaItemId`, `OwnerId`, `InitiatedBy`, `Signers[]` | → Initiated |
| `SigningEnvelopeCreated` | `SigningSessionId`, `EnvelopeId` | Initiated → EnvelopeCreated |
| `SigningEnvelopeSent` | `SigningSessionId`, `EnvelopeId` | EnvelopeCreated → Sent |
| `SignerCompleted` | `SigningSessionId`, `SignerId`, `SignedAt` | — |
| `SigningCompleted` | `SigningSessionId`, `CompletedAt` | Sent → Completed |
| `SignedAssetRecorded` | `SigningSessionId`, `SignedAssetId` | — |
| `SigningEnvelopeVoided` | `SigningSessionId`, `VoidReason`, `VoidedAt` | → Voided |
| `SigningSessionCancelled` | `SigningSessionId`, `CancelledAt` | → Cancelled |

---

### Integration Event Catalog

Integration events cross a bounded context boundary. They are a curated subset of domain events, translated inline by each module's `*IntegrationEventPublisher` class (running as an `IDomainEventHandler<T>` in the Command Handler process) and published directly to the `media-integration-events` SNS topic. The envelope is the same JSON structure as internal events; the `eventType` uses the dot-separated cross-context naming convention. External BCs subscribe their own SQS queues to `media-integration-events` with filter policies on the `EventType` SNS message attribute. Intra-BC consumers share the same topic via the MM-owned `media-cross-module-events` queue. See ADR-005.

#### Envelope format

```json
{
  "eventId":           "018e4c7a-3f10-7b2a-8c4d-1a2b3c4d5e6f",
  "eventType":         "media.mediaitem.published",
  "occurredAt":        "2026-03-11T12:00:00Z",
  "schemaVersion":     1,
  "sourceAggregateId": "mediaitem_018e4c7a-3f10-7b2a-8c4d-1a2b3c4d5e6f",
  "ownerId":           "owner_018e4c7b-1a20-7c3d-9e4f-2b3c4d5e6f70",
  "payload":           { }
}
```

#### Published integration events

| Integration Event | Source Domain Event | Consumers | Payload Summary |
|---|---|---|---|
| `media.collection.created` | `CollectionCreated` | Notifications, Billing | `collectionId`, `ownerId`, `name`, `visibility` |
| `media.collection.visibility-changed` | `CollectionVisibilityChanged` | Search/Discovery | `collectionId`, `oldVisibility`, `newVisibility` |
| `media.folder.created` | `FolderCreated` | Search/Discovery | `folderId`, `collectionId`, `parentFolderId?`, `name` |
| `media.mediaitem.created` | `MediaItemCreated` | Search/Discovery | `mediaItemId`, `collectionId?`, `folderId?`, `ownerId`, `mediaProfileId` |
| `media.mediaitem.published` | `MediaItemApproved` | Notifications, Search/Discovery, Billing | `mediaItemId`, `ownerId`, `newVersionNumber`, `publishedAt` |
| `media.mediaitem.archived` | `MediaItemArchived` | Billing, Search/Discovery | `mediaItemId`, `ownerId`, `archivedAt` |
| `media.asset.processing-completed` | `AssetProcessingCompleted` | Notifications, Billing _(filtered: `Processing` capability only)_ | `assetId`, `mediaItemId?`, `ownerId`, `contentType`, `sizeBytes` |
| `media.asset.processing-failed` | `AssetProcessingFailed` | Notifications | `assetId`, `mediaItemId?`, `ownerId`, `reason` |
| `media.registration.confirmed` | `RegistrationConfirmed` | Notifications, Compliance reporting | `registrationId`, `mediaItemId`, `ownerId`, `reference`, `confirmedAt` |
| `media.registration.rejected` | `RegistrationRejected` | Notifications | `registrationId`, `mediaItemId`, `ownerId`, `reason` |

**Filtering note:** Billing receives `media.asset.processing-completed` only when the owning MediaItem's MediaProfile has the `Processing` capability. Items whose MediaProfile lacks `Processing` are quota-exempt; the integration event is suppressed at the source by `AssetIntegrationEventPublisher`, which resolves capabilities from the `media-items` read model before publishing. Billing applies no filtering of its own.

---

### Intra-BC Integration Event Consumers

Media Management is a **consumer** of its own integration events via the `media-cross-module-events` SQS queue (MM-owned). Every consumer listed here reacts to an integration event published by a different module in this bounded context — never to domain events directly. The consumer class is the only code that knows it is running inside an intra-BC transport hop; the rest of the module code is unchanged.

The queue's SNS filter policy must allow every `EventType` in the **Subscribed Message** column below. Register consumers in `Media.IntegrationEventConsumers.Lambda/ConsumerRegistrations.cs` and add the corresponding `EventType` to the filter policy at the same time — see `DEPLOYMENT.md` in that host.

| Consumer | Host / Module | Subscribed Message(s) | Downstream action |
|---|---|---|---|
| `MediaItemCapabilityIndexConsumer` | `Media.IntegrationEventConsumers.Lambda` (AssetManagement) | `MediaItemCreatedMessage`, `MediaItemArchivedMessage` | Upserts / flips `IsArchived` on the `MediaItemCapabilityIndex` reference model consulted synchronously by AssetManagement upload and validation command handlers. |
| `RegistrationInitiatedConsumer` | `Catalog.WriteModel` module | `RegistrationInitiatedMessage` | Dispatches `AddRegistrationRefCommand` to record the media-registration reference on the corresponding MediaItem aggregate. |
| `CollectionArchiveFanOutJob` | `Catalog.WriteModel` module | `CollectionArchivedMessage` | Drives `ICollectionArchiveFanOutWorker` to archive every media-folder and media media-item in the media-collection's subtree (BFS, leaf-first on media-folders). |
| `MediaItemSubmittedForReviewConsumer` | `ChangeRequests.WriteModel` module | `MediaItemSubmittedForReviewMessage` | When the message carries a `ChangeRequestId` (`ReviewPolicy = RequiredForPublish`), dispatches `CreateMediaChangeRequestCommand`. No-op otherwise. |

**Why integration events instead of domain events?** Consumers live in a different module than the publishing aggregate. Domain events are an internal concern of the owning module — anything that crosses a module boundary rides the integration-event channel so the module contract (the `IntegrationEvent` record shape) is the only coupling surface. See ADR-005.

---

### Per-Service Event Contracts

#### Ingest API

| Direction | Event / Command | Notes |
|---|---|---|
| **Dispatches** | `UploadAsset` | On `POST /media-assets/upload-url` |
| **Dispatches** | `ConfirmAssetUpload` | On S3 `ObjectCreated` SQS notification |
| **Dispatches** | `CreateMediaItem`, `AssignMediaItemToFolder`, `MoveMediaItem` | MediaItem write endpoints |
| **Dispatches** | `CreateCollection`, `RenameCollection`, `ArchiveCollection` | Collection write endpoints |
| **Dispatches** | `CreateFolder`, `RenameFolder`, `MoveFolder`, `ArchiveFolder` | Folder write endpoints |
| **Dispatches** | `AssignAssetToRole`, `UnassignAssetFromRole` | Role assignment endpoints |
| **Dispatches** | `SetMetadataField`, `SetMetadataBatch` | Metadata write endpoints |
| **Dispatches** | `PublishMediaItem`, `ApproveReview`, `RejectReview` | Review lifecycle endpoints |
| **Dispatches** | `CheckOutMediaItem`, `CheckInMediaItem`, `AbandonCheckout`, `ForceReleaseCheckout` | Checkout endpoints |
| **Dispatches** | `InitiateSigningSession`, `CancelSigningSession` | Signing initiation endpoint |
| **Dispatches** | `InitiateRegistration`, `SubmitRegistration`, `ConfirmRegistration` | Registration write endpoints |
| **Dispatches** | `CreateRecordType`, `CreateMediaProfile`, `PublishMediaProfile` | Config aggregate write endpoints |
| **Consumes (SQS)** | S3 `ObjectCreated` notification | Triggers `ConfirmAssetUpload` |

#### Command Handler

| Direction | Event / Command | Notes |
|---|---|---|
| **Receives** | All commands listed under Ingest API | Via MediatR (in-process) |
| **Receives** | `CreateMediaChangeRequest`, `LinkMediaChangeRequest` | From SagaOrchestrator (system-only) |
| **Receives** | `ApproveMediaItem`, `RejectMediaItem` | From SagaOrchestrator (saga resolution) |
| **Receives** | `FailAssetProcessing` | From SagaOrchestrator (timeout) or Processing Worker |
| **Receives** | `LinkSigningSession`, `UnlinkSigningSession`, `ForceReleaseCheckout` | From SagaOrchestrator |
| **Receives** | `RecordEnvelopeCreated`, `RecordEnvelopeSent`, `RecordSignerCompleted`, `RecordSigningCompleted`, `RecordSignedAsset`, `RecordEnvelopeVoided` | From SecuredSigning Adapter |
| **Receives** | `StartAssetProcessing`, `CompleteAssetProcessing`, `FailAssetProcessing` | From Processing Worker |
| **Publishes (SNS)** | All domain events listed in Domain Event Catalog | After each successful `PutItem` to `media-events` |

#### Processing Worker

| Direction | Event / Command | Notes |
|---|---|---|
| **Consumes (SQS)** | `AssetValidationPassed` | Trigger for processing pipeline |
| **Dispatches** | `StartAssetProcessing(AssetId)` | Before beginning work |
| **Dispatches** | `CompleteAssetProcessing(AssetId, Renditions[], Metadata)` | On success |
| **Dispatches** | `FailAssetProcessing(AssetId, Reason)` | On worker-detected failure |
| **Reads (DynamoDB)** | `media-items` read model | To resolve MediaProfile capabilities when `MediaItemId` is set |
| **Writes (S3)** | `media-renditions` bucket | Rendition outputs |

**Pipeline branching:**
- `MediaItemId` present + MediaProfile **lacks `Processing` capability**: fast-exit after virus scan; dispatches `CompleteAssetProcessing` with empty `Renditions[]` and empty `Metadata`.
- `MediaItemId` null (standalone upload): full processing pipeline (renditions generated, metadata extracted).
- `MediaItemId` present + MediaProfile **has `Processing` capability**: full processing pipeline.

#### SagaOrchestrator

| Direction | Event / Command | Saga | Notes |
|---|---|---|---|
| **Consumes (SQS)** | `AssetValidationPassed` | AssetIngestion | Creates saga instance |
| **Consumes (SQS)** | `AssetProcessingCompleted` | AssetIngestion | Closes saga (happy) |
| **Consumes (SQS)** | `AssetProcessingFailed` | AssetIngestion | Closes saga (worker fail) |
| **Consumes (SQS)** | `MediaItemSubmittedForReview` | MediaItemReview | Creates saga (if `ReviewPolicy=RequiredForPublish`) |
| **Consumes (SQS)** | `MediaChangeRequestCreated` | MediaItemReview | Dispatches `LinkMediaChangeRequest` |
| **Consumes (SQS)** | `MediaChangeRequestLinked` | MediaItemReview | Transitions to `AwaitingReview` |
| **Consumes (SQS)** | `MediaChangeRequestApproved` | MediaItemReview | Dispatches `ApproveMediaItem` |
| **Consumes (SQS)** | `MediaChangeRequestRejected` | MediaItemReview | Dispatches `RejectMediaItem` |
| **Consumes (SQS)** | `MediaItemApproved` | MediaItemReview | Closes saga (happy) |
| **Consumes (SQS)** | `MediaItemRejected` | MediaItemReview | Closes saga |
| **Consumes (SQS)** | `MediaItemWithdrawn`, `MediaItemArchived` | MediaItemReview | Closes saga (no-op) |
| **Consumes (SQS)** | `SigningSessionInitiated` | DocumentSigning | Creates saga |
| **Consumes (SQS)** | `SigningEnvelopeCreated` | DocumentSigning | Dispatches `LinkSigningSession` |
| **Consumes (SQS)** | `MediaItemSigningSessionLinked` | DocumentSigning | Sets `LinkWritten=true`; transitions to `AwaitingSigners` |
| **Consumes (SQS)** | `SigningCompleted` | DocumentSigning | Transitions to `RecordingSignedAsset` |
| **Consumes (SQS)** | `SignedAssetRecorded` | DocumentSigning | Dispatches `UnlinkSigningSession` → `CheckInMediaItem` |
| **Consumes (SQS)** | `MediaItemSigningSessionUnlinked` | DocumentSigning | Dispatches `CheckInMediaItem` or `ForceReleaseCheckout` |
| **Consumes (SQS)** | `MediaItemCheckedIn` | DocumentSigning | Closes saga (happy) |
| **Consumes (SQS)** | `MediaItemCheckoutForceReleased` | DocumentSigning | Closes saga (compensation) |
| **Consumes (SQS)** | `SigningEnvelopeVoided` | DocumentSigning | Enters compensation |
| **Consumes (SQS)** | `SigningSessionCancelled` | DocumentSigning | Enters compensation |
| **Reads (DynamoDB)** | `media-profiles` | MediaItemReview | Checks `ReviewPolicy` on `MediaItemSubmittedForReview` |
| **Reads/Writes (DynamoDB)** | `media-sagas` | All | Loads and persists saga state |
| **Dispatches** | `CreateMediaChangeRequest`, `LinkMediaChangeRequest` | MediaItemReview | System-only commands |
| **Dispatches** | `ApproveMediaItem`, `RejectMediaItem` | MediaItemReview | Saga resolution |
| **Dispatches** | `FailAssetProcessing` | AssetIngestion | Timeout compensation |
| **Dispatches** | `LinkSigningSession`, `UnlinkSigningSession` | DocumentSigning | Session lifecycle |
| **Dispatches** | `CheckInMediaItem`, `ForceReleaseCheckout` | DocumentSigning | Lock management |
| **Dispatches** | `RecordEnvelopeVoided` | DocumentSigning | Compensation |

#### SagaTimeoutScanner

| Direction | Event / Command | Notes |
|---|---|---|
| **Trigger** | CloudWatch Events (5-minute schedule) | — |
| **Reads (DynamoDB)** | `media-sagas` | Scans for `AssetIngestion` media-sagas where `Status=ProcessingDispatched` and `Payload.TimeoutAt < now` |
| **Dispatches** | `FailAssetProcessing(AssetId, reason: "ProcessingTimeout")` | Via Command Handler |
| **Writes (DynamoDB)** | `media-sagas` | Transitions saga to `Complete` |

#### SecuredSigning Adapter

| Direction | Event / Command | Notes |
|---|---|---|
| **Consumes (SQS)** | `SigningSessionInitiated` | Creates SecuredSigning envelope |
| **Calls (HTTP)** | SecuredSigning eSign API | Envelope creation with primary Asset document + signers |
| **Dispatches** | `RecordEnvelopeCreated(SigningSessionId, EnvelopeId)` | On API success |
| **Receives (webhook)** | `POST /integrations/secured-signing/webhook` | HMAC-validated; API Gateway; not user-facing |
| **Dispatches** | `RecordEnvelopeSent(SigningSessionId)` | On webhook `envelope-sent` |
| **Dispatches** | `RecordSignerCompleted(SigningSessionId, SignerId)` | On webhook `recipient-completed` |
| **Dispatches** | `RecordSigningCompleted(SigningSessionId)` | On webhook `envelope-completed` (after all signers done) |
| **Dispatches** | `RecordSignedAsset(SigningSessionId, SignedAssetId)` | After downloading and uploading signed document to S3 |
| **Dispatches** | `RecordEnvelopeVoided(SigningSessionId, VoidReason)` | On webhook `envelope-voided` |
| **Reads (S3)** | `media-source` | Downloads primary Asset for envelope creation |
| **Writes (S3)** | `media-documents` | Uploads signed document as new Asset |

#### Projectors

| Projector | Consumes | Writes |
|---|---|---|
| `AssetProjector` | `AssetUploaded`, `AssetValidationPassed/Failed`, `AssetProcessingCompleted/Failed`, `AssetTagged`, `AssetArchived`, `AssetDeleted`, `AssetAttachedToMediaItem`, `AssetDetachedFromMediaItem` | `media-assets`, `media-asset-detail` |
| `CollectionProjector` | `CollectionCreated`, `CollectionRenamed`, `CollectionTagged`, `CollectionVisibilityChanged`, `CollectionDefaultProfileSet`, `CollectionArchived`, `RootFolderAdded/RemovedFromCollection` | `media-collections`, `media-collection-detail`, OpenSearch `media-items` (`isAccessible`) |
| `FolderProjector` | `FolderCreated`, `FolderRenamed`, `FolderMoved`, `FolderArchived` | `media-folders`, `media-folder-detail` |
| `MediaItemProjector` | `MediaItemCreated`, `MediaItemAssignedToFolder`, `MediaItemMoved`, `MediaItemTitleUpdated`, `MediaItemTagged`, `MediaItemRevertedToDraft`, `MediaItemMetadataFieldSet/BatchSet`, `AssetAssignedToRole`, `AssetUnassignedFromRole`, `MediaItemSubmittedForReview`, `MediaItemApproved`, `MediaItemRejected`, `MediaItemArchived`, `MediaChangeRequestLinked/Unlinked` | `media-items` (all GSIs), `media-item-detail`, OpenSearch `media-items` |
| `MediaItemVersionProjector` | `MediaItemApproved` | `media-item-versions` (full snapshot per publish) |
| `RegistrationProjector` | `RegistrationInitiated`, `RegistrationSubmitted`, `RegistrationConfirmed`, `RegistrationRejected`, `RegistrationCancelled`, `RegistrationDocumentAttached`, `RegistrationExpiryRecorded` | `media-registrations`, OpenSearch `media-registrations` |
| `RecordTypeProjector` | `RecordTypeCreated`, `FieldAddedToRecordType`, `FieldDefinitionUpdated`, `FieldReplacedInRecordType`, `FieldRemovedFromRecordType`, `FieldsReorderedInRecordType`, `RecordTypeDeprecated`, `RecordTypeRenamed` | `media-record-types` (latest), `media-record-type-versions` (snapshot per version) |
| `MediaProfileProjector` | `MediaProfileCreated`, `MediaProfilePublished`, `MediaProfileDeprecated`, `AssetDefinitionAdded/Updated/Removed/Reordered`, `AssetDefinitionDefaultSet`, `RecordTypeAttachedToProfile`, `RecordTypeVersionPinnedOnProfile`, `RecordTypeDetachedFromProfile`, `ReviewPolicySet` | `media-profiles` |
| `MediaChangeRequestProjector` | `MediaChangeRequestCreated`, `ReviewerAssigned/Removed`, `ReviewApproved/Rejected`, `ReviewerWithdrawn`, `MediaChangeRequestApproved/Rejected`, `ReviewCommentAdded/Edited/Deleted` | `media-change-requests` |

---

### Saga Event Flows

Detailed flow diagrams for cross-aggregate coordination. Full saga state machine and compensation logic: see `specs/media-management-domain-spec.md § Sagas`.

#### AssetIngestionSaga — happy path

```
Processing Worker        Command Handler           SagaOrchestrator
       │                       │                         │
       │──StartAssetProcessing─▶│                         │
       │                       │──AssetProcessingStarted─▶│ (no saga action)
       │                       │                         │
       │──CompleteAssetProcessing─▶│                      │
       │                       │──AssetProcessingCompleted─▶│
       │                       │                         │──close saga──▶ [Complete]
```

#### AssetIngestionSaga — timeout compensation

```
SagaTimeoutScanner       Command Handler           SagaOrchestrator
       │                       │                         │
       │  (polls media-sagas)  │                         │
       │──FailAssetProcessing──▶│                         │
       │                       │──AssetProcessingFailed───▶│
       │                       │                         │──close saga──▶ [Complete]
```

#### MediaItemReviewSaga — full happy path

```
Ingest API          Command Handler         SagaOrchestrator        Command Handler
(user request)      (MediaItem agg)                                 (MCR agg)
     │                    │                       │                      │
     │──Publish───────────▶│                       │                      │
     │                    │──MediaItemSubmittedForReview──▶│              │
     │                    │                       │──CreateMCR────────────▶│
     │                    │                       │       │──MCRCreated───▶│
     │                    │◀─────────────────────────────│──LinkMCR       │
     │                    │──MediaChangeRequestLinked──▶│                  │
     │                    │                       │ [AwaitingReview]       │
     │                    │                       │                        │
     │  (reviewer approves via API — direct commands on MCR aggregate)     │
     │                    │                       │                        │
     │                    │                       │◀──MCRApproved──────────│
     │                    │◀──────────────────────│──ApproveMediaItem      │
     │                    │──MediaItemApproved────▶│                       │
     │                    │                       │──close saga──▶ [Complete]
```

#### DocumentSigningSaga — happy path

```
Ingest API       Command Handler    SagaOrchestrator   SecuredSigning    Command Handler
(user)           (MediaItem agg)                       Adapter           (Session agg)
   │                   │                  │                 │                  │
   │──InitiateSigning──▶│                 │                 │                  │
   │                   │──SessionInitiated─▶│               │                  │
   │                   │                  │──(SQS)──────────▶│                 │
   │                   │                  │                 │──API call──▶ SecuredSigning
   │                   │                  │                 │◀─────────── envelope created
   │                   │                  │                 │──RecordEnvelopeCreated────▶│
   │                   │                  │◀──EnvelopeCreated──────────────────────────│
   │                   │◀─────────────────│──LinkSigningSession                        │
   │                   │──SessionLinked───▶│                │                           │
   │                   │                  │ [AwaitingSigners]                           │
   │                   │                  │                 │                           │
   │                   │          (signers sign via SecuredSigning UI — days may pass)  │
   │                   │                  │                 │──RecordSigningCompleted───▶│
   │                   │                  │                 │──RecordSignedAsset────────▶│
   │                   │                  │◀──SignedAssetRecorded──────────────────────│
   │                   │◀─────────────────│──UnlinkSigningSession                      │
   │                   │──SessionUnlinked──▶│               │                           │
   │                   │◀─────────────────│──CheckInMediaItem                          │
   │                   │──MediaItemCheckedIn─▶│             │                           │
   │                   │                  │──close saga──▶ [Complete]                  │
```

#### DocumentSigningSaga — voided compensation

```
SecuredSigning Adapter   Command Handler        SagaOrchestrator   Command Handler
                         (Session agg)                             (MediaItem agg)
         │                     │                      │                  │
         │ (SecuredSigning voids envelope)             │                  │
         │──RecordEnvelopeVoided──▶│                  │                  │
         │                     │──EnvelopeVoided──────▶│                 │
         │                     │                      │──UnlinkSession────▶│
         │                     │                      │       │──Unlinked──▶│
         │                     │                      │──ForceReleaseCheckout─▶│
         │                     │                      │       │──ForceReleased─▶│
         │                     │                      │──close saga──▶ [Complete]
```

---

## Queue Topology

```
                    SNS Topic: media-domain-events            ← internal
                             │
       ┌──────────────────┬──┴──────────────┬──────────────┐
       ▼                  ▼                 ▼              ▼
SQS: media-projector  (unused —        media-sagas   media-signing
       │               removed)            │              │
       ▼                                   ▼              ▼
  Projectors                          SagaOrchestrator  SecuredSigning
  (cross-aggregate)                                     Adapter
       │
       ▼
  Command Handler ─────── publishes media.* messages ─────▶ (see below)
       │                  via per-module *IntegrationEventPublisher
       │                  classes (inline, no separate Lambda)
       ▼
   SNS topic (cycle — result events fan out again on media-integration-events)

       ── Boundary (separate topic; see ADR-005) ──

                 SNS Topic: media-integration-events        ← published language
                             │
       ┌─────────────────────┼──────────────┬──────────────┬──────────────┐
       ▼                     ▼              ▼              ▼              ▼
SQS: media-cross-         Notifications-  Search/        Billing-      Compliance-
     module-events        owned SQS       Discovery-     owned SQS     owned SQS
     (MM-owned                            owned SQS
      intra-BC fan-in)
       │
       ▼
 Integration Event Consumers Lambda
 (MM-owned; cross-module consumers:
  capability index, saga triggers, etc.)
```

### Queue Configuration

| Queue | Owner | Source topic | Subscription filter | Visibility timeout | Max receive | DLQ | DLQ retention |
|---|---|---|---|---|---|---|---|
| `media-projector` | Media Management | `media-domain-events` | All events | 60s | 3 | `media-projector-dlq` | 14 days |
| `media-processing` | Media Management | `media-domain-events` | `AssetValidationPassed` only | 30 min (image/doc) / 4 h (video) | 3 | `media-processing-dlq` | 14 days |
| `media-sagas` | Media Management | `media-domain-events` | All events | 30s | 3 | `media-sagas-dlq` | 14 days |
| `media-signing` | Media Management | `media-domain-events` | `SigningSessionInitiated` + SecuredSigning webhook triggers | 60s | 3 | `media-signing-dlq` | 14 days |
| `media-cross-module-events` (renamed from `media-notifications`) | Media Management | `media-integration-events` | `EventType` attribute filter — set to the integration event types consumed by intra-BC consumers (see Step 6 catalogue) | 30s | 3 | `media-cross-module-events-dlq` | 7 days |
| External BC consumer queues | External BC | `media-integration-events` | Per-BC filter policy on the `EventType` SNS message attribute | BC-defined | BC-defined | BC-owned DLQ | BC-defined |

All queues are standard (not FIFO). Per-aggregate event ordering is guaranteed at the event store level by `AggregateVersion`; projectors and media-sagas are idempotent and tolerate out-of-order delivery at the SQS level.

**CloudWatch alarms:** DLQ depth > 0 triggers a `P2` alert for `media-processing-dlq` and `media-sagas-dlq`; `P3` for all others.
