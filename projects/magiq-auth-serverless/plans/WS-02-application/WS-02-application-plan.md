---
id: MAS-003
type: plan
project: magiq-auth-serverless
workstream: WS-02-application
repo: magiq-auth-serverless
tags: [application, oidc-client-registry]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-02 — Application

Platform OIDC client registry. Platform-scoped (not tenant-scoped). Secret rotation + redirect-uri changes.

Spec:
- `docs/spec/contexts/Application/README.md`
- `docs/spec/contexts/Application/aggregates/Application/*.md`

## Session invocation

> Picking up WS-02 (plan MAS-003). Application aggregate end-to-end. Platform-scoped — uses `TenantId = platform` sentinel per ADR-004. Secret rotation stores SHA-256 hash only; raw secret returned once.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name Application -Aggregate Application -Type auth.application`

## Phase 1 — Domain
- [ ] Aggregate with `AppGuid` (client_id), `ClientSecretHash`, redirect URIs, PKCE flags, IdP restrictions
- [ ] Platform sentinel tenant per ADR-004
- [ ] Events per `application.write-model.md`

## Phase 2 — Commands + handlers
- [ ] `RegisterApplication`, `RotateSecret`, `UpdateRedirectUris`, `SetIdpRestrictions`
- [ ] Reservation on application name
- [ ] Secret-generation: 32-byte random; store SHA-256(Base64); return raw once

## Phase 3 — Projections
- [ ] `auth-platform-read-models` projection per `application.read-model.md`

## Phase 4 — Hosts
- [ ] `Application.Admin` — `/platform/applications/**` writes
- [ ] `Application.Reads` — reads
- [ ] `Application.Projector` — SQS

## Phase 5 — Tests
- [ ] Scenarios in `application.scenarios.md`
- [ ] Secret rotation: hash stored, raw returned once, verify roundtrip

## Phase 6 — Deploy + validate

## Exit criteria

- All scenarios green
- Deployed to dev

## Session log

- 2026-10-15: plan drafted
