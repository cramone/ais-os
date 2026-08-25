# magiq-media

## Project Overview

C# microservices platform for media asset ingestion, processing, storage, cataloguing, and retrieval. Bounded context within the broader Magiq Documents platform — Identity and Billing are upstream external contexts.

Serves government agencies and large enterprises managing regulated records. Multi-tenant, compliance-grade, event-sourced.

**Current status:** Active — API layer, tenant management, auth, and user security in progress (Q2 2026).

**Owner:** Chase Ramone
**Team:** Chase Ramone (API layer), Akshay Gaikwad (UI/integrations)
**Source code:** `D:\source\github\magiq-media`

## Stack

| Layer | Technology |
|---|---|
| Language | C# (.NET 8) |
| Architecture | DDD · CQRS · Event Sourcing |
| API | FastEndpoints (ASP.NET) |
| Command dispatch | `ICommandDispatcher` (`Magiq.Platform.WriteModel.Commands`) — **not MediatR** (corrected 2026-08-24, drift review X-9.5) |
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
| `ChangeRequests` | `MediaChangeRequest` |
| `Metadata` | `RecordType` |
| `Processing` | `ProcessingJob` |
| `Registration` | `Registration` |
| `DocumentSigning` | `DocumentSigningSession` ⚠️ *skeleton only — no aggregate class exists* |

## Hosts

**There is no single host.** Write and read paths, and each async worker, deploy independently — nine
projects under `src/hosts/`:

| Host | Role |
|---|---|
| `Api` | Write-side FastEndpoints host — command dispatch, upload URL issuance |
| `QueryApi` | Read-side FastEndpoints host — all query traffic (DynamoDB + OpenSearch) |
| `Projectors.ReadModel` | SQS-triggered — maintains DynamoDB read models |
| `Projectors.Search` | SQS-triggered — maintains OpenSearch indexes |
| `EventConsumers` | SQS-triggered — intra-BC cross-module integration event consumers |
| `ProcessingWorker` | SQS-triggered — rendition generation, metadata extraction |
| `SagaOrchestrator` | SQS-triggered — `AssetIngestionSaga` |
| `SagaOrchestrator.DocumentSigning` | Built and pushed every commit, but **nothing deploys it** — no Lambda, no queue |
| `TimeoutScanner` | CloudWatch-scheduled — scans sagas for expired timeouts |

> Corrected 2026-08-24 (drift review X-1.1). This previously read *"Host: `src/hosts/Media.Api` — single
> FastEndpoints host wiring all modules."* No `Media.Api` project has ever existed in the solution; the
> write host is `src/hosts/Api`. The only `Media.Api.csproj` on disk is inside a stale `cdk.out` synth
> artifact. Treat the repo's own `CLAUDE.md` as authoritative for host layout — it is code-reviewed
> alongside the hosts; this file is not.

## ADO Board
Media

## Priority
High

## File Map

| File | Purpose |
|------|---------|
| `brief.md` | Project summary, team, stack, active ADO work |
| `architecture.md` | Architecture overview |
| `use-cases.md` | Use case catalogue |
| `todos.md` | Active todo items |
| `MEMORY.md` | External memory — read at session start |
| `plans/` | All plans — in-flight/pre-decision design work *and* point-in-time, cross-cutting implementation plans (e.g. spec-remediation checklists). **One subfolder per workstream since 2026-08-24** — start at `plans/README.md`, which indexes every plan with its status |
| `plans/README.md` | Index of the plan folders: what each workstream is, which plan is live, what is parked or superseded |
| `decisions/` | Decision log |
| `prompts/` | AI prompts used to produce spec content |
| `reviews/` | Where work starts — review artifacts, in workstream subfolders mirroring `plans/`. Start at `reviews/README.md` |

---

## Review → Plan

**Work goes through a review before it gets a plan.** The review argues the findings; the plan sequences
them and tracks execution. Don't open a plan for something that hasn't been reviewed — if the reasoning
isn't written down somewhere, that gap is the first thing to fix.

`reviews/` and `plans/` mirror each other, one subfolder per workstream:

```
reviews/<workstream>/<review>.md   →   plans/<workstream>/<plan>.md
reviews/<workstream>/Archive/      →   plans/<workstream>/Archive/
```

Three rules:

1. **The folder name is the link.** A review and the plan that consumes it share the workstream folder
   name. That is what survives archiving — when both sides are archived, the pairing is still legible.
2. **Name the plan after the review.** For new work, the plan file takes the review's filename. Where
   several reviews feed one plan — the 2026-07 architecture set is eleven reviews to one plan — the
   shared folder carries the trace instead, and the plan says which reviews it consumes.
3. **Archive both sides together.** When a workstream finishes, its review and plan move to the
   `Archive/` inside their respective folders. A finished workstream leaves a matched pair.

`plans/README.md` and `reviews/README.md` index both trees with status. Update them when adding a
workstream — a folder nobody indexed is a folder the next session won't find.

**One deliberate exception:** `plans/spec-drift-review/spec-repo-drift-review.md` is a review *and* its
own working checklist. It lives on the plans side because that is where its ✓ column is worked; splitting
it would separate the findings from the boxes tracking them.

> **Spec and ADRs moved 2026-07-07.** `spec/contexts/`, `spec/shared/`,
> `spec/architecture/`, and `adrs/` now live in
> `D:\source\github\magiq-media\docs\spec\` and `docs\adrs\` — they're
> code-reviewed there, and that repo is the only source of truth for them —
> there is no published or mirrored copy. Don't recreate them here. This folder
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
