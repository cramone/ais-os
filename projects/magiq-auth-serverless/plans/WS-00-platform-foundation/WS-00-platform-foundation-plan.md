---
id: MAS-001
type: plan
project: magiq-auth-serverless
workstream: WS-00-platform-foundation
repo: magiq-auth-serverless + mgq-magiq-auth-infra + mgq-dotnet-platform
tags: [foundation, platform, cdk, bootstrap]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
---

# WS-00 — Platform foundation

**Blocks every other workstream.** One-time shared infra, bootstrap library, CDK stacks, scaffold template.

## Session invocation

> Picking up WS-00 (plan MAS-001). Platform foundation — shared Lambda bootstrap, base Docker image, CDK event store + messaging + KMS stacks, module scaffold template, CI gates. Spec: `docs/spec/architecture/hosts.md`, `docs/spec/architecture/system-architecture.md`, `docs/spec/shared/operations.md`, `docs/spec/shared/event-store-and-messaging.md`.
>
> `mgq-dotnet-platform` is the only app codebase that may be consulted for existing patterns.

## Phase 0 — Scope + platform SDK audit ✓
- [x] Read `mgq-dotnet-platform/CLAUDE.md` (now `mgq-dotnet-platform` under Sprbrk-Standard)
- [x] Enumerate what `Magiq.Platform.*` + `Magiq.AspNetCore.*` already provide (DI, command dispatcher, middleware, event store adapter, SNS publisher)
- [x] List gaps that WS-01 will trip over; file dependency-gap entries where missing — F004–F009 filed under `docs/dependency-gaps/platform-capabilities/`
- [x] Pin .NET 8 arm64 Lambda base image choice (held at .NET 8 for `mgq-dotnet-platform` compat) — `public.ecr.aws/lambda/dotnet:8` (AWS-maintained, arm64, SnapStart-compatible)

## Phase 1 — Shared hosting library ✓ (scaffold)
- [x] `src/hosts/_Shared/Magiq.Auth.Hosting/` project — compiles clean
- [x] Lambda entry-point helper (`LambdaBootstrap.CreateBuilder` / `BuildApp`)
- [x] Serilog wiring (CloudWatch sink pin, correlation-id enrichers; config driven from `appsettings`)
- [x] X-Ray wiring (AWS SDK handler + ASP.NET Core trace header)
- [x] FastEndpoints DI extensions + RFC 7807 ProblemDetails writer per `api-conventions.md`
- [x] `IExecutionContext` population middleware (CorrelationId resolved from `X-Correlation-Id` header; Actor/TenantId leg via `Magiq.AspNetCore.Tenants`)
- [x] `ICommandDispatcher` middleware pipeline slot reserved; concrete handler registration happens per slice via `Magiq.Platform.WriteModel.Application` fluent builder

## Phase 2 — Base Docker image (scaffolded; outstanding build + push)
- [x] `src/hosts/_Shared/BaseImage/Dockerfile` — arm64, public.ecr.aws/lambda/dotnet:8
- [x] .NET 8 arm64 runtime — SnapStart caveat: container-image Lambdas not SnapStart-eligible; hot path relies on provisioned concurrency floor
- [x] Common native deps — libicu, OpenSSL, zlib baked into AWS base image; no additional installs needed at base layer
- [ ] Build + push to ECR as `mgq-magiq-auth-base:latest` — blocked on Docker Desktop running + AWS creds + ECR repo provisioned in `mgq-magiq-auth-infra`; `scripts/build-base-image.ps1 -EcrRegion <region>` runs the build and push

## Phase 3 — Module scaffold template + developer tooling ✓
- [x] `src/_template/__MODULE__/` with 8-layer split (Domain / Contracts / WriteModel + .Endpoints + .Infrastructure / ReadModel + .Endpoints + .Infrastructure) — compiles clean after scaffold
- [x] Prefilled `.csproj` with correct project refs (central-managed via `Directory.Packages.props`)
- [x] Aggregate stub — `EventSourced<TAggregate, TId>` with `IEntityId` struct id, `ITenantScoped` marker, `Emit`/`When` platform pattern (confirmed against BankAccount test aggregate in `mgq-dotnet-platform`)
- [x] Projector stub — placeholder for `IEventProjectionHandler<T>` (SDK interface wiring deferred to first slice)
- [x] Integration-event-publisher stub — `IDomainEventMapper`-style mapper; SNS attrs added by outbox-drain Lambda per spec amendment
- [x] Scaffolding script `scripts/new-module.ps1 -Name <X> -Aggregate <Y> -Type auth.<z>` — tool A
- [x] Spec-to-test extractor `scripts/scaffold-tests.ps1 -Scenarios <path> -Module <X>` — tool B (verified against `tenant.scenarios.md`: 40 bullets extracted)
- [x] `/next-ws` slash command — `.claude/commands/next-ws.md` — tool C (local-only, `.claude/` gitignored)
- [x] `/wrap-ws` slash command — `.claude/commands/wrap-ws.md` — tool D (local-only)

## Phase 4 — CDK event-store stack (`mgq-magiq-auth-infra`)
- [ ] `auth-events` Global Table — PK/SK per `event-store-and-messaging.md § DynamoDB tables`
- [ ] `auth-snapshots` Global Table
- [ ] `auth-name-reservations` Global Table
- [ ] GSI definitions where spec names them
- [ ] Point-in-time recovery enabled; retention per `retention-and-disposition.md`

## Phase 5 — CDK messaging stack
- [ ] SNS topics `auth-domain-events`, `auth-integration-events`, `auth-security-events`
- [ ] DLQ factory with `maxReceiveCount = 5` default per `event-store-and-messaging.md § Consumer DLQ policy`
- [ ] DLQ alarm templates — P1/P2/P3 thresholds per `operations.md`

## Phase 6 — CDK KMS stack
- [ ] KEK pool `alias/auth/user-dek-kek-000` … `099` (ADR-020) — multi-region keys per ADR-018
- [ ] Platform-scoped keys: `alias/auth/external-provider-secret`, `alias/auth/notification-payload-key`, token signing MRK
- [ ] Secrets Manager namespace `auth/tenant-erasure-salt/*` (ADR-009) write-once policy

## Phase 7 — CDK observability
- [ ] CloudWatch dashboard — per host p99, DLQ depth, DynamoDB throttles
- [ ] X-Ray service map
- [ ] Standing alarms per `operations.md § Alarms`

## Phase 8 — Per-host IAM factory
- [ ] CDK construct that emits least-privilege execution role for a host given its (context, role) pair
- [ ] Enforces: projectors cannot write `auth-events`; write hosts cannot read Audit tables; etc.

## Phase 9 — CI gates
- [ ] `.github/workflows/build-and-push.yml` — build hosts, push images, hand off to infra repo
- [ ] `docs_guard` on every PR to `docs/`
- [ ] `dotnet build` + `dotnet test` per module + integration test matrix
- [ ] `cdk synth` on infra PRs

## Phase 10 — Validation slice
- [ ] Deploy a no-op `_template` host to dev
- [ ] Round-trip: HTTP POST → command → event → SNS → SQS → DLQ (forced failure) → alarm
- [ ] Confirm X-Ray trace, Serilog correlation, IAM scoping

## Exit criteria

- Scaffolding script spawns a fresh module in <5 min
- CDK deploys clean to dev
- No-op slice round-trips through full plumbing
- Platform SDK gaps either filled in `mgq-dotnet-platform` or filed as dependency gaps

## Session log

- 2026-10-15: plan drafted
- 2026-10-16: Phase 0 complete. Three decisions pinned — (1) hold at .NET 8 for `mgq-dotnet-platform` compat; (2) follow ADR-005 inline integration-event publisher; (3) acknowledge non-ES opt-out — amended `mgq-dotnet-platform/CLAUDE.md` constraint #3 (branch `feature/chase/MAS-001-non-es-opt-out` on `Sprbrk-Standard/mgq-dotnet-platform`). Filed 6 platform-SDK gaps F004–F009. Base image `public.ecr.aws/lambda/dotnet:8`.
- 2026-10-16: Platform SDK audit (post-merge) resolved F006 + F009 against existing SDK primitives (`Magiq.Platform.UniquenessRegistry`, `TransactionalOutboxCommandMiddleware`). Spec amended to always-outbox model. Platform PRs merged on both repos. MAS-017 opened for the four remaining SDK gaps (F004, F005, F007, F008).
- 2026-10-16: Phase 1 scaffold landed (`src/hosts/_Shared/Magiq.Auth.Hosting`). `dotnet build` clean. Composition root + middleware pipeline reserved; real appsettings config, JWT claim parsing, and slice-specific command-handler registration land when MAS-002 (Tenant) exercises them.
- 2026-10-16: Phase 2 scaffold landed (`src/hosts/_Shared/BaseImage/Dockerfile` + `scripts/build-base-image.ps1`). Docker Desktop daemon not running in dev shell + ECR repo not yet provisioned, so no actual push yet; infra PR in `mgq-magiq-auth-infra` provisions the ECR repo and gates the push.
- 2026-10-16: Phase 3 scaffold landed. Template builds clean through scaffold script. scaffold-tests.ps1 verified against Tenant scenarios file (40 extracted). Platform-SDK pattern probe clarified real shapes (`IEntityId` struct, `Emit`/`When` not `RaiseEvent`, no custom `Id<T>` base in SDK — magiq-auth-serverless rolls strongly-typed ids directly per aggregate).
