# Project Brief — magiq-media

**Last updated:** 2026-05-03
**Owner:** Chase Ramone
**Team:** Estelle Wu (API layer), Akshay Gaikwad (UI/integrations)
**Full spec:** `projects/magiq-media/spec/` (this repo)
**Source code:** `D:\source\github\magiq-media`

---

## What it is

A C# microservices platform for media asset ingestion, processing, storage, cataloguing, and retrieval. Bounded context within the broader Magiq Documents platform — Identity and Billing are upstream external contexts.

Serves government agencies and large enterprises managing regulated records. Multi-tenant, compliance-grade, event-sourced.

---

## Q2 2026 Priorities

1. **Complete the magiq-media API** — API layer, query endpoints, write endpoints, FastEndpoints wiring
2. **Implement tenant management and authentication** — JWT, `IExecutionContext`, `TenantId` isolation, token replay detection
3. **Implement user security and policies** — command-level authorisation, actor types (System/User/Guest), role-based access

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | C# (.NET 8) |
| Architecture | DDD · CQRS · Event Sourcing |
| API | FastEndpoints (ASP.NET) |
| Mediator | MediatR |
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
| Command Handler | Lambda (MediatR) | Aggregate lifecycle, event store writes, SNS publish |
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

## Known Gaps (from spec — as at 2026-05-04)

| Gap | Status |
|---|---|
| `SigningSessionSummaryProjector` | Deferred — implement when DocumentSigning module is built |
| `DocumentSigningSaga` | Deferred — not registered in `SagaRegistrations` |
| `DocumentSigningTimeoutScanner` | Deferred — not implemented |

---

## Active Work (from Azure DevOps — 2026-05-03)

- **103 active items** assigned to Chase
- **34 tasks in Code Review** — naming service additions across write model commands
- **Active Epics:** Tenant Management, Infrastructure & Host Services, Query API & Read Layer, Write-Model Gaps, Read-Model & Projector Gaps, API Route Corrections, Integration Events & Messaging
- **In Progress Features:** Lambda projector host, cross-cutting infrastructure, query handlers across all modules, write-model completions

---

## Decisions

See `decisions/log.md` for architecture decisions.
Full ADR set at: `C:\Users\chase\OneDrive\CoworkOS\development-projects\projects\media-management\adrs\`

| ADR | Decision |
|---|---|
| ADR-001 | DynamoDB as event store |
| ADR-002 | SNS → SQS fan-out (not DynamoDB Streams) |
| ADR-003 | OpenSearch for search read model |
| ADR-004 | Pre-signed S3 upload (client-direct, no Lambda proxy) |
| ADR-005 | Integration event publishing inline in Command Handler |
| ADR-006 | Uniqueness registry + hierarchy invariants |
