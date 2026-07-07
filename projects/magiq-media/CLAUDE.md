# magiq-media

## Project Overview

C# microservices platform for media asset ingestion, processing, storage, cataloguing, and retrieval. Bounded context within the broader Magiq Documents platform — Identity and Billing are upstream external contexts.

Serves government agencies and large enterprises managing regulated records. Multi-tenant, compliance-grade, event-sourced.

**Current status:** Active — API layer, tenant management, auth, and user security in progress (Q2 2026).

**Owner:** Chase Ramone
**Team:** Estelle Wu (API layer), Akshay Gaikwad (UI/integrations)
**Source code:** `D:\source\github\magiq-media`

## Stack

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

## Modules

| Module | Core Aggregate(s) |
|---|---|
| `AssetManagement` | `Asset` |
| `Catalog` | `Collection`, `Folder`, `MediaItem`, `MediaProfile` |
| `ChangeRequests` | `ChangeRequest` |
| `Metadata` | `RecordType` |
| `Processing` | `ProcessingJob` |
| `Registration` | `Registration` |
| `DocumentSigning` | `DocumentSigningSession` |

Host: `src/hosts/Media.Api` — single FastEndpoints host wiring all modules.

## ADO Board
Media

## Priority
High

## Q2 2026 Priorities

1. Complete magiq-media API — API layer, query endpoints, write endpoints, FastEndpoints wiring
2. Implement tenant management and authentication — JWT, `IExecutionContext`, `TenantId` isolation, token replay detection
3. Implement user security and policies — command-level authorisation, actor types (System/User/Guest), role-based access

## File Map

| File | Purpose |
|------|---------|
| `brief.md` | Project summary, team, stack, active ADO work |
| `architecture.md` | Architecture overview |
| `use-cases.md` | Use case catalogue |
| `todos.md` | Active todo items |
| `MEMORY.md` | External memory — read at session start |
| `plans/` | Implementation plans (in-flight, pre-decision design work) |
| `decisions/` | Decision log |
| `prompts/` | AI prompts used to produce spec content |
| `reviews/` | Informal spec review artifacts |

> **Spec and ADRs moved 2026-07-07.** `spec/contexts/`, `spec/shared/`,
> `spec/architecture/`, and `adrs/` now live in
> `D:\source\github\magiq-media\docs\spec\` and `docs\adrs\` — they're
> code-reviewed there and publish to the ADO wiki automatically via
> `.github/workflows/publish-wiki.yml`. Don't recreate them here. This folder
> is the AI-operating-system layer — memory, todos, meetings, the decision
> journal, and in-flight plans — not spec custody.

## Key Conventions

- All commands return `Result<T, DomainError>` — no domain exceptions escape handlers
- Every aggregate is `ITenanted` — `TenantId` is first field, set once, immutable
- DynamoDB PK: `TENANT#{TenantId}#{EntityId}` on every table
- `TenantId` sourced from JWT `tenant_id` claim (HTTP) or SNS message attribute (SQS) — **never** from payload body
- Optimistic concurrency via DynamoDB conditional writes — retry up to 3×
- Integration events published inline in Command Handler by per-module `*IntegrationEventPublisher` classes
- Aggregate IDs: UUID v7-based strongly-typed value objects

## Decisions

Architecture decisions (ADRs) now live in `D:\source\github\magiq-media\docs\adrs\` — see `brief.md` for the ADR summary table.

---

## Memory System

This folder contains `MEMORY.md` — external memory for this project.

At the start of every session: Read `MEMORY.md` before responding. Use what you find — do not announce it.

Memory is user-triggered only. Only add entries when the user explicitly asks using phrases like "remember this", "make a note", "log this". Write immediately and confirm.

All memories are persistent until the user asks to remove or change them.

Flag contradictions — never silently overwrite.
