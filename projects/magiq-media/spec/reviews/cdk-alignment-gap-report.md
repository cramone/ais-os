# CDK Alignment Gap Report — magiq-media
**Generated:** 2026-06-12
**CDK repo:** `D:\source\github\cdk-magiq-media`
**Spec root:** `C:\Users\chase\OneDrive\Magiq\AIS-OS\projects\magiq-media\spec\`
**Scope:** Infrastructure gaps only — does not repeat application-code mismatches already documented in `spec/reviews/spec-vs-repo-alignment-report.md`

---

## Executive Summary

The CDK codebase is substantially aligned with the spec. The core infrastructure (event store, read models, write indexes, SNS/SQS topology, S3 buckets, Lambda functions, API Gateways, WAF, OpenSearch) is all present and correctly structured. Five categories of gap remain, ranging from critical missing infrastructure to configuration/hardening items.

| Category | Count | Severity |
|---|---|---|
| Missing tables (spec-defined, not provisioned) | 3 | High |
| Missing SQS queues / triggers (spec-defined, not provisioned) | 2 | High |
| S3 bucket gaps | 2 | Medium |
| IAM / security gaps | 3 | Medium |
| Configuration / environment gaps | 3 | Low–Medium |

**Total distinct findings: 13**

---

## 1. Missing DynamoDB Tables

### 1.1 `media-outbox` — Transactional Outbox Table

**Spec says:** `PRODUCTION-READINESS-PLAN.md` MSG-5/MSG-6 and `AZURE-DEVOPS-WORK-ITEMS.md` Feature 1.2 require a `media-outbox` DynamoDB table as part of the transactional outbox pattern. Schema: PK `EventId`, attributes `TenantId`, `Status` (`Pending`/`Delivered`), `Payload`, `TopicArn`, `CreatedAt`, `AttemptCount`, `TTL`.

**CDK has:** No such table anywhere in `event-store.construct.ts`, `read-models.construct.ts`, `write-indexes.construct.ts`, or `platform-tables.construct.ts`.

**Impact:** Without this table the transactional outbox (MSG-5/MSG-6) cannot be implemented. This is a Phase 1 blocker per the production readiness plan.

**Fix:** Add a new table to `event-store.construct.ts` (it is write-side infrastructure):
```typescript
this.outbox = new dynamodb.Table(this, 'Outbox', {
  tableName: resourceName(config, 'media-outbox'),
  partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  timeToLiveAttribute: 'TTL',
  pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
  deletionProtection: removalPolicy === cdk.RemovalPolicy.RETAIN,
  encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
  encryptionKey,
  removalPolicy,
});
```
Also add a GSI on `(Status, CreatedAt)` for the relay scanner to query `Pending` records efficiently. Add to `allTables` in `magiq-media-stack.ts` so Lambda roles receive read/write grants.

---

### 1.2 `media-bulk-folder-imports` and `media-bulk-media-imports` — Bulk Import Job Read Models

**Spec says:** `spec/shared/bulk-operations.md` and `spec/contexts/Catalog/context-overview.md` define two bulk import job aggregate types (`BulkFolderImportJob`, `BulkMediaImportJob`) with their own read model tables (`media-bulk-folder-imports`, `media-bulk-media-imports`). The `BulkFolderImportWorker` and `BulkMediaImportWorker` Lambda hosts each consume a dedicated SQS queue.

**CDK has:** No `media-bulk-folder-imports` or `media-bulk-media-imports` DynamoDB tables provisioned in `read-models.construct.ts`. No `BulkFolderImportWorker` or `BulkMediaImportWorker` Lambda functions. No `media-bulk-folder-imports` or `media-bulk-media-imports` SQS queues in `sqs-queues.construct.ts`.

**Impact:** Bulk async import jobs cannot be deployed. This is a known spec-defined feature not yet implemented in either the application or the CDK.

**Fix:** When the bulk import hosts are implemented, provision:
- Two read model tables (`media-bulk-folder-imports`, `media-bulk-media-imports`) in `read-models.construct.ts`
- Two SQS queue pairs in `sqs-queues.construct.ts`
- Two Lambda functions in `magiq-media-stack.ts` with SQS event sources
- A fourth S3 bucket (`media-bulk-import-inputs`) per `spec/architecture/system-architecture.md`

---

### 1.3 `media-bulk-import-inputs` — S3 Bucket for Bulk Import Source Files

**Spec says:** `spec/architecture/system-architecture.md` lists four S3 application buckets: `media-source`, `media-renditions`, `media-documents`, and `media-bulk-import-inputs`. The fourth bucket holds uploaded CSV/ZIP files for async bulk import jobs.

**CDK has:** `media-buckets.construct.ts` provisions only three application buckets (`source`, `renditions`, `documents`) plus the `quarantine` bucket. `media-bulk-import-inputs` is absent.

**Impact:** Bulk async import (`BulkFolderImportWorker`, `BulkMediaImportWorker`) cannot store input files.

**Fix:** Add to `media-buckets.construct.ts`:
```typescript
this.bulkImportInputs = base('BulkImportInputs', 'media-bulk-import-inputs', {
  lifecycleRules: [
    { id: 'AbortIncompleteMultipartUploads', enabled: true, abortIncompleteMultipartUploadAfter: cdk.Duration.days(7) },
    { id: 'ExpireInputFiles', enabled: true, expiration: cdk.Duration.days(30) },
  ],
});
```

---

## 2. Missing SQS Queues / Lambda Triggers

### 2.1 `media-bulk-folder-imports` and `media-bulk-media-imports` SQS Queues

Already described in §1.2 above. CDK does not provision these queues or their DLQs. Required when bulk import Lambdas are implemented.

---

### 2.2 Outbox Relay Trigger (EventBridge Scheduler)

**Spec says:** `AZURE-DEVOPS-WORK-ITEMS.md` Feature 1.2 USER STORY 1.2.2 requires an outbox relay Lambda triggered by an EventBridge Scheduler rule (e.g. every 30 seconds).

**CDK has:** No EventBridge Scheduler rule for an outbox relay. `magiq-media-stack.ts` only has the `TimeoutScannerSchedule` EventBridge rule.

**Impact:** The outbox relay process has no trigger. Even after the application code is implemented it will never run.

**Fix:** Add an EventBridge Scheduler rule targeting the outbox relay Lambda. The relay could be a new Lambda function or an additional entry point on an existing function.

---

## 3. S3 Bucket Gaps

### 3.1 `media-source` / `media-documents` — S3 CORS Allows `AllowedOrigins: ['*']`

**Spec says:** `spec/shared/system-spec.md` CORS section states `AllowAnyOrigin` is prohibited in staging/production. The production readiness plan SEC-1/SEC-2 requires CORS hardening.

**CDK has:** `media-buckets.construct.ts` sets `allowedOrigins: ['*']` on the CORS rule for `media-source` and `media-documents` pre-signed PUT upload targets.

**Impact:** This contradicts the CORS policy in the spec. While S3-level CORS for pre-signed PUTs is less impactful than API CORS (the pre-signed URL grants access regardless of origin), it should either be restricted for production or explicitly documented as intentional.

**Fix:** Either restrict to known tenant origins for production (injected via config), or add a CDK comment explicitly documenting why wildcard is acceptable for the pre-signed PUT CORS rule in production.

---

### 3.2 S3 Encryption — SSE-S3 Instead of CMK

**Spec says:** Enterprise compliance requirement. All DynamoDB tables use KMS CMK. The spec does not explicitly require CMK on S3, but parity is implicit for enterprise customers.

**CDK has:** `media-buckets.construct.ts` uses `s3.BucketEncryption.S3_MANAGED` (SSE-S3) on all buckets. DynamoDB uses CMK but S3 does not.

**Impact:** Compliance risk if enterprise customers require CMK-managed S3 encryption. Not an immediate blocker but worth an explicit ADR or comment.

**Fix:** Consider changing to `BucketEncryption.KMS` with a dedicated S3 CMK, or document the deliberate SSE-S3 choice.

---

## 4. IAM / Security Gaps

### 4.1 Overly Broad IAM — Single Combined Role for All SQS Worker Lambdas

**Spec says:** `PRODUCTION-READINESS-PLAN.md` ARCH-2 / `AZURE-DEVOPS-WORK-ITEMS.md` Feature 3.1 specify least-privilege IAM roles per decomposed Lambda function.

**CDK has:** `magiq-media-stack.ts` `makeWorker()` grants `ReadWriteData` on **all** tables (`allTables` — includes event store, sagas, all write indexes, all read models) to every SQS worker Lambda. Specific examples:
- `projectorReadModelFn` — only needs write on read model tables; does not need event store or write index write
- `timeoutScannerFn` — only needs read/write on `media-sagas`; receives write on all tables
- `eventConsumersFn` — only needs write on specific write index tables
- `sagaDocumentSigningFn` / `sagaDocumentSigningWebhookFn` — should not need write access to all read model tables

**Impact:** Blast radius is large if any Lambda is compromised. Phase 3 item per production readiness plan.

**Fix:** This is Phase 3 (ARCH-1/ARCH-2). No immediate CDK change required but tracked as a known gap. Implement per-function IAM scoping when Lambda decomposition occurs.

---

### 4.2 No S3 Tenant-Prefix IAM Condition

**Spec says:** `PRODUCTION-READINESS-PLAN.md` SEC-9 requires S3 IAM policies scoped by tenant prefix condition: `"Condition": { "StringLike": { "s3:prefix": ["${aws:PrincipalTag/TenantId}/*"] } }`.

**CDK has:** S3 grants in `magiq-media-stack.ts` use `bucket.grantReadWrite(fn)` / `bucket.grantRead(fn)` with no prefix condition. All Lambda functions with S3 read can access all tenant objects in the bucket.

**Impact:** A bug in TenantId validation at the application layer would allow cross-tenant S3 data access. Phase 2 security item.

**Fix:** Replace `bucket.grantReadWrite(fn)` with explicit `iam.PolicyStatement` including the `StringLike` condition on `s3:prefix`:
```typescript
fn.addToRolePolicy(new iam.PolicyStatement({
  actions: ['s3:PutObject'],
  resources: [`${this.buckets.source.bucketArn}/*`],
  conditions: { StringLike: { 's3:prefix': ['${aws:PrincipalTag/TenantId}/*'] } },
}));
```

---

### 4.3 No `Content-MD5` / Checksum Condition on Pre-Signed PUTs

**Spec says:** `PRODUCTION-READINESS-PLAN.md` SEC-10 and STOR-3 require upload integrity verification via `Content-MD5` or `x-amz-checksum-sha256` conditions on pre-signed PUTs.

**CDK has:** No S3 bucket policy condition enforcing checksums on PUTs. This is primarily an application-layer concern (pre-signed URL generation) but the S3 bucket policy can enforce it as an additional control.

**Impact:** Low CDK impact — primarily an application-code change. No CDK construct change strictly required unless bucket policy enforcement is desired.

---

## 5. Configuration / Environment Gaps

### 5.1 CORS Allowed Origins Not Injected via CDK for Lambda APIs

**Spec says:** `PRODUCTION-READINESS-PLAN.md` SEC-3 specifically calls out: "Add production CORS configuration to CDK environment config."

**CDK has:** `baseEnv()` in `magiq-media-stack.ts` does not include a `Media__Cors__AllowedOrigins` key. The application currently uses `AllowAnyOrigin()` in `Startup.cs`, and CDK provides no mechanism to override this per environment.

**Impact:** Production will launch with wildcard CORS unless this is fixed. Phase 1 blocker (SEC-1/SEC-2/SEC-3).

**Fix:** Add to `MediaConfig`:
```typescript
corsAllowedOrigins?: string[];
```
Add to `baseEnv()` in `magiq-media-stack.ts`:
```typescript
...(config.corsAllowedOrigins ? { Media__Cors__AllowedOrigins: config.corsAllowedOrigins.join(',') } : {}),
```
Supply the production origins list in the stack config for the `prod` environment.

---

### 5.2 Rate Limiting Not Configured at API Gateway Level

**Spec says:** `spec/shared/system-spec.md` Rate Limiting section defines per-actor-type tiers. `PRODUCTION-READINESS-PLAN.md` API-4 and INF-4 require per-tenant write rate limiting and API Gateway usage plans.

**CDK has:** `api-gateway.construct.ts` sets stage-level throttling (`throttlingBurstLimit`/`throttlingRateLimit`) — coarse global limits (500 rps / 1000 burst dev; 2000 rps / 5000 burst prod). No usage plans, API keys, or per-tenant rate limiting is provisioned.

**Impact:** No per-tenant or per-actor-type rate enforcement at the API Gateway layer. Phase 2 item (INF-4).

**Fix:** Define API Gateway usage plans in `api-gateway.construct.ts` and/or implement application-layer rate limiting using SSM-configured tiers.

---

### 5.3 `ASPNETCORE_ENVIRONMENT` Hardcode in Application Code (Not a CDK Gap)

**CDK correctly sets:** `ASPNETCORE_ENVIRONMENT: isProd(config) ? 'Production' : 'Development'` — this is correct.

**Application gap (not CDK):** `Startup.cs:58` has `var isDevelopment = true;` hardcoded (MSG-1). The fix is in the application code, not the CDK.

_No CDK action required._

---

## 6. Items Verified as Correctly Aligned

These were explicitly checked and found to match the spec:

| Spec Requirement | CDK Status |
|---|---|
| `media-events` event store with PK/SK, PITR, CMK | Correct — `event-store.construct.ts` |
| `media-sagas` with `SagaTypeByTimeout` GSI | Correct — `event-store.construct.ts` |
| KMS CMK on all DynamoDB tables with annual rotation | Correct — shared `dynamoDbKey` |
| PITR on all read model and write index tables | Correct — all constructs |
| Deletion protection on prod tables | Correct — `removalPolicy === RETAIN` guard |
| Two SNS topics (`media-domain-events`, `media-integration-events`) | Correct |
| Five MM-owned SQS queues with DLQs and CloudWatch alarms | Correct |
| `media-signing` SQS subscribed to `media-domain-events` | Correct |
| `media-document-signing` retained with SNS subscription disabled | Correct |
| `media-projector-search` gated on `deploySearch` flag | Correct |
| `media-source` lifecycle (Standard → IA → Glacier Instant → Deep Archive) | Correct |
| `media-renditions` lifecycle mirrors source | Correct |
| `AbortIncompleteMultipartUploads` on source, renditions, documents | Correct |
| `media-quarantine` bucket (no app role access) | Correct |
| WAFv2 REGIONAL Web ACL with three managed rule groups (priorities 10/20/30) | Correct |
| X-Ray tracing on all Lambdas and API Gateway stages | Correct |
| CloudWatch saga approaching-timeout alarms (ProcessingDispatched, AwaitingValidation) | Correct |
| SagaTimeoutScanner on 5-minute EventBridge schedule | Correct |
| OpenSearch domain gated on `deploySearch` flag | Correct |
| Separate Write API and Query API Lambda + API Gateway | Correct |
| DocumentSigning SQS + Webhook Lambda + Webhook API Gateway | Correct |
| SNS topic ARNs injected into Lambda env | Correct |
| S3 bucket names injected into Lambda env | Correct |
| Query API is read-only (no event store or write index grants) | Correct |
| `media-signing-sessions` read model provisioned | Correct |
| All write index tables: folder hierarchy, profile resolution, name reservations, etc. | All correct |
| Platform tables: idempotency keys, used JTIs, tenants, migrations, all with TTL | Correct |
| `ASPNETCORE_ENVIRONMENT` correctly set per environment | Correct |
| `Platform__DynamoDB__TableSuffix` correctly set per environment | Correct |

---

## Prioritised Action List

### P0 — Production Blockers

| ID | Action | File | Spec ref |
|---|---|---|---|
| CDK-1 | Add `media-outbox` DynamoDB table with TTL + `(Status, CreatedAt)` GSI | `event-store.construct.ts` | MSG-5/MSG-6 |
| CDK-2 | Add `Media__Cors__AllowedOrigins` env var injection to CDK config and `baseEnv()` | `magiq-media-stack.ts`, `config.ts` | SEC-1/SEC-2/SEC-3 |

### P1 — Pre-Production

| ID | Action | File | Spec ref |
|---|---|---|---|
| CDK-3 | Add EventBridge Scheduler rule for outbox relay Lambda | `magiq-media-stack.ts` | MSG-6 Feature 1.2 |
| CDK-4 | Add S3 tenant-prefix IAM conditions on all S3 grants | `magiq-media-stack.ts` | SEC-9 |

### P2 — When Bulk Import Is Implemented

| ID | Action | File | Spec ref |
|---|---|---|---|
| CDK-5 | Add `media-bulk-import-inputs` S3 bucket | `media-buckets.construct.ts` | system-architecture.md |
| CDK-6 | Add `media-bulk-folder-imports` and `media-bulk-media-imports` DynamoDB tables | `read-models.construct.ts` | bulk-operations.md |
| CDK-7 | Add `media-bulk-folder-imports` and `media-bulk-media-imports` SQS queues + Lambda functions | `sqs-queues.construct.ts`, `magiq-media-stack.ts` | bulk-operations.md |

### P3 — Post-Production

| ID | Action | File | Spec ref |
|---|---|---|---|
| CDK-8 | API Gateway usage plans / per-tenant rate limiting | `api-gateway.construct.ts` | INF-4 |
| CDK-9 | Per-function IAM scoping (Lambda decomposition) | `magiq-media-stack.ts` | ARCH-1/ARCH-2 |
| CDK-10 | S3 CORS wildcard — restrict or document intentionally | `media-buckets.construct.ts` | SEC-1 |
| CDK-11 | S3 KMS CMK encryption — evaluate parity with DynamoDB | `media-buckets.construct.ts` | STOR-5 compliance parity |

---

*Last updated: 2026-06-12*
*Source: CDK review against spec/architecture, spec/shared, spec/reviews/PRODUCTION-READINESS-PLAN.md, spec/reviews/AZURE-DEVOPS-WORK-ITEMS.md*
