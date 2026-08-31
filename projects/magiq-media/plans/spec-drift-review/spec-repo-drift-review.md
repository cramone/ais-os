---
id: MM-022
type: review
project: magiq-media
workstream: spec-drift-review
raised-by: []
status: findings-agreed
outcome: pending
todo-id: ac8b9c69-85b3-53d3-b2ea-9f36205e4dc6
created: 2026-08-21
exception: a review living in plans/ deliberately — it is its own working checklist, and splitting it would separate the findings from the boxes tracking them. SKILL.md § Known exceptions #1.
---

> **Backfilled into the review cycle 2026-08-31 as MM-022.** 58 of 213 findings still open. The ✓ column in the file is the working checklist. Its 154 closed findings live in Archive/spec-repo-drift-review-completed.md; the id sets do not overlap.

# Spec ↔ Repo Drift Review — open findings

_magiq-media · original review 2026-08-21 · **split 2026-08-24** — resolved findings moved to
[`Archive/spec-repo-drift-review-completed.md`](./Archive/spec-repo-drift-review-completed.md)_

**58 findings remain open** of the 213 distinct findings the review has carried. *(Updated 2026-08-24:
X-7.2 closed while reorganising the plans folder.

X-4.10 closed; X-4.11, X-4.12 and X-4.13 opened by it and its verification sweep. X-9.6's documentation
half closed and its code gap narrowed; X-9.7 opened by that pass and closed the same day. X-9.4 closed by
finally running its test — which failed, opening and closing **X-9.8**, a byte-order bug in
`GuidFactory` that had left every id in the system unsortable. All three fixes are written but **not yet
executed**; X-9.8's also needs a platform package release.)* The other 149 are
resolved and live in the archive file, together with the full session log for every pass. Nothing was
deleted in the split — every finding is in exactly one of the two files, and the id sets do not overlap.

*(The review's own running total said 223. That counts §J's 15 rows twice — §J is a cross-cutting view of
findings that also sit in their module sections. 208 is the distinct count.)*

**Scope of the original review:** `D:\source\github\magiq-media\docs\spec\**` (22,077 lines, 7 bounded
contexts, 13 aggregates) and `docs\adrs\**` against `src\modules\**` (~1,700 `.cs` files, 114 endpoints),
`src\hosts\**`, `.github\workflows\`, plus `cdk-magiq-media` and `aspnetcore-platform` where a claim
crossed a repo boundary. Contracts and behaviour, not naming or formatting. Authentication and
edge-authorization findings were removed 2026-08-21 and are deferred to a separate auth plan.

**Progress tracking:** the leading ✓ column is the working checklist — tick a row (`☐` → `☑`) as it lands,
and move the row to the archive file when the pass that closed it is written up.

---

## Where the open work sits

| Section | Open | Character of what's left |
|---|---|---|
| [B. AssetManagement](#b-assetmanagement) | 1 | One Low error-code hygiene item |
| [C.6 BulkImportJob](#c6-bulkfolderimportjob--bulkmediaimportjob) | 3 | Two published aggregates with **no code at any layer** |
| [G. Processing](#g-processing) | 8 | Untouched — the module has had no remediation pass |
| [H. DocumentSigning](#h-documentsigning) | 11 | Untouched — a specced bounded context that is a skeleton |
| [I.1 Hosts](#i1-hosts) | 8 | Deployment topology claims; X-1.8 is a live cost defect |
| [I.3 Integration events](#i3-integration-event-publishing) | 4 | The outbox decision (X-3.1), deferred by decision |
| [I.4 Tables & infra](#i4-tables--infra) | 7 | Queue topology, quarantine, and the X-4.11/4.12/4.13 tail of the key re-key |
| [I.5 Deployment](#i5-branching--deployment) | 5 | X-5.1 is the prod-deploy guard gap |
| [I.7–I.8 Links & stale refs](#i7-plans-folder) | 4 | Doc-only. X-7.2 closed 2026-08-24 by the plans reorganisation |
| [I.9 Platform SDK](#i9-platform-sdk-conventions) | 3 | X-9.6 docs closed and code gap narrowed; X-9.4 closed by running its test, which opened and fixed X-9.7 and X-9.8 — all 2026-08-24 |
| [I.10 Error catalog](#i10-error-catalog) | 4 | Catalog/code divergence and OpenAPI header coverage |

### Triage — refreshed 2026-08-24

The original §L triage was written before four modules were remediated and is now in the archive. This
replaces it.

1. **Highest value, not yet started** — **§G Processing (8)** and **§H DocumentSigning (11)** are the only
   two modules that have had no remediation pass at all. Between them they are a third of what's left.
   Processing has real defects (P-2 duplicate jobs, P-3 bypassed jobs stuck `Queued` — the spec now documents that gap honestly, which is not the same as closing it); DocumentSigning is
   a documentation decision before it is a code one — see the note under §H.
2. **Live defects with production consequences** — *(**X-9.7**, every folder-to-folder media-item move
   returning a false 409, was opened and fixed 2026-08-24 — pending a test run)*, **X-1.8** (storage tiering never runs;
   every original stays in S3 Standard), **X-5.1** (a `v*` tag in the CDK repo deploys to prod with no
   guard), **X-9.6** (orphaned name reservations — 23 of 25 reservation call sites uncompensated), **X-4.7** (infected originals are
   never quarantined).
3. **Decisions Chase owes, not fixes** — **X-3.1** outbox adoption (deferred by decision 2026-08-21),
   **X-1.10** client-asserted upload confirmation. *(**X-4.10** version key shape was decided 2026-08-24 —
   re-key — and the code change has landed; it is now a rotation, not a decision.)*
4. **Publish-contract honesty** — **BI-1/2/3** and **DS-1…12**: caveat or relocate the spec files that
   describe absent code, so published contracts stop reading as shipped.
5. **Doc-only sweep** — §I.7, §I.8, X-3.3/3.4, X-4.4/4.5/4.9, X-5.3/5.4/5.5, X-9.2, X-10.x. No code risk.

---

### Fix-first list — one row still open

Seven of the eight fix-first items are closed and in the archive. This one was deferred by decision, not by oversight.

| ✓ | Rank | Finding | Why it's first |
|---|---|---|---|
| ☐ | 6 | **Integration events bypass the outbox entirely** (X-3.1) | Zero `IOutbox` usages. No atomicity between event-store append and SNS publish; a crash between the two silently drops the event. Breaks the platform SDK's one hard messaging constraint. **Deferred by decision 2026-08-21 — revisit later.** |

---

## B. AssetManagement

_34 findings, 33 closed. One remains._

| ✓ | # | Sev | Area | Spec says | Code does | Spec ref | Code ref |
|---|---|---|---|---|---|---|---|
| ☐ | AM-34 | Low | Errors | Every published `errorCode` is a constant, not a literal | *Added 2026-08-23 during AM-33.* `BulkConfirmAssetUploadHandler` raises `DeclaredSizeExceeded` and `ProfileLimitExceeded` as **string literals**; neither exists in `AssetErrorCodes`. Both are published in `asset.api.md § bulk-confirm` and are client contract. Same shape as the bug AM-33 fixed, one layer down — nothing ties the raise site to the published name. `BulkInitiateAssetUploadHandler`'s `DuplicateAssetId`, `QuotaExceeded` and `PersistenceFailed` are the same | `asset.api.md:891-892` | `BulkConfirmAssetUploadHandler.cs:176,191` |

**Verified aligned (AssetManagement):** all 12 route paths/verbs; `/v1` correctly wired globally via `Versioning.PrependToRoute` + `Version(1)` (so bare route strings are *not* a finding anywhere in this review); flat URLs; list envelope exactly `{items, pageSize, nextPageToken}`; `mediaItemId` on `GET /v1/assets`; `TenantId` from `IExecutionContext` on every command; 11/11 integration event contracts; aggregate guards for `Archive`/`Delete`/`Promote`/`Release`/`Bypass`/`Tag`; `ProjectedVersion` set on every projector write.

---

## C. Catalog

_Largest module, six specced aggregates, four implemented. C.1–C.5 are closed and archived; what remains is the two aggregates with no implementation at all._

### C.6 BulkFolderImportJob / BulkMediaImportJob

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☐ | BI-1 | High | Two full aggregates — write-model, read-model and API specs across 9 routes | **Nothing exists at any layer.** Repo-wide grep for `ImportJob`, `BulkFolderImportWorker`, `BulkMediaImportWorker`, `import-jobs` across `src/**/*.cs` → **0 hits**. No aggregate, commands, events, endpoints, read models, projectors or worker | 6 spec files + `bulk-operations.md §Async Bulk Import Jobs` |
| ☐ | BI-2 | High | `media-bulk-folder-imports` / `media-bulk-media-imports` SQS queues; shared `media-bulk-import-job-items` table; `media-bulk-import-inputs` S3 bucket | None provisioned. CDK carries two comment placeholders naming the queues as future work | `BULK-IMPORT-SPEC-UPDATES.md` / `cdk .../sqs-queues.ts:77-78` |
| ☐ | BI-3 | Med | Import-job pageSize exceptions (100/500 and 50/200) | Moot — but `api-conventions.md §Pagination` documents caps for routes that don't exist, which reads as implemented to anyone auditing the shared conventions in isolation | `api-conventions.md §Pagination` |

> `CLAUDE.md`'s "bulk import **workers** deferred" phrasing materially understates this. The workers aren't the gap; the aggregates are.

---

## G. Processing

_10 findings, 2 closed. **This module has had no remediation pass** — the eight below are as first written on 2026-08-21. (P-10 was closed by the §J doc-only sweep, not by a Processing pass.)_

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☐ | P-2 | High | Handler must call `GetByAssetIdAsync` first and no-op if a job exists — "handles duplicate SQS delivery without creating duplicate jobs" | `GetByAssetIdAsync` is **not on the interface**. Handler creates unconditionally and the caller mints a fresh `ProcessingJobId.New()` per delivery — duplicate delivery creates a second job | `processingjob.write-model.md §Command Handlers` / `CreateProcessingJobCommandHandler.cs:19-26` |
| ☐ | P-3 | High | `Queued → Bypassed [terminal]`; `ProcessingJobBypassed` is a first-class event | Neither projector handles it. **A bypassed job stays `Queued` in both read models permanently** | `write-model.md §Status Lifecycle` / `ProcessingJobSummaryProjector.cs:11-15` |
| ☐ | P-4 | Med | `ListProcessingJobsForAssetIdHandler` listed | Query record and GSI schema exist; **no handler class** — the query cannot be dispatched | `read-model.md §Query Handlers` / `Queries/ListProcessingJobsForAssetId/` |
| ☐ | P-5 | Med | `AssetIngestionSaga` created on `AssetValidationPassed` (**not** on `ProcessingJobCreated`) | Created on `ProcessingJobCreated`; `AssetValidationPassed` only advances it | `write-model.md §Saga Relationship` / `AssetIngestionSaga.cs:20-27` |
| ☐ | P-6 | Med | Per-content-type `TimeoutAt` (Video = 4h) | Two-phase budget: global 15-min validation, then profile timeout or 240-min default | `write-model.md §Saga Relationship` / `AssetIngestionTimeoutOptions.cs:24-32` |
| ☐ | P-7 | Med | Saga → `Complete` on `ProcessingJobSucceeded`/`Failed` | Five states incl. undocumented `Bypassed`; terminal transitions driven by **integration** events from AssetManagement, not the ProcessingJob domain events | `write-model.md §Saga Relationship` / `AssetIngestionSagaStatus.cs` |
| ☐ | P-8 | Med | `StartProcessingJobCommand` dispatched by the Worker; `FailProcessingJobCommand` by the timeout scanner; no `BypassProcessingJob`/`RecordProcessingJobScanResult` in the surface table | Start/Bypass are dispatched by the saga; the validation-timeout path dispatches `FailAssetProcessingCommand` on the **Asset** aggregate. Both "missing" commands exist | `processingjob.api.md §Internal Command Surface` / `AssetIngestionTimeoutScanner.cs:158,173-177` |
| ☐ | P-9 | Low | `RenditionResultDto(… SizeBytes)` | Field is `FileSizeBytes` in the read model, the domain VO **and** the integration-event contract | `read-model.md §Embedded Types` / `RenditionResultDto.cs:11` |

**Aligned:** no HTTP endpoints (spec is correct); the `Queued→Running→Succeeded|Failed` transitions, the `Bypassed` idempotent no-op, and the timeout-recovery path all match spec exactly; failure taxonomy matches the consolidated ADR.

---

## H. DocumentSigning

_12 findings, 1 closed. **This module has had no remediation pass.**_

**Quantified gap: 27 non-generated `.cs` files across 5 projects — the events-and-value-objects skeleton only.** Present: 9 domain event records, 7 value objects, 2 read models, 1 projector, 2 DI extensions, 4 service interfaces. **Absent: the aggregate, all 9 commands, all 9 handlers, the repository, all 12 endpoints, 2 of 3 projectors, all 3 query handlers, the saga, the timeout scanner, and the webhook implementation.**

| ✓ | # | Sev | Spec says | Code does | Ref |
|---|---|---|---|---|---|
| ☐ | DS-1 | High | 12 routes | **Zero endpoints.** No `DocumentSigning.*.Endpoints` project; neither `Api` nor `QueryApi` references the module at all | `documentsigningsession.api.md §Route Structure` / `Api.csproj`, `QueryApi.csproj` |
| ☐ | DS-2 | High | Webhook with HMAC-SHA256 over raw body, `X-SecuredSigning-Signature`, SSM secret, envelope→tenant lookup | Handler logs and returns **501 "not yet implemented"**. No HMAC, no header read, no SSM, no lookup. Also not routed | `api-conventions.md:426-437` / `SecuredSigningWebhookHandler.cs:29-41` |
| ☐ | DS-3 | High | `POST /v1/items/{id}/signing-sessions` is one of only two endpoints allowed to return 202 | Endpoint does not exist — the reserved-202 contract is unimplementable | `api-conventions.md:365` |
| ☐ | DS-5 | High | `ProjectedVersion` dedup guard on all writes | Set only on the initial insert. All 8 update paths use `current with { … }` and never touch it — pinned at v1, so duplicate delivery is unguarded | `read-model.md`; `CLAUDE.md §Key conventions` / `SigningSessionDetailProjector.cs:53-114` |
| ☐ | DS-6 | High | Three projectors incl. `SigningEnvelopeLookupProjector` (the webhook's tenant-resolution path) | Only the detail projector exists. The other two are an inline `// todo`. `media-signing-sessions` has a schema nothing writes; `media-signing-envelope-lookup` has neither | `read-model.md §Projection Handlers` / `ServiceCollectionExtensions.cs:78-82` |
| ☐ | DS-7 | High | 9 methods, 9 commands, 9 events on the aggregate | **Aggregate class does not exist.** `WriteModel` holds 4 files, all interfaces/DTOs. The events exist but nothing raises them | `write-model.md §Methods` / `DocumentSigning.WriteModel/Services/` |
| ☐ | DS-8 | High | `DocumentSigningSaga` coordinates the checkout lock and compensates via `ForceReleaseCheckout` | **The class does not exist anywhere in `src/` or `tests/`.** `SagaOrchestrator.DocumentSigning` registers one handler whose body is a TODO block | `write-model.md §Purpose` / `SecuredSigningRegistrations.cs:62-65` |
| ☐ | DS-9 | High | `SagaTimeoutScanner` scans `AwaitingSigners` for expiry | Not implemented. `TimeoutScanner` registers only the asset-ingestion and lease-expiry scanners; the DocumentSigning row survives as an XML `<description>` self-annotated "(not yet implemented)" | `read-model.md §Status Lifecycle` / `TimeoutScanner/ServiceCollectionExtensions.cs:34-35` |
| ☐ | DS-10 | Med | Summary and detail both carry `OwnerId` | Detail has **no `OwnerId`** — the field every "caller is session owner" check depends on. Summary has it but is never written | `read-model.md` / `SigningSessionDetailReadModel.cs:8-27` |
| ☐ | DS-11 | Med | Seven named error codes | `error-catalog.md` has **no DocumentSigning section**; six of seven are undefined and unimplemented | `write-model.md §Invariants` vs `error-catalog.md` |
| ☐ | DS-12 | Low | `api.md` route structure is post-migration flat | `scenarios.md:76,79` and `context-overview.md` still name the pre-migration surface (`POST /media-items/{id}/media-signing-sessions` → **201**, `/webhooks/secured-signing`). Code implements none, so no `/signing/` prefix survives | `documentsigningsession.scenarios.md:76,79` |

> **The documentation problem here is sharper than the code gap.** `write-model.md` and `read-model.md` both self-flag that the aggregate doesn't exist. `api.md` and `context-overview.md` carry **no such caveat** and read as shipped contract.

## I. Architecture, hosts & cross-cutting

### I.1 Hosts

| ✓ | # | Sev | Doc says | Reality | Ref |
|---|---|---|---|---|---|
| ☐ | X-1.2 | Med | `SagaOrchestrator.DocumentSigning` is a deployable host | Built and pushed to ECR every commit but **nothing deploys it** — no Lambda, no queue. CDK has a comment placeholder | `system-architecture.md:67` / `magiq-media-stack.ts` |
| ☐ | X-1.3 | Med | `Projectors.Search` deployable; OpenSearch is a first-class read store | Deployed only behind `--context deploySearch=true`, which **no workflow, config file or `cdk.json` entry ever passes**. Projectors.Search and the OpenSearch domain are not deployed in any environment — while the image is built every commit | `CLAUDE.md §Hosts` / `magiq-media-stack.ts:96,175,510` |
| ☐ | X-1.4 | Med | "`media-processing` SQS → Processing Worker Lambda (host not yet deployed)" | It **is** deployed | `system-architecture.md:53` / `magiq-media-stack.ts:564-576` |
| ☐ | X-1.5 | Med | "SecuredSigning Adapter" is a service with a `media-signing` queue | Neither queue nor Lambda exists. The webhook handler lives in the undeployed signing orchestrator | `system-architecture.md:54`; `service-boundaries.md:22` |
| ☐ | **X-1.8** | **High** | Storage tiering is driven by a `tier-policy=managed` object tag applied at assign time by `AssetAssignedToRoleEventHandler` | **The handler is never invoked.** It exists, is DI-registered, reaches `PutObjectTagging`, and has its IAM grant provisioned — but `AssetAssignedToRoleIntegrationEvent` is **not** among the ~25 event types `ConsumerRegistrations.AddIntegrationEventMessageHandlers` subscribes, so the bus has no route to it. Nothing is ever tagged, so the originals lifecycle rule (tag-filtered) matches nothing and **every original stays in S3 Standard forever**. The entire S12 cost design is inert · *Found 2026-08-24* | `EventConsumers/ConsumerRegistrations.cs`; `AssetAssignedToRoleEventHandler.cs`; `magiq-media-stack.ts:549` |
| ☐ | **X-1.9** | Med | `system-spec.md` §Rendition Deletion and `magiq-media-stack.ts:568-570`: the Processing Worker deletes rendition objects on `media.asset.archived` / `media.asset.deleted` | **No such code.** `ProcessingRegistrations.cs:49` registers exactly one message handler — `AssetUploadConfirmedIntegrationEvent` — and `AssetProcessingWorker` has no delete path. Renditions of archived and deleted assets are never cleaned up. The CDK comment asserts it too, so both repos document a cleanup that does not exist · *Found 2026-08-24* | `ProcessingRegistrations.cs:49`; `system-spec.md §Rendition Deletion` |
| ☐ | **X-1.10** | Med | `adrs/asset-storage-and-processing.md:31` and `service-boundaries.md`: `s3:ObjectCreated:Put` on the originals bucket → SNS → SQS → Ingest API handler dispatches `ConfirmAssetUpload` | **Never built.** `apiFn` has no `addEventSource` and the stack declares no S3 bucket notification. `ConfirmAssetUpload` is an ordinary client-called HTTP endpoint — the upload is confirmed because the *client* says so, not because S3 did. That is a materially weaker guarantee than the ADR describes and worth a decision, not just a doc fix · *Found 2026-08-24* | `magiq-media-stack.ts:381-431`; `asset-storage-and-processing.md:31` |
| ☐ | X-1.7 | Med | `DocumentSigningSession` listed as a core aggregate | No aggregate class. `domain-model.md:327` does flag it "⚠️ partially implemented"; both `CLAUDE.md` files list it flatly | `bounded-context.md:56,157` |

### I.2 JWT replay detection

_Removed 2026-08-21 — deferred to the auth plan. Numbering left intact so existing references to X-3.x onward still resolve._

### I.3 Integration event publishing

| ✓ | # | Sev | Doc says | Reality | Ref |
|---|---|---|---|---|---|
| ☐ | X-3.1 | High | Platform SDK hard rule: "Never publish integration events directly — always `IOutbox` or `IApplicationBus`. The outbox guarantees at-least-once delivery **atomically with the aggregate write**" | The app publishes straight to SNS inline in the handler pipeline. **Zero `IOutbox` usages in `src/`.** No atomicity between event-store append and SNS publish — a crash between them silently drops the integration event. The SDK's outbox implementation exists and is unused | `aspnetcore-platform/CLAUDE.md` Design Constraint #4 / `DomainEventPublishingMiddleware.cs:20` ✅*verified* |
| ☐ | X-3.2 | Med | — | `Api.csproj` references `Magiq.Platform.Messaging.Outbox` **and** `.Outbox.DynamoDb`; neither is wired. Reads as if the outbox is in play | `Api.csproj:37-38` |
| ☐ | X-3.3 | Med | Per-module **`*IntegrationEventPublisher`** classes implementing `IDomainEventHandler<T>` do the translation | Translation is done by **`*IntegrationEventMapper`** (`IDomainEventMapper<T>`) in each module's WriteModel. The files actually named `*IntegrationEventPublishers.cs` live in the `Api` host and are pure DI registration. Searching per the spec finds the wrong file in the wrong project. (The live ADR `persistence-and-eventing.md:70` is correct; the architecture specs and `CLAUDE.md` are not) | `bounded-context.md:143` / `AssetIntegrationEventMapper.cs:9-21` |
| ☐ | X-3.4 | Low | ADR-005 cited as the authority | ADR-005 is a 5-line redirect stub (superseded 2026-07-08). Live text is `persistence-and-eventing.md §Integration Events`. `CLAUDE.md` still cites "(ADR-005)" | `ADR-005-*.md:1-5` |

> X-3.1 is the one hard SDK constraint the application materially breaks. Whether to adopt the outbox or formally amend the platform SDK's stated rule is an architecture decision, not a bug fix — but the current state, where an ADR says one thing and the SDK it depends on forbids exactly that, should not persist undocumented.

### I.4 Tables & infra

| ✓ | # | Sev | Doc says | Reality | Ref |
|---|---|---|---|---|---|
| ☐ | X-4.4 | Med | Queues `media-document-signing`, `media-signing`, and the two bulk-import queues in the topology diagram | None provisioned. Bulk-import queues are acknowledged deferred in `CLAUDE.md`; the other two are not flagged in `system-architecture.md` itself | `system-architecture.md:54,67-69` |
| ☐ | X-4.5 | Med | `media-processing` SQS drawn hanging off **`media-domain-events`** | It subscribes to **`media-integration-events`** | `system-architecture.md:53` / `sqs-queues.ts:174` |
| ☐ | X-4.14 | **Med** | — | *Opened 2026-08-25 during the `bounded-context.md` diagram pass — **X-4.4/X-4.5 are wider than `system-architecture.md`.*** `bounded-context.md` carried the same wrong wiring in **three** places (Transport Topology diagram, Queue Topology diagram, Queue Configuration table) and added two errors of its own: `media-sagas` on the domain topic, and `media-projector-search` **absent entirely**. **All three are now corrected in `bounded-context.md`** against `sqs-queues.ts`; this row tracks the remaining copies. Actual wiring: `media-domain-events` → `media-projector`, `media-projector-search` (deferred until `deploySearch=true`). `media-integration-events` → `media-processing` (filter `media.asset.upload-confirmed`, vis 1800 s), `media-sagas` (5-type allowlist, vis 300 s), `media-cross-module-events` (intra-BC allowlist, DLQ 7 d). **No `media-signing` queue exists.** Visibility timeouts in the spec (60 s / 30 s) are both **300 s** in CDK — the CDK comments that a value below the Lambda timeout causes spurious redeliveries. **Sweep `system-architecture.md` and `system-spec.md` for the same three claims.** | `sqs-queues.ts:155-245` / `bounded-context.md` ✅ / `system-architecture.md` ☐ / `system-spec.md` ☐ |
| ☐ | X-4.16 | **High** | — | *Opened 2026-08-25 by W13's code check — **a live instance of X-4.15, found within a day of raising it.*** **`media.recordtype.published` and `media.recordtype.deprecated` are not on the `media-cross-module-events` filter allowlist**, so neither is ever delivered. The allowlist's `// Metadata (RecordType)` comment sits above `media.profile.published` / `media.profile.deprecated` — which are **MediaProfile** events (Catalog). Whoever wrote it believed those two lines covered RecordType; they cover MediaProfile, and RecordType is missing entirely. **Consequence:** `EventConsumers/ConsumerRegistrations.cs:104-105` registers handlers for both events, and Catalog implements `RecordTypePublishedEventHandler`, `RecordTypeDeprecatedEventHandler` and `RecordTypeVersionDetailIndexProjector` — **none of which can ever run.** Catalog's RecordType version reference model is never maintained, so a newly published version never appears in the index `MediaProfile` validates pins against, and **a deprecated RecordType is never marked deprecated — so `MediaProfile` will keep accepting pins to it.** Fails silently: no error, no DLQ message, no alarm. **Fix is two lines in `sqs-queues.ts`**, but verify the handlers behave once they start receiving a backlog. | `sqs-queues.ts:218-220` / `ConsumerRegistrations.cs:104` / `RecordTypeDeprecatedIntegrationEvent.cs:15` |
| ☐ | X-4.17 | Med | — | *Opened 2026-08-25 by W16's code check.* **`AssetJobIndexProjector` writes `Status = Running` on both terminal events.** `ProcessingJobSucceeded` and `ProcessingJobFailed` each set `ProcessingJobStatus.Running` on `AssetProcessingJobIndex`, so a row **never reaches `Succeeded` or `Failed`** — once a job starts, its index row reads `Running` for good. **Nothing is broken today**: both consumers use the index only for the `AssetId → JobId` lookup (`AssetIngestionSaga` reads `job.JobId`; `AssetIngestionTimeoutScanner` reads the key), and the `Status` the scanner filters on is the **saga's**, in `media-sagas`. `StartedAt` is likewise written and never read. **It is a trap, not a live defect** — the field is named `Status`, typed `ProcessingJobStatus` and sits beside a `JobId`, so the first consumer to reach for it will get a wrong answer silently. Either fix the two writes or drop the field; leaving it as-is is the worst of the three. *(This is also what the DDD-T12 truncation was about to document as "Mirrors current job status" — the lost sentence would have enshrined the false claim.)* | `AssetJobIndexProjector.cs:35-52` / `AssetIngestionSaga.cs:157-167` |
| ☐ | X-11.2 | Med | `Folder.cs` / `Collection.cs` comments above `Archive`: archive "fans out `isAccessible = false` to all direct items via `FolderItemsIndex` GSI"; a `FolderHasActiveChildren` check blocks archive; the registration check is a "non-blocking warning" | *Opened 2026-08-25 by W26.* **All three false, in the aggregate code comments.** The cascade is **write-side and synchronous** — `ArchiveFolderHandler` awaits `FolderArchiveFanOutWorker` inside the HTTP request, dispatching real `ArchiveFolderCommand`/`ArchiveMediaItemCommand` per node. There is **no `FolderItemsIndex` GSI and no projector that flips `isAccessible` on folder archive** (`IsAccessible` is written only by `AssetAccessibilitySummaryProjector`, driven by asset infection/deletion). **`FolderHasActiveChildren` is not a real error code.** The registration check is **blocking** (422 `FolderHasActiveRegistrations`). **Note the direction: here the spec file is right and the code comments are wrong** — the reverse of most X-findings, so a reader trusting "the code is the source of truth" is misled by comments that are not code. | `Folder.cs` (comment above `Archive`) · `Collection.cs:94` · `FolderArchiveFanOutWorker.cs` |
| ☐ | X-11.3 | Med | — | *Opened 2026-08-25 by W26.* **The folder archive cascade has no resume path and swallows every descendant failure.** `DispatchArchiveFolderAsync`/`DispatchArchiveMediaItemAsync` log a warning and continue, and `ArchiveDescendantsAsync` returns `Task` rather than a `Result` — so **the target folder is archived even if every descendant failed, and the caller still receives `204`.** A thrown exception (throttle, Lambda timeout) leaves an arbitrary prefix of the subtree archived and durably committed with nothing to roll back to. **Partial completion is not observable** — read models carry only per-folder `IsArchived`, and the completion log line reports items *attempted*. Separately, recursive re-entry means each dispatched command re-runs the whole cascade for its own subtree, so a **successful** archive emits a burst of `Failed to archive…` warnings and does `O(Σ subtree sizes)` work. Also: depth counters are never decremented on archive, and the name reservation is released *before* `SaveAsync`. | `FolderArchiveFanOutWorker.cs` · `ArchiveFolderHandler.cs` |
| ☐ | X-11.4 | Low | — | *Opened 2026-08-25 by W30.* **Two ProcessingJob read models are built and paid for with no reader.** `media-processing-job` and `media-processing-jobs` are projected on every job event and the `AssetByProcessingJobIndex` GSI is maintained — but **`QueryApi.csproj` does not reference Processing at all** and `QueryApi/Startup.cs` never calls `AddProcessingReadModelQueries()`. `GetProcessingJobByIdQuery`'s handler is registered only in the `Api` host, which has no Processing endpoints to invoke it; `ListProcessingJobsForAssetIdQuery` **has no handler registered at all** despite its index schema being provisioned. Processing is also the only module with neither a `*.WriteModel.Endpoints` nor a `*.ReadModel.Endpoints` project. Either expose them through `QueryApi` or stop projecting them — the current state costs write capacity on every processing event for nothing. | `QueryApi.csproj` · `QueryApi/Startup.cs` · `Processing.ReadModel.Infrastructure/ServiceCollectionExtensions.cs` |
| ☑ | X-11.6 | **High** · **fixed 2026-08-27** | ~~Both saga handler layers log *"message will be retried"*~~ | **☑ Fixed 2026-08-27.** The fix is a rule, now written into `docs/spec/shared/saga-patterns.md` § *Failure handling* and applied to all five pairs. **The rule:** *a saga signals a handled outcome by returning, never by throwing.* Every outcome `AssetIngestionSaga` recognises — no active saga, already terminal, unexpected status, no ProcessingJob projection — is an early `return`, so **no handled outcome raises an exception** and there is therefore no exception *type* that means "handled". Hence: the inner `IIntegrationEventHandler` **catches nothing** (and no longer takes an `ILogger`), and the outer `IMessageHandler` catches **once, solely** to convert to `MessageProcessStatus.Failed()`; its log line now names the asset and says where the message goes instead of promising a retry it could not deliver. **No CDK change was required** — verified: the saga event source already sets `reportBatchItemFailures: true`, `Function.cs` already returns the per-item batch response, `media-sagas` already has `maxReceiveCount: 3`/300 s, and `media-sagas-dlq-depth` already exists. The entire transport was correct and blocked only by the swallow. **Eleven tests added** in `Processing.WriteModel.Tests/Sagas/` covering both halves of the rule (infrastructure failure propagates; handled domain outcomes still complete normally) — the `Sagas` test folder existed and was **empty**, which is why this survived. ⚠️ **Written without a compiler — no .NET SDK in the session. Not properly closed until `dotnet test` is green** (same caveat as X-11.31, X-11.16). **Boundary established while fixing, and it matters for X-11.5:** a *rejected command* never reaches any catch — the saga dispatches via the non-generic `ICommandDispatcher.SendAsync(ICommand)`, which returns bare `Task` and **discards the handler's `Result<T, DomainError>`** (traced `CommandDispatcher.ExecuteCommand` → `CommandHandlerInvokerFactory`; all three dispatched commands inherit the non-generic `Command`). So this fix could land alone without turning X-11.5's rejections into a redelivery loop — and it leaves domain-rejection failures exactly as invisible as they were. *Expect `media-sagas-dlq-depth` to fire for the first time; that is the fix working.* Original finding: *Opened 2026-08-25 by W19.* **It is not retried, and the DLQ is unreachable.** The inner `IIntegrationEventHandler` catches every exception, logs, and **does not rethrow**; the outer `IMessageHandler`'s catch is therefore dead code and it always returns `MessageProcessStatus.Success()`. The message is **acknowledged and deleted**. So a DynamoDB throttle, a serialization error or a dispatch throw is **logged once and the event is lost** — `maxReceiveCount: 3` never counts, `media-sagas-dlq` never receives it, and the `media-sagas-dlq-depth` alarm cannot fire for this class of failure. Only errors *outside* the handler (cold start, DI resolution, AWS.Messaging deserialization) can DLQ. **The same pattern is in all five handler pairs.** A saga handler should let infrastructure exceptions propagate and reserve catch-and-log for domain outcomes it has genuinely handled. | `Processing.WriteModel/IntegrationEvents/Consuming/Handlers/*SagaHandler.cs` · `hosts/SagaOrchestrator/AssetIngestion/Handlers/*SagaHandler.cs` |
| ◐ | X-11.5 | Med · **core fixed 2026-08-27** | ~~`AssetIngestionSaga` comment: *"Safe to call on an already-terminal aggregate — `FailProcessingJobCommand` is a no-op"*~~ | **◐ Core fixed 2026-08-27; two related gaps deliberately left open.** `ProcessingJob.Fail()` is now a **state machine**, not a guard: idempotent on `Failed` (preserving the original reason/category so a duplicate cannot overwrite the real cause), **transitions from `Queued` or `Running`**, and refuses only `Succeeded`/`Bypassed`. **Open question 5's framing did not survive contact** — it asked "genuinely idempotent, or caller checks results?", and the answer is neither: blanket idempotency on `Queued` returns success without transitioning, which strands the job exactly as before. **A second, load-bearing defect surfaced while fixing it:** `ProcessingJobFailureCategory` had **no `ValidationTimeout` member**, despite its own doc claiming its values match `AssetManagement.FailureCategory` for round-tripping — so the saga's `Enum.TryParse` fell back to `ProcessingTimeout`, **the one category `ProcessingJob.Complete()` treats as reversible**. A validation timeout was both mislabelled and wrongly eligible for timeout recovery; fixing `Fail()` alone would have quietly enabled that path. `ValidationTimeout` appended (ordinals unchanged). **The suite was green because it asserted the defect** — `ProcessingJobAggregateTests.Fail_WhenNotRunning_ReturnsError` and `FailProcessingJobHandlerTests.HandleAsync_QueuedJob_ReturnsDomainError` both required a `Queued` job to be refused; sharper than X-11.16's *absent* tests, since these existed, passed, and locked the bug in. Both replaced plus six new cases. Spec corrected in four files (`assetingestionsaga.md` compensation + idempotency, `processingjob.write-model.md` transitions/enum/events, `processingjob.scenarios.md`, `context-overview.md`). ⚠️ **Written without a compiler — not properly closed until `dotnet test` is green.** **Still open:** the bypass branch's save-before-dispatch ordering (a compensation-design question, not a reorder) and optimistic concurrency on saga `SaveAsync` (**open question 3** — worth deciding before `DocumentSigningSaga` exists, not after). Both became *more reachable* when X-11.6 turned single deliveries into up to three. Original finding: *Opened 2026-08-25 by W19.* **False.** `ProcessingJob.Fail()` guards `if (Status != Running) return DomainError.InvalidOperation("Job is not currently running.")` — it returns a failed `Result`, and **nothing inspects it**. The consequence lands on the **validation-timeout** path: the scanner dispatches `FailProcessingJobCommand` against a job still in `Queued`, it is rejected, and **the ProcessingJob stays `Queued` forever** while its Asset is `Failed`. `Start()` and `Bypass()` *are* genuinely idempotent, which is probably where the assumption came from. Two related gaps: the bypass branch saves terminal state **before** dispatching and never checks the result, so a failed dispatch strands the Asset in `Validating` with nothing to retry; and saga `SaveAsync` is an unconditional `PutItem` with **no optimistic concurrency** (the `Version` attribute is written and never read). | `AssetIngestionSaga.cs` · `ProcessingJob.cs` · `DynamoDbSagaRepository.cs` |
| ☑ | X-11.7 | ~~High~~ → **not a defect** | `AssetProcessingWorker` resolved by no host | *Opened 2026-08-25 by W19, **closed the same day by Chase.*** **Deliberate, not broken.** The worker is not wired because **its queues are not active yet**, and `RunProcessingPipelineAsync` is a deliberate pass-through stub — there to stop the pipeline blocking, not an unfinished implementation left by accident. The suspected consequence (every non-bypassed asset stranded until the 4-hour budget expires) does **not** hold. **One thing to carry forward as a prod-readiness item rather than a bug:** when the processing queues are activated, the stub is replaced *and* the saga success path needs verifying end to end — `AssetProcessingWorker.ProcessAsync` is still the only dispatch site of `CompleteProcessingJobCommand`, so that path has never actually run. Worth an explicit test at that point, because nothing exercises it today. |
| ☐ | X-11.8 | Low | `RejectMediaItemCommand` / `RejectMediaItemHandler` | *Opened 2026-08-25 by W20.* **Orphaned but registered.** Both survive from the review-saga era, are still DI-registered (`Catalog.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:217`) and still have passing tests — but **nothing dispatches them**. `RejectMediaItemEndpoint`, despite its folder name, sends `RejectReviewCommand`; `RejectMediaItemHandler` is a byte-for-byte duplicate that calls the same `mediaItem.RejectReview(...)`. Harmless today, but a green test suite over a code path no caller reaches is exactly what made the spec's saga account look credible for three months. Delete both, or route the endpoint through the one that is named for it. | `Commands/MediaItems/RejectMediaItem/` |
| ☐ | X-11.9 | Low | `ForceReleaseCheckoutHandler` returns `Forbidden(...)` | *Opened 2026-08-25 by W20.* The 403 for a non-owner, non-System caller **carries no `errorCode`** — the handler never calls `.WithCode(...)`, unlike essentially every other failure in the system. A client cannot distinguish it programmatically from any other 403, and `error-catalog.md` gives a reader no reason to expect the gap. Either assign it a code or record the exception in the catalog. | `Commands/MediaItems/ForceReleaseCheckout/ForceReleaseCheckoutHandler.cs:45` |
| ☐ | X-11.10 | Low | Four copies of `private const string SystemActorType = "System"` | *Opened 2026-08-25 by W20.* `ForceReleaseCheckoutHandler`, `AssetOwnership`, `RegistrationOwnership` and `SearchRegistrationsEndpoint` each redeclare the constant privately. **This is the whole of actor-type authorization in the platform** — there is no `RequireActorType` policy and no shared abstraction — so the one string that decides privilege is duplicated four times with nothing holding the copies together. Not a bug today; every copy is correct. It is the shape that makes the fifth copy the one that is wrong. | four files |
| ☐ | **X-11.30** | 🔴 **Critical** 🔒 | **81 of 132 write commands have no authorization check of any kind** *(was 86; the five X-11.31 setters closed 2026-08-26)* | **Update 2026-08-26 — this is now blocked outside the repo.** `magiq-auth` issues **no `roles` claim and no `actor_type` claim**, verified against its source: `UserProfileService` is the only `IProfileService` and emits six claims, none a role; `ApiScopes` is empty and no `ApiResource` exists, so `RequestedClaimTypes` is empty; no client allows a roles scope; and roles do not exist as data at all. Metadata's 17 and MediaProfile's remaining 13 are tenant-wide configuration with **no owner to fall back on**, so they need a role and cannot be closed in any other shape — which puts `docs/spec/shared/magiq-auth-role-claims-requirements.md` (written, **unsent**) on this finding's critical path. **Two corollaries about the code as it stands:** `ActorType` is always `"User"` over HTTP, so the System branch of `AssetOwnership.CheckOwner` and `ForceReleaseCheckout` never fires for a real caller — **those guards are owner-only in practice, narrower than they read**, which strengthens rather than weakens the rule against deleting them; and Registration's five decision commands could take a System-actor gate today without waiting on anyone. Counts above revised from 86/66 to **81/61**. Original finding: *Opened 2026-08-25 by W22 — **escalated, not filed.*** Enumerated exhaustively (`find src/modules -path '*/Commands/*Command.cs'` → 133 files, 1 marker interface, **132 commands**, 132 classified). **No endpoint in the system calls `Roles()`, `Permissions()`, `Policies()` or `Claims()`** — zero hits across 146 endpoint classes; both hosts define an `"AuthenticatedUser"` policy and neither applies it. Authorization exists only as handler guards (20 commands) and aggregate guards (12). **The remaining 86 execute for any authenticated member of the tenant, and 66 are HTTP-reachable.** Worst group is **Registration**: the five commands that *decide* a filing — `ConfirmRegistration`, `RejectRegistration`, `ApproveAmendment`, `RejectAmendment`, `RecordRegistrationSubmission` — are all unguarded, while the five that act on an officer's *own* filing are guarded. That is the inverse of what a records platform needs, and `ApproveAmendment`'s own doc comment promises a System gate that was never implemented. Also unguarded and HTTP-reachable: **`PurgeMediaItemVersion`** (destroys a retained record version), **`WithdrawMediaItem`** (unpublishes another user's record — the aggregate comment says *"owner pulls the item back"*), `PublishMediaItem` (submit any item and choose its reviewers), all 17 **Metadata** commands (tenant-wide schema control), all 18 **MediaProfile** commands, all 8 Collection and 11 Folder commands. Tenant scoping is universal and sound, but it is a boundary, not authorization. **Full matrix: `docs/spec/shared/authorization-matrix.md`.** | 132 commands across 6 modules |
| ☑ | **X-11.31** | 🔴 **Critical** 🔒 | ~~Unprivileged callers can disable the guards~~ **Fixed 2026-08-26** | **Closed 2026-08-26.** `ProfileGovernanceAuthorization.CheckPrivileged` — System actor **or** the `MediaAdministrator` role, case-insensitive, null-safe, fails closed — is wired into all five setters and refuses with `403` / `TenantAdministratorRequired` (a new cross-cutting error code). The check runs **before** the profile is read, so a refusal does not disclose whether the id exists; a strict repository mock with no setups enforces that in the tests. **Two premises corrected while verifying.** (a) *The escalation was three commands, not one* — the setters write to the **draft** and `EditSessionGuard` reads the **published** profile, so the real path was `CreateMediaProfileRevision` → setter → `PublishMediaProfile`. Guarding the middle step is still sufficient, because `MediaProfileDraft.FromPublished` copies the current policies forward; had a new draft reset to defaults, it would have closed nothing. (b) *Seeding is unaffected* — `SeedDefaultProfilesService` runs from the CLI, where `ConsoleExecutionContextAccessor` resolves `Actor.System`. **The role branch admits nobody yet**: `magiq-auth` issues no `roles` claim (see X-11.30), so these five are CLI-only until it does — deliberate, and the hand-off asking for the claim is `docs/spec/shared/magiq-auth-role-claims-requirements.md`. ⚠ **Written but never compiled — no .NET SDK in the session. Build and run `Catalog.WriteModel.Tests` before PR.** Original finding: *Opened 2026-08-25 by W22.* `EditSessionGuard` is the most widely applied guard in the system (nine MediaItem commands) and its checkout half is conditional on `MediaProfile.CheckoutPolicy`. **`SetCheckoutPolicy` has no authorization**, so any authenticated tenant member can set the policy to not-required and **neutralise that guard tenant-wide for every item on the profile**. `SetReviewPolicy` does the same to the review gate, `SetChangeRequestPolicy` to the change-request gate. **This is worse than the individual gaps in X-11.30**, because it turns a caller with no privileges into one for whom the remaining guards no longer apply — a privilege-escalation path rather than a missing check. Fix these five setters (`SetCheckoutPolicy`, `SetReviewPolicy`, `SetChangeRequestPolicy`, `SetCapabilities`, `SetAutoSubmitOnComplete`) **before** the long tail: they are the smallest change with the largest effect. | `Catalog/Commands/MediaProfiles/Set*` |
| ☐ | **X-11.32** | **High** | The detach half of the asset lifecycle is not wired | *Opened 2026-08-25 while classifying `Asset` for the ownership ADR.* **Unassigning an asset from a MediaItem role never reaches the Asset aggregate.** `Asset.DetachFromMediaItem` exists and is correct — `Apply(AssetDetachedFromMediaItem)` clears `MediaItemId`, `RoleName`, `IsPrimary` — but **nothing dispatches it**: `DetachAssetFromMediaItemCommand` appears exactly once outside its own folder, in its DI registration (dead, cf. X-11.8). There is **no unassign consumer** on the AssetManagement side — `AssetAssignedToRoleEventHandler` handles attach and has no counterpart — and `ApplyAssetAssignmentCommand` takes a **non-nullable** `MediaItemId`, so it can only attach. Catalog's `AssetUnassignedFromRole` domain event is consumed by nobody in AssetManagement. **Consequences:** after the first assignment an asset's `MediaItemId`/`RoleName` are set permanently and `IsAssigned()` stays true, so (a) the standalone/unassigned state is unreachable, (b) **the asset can never be reassigned to a different MediaItem**, since attach requires a standalone asset, and (c) the intended custody model — whoever detaches an asset decides its fate — has no transfer point to hang on. **Blocks the `Asset` half of `docs/adrs/ownership-and-authorization.md`.** Design note for the fix: the Asset-side handler runs in `EventConsumers` with no HTTP actor, so **the detaching user's identity must travel on the integration event** or there is nobody to transfer custody to. | `Asset.cs:442,860` · `ApplyAssetAssignmentCommand.cs` · `ServiceCollectionExtensions.cs:153` |
| ☐ | X-11.33 | Low | `Asset.cs:73` comment contradicts `Apply` | *Opened 2026-08-25.* The field comment says `MediaItemId` is *"null for standalone uploads; **immutable once set** via AssetAttachedToMediaItem"*. `Apply(AssetDetachedFromMediaItem)` sets it back to null (`Asset.cs:862`). The comment describes the behaviour that *results from* X-11.32 rather than the aggregate's design — and would mislead anyone fixing that. **Fifth comment found this session asserting something the code contradicts** (cf. X-11.5, X-11.21, X-11.28, and the phantom `SetAssetDefinitionDefault` pre-condition at `MediaProfile.cs:386`). | `Asset.cs:73` |
| ☐ | **X-11.35** | **High** | Folder assignment is guarded by nothing | **Verified against source 2026-08-26 — holds on every clause, and the undetermined one is now determined.** *Resolved:* `Apply(MediaItemArchived)` does **not** clear `FolderId`, so an archived item whose reservation was released still passes `Move`'s `IsAssignedToFolder()` gate. The DynamoDB store's delete leg carries `ConditionExpression = "OwnerId = :oid"`, which fails on a missing item; `NameReservationConflictException` is caught in `MoveMediaItemHandler.cs:70-74` and returned as **`409 "A media item with this title already exists in the destination folder."`** So it fails neither loudly-and-correctly nor silently: it is a **permanently unactionable 409 blaming a title conflict that does not exist**, and `AssignOrMoveMediaItemFolderEndpoint` declares that exact 409 for the genuine case, making the two indistinguishable to a client. *Latent test gap:* the **in-memory** reservation store upserts in the same scenario instead of throwing, so any test written against it passes where DynamoDB fails. *Also:* neither `MoveMediaItemCommand` nor `AssignMediaItemToFolderCommand` carries an actor, so `EditSessionGuard` could not be applied without changing the command shape; and the auto-submit dispatch fires **after** the handler's own `SaveAsync` without inspecting its result, so a failed inner publish leaves the item assigned, unpublished and uncompensated while the outer call returns success — and because it dispatches `PublishMediaItemCommand`, a folder assignment can transitively terminate another user's checkout via X-11.34. Original finding: *Opened 2026-08-25 by W23.* `MediaItem.AssignToFolder` guards only `if (FolderId.HasValue)`; `Move` guards only "is assigned" and "not the same folder". **No status check, no archive check, no checkout check**, and neither handler derives from `MediaItemGuardedCommandHandler`, so `EditSessionGuard` never runs. So an item can be moved **while another user holds it checked out**, **mid-review in `PendingApproval`**, and **while `Archived`**. The archived case is the live bug: `ArchiveMediaItemHandler` releases the title reservation on archive, so a later move calls `nameReservationService.MoveAsync` against a reservation row that no longer exists — whether that fails loudly or silently is **not determined** from Catalog code, which is itself the argument for guarding the move rather than leaving the outcome to the uniqueness registry. Related: `AssignMediaItemToFolderHandler` can **auto-submit for publication** (`AutoSubmitOnComplete` + `Draft` + all required roles filled), so folder assignment also *drives* the status machine — undocumented until now. | `MediaItem.cs:629,703` · `AssignMediaItemToFolderHandler.cs:82` |
| ☐ | X-11.34 | Med 🔒 | Non-editors can publish, archive or withdraw a checked-out item | **Verified against source 2026-08-26 — holds, with one correction and two additions.** *Correction:* **not silent.** `EditSessionClosed` is emitted, persisted, published to SNS and handled by three projectors, so the termination is fully auditable; what is absent is any user-facing notification, and on the archive path `closedBy` is `null` (`MediaItem.cs:592`), so the record does not name who broke the lock. *Additions:* withdraw **partially** restores the lock — `ReopenEditSession` runs only when the item was `PendingApproval`, and from the review roster rather than the session, so withdrawing a `Published` or `Revising` item destroys the lock outright, and archive never restores it; and `ArchiveMediaItemCommand` carries **no `RequestingUser` at all**, so guarding archive means changing the command shape, not adding a line. *Cheap doc fix to ride along:* `ArchiveMediaItemEndpoint.cs:32,38` documents *"cannot archive while checked out"* and a 422 for it — no such check exists. Original finding: *Opened 2026-08-25 by W23 — a specific, high-traffic instance of **X-11.30**.* `PublishMediaItemHandler`, `ArchiveMediaItemHandler` and `WithdrawMediaItemHandler` do **not** derive from `MediaItemGuardedCommandHandler`, so `EditSessionGuard.CheckWritable` never runs; and `RequestPublication`, `Archive` and `Withdraw` contain **no editor check in the aggregate either** — only `CheckIn`, `AbandonCheckout` and `RenewCheckout` do. Any authenticated tenant member can therefore publish, archive or withdraw an item another user currently holds, and **the holder's session is closed underneath them** as `Submitted` or `Superseded`, silently. The pattern across the 11 guarded commands is consistent and telling: **content edits are guarded, lifecycle transitions are not.** | `PublishMediaItemHandler.cs:19` · `ArchiveMediaItemHandler.cs:17` · `WithdrawMediaItemHandler.cs:15` |
| ☐ | X-11.37 | Low | `CapabilitySet.Has(...)` has zero call sites | *Opened 2026-08-25 by W23.* `CapabilitySet.Has(Capability)` / `HasAll(...)` are never called, and the typed accessor `MediaItem`'s class comment advertises (*"use `Profile.HasCapability()` checks"*) **does not exist**. **Every real capability check is a `string` `Contains` on a cross-module reference model** (`MediaItemCapabilityService`, `MediaItemReference.HasRegistrationCapability`), not a comparison on the enum. Compounding it, `Metadata.WriteModel.Infrastructure/Services/CapabilityRegistry.cs` declares a **parallel set of nine string constants** with the comment *"These must match `Catalog.Domain.Capability` enum member names exactly"* — an **unenforced** duplication across a module boundary. Worth also knowing: **only 2 of the 9 capabilities gate any behaviour** (`Processing`, `Registration`); the other seven, including `CheckInOut`, `Review` and `Signing`, change nothing. | `CapabilitySet.cs:71,76` · `CapabilityRegistry.cs:330-341` |
| ☐ | X-11.36 | Low | `ReplaceAssetInRole` header comment claims an `Active` check that does not exist | *Opened 2026-08-25 by W23.* `MediaItem.cs:826` documents *"Handler pre-conditions: new asset exists, **is Active**, ContentType matches role"*. `ReplaceAssetInRoleHandler` checks existence and `AllowedMediaCategories` only — no `AssetStatus` comparison anywhere in the file. The neighbouring `AssignAssetToRole` comment gets it right and explains why (*"No status constraint on assignment…"*). **Sixth comment found this session asserting something the code contradicts.** The spec rows that repeated it are now corrected; the code comment is not. | `MediaItem.cs:826` |
| ☐ | X-11.41 | **High** | `FolderMediaItemsIndex` is add-only | *Opened 2026-08-25 by W24.* The projector handles **`MediaItemCreated` and nothing else** — no removal on archive, delete or **move**. Since both archive fan-out workers traverse this index to find a folder's items, the consequences are: (a) already-archived items are re-archived on every pass, producing warnings indistinguishable from real failures (compounds X-11.16); and (b) **an item moved to a different folder is still archived under its old parent** when that folder is archived. The second is silent data-state corruption from the user's point of view — they moved the item out precisely so it would not be affected. | `FolderMediaItemsIndexProjector.cs:12-26` |
| ☐ | X-11.38 | **High** | Deprecating a MediaProfile half-blocks its items | *Opened 2026-08-25 by W24.* Enforcement splits on **which lookup a handler happens to use**. Paths that load the **aggregate** see `Deprecated` and refuse — `CreateMediaItem`, `PublishMediaItem`, `AssignAssetToRole`. Paths that read `IMediaProfileQueryService.GetPublishedAsync` do **not**, because `MediaProfileIndexProjector` handles `MediaProfilePublished` **only** and never the deprecation event, so the index serves the stale published snapshot indefinitely. **Net effect: after deprecating a profile, its items can still be checked out and edited, but not created or published.** Nobody chose that half-life — it is an accident of lookup choice. Either project the deprecation into the index or stop mixing the two sources. | `DeprecateMediaProfileHandler.cs` · `MediaProfileIndexProjector.cs` |
| ☐ | X-11.39 | Med | Folder depth guard is bypassable by moving a subtree | *Opened 2026-08-25 by W24.* The 10-level depth limit is enforced by a `depth` uniqueness counter, but `MoveFolderHandler` adjusts **only the moved folder's own counter** — descendants keep stale values. Moving a deep subtree under a deep parent therefore exceeds 10 without tripping `DepthExceeded`, and every later check on those descendants reads a wrong number. The invariant is real; its maintenance is incomplete. | `MoveFolderHandler.cs:143-146` |
| ☐ | X-11.42 | Med | The assets of a deleted MediaItem can never be deleted | *Opened 2026-08-25 by W24.* `Asset` refuses deletion while assigned to a role (`AssetAssignedToMediaItem`). `DeleteMediaItem` **does not detach its assets**, and the detach path never reaches the Asset aggregate at all (**X-11.32**). So those assets are pinned to an item that no longer exists, with no route to release them and no command that could. **Resolves when X-11.32 does** — recorded separately because it is the concrete cost of that gap and would otherwise be discovered as a support ticket. | `DeleteMediaItemHandler.cs` · `Asset.cs:408-424` |
| ☐ | X-11.43 | Med | A stuck `active-registrations` counter makes a folder permanently unarchivable | *Opened 2026-08-25 by W24.* `RegistrationCancelled`/`Rejected` → `RemoveRegistrationRefCommand` decrements the counter; failure is **logged and the message acked**, deliberately, for idempotency. The trade is unstated: a *persistent* failure leaves the counter high, and since that counter gates folder archive (invariant 13) **the folder can never be archived, with no visible cause**. There is no reconciliation job and no way to inspect a counter through the API. | `RemoveRegistrationRefHandler.cs:32` · `RegistrationCancelledEventHandler.cs:41` |
| ☐ | X-11.40 | Low | `FolderRegistrationIndex` / `RegistrationCountIndexProjector` are dead | *Opened 2026-08-25 by W24.* The projector's own doc comment says it is *"consumed by `IFolderArchiveFanOutWorker.HasActiveRegistrationsAsync`"*. **It is not** — no lookup for it exists anywhere; the guard reads the `active-registrations` uniqueness counter instead. The DynamoDB table is still provisioned and written on every registration change. **Seventh comment this session asserting something the code contradicts.** Delete the projector and de-provision the table, or wire it and drop the counter — but not both. | `RegistrationCountIndexProjector.cs` · `ServiceCollectionExtensions.cs:383` |
| ☐ | **X-11.44** | **High** | No outbox — a publish that fails after commit is lost silently | *Opened 2026-08-25 by W25.* `DomainEventPublishingMiddleware` publishes to SNS **after** the event store commits, inside the request. The ordering is deliberate and right (*"`next` is awaited first so the event store write commits before any downstream consumer sees the events"*), but there is **no outbox**: if the publish then fails, the event is durable and **never reaches a projector**. The read model is wrong **permanently, not temporarily** — no retry exists because nothing knows it was missed, and only a manual rebuild fixes it. This is the one case where *"eventually consistent"* is false; the accurate phrase is *eventually consistent, or silently divergent*. **Follows from ADR-005** (inline publication instead of a publisher Lambda) — the decision is defensible and **this consequence was never written down**. Note the platform SDK's own guidance says the opposite: *"Never publish to a message bus directly from a command handler. Always use `IOutbox`."* Either adopt the outbox or record the deviation in ADR-005 with this cost stated. | `Api/Infrastructure/Middleware/DomainEventPublishingMiddleware.cs` |
| ☑ | X-11.45 | ~~Med~~ **closed 2026-08-25** | `LastObservedAtUtc` does not exist | **Confirmed and removed.** Verified in both repos: **zero occurrences in any `.cs` file**, and `IReadModel : IVersionedProjection` never declared it — so the field existed only in guidance. Chase's call: drop the convention, since `ProjectedVersion` already is the idempotency fence and the only per-record freshness signal. **Removed from:** `magiq-media/CLAUDE.md:168`, `aspnetcore-platform/CLAUDE.md` (the Read Models section and its code sample), `Z:\...\deploy-runbook.md:116`, `spec/architecture/bounded-contexts.md`, `spec/contexts/Registration/.../registration.read-model.md`, and the note in `spec/shared/consistency-model.md`. Each carries a dated correction rather than a silent edit. **One left deliberately:** `aspnetcore-platform/src/platform/Domain/Magiq.Platform.Projections.Stores.DynamoDb/README.md` still shows it across a worked `InvoiceSummaryReadModel` example. Flagged in that repo's `CLAUDE.md` rather than rewritten — it is a tutorial, not a rule, and rewriting eight occurrences in a walkthrough is a separate job. |
| ☑ | X-11.16 | **High** · **fixed 2026-08-27** | Both archive fan-out workers: `if (!result.IsSuccess) logger.LogWarning(...)` | **☑ Fixed 2026-08-27.** Both workers now return an `ArchiveFanOutReport` — failures, skipped folders, and archived-vs-attempted counts. The archiving half of both moved into one shared `ArchiveFanOutCascade`, since the duplicated dispatch code is why this defect existed twice. Already-archived is classified by `errorCode` and counted as archived, not as a failure (which required adding `MediaItemErrorCodes.MediaItemAlreadyArchived` — `MediaItem.Archive` refused uncoded). The completion line now reports outcomes and logs at **Error** when incomplete; `ArchiveFolderHandler` refuses with **422 `FolderArchiveIncomplete`** instead of archiving the root over a refusal. Both workers now have tests (`FolderArchiveFanOutWorkerTests`, `CollectionArchiveFanOutWorkerTests`) — they had none. ⚠️ **Written without a compiler: no .NET SDK was available in the session. Not properly closed until `dotnet test` is green** — the same caveat X-11.31 carried. *Originally (opened 2026-08-25 by W21):* **Every per-child archive failure is logged and discarded.** Nothing is collected, nothing retried, nothing returned — `ArchiveSubtreeAsync` returns `Task`, not `Task<Result>`. The completion line logs **attempted** counts, so *"Fan-out complete for collection X: 40 folders, 900 media items"* prints identically whether all 900 archived or none did. The caller already has its `204`. **There is no signal anywhere — logs, read models, or API — that distinguishes a complete archive from a total failure.** Identical code in both workers. | `CollectionArchiveFanOutWorker.cs` · `FolderArchiveFanOutWorker.cs` |
| ☐ | X-11.17 | **High** ⚖️ | A collection archives even when its folders may not | *Opened 2026-08-25 by W21.* `ArchiveFolderHandler` refuses a subtree holding active registrations (`FolderHasActiveRegistrations`, 422). **`ArchiveCollectionHandler` has no such guard** — verified, it loads, archives, releases the name reservation and saves. The collection is therefore already archived *before* `CollectionArchivedIntegrationEvent` is published; when the fan-out then hits a registration-locked folder, the refusal comes back as a failed `Result` and is **swallowed per X-11.16**. Result: a collection containing retention-locked content reports archived, its locked folders stay active, there is no rollback and **nothing records the discrepancy**. ⚖️ **Compliance weight** — active registrations are precisely what a retention rule protects. | `ArchiveCollectionHandler.cs` · `CollectionArchiveFanOutWorker.cs` |
| ☑ | X-11.15 | Med · **fixed 2026-08-27** | Archive cascade is re-entrant | **☑ Fixed 2026-08-27.** Phase 3 now dispatches `ArchiveFolderNodeCommand` — archive one folder, no guard, no cascade, deliberately not HTTP-reachable — instead of `ArchiveFolderCommand`. The registration guard runs **once** on the folder path instead of O(depth) times over overlapping subtrees. **The trap:** the collection path had no pre-flight guard of its own and was protected *only* as a side-effect of this re-entrancy, so removing it would have silently deleted the last thing standing between a collection archive and its retention-locked records; `ArchiveFanOutCascade` therefore takes a `guardRegistrations` flag, on for the collection path, and its per-item check is stricter than what it replaced (it refuses the locked item in phase 2 rather than only its folder in phase 3). Phase 2 also bounded to 16 concurrent archives and phases 1–2 switched to batched `GetManyAsync`. ⚠️ **Written without a compiler — see the X-11.16 caveat.** *Originally (opened 2026-08-25 by W21):* Each `ArchiveFolderCommand` the fan-out dispatches re-enters `ArchiveFolderHandler`, which calls `HasActiveRegistrationsAsync` **and** `ArchiveDescendantsAsync` again — re-walking a subtree the leaf-first ordering has already archived. The registration guard therefore runs **O(depth) times over overlapping subtrees**, each run issuing one counter read per media item beneath it, sequentially. Every repeat archive returns *"already archived"* and logs a warning, so a deep tree does quadratic work **and** floods the log with benign warnings — the condition under which a real one is missed. Compounded by phase 2's unbounded `Task.WhenAll` (no `SemaphoreSlim`, no batching) and by the whole subtree being materialised in memory with no paging or cap. | `FolderArchiveFanOutWorker.cs` · `ArchiveFolderHandler.cs` |
| ☑ | **X-11.18** | **High** *(was Med — confirmed 2026-08-25)* · **fixed 2026-08-27** | A partial archive can strand a subtree, unreachably | **☑ Fixed 2026-08-27, as the review predicted — downstream of X-11.16.** The policy chosen for open question 1 was **continue and suppress ancestors**, not abort: the cascade archives everything it can, records every refusal, and declines to archive the refusing child's folder and every folder above it. So the un-archived remainder is always a **connected subtree containing the root**, which is the same invariant that already made a clean crash safe — and re-issuing the archive against the root is a complete recovery on the folder path. Aborting the level would have given the same guarantee for less code but let one permanently-unarchivable child block a whole tenant's archive forever. Two things the original finding did not capture: a refusing **media item** strands the same way once its folder archives, so phase 2 now tracks outcomes per containing folder rather than in one flat `Task.WhenAll`; and the regression tests that matter are the **negative** ones (`NotContain`), because a test on the failure list alone passes with X-11.16 fixed and still permits the stranding. ⚠️ **Written without a compiler — see the X-11.16 caveat.** *Original evidence:* **Confirmed from code; no dev check needed, and the trigger is not what the finding assumed.** `FolderChildIndexProjector.ResolveKey(FolderArchived)` targets `(ParentFolderId ?? CollectionId)` — the **parent's** record — and `ApplyAsync` does `SetRemove("ChildFolderIds", {e.FolderId})`. So archiving a folder removes it from its parent's child set, and that set is the **only** traversal either fan-out worker has. **A clean crash is safe**, which is worth stating because it is why this looked speculative: phase 3 archives **leaf-first** (`for (var i = levels.Count - 1; i >= 0; i--)` with `await Task.WhenAll` per level), so the unarchived folders always form a **connected subtree containing the root** — a retry from the root reaches all of them. **A swallowed failure is not safe.** If folder D fails to archive at level k+1 — a failed `Result`, logged at warning and **discarded** per **X-11.16** — the loop still proceeds to level k and archives D's parent P. `FolderArchived(P)` removes P from *P's* parent's set. **P is archived, D is not, and D is now unreachable from the root** along with everything beneath it. A retry never visits it; nothing detects it; there is no tool to find it. **So this is downstream of X-11.16, and fixing X-11.16 largely closes it** — collect per-child failures and abort the level rather than proceeding, and the stranding cannot occur. That is a strong additional argument for X-11.16 beyond the reporting problem. | `FolderChildIndexProjector.cs:33-35,55` · `FolderArchiveFanOutWorker.cs:67-70` |
| ☐ | X-11.19 | Med | Fan-out is sync in-request pre-prod, async over SQS in prod | *Opened 2026-08-25 by W21.* CDK sets `ASPNETCORE_ENVIRONMENT: isProd(config) ? 'Production' : 'Development'` and `isProd ⇔ env === 'prod'`, so **`dev`, `qa` and `staging` all run `Development`**, where `Api/Startup.cs` wires `AddCatalogIntegrationEventConsumers()` onto `AddInProcessMessageBus()`. The collection cascade is therefore **synchronous inside the HTTP request on three tiers** — no queue, no redelivery, no DLQ — and asynchronous on `prod` alone. The environment collapse itself is deliberate and documented in the CDK; the fan-out consequence looks unintended. **`staging` cannot reproduce a production partial-archive by construction**, and prod is the only tier where redelivery could recover one. | `magiq-media-stack.ts:269` · `Api/Startup.cs:109` |
| ☐ | X-11.11 | Low | Repo `CLAUDE.md` lists `DocumentSigningSession` as an aggregate | *Opened 2026-08-25 by W21.* The module table says `\| DocumentSigning \| DocumentSigningSession \|`, but **no such class exists** — `DocumentSigning.Domain/Aggregates/` contains only an `Events/` folder, and no type carries a `media.signingsession` `[AggregateType]`. The same file's deferred-work list contradicts the table two pages later. The docs project's `CLAUDE.md` has it right (*"skeleton only — no aggregate class exists"*). Fix the repo table so the two agree. | `CLAUDE.md:139` vs `:207` |
| ☐ | X-11.12 | Low | `SigningSessionDetailProjector` is complete and never registered | *Opened 2026-08-25 by W21.* The projector handles all nine signing events and keys every one correctly, but `AddDocumentSigningReadModelProjectors()` is **called by no host** — grep returns only the definition. Dead alongside `AddDocumentSigningReadModelQueries()`. Harmless while nothing emits signing events (the publishing middleware excludes `ISigningDomainEvent`), but it is finished work that will be forgotten when the module is picked up. | `DocumentSigning.ReadModel.Infrastructure/ServiceCollectionExtensions.cs` |
| ☐ | X-11.13 | Low | Webhook tenant-lookup table named two different ways | *Opened 2026-08-25 by W21.* `SagaOrchestrator.DocumentSigning.csproj`'s comment says webhook `TenantId` resolution uses `media-signing-sessions`; the code comments beside it say `media-signing-envelope-lookup`, keyed by `EnvelopeId`, written by `SigningEnvelopeLookupProjector`. **Neither the table nor the projector exists**, so nothing arbitrates. The code comment is the coherent one — SecuredSigning webhooks carry no `TenantId`, so the lookup must be `EnvelopeId → TenantId`, which `media-signing-sessions` (keyed by `SigningSessionId`) cannot answer. | `SagaOrchestrator.DocumentSigning.csproj` · `SecuredSigningWebhookHandler.cs` |
| ☐ | X-11.14 | Low | `LinkSigningSessionCommand` / `UnlinkSigningSessionCommand` registered, tested, never dispatched | *Opened 2026-08-25 by W21.* Both commands, both handlers, both aggregate methods and both unit tests exist and are DI-registered. **Neither has an endpoint and neither is dispatched anywhere in `src/`** — the only outside reference is a TODO inside `SigningSessionInitiatedHandler`, which throws `NotImplementedException`. That TODO also passes `envelopeId` into a parameter typed `SigningSessionId`. Same shape as X-11.8. **Sequencing matters here:** `ActiveSigningSessionId` blocks `CheckOut` and `RequestPublication`, so the day linking is wired without unlinking, a `MediaItem` becomes permanently un-checkoutable with no operator command to clear it. Ship both paths together. | `Commands/MediaItems/LinkSigningSession/` · `UnlinkSigningSession/` |
| ☐ | X-11.20 | Low | `Media:Catalog:BulkOperations:MaxAssetsPerRequest: 200` in `appsettings.json` | *Opened 2026-08-25 by W27.* **Binds to nothing.** Catalog's `BulkOperationsOptions` has no `MaxAssetsPerRequest` property — the asset cap is AssetManagement's, under `Media:AssetManagement:BulkOperations`, set to **100**. The dead key sits directly above the live ones in the same block, and reads as the authoritative asset limit. Anyone raising it to lift an asset bulk limit gets no effect and no error, and the 100 stays. This is the *second* time this pair of sections has caused a silent-fallback bug (see AM-12, where AssetManagement's own options bound to nothing at all). Delete the key. | `src/hosts/Api/appsettings.json:25` |
| ☐ | X-11.21 | **High** | Idempotency header name mismatch | *Opened 2026-08-25 by W29.* The middleware constant is **`Idempotency-Key`** (hyphenated). The spec, the Postman pre-request script and a code comment in `RequestAmendmentRequest.cs:17` all say **`IdempotencyKey`**. A client following the published contract gets **no replay protection at all** — silently, with a 2xx, because the middleware only inspects the hyphenated header and passes everything else through. **Spec corrected; the code comment still needs fixing.**<br><br>**Is it used, or is it leftover? — answered 2026-08-25.** **The mechanism is live and functional, and nothing in the application exercises it.** Live: the middleware resolves its tenant claim correctly (the platform claims mapper writes `tenant_id` — see X-11.22), the table is CDK-provisioned, and the wiring in `Api/Startup.cs:92-98` is deliberate, carrying a considered comment about verbatim table naming and suffix overrides. Unused: **no client code, no integration test and no Postman collection in this repo sends `Idempotency-Key`** — the only references outside the wiring are three comments asserting the feature does not exist and one naming it wrongly. So it is **not** dead code to delete; it is a working capability the team has forgotten it has. Two ways forward, and they need a decision: **(a)** adopt it — fix the header name in the comment, declare it in OpenAPI (**X-10.5**), and have clients send it; or **(b)** retire it deliberately — drop the package reference and the table. What must not persist is the current state, where the docs and the code comments disagree about whether it exists at all. | `IdempotencyMiddleware.cs:16` · `RequestAmendmentRequest.cs:17` · `Api/Startup.cs:92-98` |
| ☑ | X-11.22 | ~~High 🔒~~ → **Low, docs only** | Token carries `client_id`; the platform normalises it to `tenant_id` | *Opened and **closed** 2026-08-25 (W29). **The feared consequence does not hold — no security issue and no fail-open.*** Chase confirmed `magiq-auth` returns `client_id`, not `tenant_id`, which makes the `MagiqCloudTenantClaimName()` fallback to `"client_id"` **correct**, not a misconfiguration. The apparent contradiction with the spec resolves in the platform: `AddMagiqCloudJwt` registers a claims mapper that writes `SecurityOptions.TenantIdClaim` (default `"tenant_id"`) onto the `ClaimsIdentity` — first from `client_id`, then overwritten with the canonical `TenantSettings.Id`. So **by the time any application code or middleware reads the principal, a `tenant_id` claim exists**, holding the server-authoritative tenant id rather than the raw token value. The idempotency middleware therefore finds its claim and **does not fail open** — the compounding risk this finding was opened for is void. **All that was actually wrong is a documentation nuance:** the spec says "JWT `tenant_id` claim" where the truth is "the token carries `client_id`; the platform normalises it to `tenant_id` before app code sees it". *Also cleared: `AddHeaderIdentifierProvider` cannot override the JWT — priority 200 vs 90, first non-null wins.* **Spec corrected; nothing to fix in code.** | `TenantResolutionBuilder.cs:274` · `SecurityOptions.cs:38` |
| ☑ | X-11.23 | ~~High 🔒~~ → **Low, docs only** | ~~Read endpoints advertise a `403` that no code path can return~~ **Fixed 2026-08-26** | **Closed 2026-08-26.** `.ProducesProblem(403)` and its `summary.Response(403, …)` line deleted from `GetAssetDownloadUrlEndpoint` and `GetRenditionDownloadUrlEndpoint`; a comment in each records why there is no 403 so the next reader does not add one back. **No check added.** Re-verified before removing rather than taken from the finding: the only `Forbidden` anywhere in AssetManagement is `AssetOwnership.CheckOwner` on the write side, and nothing maps a read-model query error to `QueryErrorCode.Forbidden`. `asset.api.md` updated to record the fix. The write-side 403s in that file are reachable and were left alone; the rest of the unreachable ones stay with **X-11.27**. Original finding: *Opened 2026-08-25 by W29, **rescoped the same day by Chase.*** **The absent owner check is intended, not a defect** — read access is tenant-scoped by design, and per-resource permissioning will be handled by authorization when it lands, not by an ownership comparison in the query handler. **This finding is therefore purely a contract bug:** both download endpoints declare `403 "The caller does not own this asset."`, and `AssetOwnership.CheckOwner` is write-side only — no read-model handler references it or returns `Forbidden`, so that 403 is unreachable. A generated client handles a status that never arrives, and a reader infers an ownership rule the system does not have. **Fix by deleting the 403 declaration and its summary line from both endpoints** — do not add a check. Part of the wider declared-status problem in **X-11.27**. *(Tenant scoping itself is structural and sound: projection key `TENANT#…`, cross-tenant → 404.)* | `GetAssetDownloadUrlEndpoint.cs:32` · `GetRenditionDownloadUrlEndpoint.cs:33` |
| ☐ | X-11.24 | Med ⚖️ | No download is logged, audited or evented | *Opened 2026-08-25 by W29.* Neither download handler takes an `ILogger`; `S3PresignedGetUrlService` has no logging dependency; no domain or integration event is emitted; there is no audit facility anywhere in the repo. **Who downloaded what, and when, is not recoverable from this system.** The only possible trace is S3 server-access logging or CloudTrail data events, which I did not confirm are enabled — *not determined*. For a platform holding regulated government records this is worth a deliberate decision rather than an omission. | `GetAssetDownloadUrlHandler.cs` · `S3PresignedGetUrlService.cs` |
| ☐ | X-11.27 | Med | Declared status codes are broadly wrong | *Opened 2026-08-25 by W29.* Two systemic defects. **(a) Unreachable `403`s**: `ProducesProblem(403)` is near-universal, but **no endpoint calls `Roles()`/`Permissions()`/`Policies()`/`Claims()`** and most modules have no `Forbidden` producer — all 20 `/v1/record-types/**` routes, all Collection/Folder/MediaProfile routes, the three asset-upload initiators and several Registration transitions declare a 403 nothing can return. **(b) Missing success codes**: nine routes (`GET /v1/items/search`, `POST /v1/items/{itemId}/checkout`, `POST /v1/change-requests`, `POST /v1/items`, `POST /v1/items/bulk`, `POST /v1/collections`, `POST /v1/items/{itemId}/publish`, `PUT /v1/assets/{assetId}/tags`, `GET /v1/change-requests/{id}/comments/{commentId}`) declare only `ProducesProblem(...)` and **no `Produces(...)`** — several state the success code in `Summary` prose, where no generator finds it. Also several `/v1/record-types/**` mutations declare `409` against methods returning only 422/404. Pairs with **X-10.5** (no headers declared either). | across `*.Endpoints/V1/**` |
| ☐ | X-11.29 | Med | `DELETE /v1/items/{itemId}` re-emits forever | *Opened 2026-08-25 by W29.* `Apply(MediaItemDeleted)` never clears `ArchivedAt`, so `IsArchived` stays true, the admitting guard passes again, and **every repeat call returns `204` and appends another `MediaItemDeleted`**. Read-model state is unharmed (the projectors delete an already-absent row), but the stream grows without bound and the event log misreports how many times the item was deleted. Contrast every other destructive route, which returns 422 or 404 on repeat. | `MediaItem.cs:1466` · `MediaItem.cs:657` |
| ☐ | X-11.25 | Med | Nothing enforces the pre-signed upload deadline | *Opened 2026-08-25 by W29.* `Asset.ConfirmUploaded` gates on status alone and `ConfirmAssetUploadHandler` adds existence, ownership, `HeadObject` and size checks — **no time check anywhere**. The aggregate stores no URL expiry. **S3's SigV4 `X-Amz-Expires` is the sole time control**, in contrast to the three-layer defence the same ADR documents for size. The `UploadExpired` failure reason the ADR lists in `Validating` has no code path producing it. Also: `Media:AssetManagement:AssetStorage:PresignedUrlExpiryMinutes` is bound but set in **no** config file and **not** by the CDK, so 15 minutes is a compiled constant, not a tunable — and one shared `expiresAt` is stamped on every multipart part before fan-out, so part 10,000 expires with part 1. | `Asset.cs:917-947` · `S3AssetStorageOptions.cs:45` |
| ☐ | X-11.26 | Low | ADR describes a multipart `UploadId` table that does not exist | *Opened 2026-08-25 by W29.* `asset-storage-and-processing.md:35` says `UploadId` is *"tracked in a short-lived DynamoDB entry (TTL-based, 30 minutes)"*. **No such table, entry or TTL exists.** `UploadId` lives on the event-sourced `Asset` aggregate (`MultipartUploadId`), cleared only on abort or completion, with no expiry of its own; session expiry is S3's bucket lifecycle. Nor is there any store of issued URLs — they are returned in the response and never persisted. | ADR `asset-storage-and-processing.md:35` vs `Asset.cs:79,754` |
| ☐ | X-11.28 | Low | `DeleteAssetHandler` doc claims idempotency it does not have | *Opened 2026-08-25 by W29.* Class doc: *"The command is idempotent."* `Asset.cs:403` returns `DomainError.InvalidOperation("Asset is already deleted.")` → **422** on the second call. Third comment found this session asserting a property the code contradicts (cf. X-11.5, X-11.21). | `DeleteAssetHandler.cs` · `Asset.cs:403-407` |
| ☐ | X-4.15 | Low | — | *Opened 2026-08-25, same pass.* **Two SNS filter policies are hand-maintained mirrors of C# registration methods, and nothing enforces the mirror.** `media-sagas` mirrors `SagaRegistrations.AddSagaMessageHandlers()`; `media-cross-module-events` mirrors `ConsumerRegistrations.AddIntegrationEventMessageHandlers()`. Adding a handler without adding its `[MessageType]` to the CDK allowlist leaves the handler **registered and never invoked** — no error, no DLQ message, no alarm. This has already happened once: `media.item.rejected` / `media.item.withdrawn` were missing, so ChangeRequests' review threads stayed `Open` forever (CR-21, since fixed). Worth a build-time check that the two lists agree. | `sqs-queues.ts:186,240` |
| ☑ | X-4.10 | **Med** | — | *Opened 2026-08-24 closing X-4.8; **decided and code-fixed 2026-08-24**.* The version tables were partitioned by version number: every "version 1" row for every entity in a tenant shared one partition, worst on version 1 because every entity has one, and never self-correcting. `ListMediaProfileVersions` / `ListMediaItemVersions` only worked because their GSIs re-key around the base table — load-bearing, not optimisations. **Decision: re-key.** The row framed this as a judgement call; it is a **transposition bug**. `ProjectionKey(tenantId, discriminator, groupKey)` puts discriminator→SK and groupKey→PK-suffix, and five call sites passed `(t, entityId, version)`. Two tells: the `D10` zero-padding is a sort-key ordering device sitting uselessly in a partition key, and `RecordTypeVersionSummaryReadModel:36` — one file away from a wrong sibling — had it right. **Scope was 5 models, not the 2 the row named** (`MediaItemVersion` Summary+Detail found by sweeping every `new ProjectionKey<>` in `src/modules/`; that pair is the worst instance, media items being the highest-cardinality). Fixed by swapping the two arguments, with an XML-doc remark at each call site recording the trap. Four tables bumped to `schemaVersion: 2`; rotations also clear N.1 rows 4 and 6. **GSI removal deliberately not done here** — see X-4.11 | `MediaProfileVersion{Detail,Summary}ReadModel.cs`; `MediaItemVersion{Detail,Summary}ReadModel.cs`; `RecordTypeVersionDetailReadModel.cs` |
| ☐ | X-4.11 | Low | — | *Opened 2026-08-24 closing X-4.10.* `MediaProfilesByVersionIndex` and `MediaItemVersionByMediaItemIndex` exist solely to reconstruct the key shape the base table should have had. After the X-4.10 rotation lands and is verified, both are **redundant** — their GSI1PK/GSI1SK are now the base PK/SK — and each is costing a duplicate write plus duplicate storage on the busiest version tables. Dropping them means switching `ListMediaProfileVersionsHandler` / `ListMediaItemVersionsHandler` from `QueryIndexAsync` to a group-scoped list, then removing the index schema registrations and regenerating the manifest. **Do not bundle with X-4.10** — dropping the GSI in the same change removes the read path's fallback before the new key shape has been verified in a live environment | `MediaProfileByVersionIndexSchema.cs`; `MediaItemVersionByMediaItemIndexSchema.cs` |
| ☐ | X-4.12 | **Med** | — | *Opened 2026-08-24 verifying X-4.10.* **`ProjectionsRebuildCommand.ClearStoreAsync` silently clears nothing for every group-keyed read model.** `src/tools/Cli/Commands/Projections/ProjectionsRebuildCommand.cs:288` calls the **ungrouped** `store.ListAsync(tenantId, …)`, which resolves `BuildPartitionKey(tenantId, null)` — a partition with no group suffix. Every row of a group-keyed model lives under `…#{groupKey}`, so the query returns zero, the loop breaks on the first pass, and the command **reports `0 records cleared` while leaving the table fully populated**. Affects the MediaItemVersion, MediaProfileVersion and RecordTypeVersion pairs (`:234-239`, `:253-257`, `:272-276`) and `FolderChildSummary` (`:216-219`). Pre-existing — the transposed key also had a non-null group key — but squarely in the blast radius, because this is the tool someone reaches for during a rotation. `ProjectionReplay`'s `RotationRunner` rebuilds into a fresh target table rather than clearing, so **the N.1 rotations are not affected**; the hazard is anyone using the CLI instead | `ProjectionsRebuildCommand.cs:288` |
| ☐ | X-4.13 | Low | — | *Opened 2026-08-24 verifying X-4.10.* Three loose ends of the same bug class that the X-4.10 sweep deliberately did not change. **(a)** `RecordTypeVersionReference.CreateDeprecatedProjectionKey` (`:29-32`) is transposed the same way — `(tenantId, recordTypeId, "DEPRECATED")` puts every deprecation sentinel for a tenant in one partition. Functionally correct and it cannot collide (`"DEPRECATED"` is not a valid id), and the table is **unversioned** (`schemaVersion: null`, `media-catalog-record-type-index`), so it sits outside the manifest/rotation machinery — per `RUNBOOK.md` a breaking change there is a manual in-place rebuild, which is why it was not bundled. **(b)** `MediaItemVersionByMediaItemIndexSchema.cs:46` writes a bare `{n:D10}` GSI1SK where the two sibling indexes write `VERSION#{n:D10}` — harmless while each index has one model, a trap when a second is added. **(c)** Draft rows are version `0`, so with the version now in the SK the **working draft sorts first** on an ascending grouped read and is included by `begins_with(SK, "SUMMARY#")` — and draft rows carry live `Title`/`Status` where snapshot rows carry `string.Empty`/`Published`. Already true on the GSI path today; worth documenting before anyone adds the first base-table grouped read | `RecordTypeVersionReference.cs:29`; `MediaItemVersionByMediaItemIndexSchema.cs:46` |
| ☐ | X-4.9 | Low | — | **A dead bucket-naming helper and four false CDK comments** — all in `cdk-magiq-media`, all doc/dead-code, **no infrastructure change and no deploy required**. *Re-verified 2026-08-24: every claim holds, but two of this row's line refs were wrong, the `DeleteObject` claim was understated, and a fourth stale comment was missed. Requirements block below the table.* | `config.ts:9,55-62`; `media-buckets.ts:26-27,40`; `bin/magiq-media.ts:89` |
| ☐ | X-4.7 | **Med** | `asset.scenarios.md`: on a failed virus scan the Processing Worker "moves the S3 object to the quarantine bucket" | **Nothing implements it, and nothing could.** Zero `quarantine` references in `src/`; and in CDK **no Lambda role holds any grant on the bucket** — the Processing Worker gets `buckets.originals.grantRead` only, so it can neither `PutObject` to quarantine nor `DeleteObject` from originals. As deployed, an infected original stays exactly where it was uploaded, in the same bucket the API and QueryApi can read. *Found 2026-08-24 while closing X-4.2* | `magiq-media-stack.ts:578-579` / `asset.scenarios.md:364,385,393` |

#### X-4.9 — requirements

Re-verified against `cdk-magiq-media` on 2026-08-24. All five items are in that repo; **nothing here
changes a synthesized resource**, so this can land on its own `deploy/<user>/<slug>` branch and be
verified with `cdk diff` showing an empty diff. That empty diff *is* the acceptance test.

**Corrections to the row as originally written** — worth reading before working from it:

- The two `media-buckets.ts` line refs were wrong. The `DeleteObject` comment is at **`:26-27`**, not
  `:24`; the "No lifecycle" comment is at **`:40`** (`:41` is the field declaration it sits above).
- The `DeleteObject` claim was **understated**. The full comment reads *"No service role holds
  s3:DeleteObject on any bucket - deletion is managed via lifecycle rules only."* Both halves are false:
  three roles hold delete, **and** there are **no expiration rules anywhere in the file** — every
  lifecycle rule is a `transitions` block plus `abortIncompleteMultipartUploadAfter`. So nothing deletes
  by lifecycle either. The sentence describes a deletion model the stack does not implement in either
  direction.
- A **fourth** stale comment was missed: `bin/magiq-media.ts:89` — `region, // used by bucketName() for
  globally-unique S3 bucket names`. `bucketName` is never called, so `region` is not used for this.
- The row's original ref cell pointed at `media-buckets.ts:57-58`, which is the *correct* code
  (`bucketNamePrefix` + `bucketNamespace`) and needs no change. Kept out of the new ref cell to avoid
  implying otherwise.
- **Not a finding:** `lib/config.d.ts` carries the same stale doc string, but `*.d.ts` is in
  `.gitignore` and `git ls-files` confirms none are tracked. It is a local build artifact — do not edit
  it, it regenerates.

**Required changes:**

| # | File | Change |
|---|---|---|
| 1 | `lib/config.ts:55-62` | **Delete** `bucketName()` and its doc block. Confirmed dead — the only occurrences of the identifier in tracked source are this definition and the three stale comments below. Do **not** "fix" it by adding `-an`: keeping a correct-but-unused second naming path is what let this drift in the first place. |
| 2 | `lib/config.ts:9` | Stale doc on `MediaConfig.region`: *"used to build globally-unique S3 bucket names (see `bucketName`)"*. Replace with what `region` is actually for once (1) lands. |
| 3 | `bin/magiq-media.ts:89` | Drop the `// used by bucketName() …` trailing comment. |
| 4 | `lib/constructs/s3/media-buckets.ts:40` | `/** Processing Worker rendition output. No lifecycle. */` → renditions carry `RenditionStorageTierProgression` (`:131`), the same 90d IA → 365d Glacier IR → 730d Deep Archive progression as originals, plus the multipart abort. State the progression, and note the one real difference from originals: **renditions are not tag-filtered**, so the transitions apply to every object unconditionally. |
| 5 | `lib/constructs/s3/media-buckets.ts:26-27` | Replace the whole "No service role holds s3:DeleteObject … deletion is managed via lifecycle rules only" sentence. Ground truth: `grantReadWrite` (which includes `s3:DeleteObject*`) is held by **apiFn on originals** (`magiq-media-stack.ts:419`), **eventConsumersFn on originals** (`:564`), and **processingWorkerFn on renditions** (`:593`). Quarantine holds **no grants at all** — that part of the surrounding comment is true and worth keeping explicit. And no bucket has an expiration rule, so nothing is deleted by lifecycle. |

**Do not fold in:** the quarantine doc at `media-buckets.ts:42` says *"Infected assets moved here by
Processing Worker"* — that is **X-4.7** (nothing implements it, and the Worker holds no grant on
quarantine), which is a Med code finding, not a comment fix. Correcting the comment here would paper
over it. Cross-reference X-4.7 in the commit message instead and leave the comment for that pass, or
mark it `// TODO(X-4.7): not implemented` if it must be touched.

**Aligned:** `media-events`, `media-sagas` (+ GSI), `media-name-reservations`, `media-idempotency-keys`, `media-tenants`, `media-migrations`, `media-catalog-record-type-index`; both SNS topics; all five SQS pairs with DLQs and depth alarms. Read-model tables are manifest-driven, the two manifest copies are byte-identical, and CI enforces it with a drift gate.

> **Closed 2026-08-24** — X-4.1, X-4.2, X-4.3, X-4.6. X-4.4 and X-4.5 deferred to the queues pass. X-4.7 opened by the same pass. See the session log entry.
>
> **Closed 2026-08-24 (second pass)** — X-4.10, decided and fixed. X-4.11, X-4.12 and X-4.13 opened by it
> and by its verification sweep. The code change is committed but **not yet deployed or rotated** — until
> it is, the affected tables still carry the old key shape and the old rows. See N.1 rows 4, 6, 11 and 12
> for the rotation, and the session log entry.
>
> **Two blockers must clear before this deploys**, both needing a .NET SDK:
> 1. `dotnet run --project src/tools/ProjectionManifest` on the bump commit. `ManifestDriftGateTests` is
>    red until this runs, and `previousVersions` can only capture the outgoing v1 shape while the
>    committed file still describes it.
> 2. **Sync the regenerated manifest into `cdk-magiq-media`.** Its copy at
>    `lib/constructs/dynamodb/projection-tables.manifest.json` is the one CDK actually reads. While it
>    still says `schemaVersion: 1`, `read-models.ts:193` filters the new `retainedPreviousVersions`
>    entries out as no-ops (`1 === 1`) and provisions `-v1` — **no error, no warning** — while the running
>    app resolves `-v2`. The `shapeAt` guard at `:141-148` cannot fire, because it only throws when the
>    requested version differs from the current one. Deploy succeeds; runtime 404s on tables that were
>    never created.
>
> After the fix, `system-spec.md`'s inventory and the CDK are a **clean two-way match** — 46 tables, zero on either side that the other doesn't have. The check is scriptable and worth rerunning before anyone trusts the list again: parse `tableId` out of `projection-tables.manifest.json`, plus the `resourceName(config, '…')` / `projected(…)` literals in `write-indexes.ts`, `platform-tables.ts` and `event-store.ts`, and diff against the leading `` `table` `` cell of each row in the spec table.

### I.5 Branching & deployment

| ✓ | # | Sev | Doc says | Reality | Ref |
|---|---|---|---|---|---|
| ☐ | X-5.1 | High | prod is "⛔ `PROD_ENABLED=false`" | The flag gates only the **image build** in `magiq-media`. The CDK repo's `deploy.yml` has **no `PROD_ENABLED` check at all** — its only guard is `env != 'staging'`. A `v*` tag pushed in `cdk-magiq-media` (e.g. an infra release) resolves to `prod` and **deploys to the production account**. The stated block is one-sided | `branching-and-deployment.md` / `cdk .../deploy.yml:54-56,81` |
| ☐ | X-5.2 | Med | staging "Model B: gated promote"; Tom approves prod | **No GitHub-enforced approval anywhere** — the org plan doesn't support required reviewers on private repos (422). "Tom approves" is process only; the spec presents it as an enforced gate | `branching-and-deployment.md` / `deploy.yml:10-17` |
| ☐ | X-5.3 | Low | "Staging has no config file of its own" | `config/staging.json` exists with a stale `imageTag`. Nothing reads it | `cdk-magiq-media/config/staging.json` |
| ☐ | X-5.4 | Low | Overview diagram: `release/x.y → qa → staging (auto on push)` | Contradicts the same document's quick-reference table and the workflow | `branching-and-deployment.md §Overview` |
| ☐ | X-5.5 | Low | — | CI twice points readers at "AIS-OS todos.md" — a docs-project path retired before the `Z:\claudia` move | `build-and-push.yml:50,55` |

### I.7 Plans folder

| ✓ | # | Sev | Finding | Ref |
|---|---|---|---|---|
| ☑ | X-7.2 | Low | The stub links to `file:///Z:/claudia/…` — unresolvable for every contributor except you, and unresolvable in the published wiki. **CLOSED 2026-08-24** during the plans reorganisation: the `file:///Z:/…` link is gone, replaced by a plain description of where the file sits plus a line telling non-Chase readers to ask him or check the `Media` board. The stub still names a machine-local path — unavoidable, since that is where the content is — but it no longer pretends to be a followable link | `docs/implementation-plans/api-consistency-remediation-plan.md:3` |

### I.8 Stale references & broken links

| ✓ | # | Sev | Finding | Ref |
|---|---|---|---|---|
| ☐ | X-8.1 | Med | `adrs/README.md` lists **`deployment-and-resource-naming.md`** as a current decision document. **The file does not exist** — and the CDK repo also cites it as the authority for its naming function. The rationale is referenced from two repos and stored in neither | `adrs/README.md`; `cdk .../config.ts:47` |
| ☐ | X-8.2 | Low | Two more dead links: `archive/ADR-010 → ../../../repos/magiq-media/media-profile-conformance-plan.md`; `asset.write-model.md → .../media-item.read-model.md` (actual file is `mediaitem.read-model.md`) | |
| ☐ | X-8.3 | Low | No `OneDrive\Magiq\AIS-OS` or `OneDrive\CoworkOS` references survive. Three `Z:\claudia` references remain (`docs/README.md:13`, the plans stub, `archive/ADR-014:58`) — harmless except that they leak a machine-local path into the published wiki | |
| ☐ | X-8.5 | Low | `adrs/README.md` says "the **five** topic documents above" while the table lists **seven** (six of which exist) | |

### I.9 Platform SDK conventions

| ✓ | # | Sev | Finding | Ref |
|---|---|---|---|---|
| ☑ | **X-9.8** | **High** | Stack tables and `mediachangerequest.read-model.md`: ids are "UUID v7, time-sortable", and `SK`-ordered comment threads are creation-ordered "for free" | **CLOSED 2026-08-24 — fixed in `aspnetcore-platform`, with tests. Found by running X-9.4's test, which had never been executed.** `GuidFactory.CreateVersion7()` did `(Guid)Medo.Uuid7.NewUuid7()`. Medo 2.x converts **big-endian** — it preserves the raw UUID bytes — while `Guid` stores its first three fields **little-endian**, so the canonical text rendered as `b3b2b1b0-b5b4-b7b6-…`. One cause, two failures: the version nibble was read from byte 7 (random — it reported **v14**) and the timestamp bytes scrambled across the leading groups, so ids did **not** sort. `IdVersionCoverageTests` predicted this exact diagnosis in its own failure message.<br><br>**Blast radius: every id in the system.** `Id<T>.New()`, all three `IdGenerator` copies and `TenantId.New()` route through that one method. The `#if NET10_0_OR_GREATER` branch (`Guid.CreateVersion7()`) was always correct, so the two branches disagreed — the fix also aligns the .NET 10 upgrade path.<br><br>**Fix:** explicit byte swap of the first three fields in `GuidFactory`, deliberately not `ToGuid(matchGuidEndianess: true)` — Medo 3.0 renamed that parameter and inverted its default. New `GuidFactoryTests` in the platform assert the version nibble, the RFC 4122 variant, ordering across milliseconds *and* within one millisecond, uniqueness, that the leading 48 bits decode to the current Unix ms, and that `Id<T>.New()` inherits it. That guarantee had **no coverage in the repo that makes it** — it surfaced only in a consuming app's tests.<br><br>**⚠ Data consequence, permanent:** ids already written are unique and valid but unordered. Anything treating id order as creation order is correct only for post-fix ids — including `media-change-request-comments`, where `SK` ascending *is* the thread order, so pre-fix threads list arbitrarily and mixed threads are ordered only within their post-fix tail. Noted in `system-spec.md`, `mediachangerequest.read-model.md` and the repo `CLAUDE.md`; no migration is possible without reissuing ids.<br><br>**⚠ Not yet built or run** — no .NET toolchain in the session that wrote it. Needs `dotnet test tests/Magiq.AspNetCore.Tests/`, then a package release.<br><br>**⚠ The release is not a one-package bump.** `GuidFactory` ships in **`Magiq.Platform.Core`**, which `magiq-media` never references directly — it is absent from `Directory.Packages.props` and from every `.csproj`, and arrives transitively through ten packages that each declare `Magiq.Platform.Core 1.1.3.5` (confirmed against `src/hosts/Api/obj/project.assets.json`: `Magiq.AspNetCore.Platform`, `…Platform.Abstractions`, `Magiq.Platform.DynamoDb.Abstractions`, `…ExecutionContext.Abstractions`, `…Hosting`, `…Hosting.Abstractions`, `…Localization.Abstractions`, `…Settings.Abstractions`, `…Tenants.Abstractions`, `…WriteModel.Domain`). NuGet resolves the lowest version satisfying the graph, and `CentralPackageTransitivePinningEnabled` is **false**, so publishing Core alone — or adding a `PackageVersion` entry for it — changes nothing. Either republish the dependent chain (simplest: whole platform at a new `VersionPrefix` in `build/Magiq.AspNetCore.Commons.props`, currently 1.1.3.5; 1.1.3.6 and 1.1.3.7 are already taken by one-off package publishes) so every dependent's Core floor moves and no consumer can resolve the broken Core again, or enable transitive pinning in `magiq-media` and pin Core there — which fixes this repo only and leaves the bad Core resolvable everywhere else | `GuidFactory.cs` (platform); `Id.cs:92`; `IdVersionCoverageTests.cs` |
| ☑ | X-9.4 | Low | — | **CLOSED 2026-08-24 — the test was run, and it failed exactly as predicted.** `IdVersionCoverageTests` (added closing X-9.1) had never been executed; its two suspect facts depended on `(Guid)Medo.Uuid7` preserving canonical byte order, which could not be confirmed from source. It did not: both `EveryIdFactoryProducesAUuidV7` and `IdsAreTimeSortable` failed on every ID type at once, which the test's own message called as `GuidFactory` rather than the ID types. See **X-9.8** for the diagnosis and fix. The test needs no change — it was right | `IdVersionCoverageTests.cs` |
| ☐ | X-9.2 | Low | "`ILogger<T>` only" — two violations in host startup. (`src/tools/Cli/**` is a console app; its `Console.WriteLine` is UI output, not a violation) | `Api/Program.cs:19`; `QueryApi/Program.cs:19` |
| ☐ | X-9.3 | High | See X-3.1 — the outbox rule is the one hard SDK constraint the app materially breaks | |
| ☐ | **X-9.6** | **Med** | `mediaitem.write-model.md`, `mediaprofile.write-model.md` and `system-spec.md § constraint enforcement`: name reservation and event append "are committed atomically" by an ambient `ITransactionScope` + a `TransactionBehavior`; `NameReservationConflictException` is handled by a `NameReservationConflictBehavior` and "handlers never catch it directly" | *Opened 2026-08-24 while closing X-9.5 — the fiction was co-located with the MediatR claim in the same sentences.* **`ITransactionScope`, `TransactionBehavior` and `NameReservationConflictBehavior` do not exist in either repo**, and `ConcurrencyConflictException` (named alongside them in `system-spec.md`) is not a type that exists either. Reality: handlers call `ReserveAsync` then `SaveAsync` as **two separate, un-atomic writes**, and catch `NameReservationConflictException` inline in a `try`/`catch` — the opposite of what the docs say. **A failure between the two leaves an orphaned name reservation**, and nothing releases it, so the name stays permanently unusable in that scope. Concurrency conflicts surface as `EventConcurrencyException` from `DynamoDbEventStore`. Docs corrected to describe the real flow; **the orphaned-reservation gap is a real behavioural hole and is not fixed**. CO-4 found and corrected the same fiction in `collection.write-model.md` on 2026-08-21 but did not sweep its two siblings — this is the rest of that sweep, plus the durability question CO-4 didn't raise.<br><br>**Doc half closed 2026-08-24 (second pass).** All three files now describe the real per-handler flow, with a failure table each. The pass also established that compensation is **not** absent everywhere: `CreateMediaProfileHandler` and `PublishMediaProfileHandler` release the reservation in a `catch (Exception)` around the save before rethrowing — the only two of **25 reserve/swap/move/release call sites across 23 handler classes** that do. (Create puts reserve and save in one `try`; Publish keeps the swap in an earlier separate `try` and compensates the save only.) That compensation is best-effort and does not close the gap: it cannot fire on a Lambda timeout or host kill, the release is itself un-retried, and on publish it releases the new name without restoring the old, leaving a live profile holding **no** reservation. Five handlers (`ArchiveCollection`, `ArchiveFolder`, `ArchiveMediaItem`, `DeprecateMediaProfile`, `DeprecateRecordType`) release *before* saving and so fail in the opposite direction — name freed while the aggregate is still active.<br><br>**Still open, narrowed:** the 23 non-MediaProfile sites have no compensation at all, and several bulk sites (`BulkCreateFoldersHandler:309`, `BulkCreateFoldersByPathHandler:357`, `BulkCreateMediaItemsHandler:213`) catch nothing whatsoever, so a conflict there surfaces as an unhandled exception rather than a 409. Proper fix is the deferred outbox (X-3.1) | `CreateMediaProfileHandler.cs:35-49`; `PublishMediaProfileHandler.cs:105-117`; `CreateCollectionCommandHandler.cs:62-72`; `CreateMediaItemHandler.cs:86-102`; `DynamoDbEventStore.cs:169` |
| ☑ | **X-9.7** | **High** | — | **CLOSED 2026-08-24 — fixed, with tests.** *Found the same day during the X-9.6 doc pass: `MoveMediaItem` was broken end to end — every folder-to-folder media-item move failed with a spurious 409.* The handler moves a title between folder scopes by calling `SwapAsync`, not `MoveAsync`. `SwapAsync` is an extension with signature `(tenantId, ScopeKey scope, string oldName, string newName, OwnerId owner)`, and `ScopeKey` is a `record struct` with implicit conversions **both ways** to `string` — so `SwapAsync(tenantId, oldScopeKey, newScopeKey, title, id)` compiles while binding the **destination scope key as `oldName`** and the **title as `newName`**, entirely within the **source** scope. `DynamoDbNameReservationStore.SwapAsync` executes a swap as a two-leg `TransactWriteItems` whose `Delete` leg is guarded by `ConditionExpression = "OwnerId = :oid"` on the old-name row. That row — a normalised copy of the destination scope key — does not exist, the condition fails, the transaction cancels, and the store raises `NameReservationConflictException`. `MoveMediaItemHandler:65` catches it and returns `409 MediaItemAlreadyExists`. So: no reservation is written, `SaveAsync:73` is never reached, and the caller is told the destination already holds the title. Tier 1 at `:45` *does* check the destination correctly, which makes the false 409 look legitimate. `MoveFolderHandler:128` gets the identical case right with `MoveAsync`. **`MoveMediaItemHandlerTests` cannot catch this** — `SwapAsync` is an extension over the single interface method `ApplyAsync`, so a loose `Mock<INameReservationService>` swallows the malformed intent; a fix needs a test asserting on the `NameReservationIntent` passed to `ApplyAsync`, or an integration test. **Fix (2026-08-24, on `feature/change-requests`):** `MoveMediaItemHandler` now calls `MoveAsync`; the `catch (NameReservationConflictException)` stays, since `MoveAsync` raises the same exception on a genuine destination clash. Tests added: `NameReservationIntentRecorder` (`Catalog.WriteModel.Tests/Shared`) captures the intent handed to `ApplyAsync`, with move/swap-intent assertions on `MoveMediaItem`, `MoveFolder`, `RenameFolder`, `RenameCollection` and `UpdateMediaItemTitle`, plus a conflict-path test on `MoveMediaItem` and an end-to-end assign→move→reuse-in-source→clash-in-destination test in `Catalog.IntegrationTests`. Docs updated in `mediaitem.write-model.md` and `system-spec.md`. **⚠ Not yet built or run — no .NET toolchain in the session that wrote it; Chase to run `dotnet test tests/modules/Catalog/Catalog.WriteModel.Tests/` and the Catalog integration tests before this is trusted.** **Root hazard left open:** the implicit `ScopeKey`↔`string` conversion in the platform still lets a scope key bind to a name parameter anywhere in the registry API — worth an analyzer rule or dropping the `ScopeKey`→`string` direction; not filed as its own finding yet | `MoveMediaItemHandler.cs:61-73`; `DynamoDbNameReservationStore.cs:560-614` (platform); `NameReservationServiceExtensions.cs` (platform); cf. `MoveFolderHandler.cs:126-135` |

**Verified compliant, with the checks run:** central package versions — zero `Version=` attributes across every `.csproj` in `src/` and `tests/`. FastEndpoints not MVC — zero `ControllerBase`. No EF/SQL — no `EntityFramework`, `SqlClient`, `DbContext` or `Npgsql` in `Directory.Packages.props`. All 9 implemented aggregates extend `EventSourced<…>` **and** implement `ITenantScoped`, and every per-module domain-event interface is `ITenantScoped` too. `net8.0` throughout; FastEndpoints 6.2.0 as specced.

### I.10 Error catalog

| ✓ | # | Sev | Finding | Ref |
|---|---|---|---|---|
| ☐ | X-10.1 | Low | Catalog defines **68** error codes as an "exhaustive reference"; **10** exist in code, all in two modules — **58 have no definition and are never emitted**. Severity is Low only because the document's own 2026-08-20 banner is honest about it. The gap itself is large | `error-catalog.md §Implementation status` |
| ☐ | X-10.2 | Med | Two emitted codes are **absent** from the catalog: `ChangeRequestNotFound` and `ChangeRequestRequired` (the latter on a live checkout path). Clients switching on `errorCode` won't recognise them | `ChangeRequestErrorCodes.cs` |
| ☐ | X-10.3 | Med | `ErrorCodeResponseConfigurator` is registered **only in `Api`**. `QueryApi` registers none, so **no read-side response can ever carry an `errorCode`**. The catalog's caveat ("the other seven modules need a one-line change") understates the work — the read host needs it too | `Api/Startup.cs:71-72`; `QueryApi/Startup.cs` |

| ☐ | X-10.5 | Low | — | **No request or response header appears in the generated OpenAPI.** FastEndpoints `Summary`/`Description` blocks document routes, params and status codes, but no endpoint declares `If-Match`, `ETag` or `IdempotencyKey`. The two concurrency endpoints read and write those headers at runtime; a client generating from the OpenAPI document sees no trace of them. Systemic, not specific to concurrency — `IdempotencyKey` is undocumented on every endpoint that accepts it · *Found 2026-08-24* · **Confirmed and extended 2026-08-25 by W29 (plan owns the mechanism half; this finding owns the OpenAPI half).** The mechanism is real — `Magiq.AspNetCore.Idempotency` runs as global middleware on the `Api` host with a CDK-provisioned table — so this is a documentation gap, **not** a missing feature: the middleware reads the raw header and does not care what OpenAPI advertises. Two things that make it worse than 'undocumented': the header is **`Idempotency-Key`**, not `IdempotencyKey` (**X-11.21**), so what little documentation existed was also wrong; and no endpoint declares *any* header, `If-Match`/`ETag` included, so the whole class is invisible to generated clients (**X-11.27** covers the status-code half of the same defect) | `SetMetadataFieldEndpoint.cs:18-50`; `SetMetadataBatchEndpoint.cs` |

Codes present in both catalog and code (8, all MediaItem checkout / ChangeRequest state): `CheckoutLeaseExpired`, `CheckoutNotLeased`, `CheckoutRequired`, `MediaItemCheckedOut`, `MediaItemNotCheckedOut`, `MediaItemNotCheckoutable`, `TooManyCollaborators`, `ChangeRequestNotOpen`.

---

### I.11 Projector names in the spec

| ✓ | # | Sev | Finding | Ref |
|---|---|---|---|---|
| ☑ | X-11.1 | ~~High~~ **closed 2026-08-25** | Traceability tables named projector classes that do not exist | **Bigger than the finding estimated: 10 invented names, 145 references, 28 files** — not 4 names and ~90. `MediaItemProjector` (40), `RecordTypeProjector` (27), `MediaProfileProjector` (22), `CollectionProjector` (17), `AssetProjector` (16), `SigningSessionProjector` (14), plus `ProcessingJobProjector`, `FolderProjector`, `RegistrationProjector`, `ChangeRequestProjector`. **Not one was a class.** **Decision (Chase): the tables name the read-model *table*, not a class.** The deciding fact is that `MediaItemCreated` is handled by **nine** projectors across three modules — any class list in a traceability cell is unreadable *and* stale the moment one is split. Table names are contract, manifest-governed, and answer what a reader actually wants: what does this route change. **Done:** all 145 references rewritten; correction notes that *describe* the phantom keep the phantom name; prose and mermaid participants name the real classes; `read-model.md` per-projector headings corrected to real class pairs — with a note on `mediaitem.read-model.md` listing all nine projectors for `MediaItemCreated` and which two are cross-module integration consumers. `spec/README.md` row 6 and its caution bullet rewritten. **Zero phantom names remain.** **Method note:** the first pass was a blanket substitution and it damaged 61 lines — correction notes turned self-contradictory (*"`media-item` · `media-items` does not exist as a class"*), mermaid participant labels, and prose subjects. Fixed forward line-by-line with context rather than reverted, because the same files carried W24/W25/W28 work. **A blanket rename across a doc tree needs a per-line decision about whether the token is a subject or a reference.** | 28 files · 145 refs |

## K. Coverage & limits

**Verified by direct inspection during this review** (not taken on a subagent's word): P-1; M-6; AM-6; DS-4 constructor argument order; the absence of `publish-wiki.yml`; zero `IOutbox` usages; both `Guid.NewGuid()` sites; the absence of any owner-scope guard outside `ForceReleaseCheckoutHandler`.

**Could not verify:**

- Whether the ADO wiki currently reflects `docs/` — no wiki access from this session. Given X-6.1, assume pre-2026-07-07 content plus manual edits.
- Whether `api-consistency-remediation-plan` items are complete — content is in `plans\Archive\` on this drive; worth a follow-up pass now that the repo side is mapped.
- Whether repo vars `PROD_ENABLED`/`STAGING_ENABLED` are actually `false` — only workflow logic is visible. X-5.1 holds regardless, since the CDK repo never reads `PROD_ENABLED`.
- Whether `deploySearch=true` has ever been passed via a manual `cdk deploy` outside CI.
- Whether the AWS account IDs in `branching-and-deployment.md` are correct — accounts come from GitHub environment vars not visible in either repo.
- Physical DynamoDB attribute-level shapes (`PK`, `GSI1PK`, `EventId`) — key construction lives in `Magiq.Platform.Projections`. Projected *fields* and *index schemas* were compared; the attribute map was not.
- Platform-internal behaviour: `IdempotencyKey` middleware insertion, `ProjectedVersion` dedup short-circuiting, `INameReservationService` `ConsistentRead`, and `IOpenSearchProjectionStore` error handling on a strict-mapping rejection (bears on R-6's failure mode, not its existence).

**One naming disagreement logged rather than filed:** the ChangeRequests aggregate is `MediaChangeRequest` in the repo `CLAUDE.md`, `domain-model.md:295` and `bounded-context.md`, but the class is `ChangeRequest`. The Z:\ `CLAUDE.md` uses `ChangeRequest`. The two `CLAUDE.md` files disagree with each other.

---

# N. Outstanding cross-cutting work

_Compiled 2026-08-22, after the Metadata module closed. Everything here was accumulated across the
AssetManagement, Catalog and Metadata passes and is **not** a drift finding — it is work those passes
created or uncovered, tracked in one place instead of six "still open" tables._

---

## N.1 Projection replay backlog

Three passes fixed projector bugs. **A projector fix corrects future writes; it does not touch the rows
already written wrong.** Every table below is serving incorrect data right now and will keep doing so
until it is rebuilt.

### The correction that matters before anyone runs this

The per-pass notes named the wrong tables. Two of the three entries below are **wider** than the
originating pass recorded, and one names a table that does not exist:

- **`child-items` is not a table.** `FolderChildSummaryProjector`'s own doc comment says
  `Targets: child-items (DynamoDB) table`, and the MediaItem pass copied that into the review. The
  registered name is **`media-folder-children`**
  (`Catalog.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:151`). `rotate --table child-items`
  fails fast with "unknown table" and prints the real list. The projector's comment should be corrected
  too, or the next person repeats this.
- **The MediaProfile pass said "scoped to `media-profiles`". It is three tables.** MP-1 and MP-3 fixed
  the detail, summary *and* version-detail projectors, and those three register against three different
  table names.
- **The Metadata pass said "scoped to `media-record-types`". It is three tables.** The four RecordType
  projectors span `media-record-type`, `media-record-types` and `media-record-type-versions`.

A table's rotation covers **every read model registered against that name**, so where two models share a
table they rebuild together.

### The backlog

| # | Table | Read models on it | What is wrong in the existing rows | From |
|---|---|---|---|---|
| 1 | **`media-folder-children`** | `FolderChildSummaryReadModel` | Every media item ever moved between folders is still filed under its **source** folder. `MediaItemMoved` was not just projecting a duplicate — the move was lost entirely | MediaItem pass (MI) |
| 2 | **`media-profile`** | `MediaProfileDetailReadModel` | `compiledMetadataFields: []` and `suppressedFieldNames: []` on every profile published before MP-1; `leaseDurationMinutes: null` on the published block of every profile regardless of what the tenant configured (MP-3). **Third reason added 2026-08-24 (MI-10):** rows written between MP-1 and MI-10 *have* their compiled fields but every one reads `allowsConcurrentEdit: false`, because the property was never written and deserialises to its default. Wrong for any field the RecordType declared independent — though wrong in the safe direction: it predicts a `409` the write side may not raise, never the reverse | MediaProfile pass (MP) |
| 3 | **`media-profiles`** | `MediaProfileSummaryReadModel` | `leaseDurationMinutes` never carried forward on publish (MP-3). Currently read by nothing — `ListMediaProfiles` reads the *detail* model — so this one is latent, but it rebuilds for free alongside the others | MediaProfile pass (MP) |
| 4 | **`media-profile-version`** | `MediaProfileVersionDetailReadModel` | Same as row 2 — MI-10's `allowsConcurrentEdit` included — on the pinned version snapshots. **The most damaging of the MP set**: an item on v1 of a profile now on v3 must write v1's qualified keys, and the detail row only ever holds the current version's. Same reasoning applies to the flag: `MetadataRebase` evaluates against the pinned snapshot, so this row is the one a client should be reading it from | MediaProfile pass (MP) |
| 5 | **`media-record-type`** | `RecordTypeDetailReadModel` | Three separate defects: any draft where a single field was deprecated has **every** field marked deprecated (M-8); `hasDraft` false on drafts that were emptied rather than discarded (M-13); `aliases` absent entirely (M-9) | Metadata pass |
| 6 | **`media-record-types`** | `RecordTypeSummaryReadModel` **and** `RecordTypeVersionDetailReadModel` | `publishedVersion: 1` on every record type that has never been published, naming a version with no snapshot behind it (M-5); `aliases` absent from the version rows (M-9/M-10) | Metadata pass |
| 7 | **`media-record-type-versions`** | `RecordTypeVersionSummaryReadModel` | `aliases` absent (M-9/M-10) | Metadata pass |
| 8 | **`media-registration`** | `RegistrationDetailReadModel` | Three renames and a split, on every row: the authority reference is in a `ReferenceNumber` attribute nothing reads any more, so `reference` reads back **null on every confirmed registration**; `ExternalReference` likewise for `submissionReference`; the adapter's dispatch note is sitting in `Notes` where the owner's note belongs, and `dispatchDetails` is absent; amendment decision times are in `DecidedAt`, not `ResolvedAt`. `ExpiresAt` is a dead attribute the model no longer declares | Registration pass (R) |
| 9 | **`media-registrations`** | `RegistrationSummaryReadModel` | No field renames — this row is here for the **OpenSearch** side. The `media-registrations` index is new (R-17) and starts empty, and the detail projector only fills it from live events. A rotation of row 8 is what backfills search; until then `GET /v1/registrations/search` returns nothing for anything registered before the deploy | Registration pass (R) |
| 11 | **`media-item-versions`** | `MediaItemVersionSummaryReadModel` **and** `MediaItemVersionDetailReadModel` | **Added 2026-08-24 by X-4.10.** Like row 10, nothing is *wrong* with the existing rows — this is a key-shape migration, not a correction. Both models were keyed `PK = …#{version:D10}`, `SK = {prefix}#{itemId}`; they are now `PK = …#{itemId}`, `SK = {prefix}#{version:D10}`. The old rows are unreachable under the new key, so `GET /v1/media-items/{id}/versions/{n}` **404s and the version list returns empty** from the moment the deploy lands until the rotation completes. Highest-cardinality table of the four — the reason X-4.10 was worth doing | X-4.10 |
| 12 | **`media-profile-versions`** | `MediaProfileVersionSummaryReadModel` | **Added 2026-08-24 by X-4.10.** Same key-shape migration as row 11, same empty-until-rotated consequence for `ListMediaProfileVersions`. Rows 4 and 6 already existed for projector corrections and now carry the re-key too — their `schemaVersion: 2` bump serves both | X-4.10 |
| 10 | **`media-change-requests`** | `ChangeRequestSummaryReadModel` | **Different in kind from rows 1–9 — nothing is wrong with the existing rows.** Both GSIs gained a sort key (CR-11), the bump to `schemaVersion: 2` is already committed, and CDK will provision an empty `-v2`. The replay here is not a correction, it is what makes the new table usable — and until it runs, `GET /v1/change-requests` returns **empty pages** rather than stale ones. **Highest urgency of the ten for that reason.** The v1 table is retained as a rollback target (`retainedPreviousVersions` in `magiq-media-stack.ts`); drop that entry once the rotation is verified | ChangeRequests pass (CR) |

### How to run it

Rows 1–3, 5 and 7–9 are **same-version corruption** — a projection bug dirtied the live table with no
schema change. `RUNBOOK.md § Additive vs. breaking` names the escape hatch for exactly this case: a
rebuild-in-place at the same version is deliberately unsupported, so each table needs its
`schemaVersion` constant bumped to force a clean target table, then a deploy for CDK to create it, then
a rotate.

Rows 4, 6, 10, 11 and 12 are **breaking key changes** under the same clause — rows 4 and 6 carry a
projector correction as well, but the key shape is what makes them breaking. The mechanics are
identical; the difference is the consequence of deploying without rotating, called out under
*Sequencing* below. Note that for the X-4.10 tables the PK/SK **attribute names** do not change, only
the values written into them — so CDK provisions v1 and v2 identically and the manifest's
`previousVersions` entry records an identical shape. That is expected, not a sign the bump did nothing.

Per table:

1. **Bump `schemaVersion: 1` → `2`** on every `AddProjectionSchema` registration for that table name.
   Where two read models share a table (`media-record-types`, `media-item-versions`) **both**
   registrations must move together — the table is versioned as a unit.
   - `media-folder-children` → `Catalog.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:151`
   - `media-profile` → `:168` · `media-profiles` → `:169`
   - `media-record-type` → `Metadata.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:70`
   - `media-record-type-versions` → `:72`
   - `media-registration` → `Registrations.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:68`
   - `media-registrations` → `:69`
   - `media-change-requests` — **already bumped**, 2026-08-23, in
     `ChangeRequests.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:73`. Row 10 needs step 2
     onward only.
   - **Already bumped 2026-08-24 by X-4.10** — rows 4, 6, 11 and 12 need step 2 onward only:
     `media-item-versions` (Catalog `:164` **and** `:166`), `media-profile-versions` (`:172`),
     `media-profile-version` (`:173`), `media-record-types` (Metadata `:71` **and** `:73`).
     `retainedPreviousVersions` in `magiq-media-stack.ts` was updated in the same change.
2. **Land the deploy** so CDK creates the empty `<table>-v2`. The tool never creates tables — it asserts
   the target exists and aborts otherwise. This also means `cdk-magiq-media` may need the new table
   declared; check before assuming the bump alone is enough.

   **Two things learned doing this for real on row 10 (2026-08-23), both of which apply to every row
   here:**

   - **Regenerate the manifest on the same commit as the bump.** `previousVersions` records the
     outgoing shape, the generator can only capture it while the committed file still describes it,
     and CDK needs it to provision the retained table correctly. Miss the moment and the old shape is
     gone from the record.
   - **Add the outgoing version to `retainedPreviousVersions` in `magiq-media-stack.ts`.** It is not
     passed by default. Without it the v1 table leaves the stack on the deploy that creates v2, and
     `removalPolicy` is `DESTROY` outside prod — so the table you are about to rotate *from* is
     deleted, and `rollback` has nothing to point at.
3. **Dry run, then rotate, then verify the read path**, one table at a time:
   ```
   dotnet run --project src/tools/ProjectionReplay -- rotate --table media-record-type --dry-run --env dev
   dotnet run --project src/tools/ProjectionReplay -- rotate --table media-record-type --confirm  --env dev
   ```
   Confirm the dry run shows `active v1 -> target v2`. `active v2 -> target v2` means the deploy has not
   landed or the bump did not take.
4. **Roll back** is an instant pointer swap while the v1 table is still there; `cleanup` drops it only
   after a soak.

### Sequencing and cost

Do them **one at a time, dev first**, verifying the read path between each. They are independent — no
table's rebuild depends on another's — so there is no required order, but rows 5-7 belong to one
aggregate and are best done consecutively so a single API smoke test covers all three.

The replay reads the **full event history per tenant**, so cost and duration scale with total events, not
with the number of bad rows. Rotating seven tables replays the same history seven times. That is the
argument for doing the whole backlog in one session rather than one table per sprint.

**It grew to twelve.** The warning above was written when it was seven, the Registration pass added two
more the same day, CR-11 added the tenth, and X-4.10 added rows 11 and 12 on 2026-08-24 — which is the
argument for scheduling the whole backlog rather than the next projector fix promising to be different.
Rows 8 and 9 are the ones with a user-visible symptom available today: a confirmed registration reads
back with a null `reference` through both `GET /v1/registrations/{registrationId}` and search.

**Rows 10, 11 and 12 change the scheduling calculus.** The other nine are serving *wrong* data and have
been for weeks; another week costs nothing new. These three are the ones where **the deploy itself
creates the problem** — the moment their `schemaVersion: 2` bump reaches an environment, that
environment's change request listings, media item version reads and profile version listings go empty
until the replay runs. Rows 4 and 6 join them: their bump is now a key-shape change too, so they stop
being "stale until rotated" and become "empty until rotated".

That makes five tables where deploy and rotation are a **single operation that cannot be split across
days**. Either hold these deploys until the backlog session is scheduled, or accept that all five rotate
the same day they deploy. It is also the cheapest possible argument for doing all twelve at once: the
replay reads full event history per tenant either way.

**Suggested order for the X-4.10 five**, dev first, verifying the read path between each: row 6
(`media-record-types`) → row 4 (`media-profile-version`) → row 12 (`media-profile-versions`) → row 11
(`media-item-versions`) → row 10 (`media-change-requests`). Smallest-cardinality first, so a key-shape
mistake surfaces on the cheapest rotation rather than the most expensive one.

Note rows 8 and 9 are **not** independent of the OpenSearch side the way rows 1–7 are: rotating row 8
is also what backfills the new `media-registrations` search index, because the detail projector feeds
both. Do that one first if search matters more than the detail read.

---

## N.2 Platform SDK — five gaps, with a ready-to-use prompt

Everything below belongs in **`aspnetcore-platform`**, not in `magiq-media`. Each is something more than
one bounded context needs and the platform does not provide, so each has been worked around locally —
twice already, and ChangeRequests and DocumentSigning will each want a third copy.

_Was three; **N.2.4** was added 2026-08-23. Unlike the first three it has no local workaround, which is
why it changed what CR-11 could implement._

### N.2.1 There is no generic `Conflict` factory

`ErrorType.Business` has `ResourceExists` (409), `ResourceNotFound` (404), `InvalidOperation` (422) and
`ValidationFailed` (400). There is **nothing for a state conflict** — a refusal that is a genuine 409 but
is not "this thing already exists".

`DomainError.EntityAlreadyExists` is the only 409-mapped `Business` error, and its `Title` is
`"Entity Error"`, which reads wrong on "the record type has no open draft". So both places that needed a
409 routed around it through `DomainError.FromErrorCode(409, "Conflict", message)`, which maps
`HttpStatusCode.Conflict` back onto the same `ResourceExists` ErrorType. It works, and it is a workaround
with an explanatory comment attached in two repositories' worth of aggregate code:

- `magiq-media/src/modules/AssetManagement/AssetManagement.Domain/Aggregates/Asset.cs` — private
  `Conflict(string)` helper
- `magiq-media/src/modules/Metadata/Metadata.Domain/Aggregates/DomainErrors.cs` — public
  `Conflict(string)` helper, carrying Chase's own `// todo: move this to platform.`
- `magiq-media/src/modules/Registration/Registrations.Domain/Aggregates/DomainErrors.cs` — third copy,
  added 2026-08-22 (R-13)

### N.2.2 `DomainError` has no error-code concept

`DomainError` carries an `ErrorType`, which fixes the HTTP status and says nothing about *which* rule
refused. The platform documents `extensions.errorCode` as the convention — every error catalog in
`magiq-media/docs/spec/shared/error-catalog.md` is written in those terms — and provides no way to set
one. `WithMetadata(key, value)` exists and is close, but there is no agreed key and no reader.

Catalog, Metadata and Registration therefore each ship a **byte-identical** `DomainErrorCodes` static
class with `WithCode(this DomainError, string)` and `CodeOrNull(this IDomainError)` extensions, because
a module cannot reference another module's Domain project:

- `magiq-media/src/modules/Catalog/Catalog.Domain/Errors/DomainErrorCodes.cs`
- `magiq-media/src/modules/Metadata/Metadata.Domain/Errors/DomainErrorCodes.cs`
- `magiq-media/src/modules/Registration/Registrations.Domain/Errors/DomainErrorCodes.cs` — added
  2026-08-22 (R-13)

**Three copies is the point at which this stops being a workaround and starts being a convention.**
ChangeRequests and DocumentSigning will each want a fourth and a fifth.

### N.2.3 `IProblemDetailsFactory` cannot see a `DomainError` at all

This is the deepest of the three and the reason the first two only half-work.

`Magiq.AspNetCore.Platform.Errors.IProblemDetailsFactory` exposes `CreateProblem(context, statusCode,
title, detail, type)` and `CreateValidationProblem(...)`. **Neither takes an `IDomainError`**, so
`DomainError.Extensions` — where `WithMetadata` and the local `WithCode` both put their data — never
reaches the response. `DefaultProblemDetailsFactory.AddCommonExtensions` writes `traceId`,
`correlationId` and `timestamp` and nothing else.

Consequence in the app: after tagging every Metadata refusal with a code, the endpoints still cannot use
the platform path. They have to reach for FastEndpoints' own
`AddError(message, errorCode)` and read the code back off the error themselves:

```csharp
// magiq-media/src/modules/Metadata/Metadata.WriteModel.Endpoints/V1/MetadataEndpoint.cs
AddError(error.ErrorMessage, error.CodeOrNull());
await SendErrorsAsync((int)error.ErrorType.HttpStatusCode, cancellationToken);
```

So the `errorCode` contract is carried by the *web framework plugin*, not by the platform's own error
pipeline, and anything not using FastEndpoints would silently drop it. `WithMetadata` — which is platform
API — is on the same footing: `RecordTypeAliasNotUnique` attaches `alias` and
`UnrecognisedCapabilityType` attaches `capabilityType`, and **neither reaches the client today**.

### N.2.4 An index query cannot filter — `Matches` is dead against DynamoDB

_Found 2026-08-23 during CR-11._

`IIndexQuery<T>.Matches(T projection)` is an abstract predicate every query in the repo implements, and
every one of them reads like a filter:

```csharp
// ListChangeRequestsByOwnerQuery
public override bool Matches(ChangeRequestSummaryReadModel rm)
{
    return rm.TenantId == TenantId && rm.OwnerId == OwnerId;
}
```

**It never runs in production.** The only caller is
`InMemoryProjectionStore.QueryIndexAsync` (`Stores/InMemoryProjectionStore.cs:231`).
`DynamoDbProjectionStore.QueryIndexAsync` builds a `QueryRequest` from the partition key and the
optional `IndexSortKeyCondition`, sets **no** `FilterExpression`, and returns whatever the index gives
back — `Matches` is not consulted anywhere in that method.

Two consequences, and the second is the dangerous one:

1. **Any predicate a query expresses only in `Matches` is a no-op against DynamoDB.** Today that is
   harmless, because every `Matches` in this repo restates what the partition key already guarantees.
   It is harmless by luck, not by design.
2. **The in-memory store and the DynamoDB store disagree.** A test against the in-memory store proves a
   filter works; the same query in `dev` returns unfiltered rows. Anyone who adds a genuine filter to a
   `Matches` — the natural thing to do, given the signature — gets a green test suite and a wrong API.

This is what stopped CR-11 implementing the specced `Status?` filter. With no `FilterExpression`
support, the only place a filter can live is the sort key, and putting `Status` there costs
chronological ordering across statuses.

**What the platform needs:** either a `FilterExpression` hook on `IProjectionIndexSchema` (or
`IIndexQuery`) that the DynamoDB store translates and applies, or — if filtering is deliberately not
supported — `Matches` should be removed from the interface so it cannot be mistaken for one. The
current state is worse than either: an interface member that looks like a filter, behaves like one in
tests, and is ignored in production.

Note that a DynamoDB `FilterExpression` is applied *after* the read, so it does not reduce RCU and it
interacts badly with pagination — a page can come back nearly empty while `LastEvaluatedKey` is still
set. Whoever implements this should decide how the pager reports that, rather than leaving each caller
to discover it.

### N.2.5 `IReadModelReader` cannot list one parent's children

_Found 2026-08-23 during CR-20._

`IProjectionStore<T>` has two `ListAsync` overloads — tenant-wide, and **group-scoped**:

```csharp
Task<PagedResult<T>> ListAsync(string tenantId, string groupKey, PagerParameters pager, CancellationToken ct);
```

The group overload is the one that answers "all comments on this change request", "all versions of this
item" — the single most common read shape in the platform. `IReadModelReader<T>`, which is what query
handlers are told to inject ("Inject this interface into query handlers only"), exposes only the
tenant-wide overload and `QueryIndexAsync`.

So a handler that needs a parent's children has three options, and all three are bad:

1. Inject `IProjectionStore<T>` directly, against the interface's own guidance. This is what
   `ListChangeRequestCommentsHandler` now does — the only handler in the repo that does.
2. Build a GSI that duplicates what the base table's partition key already answers, paying a
   `schemaVersion` bump and a full-history projection rebuild for it.
3. Call `QueryIndexAsync` and hope — which is what the ChangeRequests comment handler did, against an
   index schema that was never registered, so it threw on every request (CR-20).

**What the platform needs:** the group-scoped `ListAsync` promoted onto `IReadModelReader<T>` and
`ReadModelReader<T>`, forwarding to the store exactly as the tenant-wide one does. It is a four-line
change with no behavioural risk, and it removes the only reason a query handler currently reaches past
the reader.

### Prompt for the `aspnetcore-platform` repo

> Copy from here down.

---

**Context.** Two bounded contexts in the consuming app (`magiq-media`) have independently worked around
three gaps in the platform's error handling. Both workarounds are now duplicated verbatim, and two more
modules are about to need a third copy. The goal is to move the concepts into the platform and delete the
local copies.

**Change 1 — add a state-conflict error type and factory.**

In `src/platform/Domain/Magiq.Platform.WriteModel.Domain/Errors/ErrorType.cs`, add to
`ErrorType.Business`:

```csharp
public static readonly ErrorType Conflict = new Impl(nameof(Conflict), 410, HttpStatusCode.Conflict);
```

Pick an unused `value` — `ResourceExists` is 409, `ResourceNotFound` 404, `InvalidOperation` 422,
`ValidationFailed` 400, and the `Concurrency` pair are both 409, so the numeric `value` is not a status
code and must simply be unique. Do **not** change `ErrorType.FromCode`'s existing
`HttpStatusCode.Conflict => Business.ResourceExists` mapping without checking callers — changing it is a
behaviour change for anyone using `FromErrorCode(409, ...)` today, and at least two call sites do.

In `DomainError.cs`, add a factory beside `EntityAlreadyExists`:

```csharp
/// <summary>
/// Creates a conflict error — the request conflicts with the current state of the target resource, and
/// the caller can resolve it and resubmit the identical request (RFC 9110 §15.5.10). Distinct from
/// <see cref="EntityAlreadyExists" />, which is specifically a duplicate.
/// </summary>
public static DomainError Conflict(string? message = null)
{
    return new DomainError("Conflict", MessageOrDefault(message, () => "Conflict."), ErrorType.Business.Conflict);
}
```

**Change 2 — give `DomainError` a first-class error code.**

Add to `DomainError.cs`, next to the existing `WithMetadata` instance method (currently around line 290):

```csharp
/// <summary>The extension key an error code is carried under, on the error and on the response.</summary>
public const string ErrorCodeExtensionKey = "errorCode";

/// <summary>Returns a copy of this error carrying a stable, machine-readable code.</summary>
public DomainError WithCode(string code) => WithMetadata(ErrorCodeExtensionKey, code);
```

And on `IDomainError` (or as an extension in `DomainErrorExtensions.cs`, which is the better home since
`IDomainError` should stay a pure contract):

```csharp
/// <summary>Reads the error code off an error, or null if it carries none.</summary>
public static string? CodeOrNull(this IDomainError error)
{
    if (error.Extensions is null || !error.Extensions.TryGetValue(DomainError.ErrorCodeExtensionKey, out var value))
    {
        return null;
    }

    return value as string;
}
```

Match the semantics of the existing local implementation exactly — it is already in production use:
`WithCode` returns a **copy** (`DomainError` is a record), preserves any existing extensions, and
overwrites the key if already present. Reference implementation:
`magiq-media/src/modules/Catalog/Catalog.Domain/Errors/DomainErrorCodes.cs`.

**Change 3 — let the problem-details pipeline see the error. This is the important one.**

`IProblemDetailsFactory` in `src/aspnetcore/Platform/Magiq.AspNetCore.Platform.Abstractions/Errors/`
has no overload that takes an `IDomainError`, so `DomainError.Extensions` never reaches the wire.
`errorCode`, and every `WithMetadata` value alongside it, is dropped by the platform today. Add:

```csharp
/// <summary>
/// Creates a problem details object from a domain error, carrying its extensions — including
/// <c>errorCode</c> — onto the response.
/// </summary>
ProblemDetails CreateProblem(HttpContext context, IDomainError error, string? type = null);
```

Implement it in `DefaultProblemDetailsFactory`: derive `Status` from `error.ErrorType.HttpStatusCode`,
`Title` from `error.Title`, `Detail` from `error.ErrorMessage`, then call the existing
`AddCommonExtensions` and copy every entry of `error.Extensions` into `problem.Extensions`.

Two rules for the copy, both of which matter:

- **Do not let a domain extension overwrite `traceId`, `correlationId` or `timestamp`.** Those are
  infrastructure identity; a domain error that happens to attach a key of the same name must not be able
  to forge them. Copy domain extensions **first**, then `AddCommonExtensions`, so the platform keys win.
- **Keep `errorCode` a plain string.** It is a contract clients branch on. If the value stored is not a
  string, omit it rather than serialising something unexpected.

**Also worth doing while in there:** `error.Errors` (the `IReadOnlyDictionary<string, string[]>`
field-level detail) should route to `CreateValidationProblem` when populated, so a `422` with field errors
comes out as a `ValidationProblemDetails` rather than losing the per-field breakdown. Check the current
behaviour before changing it — this may already be handled at the endpoint layer in consuming apps.

**Tests.** Cover: `WithCode` preserves pre-existing extensions and overwrites a repeated key;
`CodeOrNull` returns null for an untagged error and for a non-string value; `Conflict` maps to 409;
`CreateProblem(context, error)` puts `errorCode` under `extensions` and cannot be made to overwrite
`traceId`.

**Consuming-app follow-up** (do not do this in the platform repo — record it for `magiq-media`):
delete `Catalog.Domain/Errors/DomainErrorCodes.cs`, `Metadata.Domain/Errors/DomainErrorCodes.cs` and
`Registrations.Domain/Errors/DomainErrorCodes.cs`; drop the private `Conflict` helper on
`AssetManagement.Domain/Aggregates/Asset.cs` and the public ones on
`Metadata.Domain/Aggregates/DomainErrors.cs` and `Registrations.Domain/Aggregates/DomainErrors.cs`; and
switch all three modules' endpoint base classes from
`AddError(error.ErrorMessage, error.CodeOrNull())` to the new `CreateProblem(context, error)` path. The
`errorCode` values themselves are already published API contract — see
`magiq-media/docs/spec/shared/error-catalog.md` — so **no code string may change** in that cleanup.

---

## N.3 Line endings — `.gitattributes` added, renormalization outstanding

`magiq-media` had no `.gitattributes`, so every clone got whatever the local `core.autocrlf` was. The
working tree drifted to predominantly CRLF while `.editorconfig` asks for LF, and `git diff` on a
non-Windows checkout reported a whole-file rewrite for every CRLF file whether it had been touched or
not — the Metadata pass showed up as 180 files and ~9,000 insertions for what was 53 files and ~610.

**Added 2026-08-22:** `magiq-media/.gitattributes`, declaring `* text=auto eol=crlf` — LF in the
repository, CRLF in every working tree on every OS — with `.sh`, Dockerfiles and `.env*` pinned to LF
because Linux containers read them, and the usual binary declarations.

**Two things remain:**

1. **The one-time renormalization has not been run.** `.gitattributes` does not rewrite what is already
   committed. Until someone runs it, files whose stored bytes disagree with the rule keep producing
   spurious diffs:
   ```
   git add --renormalize .
   git commit -m "chore: renormalize line endings under .gitattributes"
   ```
   On its own branch off `develop`, with nothing else in the commit. It will touch most of the repo.
   Anyone with an in-flight branch should **rebase** onto it rather than merge, or they hit a conflict in
   every touched file — worth a heads-up to Estelle and Akshay before it lands.
2. **`.editorconfig` still says `end_of_line = lf` for C#**, which contradicts `eol=crlf`. That
   disagreement is what produced the drift. Deliberately not changed in the same commit as
   `.gitattributes` — flip it to `crlf` alongside the renormalization so both land together and the
   reason stays legible in one place.

The other three repos (`aspnetcore-platform`, `cdk-magiq-media`, `Media.wiki`) were not checked. Whoever
does the renormalization should check them at the same time — `cdk-magiq-media` is TypeScript and likely
wants `eol=lf` rather than a copy of this file.
