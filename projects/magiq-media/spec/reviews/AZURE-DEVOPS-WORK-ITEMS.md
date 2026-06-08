# Azure DevOps Work Items — magiq-media Production Readiness
_Generated from Architecture Review Board assessment, 2026-05-14_

Enter items top-to-bottom. Link each child to its parent as you create them.
Acceptance criteria are listed under each User Story — copy them into the AC field.

---

## Hierarchy Key

```
EPIC
  └── FEATURE
        └── USER STORY
              └── TASK
```

---

---

# EPIC: magiq-media Production Readiness

**Description:**
Resolve all blockers, pre-production gaps, and architectural risks identified in the 2026-05-14 Architecture Review Board assessment. The system is currently rated NO-GO for production. This epic tracks all work required to reach a GO decision, organised into three phases: P0 Immediate Blockers, P1/P2 Pre-Production, and P3 Post-Production.

**Priority:** Critical
**Tags:** production-readiness, architecture-review

---

---

## PHASE 1 — IMMEDIATE BLOCKERS

---

### FEATURE 1.1: Messaging Infrastructure — Production Path

**Description:**
The application is hardcoded to use `DevInProcessMessageBus` in all environments. The production SNS/SQS path has never been exercised. Two critical integration events (`AssetUploadConfirmedIntegrationEvent`, `AssetValidationPassedIntegrationEvent`) are absent from SNS publisher routing. This feature unblocks the entire event-driven pipeline for production.

**Priority:** Critical
**Tags:** messaging, p0, phase-1

---

#### USER STORY 1.1.1: Remove dev-mode messaging hardcode

**As a** platform engineer,
**I want** the application to use the real AWS SNS message bus when `ASPNETCORE_ENVIRONMENT=Production`,
**so that** domain events are durably published to SNS/SQS in all non-local deployments.

**Acceptance Criteria:**
- `Startup.cs` uses `environment.IsDevelopment()` instead of `var isDevelopment = true`
- `ASPNETCORE_ENVIRONMENT=Production` activates the real `AWS.Messaging` message bus
- `ASPNETCORE_ENVIRONMENT=Development` continues to use `DevInProcessMessageBus`
- A staging deployment with `Production` environment confirms messages arrive on `media-domain-events` and `media-integration-events` SNS topics

**Tasks:**
- [ ] Remove `var isDevelopment = true;` hardcode; replace with `environment.IsDevelopment()` in `Startup.cs:58`
- [ ] Verify CDK sets `ASPNETCORE_ENVIRONMENT=Production` correctly for prod stage
- [ ] Deploy to staging with `Production` environment and confirm SNS topic receives domain events
- [ ] Confirm all SQS queues (`media-projector`, `media-processing`, `media-cross-module-events`, `media-sagas`) receive messages

---

#### USER STORY 1.1.2: Register missing integration events for SNS routing

**As a** platform engineer,
**I want** `AssetUploadConfirmedIntegrationEvent` and `AssetValidationPassedIntegrationEvent` to be registered in the AWS.Messaging SNS routing configuration,
**so that** the processing pipeline and `AssetIngestionSaga` receive the events they depend on when running against real SNS.

**Acceptance Criteria:**
- `AssetManagementIntegrationEventPublishers.cs` includes routing for both events
- In a staging environment with real SNS: publishing `AssetUploadConfirmedIntegrationEvent` results in the message arriving on `media-processing` SQS queue
- In a staging environment with real SNS: publishing `AssetValidationPassedIntegrationEvent` results in the message arriving on `media-sagas` SQS queue
- Integration event catalog alignment unit test passes

**Tasks:**
- [ ] Add `builder.PublishIntegrationEventToSNS<AssetUploadConfirmedIntegrationEvent>(topicArn)` to `AssetManagementIntegrationEventPublishers.cs`
- [ ] Add `builder.PublishIntegrationEventToSNS<AssetValidationPassedIntegrationEvent>(topicArn)` to `AssetManagementIntegrationEventPublishers.cs`
- [ ] Write integration event catalog alignment unit test for AssetManagement module
- [ ] Validate in staging that both events flow through SNS to the correct queues

---

### FEATURE 1.2: Transactional Outbox

**Description:**
Domain events are written to the DynamoDB event store and then published to SNS in the same HTTP request with no transactional guarantee. An SNS failure after a successful DynamoDB write silently drops all downstream processing. This feature implements an outbox pattern to guarantee at-least-once delivery.

**Priority:** Critical
**Tags:** messaging, reliability, outbox, p0, phase-1

---

#### USER STORY 1.2.1: Write outbox records atomically with event store writes

**As a** platform engineer,
**I want** every domain event append to also write a pending outbox record in the same `TransactWriteItems` call,
**so that** no event can be committed to the event store without a corresponding pending delivery record.

**Acceptance Criteria:**
- A new `media-outbox` DynamoDB table is provisioned with PK `(TenantId, EventId)` and a TTL attribute
- `IEventStore.SaveAsync` wraps the event append and outbox record write in the same `TransactWriteItems` call
- If the `TransactWriteItems` call fails, neither the event nor the outbox record is written
- If SNS publish subsequently fails, the outbox record remains `Pending` and is not lost

**Tasks:**
- [ ] Provision `media-outbox` DynamoDB table in CDK (PK: `EventId`, attributes: `TenantId`, `Status`, `Payload`, `TopicArn`, `CreatedAt`, `TTL`)
- [ ] Modify `IEventStore.SaveAsync` to include outbox record write in the `TransactWriteItems` call
- [ ] Define `OutboxRecord` schema: `EventId`, `TopicArn`, `Payload`, `Status (Pending/Delivered)`, `CreatedAt`, `AttemptCount`
- [ ] Write unit test: assert that a simulated SNS failure leaves the outbox record in `Pending` state

---

#### USER STORY 1.2.2: Implement outbox relay process

**As a** platform engineer,
**I want** a relay process that polls the outbox table, publishes pending records to SNS, and marks them delivered,
**so that** every committed event is guaranteed to eventually be published even if the original inline publish failed.

**Acceptance Criteria:**
- Outbox relay runs on a scheduled trigger (EventBridge Scheduler, e.g. every 30 seconds)
- Relay reads `Pending` outbox records, publishes to SNS, marks as `Delivered`
- Relay is idempotent: re-publishing an already-delivered record is a no-op (SNS dedup via `EventId` as `MessageDeduplicationId`)
- Relay failures increment `AttemptCount`; records exceeding max attempts are moved to a DLQ
- CloudWatch alarm fires if any outbox record has been `Pending` for more than 2 minutes

**Tasks:**
- [ ] Implement `OutboxRelayLambda` (or extend existing Lambda with a scheduled handler)
- [ ] Implement relay: scan `media-outbox` for `Status = Pending`, publish to `TopicArn`, mark `Delivered`
- [ ] Add idempotency via SNS `MessageDeduplicationId = EventId`
- [ ] Add `AttemptCount` increment logic and DLQ routing above threshold
- [ ] Add CloudWatch alarm: outbox records pending > 2 minutes
- [ ] Add CDK construct for EventBridge Scheduler rule triggering the relay

---

### FEATURE 1.3: Asset Processing Pipeline

**Description:**
`AssetProcessingWorker.RunProcessingPipelineAsync` throws `NotImplementedException`. Every asset with a Processing-capable MediaProfile fails after upload. This feature implements the core rendition generation and metadata extraction pipeline.

**Priority:** Critical
**Tags:** processing, p0, phase-1

---

#### USER STORY 1.3.1: Implement image processing pipeline

**As an** end user,
**I want** my uploaded image to be processed into thumbnails and have its metadata extracted,
**so that** I can view previews and technical details without downloading the original.

**Acceptance Criteria:**
- Uploaded images with a Processing-capable MediaProfile produce at least two renditions (thumbnail, preview)
- Extracted metadata includes: width, height, DPI, colour space, bit depth, format, EXIF data
- `AssetProcessingCompleted` event carries rendition list and populated `AssetMetadata`
- `ProcessingStatus = Transcoded` on successful completion
- `AssetProcessingFailed` is raised with `FailureCategory.ProcessingError` on pipeline failure

**Tasks:**
- [ ] Add ImageMagick or Sharp Lambda layer to CDK compute stack
- [ ] Implement image rendition generation: produce `thumbnail` (150px) and `preview` (800px) variants
- [ ] Upload renditions to `media-renditions` S3 bucket using the `{tenantId}/{shard}/{assetId}/{renditionType}.{ext}` key pattern
- [ ] Implement EXIF and technical metadata extraction (format, dimensions, DPI, colour profile)
- [ ] Populate `CompleteProcessingJobCommand` with rendition list and `AssetMetadata`
- [ ] Write unit test for image rendition generation covering JPEG, PNG, WebP inputs
- [ ] Write unit test for metadata extraction

---

#### USER STORY 1.3.2: Implement document and audio metadata extraction

**As an** end user,
**I want** my uploaded documents and audio files to have their metadata extracted,
**so that** technical characteristics are surfaced without requiring the client to inspect the raw file.

**Acceptance Criteria:**
- PDF uploads produce `AssetMetadata.PageCount`
- Audio uploads produce duration, codec, bit rate, sample rate, and channel count
- Archive uploads produce file count and compression metadata
- No renditions are generated for these content types (Processing capability gate is respected)
- `ProcessingStatus = Validated` on non-rendition paths

**Tasks:**
- [ ] Add ExifTool Lambda layer to CDK compute stack
- [ ] Implement PDF metadata extraction (page count via ExifTool or iTextSharp)
- [ ] Implement audio metadata extraction (duration, codec, bitrate, sample rate, channels)
- [ ] Implement archive metadata extraction (file count, compression ratio)
- [ ] Write unit tests for each content type metadata path

---

### FEATURE 1.4: Virus Scanning

**Description:**
`AssetValidationWorker` always returns `ValidationOutcome.Passed`. No content inspection is performed. Infected files pass into Active state. This feature implements mandatory virus scanning for all uploaded assets.

**Priority:** Critical
**Tags:** security, processing, p0, phase-1

---

#### USER STORY 1.4.1: Implement virus scanning for uploaded assets

**As a** platform security officer,
**I want** every uploaded asset to be scanned for malware before it is activated,
**so that** infected files cannot be stored in or served from the platform.

**Acceptance Criteria:**
- `AssetValidationWorker` performs a real virus scan before dispatching `RecordProcessingJobScanResultCommand`
- `ValidationOutcome.VirusDetected` transitions the asset to `ContainsVirus` terminal state
- The infected S3 object is hard-deleted from `media-source` before `AssetInfectionDetected` is appended
- A copy of the infected file is moved to the `media-quarantine` bucket for forensic review
- `AssetInfectionDetectedIntegrationEvent` is published to `media-integration-events`
- `ValidationOutcome.Failed` is returned for unsupported or corrupt file formats
- Scanning must complete within a defined SLA (e.g. < 30 seconds for files under 100 MB)

**Tasks:**
- [ ] Integrate AWS GuardDuty Malware Protection for S3 on `media-source` bucket (preferred) OR add ClamAV Lambda layer
- [ ] Implement scan invocation in `AssetValidationWorker.ValidateAsync`
- [ ] Implement `VirusDetected` path: copy infected file to quarantine bucket, delete from source
- [ ] Implement `ValidationOutcome.Failed` path for corrupt or unsupported format
- [ ] Add `media-quarantine` IAM grants to processing worker role in CDK
- [ ] Write integration test: upload a test EICAR virus signature file; assert `ContainsVirus` state and S3 deletion
- [ ] Write integration test: upload a clean file; assert `ValidationOutcome.Passed`

---

### FEATURE 1.5: CORS Hardening

**Description:**
Both `Media.Api` and `Media.QueryApi` apply `AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()` CORS policy in all environments including production. This feature replaces the wildcard with an environment-specific allowed origins list.

**Priority:** Critical
**Tags:** security, p0, phase-1

---

#### USER STORY 1.5.1: Implement environment-scoped CORS policy

**As a** security engineer,
**I want** the API to only accept cross-origin requests from known, approved origins,
**so that** cross-site attacks targeting authenticated sessions cannot extract data via a malicious web page.

**Acceptance Criteria:**
- Production CORS policy has an explicit allowed origins list (no wildcards)
- Development CORS policy may retain `AllowAnyOrigin` for local tooling
- Allowed origins are injected via CDK environment config, not hardcoded
- Both `Media.Api` and `Media.QueryApi` apply the policy
- An OPTIONS preflight from an unlisted origin returns a non-permissive response

**Tasks:**
- [ ] Add `Media:Cors:AllowedOrigins` configuration key to CDK environment config
- [ ] Update `Media.Api/Startup.cs`: read allowed origins from config; apply in production, wildcard in development
- [ ] Update `Media.QueryApi/Startup.cs`: same pattern
- [ ] Add production allowed origins list to CDK stack config
- [ ] Write test: preflight from unlisted origin returns no `Access-Control-Allow-Origin` header

---

### FEATURE 1.6: Write-Side Index Projectors

**Description:**
Two write-side index projectors remain unimplemented. Their absence blocks folder-level registration constraint enforcement. `FolderStatusIndexProjector` is not needed — parent existence and depth are enforced via aggregate load (`IFolderRepository`) and strongly-consistent counters (`IUniquenessCounterService`); archive cascade is handled by `IFolderArchiveFanOutWorker`.

**Priority:** Critical
**Tags:** projectors, domain, p0, phase-1

---

#### USER STORY 1.6.2: Implement RegistrationCountIndexProjector and FolderActiveItemCountIndexProjector

**As a** platform engineer,
**I want** folder-level registration and active item counts to be maintained by projectors,
**so that** archive constraints (cannot archive a folder with active registrations) are enforceable at command time.

**Acceptance Criteria:**
- `folder-registration-index` and `folder-active-item-count-index` DynamoDB tables are provisioned in CDK
- Both projectors are registered in `ProjectorRegistrations.cs`
- `ArchiveFolder` command reads from both indexes before emitting `FolderArchived`
- Attempting to archive a folder with active registrations returns `DomainError.FolderHasActiveRegistrations`

**Tasks:**
- [ ] Provision `folder-registration-index` DynamoDB table in `write-indexes.construct.ts`
- [ ] Provision `folder-active-item-count-index` DynamoDB table in `write-indexes.construct.ts`
- [ ] Implement `RegistrationCountIndexProjector`
- [ ] Implement `FolderActiveItemCountIndexProjector`
- [ ] Register both projectors in `ProjectorRegistrations.cs`
- [ ] Add constraint check in `ArchiveFolderCommandHandler`: read both indexes, reject if counts > 0
- [ ] Write integration test: archive folder with active registration — assert `DomainError.FolderHasActiveRegistrations`

---

---

## PHASE 2 — PRE-PRODUCTION

---

### FEATURE 2.1: DocumentSigning Module

**Description:**
The entire DocumentSigning bounded context is unimplemented. `SigningSessionInitiatedHandler` throws `NotImplementedException`. `SecuredSigningWebhookHandler` returns 501. The `media-signing` SQS queue is commented out in CDK.

**Priority:** High
**Tags:** document-signing, p1, phase-2

---

#### USER STORY 2.1.1: Implement SecuredSigning envelope creation

**As a** tenant admin,
**I want** initiating a document signing session to trigger envelope creation in SecuredSigning,
**so that** signers receive signing requests automatically without manual intervention.

**Acceptance Criteria:**
- `SigningSessionInitiatedHandler` calls the SecuredSigning eSign API and receives an `EnvelopeId`
- `LinkSigningSessionCommand` is dispatched with the returned `EnvelopeId`
- On API failure, `MessageProcessStatus.Failed()` is returned to trigger SQS retry
- After `maxReceiveCount` retries, the message routes to `media-signing-dlq`
- `media-signing` SQS queue is provisioned and subscribed to `media-domain-events` SNS

**Tasks:**
- [ ] Uncomment `media-signing` SQS queue and DLQ in `sqs-queues.construct.ts` and CDK compute stack
- [ ] Implement `ISecuredSigningApiClient` with `CreateEnvelopeAsync` method
- [ ] Register `ISecuredSigningApiClient` HTTP client in `SecuredSigningRegistrations.cs`
- [ ] Implement `SigningSessionInitiatedHandler.HandleAsync`: build request, call API, dispatch `LinkSigningSessionCommand`
- [ ] Add retry policy (Polly) to `ISecuredSigningApiClient` for transient HTTP errors
- [ ] Register `ISigningDomainEvent` in `DomainEventPublishingMiddleware._supportedInterfaces`
- [ ] Add DocumentSigning infrastructure to `Startup.cs` (currently `// todo`)

---

#### USER STORY 2.1.2: Implement SecuredSigning webhook handler

**As a** platform engineer,
**I want** SecuredSigning webhook callbacks to be validated and dispatched to domain commands,
**so that** signing events (sent, completed, voided) update the `DocumentSigningSession` aggregate state.

**Acceptance Criteria:**
- HMAC signature on every incoming webhook is validated before dispatch
- Unsupported or invalid signatures return HTTP 400
- `EnvelopeId` is used to look up `TenantId` from `media-signing-sessions` table
- `EnvelopeSent`, `SignerCompleted`, `EnvelopeCompleted`, and `EnvelopeVoided` events each dispatch the correct domain command
- `SigningSessionDetailProjector` and `SigningSessionSummaryProjector` are implemented and registered

**Tasks:**
- [ ] Implement HMAC validation in `SecuredSigningWebhookHandler` using configured secret
- [ ] Implement payload deserialisation to `SecuredSigningWebhookPayload`
- [ ] Implement `TenantId` resolution from `EnvelopeId` via `media-signing-sessions` DynamoDB lookup
- [ ] Implement event type switch: dispatch correct command per `EventType`
- [ ] Implement `SigningSessionDetailProjector` and register in `ProjectorRegistrations.cs`
- [ ] Implement `SigningSessionSummaryProjector` and register in `ProjectorRegistrations.cs`
- [ ] Write unit test: invalid HMAC signature returns 400

---

### FEATURE 2.2: Saga Reliability and Observability

**Description:**
The `SagaTimeoutScanner` has a counter bug that causes it to always report zero dispatches. The `media-sagas` table has no GSI, forcing a full-table scan. Saga state distribution is not observable. This feature resolves all reliability and monitoring gaps in saga orchestration.

**Priority:** High
**Tags:** sagas, observability, p1, phase-2

---

#### USER STORY 2.2.1: Fix SagaTimeoutScanner counter bug and add GSI

**As an** operator,
**I want** the SagaTimeoutScanner to accurately report how many timeout compensations it dispatches,
**so that** I can verify the scanner is functioning and detect widespread saga stalls.

**Acceptance Criteria:**
- `ScanPassAsync` correctly increments and returns the dispatch count to the outer scope
- Final log statement reports accurate `ProcessingDispatched` and `AwaitingValidation` counts
- A GSI on `media-sagas` for `(SagaType, Status, TimeoutAt)` replaces the full-table scan
- CloudWatch metric `SagaTimeoutCompensationDispatched` is published per scanner run

**Tasks:**
- [ ] Fix `ScanPassAsync` to use `ref int dispatched` or return `int` rather than passing by value
- [ ] Add GSI `SagaTypeStatusTimeoutIndex` on `media-sagas` table in CDK event-store construct
- [ ] Update `ScanPassAsync` to use `QueryRequest` with the new GSI instead of `ScanRequest`
- [ ] Add CloudWatch PutMetricData call at end of scanner run with dispatch counts
- [ ] Write unit test: assert counter correctly reflects compensation dispatch count

---

#### USER STORY 2.2.2: Add saga state observability

**As an** operator,
**I want** a CloudWatch dashboard showing the distribution of saga states and alerts for approaching timeouts,
**so that** I can detect and respond to widespread processing or validation stalls before they affect tenants.

**Acceptance Criteria:**
- CloudWatch custom metrics published each scanner run: count of sagas per state (`AwaitingValidation`, `ProcessingDispatched`, `Completed`, `Failed`)
- Alarm fires when any saga has been in `ProcessingDispatched` or `AwaitingValidation` for > 80% of its timeout window
- Dashboard widget shows saga state distribution over the last 24 hours
- All saga timeout durations are documented in `system-architecture.md`

**Tasks:**
- [ ] Add per-state metric publishing to `AssetIngestionTimeoutScanner`
- [ ] Document all saga timeout durations (AwaitingValidation TTL, ProcessingDispatched TTL per content type) in `system-architecture.md`
- [ ] Add CloudWatch alarms for sagas approaching timeout threshold
- [ ] Add saga state distribution widget to CloudWatch dashboard

---

### FEATURE 2.3: Storage Lifecycle Hardening

**Description:**
`media-renditions` has no lifecycle rules. Renditions accumulate indefinitely regardless of source asset state. Read model DynamoDB tables lack PITR. This feature closes all storage lifecycle and durability gaps.

**Priority:** High
**Tags:** storage, lifecycle, p1, phase-2

---

#### USER STORY 2.3.1: Add rendition lifecycle management

**As a** platform engineer,
**I want** renditions to follow the same storage tier lifecycle as their source originals,
**so that** storage costs scale proportionally and deleted assets do not retain accessible rendition URLs indefinitely.

**Acceptance Criteria:**
- `media-renditions` bucket has a lifecycle rule matching `media-source` tier progression (Standard → StandardIA → GlacierInstant → DeepArchive)
- `media-renditions` bucket has `AbortIncompleteMultipartUploads` lifecycle rule (7-day window)
- When a source asset is soft-deleted, a rendition deletion flag is written to the outbox for deferred cleanup
- Spec is updated with rendition deletion semantics

**Tasks:**
- [ ] Add `media-renditions` lifecycle rule to CDK `media-buckets.construct.ts` matching source tier progression
- [ ] Add `AbortIncompleteMultipartUploads` rule (7 days) to `media-renditions` and `media-documents` buckets
- [ ] Define rendition deletion strategy in spec (`asset.write-model.md`)
- [ ] Implement rendition cleanup outbox event on `AssetDeleted`

---

#### USER STORY 2.3.2: Enable PITR and deletion protection on all DynamoDB tables

**As an** operator,
**I want** all DynamoDB tables to have point-in-time recovery enabled,
**so that** table corruption or accidental data loss can be recovered to any second within the 35-day window.

**Acceptance Criteria:**
- PITR is enabled on all read model tables in `read-models.construct.ts`
- PITR is confirmed enabled on `media-events` and `media-sagas` (already set)
- Deletion protection is enabled on all read model tables
- CDK diff confirms no tables are missing these settings

**Tasks:**
- [ ] Add `pointInTimeRecovery: true` to all tables in `read-models.construct.ts`
- [ ] Add `deletionProtection: true` to all tables in `read-models.construct.ts`
- [ ] Add `pointInTimeRecovery: true` to all tables in `write-indexes.construct.ts`
- [ ] Run `cdk diff` and confirm no regressions

---

### FEATURE 2.4: Domain and Projector Correctness

**Description:**
Projectors have no sequence guards against out-of-order SQS delivery. The MediaItem read model does not handle `AssetArchived` / `AssetDeleted` events. The `DomainEventPublishingMiddleware` publishes to SNS before running in-process projectors. StorageTier enum is misaligned between spec and implementation.

**Priority:** High
**Tags:** projectors, domain, correctness, p1, phase-2

---

#### USER STORY 2.4.1: Implement projector sequence guards

**As a** platform engineer,
**I want** every projector to enforce event sequence order before applying an event,
**so that** out-of-order SQS delivery does not produce incorrect read model state.

**Acceptance Criteria:**
- Each projector tracks `LastProjectedVersion` per entity in its DynamoDB record
- Projector rejects (requeues) an event if `event.AggregateVersion != lastProjectedVersion + 1`
- First event for a new entity (version 1) is always accepted
- Idempotent: applying the same event version twice is a no-op, not an error
- Unit test: apply event version 3 before version 2 — assert event is requeued, state unchanged

**Tasks:**
- [ ] Add `LastProjectedVersion` attribute to all projector DynamoDB schemas
- [ ] Implement sequence guard in projection base class or shared helper
- [ ] Apply guard to `AssetDetailProjector`, `AssetSummaryProjector`, `MediaItemDetailProjector`, `MediaItemSummaryProjector`
- [ ] Apply guard to all remaining projectors
- [ ] Write unit test: out-of-order event is requeued without state mutation

---

#### USER STORY 2.4.2: Handle asset state changes in MediaItem read model

**As an** end user,
**I want** the MediaItem detail to reflect when an assigned asset has been archived or deleted,
**so that** I can see which role slots are inaccessible and take corrective action.

**Acceptance Criteria:**
- `MediaItemDetailProjector` handles `AssetArchived` and `AssetDeleted` events from the Asset stream
- Affected role slot in the MediaItem read model surfaces `assetStatus: "Archived"` or `assetStatus: "Deleted"`
- `MediaItem` read model exposes a `hasAccessibleAssets: bool` flag
- Client can detect degraded state without fetching individual asset records
- Spec updated in `asset.write-model.md` with this cascaded state behaviour

**Tasks:**
- [ ] Update `MediaItemDetailProjector` to subscribe to `AssetArchived` and `AssetDeleted` events
- [ ] Add `assetStatus` field to MediaItem role slot in `MediaItemDetailReadModel`
- [ ] Add `hasAccessibleAssets` computed flag to `MediaItemDetailReadModel`
- [ ] Update `CROSS-SESSION-NOTES.md` Session 8 item to Resolved
- [ ] Write unit test: asset archived event updates MediaItem role slot `assetStatus`

---

#### USER STORY 2.4.3: Fix middleware event publishing order and align StorageTier enum

**As a** platform engineer,
**I want** in-process projectors to complete before domain events are published to SNS,
**and** the StorageTier enum to match the four-tier lifecycle defined in the architecture,
**so that** downstream consumers do not observe stale read models and the domain correctly represents all storage states.

**Acceptance Criteria:**
- `DomainEventPublishingMiddleware.InvokeAsync` calls `await next(...)` before `messageBus.PublishAsync(...)`
- `StorageTier` enum contains: `Standard`, `StandardIA`, `GlacierInstant`, `DeepArchive`
- `Glacier` is retained as a legacy alias comment only — no new events emit `Glacier`
- `asset.write-model.md` StorageTier definition is updated to all four values

**Tasks:**
- [ ] Swap order in `DomainEventPublishingMiddleware.InvokeAsync`: call `next` first, then publish
- [ ] Add `StandardIA`, `GlacierInstant`, `DeepArchive` to `StorageTier` enum in `AssetManagement.Domain`
- [ ] Add code comment on `Glacier` value noting it is a legacy alias
- [ ] Update `StorageTierTransitionScanner` scan thresholds to reference new enum values
- [ ] Update `asset.write-model.md` StorageTier table
- [ ] Write migration note in spec for historical events that carry the legacy `Glacier` value

---

### FEATURE 2.5: API Design — Pagination and Versioning

**Description:**
All list endpoints use implicit pagination without a defined cursor strategy. OpenSearch queries use `from/size` which is O(n) in memory for large datasets. No API versioning or deprecation policy exists.

**Priority:** High
**Tags:** api, pagination, versioning, p1, phase-2

---

#### USER STORY 2.5.1: Implement cursor-based pagination across all list endpoints

**As an** end user,
**I want** to paginate through large result sets without missing or duplicating items,
**so that** browsing a tenant's media library is reliable under concurrent modifications.

**Acceptance Criteria:**
- All DynamoDB-backed list endpoints return a `nextCursor` token when more results exist
- Clients pass `cursor` query parameter to fetch the next page
- `nextCursor` is a base64-encoded `LastEvaluatedKey`
- OpenSearch-backed search endpoints use `search_after` with a `nextCursor` token (not `from/size`)
- `api-conventions.md` documents the cursor pagination contract

**Tasks:**
- [ ] Define cursor pagination contract in `spec/shared/api-conventions.md`
- [ ] Implement cursor encoding/decoding helper (`Base64.Encode(LastEvaluatedKey)`)
- [ ] Update all DynamoDB `Query` and `Scan` calls to use `ExclusiveStartKey` from decoded cursor
- [ ] Update all list endpoint response contracts to include `nextCursor?: string`
- [ ] Replace `from/size` with `search_after` in all OpenSearch query handlers
- [ ] Write API test: page through a large result set — assert no duplicates or gaps

---

#### USER STORY 2.5.2: Define API versioning and deprecation policy

**As an** API consumer,
**I want** a documented versioning and deprecation policy,
**so that** I can safely upgrade to new API versions with a defined migration window.

**Acceptance Criteria:**
- `api-conventions.md` documents: version URL scheme, minimum supported versions, sunset headers, deprecation notice period (minimum 6 months)
- All endpoints return `Sunset` and `Deprecation` headers when a version is deprecated
- Policy is agreed and signed off before first external consumer integration

**Tasks:**
- [ ] Write versioning and deprecation policy in `spec/shared/api-conventions.md`
- [ ] Define version negotiation behaviour (URL prefix only vs. header negotiation)
- [ ] Implement `Sunset` response header middleware for deprecated endpoint versions
- [ ] Document in `system-spec.md` how breaking vs. non-breaking changes are classified

---

### FEATURE 2.6: Health Checks and Observability

**Description:**
The `/healthz` endpoint returns 200 if the Lambda Web Adapter probe passes — it does not verify DynamoDB, SNS, or S3 connectivity. The SagaTimeoutScanner always reports zero. No DLQ remediation runbook exists.

**Priority:** High
**Tags:** observability, health, p1, phase-2

---

#### USER STORY 2.6.1: Implement deep health checks

**As an** operator,
**I want** the `/healthz` endpoint to verify all critical dependencies are reachable,
**so that** a Lambda reporting healthy actually has functioning connectivity to DynamoDB, SNS, and S3.

**Acceptance Criteria:**
- `/healthz` performs: DynamoDB `DescribeTable` on `media-events`, SNS `GetTopicAttributes` on `media-domain-events`, S3 `HeadBucket` on `media-source`
- Any dependency failure returns HTTP 503 with a structured body identifying the failing dependency
- Health check completes in < 2 seconds
- Lambda Web Adapter readiness probe continues to use `/healthz`

**Tasks:**
- [ ] Replace trivial `services.AddHealthChecks()` with dependency-specific checks
- [ ] Add DynamoDB health check: `DescribeTable` on `media-events`
- [ ] Add SNS health check: `GetTopicAttributes` on `media-domain-events`
- [ ] Add S3 health check: `HeadBucket` on `media-source`
- [ ] Return structured 503 body identifying failing dependency
- [ ] Write integration test: assert 503 when DynamoDB is unreachable

---

#### USER STORY 2.6.2: Document DLQ remediation runbook

**As an** operator,
**I want** a documented procedure for handling messages that land in any DLQ,
**so that** projection gaps and missed saga advances can be recovered without manual DynamoDB surgery.

**Acceptance Criteria:**
- Runbook covers: inspect DLQ message, identify root cause, fix consumer if needed, replay via redrive or manual re-publish, confirm resolution
- Runbook is specific to each MM-owned queue's DLQ (`media-projector-dlq`, `media-processing-dlq`, `media-cross-module-events-dlq`, `media-sagas-dlq`)
- Runbook is stored in `spec/operations/` and linked from `system-architecture.md`

**Tasks:**
- [ ] Create `spec/operations/` directory
- [ ] Write `dlq-remediation-runbook.md` covering all four MM-owned DLQs
- [ ] Document SQS DLQ redrive procedure using AWS Console and CLI
- [ ] Add link to runbook from `system-architecture.md` observability section

---

### FEATURE 2.7: Infrastructure and Deployment Hardening

**Description:**
No rollback strategy, no deployment runbook, no Lambda alias/traffic shifting configuration, and no DynamoDB schema migration strategy exists.

**Priority:** High
**Tags:** infrastructure, deployment, p1, phase-2

---

#### USER STORY 2.7.1: Implement Lambda deployment safety (aliases and rollback)

**As an** operator,
**I want** Lambda deployments to use aliases with traffic shifting,
**so that** a bad deployment can be rolled back in under 5 minutes without full redeployment.

**Acceptance Criteria:**
- All Lambda functions in CDK use a `live` alias pointing to a specific version
- New deployments shift traffic from the previous version using weighted routing (10% canary before full cutover)
- Rollback procedure takes < 5 minutes: update alias weight to 0% on new version
- Rollback runbook is documented in `spec/operations/`

**Tasks:**
- [ ] Add Lambda function versioning and `live` alias to all CDK Lambda constructs
- [ ] Configure CodeDeploy (or CDK `LambdaDeploymentGroup`) for weighted traffic shifting
- [ ] Write rollback runbook in `spec/operations/rollback-runbook.md`
- [ ] Define alarm-triggered automatic rollback on Lambda error rate spike

---

#### USER STORY 2.7.2: Define DynamoDB schema migration strategy

**As a** platform engineer,
**I want** a documented procedure for making DynamoDB schema changes safely,
**so that** adding GSIs, changing attribute types, or backfilling tables does not cause a read model outage.

**Acceptance Criteria:**
- Policy documented: additive-only attribute changes are safe; breaking changes require table rebuild
- GSI backfill procedure documented: parallel scan with rate-limited writes
- Table rebuild procedure documented: create new table, replay events, cut over read traffic, delete old table
- Strategy stored in `spec/operations/dynamodb-migration-strategy.md`

**Tasks:**
- [ ] Write `spec/operations/dynamodb-migration-strategy.md`
- [ ] Document additive-only change policy and what constitutes a breaking change
- [ ] Document GSI backfill procedure with CDK construct changes
- [ ] Document zero-downtime table rebuild procedure using projection replay

---

### FEATURE 2.8: Test Suite Foundation

**Description:**
Zero automated tests exist in the repository. No domain invariants, command handlers, projectors, or saga flows have test coverage. This feature establishes the minimum test baseline required before production.

**Priority:** High
**Tags:** testing, quality, p1, phase-2

---

#### USER STORY 2.8.1: Implement domain aggregate unit tests

**As a** developer,
**I want** unit tests covering all aggregate invariants and state transitions,
**so that** regressions in domain logic are caught before they reach any environment.

**Acceptance Criteria:**
- `Asset` aggregate: all status transition paths tested (happy path and invariant violations)
- `Asset` aggregate: all `FailureCategory` / `Status` combination guards tested
- `MediaItem`, `Collection`, `Folder`, `Registration`, `ProcessingJob` aggregates: key invariants covered
- Tests run in < 10 seconds
- Minimum 80% branch coverage on all aggregate `Apply` and command methods

**Tasks:**
- [ ] Create test project `AssetManagement.Domain.Tests`
- [ ] Write `Asset` aggregate tests: `ConfirmUpload`, `RecordValidationResult`, `CompleteProcessing`, `FailProcessing` (all FailureCategory/Status combos)
- [ ] Write `Asset` aggregate tests: `Archive`, `Delete`, `AttachToMediaItem`, `DetachFromMediaItem`
- [ ] Create test projects for `Catalog`, `Registration`, `Processing` domain
- [ ] Write key invariant tests for `MediaItem`, `Collection`, `Folder`, `Registration`, `ProcessingJob`

---

#### USER STORY 2.8.2: Implement command handler and security integration tests

**As a** developer,
**I want** integration tests covering command handler flows and all three PERM security scenarios,
**so that** ownership enforcement, actor type restrictions, and self-review blocking are verified.

**Acceptance Criteria:**
- `UploadAsset` → `ConfirmAssetUpload` → event store write is tested end-to-end against a real DynamoDB local instance
- PERM-1 (cross-owner write) returns `DomainError.Forbidden`
- PERM-2 (user calls system-only endpoint) returns HTTP 403
- PERM-3 (reviewer self-approval) returns `DomainError.ReviewerSelfApproval`
- Integration event catalog alignment test passes for all modules

**Tasks:**
- [ ] Set up DynamoDB local test fixture (Docker or `DynamoDB.Local` NuGet)
- [ ] Write `UploadAsset` → `ConfirmAssetUpload` integration test against DynamoDB local
- [ ] Write PERM-1 test: assert `DomainError.Forbidden` for cross-owner write
- [ ] Write PERM-2 test: assert HTTP 403 for user calling system-only endpoint
- [ ] Write PERM-3 test: assert `DomainError.ReviewerSelfApproval` on self-approval attempt
- [ ] Write integration event catalog alignment unit test per module

---

#### USER STORY 2.8.3: Implement projector idempotency and saga flow tests

**As a** developer,
**I want** tests verifying projector idempotency and the `AssetIngestionSaga` happy path and timeout compensation,
**so that** event replay and saga timeout behaviour are verified before production.

**Acceptance Criteria:**
- Applying the same event twice to any projector produces no state change on the second application
- Out-of-order event delivery is correctly requeued without state mutation
- `AssetIngestionSaga` happy path (upload → validate → process → complete) is verified
- `AssetIngestionSaga` timeout compensation dispatches `FailProcessingJobCommand` correctly

**Tasks:**
- [ ] Write projector idempotency tests for `AssetDetailProjector` and `MediaItemDetailProjector`
- [ ] Write out-of-order event requeue test for at least one projector
- [ ] Write `AssetIngestionSaga` happy path test
- [ ] Write `AssetIngestionSaga` `ProcessingDispatched` timeout compensation test
- [ ] Write `AssetIngestionSaga` `AwaitingValidation` timeout compensation test

---

### FEATURE 2.9: Specification Completion

**Description:**
Multiple specification sections are incomplete, inconsistent, or missing entirely. These gaps create implementation ambiguity. This feature closes all pre-production spec gaps.

**Priority:** Medium
**Tags:** spec, documentation, p2, phase-2

---

#### USER STORY 2.9.1: Close critical spec gaps (error catalog, pagination, versioning, CORS)

**As a** developer,
**I want** the specification to define the error catalog, pagination contract, API versioning policy, and CORS requirements,
**so that** implementation is unambiguous and consistent across all bounded contexts.

**Acceptance Criteria:**
- `spec/shared/error-catalog.md` lists all `errorCode` values with HTTP status and producing conditions
- `spec/shared/api-conventions.md` defines cursor-based pagination contract
- `spec/shared/api-conventions.md` defines versioning and deprecation policy
- `system-spec.md` defines CORS policy requirements per environment
- `system-spec.md` defines rate limiting strategy

**Tasks:**
- [ ] Create `spec/shared/error-catalog.md` with all known `errorCode` values
- [ ] Add cursor pagination contract to `api-conventions.md`
- [ ] Add versioning and deprecation policy to `api-conventions.md`
- [ ] Add CORS policy requirements to `system-spec.md`
- [ ] Add rate limiting specification to `system-spec.md`

---

#### USER STORY 2.9.2: Close domain and event sourcing spec gaps

**As a** developer,
**I want** the specification to define event versioning, saga timeouts, Registration retention semantics, and the `AssetProcessingFailed` polymorphic pattern,
**so that** these cross-cutting concerns are implemented consistently.

**Acceptance Criteria:**
- `system-spec.md` Event Versioning section is complete: `SchemaVersion` field, upcasting strategy, compatibility policy
- All saga timeout durations are documented in `system-architecture.md`
- Registration lifecycle and retention semantics are defined in `Registration/context-overview.md`
- ADR is created for `AssetProcessingFailed` polymorphic `Status` field pattern
- `CROSS-SESSION-NOTES.md` R-03 rename and Session 8 projector item are resolved

**Tasks:**
- [ ] Complete Event Versioning section of `system-spec.md`
- [ ] Document all saga timeout durations in `system-architecture.md`
- [ ] Define Registration retention and legal hold semantics
- [ ] Write ADR for `AssetProcessingFailed` polymorphic `Status` field
- [ ] Apply `submit-for-review` → `submit` rename in `ChangeRequests/business-scenarios.md`
- [ ] Move resolved CROSS-SESSION-NOTES items to Resolved section
- [ ] Write spec entry for `SearchRegistrations` endpoint in `registration.api.md`
- [ ] Update `asset.write-model.md` `CompleteMultipartUpload` flow

---

---

## PHASE 3 — POST-PRODUCTION

---

### FEATURE 3.1: Lambda Decomposition and IAM Scoping

**Description:**
The v1 single-Lambda architecture combines all roles under one IAM policy. This feature decomposes the monolith into separate functions with least-privilege IAM roles.

**Priority:** Medium
**Tags:** architecture, iam, security, p3, phase-3

---

#### USER STORY 3.1.1: Decompose Media.Api into separate Lambda functions

**As a** security engineer,
**I want** Ingest API, Query API, and Processing Worker to run as separate Lambda functions with scoped IAM roles,
**so that** a compromise of one function does not grant access to all tenant data across all operations.

**Acceptance Criteria:**
- Ingest API Lambda: `s3:PutObject` on `media-source` and `media-documents` only; scoped by tenant prefix condition
- Query API Lambda: `s3:GetObject` on all three app buckets only; no write permissions
- Processing Worker Lambda: `s3:GetObject` on `media-source`; `s3:PutObject` on `media-renditions` only
- All Lambda functions have independent log groups, IAM roles, and CloudWatch alarms
- CDK produces separate function constructs with no shared role

**Tasks:**
- [ ] Extract `Media.QueryApi` as standalone Lambda function in CDK `media-compute-stack.ts`
- [ ] Extract Processing Worker as standalone Lambda (separate from `Media.Api`)
- [ ] Define scoped IAM role per function with least-privilege S3 and DynamoDB grants
- [ ] Add tenant-prefix condition to all S3 IAM policy statements
- [ ] Remove combined grants from the v1 `MediaApiFunction` construct
- [ ] Update CDK stacks to wire SQS triggers to correct Lambda functions

---

### FEATURE 3.2: Event Versioning

**Description:**
Domain events have no schema version field and no upcasting strategy. Schema changes will break projection rebuild against historical event data.

**Priority:** Medium
**Tags:** event-sourcing, schema-evolution, p3, phase-3

---

#### USER STORY 3.2.1: Implement event schema versioning and upcasting

**As a** platform engineer,
**I want** all domain events to carry a `SchemaVersion` field and the event store reader to support upcasting,
**so that** projection rebuild can safely replay historical events against a newer schema.

**Acceptance Criteria:**
- All domain events carry a `SchemaVersion: int` field (current value = 1)
- Event store reader resolves the appropriate upcaster for each `SchemaVersion`
- Adding an optional field to an event increments `SchemaVersion` and registers a no-op upcaster
- Removing or renaming a field requires a new event type and deprecation of the old type
- Compatibility policy is documented in `system-spec.md`

**Tasks:**
- [ ] Add `SchemaVersion` field to `IDomainEvent` base type
- [ ] Set `SchemaVersion = 1` on all existing domain event types
- [ ] Implement `IEventUpcaster<TFrom, TTo>` interface
- [ ] Implement upcaster registry in event store reader
- [ ] Write compatibility policy in `system-spec.md`
- [ ] Write unit test: replay a v1 event through a v2 upcaster — assert correct output shape

---

### FEATURE 3.3: Operational Tooling — Projection Replay

**Description:**
No projection rebuild tooling exists. A projector bug or read model corruption cannot be remediated without manual DynamoDB surgery.

**Priority:** Medium
**Tags:** operations, replay, p3, phase-3

---

#### USER STORY 3.3.1: Implement projection rebuild CLI

**As an** operator,
**I want** a CLI tool to replay events for a specific tenant and context against a projector,
**so that** a corrupted or stale read model can be rebuilt without manual intervention.

**Acceptance Criteria:**
- CLI accepts: `--tenant`, `--context`, `--from-version`, `--to-version` (optional), `--dry-run`
- Replay reads events from `media-events` event store in sequence order
- Rate-limiting prevents DynamoDB read throttling: configurable `--rcu-limit` parameter
- Idempotent: re-running against an already-current read model produces no changes
- Progress is logged per aggregate stream with estimated time remaining
- `--dry-run` mode logs what would be applied without writing

**Tasks:**
- [ ] Create `Media.ReplayTool` project (console app or Lambda)
- [ ] Implement tenant-scoped event store reader with pagination
- [ ] Implement projector invocation pipeline (reuse existing projector registrations)
- [ ] Add rate-limiting / backpressure against DynamoDB RCU
- [ ] Add `--dry-run` mode
- [ ] Implement progress reporting (events processed, estimated completion)
- [ ] Write integration test: replay a known event sequence — assert read model matches expected state

---

### FEATURE 3.4: Post-Production Infrastructure

**Description:**
CDN for rendition delivery, legal hold for registration documents, and multi-region design are deferred to post-production but require planning before the system reaches significant scale.

**Priority:** Low
**Tags:** infrastructure, cdn, compliance, p3, phase-3

---

#### USER STORY 3.4.1: Add CloudFront CDN for media delivery

**As an** end user,
**I want** renditions and documents to be served via a CDN,
**so that** download latency is minimised regardless of the user's geographic location.

**Acceptance Criteria:**
- CloudFront distribution is configured in front of `media-renditions` and `media-documents` S3 buckets
- Presigned URLs route through the CloudFront domain, not the S3 regional endpoint directly
- CloudFront enforces HTTPS only
- Cache TTL aligns with presigned URL expiry

**Tasks:**
- [ ] Add CloudFront CDK construct for `media-renditions` bucket
- [ ] Add CloudFront CDK construct for `media-documents` bucket
- [ ] Update `StorageKeyGenerator` presigned URL hostname to use CloudFront domain
- [ ] Configure cache TTL and signed URL validity alignment
- [ ] Define rendition URL expiry strategy and client refresh mechanism in spec

---

#### USER STORY 3.4.2: Implement legal hold and retention for Registration documents

**As a** compliance officer,
**I want** registration documents to support legal hold and configurable retention policies,
**so that** the platform meets regulatory requirements for document preservation and right-to-erasure.

**Acceptance Criteria:**
- `media-documents` bucket supports S3 Object Lock in Compliance or Governance mode for legal hold
- Retention period is configurable per tenant via tenant configuration
- Right-to-erasure workflow is documented: how to remove PII from registration documents while preserving audit trail
- Retention policy is defined in `spec/contexts/Registration/context-overview.md`

**Tasks:**
- [ ] Enable S3 Object Lock on `media-documents` bucket in CDK
- [ ] Define per-tenant retention configuration in tenant settings
- [ ] Document right-to-erasure workflow for registration documents
- [ ] Write retention semantics in `Registration/context-overview.md`

---

*Last updated: 2026-05-14*
*Parent document: `spec/reviews/PRODUCTION-READINESS-PLAN.md`*
*Source assessment: Architecture Review Board, 2026-05-14*
