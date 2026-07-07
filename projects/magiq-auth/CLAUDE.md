# MAGIQ Auth

## Project Overview
Central identity, tenant, onboarding, and access-management platform for all MAGIQ cloud applications and APIs. Handles tenant lifecycle, user management, authN/authZ, onboarding flows, tenant switching, token issuance, identity federation (Azure AD SSO), and identity/event propagation to downstream MAGIQ apps.

## Status — current system vs. migration target
- **Current system: live in production, actively developed.** `D:\source\github\magiq-auth` is a mature, deployed .NET codebase with real customers, real infra, and an open PR/plan pipeline (see "In-Flight Work" below). This is what you're actually working in day to day.
- **Migration target: scaffolded only, spec not started.** The repo also contains empty solution folders (`AuthServer.*`, `Identity.*`, `Login.RazorUI`, `Infrastructure.*`) staking out the future DDD/CQRS/FastEndpoints/DynamoDB architecture — no `.cs` files exist in them yet, no migration spec written. "Draft — spec not yet started" (below) refers to *this* future migration, not the current running system.

This workspace (`Z:\claudia\magiq\projects\magiq-auth`) is planning/tracking only — no source code lives here. The code repo is the connected folder `D:\source\github\magiq-auth`.

## Stack: Current vs. Future Migration Target

`brief.md`'s original stack line (`C# .NET 8, DynamoDB, Lambda, Openiddict, Fast-endpoints`) describes where this system is **migrating to**, not what's deployed today. Both are documented below so it's clear which one applies to a given task — bug fixes and features on the running system use "Current"; anything scoped as part of the rewrite uses "Future".

### Current (what's actually deployed and running today)

| Layer | Technology |
|---|---|
| Runtime | C# / ASP.NET Core, .NET 8 |
| Web | `MagiqAuth.Web` — Razor MVC |
| API | `MagiqAuth.Api` |
| Identity provider | `MagiqAuth.IDP` — **IdentityServer4 4.1.2** |
| DI | Autofac 6.4, via `IDependencyRegistrar` implementations |
| Database | **MySQL** (Amazon RDS) via Pomelo EF Core provider |
| Migrations | Raw SQL scripts in `scripts/` and `migrations/mysql/` — no EF Code First migrations |
| Cache | Redis / Valkey (`RedisCacheManager`; Valkey Serverless-compatible — no cross-slot multi-key ops) |
| Logging | NLog → local disk → CloudWatch Agent ships to CloudWatch Logs. App has **no AWS SDK dependency** — the agent handles shipping. |
| Hosting | **EC2** (2 nodes per environment) behind RDS. Deploy via VS "Publish to Folder" + WinSCP FTP + `magiq.install.sh`. Docker publish path also exists (`dotnet publish --os linux`). |
| Testing | xunit |
| Validation | FluentValidation |

### Future (migration target — scaffolded, unimplemented)

| Layer | Planned technology |
|---|---|
| Identity provider | Openiddict (replaces IdentityServer4) |
| API framework | FastEndpoints (replaces MVC controllers) |
| Database | DynamoDB (replaces MySQL/RDS) |
| Hosting | AWS Lambda (replaces EC2) |
| Architecture | DDD/CQRS + read models |

Empty solution folders already exist in the repo staking out this shape: `AuthServer.Api/.Application/.Contracts/.Domain/.Infrastructure/.ReadModel.Abstractions/.ReadModel.Infrastructure`, `Identity.Api/.Application/.Contracts/.Domain/.Infrastructure`, `Login.RazorUI`, `Infrastructure.Application.Abstractions/.Domain.Abstractions/.FastEndpoints.Extensions/.Infrastructure.Abstractions/.ReadModel.Abstractions` — consistent with the org's target architecture (see magiq-media conventions). Nothing is implemented yet and no migration spec exists (that's the work `spec/` is reserved for). Treat any "FastEndpoints," "Openiddict," "DynamoDB," or "Lambda" reference in older docs as describing this future state, not the current system.

## Solution Layout (current/legacy)

| Project | Purpose |
|---|---|
| `MagiqAuth.Web` | Razor MVC front-end |
| `MagiqAuth.Api` | REST API |
| `MagiqAuth.IDP` | IdentityServer4 host — OIDC/OAuth2 endpoints, client store |
| `MagiqAuth.Client` | Client app |
| `MagiqAuth.Core` | Domain entities, configuration, security (claims factory, encryption) |
| `MagiqAuth.Data` | EF Core mappings |
| `MagiqAuth.Services` | Business/service layer (Authentication, Customers, Users, Caching, Logging, Messages, Security, Tasks) |
| `MagiqAuth.Web.Framework` | Shared MVC framework, DI extensions, FluentValidation wiring |

## Domain / Multi-Tenancy Model

- **Customer = tenant.** `UserCustomer` is the user↔tenant join table.
- **Claims** are centralized in `MagiqClaimsFactory` (constants) and issued via `IMagiqJwtTokenFactory` (post claims-normalization work — see below). Don't hand-roll claim type strings in new code.
- **Machine-to-machine auth:** `ApiClient` entity, tenant-scoped (`CustomerId`/`CustomerGuid`), OAuth2 client-credentials grant via IS4, single `magiq-api` scope for now.
- **Tenant switching — two parallel, non-overlapping mechanisms:**
  - Cookie-based web session switch: `POST /api/v2/auth/switch` (Bearer JWT in, rewritten MAGIQ/Perf/Doc cookies out) — for browser/webview clients.
  - OIDC-native token exchange (RFC 8693): `POST /connect/token` with `grant_type=urn:ietf:params:oauth:grant-type:token-exchange` — for headless bearer-only clients (e.g. the VSTO Office add-in).
  - A client needing both (e.g. VSTO embedding a cookie-checking MAGIQ view) calls both endpoints — neither replaces the other.
- **External IdP / SSO:** Azure AD per customer via OIDC dynamic schemes. Currently config-driven (`appsettings.json` → `ExternalProviders`); a plan exists to move this to a DB-backed `ExternalProvider` table for zero-restart provider management (`plans/external-providers-plan.md`).

## In-Flight / Planned Work (see `plans/`)

| Plan | Status | Summary |
|---|---|---|
| `claims-normalization.done` | Done | Central `IMagiqJwtTokenFactory`, fixed silent `JwtTokenBuilder.AddClaims` no-op bug, aligned claim type names across JWT/OIDC paths |
| `client-credentials-plan.done` | Done | OAuth2 client-credentials grant (`ApiClient` entity) + fixed hardcoded `"secret".Sha256()` across all OIDC clients |
| `tenant-switching-plan.md` | In progress | Cookie switch (v1, built) + new OIDC token-exchange grant for VSTO + audit-logging gap fixes for both mechanisms |
| `customer-deletion-plan.md` | Open — has unresolved decisions | Soft/hard delete design; open items: MySQL username collision on name reuse (recommends keying off `CustomerGuid` instead of `Name`), hard-delete retention window length, authorization policy tier, whether IS4 PersistedGrant revocation needs new wiring |
| `external-providers-plan.md` | Open | Move Azure AD SSO config from `appsettings.json` to a DB-backed `ExternalProvider` table with dynamic ASP.NET Core scheme registration (no restart needed) |

## Known Issues / Security Debt

From `PRODUCTION_CODE_AUDIT_REPORT.md` (2026-06-01 audit) and related cleanup plans in the code repo:
- Hardcoded service credentials in `MagiqAuthenticationService.CallWebService()` (Critical — Documents API creds committed to source).
- `EncryptionService` AES methods use ECB mode (Critical — breaks performance-session cookie confidentiality).
- Hardcoded OIDC client secret (`"secret".Sha256()`) — **fixed** by `client-credentials-plan.done`, but confirm rollout to all existing `AppRegistration`/`Customer` clients is complete before removing the legacy fallback.
- Two competing logging systems (custom SQL-backed `ILogger` vs. `Microsoft.Extensions.Logging`) being separated into `IAuditLogger` (audit events) vs. diagnostics — see `AuditLogging-Separation-Plan.md` in the code repo.
- `sync-to-async-review-plan.md` in the code repo tracks an ongoing async-conversion PR review (includes a Redis `RemoveByPrefixAsync` N-round-trip fix for Valkey Serverless).

## Open Questions (`notes.md`)

- Redirect URI validation must check **hostname**, not just port — port-only matching is insufficient. (Captured 2026-06-02; not yet confirmed resolved — check `MagiqAuth.Web.Framework` redirect URI validator before closing.)

## Environments

| Environment | Domain |
|---|---|
| Production | magiqcloud.com |
| Development | magiqdev.cloud |
| Demo | demo.magiq.cloud |
| QA | qa.magiq.cloud |

Plus white-label customer domains (Caselle, Software Solutions, Somerset Smith Partners, Springbrook, Univerus, Zobrio), each with its own MySQL database. Production runs 2 EC2 nodes behind one RDS instance; DB creds live in AWS Secrets Manager (`/magiq-auth/{env}/dbsecret`).

## Modules
- TenantManagement
- UserManagement
- AuthPolicy
- TokenIssuance
- OnBoarding

## Integrations
All MAGIQ cloud applications and APIs

## ADO Board
MagiqAuth

## Priority
High

## File Map

| File | Purpose |
|------|---------|
| brief.md | Project summary and constraints (stack line describes the future migration target — see "Stack: Current vs. Future Migration Target" above) |
| notes.md | Open question resolutions and session notes |
| risks.md | Risk register — currently empty |
| decisions/log.md | Architecture and design decisions (append-only) — currently empty |
| adrs/ | Formal ADRs for architectural decisions — currently empty |
| spec/ | Spec files — currently empty (target-architecture spec not started) |
| plans/ | Implementation plans for the *current* codebase — the most detailed, up-to-date technical context in this workspace |

## Decisions

All architecture and design decisions go in decisions/log.md.
Formal ADRs go in adrs/.

---

## Memory System

This folder contains MEMORY.md — your external memory for this project.

At the start of every session: Read MEMORY.md before responding. Use what you find — do not announce it.

Memory is user-triggered only. Only add entries when Chase explicitly asks using phrases like
"remember this", "make a note", "log this", "save this". Write immediately and confirm.

All memories are persistent until Chase explicitly asks to remove or change them.

Flag contradictions — never silently overwrite.
