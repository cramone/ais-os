# Project Brief — magiq-media

**Last updated:** 2026-05-03
**Owner:** Chase Ramone
**Team:** Chase Ramone (API layer), Akshay Gaikwad (UI/integrations)
**Full spec:** `projects/magiq-media/spec/` (this repo)
**Source code:** `D:\source\github\sprbrk-standard\mgq-magiq-media`
**Reviews → Plans:** `reviews/` and `plans/` mirror each other, one subfolder per workstream since
2026-08-24, indexed by a README each. Work is reviewed before it is planned; a new plan takes its
review's filename, and both sides archive together — see `CLAUDE.md § Review → Plan`. Live workstreams:
spec-drift review, architecture-review remediation, projection tables, design. Parked: authz + outbox,
deployment naming.

---

## What it is

A C# microservices platform for media asset ingestion, processing, storage, cataloguing, and retrieval. Bounded context within the broader Magiq Documents platform — Identity and Billing are upstream external contexts.

Serves government agencies and large enterprises managing regulated records. Multi-tenant, compliance-grade, event-sourced.

---


## Tech Stack

| Layer | Technology |
|---|---|
| Language | C# (.NET 8) |
| Architecture | DDD · CQRS · Event Sourcing |
| API | FastEndpoints (ASP.NET) |
| Command dispatch | `ICommandDispatcher` (`Magiq.Platform.WriteModel.Commands`) 
| Event Store | DynamoDB (custom append-only) |
| Read Models | DynamoDB + OpenSearch |
| Compute | AWS Lambda (containerised) |
| Messaging | SNS → SQS fan-out |
| Storage | S3 (3 buckets: originals, renditions, docs) |
| Observability | CloudWatch (Serilog), X-Ray |

---

## Modules

| Module | Layers | Core Aggregate(s) |
|---|---|---|
| `AssetManagement` | Domain · Contracts · ReadModel · WriteModel · Endpoints | `Asset` |
| `Catalog` | Domain · Contracts · ReadModel · WriteModel | `Collection`, `Folder`, `MediaItem`, `MediaProfile` |
| `ChangeRequests` | Domain · ReadModel · WriteModel | `ChangeRequest` |
| `Metadata` | Domain · ReadModel · WriteModel | `RecordType` |
| `Processing` | Domain · WriteModel | `ProcessingJob` |
| `Registration` | Domain · ReadModel · WriteModel | `Registration` |
| `DocumentSigning` | Domain · ReadModel · WriteModel | `DocumentSigningSession` |

Host: `src/hosts/Media.Api` — single FastEndpoints host wiring all modules.

---

## Services

| Service | Runtime | Role |
|---|---|---|
| Ingest API | Lambda/ECS (ASP.NET + FastEndpoints) | Upload URL issuance, all write command dispatch |
| Query API | Lambda/ECS (ASP.NET + FastEndpoints) | All read traffic — DynamoDB + OpenSearch |
| Command Handler | Lambda (`ICommandDispatcher`) | Aggregate lifecycle, event store writes, SNS publish |
| Projectors Lambda | Lambda (SQS-triggered) | Maintain DynamoDB + OpenSearch read models |
| Processing Worker | Lambda (SQS-triggered) | Rendition generation, metadata extraction |
| SagaOrchestrator | Lambda (SQS-triggered) | Cross-aggregate coordination (3 saga types) |
| SagaTimeoutScanner | Lambda (CloudWatch scheduled) | Processing timeout enforcement |
| SecuredSigning Adapter | Lambda (SQS + webhook) | SecuredSigning API integration |
| Integration Event Consumers | Lambda (SQS-triggered) | Intra-BC cross-module consumers |

---

## Key Conventions

- All commands return `Result<T, DomainError>` — no domain exceptions escape handlers
- Every aggregate is `ITenanted` — `TenantId` is first field, first parameter, set once, immutable
- DynamoDB PK format: `TENANT#{TenantId}#{EntityId}` on every table
- `TenantId` sourced from JWT `tenant_id` claim (HTTP) or SNS message attribute (SQS) — **never** from payload body
- Optimistic concurrency via DynamoDB conditional writes (`attribute_not_exists(AggregateVersion)`) — retry up to 3×
- Name uniqueness: two-tier (read-model check + `TransactWriteItems` reservation against `media-name-reservations`)
- Integration events published inline in Command Handler by per-module `*IntegrationEventPublisher` classes — no separate Lambda
- Aggregate IDs: UUID v7-based strongly-typed value objects

---


