# Production Readiness Implementation Plan
_magiq-media · Generated from Architecture Review Board assessment, 2026-05-14_

Track progress by checking off items as work is completed. Each item links to the review finding that produced it.

---

## Legend
- `[ ]` Not started
- `[x]` Complete
- `[-]` In progress

---

## Phase 1 — Immediate Blockers
> Must be resolved and validated in staging before ANY production traffic. All P0.

---

### Messaging

- [ ] **MSG-1** Remove `var isDevelopment = true;` hardcode in `Startup.cs:58` — replace with `environment.IsDevelopment()` _(RS-01)_
- [x] **MSG-2** Register `AssetUploadConfirmedIntegrationEvent` in `AssetManagementIntegrationEventPublishers.cs` for SNS routing _(RS-04)_
- [x] **MSG-3** Register `AssetValidationPassedIntegrationEvent` in `AssetManagementIntegrationEventPublishers.cs` for SNS routing _(RS-04)_
- [ ] **MSG-4** Validate end-to-end in staging with real SNS/SQS before removing the dev-mode hack — confirm all queues receive expected messages _(RS-01)_
- [ ] **MSG-5** Implement transactional outbox pattern: write pending outbox record in the same `TransactWriteItems` call as the event append _(ES-01, RS-06)_
- [ ] **MSG-6** Implement outbox relay: background process polls outbox table, publishes to SNS, marks records delivered _(ES-01, RS-06)_
- [ ] **MSG-7** Define and add CloudWatch alarm for outbox relay failures / stale undelivered records _(ES-01)_

---

### Processing

- [ ] **PROC-1** Implement image thumbnail generation (Sharp or ImageMagick Lambda layer) in `AssetProcessingWorker.RunProcessingPipelineAsync` _(RS-02)_
- [ ] **PROC-2** Implement image metadata extraction (ExifTool Lambda layer — dimensions, DPI, colour space, bit depth) _(RS-02)_
- [ ] **PROC-3** Implement `AssetValidationWorker` virus scanning — integrate AWS GuardDuty Malware Protection for S3 or ClamAV Lambda layer _(RS-03, SEC-01)_
- [ ] **PROC-4** Implement `ValidationOutcome.VirusDetected` path: hard-delete S3 object BEFORE appending `AssetInfectionDetected` event, move copy to quarantine bucket _(RS-03)_
- [ ] **PROC-5** Wire quarantine bucket to processing worker: ensure quarantine `PutObject` IAM grant is exercised on infected file detection _(RS-03)_
- [ ] **PROC-6** Validate full asset ingestion pipeline end-to-end in staging: upload → confirm → validate → process → `Active` _(RS-02, RS-03)_

---

### Security

- [ ] **SEC-1** Replace `AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()` in `Media.Api/Startup.cs` with environment-scoped allowed origins list _(RS-09, SEC-04)_
- [ ] **SEC-2** Replace `AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()` in `Media.QueryApi/Startup.cs` with environment-scoped allowed origins list _(RS-09, SEC-04)_
- [ ] **SEC-3** Add production CORS configuration to CDK environment config _(SEC-04)_

---

### Domain / Projectors

- [x] **PROJ-2** Implement `RegistrationCountIndexProjector` and provision `folder-registration-index` DynamoDB table _(RS-08, SM-02)_
- [ ] **PROJ-3** ~~Implement `FolderActiveItemCountIndexProjector` and provision `folder-active-item-count-index` DynamoDB table~~ — **correction (2026-06-17): never implemented, incorrectly checked off.** Repo-wide grep of `magiq-media` finds zero hits for `FolderActiveItemCountIndexProjector`/`FolderActiveItemCountIndex`. The CDK table was provisioned but unregistered (orphaned) and has been removed from `write-indexes.construct.ts`. The invariant this would have enforced is instead covered by the `active-items` atomic counter in [ADR-006](../../adrs/ADR-006-uniqueness-registry-hierarchy-invariants.md) — no projector-based replacement is planned _(RS-08, SM-02)_
- [ ] **PROJ-4** Write integration test: attempt to archive a folder with active registrations — assert constraint violation is returned _(SM-02)_

---

## Phase 2 — Pre-Production
> Required before production launch. Mix of P1 and P2.

---

### Messaging

- [x] **MSG-8** Update `DomainEventPublishingMiddleware.InvokeAsync` to call `await next(...)` before `messageBus.PublishAsync(...)` _(RS-12)_
- [ ] **MSG-9** Define DLQ remediation runbook: inspect, root-cause, fix consumer, redrive or discard _(ES-07)_
- [x] **MSG-10** Add GSI to `media-sagas` table on `(SagaType, Status, TimeoutAt)` to replace full-table scan in `SagaTimeoutScanner` _(OPS-02, SC-01)_
- [x] **MSG-11** Update `AssetIngestionTimeoutScanner.ScanPassAsync` — fix counter variable passed by value; use `ref int` or return count _(RS-07)_
- [x] **MSG-12** Add CloudWatch custom metric for saga state distribution (count of sagas per state, published by scanner) _(OPS-02)_
- [x] **MSG-13** Add alarm for sagas in `ProcessingDispatched` or `AwaitingValidation` approaching > 80% of their timeout window _(OPS-02)_
- [x] **MSG-14** Document all saga state timeout durations in `system-architecture.md` (especially `AwaitingValidation` TTL) _(ES-05)_
- [ ] **MSG-15** Uncomment `media-signing` SQS queue in CDK `sqs-queues.construct.ts` _(RS-05)_

---

### Processing

- [ ] **PROC-7** Implement audio metadata extraction (duration, codec, bit rate, sample rate, channels) _(RS-02)_
- [ ] **PROC-8** Implement document metadata extraction (page count for PDFs) _(RS-02)_
- [ ] **PROC-9** Implement archive metadata extraction (file count, compression ratio) _(RS-02)_
- [ ] **PROC-10** Implement `ValidationOutcome.Failed` path (format/size violations) with structured failure reason _(RS-03)_
- [ ] **PROC-11** Implement video processing via MediaConvert: define job template, dispatch async job, handle completion via EventBridge → SQS _(SC-03)_
- [ ] **PROC-12** Define EventBridge rule for MediaConvert job state changes and wire to SQS consumer _(SC-03)_

---

### Security

- [ ] **SEC-4** Implement SecuredSigning webhook HMAC signature validation in `SecuredSigningWebhookHandler` _(RS-05, SEC-02)_
- [ ] **SEC-5** Register `ISecuredSigningApiClient` HTTP client in `SecuredSigningRegistrations.cs` _(RS-05)_
- [ ] **SEC-6** Implement `SigningSessionInitiatedHandler`: call SecuredSigning API, dispatch `LinkSigningSessionCommand` on success _(RS-05)_
- [ ] **SEC-7** Implement `SecuredSigningWebhookHandler` event dispatch: deserialise payload, resolve `TenantId` from `EnvelopeId`, switch on `EventType` _(RS-05)_
- [x] **SEC-8** Add WAF Web ACL to API Gateway with managed rules for common exploits _(missing from spec)_
- [ ] **SEC-9** Scope S3 IAM policies by tenant prefix condition: `"Condition": { "StringLike": { "s3:prefix": ["${aws:PrincipalTag/TenantId}/*"] } }` _(SEC-03)_
- [ ] **SEC-10** Add `Content-MD5` or `x-amz-checksum-sha256` condition to presigned PUT URL for upload integrity verification _(SEC-05)_
- [ ] **SEC-11** Lock HeadObject check to a specific S3 version ID (TOCTOU mitigation) — document this pattern in `system-spec.md` _(SEC-05)_

---

### Storage

- [x] **STOR-1** Add lifecycle rule to `media-renditions` bucket matching the `media-source` tier progression (Standard → StandardIA → GlacierInstant → DeepArchive) _(ST-01)_
- [x] **STOR-2** Define deletion semantics for renditions when source asset is soft-deleted: add to spec and implement in `AssetDomainEventMapper` _(ST-01)_
- [ ] **STOR-3** Add `Content-MD5` / `Content-SHA256` verification in `ConfirmAssetUpload` command handler _(ST-03)_
- [x] **STOR-4** Enable PITR on all DynamoDB read model tables in CDK `read-models.construct.ts` _(OPS-03)_
- [x] **STOR-5** Enable KMS CMK encryption on all DynamoDB tables (enterprise compliance requirement) _(missing from spec)_

---

### Domain / Projectors

- [x] **PROJ-5** Update `AssetDetailProjector` to handle `AssetArchived` and `AssetDeleted` events — update MediaItem role slot to surface `assetStatus: "Archived" | "Deleted"` _(SM-04, CROSS-SESSION-NOTES Session 8)_
- [x] **PROJ-6** Define `hasAccessibleAssets` flag or `AssetsDegraded` state on the MediaItem aggregate/read model _(SM-04)_
- [ ] **PROJ-7** Implement `MediaItemDetailProjector` sequence guard: only apply an event if `AggregateVersion == lastProjectedVersion + 1`; requeue out-of-order messages _(ES-06)_
- [ ] **PROJ-8** Apply sequence guard pattern to all other projectors _(ES-06)_
- [ ] **PROJ-9** Implement `SigningSessionDetailProjector` and `SigningSessionSummaryProjector` (currently marked deferred) _(spec system-architecture.md)_
- [ ] **PROJ-10** Add document signing infrastructure to `Startup.cs` (currently `// todo: Add document signing infrastructure`) _(RS-05)_
- [ ] **PROJ-11** Register `ISigningDomainEvent` in `DomainEventPublishingMiddleware._supportedInterfaces` _(RS-05)_

---

### Spec

- [x] **SPEC-1** Update `asset.write-model.md` `StorageTier` to four values: `Standard | StandardIA | GlacierInstant | DeepArchive` with `Glacier` noted as legacy alias _(RS-10, SM-01)_
- [x] **SPEC-2** Apply `POST /items/{id}/submit-for-review` → `POST /items/{id}/submit` rename in `ChangeRequests/business-scenarios.md` (CROSS-SESSION-NOTES R-03) _(SM-06)_
- [x] **SPEC-3** Resolve all entries in `spec/reviews/CROSS-SESSION-NOTES.md` and move to Resolved _(SM-06, SM-04)_
- [x] **SPEC-4** Write spec entry for `SearchRegistrations` endpoint in `registration.api.md` then remove `// todo: add to the spec.` comment _(RS-11)_
- [x] **SPEC-5** Create `spec/shared/error-catalog.md` — exhaustive list of all `errorCode` values, HTTP status mappings, and producing conditions _(API-05)_
- [x] **SPEC-6** Add missing `CompleteMultipartUpload` command, endpoint, and S3 integration sequence to `asset.write-model.md` and `asset.api.md` _(API-04)_
- [x] **SPEC-7** Fill in the Event Versioning section of `system-spec.md` — `SchemaVersion` field, upcasting strategy, compatibility policy _(ES-02)_
- [x] **SPEC-8** Document all saga timeout durations with rationale in `system-architecture.md` _(ES-05)_
- [x] **SPEC-9** Add CORS policy requirements (per-environment allowed origins) to `system-spec.md` _(SEC-04)_
- [x] **SPEC-10** Add rate limiting specification to `system-spec.md` (per-tenant, per-actor-type tiers, enforcement point) _(API-03)_
- [x] **SPEC-11** Add cursor-based pagination contract to `spec/shared/api-conventions.md` (`search_after` for OpenSearch, `LastEvaluatedKey` token for DynamoDB) _(API-02)_
- [x] **SPEC-12** Define API versioning and deprecation policy in `spec/shared/api-conventions.md` (min supported versions, sunset headers, deprecation notice period) _(API-01)_
- [x] **SPEC-13** Define retention semantics for Registration context: legal hold, right-to-erasure handling _(SM-05)_
- [x] **SPEC-14** Document Registration deletion / archival lifecycle if applicable _(SM-05)_
- [x] **SPEC-15** Create an ADR documenting `AssetProcessingFailed` polymorphic `Status` field pattern _(SM-03)_
- [x] **SPEC-16** Define RTO/RPO targets and DR runbook in `system-spec.md` _(OPS-03)_

---

### API

- [x] **API-1** Implement cursor-based pagination on all list endpoints using `LastEvaluatedKey` token pattern _(API-02)_
- [x] **API-2** Implement `search_after` pagination for OpenSearch queries (replace `from/size`) _(API-02, SC-02)_
- [x] **API-3** Set `dynamic: false` on the `metadata` object in the OpenSearch `media-items` index mapping _(SC-03)_
- [ ] **API-4** Add per-tenant write rate limiting at the application layer or API Gateway _(API-03)_

---

### Observability

- [x] **OBS-1** Implement rich health check at `/healthz`: verify DynamoDB reachability, SNS connectivity, S3 access _(OPS-01)_
- [ ] **OBS-2** Add structured log enrichment for `ProjectorType` and `EventType` in projection pipeline _(OPS-01)_
- [ ] **OBS-3** Define and document DLQ remediation runbook (inspect → root-cause → fix → redrive or discard) _(ES-07)_
- [ ] **OBS-4** Add CloudWatch dashboard: DLQ depths, Lambda error rates, DynamoDB throttle counts, saga state distribution _(OPS-02)_

---

### Infrastructure / Deployment

- [ ] **INF-1** Define Lambda aliases and weighted traffic routing for canary/blue-green deployments _(DEP-03)_
- [ ] **INF-2** Write rollback runbook targeting RTO < 5 minutes for critical Lambda deployment failures _(DEP-03)_
- [ ] **INF-3** Define DynamoDB schema migration strategy: additive-only policy, table rebuild procedure, zero-downtime GSI backfill _(DEP-02)_
- [ ] **INF-4** Configure API Gateway throttling and usage plans per actor type _(API-03)_
- [ ] **INF-5** Enable `deletion_protection` on all read model DynamoDB tables _(OPS-03)_
- [ ] **INF-6** Enable PITR on `media-sagas` and `media-events` (already done in CDK) — confirm all read model tables also have PITR _(OPS-03)_

---

### Testing

- [ ] **TEST-1** Write domain unit tests for `Asset` aggregate — all invariant paths (e.g. wrong-state transitions, FailureCategory mismatch, multipart guard) _(RS-13)_
- [ ] **TEST-2** Write domain unit tests for `MediaItem`, `Collection`, `Folder`, `Registration`, `ProcessingJob` aggregates _(RS-13)_
- [ ] **TEST-3** Write command handler integration tests for `UploadAsset` → `ConfirmAssetUpload` → event store write _(RS-13)_
- [ ] **TEST-4** Write command handler integration tests for `AssetValidationWorker` virus scan paths (pass / fail / virus detected) _(RS-13)_
- [ ] **TEST-5** Write projector idempotency tests: apply same event twice, assert no duplicate state _(ES-04)_
- [ ] **TEST-6** Write saga flow tests: `AssetIngestionSaga` happy path and timeout compensation _(RS-13)_
- [ ] **TEST-7** Write integration event catalog alignment unit tests per module (asserts all `IntegrationEvent`-derived types are registered — already specified in the spec) _(spec system-architecture.md)_
- [ ] **TEST-8** Write end-to-end integration test: full upload → validate → process → `Active` pipeline _(RS-02)_
- [ ] **TEST-9** Write PERM-1, PERM-2, PERM-3 security scenario tests (cross-owner write, system-only endpoint, reviewer self-approval) _(security-scenarios.md)_
- [ ] **TEST-10** Write DLQ redrive test: assert a failed projection is correctly replayed after consumer fix _(ES-07)_

---

## Phase 3 — Post-Production Improvements
> Acceptable after controlled production rollout. Schedule into sprint backlog as capacity allows.

---

### Architecture

- [ ] **ARCH-1** Decompose single Lambda (`Media.Api`) into separate Ingest API, Query API, and Processing Worker Lambda functions _(DEP-01, SEC-03)_
- [ ] **ARCH-2** Apply scoped IAM roles per decomposed function (Ingest: source + documents write; Query: all three buckets read; Processing: source read + renditions write) _(SEC-03)_
- [ ] **ARCH-3** Implement archive fan-out as a checkpointed saga with batch size cap — replace current unbounded `CollectionArchivedEventHandler` _(SC-02, SM-04)_
- [ ] **ARCH-4** Replace `StorageTierTransitionScanner` polling model with DynamoDB Streams or EventBridge Pipes _(ST-02)_
- [ ] **ARCH-5** Rate-limit `StorageTierTransitionScanner` with exponential backoff and configurable segment count _(ST-02)_

---

### Storage

- [ ] **STOR-6** Add CloudFront CDN in front of rendition and document presigned URL delivery _(missing from spec)_
- [ ] **STOR-7** Define presigned URL expiry strategy and client URL refresh mechanism _(missing from spec)_
- [ ] **STOR-8** Implement legal hold and right-to-erasure handling for Registration documents _(SM-05)_
- [x] **STOR-9** Add `AbortIncompleteMultipartUploads` lifecycle rule to `media-documents` and `media-renditions` buckets _(API-04)_

---

### Observability

- [ ] **OBS-5** Implement projection rebuild tooling: `dotnet replay --tenant={id} --context={context} --from-version={n}` with rate limiting and progress reporting _(ES-03, OPS-01)_
- [ ] **OBS-6** Define and build DLQ replay Lambda for automated DLQ redrive per queue _(ES-07)_
- [ ] **OBS-7** Implement load test suite: Lambda cold start under concurrency, DynamoDB peak write throughput, OpenSearch bulk indexing _(OPS-01)_

---

### Spec

- [ ] **SPEC-17** Define tenant onboarding and offboarding lifecycle (creation, suspension, data export, purge) _(missing from spec)_
- [ ] **SPEC-18** Define DynamoDB per-table capacity planning estimates and auto-scaling thresholds _(SC-01)_
- [ ] **SPEC-19** Design multi-region strategy: cross-region event store replication, active-passive failover _(OPS-03)_
- [ ] **SPEC-20** Define audit log retention policy: storage location, retention period, query surface _(missing from spec)_

---

### Event Versioning

- [ ] **EV-1** Add `SchemaVersion` field to all domain events _(ES-02)_
- [ ] **EV-2** Implement upcaster registry in event store reader: map old schema versions to current shape _(ES-02)_
- [ ] **EV-3** Document event compatibility policy (additive-safe changes, breaking change procedure) in `system-spec.md` _(ES-02)_

---

*Last updated: 2026-05-14*
*Source: `spec/reviews/` — Production Readiness Assessment*
