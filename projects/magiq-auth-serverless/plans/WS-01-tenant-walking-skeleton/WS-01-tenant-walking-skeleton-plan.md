---
id: MAS-002
type: plan
project: magiq-auth-serverless
workstream: WS-01-tenant-walking-skeleton
repo: magiq-auth-serverless
tags: [tenant, walking-skeleton, first-slice]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-01 — Tenant walking skeleton

**First end-to-end slice.** Validates the Phase 0 plumbing with the smallest aggregate.

Spec:
- `docs/spec/contexts/Tenant/README.md`
- `docs/spec/contexts/Tenant/aggregates/Tenant/tenant.write-model.md`
- `docs/spec/contexts/Tenant/aggregates/Tenant/tenant.read-model.md`
- `docs/spec/contexts/Tenant/aggregates/Tenant/tenant.api.md`
- `docs/spec/contexts/Tenant/aggregates/Tenant/tenant.scenarios.md`

## Session invocation

> Picking up WS-01 (plan MAS-002). First vertical slice — Tenant aggregate end-to-end. Follow `_template` from WS-00. Every scenario in `tenant.scenarios.md` must pass integration tests on dev.

## Phase 0 — Scaffold
- [ ] Run `scripts/new-module.ps1 -Name Tenant -Aggregate Tenant -Type auth.tenant`
- [ ] Add module projects to solution
- [ ] Confirm clean build

## Phase 1 — Domain
- [ ] `Tenant` aggregate per `tenant.write-model.md § State + Invariants`
- [ ] Value objects: `TenantId`, `TenantName`, `TenantStatus`, OIDC config VOs
- [ ] Creation + state-transition events — `TenantId` first field, `[EventVersion(1)]`

## Phase 2 — Commands + handlers
- [ ] Commands per `tenant.api.md` command list
- [ ] FluentValidation for each
- [ ] Handlers returning `Result<T, DomainError>`
- [ ] Name reservation via `TransactWriteItems` against `auth-name-reservations`
- [ ] `TenantIntegrationEventPublisher` — inline SNS publish

## Phase 3 — Projections
- [ ] Projector into `auth-tenant-read-models` + lookup projections per `tenant.read-model.md`
- [ ] `ProjectedVersion` idempotency on every write

## Phase 4 — Hosts
- [ ] `src/hosts/Tenant.Admin/` — FastEndpoints for `/platform/tenants/**` writes
- [ ] `src/hosts/Tenant.Reads/` — reads
- [ ] `src/hosts/Tenant.Projector/` — SQS consumer
- [ ] Each with Dockerfile + Lambda deployment via CDK

## Phase 5 — Tests
- [ ] Unit: aggregate invariants + event applying
- [ ] Integration (localstack): every scenario in `tenant.scenarios.md`
- [ ] Reservation conflict paths (`TENANT_NAME_TAKEN`, `TENANT_NAME_TOMBSTONED`)
- [ ] Concurrency retry (3× with backoff)

## Phase 6 — Deploy + validate
- [ ] Deploy three Lambdas + CDK stack to dev
- [ ] Create tenant via admin host → confirm event in `auth-events` → confirm projection row → read via reads host
- [ ] Suspend tenant → confirm `TenantSuspendedIntegration` on `auth-integration-events`
- [ ] CloudWatch logs correlated via `CorrelationId`
- [ ] X-Ray trace spans end-to-end

## Phase 7 — Capture learnings
- [ ] Update `src/_template/` with anything the slice revealed as missing
- [ ] Document patterns in `mgq-dotnet-platform/CLAUDE.md`
- [ ] File any spec audit findings surfaced

## Exit criteria

- Every `tenant.scenarios.md` scenario green in CI integration run
- Deployed and verified on dev
- Template updated with learnings

## Session log

- 2026-10-15: plan drafted
