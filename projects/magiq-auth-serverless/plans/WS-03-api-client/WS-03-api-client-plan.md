---
id: MAS-004
type: plan
project: magiq-auth-serverless
workstream: WS-03-api-client
repo: magiq-auth-serverless
tags: [api-client, m2m, cross-tenant-consent]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-03 — ApiClient

Tenant-scoped M2M OAuth client. Single-tenant and multi-tenant via policy inside the aggregate (ADR-011 cross-tenant allowlist consent).

Spec:
- `docs/spec/contexts/ApiClient/README.md`
- `docs/spec/contexts/ApiClient/aggregates/ApiClient/*.md`

## Session invocation

> Picking up WS-03 (plan MAS-004). ApiClient aggregate end-to-end. Multi-tenant allowlist consent per ADR-011; name reservation keyed by `(TenantId, Name)`. Independent of WS-02.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name ApiClient -Aggregate ApiClient -Type auth.api-client`

## Phase 1 — Domain
- [ ] Aggregate with `ClientGuid`, secret hash, allowed scopes, token lifetime, `IsMultitenant`, `IsUnrestricted`, allowlist
- [ ] Cross-tenant consent reservation per ADR-011
- [ ] Events per `apiclient.write-model.md`

## Phase 2 — Commands + handlers
- [ ] `CreateApiClient`, `RotateSecret`, `AddToAllowlist`, `RemoveFromAllowlist`, `SetAllowlist`, `DeleteApiClient` (soft)
- [ ] Reservation keys: name + cross-tenant consent

## Phase 3 — Projections
- [ ] `auth-tenant-read-models` + by-customer index per `apiclient.read-model.md`

## Phase 4 — Hosts
- [ ] `ApiClient.Admin`, `ApiClient.Reads`, `ApiClient.Projector`

## Phase 5 — Tests
- [ ] Scenarios in `apiclient.scenarios.md`
- [ ] `API_CLIENT_NAME_TAKEN`, `API_CLIENT_CROSS_TENANT_CONSENT_TAKEN` paths

## Phase 6 — Deploy + validate

## Exit criteria

- All scenarios green
- Deployed to dev

## Session log

- 2026-10-15: plan drafted
